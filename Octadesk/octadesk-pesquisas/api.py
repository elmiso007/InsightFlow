import pandas as pd
from sqlalchemy import create_engine,text
from datetime import datetime,timedelta, timezone
import json
import sys
import requests
import psycopg2
from function_logger import configurar_logger
from pathlib import Path
import os
import logging
import time


# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack, notify_slack_success  

def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)

def get_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Variavel de ambiente obrigatoria ausente: {name}")
    return value

# Caminhos e configuracoes
sql_path = Path(__file__).parent 
env_path = sql_path / ".env"
env_exists = env_path.exists()
load_env_file(env_path)

# Configurar logger
def parse_log_level(value: str):
    value = (value or "").strip().upper()
    return getattr(logging, value, logging.INFO)

log_level = parse_log_level(os.getenv("OCTADESK_LOG_LEVEL", "INFO"))
log_max_bytes = int(os.getenv("OCTADESK_LOG_MAX_BYTES", "5242880"))
log_backup_count = int(os.getenv("OCTADESK_LOG_BACKUP_COUNT", "5"))
logger = configurar_logger(
    nivel=log_level, max_bytes=log_max_bytes, backup_count=log_backup_count
)
if env_exists:
    logger.info(f".env carregado de {env_path}")
else:
    logger.warning(f"Arquivo .env nao encontrado em {env_path}")

tabela = 'rawdata_pesquisas'
schema = 'octadesk'  
rotina = "Octadesk (Carrega Pesquisas Chat)"

try:
    # Set up PostgreSQL connection
    server = get_env_var("OCTADESK_DB_HOST")
    database = get_env_var("OCTADESK_DB_NAME")
    uid = get_env_var("OCTADESK_DB_USER")
    pwd = get_env_var("OCTADESK_DB_PASSWORD")
    engine_conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
    engine = create_engine(engine_conn_string)
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
logger.info(f"Inicio da rotina {rotina}")
inicio_execucao = time.perf_counter()

DDL_URL = os.getenv("OCTADESK_API_BASE_URL", "https://help.apibeta.octadesk.services")
TOKEN = get_env_var("OCTADESK_API_TOKEN")

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

    data_ontem = data - timedelta(days=5)
    data_amanha = data + timedelta(days=1)
    limit = 100

    endpoint = f"{DDL_URL}/survey/submissions?page={page}&limit={limit}?type=chat&isAnswered=true&createdBetween={data_ontem}&createdBetween={data_amanha}"

    logger.info(f"Buscando pagina {page} - endpoint: {endpoint}")

    headers = {
        "accept": "application/json",
        "X-API-KEY": TOKEN
    }

    response = requests.get(endpoint, headers=headers)

    if response.status_code == 200:
        data = response.json()
        logger.info(f"Pagina {page} retornou {len(data)} registros")
        return data
    else:
        print(f"Falha na autenticação. Código de status: {response.status_code}")
        logger.warning(f"Falha na requisicao: status={response.status_code}")
        return None
    

try:    
    # Variáveis para armazenar os registros gerados
    carga = []
    # Lista para acumular todos os dados de todas as páginas
    todas_pesquisas = []

    #Loop para percorrer todas as páginas da requisição
    for page in range(1, 16): 
        #Chama a função que realiza a autenticação
        inicio_pagina = time.perf_counter()
        pesquisas = get_pesquisas(DDL_URL, TOKEN, page)
        logger.info(
            f"Tempo pagina {page}: {(time.perf_counter() - inicio_pagina):.2f}s"
        )
        
        # Interrompe o loop se nenhum dado for retornado
        if not pesquisas:
            logger.info("Nenhum dado retornado, encerrando paginacao")
            break  

        # Adiciona os dados desta página à lista completa
        todas_pesquisas.extend(pesquisas)

        # Processar cada atendimento (Dados de cabeçalho)
        for pesquisa in pesquisas:

            id_pesquisa = pesquisa.get('baseSurveyKey')
            type = pesquisa.get('type')
            room = pesquisa.get('room')
            ticket = pesquisa.get('ticket')
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
                "code":code,
                "ticket":ticket

            }
            carga.append(registro)
        
    # Salva o JSON completo com todos os dados de todas as páginas
    if todas_pesquisas:
        inicio_json = time.perf_counter()
        json_file = f'{sql_path}/pesquisas.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(todas_pesquisas, f, ensure_ascii=False, indent=4)
        print(f"JSON salvo com {len(todas_pesquisas)} registros de todas as páginas")
        logger.info(f"JSON salvo com {len(todas_pesquisas)} registros em {json_file}")
        logger.info(
            f"Tempo para salvar JSON: {(time.perf_counter() - inicio_json):.2f}s"
        )
    
    inicio_df = time.perf_counter()
    df_content = pd.DataFrame(carga)
    logger.info(f"DataFrame criado com {len(df_content)} linhas")
    logger.info(f"Tempo para montar DataFrame: {(time.perf_counter() - inicio_df):.2f}s")

    linhas_inseridas = 0
    linhas_atualizadas = 0

    if df_content.empty:
        print("Nenhuma pesquisa retornada. DataFrame vazio. Interrompendo execução.")
        logger.warning(f"Nenhuma pesquisa retornada na rotina {rotina}.")
        # Notificação consolidada após o processo
        notify_slack_success(f"{linhas_inseridas} linhas inseridas na tabela {tabela}.:octadesk:",linhas_inseridas,linhas_atualizadas, rotina)
    else:
        logger.info(f"Iniciando carga na tabela {schema}.{tabela}")
        inicio_carga = time.perf_counter()
        df_content.to_sql(tabela, con=engine, if_exists='replace', index=False, schema=schema)
        print(f"Dados carregados na tabela: {tabela}...")

        df_content.to_sql(tabela, con=engine, if_exists='replace', index=False, schema= schema)

        print(f"Dados carregados na tabela: {tabela}...")
        logger.info(
            f"Tempo de carga na staging: {(time.perf_counter() - inicio_carga):.2f}s"
        )

        inicio_sql = time.perf_counter()
        with open(f'{sql_path}/insereDados.sql', 'r',encoding='utf-8') as file: 
            query_insercao = text(file.read())

        tabela = 'octadesk.pesquisa_de_satisfacao'
        print(f"Inserindo dados na tabela {tabela} ...")
        result = connection.execute(query_insercao)
        total_linhas_inseridas = result.rowcount
        linhas_inseridas += total_linhas_inseridas
        connection.commit()
        logger.info(f' {linhas_inseridas} linhas inseridas na tabela {tabela}')
        logger.info(
            f"Tempo de insercao tabela final: {(time.perf_counter() - inicio_sql):.2f}s"
        )
        # Notificação consolidada após o processo
        notify_slack_success(f"{linhas_inseridas} linhas inseridas na tabela {tabela}.:octadesk:",linhas_inseridas,linhas_atualizadas, rotina)

except Exception as e:
    print("Ocorreu um erro:", e)
    logger.error(f'Ocorreu um erro: {e}')
    notify_slack(f"Erro na execução da {rotina}: {e}", rotina)
finally:
    logger.info(
        f"Tempo total de execucao: {(time.perf_counter() - inicio_execucao):.2f}s"
    )


