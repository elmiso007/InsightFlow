import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import VARCHAR, TIMESTAMP, TEXT
from datetime import datetime, timedelta
import json
import requests
import urllib3
from function_logger import configurar_logger
from pathlib import Path
import os
import configparser
import time

sql_path = Path(__file__).parent
# Vase o config.ini no root do workspace (subindo de tray/login_cliente -> tray -> .)
root_config_path = Path(__file__).resolve().parents[2] / 'config.ini'
config_file_path = root_config_path

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

def get_user(DDL_URL, TOKEN, ID, verify_ssl=True):
    endpoint = f"{DDL_URL}/chat/{ID}"
    headers = {"accept": "application/json", "X-API-KEY": TOKEN}

    try:
        r = requests.get(endpoint, headers=headers, timeout=120, verify=verify_ssl)
        if r.status_code == 200:
            return r.json()
        elif r.status_code >= 500:
            logger.error(f"[API] {ID} -> status {r.status_code}: {r.text}")
            return None
        else:
            logger.error(f"[API] {ID} -> status {r.status_code}: {r.text}")
            return None
    except requests.RequestException as e:
        logger.error(f"[API] Erro ao buscar {ID}: {e}")
        return None

# -------- setup --------
logger = configurar_logger()

# Carregar configurações do config.ini com validação
def load_config():
    config = configparser.ConfigParser()
    config.read(config_file_path)

    def get_required(section, option, name=None):
        name = name or option
        try:
            value = config.get(section, option)
            if not value:
                raise ValueError(f"Variável {name} não definida no config.ini")
            return value
        except (configparser.NoSectionError, configparser.NoOptionError):
            raise ValueError(f"Variável {name} não definida no config.ini")

    config_dict = {}

    # Seção tray
    config_dict['TRAY_DDL_URL'] = get_required('tray', 'DDL_URL', 'TRAY_DDL_URL')
    config_dict['TRAY_TOKEN'] = get_required('tray', 'TOKEN', 'TRAY_TOKEN')
    config_dict['TRAY_VERIFY_SSL'] = config.getboolean('tray', 'verify_ssl', fallback=True)

    # Seção database
    config_dict['DB_SERVER'] = get_required('database', 'server', 'DB_SERVER')
    config_dict['DB_DATABASE'] = get_required('database', 'database', 'DB_DATABASE')
    config_dict['DB_UID'] = get_required('database', 'uid', 'DB_UID')
    config_dict['DB_PWD'] = get_required('database', 'pwd', 'DB_PWD')

    # Optional
    config_dict['TIME_WINDOW_MINUTES'] = config.getint('tray', 'TIME_WINDOW_MINUTES', fallback=80)

    return config_dict

config = load_config()

DDL_URL = config['TRAY_DDL_URL']
TOKEN = config['TRAY_TOKEN']
VERIFY_SSL = config['TRAY_VERIFY_SSL']
TIME_WINDOW_MINUTES = config['TIME_WINDOW_MINUTES']

if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    server = config['DB_SERVER']
    database = config['DB_DATABASE']
    uid = config['DB_UID']
    pwd = config['DB_PWD']
    conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
    engine = create_engine(conn_string)
    connection = engine.connect()

    logger.info("Banco conectado com sucesso")
except Exception as e:
    print("Ocorreu um erro na conexão com o banco:", e)
    logger.error(f"Ocorreu um erro de conexão: {e}")
    raise


print(f"Inicio : {datetime.now()}")

# -------- coleta IDs a enriquecer --------
data_2 = datetime.now()
data_1 = data_2 - timedelta(minutes=TIME_WINDOW_MINUTES)

query = (f"SELECT id, data_ultima_interacao FROM tray.chat WHERE data_ultima_interacao >= '{data_1}'")
#query = (f"SELECT id, data_ultima_interacao FROM tray.chat WHERE data_ultima_interacao BETWEEN '2026-02-22 21:00:00' AND '2026-02-23 09:00:59'")

df = pd.read_sql_query(query, connection)

#CONTAGEM DE LIHAS DO DF
print(f"[diag] base: {len(df)} linhas")

# -------- enrich + staging --------
carga = []

for _, row in df.iterrows():
    atendimento_id = row['id']
    atendimento = get_user(DDL_URL, TOKEN, atendimento_id, verify_ssl=VERIFY_SSL)

    if not atendimento:
        logger.warning(f"Falha ao obter dados para ID {atendimento_id}. Pulando...")
        continue

    # Salvar resposta da API em JSON para debug (opcional)
    json_file = 'atendimentos_tray.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(atendimento, f, ensure_ascii=False, indent=4)

    login_usuario = customer_id = messages_count = None
    level_path = None
    past_agents_json = None
    from_number = from_name = to_number = None

    try:
        contact_cf = atendimento.get('contact', {}).get('customFields', {})
        login_usuario = scalarize(contact_cf.get('login_usuario', None))
        customer_id = scalarize(contact_cf.get('customer_id', None))
        messages_count = atendimento.get('messagesCount', None)
        cf = atendimento.get('customFields', [])

        past_agents = atendimento.get('pastAgents', [])
        past_agents_json = json.dumps(past_agents) if past_agents else None

        level_path = None
        for campo in cf:
            if campo.get("id") == "customField.motivo_de_contato_1":
                value = campo.get("value", [])
                if isinstance(value, list) and value:
                    level_path = value[0].get("levelPath")
                break

        from_number = from_name = to_number = None
        for campo in cf:
            if campo.get("id") == "octabsp":
                integrator = campo.get("integrator", {})
                from_data = integrator.get("from", {})
                to_data = integrator.get("to", {})

                from_number = from_data.get("number")
                from_name = from_data.get("name")
                to_number = to_data.get("number")
                break

    except Exception as e:
        logger.error(f"Erro ao processar dados para ID {atendimento_id}: {e}")
        continue

    carga.append({
        "id": str(atendimento_id),
        "data_ultima_interacao": row['data_ultima_interacao'],
        "login_usuario": login_usuario,
        "customer_id": customer_id,
        "messages_count": messages_count,
        "motivo_de_contato": level_path,
        "lista_agentes": past_agents_json,
        "from_number": from_number,
        "from_name": from_name,
        "to_number": to_number
    })

df_content = pd.DataFrame(carga)


# staging com dtype explícito (NÃO filtra nada)
df_content.to_sql(
    'rawdata_login_do_cliente',
    con=engine,
    if_exists='replace',
    index=False,
    schema='tray',
    method='multi')

# -------- merge/upsert final --------

try:
    # Alimenta a tabela raw
    df_content.to_sql(
        'rawdata_login_do_cliente',
        con=engine,
        if_exists='replace',
        index=False,
        schema='tray',
        method='multi'
    )
    logger.info(f"{len(df_content)} linhas inseridas na tabela rawdata_login_do_cliente")

    # Trunca a tabela stg
    table_name = 'tray.stg_login_do_cliente'
    truncate_query = text(f"TRUNCATE TABLE {table_name}")
    connection.execute(truncate_query)
    connection.commit()
    logger.info(f"Tabela {table_name} truncada com sucesso")

    # Alimenta a tabela stg
    with open(f'{sql_path}/InsereStgDados.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    result = connection.execute(query_insercao)
    connection.commit()
    logger.info(f"{result.rowcount} linhas inseridas na tabela {table_name}")

    # Inserção na tabela final
    with open(f'{sql_path}/insereDadosUsers.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    tabela = 'tray.login_do_cliente'
    result = connection.execute(query_insercao)
    connection.commit()
    logger.info(f'{result.rowcount} linhas inseridas em {tabela}')

    # Atualização na tabela final
    with open(f'{sql_path}/atualizaDadosUsers.sql', 'r', encoding='utf-8') as file:
        query_atualizacao = text(file.read())

    result = connection.execute(query_atualizacao)
    connection.commit()
    logger.info(f'{result.rowcount} linhas atualizadas em {tabela}')

except Exception as e:
    logger.error(f'Ocorreu um erro no processamento do banco: {e}')
    connection.rollback()
    raise
finally:
    try:
        connection.close()
    except Exception:
        pass
    try:
        engine.dispose()
    except Exception:
        pass

print(f"FIM : {datetime.now()}")