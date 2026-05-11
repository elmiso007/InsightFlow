from datetime import datetime, timedelta,timezone
import pandas as pd
import sys
from sqlalchemy import create_engine, text
from psycopg2.extras import Json
import psycopg2
import os
import requests
import json
from email.utils import parsedate_to_datetime
from pathlib import Path
from bs4 import BeautifulSoup
import configparser

# include parent-parent path so `notifica` can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack, notify_slack_success


sql_path = Path(__file__).parent 

# Config path absolute (user requested)
config_path = Path(r"C:\Users\emerson.ramos\Desktop\projetos\config.ini").resolve()
if not config_path.exists():
    raise FileNotFoundError(f"Config file not found: {config_path}")

config = configparser.ConfigParser()
config.read(config_path, encoding='utf-8')

# Set up PostgreSQL connection from config
server = config.get('database', 'server', fallback='10.30.138.28')
database = config.get('database', 'database', fallback='report_requesttracker')
uid = config.get('database', 'uid', fallback='a_report')
pwd = config.get('database', 'pwd', fallback='Eequ8ohc')
engine_conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"

engine = create_engine(
    engine_conn_string,
    connect_args={"client_encoding": "utf8"}
)
#ngine = create_engine(engine_conn_string)
conn = engine.connect()



# Set up PostgreSQL connection
psy_conn = psycopg2.connect(
    dbname=database,
    user=uid,
    password=pwd,
    host=server
)
cur = psy_conn.cursor()

rotina = "Tray (Carrega Tickets Interactions)"

data_hora = datetime.now()
print(f"Inicio : {data_hora}")

DDL_URL = config.get('tray', 'DDL_URL', fallback='https://o192082-4c6.api001.octadesk.services')
TOKEN = config.get('tray', 'TOKEN', fallback='[REDACTED_TRAY_TOKEN]')
validate_ssl = config.getboolean('tray', 'verify_ssl', fallback=False)


def finalizar_programa():
    print("\033[92m" + "="*40)
    print("   🚀 PROGRAMA ENCERRADO COM SUCESSO! 🚀   ")
    print("="*40 + "\033[0m")
    sys.exit()


def ajusta_formato_data(atendimento):
    if atendimento:
        return datetime.fromisoformat(
            atendimento.replace("Z", "+00:00")
        )
    return None


agora_utc = datetime.now(timezone.utc)

data_final = agora_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
data_inicial = (agora_utc - timedelta(hours=3))\
    .strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

limit = 20



def get_interactions(DDL_URL, TOKEN, page, data_inicial, data_final, limit):

    endpoint = f"{DDL_URL}/tickets/interactions?from={data_inicial}&to={data_final}&page={page}&take={limit}&humanOnly=false&handlersOnly=false"

    print(endpoint)

    headers = {
        "accept": "application/json",
        "X-API-KEY": TOKEN,
        "Cache-Control": "no-cache"
    }

    try:
        response = requests.get(endpoint, headers=headers, verify=validate_ssl)
        
        if response.status_code == 200:
            # Retornamos o JSON e o objeto de headers completo
            return response.json(), response.headers, endpoint
        else:
            print(f"Erro na requisição: {response.status_code}")
            return None, None
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None, None

def limpar_html(texto):
    if not texto:
        return ""

    import re

    texto = re.sub(r'<!--.*?-->', '', texto, flags=re.S)
    texto = re.sub(r'<br\s*/?>', ' ', texto)
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = re.sub(r'[\u200c\u200b\u200d\uFEFF]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)

    return texto.strip()


try:    
    # Variáveis para armazenar os registros gerados
    carga = []
    bruto = []
    current_page = 1
   
    
    print("Iniciando coleta de dados...")

    while True:
        
        print(f"Coletando página {current_page}...")

        data, headers, endpoint = get_interactions(DDL_URL, TOKEN, current_page,data_inicial, data_final,limit)

        if not data:
            print("Sem dados, encerrando...")
            break
        
        print(f"Registros retornados: {len(data)}")

        pagina_atual = current_page


        request_id = headers.get('X-Correlation-Id')

        data_requisicao = parsedate_to_datetime(headers.get('Date'))
        

        
        print(f"Total de registros carregados: {len(carga)}")

        json_file = 'interactions.json'

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        for t in data:

            number = str(t.get("number"))
            interactions = t.get("interactions",[])  # Convertendo lista para string JSON
           
            for i in interactions:

                user = i.get("user", {})
                comments = i.get("comments", [])
                
                if comments:
                    comment = comments[0]

                    comments_content = comment.get("content")
                    comments_type = comment.get("type")
                    comments_is_public = comment.get("isPublic")
                else:
                    comments_content = None
                    comments_type = None
                    comments_is_public = None

                comments_content = limpar_html(comments_content)

                pc = i.get("propertiesChanges",{}) 


                registro = {
                    "number": number,  # id serial do chamado
                    "interaction_id": i.get("_id"), #ID interação (Não corresponde ao id do chamado)
                    "created_at": ajusta_formato_data(i.get("createdAt")),  # data de criação da insteração formatada
                    "user_id": user.get("_id"),  # id do usuário que fez a interação
                    "user_name": user.get("name"),  #Nome do usuário que fez a interação
                    "user_email":user.get("email"), # Email do usuário que fez a interação
                    "user_type":user.get("type"), #Perfil de usuário que fez a interação
                    "comments_content": comments_content,
                    "comments_type": comments_type,
                    "comments_is_public":comments_is_public,
                    "pc_channel_name":pc.get("channelName", None),
                    "pc_priority_name":pc.get("priorityName", None),
                    "pc_group_assigned_name": pc.get("groupAssignedName",None),
                    "pc_requester_name":pc.get("requesterName", None),
                    "pc_organization_name":pc.get("organizationName", None),
                    "pc_tags": pc.get("tags",None),
                    "pc_status":pc.get("status", None),
                    "pc_departamento": pc.get("departamento",None),
                    "pc_type_name":pc.get("typeName", None),
                    "pc_cc":pc.get("cc", None),
                    "pc_form":pc.get("form", None)
                    }

                carga.append(registro)    
            


            
            interactions = json.dumps(interactions,ensure_ascii=False)

            #CARREGAMENTO DO bruto COMPLETO POR ID
            registro_bruto = {
                "number": number,  # id serial do chamado
                "data_requisicao": data_requisicao,
                "request_id": request_id, #id da requisição 
                "pagina": pagina_atual,
                "payload": interactions,  #interactions
                "data_insercao":data_hora,
                "source": "API Tray",
                "endpoint": endpoint
            }

            bruto.append(registro_bruto)

        # 🚨 CONDIÇÃO DE PARADA
        if len(data) < limit:
            print("Última página alcançada.")
            break

        current_page += 1


    df_payload = pd.DataFrame(carga)
    df_bruto = pd.DataFrame(bruto)

    if not carga:
        msg = "Nenhum dado foi carregado da API. A execução será finalizada."
        print(msg)
        notify_slack(msg)
        finalizar_programa()

    df_payload.to_sql('payload_tickets_interactions',con=engine,if_exists='replace',index=False,schema='tray')
    df_bruto.to_sql('raw_data_tickets_interactions',con=engine,if_exists='append',index=False,schema='tray')

    total_linhas_inseridas = 0
    total_linhas_atualizadas = 0

     #Trunca a tabela stgchat
    table_name = 'tray.stg_tickets_interactions'
    truncate_query = f"TRUNCATE TABLE {table_name}"
    cur.execute(truncate_query)
    psy_conn.commit()
    print(f"Tabela {table_name} truncada com sucesso")

    # Alimenta a tabela tray.stg_tickets_interactions
    with open(rf'{sql_path}\InsereStgtickets_interactions.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    with engine.connect() as conn:
        result = conn.execute(query_insercao)
        linhas_inseridas = result.rowcount
        total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
        conn.commit()
        print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")
    
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    # Alimenta a tabela tray.tickets_interactions
    total_linhas_inseridas = 0
    table_name = 'tray.tickets_interactions'
    with open(rf'{sql_path}\Inseretickets_interactions.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    with engine.connect() as conn:
        result = conn.execute(query_insercao)
        linhas_inseridas = result.rowcount
        total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
        conn.commit()
        success_msg = f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}."
        print(success_msg)
        notify_slack_success(f":tray: {rotina}: {success_msg}")

    # notificação consolidada de sucesso para tickets
    final_msg = (f":tray: {rotina}: carga finalizada com sucesso. "
                 f"{len(carga)} registros processados. "
                 f"Payload: {df_payload.shape[0]} | Bruto: {df_bruto.shape[0]}.")
    print(final_msg)
    notify_slack_success(final_msg)

except Exception as e:
    err_msg = f"Ocorreu um erro na rotina {rotina}: {e}"
    print(err_msg)
    notify_slack(err_msg)
    logging.error(err_msg)

data_hora = datetime.now()
print(f"Fim : {data_hora}")

cur.close()
psy_conn.close()
conn.close()

finalizar_programa()
