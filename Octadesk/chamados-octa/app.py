from datetime import datetime, timedelta
import pandas as pd
import sys
from sqlalchemy import create_engine, text
import psycopg2
import os
import requests
import json
import logging
import configparser

# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack, notify_slack_success  

# Configurar logging
logging.basicConfig(filename='erro_execucao.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

rotina = "Octadesk (Carrega Tickets no Backlog)"


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
conn = engine.connect()

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

DDL_URL = "https://help.apibeta.octadesk.services"
#TOKEN = "75657565-0f17-4044-ab0b-3268d2052a6b.ae43d054-7ec4-4cf1-8b01-7ae37436af67"
TOKEN = "75657565-0f17-4044-ab0b-3268d2052a6b.13dd5460-8d60-4df0-b79a-7d842db006dc"

def finalizar_programa():
    print("\033[92m" + "="*40)
    print("   🚀 PROGRAMA ENCERRADO COM SUCESSO! 🚀   ")
    print("="*40 + "\033[0m")
    sys.exit()


def ajusta_formato_data(atendimento):
    if atendimento:
        # Substitui 'Z' por '+0000' para representar UTC corretamente
        if atendimento.endswith("Z"):
            atendimento = atendimento[:-1] + "+0000"

        # Tenta converter a string com e sem frações de segundo
        formatos = ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S.%f%z']
        
        for formato in formatos:
            try:
                atendimento_convertido = datetime.strptime(atendimento, formato)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Formato de data inválido: {atendimento}")

        # Ajustar o fuso horário (exemplo: UTC-3)
        ajusta_fuso = atendimento_convertido - timedelta(hours=3)

        # Formatar a data no formato desejado
        return ajusta_fuso.strftime('%Y-%m-%d %H:%M:%S')

    return None


def get_interactions(DDL_URL, TOKEN, page):
    
    sort = 'desc'
    limit = 100

    #periodo = '2025-03-01T00%3A00%3A00.300Z'
    #endpoint = f"{DDL_URL}/chat?filters[0][operator]=ge&filters[0][property]=createdAt&filters[0][value]={periodo}&page={page}&limit={limit}&sort[direction]={sort}"

    endpoint = f"{DDL_URL}/tickets?page={page}&limit={limit}&sort[direction]={sort}&sort[property]=updatedAt"

    headers = {
        "accept": "application/json",
        "X-API-KEY": TOKEN
    }

    response = requests.get(endpoint, headers=headers, timeout=(60), verify=False)
    #response = requests.get(endpoint, headers=headers)


    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Falha na autenticação. Código de status: {response.status_code}")
        notify_slack(f"Falha na autenticação. Código de status: {response.status_code}", rotina)
        return None

try:    
    # Variáveis para armazenar os registros gerados
    carga = []

    #Loop para percorrer todas as páginas da requisição
    for page in range(1, 3):     
    
        tickets = get_interactions(DDL_URL,TOKEN,page)

        if not tickets:
            #print(f"Nenhum ticket encontrado na página {page}")
            continue  # pula pra próxima página do loop

        
        json_file = 'tickets.json'

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(tickets, f, ensure_ascii=False, indent=4)

        for t in tickets:
                            
            participating_assigned = t.get("participatingAssigned", [])  # Convertendo lista para string JSON
            ultima_atribuicao = participating_assigned[-1] if participating_assigned else {}
            participating_assigned = json.dumps(participating_assigned)  # Mantendo a string JSON
            participating_assigned_ultimo_id = ultima_atribuicao.get("id", "")
            participating_assigned_ultimo_name = ultima_atribuicao.get("name", "")

            registro = {
                "id": t.get("id"),  # id serial do chamado
                "number": t.get("number"),  # numero do chamado
                "summary": t.get("summary"),  # assunto
                "status_id": t.get("status", {}).get("id"),  # id do status do chamado
                "status_name": t.get("status", {}).get("name"),  # status atual
                "channel_id": t.get("channel", {}).get("id"),  # id serial do canal
                "channel_name": t.get("channel", {}).get("name"),  # nome do canal
                "requester_id": t.get("requester", {}).get("id"),  # id do solicitante do ticket
                "requester_name": t.get("requester", {}).get("name"),  # nome do solicitante
                "requester_email": t.get("requester", {}).get("email"),  # email do solicitante
                ## Validar custom fields aqui
                "group_id": t.get("group", {}).get("id"),  # id do grupo
                "group_name": t.get("group", {}).get("name"),  # nome do grupo
                "priority_id": t.get("priority", {}).get("id"),  # id do status de prioridade
                "priority_name": t.get("priority", {}).get("name"),  # nome do status de prioridade
                "organization_id": t.get("organization", {}).get("id"),  # id da organização solicitante
                "organization_name": t.get("organization", {}).get("name"),  # nome da organização
                # organization também possui campos customizados
                "assigned_id": t.get("assigned", {}).get("id"),  # id assinatura
                "participating_assigned": participating_assigned,
                "participating_assigned_id": participating_assigned_ultimo_id,
                "participating_assigned_name": participating_assigned_ultimo_name,
                "tags": json.dumps(t.get("tags", [])),  # Convertendo lista para string JSON
                "created_at": ajusta_formato_data(t.get("createdAt")),  # data de criação formatada e com tratamento do fuso
                "interactions_count": t.get("interactionsCount", {}),  # interações no chamado
                "update_at": ajusta_formato_data(t.get("updatedAt")),  # ultima atualização
                "update_by_id": t.get("updatedBy", {}).get("id"),  # id de quem fez a última atualização
                "update_by_name": t.get("updatedBy", {}).get("nome"),  # nome de quem fez a última atualização
                "update_by_email": t.get("updatedBy", {}).get("email"),  # email de quem fez a última atualização
                # +1 Custom fields
                "li_id": t.get("lastInteraction", {}).get("id"),
                "li_comments": json.dumps(t.get("lastInteraction", {}).get("comments", [])),  # Convertendo lista para string JSON
                "li_properties_changes_channel": json.dumps(t.get("lastInteraction", {}).get("propertiesChanges", {}).get("channel", {})),
                "li_properties_changes_requester": json.dumps(t.get("lastInteraction", {}).get("propertiesChanges", {}).get("requester", {})),
                "li_properties_changes_organization": json.dumps(t.get("lastInteraction", {}).get("propertiesChanges", {}).get("organization", {})),
                "li_properties_changes_status": json.dumps(t.get("lastInteraction", {}).get("propertiesChanges", {}).get("status", {})),
                "li_properties_changes_form": json.dumps(t.get("lastInteraction", {}).get("propertiesChanges", {}).get("form", {})),
                "li_attachments": json.dumps(t.get("lastInteraction", {}).get("attachments", [])),  # Convertendo lista para string JSON
                "lhi_id": t.get("lastHumanInteraction",{}).get("id"),
                "lhi_attachments": json.dumps(t.get("lastHumanInteraction", {}).get("attachments", [])),  # Convertendo lista para string JSON
                "lhi_properties_changes_channel": json.dumps(t.get("lastHumanInteraction", {}).get("propertiesChanges", {}).get("channel", {})),
                "lhi_properties_changes_requester": json.dumps(t.get("lastHumanInteraction", {}).get("propertiesChanges", {}).get("requester", {})),
                "lhi_properties_changes_organization": json.dumps(t.get("lastHumanInteraction", {}).get("propertiesChanges", {}).get("organization", {})),
                "lhi_properties_changes_status": json.dumps(t.get("lastHumanInteraction", {}).get("propertiesChanges", {}).get("status", {})),
                "lhi_properties_changes_form": json.dumps(t.get("lastHumanInteraction", {}).get("propertiesChanges", {}).get("form", {}))
            }

            carga.append(registro)

    df_content = pd.DataFrame(carga)

    if not carga:
        print("Nenhum dado foi carregado da API. A execução será finalizada.")
        exit()  


    #df_content.to_csv('teste.csv',index=False)

    df_content.to_sql('rawdata_tickets',con=engine,if_exists='replace',index=False,schema='octadesk')


    total_linhas_inseridas = 0
    total_linhas_atualizadas = 0

    # Trunca a tabela stgchat
    table_name = 'octadesk.stgtickets'
    truncate_query = f"TRUNCATE TABLE {table_name}"
    cur.execute(truncate_query)
    psy_conn.commit()
    print(f"Tabela {table_name} truncada com sucesso")

    # Alimenta a tabela octadesk.stgchat
    with open(r'C:\Users\lucas.abner\Desktop\Rotinas Python\Octadesk\chamados-octa\InsereStgTickets.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    with engine.connect() as conn:
        result = conn.execute(query_insercao)
        linhas_inseridas = result.rowcount
        total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
        conn.commit()
        print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")
    
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    # Alimenta a tabela octadesk.ticketsbacklog
    total_linhas_inseridas = 0
    table_name = 'octadesk.ticketsbacklog'
    with open(r'C:\Users\lucas.abner\Desktop\Rotinas Python\Octadesk\chamados-octa\InsereTicketsBacklog.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    with engine.connect() as conn:
        result = conn.execute(query_insercao)
        linhas_inseridas = result.rowcount
        total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
        conn.commit()
        print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Notificação consolidada após o processo
    notify_slack_success(f"{total_linhas_inseridas} linhas inseridas e {total_linhas_atualizadas} linhas atualizadas na tabela {table_name}.  :octadesk:",total_linhas_inseridas,total_linhas_atualizadas, rotina)



except Exception as e:
    print("Ocorreu um erro:", e)
    logging.error(f"Ocorreu um erro: {e}")
    notify_slack(f"Erro na execução da {rotina}: {e}", rotina)



data_hora = datetime.now()
print(f"Fim : {data_hora}")

cur.close()
psy_conn.close()
conn.close()

finalizar_programa()
