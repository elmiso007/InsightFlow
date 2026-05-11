import toml
import streamlit as st
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import psycopg2
import pandas as pd
from notifica import notifica_analista
import configparser
import os
from get_escala import get_escala

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

data_hora = datetime.now()
data_hora = data_hora.strftime("%Y-%m-%d %H:%M:%S")


try:
    #armazena o conteúdo do google planilhas que esta em formato json a um df.
    df = get_escala()

    #Converte o df que esta em json para um df do pandas para poder renomear as colunas.
    df = pd.DataFrame(df)

    #nome da tabela que receberá os dados crûs
    tabela = 'rawdata'
    schema = 'control_desk'

    #renomeação das colunas do df para facilitar a manipulação
    df= df.rename(columns={
        "Login": "login",
        "Matricula": "matricula",
        "Status":"status",
        "Equipe":"equipe",
        "Skill":"skill",
        "Função":"funcao",
        "Coordenador":"coordenador",
        "Horario":"horario",
        "Pausa1":"pausa1",
        "Almoço":"intervalo",
        "Pausa3":"pausa3",
        "Saida":"saida",
        "Obs":"observacoes",
        "ID Slack":'id_slack'}
    )

    #inicializa as listas usadas para quantificar registros inseridos e eatualizados
    inserted_rows = []
    update_rows = []

    #inserção do df renomeado ta natela e schema definidos. Insere dados crûs para realização do ETL
    df.to_sql(tabela, con=engine, if_exists='replace', index=False, schema= schema)


    tabela = 'control_desk.mapa_operacional'

    # Obter a data atual
    hoje = datetime.now()

    # Verificar se é o primeiro dia do mês
    if hoje.day == 1:

        print("Hoje é dia primeiro! Todos serão notificados!")

        #Começa inserindo os registros que não existem
        with open(r"C:\Users\lucas.abner\Desktop\Rotinas Python\Projeto Control\InsereDados.sql") as file:
            sql_script = text(file.read())

        # Executando o script SQL
        result = connection.execute(sql_script)
        contagem = result.rowcount
        connection.commit()
        print(f"{contagem} registros inseridos na tabela {tabela}.")


        with open(r"C:\Users\lucas.abner\Desktop\Rotinas Python\Projeto Control\AtualizaDados.sql") as file:
            sql_script = text(file.read())

        # Executando o script SQL
        result = connection.execute(sql_script)
        connection.commit()
        print(f"{contagem} registros atualizados na tabela {tabela}.")

        with open(r"C:\Users\lucas.abner\Desktop\Rotinas Python\Projeto Control\InativaDados.sql") as file:
            sql_script = text(file.read())
        
        result = connection.execute(sql_script)
        contagem_delets = result.rowcount
        connection.commit()
        print(f"{contagem_delets} registros inativados na tabela {tabela}.")

        time.sleep(3)


        # Carregar os dados da tabela
        query = "SELECT * FROM control_desk.mapa_operacional WHERE status in ('Ativo');"
        df_table = pd.read_sql_query(query, engine)

        for _, row in df_table.iterrows():  # Iterar sobre as linhas do DataFrame
            id_slack = row['id_slack']
            login = row['login']  # Substitua pelo nome de outros campos do SQL
            horario = row['horario']
            pausa1 = row['pausa1']
            intervalo = row['intervalo']
            pausa3 = row['pausa3']
            saida = row['saida']
            equipe = row['equipe']
            skill = row['skill']
            coordenador = row['coordenador']
            funcao = row['funcao']

            print(f"notificação enviada para {login}")

            log_message = f"{data_hora} - Notificação Enviada | ID Slack: {id_slack} | Login: {login}\n"

            # Abre o arquivo em modo append (adiciona ao final)
            with open("logfile.txt", "a") as log_file:
                log_file.write(log_message)
            
            # Chamar a função de notificação
            notifica_analista(login, horario, pausa1, intervalo, pausa3, saida, id_slack, funcao, equipe, coordenador, skill)

    else:
        print("Notificando apenas atualizações")
        with open(r"C:\Users\lucas.abner\Desktop\Rotinas Python\Projeto Control\InsereDados.sql") as file:
            sql_script = text(file.read())

        # Executando o script SQL
        result = connection.execute(sql_script)
        contagem = result.rowcount
        inserted_rows = result.mappings().all()  # Converte para dicionário
        connection.commit()

        contagem = len(inserted_rows)

        # Iterar sobre os registros inseridos
        for row in inserted_rows:
            id_slack = row.get('id_slack')
            login = row.get('login')  # Substitua pelo nome de outros campos do SQL
            horario = row.get('horario')
            pausa1 = row.get('pausa1') 
            intervalo = row.get('intervalo') 
            pausa3= row.get('pausa3')
            saida = row.get('saida') 
            id_slack = row.get('id_slack') 
            equipe = row.get('equipe')
            skill= row.get('skill') 
            coordenador = row.get('coordenador')
            funcao = row.get('funcao')

            print(f"Registro inserido - ID Slack: {id_slack}, Login: {login}")

            log_message = f"{data_hora} - Registro Inserido | ID Slack: {id_slack} | Login: {login}\n"

            # Abre o arquivo em modo append (adiciona ao final)
            with open("logfile.txt", "a") as log_file:
                log_file.write(log_message)

            notifica_analista(login, horario, pausa1, intervalo, pausa3, saida, id_slack,funcao,equipe, coordenador, skill)

        print(f"{contagem} registros inseridos na tabela {tabela}.")
        


        with open(r"C:\Users\lucas.abner\Desktop\Rotinas Python\Projeto Control\AtualizaDados.sql") as file:
            sql_script = text(file.read())

        # Executando o script SQL
        result = connection.execute(sql_script)
        connection.commit()
        update_rows = result.mappings().all()  # Converte para dicionário
        contagem = len(update_rows)
        
        # Iterar sobre os registros atualizados
        for row in update_rows:
            id_slack = row.get('id_slack')
            login = row.get('login')  # Substitua pelo nome de outros campos do SQL
            horario = row.get('horario')
            pausa1 = row.get('pausa1') 
            intervalo = row.get('intervalo') 
            pausa3= row.get('pausa3')
            saida = row.get('saida') 
            id_slack = row.get('id_slack') 
            equipe = row.get('equipe')
            skill= row.get('skill') 
            coordenador = row.get('coordenador')
            funcao = row.get('funcao')

            log_message = f"{data_hora} - Registro Atualizado | ID Slack: {id_slack} | Login: {login}\n"

            # Abre o arquivo em modo append (adiciona ao final)
            with open("logfile.txt", "a") as log_file:
                log_file.write(log_message)

            print(f"Registro atualizado - ID Slack: {id_slack}, Login: {login}")
            notifica_analista(login, horario, pausa1, intervalo, pausa3, saida, id_slack,funcao,equipe,coordenador, skill)

        print(f"{contagem} registros atualizados na tabela {tabela}.")
        

except Exception as e:
    print(f"Erro ao processar as registros: {e}")

connection.close()
engine.dispose()
