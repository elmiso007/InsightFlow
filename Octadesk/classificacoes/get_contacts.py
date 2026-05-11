import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import logging
import psycopg2
import sys
import os 
import configparser
from pathlib import Path

sql_path = Path(__file__).parent 

# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack, notify_slack_success  

# Configurar logging
logging.basicConfig(filename='erro_execucao.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

rotina = "Octadesk (Carrega Classificações)"

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

data_hora = datetime.now()
print(f"Inicio : {data_hora}")

data_hoje = datetime.now().strftime("%Y-%m-%d")
hora_atual = datetime.now().strftime("%H:%M:%S")
hora_inicial = (datetime.now() - timedelta(hours=2)).strftime("%H:%M:%S")

query = f"SELECT distinct id FROM octadesk.chat WHERE data_ultima_interacao >='{data_hoje} {hora_inicial}'"
#query = f"SELECT distinct id FROM octadesk.chat WHERE data_ultima_interacao BETWEEN '2026-02-01 00:00:00' and '2026-02-02 23:59:59'"

df = pd.read_sql_query(query,connection)
connection.close()


DDL_URL = "https://help.apibeta.octadesk.services"
#TOKEN = "75657565-0f17-4044-ab0b-3268d2052a6b.70be86ec-b219-41ae-a16c-8d73350d3618"
TOKEN = "75657565-0f17-4044-ab0b-3268d2052a6b.13dd5460-8d60-4df0-b79a-7d842db006dc"

def get_contacts(DDL_URL, TOKEN, id):

    endpoint = f"{DDL_URL}/chat/{id}"

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
    

total_linhas_inseridas = 0
total_linhas_atualizadas = 0

try:
    df_contacts = df['id']

    contagem = len(df_contacts)

    print(f'contagem de linhas {contagem}')

    # Variáveis para armazenar os registros gerados
    fullcontacts = []

    contador = 0  # Inicializa o contador

    for contact_id in df_contacts:
        try:           
            atendimento = get_contacts(DDL_URL, TOKEN, contact_id)
         
            # Se a resposta for None ou vazia, apenas pule
            if not atendimento:
                print(f"Contato {contact_id} não encontrado")
                continue

            # Extrai os dados do contato

            caminho_arquivo = os.path.join(sql_path, 'contacts.json')
            with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                json.dump(atendimento, f, ensure_ascii=False, indent=4)
            
            chat_id = atendimento.get('id')
            updated_at = atendimento.get('updatedAt')
            updated_at = ajusta_formato_data(updated_at)

            contact = atendimento.get('contact', {})
            
            contact_id = contact.get('id', None)
            contact_name = contact.get('name', None)
            contact_email = contact.get('email', None)

            organization = contact.get('organization',{})
            organization_number = organization.get('number',None)
            organization_name = organization.get('name',None)

            organization_cf = organization.get('customField',{})
            org_cf_topmrr = organization_cf.get('top100_mrr_ou_atritado',None)
            org_cf_tipo_uso_pri = organization_cf.get('qual_o_tipo_de_uso_primario',None)
            org_cf_tipo_uso_sec = organization_cf.get('qual_o_tipo_de_uso_primario',None)
            org_cf_plano = organization_cf.get('plano',None)
            org_cf_mrr = organization_cf.get('mrr',None)
            codigo_do_plano = organization_cf.get('codigo_do_plano',None)

            messages_count = atendimento.get('messagesCount',None)

            cf = atendimento.get('customFields',[])

            cf_motivo_de_contato = None
            cf_name = None

            for campo in cf:
                if campo.get("id") == "customField.motivo_contato_n1":
                    value = campo.get("value", [])
                    if isinstance(value, list) and value:  # garante que seja lista e não esteja vazia
                        cf_name = value[0].get("name")
                        cf_motivo_de_contato = value[0].get("levelPath")  # pega o primeiro item da lista
                        
                        break
       

            registro = {
                "chat_id": chat_id,
                "data_ultima_interacao":updated_at,
                "contact_id": contact_id,
                "contact_name": contact_name,
                "contact_email": contact_email,
                "organization_number": organization_number,
                "organization_name": organization_name,
                "org_cf_topmrr_atritado":org_cf_topmrr,
                "org_cf_tipo_uso_pri":org_cf_tipo_uso_pri,
                "org_cf_tipo_uso_sec":org_cf_tipo_uso_sec,
                "org_cf_plano":org_cf_plano,
                "org_cf_mrr":org_cf_mrr,
                "codigo_do_plano":codigo_do_plano,
                "motivo_de_contato_name":cf_name,
                "cf_motivo_de_contato":cf_motivo_de_contato

            }

            fullcontacts.append(registro)

        except Exception as e:
            print(f"Erro ao processar contato {contact_id}: {e}")
            continue  # Continua com o próximo contato mesmo em caso de erro

    df_content = pd.DataFrame(fullcontacts)
    df_content.to_sql('rawdata_classificacoes', con=engine, if_exists='replace', index=False, schema= 'octadesk')



    # Trunca a tabela stg_classificacoes
    table_name = 'octadesk.stg_classificacoes'
    truncate_query = f"TRUNCATE TABLE {table_name}"
    cur.execute(truncate_query)
    psy_conn.commit()
    print(f"Tabela {table_name} truncada com sucesso")

    # Alimenta a tabela octadesk.stgchat
    with open(f"{sql_path}/StgInsereDados.sql", 'r', encoding='utf-8') as file:
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
    table_name = 'octadesk.classificacoes'
    with open(f"{sql_path}/InsereDados.sql", 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    with engine.connect() as conn:
        result = conn.execute(query_insercao)
        linhas_inseridas = result.rowcount
        total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
        conn.commit()
        print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Atualiza a tabela octadesk.chat
    with open(f"{sql_path}/AtualizaDados.sql", 'r', encoding='utf-8') as file:
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
notify_slack_success(f"{total_linhas_inseridas} linhas inseridas e {total_linhas_atualizadas} linhas atualizadas na tabela {table_name}.",total_linhas_inseridas,total_linhas_atualizadas, rotina)


data_hora = datetime.now()
print(f"Fim : {data_hora}")

connection.close()
engine.dispose()

