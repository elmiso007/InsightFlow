"""
Acesso à configuração do PostgreSQL e introspecção de colunas (compartilhado entre os pipelines).

Usado pelo LocaPredict e pelo Guardião para montar SQL compatível com o schema real.
"""

from __future__ import annotations

import configparser
from typing import Any, Dict, Set


def load_db_config(path: str = "config.ini") -> Dict[str, Any]:
    """
    Lê a seção [database] e devolve um dicionário pronto para psycopg2.connect(**kwargs).

    Aceita nomes alternativos de chaves (server/host, database/dbname, uid/user, pwd/password).
    """
    cfg = configparser.ConfigParser()
    cfg.read(path)

    if "database" not in cfg:
        raise ValueError(f"O arquivo '{path}' não contém a seção [database]")

    # Mapeamento unificado para os nomes esperados pelo psycopg2
    parametros = {
        "host": cfg.get("database", "server", fallback=None) or cfg.get("database", "host", fallback=None),
        "port": cfg.getint("database", "port", fallback=5432),
        "dbname": cfg.get("database", "database", fallback=None)
        or cfg.get("database", "dbname", fallback=None),
        "user": cfg.get("database", "uid", fallback=None) or cfg.get("database", "user", fallback=None),
        "password": cfg.get("database", "pwd", fallback=None)
        or cfg.get("database", "password", fallback=None),
    }

    faltando = [k for k, v in parametros.items() if v is None]
    if faltando:
        raise ValueError(f"Faltam chaves em [database]: {', '.join(faltando)}")

    return parametros


def get_table_columns(conn, schema: str, table: str) -> Set[str]:
    """
    Lista nomes de colunas publicadas em information_schema para o par esquema/tabela.

    Serve para decidir dinamicamente quais expressões SQL usar (tempo, atualizações, etc.).
    """
    consulta_sql = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s
    """
    with conn.cursor() as cursor_banco:
        cursor_banco.execute(consulta_sql, (schema, table))
        return {row[0] for row in cursor_banco.fetchall()}
