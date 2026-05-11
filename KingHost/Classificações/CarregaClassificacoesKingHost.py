import os
from sqlalchemy import create_engine, text
import pandas as pd
import configparser
import sys
import time
from pathlib import Path

sql_path = Path(__file__).parent 

marcador = "Kinghost/pentaho_Classificacoes"
assunto = "Atendimentos KingHost"
destino = "C:/Users/lucas.abner/Desktop/Rotinas Python/KingHost/Classificações"

# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from baixaEmail import baixar_anexo_gmail

baixar_anexo_gmail(marcador,assunto,destino)

time.sleep(10)

# Obter o caminho absoluto para o arquivo config.ini
config_folder = r'C:\Users\lucas.abner\Desktop\Rotinas Python'
config_file_path = os.path.join(config_folder, 'config.ini')

# Ler as configurações do arquivo config.ini
config = configparser.ConfigParser()
config.read(config_file_path)

# Set up PostgreSQL connection
server = '10.30.138.28'
database = 'report_requesttracker'
uid = 'a_report'
pwd = 'Eequ8ohc'
conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
engine = create_engine(conn_string)
connection = engine.connect()

# Lê o arquivo Excel e armazena em um data frame
csv_file = f'{sql_path}/IntegracaoLocawebHistoricos.csv'
df = pd.read_csv(csv_file, encoding='utf-8', delimiter=';')

# Define o nome da tabela a ser criada e copia o df para o banco
nova_tabela = 'rawdata'
df.to_sql(nova_tabela, engine, index=False, if_exists='replace', schema='kinghost')
print("Dados inseridos na tabela kinghost.rawdata")

# Trunca a tabela kinghost.stgclassificacoes
truncate_query = text("TRUNCATE TABLE kinghost.stgclassificacoes")
connection.execute(truncate_query)
connection.commit()
print("Tabela kinghost.stgclassificacoes truncada com sucesso")

# Alimenta a tabela kinghost.stgclassificacoes
with open(f'{sql_path}/InsereStgClassificacoes.sql', 'r', encoding='utf-8') as file:
    sql_script = text(file.read())

# Executando o script SQL
connection.execute(sql_script)
connection.commit()
print("Dados Inseridos na tabela kinghost.stgclassificacoes")


# Alimenta a tabela kinghost.classificacoes
with open(f'{sql_path}/InsereClassificacoes.sql', 'r', encoding='utf-8') as file:
    sql_script = text(file.read())


# Executando o script SQL
connection.execute(sql_script)
connection.commit()
print("Dados inseridos na tabela kinghost.classificacoes")


# Teste de atualização de registros com base no protocolo+ IdSession
# Atualiza a tabela kinghost.classificacoes
with open(f'{sql_path}/AtualizaClassificacoes.sql', 'r', encoding='utf-8') as file:
    sql_script = text(file.read())

# Executando o script SQL
connection.execute(sql_script)
connection.commit()
print("Dados atualizados na tabela kinghost.classificacoes")

connection.close()
