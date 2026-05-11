import pandas as pd
from sqlalchemy import create_engine,text
from datetime import datetime,timedelta, timezone
import json
import configparser
import requests
import sys
import os

# Obter o caminho absoluto para o arquivo config.ini
config_folder = r'C:\Users\lucas.abner\Desktop\Rotinas Python'
config_file_path = os.path.join(config_folder, 'config.ini')

# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..')))
from notifica import notify_slack, notify_slack_success
from function_logger import configurar_logger


rotina = 'Carrega Mensagens Chat Octadesk'
arquivo_logs = r'C:\Users\lucas.abner\Desktop\Rotinas Python\Octadesk\octadesk-mensagens\logs.log'

# Configurar logger
logger = configurar_logger(nome_log=rotina , arquivo_log = arquivo_logs)

try:
    
    # Ler as configurações do arquivo config.ini
    config = configparser.ConfigParser()
    config.read(config_file_path)

    # Set up PostgreSQL connection
    server = config['database']['server']
    database = config['database']['database']
    uid = config['database']['uid']
    pwd = config['database']['pwd']
    pg_conn_string = f'DRIVER={{PostgreSQL Unicode}};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}'
    conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
    engine = create_engine(conn_string)
    connection = engine.connect()
    logger.info("Conexao com o Banco estabelecida!")

except Exception as e:
    print("Ocorreu um erro:", e)
    logger.error(f"Ocorreu um erro: {e}")
    notify_slack(f"Erro na execução da {rotina}: {e}", rotina)    



data_hora = datetime.now()
data = datetime.now().date()
hora = datetime.now().time()
hora_anterior = data_hora - timedelta(hours=2)
hora_anterior = hora_anterior.time()

print(f"Inicio : {data_hora}")

DDL_URL = "https://help.apibeta.octadesk.services"
TOKEN = "75657565-0f17-4044-ab0b-3268d2052a6b.70be86ec-b219-41ae-a16c-8d73350d3618"

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
    

query = f"SELECT id , data_ultima_interacao FROM octadesk.chat WHERE data_ultima_interacao >= '{data} {hora_anterior}'"

df = pd.read_sql_query(query,connection)

carga = []

for _, row in df.iterrows():
    atendimento_id = row['id']
    mensagens_json = get_message(DDL_URL, TOKEN, atendimento_id)
    print(f"Coletando as mensagens do atendimento : {atendimento_id}")

    registro = {
        "id": atendimento_id,
        "data_ultima_interacao": row['data_ultima_interacao'],
        "mensagens": json.dumps(mensagens_json)  # <-- conversão aqui
    }

    carga.append(registro)

if not carga:
    print("Carga vazia. Pipeline encerrado antes dos inserts.")
else:
    df_content = pd.DataFrame(carga)


    df_content.to_sql('rawdata_messages',con=engine,if_exists='replace',index=False,schema='octadesk')


    try:
        with open(r'C:\Users\lucas.abner\Desktop\Rotinas Python\Octadesk\octadesk-mensagens\insereDadosMensagens.sql', 'r',encoding='utf-8') as file: 
            query_insercao = text(file.read())

        tabela = 'octadesk.mensagens'
        linhas_inseridas = 0
        result = connection.execute(query_insercao)
        total_linhas_inseridas = result.rowcount
        linhas_inseridas += total_linhas_inseridas
        connection.commit()
        logger.info(f' {linhas_inseridas} linhas inseridas na tabela {tabela}')
    except Exception as e:
        print("Ocorreu um erro:", e)
        logger.error(f'Ocorreu um erro: {e}')
        notify_slack(f"Erro na execução da {rotina}: {e}", rotina)

    try:
        with open(r'C:\Users\lucas.abner\Desktop\Rotinas Python\Octadesk\octadesk-mensagens\AtualizaDados.sql', 'r',encoding='utf-8') as file: 
            query_insercao = text(file.read())

        tabela = 'octadesk.mensagens'
        linhas_inseridas = 0
        result = connection.execute(query_insercao)
        total_linhas_inseridas = result.rowcount
        linhas_inseridas += total_linhas_inseridas
        connection.commit()
        logger.info(f' {linhas_inseridas} linhas atualizadas na tabela {tabela}')

    except Exception as e:
        print("Ocorreu um erro:", e)
        logger.error(f'Ocorreu um erro: {e}')
        notify_slack(f"Erro na execução da {rotina}: {e}", rotina)

connection.close()
engine.dispose

data_hora = datetime.now()

print(f"FIM : {data_hora}")












    

