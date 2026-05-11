import os
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
import pyodbc
import datetime
import shutil
import sys
import requests
import logging
import time

rotina = "Kinghost D-1"
marcador = "Kinghost/xgen_d-1"
assunto = "D-1-KingHost"
destino = "C:/Users/lucas.abner/Desktop/Rotinas Python/KingHost/Chat"


# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack, notify_slack_success  
from baixaEmail import baixar_anexo_gmail

# Configurar logging
logging.basicConfig(filename='erro_execucao.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

try:
    baixar_anexo_gmail(marcador,assunto,destino)

    time.sleep(10)

    # Pastas de origem e destino do arquivo csv
    pasta_origem = r'.\\'  # ajustar de acordo com o caminho na VM
    pasta_destino = r'.\\legado'  # ajustar de acordo com o caminho na VM

    # Extensão do arquivo que será consumido
    extensao_desejada = ".csv"

    # Listar arquivos na pasta
    arquivos = os.listdir(pasta_origem)

    # arquivos_ordenados = sorted(arquivos) #Ordena arquivos
    arquivos_ordenados = sorted(arquivos, key=lambda x: x.split('Relatorio_Detalhado_Interações')[-1])

    # Obter a data e hora atuais
    agora = datetime.datetime.now()

    # Formatar a data e hora no formato desejado (exemplo: DD/MM/AAAA HH:MM:SS)
    data_hora_formatada = agora.strftime("%d/%m/%Y %H:%M:%S")


    # Função para verificar a extensão do arquivo
    def verificar_extensao_arquivo(caminho_do_arquivo, extensao_desejada):
        if os.path.isfile(caminho_do_arquivo):
            nome_do_arquivo, extensao = os.path.splitext(caminho_do_arquivo)
            if extensao == extensao_desejada:
                return True
        return False


    

    # Verifica se a pasta de destino existe, senão a cria
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)

    # Conexões
    server = '10.30.138.28'
    database = 'report_requesttracker'
    uid = 'a_report'
    pwd = 'Eequ8ohc'
    engine_conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
    engine = create_engine(engine_conn_string)
    connection = engine.connect()
    driver = '{PostgreSQL Unicode(x64)}'
    conn_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}'
    conn = pyodbc.connect(conn_string)

    # Set up PostgreSQL connection
    psy_conn = psycopg2.connect(
        dbname="report_requesttracker",
        user="a_report",
        password="Eequ8ohc",
        host="10.30.138.28"
    )
    cur = psy_conn.cursor()

    # Processamento dos arquivos
    for documento in arquivos_ordenados:
        try:
            caminho_arquivo = os.path.join(pasta_origem, documento)
            if os.path.isfile(caminho_arquivo):
                if verificar_extensao_arquivo(documento, extensao_desejada):

                    # Ler o arquivo CSV para um DataFrame
                    df = pd.read_csv(caminho_arquivo, encoding='utf-8', delimiter=';')

                    # Convertendo coluna por coluna para string
                    for coluna in df.columns:
                        df[coluna] = df[coluna].astype(str)

                    # Renomear as colunas
                    renomeacoes = {
                        'Árvore de Classificação': 'Arvore_de_classificacao',
                        'Fluxo Atualização Cadastral': 'Fluxo_Atualizacao_Cadastral',
                        'Fldaux1.1': 'fldaux1_1',
                        'Fldaux2.1': 'fldaux2_1',
                        'Fldaux3.1': 'fldaux3_1',
                        'Fldaux4.1': 'fldaux4_1',
                        'Fldaux5.1': 'fldaux5_1',
                        'Fldaux6.1': 'fldaux6_1',
                        'Fldaux7.1': 'fldaux7_1',
                        'Fldaux8.1': 'fldaux8_1',
                        'Número Entrada WhatsApp':'numeroentradawhatsapp',
                        'StartedInteraction': 'DateStartedInteraction',
                        'DivertedInteraction':'datedivertedinteraction',
                        'AnsweredInteraction':'dateansweredinteraction',
                        'ReleasedInteraction':'datereleasedinteraction',
                        'ReferenceDate':'dateprocess',
                        'ReportGeneratedAt':'DateFileCreation',
                        'Protocol':'protocolo',
                        'Status':'steptype',
                        'StatusName':'steptypename',
                        'StartedSession':'datetimestarted',
                        'ReleasedSession':'datereleased',
                        'SessionId':'sessionid',
                        'StartedInteraction.1': 'DateStartedInteraction_1',
                        
                    }
                    df = df.rename(columns=renomeacoes)

                    # Trunca a tabela kinghost.rawdata
                    table_name = 'teste.rawdata'
                    truncate_query = f"TRUNCATE TABLE {table_name}"
                    cur.execute(truncate_query)
                    psy_conn.commit()
                    print("Tabela teste.rawdata truncada com sucesso")

                    # Inserir dados na tabela kinghost.rawdata
                    for index, row in df.iterrows():
                        insert_query = f"INSERT INTO {table_name} ({', '.join(df.columns)}) VALUES ({', '.join(['%s']*len(df.columns))})"
                        cur.execute(insert_query, tuple(row))
                        psy_conn.commit()
                    print("Dados inseridos na tabela kinghost.rawdata")

                    # Verifica se o caminho atual é um arquivo
                    move_arquivo = f" Arquivo '{documento}' movido para '{pasta_destino}'.\n"
                    if os.path.isfile(os.path.join(pasta_origem, documento)):
                        # Move o arquivo para a pasta de destino
                        shutil.move(os.path.join(pasta_origem, documento), os.path.join(pasta_destino, documento))
                        print(move_arquivo)

                    # Trunca a tabela kinghost.stginteracoes
                    table_name = 'teste.stginteracoes'
                    truncate_query = f"TRUNCATE TABLE {table_name}"
                    cur.execute(truncate_query)
                    psy_conn.commit()
                    print("Tabela teste.stginteracoes truncada com sucesso")

                    

                    # Alimenta a tabela kinghost.stginteracoes
                    with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\Kinghost\\Chat\\InsereStgInteracoes.sql', 'r', encoding='utf-8') as file:
                        df_interacoes = text(file.read())

                    df = pd.read_sql_query(df_interacoes, engine)
                    df = df.astype(object)
                    df = df.where(pd.notna(df), None)
                    for index, row in df.iterrows():
                        insere_interacoes = f'''INSERT INTO teste.stginteracoes (protocolo, login_agente, fila, cliente, email, telefone_1,
                            telefone_2, navegador, data_inicio_interacao, data_desvio_interacao, data_resposta_interacao,
                            data_encerramento_interacao, duracao_atendimento, duracao_espera, status, quantidade_interacoes,
                            nivel1, nivel2, nivel3, nivel4, nivel5, p1, p2, p3, comentarios, comentarios_2, comentarios_3,
                            login_cliente, autorizacao_requisitada, autorizacao_aceita, autorizacao_erro, boleto, canal, ip,
                            data_processamento, data_criacao_do_arquivo, id_sessao, fonte_de_dados)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
                        cursor = conn.cursor()
                        cursor.execute(insere_interacoes, tuple(row))
                        conn.commit()
                    print(f"Dados inseridos na tabela {table_name}")

                    
                    # Atualiza a tabela kinghost.chat_backlog
                    with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\Kinghost\\Chat\\AtualizaInteracoes.sql', 'r', encoding='utf-8') as file:
                        sql_script = text(file.read())

                    # Executando o script SQL
                    connection.execute(sql_script)
                    connection.commit()
                    print("Dados atualizados na tabela kinghost.chat_backlog")

                    # Alimenta a tabela kinghost.chat_backlog
                    with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\Kinghost\\Chat\\InsereInteracoesBacklog.sql', 'r', encoding='utf-8') as file:
                        sql_script = text(file.read())

                    # Executando o script SQL
                    connection.execute(sql_script)
                    connection.commit()
                    print("Dados inseridos na tabela kinghost.chat_backlog")
                    

                    
        except Exception as e:
            print("Ocorreu um erro:", e)
            logging.error(f"Ocorreu um erro: {e}")
            notify_slack(f"Erro na execução da rotina {rotina}: {e}", rotina)

except Exception as e:
    print("Ocorreu um erro:", e)
    logging.error(f"Ocorreu um erro: {e}")
    notify_slack(f"Erro na execução da {rotina}: {e}", rotina)

# Fechar conexões
cur.close()
psy_conn.close()
conn.close()
