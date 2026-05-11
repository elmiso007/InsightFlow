import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import logging
import psycopg2
import time
import sys
import os 
import configparser


# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack, notify_slack_success  

# Configurar logging
logging.basicConfig(filename='erro_execucao.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

rotina = "Octadesk (Carrega Contatos)"

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

conn = None

data_hora = datetime.now()
print(f"Inicio : {data_hora}")

data_hoje = datetime.now().strftime("%Y-%m-%d")
hora_atual = datetime.now().strftime("%H:%M:%S")
hora_inicial = (datetime.now() - timedelta(hours=5)).strftime("%H:%M:%S")

query = f"SELECT distinct contact_id FROM octadesk.vw_atendimentos_completos where data_inicio_interacao BETWEEN '{data_hoje} {hora_inicial}' AND '{data_hoje} {hora_atual}' AND contact_id IS NOT NULL;"
df = pd.read_sql_query(query,connection)
connection.close()


DDL_URL = "https://help.apibeta.octadesk.services"
TOKEN = "75657565-0f17-4044-ab0b-3268d2052a6b.70be86ec-b219-41ae-a16c-8d73350d3618"

def get_contacts(DDL_URL, TOKEN, id):

    endpoint = f"{DDL_URL}/contacts/{id}"

    headers = {
        "accept": "application/json",
        "X-API-KEY": TOKEN
    }

    response = requests.get(endpoint, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Falha na autenticação. Código de status: {response.status_code}")
        return None
    
def finalizar_programa():
    print("\033[92m" + "="*40)
    print("   🚀 PROGRAMA ENCERRADO COM SUCESSO! 🚀   ")
    print("="*40 + "\033[0m")
    sys.exit()

total_linhas_inseridas = 0
total_linhas_atualizadas = 0

try:
    df_contacts = df['contact_id']

    # Variáveis para armazenar os registros gerados
    fullcontacts = []

    contador = 0  # Inicializa o contador

    for contact_id in df_contacts:
        try:
            #print(f"Tentando buscar contato: {contact_id}")  # <-- Adicione esta linha para verificar os IDs
            
            contact_data = get_contacts(DDL_URL, TOKEN, contact_id)
            
            #print(f"Resposta da API para {contact_id}: {contact_data}")  # <-- Verifica a resposta da API

            # Se a resposta for None ou vazia, apenas pule
            if not contact_data:
                print(f"Contato {contact_id} não encontrado")
                continue

            # Incrementa o contador
            contador += 1

            # Pausa se atingir 9 requisições
            if contador % 9 == 0:
                time.sleep(2)

            # Salva o contato em um arquivo JSON (pode ser útil para depuração)
            #with open(f'contact_{contact_id}.json', 'w', encoding='utf-8') as file:
            #    json.dump(contact_data, file, ensure_ascii=False, indent=4)

            # Extrai os dados do contato
            contact_name = contact_data.get('name')
            contact_email = contact_data.get('email')
            numeros_tel_json = json.dumps(contact_data.get("phoneContacts", [])) if contact_data.get("phoneContacts") else None
            telefone = next((item.get('number') for item in contact_data.get('phoneContacts', []) if isinstance(item, dict)), None)
            country_code = next((item.get('countryCode') for item in contact_data.get('phoneContacts', []) if isinstance(item, dict)), None)
            custom_fields = {item["key"]: item["value"] for item in contact_data.get("customFields", []) if isinstance(item, dict)}
            chat_id = custom_fields.get("chat_id-conversa")
            subdominio_octadesk = custom_fields.get("subdominio_octadesk")
            nome_da_empresa = custom_fields.get('nome_da_empresa')
            cnpj = custom_fields.get('cnpj')
            v2_cnpj = custom_fields.get('v2_cnpj')
            cluster = custom_fields.get('cluster')
            id_do_contato_no_hubspot = custom_fields.get('id_do_contato_no_hubspot')
            periodo_de_onboarding = custom_fields.get('periodo_de_onboarding')
            cs_responsavel = custom_fields.get('cs_responsavel')
            organization_id = contact_data.get('organization', {}).get('id')
            organization_name = contact_data.get('organization', {}).get('name')

            registro = {
                "contact_id": contact_id,
                "contact_name": contact_name,
                "contact_email": contact_email,
                "country_code": country_code,
                "telefone": telefone,
                "numeros_tel": numeros_tel_json,
                "chat_id": chat_id,
                "subdominio_octadesk": subdominio_octadesk,
                "nome_da_empresa": nome_da_empresa,
                "cnpj": cnpj,
                "v2_cnpj": v2_cnpj,
                "cluster": cluster,
                "id_do_contato_no_hubspot": id_do_contato_no_hubspot,
                "periodo_de_onboarding": periodo_de_onboarding,
                "cs_responsavel": cs_responsavel,
                "organization_id": organization_id,
                "organization_name": organization_name
            }

            fullcontacts.append(registro)

        except Exception as e:
            print(f"Erro ao processar contato {contact_id}: {e}")
            continue  # Continua com o próximo contato mesmo em caso de erro

    df_content = pd.DataFrame(fullcontacts)
    df_content.to_sql('rawdata_contacts', con=engine, if_exists='replace', index=False, schema= 'octadesk')

        # Verifica se a coluna 'numeros_tel' existe antes de tentar convertê-la
    if 'numeros_tel' in df_content.columns:
        df_content['numeros_tel'] = df_content['numeros_tel'].apply(
            lambda x: json.dumps(x) if isinstance(x, dict) else x)
        
    # Verifica se a coluna 'numeros_tel' existe antes de tentar convertê-la
    if 'chat_id' in df_content.columns:
        df_content['chat_id'] = df_content['chat_id'].apply(
            lambda x: json.dumps(x) if isinstance(x, dict) else x)
        
    # Verifica se a coluna 'numeros_tel' existe antes de tentar convertê-la
    if 'subdominio_octadesk' in df_content.columns:
        df_content['subdominio_octadesk'] = df_content['subdominio_octadesk'].apply(
            lambda x: json.dumps(x) if isinstance(x, dict) else x)
        
    # Verifica se a coluna 'numeros_tel' existe antes de tentar convertê-la
    if 'cluster' in df_content.columns:
        df_content['cluster'] = df_content['cluster'].apply(
            lambda x: json.dumps(x) if isinstance(x, dict) else x)



# Trunca a tabela stgchat
    table_name = 'octadesk.stgcontatos'
    truncate_query = f"TRUNCATE TABLE {table_name}"
    cur.execute(truncate_query)
    psy_conn.commit()
    print(f"Tabela {table_name} truncada com sucesso")

    # Alimenta a tabela octadesk.stgchat
    with open(r'C:\Users\lucas.abner\Desktop\Rotinas Python\Octadesk\contatos\StgInsereDados.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    with engine.connect() as conn:
        result = conn.execute(query_insercao)
        linhas_inseridas = result.rowcount
        total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
        conn.commit()
        print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Alimenta a tabela octadesk.chat
    total_linhas_inseridas = 0
    table_name = 'octadesk.contatos'
    with open(r'C:\Users\lucas.abner\Desktop\Rotinas Python\Octadesk\contatos\InsereDados.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    with engine.connect() as conn:
        result = conn.execute(query_insercao)
        linhas_inseridas = result.rowcount
        total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
        conn.commit()
        print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Atualiza a tabela octadesk.chat
    with open(r'C:\Users\lucas.abner\Desktop\Rotinas Python\Octadesk\contatos\AtualizaDados.sql', 'r', encoding='utf-8') as file:
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
    #notify_slack(f"Erro na execução da {rotina}: {e}", rotina)

# Notificação consolidada após o processo
notify_slack_success(f"{total_linhas_inseridas} linhas inseridas e {total_linhas_atualizadas} linhas atualizadas na tabela {table_name}.",total_linhas_inseridas,total_linhas_atualizadas, rotina)


data_hora = datetime.now()
print(f"Fim : {data_hora}")

conn.close()
connection.close()
engine.dispose()

finalizar_programa()

