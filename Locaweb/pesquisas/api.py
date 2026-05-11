import pandas as pd
from sqlalchemy import create_engine,text
from datetime import datetime,timedelta, timezone
import json
import configparser
import requests
import psycopg2
from function_logger import configurar_logger
from pathlib import Path
import configparser
import os
import sys

# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack, notify_slack_success  

# Configurar logger
logger = configurar_logger()

sql_path = Path(__file__).parent 


tabela = 'rawdata_pesquisas'
schema = 'lw_octadesk'  
rotina = "Locaweb (Carrega Pesquisas Chat)"

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

    # Set up PostgreSQL connection
    psy_conn = psycopg2.connect(
        dbname=database,
        user=uid,
        password=pwd,
        host=server
    )
    cur = psy_conn.cursor()
    logger.info("Banco conectado com sucesso")

except Exception as e:
    print("Ocorreu um erro:", e)
    logger.error(f"Ocorreu um erro de conexão: {e}")    



data_hora = datetime.now()
data = datetime.now().date()

hora = datetime.now().time()
hora_anterior = data_hora - timedelta(hours=2)
hora_anterior = hora_anterior.time()

print(f"Inicio : {data_hora}")

DDL_URL = "https://o203894-994.api003.octadesk.services"
TOKEN = "06b70186-121d-430b-98c9-405de0585920.863f975d-57f6-4727-b486-fe192b7c8ab4"

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



def get_pesquisas(DDL_URL,TOKEN,page):

    data = datetime.now().date()

    data_ontem = data - timedelta(days=1)
    data_amanha = data + timedelta(days=1)

    limit = 100

    endpoint = f"{DDL_URL}/survey/submissions?page={page}&limit={limit}?type=chat&isAnswered=true&createdBetween={data_ontem}&createdBetween={data_amanha}"

    #endpoint = f"{DDL_URL}/survey/submissions?page={page}&limit={limit}?type=chat&isAnswered=true&createdBetween=2025-08-25&createdBetween=2025-08-28"

    print(endpoint)

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
    

try:    
    # Variáveis para armazenar os registros gerados
    carga = []
    # Lista para acumular todos os dados de todas as páginas
    todas_pesquisas = []

    #Loop para percorrer todas as páginas da requisição
    for page in range(1, 50): 
        #Chama a função que realiza a autenticação
        pesquisas = get_pesquisas(DDL_URL, TOKEN, page)
        
        # Interrompe o loop se nenhum dado for retornado
        if not pesquisas:
            break  

        # Adiciona os dados desta página à lista completa
        todas_pesquisas.extend(pesquisas)

        # Processar cada atendimento (Dados de cabeçalho)
        for pesquisa in pesquisas:

            id_pesquisa = pesquisa.get('baseSurveyKey')
            type = pesquisa.get('type')
            room = pesquisa.get('room')
            is_answered = pesquisa.get('isAnswered')
            status = pesquisa.get('status')
            answers = pesquisa.get("answers", [])
            # Acessa os valores diretamente por índice (se existirem)
            p1_answers_type     = answers[0].get('type')     if len(answers) > 0 else None
            p1_answers_question = answers[0].get('question') if len(answers) > 0 else None
            p1_answers_answer   = answers[0].get('answer')   if len(answers) > 0 else None

            p2_answers_type     = answers[1].get('type')     if len(answers) > 1 else None
            p2_answers_question = answers[1].get('question') if len(answers) > 1 else None
            p2_answers_answer   = answers[1].get('answer')   if len(answers) > 1 else None

            p3_answers_type     = answers[2].get('type')     if len(answers) > 2 else None
            p3_answers_question = answers[2].get('question') if len(answers) > 2 else None
            p3_answers_answer   = answers[2].get('answer')   if len(answers) > 2 else None

            p4_answers_type     = answers[3].get('type')     if len(answers) > 3 else None
            p4_answers_question = answers[3].get('question') if len(answers) > 3 else None
            p4_answers_answer   = answers[3].get('answer')   if len(answers) > 3 else None

            data_criacao = pesquisa.get('createdAt')   
            data_criacao = ajusta_formato_data(data_criacao)           
            data_ultima_interacao = pesquisa.get('updatedAt')
            data_ultima_interacao = ajusta_formato_data(data_ultima_interacao)
            data_expiracao = pesquisa.get('expiresAt')
            data_expiracao = ajusta_formato_data(data_expiracao)
            version = pesquisa.get('version')
            subdomain = pesquisa.get('subDomain')
            code = pesquisa.get('code')


            registro = {
                "id_pesquisa": id_pesquisa,
                "tipo": type,
                "chat_id": room,
                "respondida": is_answered,
                "status": status,
                "p1_tipo": p1_answers_type,
                "p1_pergunta": p1_answers_question,
                "p1_nota": p1_answers_answer,
                "p2_tipo": p2_answers_type,
                "p2_pergunta": p2_answers_question,
                "p2_nota": p2_answers_answer,
                "p3_tipo": p3_answers_type,
                "p3_pergunta": p3_answers_question,
                "p3_nota": p3_answers_answer,
                "p4_tipo": p4_answers_type,
                "p4_pergunta": p4_answers_question,
                "p4_nota": p4_answers_answer,
                "data_criacao": data_criacao,
                "data_ultima_interacao":data_ultima_interacao,
                "data_expiracao":data_expiracao,
                "versao":version,
                "subdominio":subdomain,
                "code":code
            }

            carga.append(registro)

    # Salva o JSON completo com todos os dados de todas as páginas
    if todas_pesquisas:
        json_file = f'{sql_path}/pesquisas.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(todas_pesquisas, f, ensure_ascii=False, indent=4)
        print(f"JSON salvo com {len(todas_pesquisas)} registros de todas as páginas")
    
    df_content = pd.DataFrame(carga)
    
    
    linhas_inseridas = 0
    linhas_atualizadas = 0

    if df_content.empty:
        print("Nenhuma pesquisa retornada. DataFrame vazio. Interrompendo execução.")
        logger.warning(f"Nenhuma pesquisa retornada na rotina {rotina}.")
        # Notificação consolidada após o processo
        notify_slack_success(f"{linhas_inseridas} linhas inseridas na tabela {tabela}.:logo-locaweb_ico:",linhas_inseridas,linhas_atualizadas, rotina)
    else:
        df_content.to_sql(tabela, con=engine, if_exists='replace', index=False, schema=schema)
        print(f"Dados carregados na tabela: {tabela}...")

        # df_content.to_sql(tabela, con=engine, if_exists='replace', index=False, schema= schema)

        # print(f"Dados carregados na tabela: {tabela}...")

        with open(f'{sql_path}/insereDados.sql', 'r',encoding='utf-8') as file: 
            query_insercao = text(file.read())

        tabela = 'lw_octadesk.pesquisas'
        print(f"Inserindo dados na tabela {tabela} ...")
        result = connection.execute(query_insercao)
        total_linhas_inseridas = result.rowcount
        linhas_inseridas += total_linhas_inseridas
        connection.commit()
        logger.info(f' {linhas_inseridas} linhas inseridas na tabela {tabela}')
        notify_slack_success(f"{linhas_inseridas} linhas inseridas na tabela {tabela}. :logo-locaweb_ico:",linhas_inseridas,linhas_atualizadas, rotina)

except Exception as e:
    print("Ocorreu um erro:", e)
    logger.error(f'Ocorreu um erro: {e}')
    notify_slack(f"Erro na execução da {rotina}: {e}", rotina)


