import requests
import pandas as pd
from datetime import datetime, timedelta,timezone
import json
import os
import sys
import logging
import configparser
from sqlalchemy import create_engine, text
import psycopg2
from pathlib import Path
from psycopg2.extras import Json
from email.utils import parsedate_to_datetime



# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack, notify_slack_success  

# Configurar logging
logging.basicConfig(filename='erro_execucao.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')


schema = 'cplug'  
rotina = "Cplug (Carrega data Chat)"

# Obter o caminho absoluto para o arquivo config.ini
config_folder = r'C:\Users\lucas.abner\Desktop\Rotinas Python'
config_file_path = os.path.join(config_folder, 'config.ini')

# Ler as configurações do arquivo config.ini
config = configparser.ConfigParser()
config.read(config_file_path)

# Set up PostgreSQL connection
server = config['database']['server']
database = config['database']['database']
uid = config['database']['uid']
pwd = config['database']['pwd']
conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
engine = create_engine(conn_string)
connection = engine.connect()

# Set up PostgreSQL connection
psy_conn = psycopg2.connect(
    dbname=database,
    user=uid,
    password=pwd,
    host=server
)
cur = psy_conn.cursor()

data_hora = datetime.now()
print(f"Inicio : {data_hora}")

DDL_URL = config['cplug']['DDL_URL'].strip()
TOKEN = config['cplug']['TOKEN'].strip()


def finalizar_programa():
    print("\033[92m" + "="*40)
    print("   🚀 PROGRAMA ENCERRADO COM SUCESSO! 🚀   ")
    print("="*40 + "\033[0m")
    sys.exit()


def ajusta_formato_data(t):
    if t:
        return datetime.fromisoformat(
            t.replace("Z", "+00:00")
        )
    return None

agora_utc = datetime.now(timezone.utc)


periodo = (agora_utc - timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
limit = 100

def get_interactions(DDL_URL, TOKEN, page, periodo,limit):
    
    endpoint = f"{DDL_URL}/chat?filters[0][operator]=ge&filters[0][property]=updatedAt&filters[0][value]={periodo}&page={page}&limit={limit}&sort[direction]=asc"

    headers = {
        "accept": "application/json",
        "X-API-KEY": TOKEN
    }

    response = requests.get(endpoint, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return response.json(), response.headers, endpoint
    else:
        print(f"Falha na autenticação. Código de status: {response.status_code}")
        return None
    
    
total_linhas_inseridas = 0
total_linhas_atualizadas = 0

try:    
    # Variáveis para armazenar os registros gerados
    carga = []
    bruto = []
    current_page = 1
    total_pages = None
    has_next = True

    #Loop para percorrer todas as páginas da requisição
    while has_next:
        print(f"Coletando página {current_page}...")

        # Chama a função que realiza a requisição
        data, headers, endpoint = get_interactions(DDL_URL, TOKEN, current_page,periodo,limit)

        if not data:
            print("Sem dados retornados. Encerrando...")
            break

        # Captura total de páginas apenas na primeira requisição
        if current_page == 1:
            total_pages = int(headers.get('X-Total-Pages', 1))
            print(f"Total de páginas: {total_pages}")

        request_id = headers.get('X-Correlation-Id')
        data_requisicao = parsedate_to_datetime(headers.get('Date'))

        # Salva o JSON (se quiser manter histórico, depois te mostro como versionar por página)
        #json_file = 'chat_cplug.json'
        #with open(json_file, 'w', encoding='utf-8') as f:
        #    json.dump(data, f, ensure_ascii=False, indent=4)

        # Controle de paginação baseado no total
        if current_page >= total_pages:
            has_next = False
            print(f"Fim da coleta. Total de páginas processadas: {current_page}")
        else:
            current_page += 1

        try:
            # Processar cada atendimento (Dados de cabeçalho)
            for t in data:

                id = t.get('id')

                id = str(t.get("id"))

              #CARREGAMENTO DO bruto COMPLETO POR ID
                registro_bruto = {
                "id": id, #id do ticket
                "data_requisicao": data_requisicao,
                "request_id": request_id, #id da requisição 
                "pagina": current_page,
                "payload": Json(t), #JSON bruto do ticket
                "data_insercao":data_hora,
                "source": "API tray",
                "endpoint": endpoint
                }

                protocolo = t.get('number')
                canal = t.get('channel')
                #Tratamento de formatos de data. Necessário chamar a função 'ajusta_formato_data' para formatar no padrão timestamp    
                data_inicio_interacao = t.get('createdAt')   
                data_inicio_interacao = ajusta_formato_data(data_inicio_interacao)           
                data_ultima_interacao = t.get('updatedAt')
                data_ultima_interacao = ajusta_formato_data(data_ultima_interacao)
                data_fim_interacao = t.get('closedAt')
                data_fim_interacao = ajusta_formato_data(data_fim_interacao)

                # Estas variáveis usam um dicionário vazio como fallback
                contact_name = t.get('contact', {}).get('name')
                contact_id = t.get('contact', {}).get('id')  
                tags = t.get('tags')
                com_bot = t.get('withBot')
                status = t.get('status')
                grupo_id = t.get('group', {}).get('id')
                grupo_nome = t.get('group', {}).get('name')
                agent_id = t.get('agent', {}).get('id')
                agent_name = t.get('agent', {}).get('name')
                agent_email = t.get('agent', {}).get('email')
                nao_lidas = t.get('unreadMessages')
                origem = t.get('origin')
                bot_name = t.get('botName')
                conversation_origin = t.get('conversationOrigin')
                statusDetail = t.get('statusDetail')

                agentFirstMessageDate = t.get('agentFirstMessageDate')
                agentFirstMessageDate = ajusta_formato_data(agentFirstMessageDate)

                assignedToAgentDate = t.get('assignedToAgentDate')
                assignedToAgentDate = ajusta_formato_data(assignedToAgentDate)

                assignedToGroupDate = t.get('assignedToGroupDate')
                assignedToGroupDate = ajusta_formato_data(assignedToGroupDate)

                pesquisa = t.get('survey',{}).get('response')
                comentario = t.get('survey',{}).get('comment')

                #lista 'bot'
                bot = t.get('bot') or {}

                bot_contact_started_at = ajusta_formato_data(bot.get('contactStartedAt'))
                bot_assigned_at = ajusta_formato_data(bot.get('assignedAt'))
                bot_id = bot.get('id')
                bot_name = bot.get('name')
                bot_transferred_to_human_at = ajusta_formato_data(bot.get('transferredToHumanAt'))
                bot_resolved_by_bot = bot.get('resolvedByBot')
                    
                # Serializar as variáveis para criação do DF que será inserido no banco.
                registro = {
                    "id": id,
                    "protocolo": protocolo,
                    "canal": canal,
                    "data_inicio_interacao": data_inicio_interacao,
                    "data_ultima_interacao": data_ultima_interacao,
                    "data_fim_interacao": data_fim_interacao,
                    "contact_name": contact_name,
                    "tags": tags,
                    "com_bot": com_bot,
                    "status": status,
                    "grupo_id": grupo_id,
                    "grupo_nome": grupo_nome,
                    "agent_id":agent_id,
                    "agent_email": agent_email,
                    "agent_name": agent_name,
                    "nao_lidas": nao_lidas,
                    "contact_id":contact_id,
                    "origem": origem,
                    "bot_name": bot_name,
                    "conversation_origin": conversation_origin,
                    "status_detail":statusDetail,
                    "data_inicio_interacao_agente":agentFirstMessageDate,
                    "atribuicao_agente":assignedToAgentDate,
                    "atribuicao_grupo":assignedToGroupDate,
                    "pesquisa":pesquisa,
                    "comentario":comentario,
                    "bot_contact_started_at":bot_contact_started_at,
                    "bot_assigned_at":bot_assigned_at,
                    "bot_id":bot_id,
                    "bot_name":bot_name,
                    "bot_transferred_to_human_at":bot_transferred_to_human_at,
                    "bot_resolved_by_bot":bot_resolved_by_bot
                }

                carga.append(registro)
                bruto.append(registro_bruto)

        except Exception as e:
            print("Erro no registro:", t)
            raise e



    df_payload = pd.DataFrame(carga)
    df_bruto = pd.DataFrame(bruto)


    df_payload.to_sql('payload_chat', con=engine, if_exists='replace', index=False, schema= schema)
    df_bruto.to_sql('raw_data_chat', con=engine, if_exists='append', index=False, schema= schema)

    # Trunca a tabela stg_chat
    table_name = 'cplug.stg_chat'
    truncate_query = f"TRUNCATE TABLE {table_name}"
    cur.execute(truncate_query)
    psy_conn.commit()
    print(f"Tabela {table_name} truncada com sucesso")

    sql_path = Path(__file__).parent 

    # Alimenta a tabela cplug.stg_chat
    with open(f'{sql_path}/StgInsereDados.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    with engine.connect() as conn:
        result = conn.execute(query_insercao)
        linhas_inseridas = result.rowcount
        total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
        conn.commit()
        print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Alimenta a tabela cplug.chat
    total_linhas_inseridas = 0
    table_name = 'cplug.chat'
    with open(f'{sql_path}/InsereDados.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    with engine.connect() as conn:
        result = conn.execute(query_insercao)
        linhas_inseridas = result.rowcount
        total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
        conn.commit()
        print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Atualiza a tabela octadesk.chat
    with open(f'{sql_path}/AtualizaDados.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    with engine.connect() as conn:
        result = conn.execute(query_insercao)
        linhas_atualizadas = result.rowcount
        total_linhas_atualizadas += linhas_atualizadas  # Contagem de linhas inseridas
        conn.commit()
        print(f"{total_linhas_atualizadas} linhas atualizadas na tabela {table_name}.")


except Exception as e:
   print("Ocorreu um erro:", e)
   logging.error(f"Ocorreu um erro: {e}")
   notify_slack(f"Erro na execução da {rotina}: {e}", rotina)

# Notificação consolidada após o processo
notify_slack_success(f"{total_linhas_inseridas} linhas inseridas e {total_linhas_atualizadas} linhas atualizadas na tabela {table_name}. :cplug_logo: ",total_linhas_inseridas,total_linhas_atualizadas, rotina)
logging.info("Tabela Chat alimentada. Report enviado com sucesso ao Slack.")
data_hora = datetime.now()
print(f"Fim : {data_hora}")

cur.close()
psy_conn.close()
#conn.close()

finalizar_programa()