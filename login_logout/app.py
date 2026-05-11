import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime,timedelta,date
import logging
import psycopg2
import numpy as np
import os

# === LOGGING === Grava em arquivo e também exibe no console
log_file_path = r'C:\Users\emerson.ramos\Desktop\projetos\Login_Logout\logs.log'
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Set up PostgreSQL connection
try:
    server = '10.30.138.28'
    database = 'report_requesttracker'
    uid = 'a_report'
    pwd = 'Eequ8ohc'
    engine_conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
    engine = create_engine(engine_conn_string)
    connection = engine.connect()
    logging.info("Conexão com o banco de dados estabelecida com sucesso.")
except Exception as e:
    logging.error(f"Erro ao conectar ao banco de dados: {e}")
    exit(1)

# === LEITURA DO EXCEL ===
try:
    df = pd.read_excel(r'C:\Users\emerson.ramos\Desktop\projetos\Login_Logout\login-logout-report.xlsx', header=1) 
    df =df.dropna(how="all")
    logging.info("Arquivo Excel lido com sucesso.")
except FileNotFoundError:
    logging.error(f"Arquivo '{r'C:\Users\emerson.ramos\Desktop\projetos\Login_Logout\login-logout-report.xlsx'}' não encontrado.")
    exit(1)
except Exception as e:
    logging.error(f"Erro ao ler o arquivo Excel: {e}")
    exit(1)

# === TRANSFORMAÇÃO ===
def serializar_dataframe(df):
    try:
        df.columns = [col.strip() for col in df.columns]

        mapeamento_colunas = {
            "Nome":"analista",
            "Login":"login",
            "Data de Login":"data_login",
            "Data de Logout":"data_logout",
            "Tempo em Pausa":"tempo_em_pausa",
            "Tempo Logado":"tempo_logado"
        }

        # Renomear colunas
        df.rename(columns=mapeamento_colunas, inplace=True)

        # Remover colunas não mapeadas (como 'Apelido' ou outras extras)
        #colunas_esperadas = list(mapeamento_colunas.values())
        #df = df[colunas_esperadas]

        
        logging.info("Transformações aplicadas com sucesso.")
        return df

    except Exception as e:
        logging.error(f"Erro durante a transformação dos dados: {e}")
        exit(1)

        # Reordenar colunas
        df = df[todas_colunas]

        return df
    
# === CARGA STAGING ===
df_serializado = serializar_dataframe(df)

df_serializado['tempo_em_pausa'] = pd.to_datetime(df_serializado['tempo_em_pausa'], format='%H:%M:%S', errors='coerce').dt.time
df_serializado['tempo_logado'] = pd.to_datetime(df_serializado['tempo_logado'], format='%H:%M:%S', errors='coerce').dt.time

print(df_serializado.head())

total_linhas_inseridas = 0

try:
    TABELA_STG='stg_ch_login_logout_chat'
    df_serializado.to_sql(TABELA_STG, con=engine,if_exists='replace', index=False, schema='public')
    logging.info(f"Dados inseridos na tabela staging '{TABELA_STG}'.")
except Exception as e:
    logging.error(f"Erro ao inserir na tabela STG: {e}")
    exit(1)

try:    
      
    with open(r'C:\Users\emerson.ramos\Desktop\projetos\Login_Logout\INSERT.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    result = connection.execute(query_insercao)
    linhas_inseridas = result.rowcount
    total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
    connection.commit()
    logging.info(f"{total_linhas_inseridas} Linhas inseridos na tabela ch_login_logout_chat.")

except Exception as e:
    logging.error(f"Erro ao inserir na tabela ch_login_logout_chat: {e}")
    exit(1)
    

connection.close()
engine.dispose