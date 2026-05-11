import os
from sqlalchemy import create_engine, text
import pandas as pd
import configparser
from datetime import datetime
import shutil
import chardet
import sys
import requests
import logging
import time

rotina = "Kinghost - Chamados Nova Rotina"
marcador = "Kinghost/pentaho_chamados_backlog"
assunto = "Locaweb - Atendimentos KingHost"
destino = "C:/Users/lucas.abner/Desktop/Rotinas Python/KingHost/Chamados - Nova Rotina"


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
    pasta_origem = r'./'  # ajustar de acordo com o caminho na VM
    pasta_destino = r'C:\Users\lucas.abner\Desktop\Rotinas Python\KingHost\Chamados - Nova Rotina\legado4'

    # Extensão do arquivo que será consumido
    extensao_desejada = ".csv"

    # Listar arquivos na pasta
    arquivos = os.listdir(pasta_origem)

    # arquivos_ordenados = sorted(arquivos) #Ordena arquivos
    arquivos_ordenados = sorted(arquivos, key=lambda x: x.split('IntegracaoLocawebChamadosInteracoes')[-1])

    # Obter a data e hora atuais
    agora = datetime.now()

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

    # Variáveis para armazenar a contagem de linhas
    total_linhas_atualizadas = 0
    total_linhas_inseridas1 = 0
    total_linhas_inseridas2 = 0

    
    # Processamento dos arquivos
    for documento in arquivos_ordenados:
        caminho_arquivo = os.path.join(pasta_origem, documento)
        
        # Identifica o tipo de codificação do arquivo
        with open(caminho_arquivo, 'rb') as f:
            result = chardet.detect(f.read())
        encoding = result['encoding']

        if os.path.isfile(caminho_arquivo):
            if verificar_extensao_arquivo(documento, extensao_desejada):

                # Lê o arquivo e armazena em um dataframe
                df = pd.read_csv(caminho_arquivo, encoding='utf-8', delimiter='|', on_bad_lines='skip')

                #Ignorar as últimas duas colunas
                #df = df.iloc[:, :-2]

                # Define o nome da tabela a ser criada e copia o df para o banco
                nova_tabela = 'stgchamadosking'
                df.to_sql(nova_tabela, engine, index=False, if_exists='replace', schema='kinghost')
                print("Dados inseridos na tabela kinghost.stgchamadosking")

                # Alimenta a tabela kinghost.chamadosbacklogking
                with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\KingHost\\Chamados - Nova Rotina\\InsereChamadosbacklog.sql', 'r', encoding='utf-8') as file:
                    sql_script = text(file.read())

                # Executando o script SQL
                result = connection.execute(sql_script)
                total_linhas_inseridas1 = result.rowcount
                connection.commit()
                print(f"{total_linhas_inseridas1} linhas inseridas na tabela kinghost.chamadosbacklogking")

                
                # ataualiza a tabela kinghost.chamadosbacklog
                with open(r'C:\Users\lucas.abner\Desktop\Rotinas Python\KingHost\Chamados - Nova Rotina\UpdateBacklog.sql', 'r', encoding='utf-8') as file:
                    sql_script = text(file.read())

                # Executando o script SQL
                chamados_atualizados = connection.execute(sql_script)
                total_linhas_atualizadas = chamados_atualizados.rowcount
                connection.commit()
                print(f"{total_linhas_atualizadas} linhas inseridas na tabela kinghost.chamadosking")

                # Alimenta a tabela kinghost.chamados
                with open('C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\KingHost\\Chamados - Nova Rotina\\InsereChamados.sql', 'r', encoding='utf-8') as file:
                    sql_script = text(file.read())

                # Executando o script SQL
                chamados_encerrados = connection.execute(sql_script)
                total_linhas_inseridas2 = chamados_encerrados.rowcount
                connection.commit()
                print(f"{total_linhas_inseridas2} linhas inseridas na tabela kinghost.chamadosking")

               # Verifica se o caminho atual é um arquivo
                if os.path.isfile(os.path.join(pasta_origem, documento)):
                    try:
                        # Adiciona timestamp ao nome do arquivo
                        data_hora = datetime.now().strftime('%Y%m%d_%H%M%S')
                        nome_base, extensao = os.path.splitext(documento)
                        novo_nome_documento = f"{nome_base}_{data_hora}{extensao}"

                        # Move o arquivo para a pasta de destino com o novo nome
                        shutil.move(
                            os.path.join(pasta_origem, documento),
                            os.path.join(pasta_destino, novo_nome_documento)
                        )
                        print(f"Arquivo '{documento}' movido para '{pasta_destino}' como '{novo_nome_documento}'")
                    except Exception as e:
                        # Verifica se o erro é o PermissionError com Errno 13
                        if isinstance(e, PermissionError) and e.errno == 13:
                            print(f"Permissão negada ao mover o arquivo '{documento}'. Ignorando o erro.")
                        else:
                            print(f"Ocorreu um erro ao mover o arquivo '{documento}': {e}")
                else:
                    print(f"O arquivo '{documento}' não existe.")
except Exception as e:
    print("Ocorreu um erro:", e)
    logging.error(f"Ocorreu um erro: {e}")
    
    # Verifica se o erro é o PermissionError com Errno 13 antes de enviar para o Slack
    if isinstance(e, PermissionError) and e.errno == 13:
        print("Erro de permissão ao tentar acessar a pasta, mas ignorado.")
    else:
        notify_slack(f"Erro na execução da {rotina}: {e}", rotina)

    # Notificação consolidada após a execução de ambos os processos
    notify_slack_success(f"{total_linhas_inseridas1} linhas inseridas na tabela kinghost.chamadosbacklogking e {total_linhas_inseridas2} linhas inseridas na tabela kinghost.chamadosking.", total_linhas_inseridas1, 0, rotina)


connection.close()
