import pandas as pd
from sqlalchemy import create_engine, text
import psycopg2
import numpy as np

# Set up PostgreSQL connection
server = '10.30.138.28'
database = 'report_requesttracker'
uid = 'a_report'
pwd = 'Eequ8ohc'
engine_conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
engine = create_engine(engine_conn_string)
connection = engine.connect()

try:

    df = pd.read_excel(r'C:\Users\emerson.ramos\Desktop\projetos\Octadesk_ticket\Ticket Criados.xlsx')

    def serializar_dataframe(df):
        mapeamento_colunas = {
            "Número do ticket":"ticket",
            "Data de entrada":"data_entrada",
            "Data da resolução":"data_resolucao",
            "Título do ticket":"titulo_ticket",
            "Usuário criador do ticket":"usuario_criador_ticket",
            "Status do ticket":"status",
            "Grupo responsável do ticket":"grupo_responsavel",
            "Responsável do ticket":"responsavel_ticket",
            "Tags do ticket":"tags_ticket",
            "Total de interações":"total_de_interacoes"
        }

        # Renomear colunas
        df = df.rename(columns=mapeamento_colunas)

        #print (df.columns)

        return df

    df_serializado = serializar_dataframe(df)

    print(df_serializado.head())
    df_serializado['tags_ticket'] = df_serializado['tags_ticket'].replace('-', np.nan)
        
    df_serializado.to_sql('stg_ticketscriados', con=engine,if_exists='replace', index=False, schema='octadesk') # Sobe dados brutos para o banco

    total_linhas_inseridas = 0

    with open(r'C:\Users\emerson.ramos\Desktop\projetos\Octadesk_ticket\INSERT.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    result = connection.execute(query_insercao)
    linhas_inseridas = result.rowcount
    total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
    connection.commit()
    print(f"{total_linhas_inseridas} linhas inseridas na tabela octadesk.sticket.")

    total_linhas_atualizadas = 0

    with open(r'C:\Users\emerson.ramos\Desktop\projetos\Octadesk_ticket\update.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    result = connection.execute(query_insercao)
    linhas_inseridas = result.rowcount
    total_linhas_atualizadas += linhas_inseridas  # Contagem de linhas inseridas
    connection.commit()
    print(f"{total_linhas_atualizadas} linhas atualizadas na tabela octadesk.sticket.")


    
except Exception as e:
    print("Ocorreu um erro:", e)

connection.close()
engine.dispose