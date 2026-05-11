# -*- coding: utf-8 -*-
"""
Pipeline Octadesk -> Postgres

Melhorias implementadas:
- Datas dinâmicas (modo 'yesterday' por padrão, veja MODO_COLETA)
- Session HTTP com Retry/Backoff e timeout
- Apenas SQLAlchemy (transação única com engine.begin())
- df.to_sql com dtype explícito (Postgres)
- Leitura de credenciais via env vars e/ou config.ini
- Tratamento seguro quando a API falha para um ID
- Logs padronizados e contagem de progresso
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from requests.adapters import HTTPAdapter, Retry
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import VARCHAR, TIMESTAMP, TEXT, INTEGER
import configparser

# ====== CONFIGURAÇÕES GERAIS ======
# Modo de coleta: "yesterday" (00:00–23:59 de ontem) ou "last_24h" (últimas 24h)
MODO_COLETA = "yesterday"  # troque para "last_24h" se preferir
TZ = ZoneInfo("America/Sao_Paulo")

# Caminhos
SQL_PATH = Path(__file__).resolve().parent
PROJ_ROOT = SQL_PATH  # ajuste se seus .sql estiverem em outra pasta

# Arquivos SQL exigidos
SQL_INSERE_STG = PROJ_ROOT / "InsereStgDados.sql"
SQL_INSERE_FINAL = PROJ_ROOT / "insereDadosUsers.sql"
SQL_ATUALIZA_FINAL = PROJ_ROOT / "atualizaDadosUsers.sql"

# Nome das tabelas
RAW_SCHEMA = "lw_octadesk"
RAW_TABLE = "rawdata_login_do_cliente"      # RAW
STG_TABLE = "lw_octadesk.stg_login_do_cliente"
FINAL_TABLE = "lw_octadesk.login_do_cliente"

# ====== LEITURA DE CONFIG E ENV VARS ======
"""
Exemplo de config.ini (opcional):

[postgres]
host = 10.30.138.28
database = report_requesttracker
user = automatizacoes
password = S3nhaSegura

[octadesk]
base_url = https://o203894-994.api003.octadesk.services
api_key = xxxxxxxx-....-yyyy

"""

CONFIG_FILE = (PROJ_ROOT / "config.ini")
cfg = configparser.ConfigParser()
if CONFIG_FILE.exists():
    cfg.read(CONFIG_FILE)

PG_HOST = os.getenv("PG_HOST", cfg.get("postgres", "host", fallback=None))
PG_DB   = os.getenv("PG_DB", cfg.get("postgres", "database", fallback=None))
PG_USER = os.getenv("PG_USER", cfg.get("postgres", "user", fallback=None))
PG_PASS = os.getenv("PG_PASS", cfg.get("postgres", "password", fallback=None))

OCTA_URL  = os.getenv("OCTA_BASE_URL", cfg.get("octadesk", "base_url", fallback=None))
OCTA_KEY  = os.getenv("OCTA_API_KEY", cfg.get("octadesk", "api_key", fallback=None))

# Validação mínima
missing = [k for k, v in {
    "PG_HOST": PG_HOST, "PG_DB": PG_DB, "PG_USER": PG_USER, "PG_PASS": PG_PASS,
    "OCTA_BASE_URL": OCTA_URL, "OCTA_API_KEY": OCTA_KEY
}.items() if not v]
if missing:
    raise RuntimeError(f"Faltam variáveis de configuração: {', '.join(missing)}")

# ====== LOGGING SIMPLES ======
from datetime import timezone
def log(msg: str):
    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")

# ====== HTTP SESSION COM RETRY ======
def make_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=4,
        backoff_factor=1.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_chat(session: requests.Session, base_url: str, token: str, chat_id: str | int, timeout=30):
    url = f"{base_url.rstrip('/')}/chat/{chat_id}"
    headers = {"accept": "application/json", "X-API-KEY": token}
    try:
        r = session.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        else:
            log(f"[API] chat {chat_id} -> HTTP {r.status_code}")
            return None
    except requests.RequestException as e:
        log(f"[API] erro chat {chat_id}: {e}")
        return None

# ====== HELPERS DE DADOS ======
def scalarize(x):
    """Converte dict/list em um valor escalar (int/float/str/None)."""
    if x is None or isinstance(x, (int, float, str)):
        return x
    if isinstance(x, dict):
        preferidas = ("login", "username", "value", "id", "name", "account_id", "customer_id")
        for k in preferidas:
            if k in x and not isinstance(x[k], (dict, list)):
                return x[k]
        for v in x.values():
            if not isinstance(v, (dict, list)):
                return v
        return None
    if isinstance(x, list):
        return scalarize(x[0]) if x else None
    return str(x)

def extrair_motivo_de_contato(custom_fields):
    """
    Procura pelo campo customField.motivo_de_contato_1.
    Pode vir como lista de objetos com .levelPath.
    """
    if not isinstance(custom_fields, list):
        return None
    for campo in custom_fields:
        if campo.get("id") == "customField.motivo_de_contato_1":
            value = campo.get("value", [])
            # value pode ser lista de dicts, string ou vazio
            if isinstance(value, list) and value:
                return value[0].get("levelPath")
            elif isinstance(value, str):
                return value
            else:
                return None
    return None

# ====== JANELA DE TEMPO ======
def periodo_coleta(modo: str = MODO_COLETA, tz: ZoneInfo = TZ):
    now = datetime.now(tz)
    if modo == "last_24h":
        fim = now.replace(microsecond=0)
        ini = fim - timedelta(hours=24)
    else:  # "yesterday"
        ontem = (now - timedelta(days=1)).date()
        ini = datetime(ontem.year, ontem.month, ontem.day, 0, 0, 0, tzinfo=tz)
        fim = datetime(ontem.year, ontem.month, ontem.day, 23, 59, 59, tzinfo=tz)
    return ini, fim

# ====== MAIN PIPELINE ======
def main():
    log("Início do pipeline")

    # 1) Conexão com Postgres
    conn_str = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}/{PG_DB}"
    engine = create_engine(conn_str, pool_pre_ping=True)

    # 2) Seleção de IDs por janela dinâmica
    dt_ini, dt_fim = periodo_coleta(MODO_COLETA, TZ)
    log(f"Janela de coleta: {dt_ini} -> {dt_fim} ({MODO_COLETA})")

    sql_ids = """
        SELECT id, data_ultima_interacao
        FROM lw_octadesk.chat
        WHERE data_ultima_interacao BETWEEN %(ini)s AND %(fim)s
    """
    with engine.connect() as conn:
        df_ids = pd.read_sql_query(sql_ids, conn, params={"ini": dt_ini, "fim": dt_fim})

    total_ids = len(df_ids)
    log(f"[diag] IDs a enriquecer: {total_ids}")

    if total_ids == 0:
        log("Nada a processar. Encerrando.")
        return

    # 3) Enriquecimento via API
    session = make_session()
    carga = []
    ok, falhas = 0, 0

    for i, row in df_ids.iterrows():
        atendimento_id = row["id"]
        atendimento = get_chat(session, OCTA_URL, OCTA_KEY, atendimento_id)

        # Inicializa campos (seguro mesmo se a API falhar)
        login_usuario = None
        customer_id = None
        messages_count = None
        motivo = None

        if atendimento:
            # contact.customFields
            contact_cf = (atendimento.get("contact") or {}).get("customFields") or {}
            login_usuario = scalarize(contact_cf.get("login_usuario"))
            customer_id = scalarize(contact_cf.get("customer_id"))
            messages_count = atendimento.get("messagesCount")

            # motivo de contato
            motivo = extrair_motivo_de_contato(atendimento.get("customFields", []))
            ok += 1
        else:
            falhas += 1

        carga.append({
            "id": str(atendimento_id),
            "data_ultima_interacao": row["data_ultima_interacao"],
            "login_usuario": login_usuario,
            "customer_id": customer_id,
            "messages_count": int(messages_count) if isinstance(messages_count, (int, str)) and str(messages_count).isdigit() else None,
            "motivo_de_contato": motivo
        })

        # log de progresso a cada 200 itens
        if (i + 1) % 200 == 0 or (i + 1) == total_ids:
            log(f"Progresso: {i + 1}/{total_ids} (ok={ok}, falhas={falhas})")

    # 4) RAW: grava DataFrame com dtype explícito
    df_raw = pd.DataFrame(carga)
    log(f"[diag] RAW linhas: {len(df_raw)}")
    df_raw.to_sql(
        RAW_TABLE,
        con=engine,
        schema=RAW_SCHEMA,
        if_exists="replace",
        index=False,
        method="multi",
        dtype={
            "id": VARCHAR(64),
            "data_ultima_interacao": TIMESTAMP(timezone=True),
            "login_usuario": VARCHAR(128),
            "customer_id": VARCHAR(128),
            "messages_count": INTEGER(),
            "motivo_de_contato": TEXT()
        }
    )
    log(f"Tabela RAW {RAW_SCHEMA}.{RAW_TABLE} atualizada (replace).")

    # 5) Executa SQLs (TRUNCATE STG + INSERE STG + INSERE FINAL + ATUALIZA FINAL)
    #    Em uma transação única.
    for f in (SQL_INSERE_STG, SQL_INSERE_FINAL, SQL_ATUALIZA_FINAL):
        if not f.exists():
            raise FileNotFoundError(f"Arquivo SQL não encontrado: {f}")

    with engine.begin() as conn:
        # TRUNCATE STG
        conn.exec_driver_sql(f"TRUNCATE TABLE {STG_TABLE}")
        log(f"Truncate em {STG_TABLE}")

        # INSERE STG
        rows = conn.execute(text(SQL_INSERE_STG.read_text(encoding="utf-8")))
        try:
            rc = rows.rowcount
        except Exception:
            rc = None
        log(f"Insert em STG concluído (linhas: {rc if rc is not None else 'n/d'})")

        # INSERE FINAL
        rows = conn.execute(text(SQL_INSERE_FINAL.read_text(encoding="utf-8")))
        try:
            rc = rows.rowcount
        except Exception:
            rc = None
        log(f"Insert na FINAL ({FINAL_TABLE}) concluído (linhas: {rc if rc is not None else 'n/d'})")

        # ATUALIZA FINAL
        rows = conn.execute(text(SQL_ATUALIZA_FINAL.read_text(encoding="utf-8")))
        try:
            rc = rows.rowcount
        except Exception:
            rc = None
        log(f"Update na FINAL ({FINAL_TABLE}) concluído (linhas afetadas: {rc if rc is not None else 'n/d'})")

    # 6) Fim
    engine.dispose()
    log("Pipeline finalizado com sucesso.")

if __name__ == "__main__":
    main()
