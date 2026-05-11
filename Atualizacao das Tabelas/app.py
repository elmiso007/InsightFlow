from typing import Optional, Dict, Any
import pandas as pd
from sqlalchemy import create_engine
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime
import sys
import os
import configparser
import json
import time
from tabulate import tabulate

def load_dotenv(dotenv_path: str) -> None:
    if not os.path.isfile(dotenv_path):
        return
    with open(dotenv_path, "r", encoding="utf-8") as dotenv_file:
        for raw_line in dotenv_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def normalize_placeholder(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    upper_value = value.upper()
    if upper_value.startswith("YOUR_") or upper_value.startswith("CHANGE_ME"):
        return None
    if value.startswith("<") and value.endswith(">"):
        return None
    return value


def get_setting(env_key: str, section: str, option: str, config: configparser.ConfigParser) -> Optional[str]:
    env_value = os.environ.get(env_key)
    if env_value:
        return env_value
    config_value = config.get(section, option, fallback=None)
    return normalize_placeholder(config_value)

def log_event(log_path: str, level: str, message: str, context: Optional[Dict[str, Any]] = None) -> None:
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "level": level,
        "message": message,
        "context": context or {},
    }
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(payload, ensure_ascii=False) + "\n")


# ----- Configurações de Conexão PostgreSQL -----
config = configparser.ConfigParser()
base_dir = os.path.dirname(__file__)
dotenv_paths = [
    os.path.join(base_dir, ".env"),
]
config_path = os.path.join(base_dir, "config.ini")

for dotenv_path in dotenv_paths:
    load_dotenv(dotenv_path)
config.read(config_path)

logs_dir = os.path.join(base_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)
log_path = os.path.join(logs_dir, f"auditoria_{datetime.now().date().isoformat()}.log")
log_event(log_path, "INFO", "Inicio da execucao", {"app": "Atualizacao das Tabelas"})

server = get_setting("PG_SERVER", "database", "server", config)
database = get_setting("PG_DATABASE", "database", "database", config)
uid = get_setting("PG_USER", "database", "uid", config)
pwd = get_setting("PG_PASSWORD", "database", "pwd", config)

missing_db = [k for k, v in {"PG_SERVER": server, "PG_DATABASE": database, "PG_USER": uid, "PG_PASSWORD": pwd}.items() if not v]
if missing_db:
    log_event(log_path, "ERROR", "Configuracao de banco incompleta", {"missing": missing_db})
    sys.exit(f"Configuração de banco incompleta. Variáveis faltando: {', '.join(missing_db)}")

conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
engine = create_engine(conn_string)
connection = engine.connect()

# ----- Verificação das tabelas principais -----
'''query_verification = """
SELECT 'lw_octadesk.chat'::varchar AS "tabela",
       MAX(data_inicio_interacao) AS "atualizacao",
       CASE WHEN MAX(data_inicio_interacao) = CURRENT_DATE - 1 THEN TRUE ELSE FALSE END AS "D-1",
       COUNT(CASE WHEN data_inicio_interacao = CURRENT_DATE - 1 THEN 1 END) AS "qtd_d1",
       COUNT(CASE WHEN data_inicio_interacao = CURRENT_DATE - 2 THEN 1 END) AS "qtd_d2"
FROM lw_octadesk.chat

"""
df_ver = pd.read_sql_query(query_verification, connection)

for _, row in df_ver.iterrows():
    if row['D-1']:
        print(f"Tabela {row['tabela']} atualizada")
    else:
        print(f"Tabela {row['tabela']} NÃO foi devidamente atualizada")
        connection.close()
        sys.exit("Encerrando: inconsistência detectada.")

print("Tabelas Base atualizadas.")
'''
# ----- Consulta à view resumo -----
query = "SELECT * FROM aplicacao.atualizacao_das_tabelas;"
df = pd.read_sql_query(query, connection)
connection.close()

print("Colunas retornadas da view:", df.columns.tolist())
log_event(log_path, "INFO", "View consultada", {"rows": int(df.shape[0])})

required_cols = {'tabela', 'atualizacao', 'd_1', 'qtd_d1', 'qtd_d2'}
if not required_cols.issubset(df.columns):
    log_event(log_path, "ERROR", "Colunas esperadas nao encontradas", {"columns": list(df.columns)})
    print("Colunas esperadas não encontradas. Verifique a view.")
    sys.exit("Encerrando por inconsistência nas colunas retornadas.")

# ----- Prepara mensagem para Slack -----
dia = datetime.now().date()
SLACK_TOKEN = get_setting("SLACK_TOKEN", "slack", "token", config)

# ===== ESCOLHA O CANAL: COMENTE/DESCOMENTE AS LINHAS ABAIXO =====
# Canal Oficial (padrão)
CHANNEL_ID = get_setting("SLACK_CHANNEL", "slack", "channel_id", config)
canal_selecionado = "OFICIAL"

# Canal de Teste - descomente as duas linhas abaixo para usar o canal de teste
# CHANNEL_ID = "C07NSPQ69TL"
# canal_selecionado = "TESTE"
# ================================================================

missing_slack = [k for k, v in {"SLACK_TOKEN": SLACK_TOKEN, "SLACK_CHANNEL": CHANNEL_ID}.items() if not v]
if missing_slack:
    log_event(log_path, "ERROR", "Configuracao do Slack incompleta", {"missing": missing_slack})
    sys.exit(f"Configuração do Slack incompleta. Variáveis faltando: {', '.join(missing_slack)}")

# Organizar e formatar a tabela com tabulate
df_fmt = df[["tabela", "atualizacao", "d_1", "qtd_d1", "qtd_d2"]].copy()
df_fmt.columns = ["Tabela", "Atualização", "D-1", "Qtd. D-1", "Qtd. D-2"]
df_fmt["D-1"] = df_fmt["D-1"].map({True: "✅", False: "❌"})

warning_text = None
if df.empty:
    warning_text = "⚠️ A view retornou 0 registros. Verifique a atualizacao dos dados."
    print(warning_text)
    log_event(log_path, "WARNING", "View retornou 0 registros")

mensagem_final = "```\n" + tabulate(df_fmt, headers="keys", tablefmt="github", showindex=False) + "\n```"

blocks = [
    {"type": "section", "text": {"type": "mrkdwn", "text": f"*Resumo das atualizações das tabelas e quantitativos D-1 e D-2 em:* `{dia}`"}},
    {"type": "section", "text": {"type": "mrkdwn", "text": f"📢 *Canal:* `{canal_selecionado}`"}},
    {"type": "section", "text": {"type": "mrkdwn", "text": warning_text}} if warning_text else None,
    {"type": "section", "text": {"type": "mrkdwn", "text": mensagem_final}},
]
blocks = [block for block in blocks if block is not None]

client = WebClient(token=SLACK_TOKEN)
log_event(log_path, "INFO", f"Enviando mensagem para canal {canal_selecionado}", {"channel": CHANNEL_ID})

max_attempts = 3
base_delay_seconds = 2
for attempt in range(1, max_attempts + 1):
    try:
        client.chat_postMessage(channel=CHANNEL_ID, text=f"Atualizações de tabelas: {dia}", blocks=blocks)
        print(f"✅ Mensagem enviada ao Slack (Canal: {canal_selecionado}) com sucesso.")
        log_event(log_path, "INFO", "Mensagem enviada ao Slack", {"channel": CHANNEL_ID, "mode": canal_selecionado, "attempt": attempt})
        break
    except SlackApiError as e:
        error_msg = e.response["error"]
        log_event(log_path, "ERROR", "Erro ao enviar mensagem Slack", {"error": error_msg, "attempt": attempt})
        if attempt == max_attempts:
            print("❌ Erro ao enviar mensagem:", error_msg)
            sys.exit(1)
        delay = base_delay_seconds * (2 ** (attempt - 1))
        time.sleep(delay)
