import os
from sqlalchemy import create_engine, text
import pandas as pd
import configparser
import sys
import requests
import logging

rotina = "Alimenta kinghost.interacoes"


# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack

# Configurar logging
logging.basicConfig(filename='erro_execucao.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

try:

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

    # Lê o arquivo Excel e armazena em um data frame
    csv_file = 'C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\KingHost\\Interações\\IntegracaoLocawebXGEN.csv'
    df = pd.read_csv(csv_file, encoding='utf-8', delimiter=';')

    # Define o nome da tabela a ser criada e copia o df para o banco
    nova_tabela = 'rawdata'
    df.to_sql(nova_tabela, engine, index=False, if_exists='replace', schema='kinghost')
    print("Dados inseridos na tabela kinghost.rawdata")

    # Trunca a tabela chat.stginteracoes
    truncate_query = text("TRUNCATE TABLE kinghost.stginteracoes")
    connection.execute(truncate_query)
    connection.commit()
    print("Tabela kinghost.stginteracoes truncada com sucesso")

    # Alimenta a tabela chat.interacoesbacklog
    with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\KingHost\\Interações\\InsereStgInteracoes.sql', 'r', encoding='utf-8') as file:
        sql_script = text(file.read())

    # Executando o script SQL
    connection.execute(sql_script)
    connection.commit()
    print("Dados atualizados na tabela kinghost.stginteracoes")


    # Alimenta a tabela chat.interacoesbacklog
    with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\KingHost\\Interações\\InsereInteracoesBacklog.sql', 'r', encoding='utf-8') as file:
        sql_script = text(file.read())


    # Executando o script SQL
    connection.execute(sql_script)
    connection.commit()
    print("Dados inseridos na tabela kinghost.interacoesbacklog")


    # Teste de atualização de registros com base no protocolo+ IdSession
    # Atualiza a tabela chat.interacoesbacklog
    with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\KingHost\\Interações\\AtualizaInteracoesBacklog.sql', 'r', encoding='utf-8') as file:
        sql_script = text(file.read())

    # Executando o script SQL
    connection.execute(sql_script)
    connection.commit()
    print("Dados atualizados na tabela kinghost.interacoesbacklog")


    # Alimenta a tabela chat.interacoes
    with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\KingHost\\Interações\\InsereInteracoes.sql', 'r', encoding='utf-8') as file:
        sql_script = text(file.read())

    # Executando o script SQL
    connection.execute(sql_script)
    connection.commit()
    print("Dados atualizados na tabela kinghost.interacoes")

    # Atualiza a tabela chat.interacoes
    with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\KingHost\\Interações\\AtualizaInteracoes.sql', 'r', encoding='utf-8') as file:
        sql_script = text(file.read())

    # Executando o script SQL
    connection.execute(sql_script)
    connection.commit()
    print("Dados atualizados na tabela kinghost.interacoes")

except Exception as e:
    print("Ocorreu um erro:", e)
    logging.error(f"Ocorreu um erro: {e}")
    notify_slack(f"Erro na execução da {rotina}: {e}", rotina)

connection.close()
