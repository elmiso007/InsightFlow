import pandas as pd
from sqlalchemy import create_engine,text
from datetime import datetime,timedelta, timezone
import json
import configparser
import requests
import psycopg2
from function_logger import configurar_logger
from pathlib import Path
import os


# Configurar logger
logger = configurar_logger()

# Obter o caminho absoluto para o arquivo config.ini
config_folder = r'C:\Users\lucas.abner\Desktop\Rotinas Python'
config_file_path = os.path.join(config_folder, 'config.ini')

# Ler as configurações do arquivo config.ini
config = configparser.ConfigParser()
config.read(config_file_path)

try:
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
    logger.info("Banco conectado com sucesso")

except Exception as e:
    print("Ocorreu um erro:", e)
    logger.error(f"Ocorreu um erro de conexão: {e}")    



data_hora = datetime.now()
data = datetime.now().date()
hora = datetime.now().time()
hora_anterior = data_hora - timedelta(hours=1)
hora_anterior = hora_anterior.time()

print(f"Inicio : {data_hora}")

DDL_URL = "https://o203894-994.api003.octadesk.services"
TOKEN = "06b70186-121d-430b-98c9-405de0585920.863f975d-57f6-4727-b486-fe192b7c8ab4"

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


def get_message(DDL_URL,TOKEN,ID):
    
    limit = 100

    endpoint = f"{DDL_URL}/chat/{ID}/messages?limit={limit}"

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
    

query = f"SELECT id , data_ultima_interacao FROM lw_octadesk.chat WHERE data_ultima_interacao >= '{data} {hora_anterior}'"
df = pd.read_sql_query(query,connection)

carga = []

for _, row in df.iterrows():

    atendimento_id = row['id']
    print(f"atendimento: {atendimento_id}")
    mensagens_json = get_message(DDL_URL, TOKEN, atendimento_id)

    registro = {
        "id": atendimento_id,
        "data_ultima_interacao": row['data_ultima_interacao'],
        "mensagens": json.dumps(mensagens_json)  # <-- conversão aqui
    }

    carga.append(registro)

df_content = pd.DataFrame(carga)

#df_content.to_csv('teste.csv',index=False)

df_content.to_sql('rawdata_messages',con=engine,if_exists='replace',index=False,schema='lw_octadesk')

sql_path = Path(__file__).parent 

try:
    with open(f'{sql_path}/insereDadosMensagens.sql', 'r',encoding='utf-8') as file: 
        query_insercao = text(file.read())

    tabela = 'lw_octadesk.mensagens'
    linhas_inseridas = 0
    result = connection.execute(query_insercao)
    total_linhas_inseridas = result.rowcount
    linhas_inseridas += total_linhas_inseridas
    connection.commit()
    logger.info(f' {linhas_inseridas} linhas inseridas na tabela {tabela}')
except Exception as e:
    print("Ocorreu um erro:", e)
    logger.error(f'Ocorreu um erro: {e}')

try:
    with open(f'{sql_path}/AtualizaDados.sql', 'r',encoding='utf-8') as file: 
        query_insercao = text(file.read())

    tabela = 'lw_octadesk.mensagens'
    linhas_inseridas = 0
    result = connection.execute(query_insercao)
    total_linhas_inseridas = result.rowcount
    linhas_inseridas += total_linhas_inseridas
    connection.commit()
    logger.info(f' {linhas_inseridas} linhas atualizadas na tabela {tabela}')
except Exception as e:
    print("Ocorreu um erro:", e)
    logger.error(f'Ocorreu um erro: {e}')

connection.close()
engine.dispose

data_hora = datetime.now()

print(f"FIM : {data_hora}")