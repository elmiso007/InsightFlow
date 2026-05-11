import os
from sqlalchemy import create_engine, text
import pandas as pd
import configparser
import chardet
import sys
import logging
import time

rotina = "Kinghost - Chamados"
marcador = "Kinghost/pentaho_chamados"
assunto = "Atendimentos KingHost (Chamados)"
destino = "C:/Users/lucas.abner/Desktop/Rotinas Python/KingHost/Chamados"

# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack
from baixaEmail import baixar_anexo_gmail


# Configurar logging
logging.basicConfig(filename='erro_execucao.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

try:
    baixar_anexo_gmail(marcador,assunto,destino)

    time.sleep(10)

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
    csv_file = 'C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\KingHost\\Chamados\\IntegracaoLocawebChamados.csv'

    #Identifica o tipo de codificação do arquivo
    with open(csv_file, 'rb') as f:
        result = chardet.detect(f.read())
    encoding = result['encoding']

    #Lê o arquivo e armazena em um dataframe
    df = pd.read_csv(csv_file, encoding=encoding, delimiter=';')

    # Define o nome da tabela a ser criada e copia o df para o banco
    nova_tabela = 'stgchamados'
    df.to_sql(nova_tabela, engine, index=False, if_exists='replace', schema='kinghost')
    print("Dados inseridos na tabela kinghost.stgchamados")


    # Alimenta a tabela kinghost.chamados
    with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\KingHost\\Chamados\\InsereChamadosbacklog.sql', 'r', encoding='utf-8') as file:
        sql_script = text(file.read())

    # Executando o script SQL
    connection.execute(sql_script)
    connection.commit()
    print("Dados inseridos na tabela kinghost.chamadosbacklog")


    # Alimenta a tabela kinghost.chamados
    with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\KingHost\\Chamados\\AtualizaRegistros.sql', 'r', encoding='utf-8') as file:
        sql_script = text(file.read())

    # Executando o script SQL
    connection.execute(sql_script)
    connection.commit()
    print("Dados atualizados na tabela kinghost.chamados")


    # Alimenta a tabela kinghost.chamados
    with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\KingHost\\Chamados\\InsereChamados.sql', 'r', encoding='utf-8') as file:
        sql_script = text(file.read())

    # Executando o script SQL
    connection.execute(sql_script)
    connection.commit()
    print("Dados inseridos na tabela kinghost.chamados")

except Exception as e:
    print("Ocorreu um erro:", e)
    logging.error(f"Ocorreu um erro: {e}")
    notify_slack(f"Erro na execução da {rotina}: {e}", rotina)



connection.close()
