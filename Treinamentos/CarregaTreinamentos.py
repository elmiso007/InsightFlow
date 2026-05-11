import os
from sqlalchemy import create_engine, text
import pandas as pd
import configparser
import chardet
from datetime import datetime
import requests
import logging
import shutil

rotina = "Alimenta Tabela de Treinamentos"


# Adiciona o caminho três diretórios acima ao Python Path
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
#from notifica import notify_slack

# Configurar logging
logging.basicConfig(filename='erro_execucao.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')


try:

    # Obter o caminho absoluto para o arquivo config.ini
    # Tenta pasta de origem especificada, senão usa caminho relativo
    possible_paths = [
        r'C:\Users\lucas.abner\Desktop\Rotinas Python\config.ini',
        os.path.join(os.path.dirname(__file__), '..', '..', 'config.ini'),
        'config.ini'
    ]
    
    config_file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            config_file_path = path
            break
    
    if not config_file_path:
        raise FileNotFoundError(f"config.ini não encontrado em nenhum dos caminhos: {possible_paths}")

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

    # Pastas de origem e destino do arquivo csv
    pasta_origem = r'.\\'  # ajustar de acordo com o caminho na VM
    pasta_destino = r'.\\legado'  # ajustar de acordo com o caminho na VM

    # Extensão do arquivo que será consumido
    extensao_desejada = ".csv"

    # Listar arquivos na pasta
    arquivos = os.listdir(pasta_origem)

    # arquivos_ordenados = sorted(arquivos) #Ordena arquivos
    arquivos_ordenados = sorted(arquivos, key=lambda x: x.split('treinamentos')[-1])

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


    # Lê o arquivo CSV e armazena em um data frame
    # Tenta encontrar o arquivo de forma relativa ou em locais conhecidos
    possible_csv_paths = [
        r'C:\Users\lucas.abner\Desktop\Rotinas Python\Treinamentos\treinamentos  - Respostas ao formulário 1.csv',
        os.path.join(pasta_origem, 'treinamentos  - Respostas ao formulário 1.csv')
    ]
    
    csv_file = None
    for path in possible_csv_paths:
        if os.path.exists(path):
            csv_file = path
            break
    
    if not csv_file:
        raise FileNotFoundError(f"Arquivo CSV não encontrado em nenhum dos caminhos: {possible_csv_paths}")

    #Identifica o tipo de codificação do arquivo
    with open(csv_file, 'rb') as f:
        result = chardet.detect(f.read())
    encoding = result['encoding']

    # Processamento dos arquivos
    for documento in arquivos_ordenados:
        caminho_arquivo = os.path.join(pasta_origem, documento)
        if os.path.isfile(caminho_arquivo):
            if verificar_extensao_arquivo(documento, extensao_desejada):
                try:
                    # Ler o arquivo CSV para um DataFrame
                    df = pd.read_csv(caminho_arquivo, encoding=encoding, delimiter=';')
                    
                    # Validar colunas obrigatórias
                    colunas_obrigatorias = ['id', 'Carimbo de data/hora', 'Nome do Colaborador']
                    colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
                    if colunas_faltantes:
                        logging.warning(f"Arquivo '{documento}' faltam colunas: {colunas_faltantes}")
                        continue

                    # Convertendo coluna por coluna para string
                    for coluna in df.columns:
                        df[coluna] = df[coluna].astype(str)

                    # Renomear as colunas
                    renomeacoes = {
                        'Carimbo de data/hora':'data_hora_preenchimento',
                        'Pontuação':'pontuacao',
                        'id':'id',
                        'Nome do Colaborador': 'nome_contratado',
                        'Login de Rede':'login_analista',
                        'Matricula': 'matricula',
                        'Data de Admissão': 'data_admissao',
                        'Cargo': 'cargo',
                        'Time': 'time',
                        'Data do Inicio do Treinamento ': 'data_inicio_treinamento',                    
                        'Nome do Treinador': 'nome_do_instrutor',  
                        'Tipo de Treinamento': 'tipo_de_treinamento',
                        'Turma':'turma',
                        'Categoria do Treinamento':'categoria',
                        'Data de Inicio na Operação': 'data_inicio_operacao'                  
                    }
                    df = df.rename(columns=renomeacoes)

                    # Adicionar colunas de 'auditoria' com a data e hora atuais e data de modificação
                    df['fonte_de_dados'] = str('Formulário de Treinamentos')
                    
                    # Converter id para int, tratando valores inválidos
                    try:
                        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
                    except Exception as e:
                        logging.error(f"Erro ao converter coluna 'id' no arquivo '{documento}': {e}")
                        continue

                

                    colunas_de_data = ['data_admissao','data_inicio_treinamento','data_inicio_operacao']

                    for coluna in colunas_de_data:
                        # Converter para o formato YYYY-MM-DD, tratando formatos variados
                        try:
                            # Tenta primeiro com formato específico, depois com inferência
                            df[coluna] = pd.to_datetime(df[coluna], format='%d/%m/%Y', errors='coerce').dt.strftime('%Y-%m-%d')
                        except Exception as e:
                            # Se falhar, tenta inferir o formato
                            try:
                                df[coluna] = pd.to_datetime(df[coluna], format='mixed', dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
                            except Exception as e2:
                                logging.warning(f"Erro ao converter coluna '{coluna}' no arquivo '{documento}': {e2}")
                                # Deixa como está se não conseguir converter

            
                    # Define o nome da tabela a ser criada e copia o df para o banco
                    nova_tabela = 'stgtreinamentos'
                    df.to_sql(nova_tabela, engine, index=False, if_exists='replace', schema='treinamentos')
                        
                    print("Dados inseridos na tabela treinamentos.stgtreinamentos")
                    logging.info(f"Arquivo '{documento}' processado com sucesso")

                    # Move o arquivo para a pasta de destino
                    shutil.move(os.path.join(pasta_origem, documento), os.path.join(pasta_destino, documento))
                    print(f"Arquivo '{documento}' movido para '{pasta_destino}'.")
                    
                except Exception as e:
                    print(f"Erro ao processar arquivo '{documento}': {e}")
                    logging.error(f"Erro ao processar arquivo '{documento}': {e}")

                

    

except Exception as e:
    print("Ocorreu um erro na execução geral:", e)
    logging.error(f"Ocorreu um erro na execução geral: {e}")
    #notify_slack(f"Erro na execução da {rotina}: {e}", rotina)
finally:
    try:
        connection.close()
    except:
        pass
