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


# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack, notify_slack_success  

# Configurar logging
sql_path = Path(__file__).parent
logging.basicConfig(filename='erro_execucao.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

tabela = 'rawdata_chat'
schema = 'lw_octadesk'  
rotina = "Locaweb (Carrega Atendimentos Chat)"

# Obter o caminho absoluto para o arquivo config.ini
config_folder = f'{sql_path}/../..'
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

DDL_URL = "https://o203894-994.api003.octadesk.services"
TOKEN = "06b70186-121d-430b-98c9-405de0585920.8238b623-1a56-41e7-bd23-bb1893e70489"


def finalizar_programa():
    print("\033[92m" + "="*40)
    print("   🚀 PROGRAMA ENCERRADO COM SUCESSO! 🚀   ")
    print("="*40 + "\033[0m")
    sys.exit()


def ajusta_formato_data(atendimento):
    if atendimento:
        # Remove o 'Z' e adiciona deslocamento de fuso horário explícito
        if atendimento.endswith("Z"):
            atendimento = atendimento[:-1] + "+0000"
        
        # Ajuste para lidar com frações de segundo
        atendimento_convertido = datetime.strptime(atendimento, '%Y-%m-%dT%H:%M:%S.%f%z')
        
        # Ajustar o fuso horário (opcional)
        ajusta_fuso = atendimento_convertido - timedelta(hours=3)
        
        # Formatar a data no formato desejado
        atendimento = ajusta_fuso.strftime('%Y-%m-%d %H:%M:%S')
        return atendimento
    return None


def get_interactions(DDL_URL, TOKEN, page):
    
    sort = 'desc'
    limit = 100

    periodo = '2025-08-10T00%3A00%3A00.300Z'
    endpoint = f"{DDL_URL}/chat?filters[0][operator]=ge&filters[0][property]=createdAt&filters[0][value]={periodo}&page={page}&limit={limit}&sort[direction]={sort}"

    #endpoint = f'{DDL_URL}/chat?page={page}&limit={limit}&sort[direction]={sort}&sort[property]=updatedAt' 

    headers = {
        "accept": "application/json",
        "X-API-KEY": TOKEN
    }

    response = requests.get(endpoint, headers=headers)

    if response.status_code == 200:
        data = response.json()
        headersResp = response.headers
        return data, headersResp
    else:
        print(f"Falha na autenticação. Código de status: {response.status_code}")
        return None
    
    
total_linhas_inseridas = 0
total_linhas_atualizadas = 0

try:    
    # Variáveis para armazenar os registros gerados
    carga = []

    # Variável para verificar total de páginas
    data, headersResp = get_interactions(DDL_URL, TOKEN, 1)

    totalPages = headersResp.get('X-Total-Pages')
    print("Total de páginas: ", totalPages)
    totalPages = int(totalPages)+1

    #Loop para percorrer todas as páginas da requisição
    for page in range(1, totalPages): 
        #Chama a função que realiza a autenticação
        data, headersResp = get_interactions(DDL_URL, TOKEN, page)
        
        # Interrompe o loop se nenhum dado for retornado
        if not data:
            break  

        json_file = 'chat.json'

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        # Processar cada atendimento (Dados de cabeçalho)
        for atendimento in data:
            id = atendimento.get('id')
            protocolo = atendimento.get('number')
            canal = atendimento.get('channel')
            #Tratamento de formatos de data. Necessário chamar a função 'ajusta_formato_data' para formatar no padrão timestamp    
            data_inicio_interacao = atendimento.get('createdAt')   
            data_inicio_interacao = ajusta_formato_data(data_inicio_interacao)           
            data_ultima_interacao = atendimento.get('updatedAt')
            data_ultima_interacao = ajusta_formato_data(data_ultima_interacao)
            data_fim_interacao = atendimento.get('closedAt')
            data_fim_interacao = ajusta_formato_data(data_fim_interacao)

            # Estas variáveis usam um dicionário vazio como fallback
            contact_name = atendimento.get('contact', {}).get('name')
            contact_id = atendimento.get('contact', {}).get('id')  
            tags = atendimento.get('tags')
            com_bot = atendimento.get('withBot')
            status = atendimento.get('status')
            grupo_id = atendimento.get('group', {}).get('id')
            grupo_nome = atendimento.get('group', {}).get('name')
            agent_id = atendimento.get('agent', {}).get('id')   
            agent_name = atendimento.get('agent', {}).get('name')
            agent_email = atendimento.get('agent', {}).get('email')
            nao_lidas = atendimento.get('unreadMessages')
            origem = atendimento.get('origin'),
            statusDetail = atendimento.get('statusDetail')

            agentFirstMessageDate = atendimento.get('agentFirstMessageDate')
            agentFirstMessageDate = ajusta_formato_data(agentFirstMessageDate)

            assignedToAgentDate = atendimento.get('assignedToAgentDate')
            assignedToAgentDate = ajusta_formato_data(assignedToAgentDate)

            assignedToGroupDate = atendimento.get('assignedToGroupDate')
            assignedToGroupDate = ajusta_formato_data(assignedToGroupDate)

            pesquisa = atendimento.get('survey',{}).get('response')
            comentario = atendimento.get('survey',{}).get('comment')

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
                "status_detail":statusDetail,
                "data_inicio_interacao_agente":agentFirstMessageDate,
                "atribuicao_agente":assignedToAgentDate,
                "atribuicao_grupo":assignedToGroupDate,
                "pesquisa":pesquisa,
                "comentario":comentario
            }

            carga.append(registro)
            
        print("Página: ", page)
            

    df_content = pd.DataFrame(carga)

    print(df_content)

    # df_content.to_sql(tabela, con=engine, if_exists='replace', index=False, schema= schema)

    # # Trunca a tabela stgchat
    # table_name = 'lw_octadesk.stgchat'
    # truncate_query = f"TRUNCATE TABLE {table_name}"
    # cur.execute(truncate_query)
    # psy_conn.commit()
    # print(f"Tabela {table_name} truncada com sucesso") 

    # # Alimenta a tabela octadesk.stgchat
    # with open(f'{sql_path}/StgInsereDados.sql', 'r', encoding='utf-8') as file:
    #     query_insercao = text(file.read())

    # with engine.connect() as conn:
    #     result = conn.execute(query_insercao)
    #     linhas_inseridas = result.rowcount
    #     total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
    #     conn.commit()
    #     print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")

    # #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # # Alimenta a tabela octadesk.chat
    # total_linhas_inseridas = 0
    # table_name = 'lw_octadesk.chat'
    # with open(f'{sql_path}/InsereDados.sql', 'r', encoding='utf-8') as file:
    #     query_insercao = text(file.read())

    # with engine.connect() as conn:
    #     result = conn.execute(query_insercao)
    #     linhas_inseridas = result.rowcount
    #     total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
    #     conn.commit()
    #     print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")

    # #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # # Atualiza a tabela octadesk.chat
    # with open(f'{sql_path}/AtualizaDados.sql', 'r', encoding='utf-8') as file:
    #     query_insercao = text(file.read())

    # with engine.connect() as conn:
    #     result = conn.execute(query_insercao)
    #     linhas_atualizadas = result.rowcount
    #     total_linhas_atualizadas += linhas_atualizadas  # Contagem de linhas inseridas
    #     conn.commit()
    #     print(f"{total_linhas_atualizadas} linhas atualizadas na tabela {table_name}.")


except Exception as e:
    print("Ocorreu um erro:", e)
    logging.error(f"Ocorreu um erro: {e}")
    #notify_slack(f"Erro na execução da {rotina}: {e}", rotina)

# Notificação consolidada após o processo
#notify_slack_success(f"{total_linhas_inseridas} linhas inseridas e {total_linhas_atualizadas} linhas atualizadas na tabela {table_name}. :logo-locaweb_ico:",total_linhas_inseridas,total_linhas_atualizadas, rotina)

data_hora = datetime.now()
print(f"Fim : {data_hora}")

cur.close()
psy_conn.close()
#conn.close()

finalizar_programa()
