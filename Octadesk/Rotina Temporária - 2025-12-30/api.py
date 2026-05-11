import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import VARCHAR, TIMESTAMP, TEXT
from datetime import datetime, timedelta
import json
import configparser
import requests
import psycopg2
from function_logger import configurar_logger
from pathlib import Path
import os

sql_path = Path(__file__).parent

# -------- helpers --------
def scalarize(x):
    """
    Converte dict/list em um valor escalar amigável ao Postgres (int, float, str ou None).
    Regras:
      - Se for None, número ou string → retorna como está.
      - Se for dict → tenta extrair chaves conhecidas ou o primeiro valor simples.
      - Se for list → tenta converter o primeiro elemento.
      - Se não couber nos casos acima → converte para string.
    """
    
    # Já é escalar
    if x is None or isinstance(x, (int, float, str)):
        return x

    # Se for dicionário
    if isinstance(x, dict):
        # Chaves de interesse
        preferidas = ("login", "username", "value", "id", "name", "account_id", "customer_id")
        
        # 1. Procura pelas chaves preferidas
        for chave in preferidas:
            if chave in x and not isinstance(x[chave], (dict, list)):
                return x[chave]
        
        # 2. Caso contrário, pega o primeiro valor escalar disponível
        for valor in x.values():
            if not isinstance(valor, (dict, list)):
                return valor
        
        # 3. Não encontrou nada aproveitável
        return None

    # Se for lista
    if isinstance(x, list):
        return scalarize(x[0]) if x else None

    # Qualquer outro tipo → força string
    return str(x)


def clean_str(x, maxlen=None):
    """strip -> '' vira None -> trunca se precisar."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).strip()
    if s == "":
        return None
    return s[:maxlen] if maxlen else s

def get_user(DDL_URL, TOKEN, ID):
    endpoint = f"{DDL_URL}/chat/{ID}"
    headers = {"accept": "application/json", "X-API-KEY": TOKEN}
    try:
        r = requests.get(endpoint, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"[API] {ID} -> status {r.status_code}")
            return None
    except requests.RequestException as e:
        print(f"[API] erro {ID}: {e}")
        return None

# -------- setup --------
logger = configurar_logger()

config_folder = f'{sql_path}/../..'
config_file_path = os.path.join(config_folder, 'config.ini')

config = configparser.ConfigParser()
config.read(config_file_path)

try:
    server = config['database']['server']
    database = config['database']['database']
    uid = config['database']['uid']
    pwd = config['database']['pwd']
    conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
    engine = create_engine(conn_string)
    connection = engine.connect()

    psy_conn = psycopg2.connect(dbname=database, user=uid, password=pwd, host=server)
    cur = psy_conn.cursor()
    logger.info("Banco conectado com sucesso")
except Exception as e:
    print("Ocorreu um erro:", e)
    logger.error(f"Ocorreu um erro de conexão: {e}")


print(f"Inicio : {datetime.now()}")



DDL_URL = "https://help.apibeta.octadesk.services"
TOKEN = "75657565-0f17-4044-ab0b-3268d2052a6b.13dd5460-8d60-4df0-b79a-7d842db006dc"


# -------- coleta IDs a enriquecer --------
data_2 = datetime.now()
data_1 = data_2 - timedelta(minutes=60)

#query = (f"SELECT id, data_ultima_interacao FROM vindi.chat WHERE data_ultima_interacao >= '{data_1}'")
query = (f"SELECT id, data_ultima_interacao FROM octadesk.chat WHERE data_ultima_interacao BETWEEN '2025-11-11 00:00:00' AND '2025-11-21 23:59:59'")

df = pd.read_sql_query(query, connection)

#CONTAGEM DE LIHAS DO DF
print(f"[diag] base: {len(df)} linhas")

# -------- enrich + staging --------
carga = []

for _, row in df.iterrows():
    atendimento_id = row['id']
    atendimento = get_user(DDL_URL, TOKEN, atendimento_id)

    json_file = 'atendimentos_octa.json'

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(atendimento, f, ensure_ascii=False, indent=4)

    if atendimento:

        contact_cf =  atendimento.get('contact',{}).get('customFields',{})
        messages_count = atendimento.get('messagesCount',None)
        cf = atendimento.get('customFields',[])

        past_agents = atendimento.get('pastAgents',[])
        # Extrai apenas os nomes, mantendo a ordem original
        nomes = [item.get('name') for item in past_agents]

        # Garante que sempre haverá até 5 posições, preenchendo com None se faltar
        nomes = (nomes + [None] * 10)[:10]

        # Atribui cada um a uma variável
        agente1, agente2, agente3, agente4, agente5,agente6,agente7,agente8,agente9,agente10 = nomes 

        past_agents = json.dumps(past_agents)

        level_path = None

        

        # Inicializa as variáveis com None
        from_number = None
        from_name = None
        to_number = None

        conversation_origin = None

        conversation_origin = atendimento.get("conversationOrigin")

        # Percorre todos os itens de customFields
        for campo in cf:
            if campo.get("id") == "octabsp":  
                integrator = campo.get("integrator", {})
                from_data = integrator.get("from", {})
                to_data = integrator.get("to", {})

                from_number = from_data.get("number")
                from_name = from_data.get("name")
                to_number = to_data.get("number")
                break  


    carga.append({
        "id": str(atendimento_id),
        "data_ultima_interacao": row['data_ultima_interacao'],
        "messages_count":messages_count,
        "lista_agentes":past_agents,
        "agente1":agente1,
        "agente2":agente2, 
        "agente3":agente3, 
        "agente4":agente4, 
        "agente5":agente5,
        "agente6":agente6,
        "agente7":agente7, 
        "agente8":agente8, 
        "agente9":agente9, 
        "agente10":agente10,
        "from_number":from_number,
        "from_name":from_name,
        "to_number":to_number,
        "conversation_origin":conversation_origin

    })

df_content = pd.DataFrame(carga)


# staging com dtype explícito (NÃO filtra nada)
df_content.to_sql(
    'rawdata_temporaria',
    con=engine,
    if_exists='replace',
    index=False,
    schema='octadesk',
    method='multi')

## -------- merge/upsert final --------

#try:
#    total_linhas_inseridas = 0
#    # Trunca a tabela stgchat
#    table_name = 'lw_octadesk.stg_login_do_cliente'
#    truncate_query = f"TRUNCATE TABLE {table_name}"
#    cur.execute(truncate_query)
#    psy_conn.commit()
#    print(f"Tabela {table_name} truncada com sucesso")
#
#    # Alimenta a tabela octadesk.stgchat
#    with open(f'{sql_path}/InsereStgDados.sql', 'r', encoding='utf-8') as file:
#        query_insercao = text(file.read())
#
#    with engine.connect() as conn:
#        result = conn.execute(query_insercao)
#        linhas_inseridas = result.rowcount
#        total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
#        conn.commit()
#        print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")
#
#     #INSERÇÃO DE DADOS NA TABELA FINAL
#    with open(f'{sql_path}/insereDadosUsers.sql', 'r', encoding='utf-8') as file:
#        query_insercao = text(file.read())
#
#    tabela = 'lw_octadesk.login_do_cliente'
#    result = connection.execute(query_insercao)
#    connection.commit()
#    logger.info(f'{result.rowcount} linhas inseridas em {tabela}')
#
#    with open(f'{sql_path}/atualizaDadosUsers.sql', 'r', encoding='utf-8') as file:
#        query_atualizacao = text(file.read())
#
#    result = connection.execute(query_atualizacao)
#    connection.commit()
#    logger.info(f'{result.rowcount} linhas atualizadas em {tabela}')
#except Exception as e:
#    print("Ocorreu um erro:", e)
#    logger.error(f'Ocorreu um erro: {e}')
#finally:
#    try:
#        connection.close()
#    except Exception:
#        pass
#    try:
#        engine.dispose()
#    except Exception:
#        pass
##
print(f"FIM : {datetime.now()}")