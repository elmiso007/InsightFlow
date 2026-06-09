"""
Backfill histórico de PRBs do Service-Now (carga única).

Diferença para o api.py (rotina diária incremental):
  - NÃO aplica o filtro de "últimas 24h" — traz todo o histórico (ou os últimos
    N anos, via --anos).
  - Pagina a API (sysparm_limit + sysparm_offset + ORDERBYnumber) em loop até
    esvaziar, evitando o corte padrão do Service-Now (~10.000 registros).

Mantém prioridade P1-P5 e as empresas Locaweb / Octadesk / KingHost, e reusa
exatamente o mesmo pipeline de carga e os mesmos SQLs do api.py
(StgInsereDados.sql -> InsereDados.sql -> AtualizaDados.sql). Como a staging usa
DISTINCT e a tabela final dedupa por `numero` (NOT EXISTS), rodar o backfill é
idempotente e seguro mesmo com a rotina diária já em produção.

Uso:
  python backfill.py                 # todo o histórico
  python backfill.py --anos 3        # PRBs abertos nos últimos 3 anos
  python backfill.py --page-size 500 # tamanho de página menor (default 1000)
  python backfill.py --dry-run       # só extrai e grava CSV, não toca no banco
"""

import argparse
import os
import sys
from datetime import datetime
from io import StringIO  # noqa: F401  (mantido por paridade com api.py)
from pathlib import Path
from urllib.parse import urlencode

import configparser
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from sqlalchemy import create_engine, text

from function_logger import configurar_logger

# Adiciona o caminho dois diretórios acima ao Python Path (igual ao api.py)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from notifica import notify_slack, notify_slack_success  # noqa: E402

sql_path = Path(__file__).parent
config_path = f"{sql_path}/../"

logger = configurar_logger()

ROTINA = "LWSA (Backfill histórico Problems P1-P5)"
TABELA_RAW = "rawdata_service_now_problems"
SCHEMA = "lwsa"


def executar_sql(engine, sql_file_path, descricao="operação SQL"):
    """Executa um arquivo SQL e retorna o número de linhas afetadas."""
    try:
        with open(sql_file_path, "r", encoding="utf-8") as file:
            query = text(file.read())
        with engine.connect() as conn:
            result = conn.execute(query)
            conn.commit()
            linhas_afetadas = result.rowcount
            logger.info(f"{descricao}: {linhas_afetadas} linhas afetadas")
            return linhas_afetadas
    except Exception as e:
        logger.error(f"Erro ao executar {descricao}: {e}")
        raise


def parse_args():
    parser = argparse.ArgumentParser(
        description="Backfill histórico de PRBs do Service-Now."
    )
    parser.add_argument(
        "--anos",
        type=int,
        default=None,
        help="Limita aos PRBs abertos nos últimos N anos (opened_at). "
        "Omitir = todo o histórico.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="Registros por página da API Service-Now (default 1000).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Só extrai da API e grava o CSV; não escreve no banco.",
    )
    return parser.parse_args()


def carregar_config():
    config_file_path = os.path.join(config_path, "config.ini")
    config = configparser.ConfigParser()
    config.read(config_file_path)
    return config


def montar_query_filters(anos):
    """Filtros do backfill: SEM janela de 24h. Opcionalmente limita por anos."""
    filtros = [
        "priority=1^ORpriority=2^ORpriority=3^ORpriority=4^ORpriority=5",
        "company.name=Octadesk^ORcompany.name=Locaweb^ORcompany.name=KingHost",
    ]
    if anos is not None:
        # Relativo ao opened_at: PRBs abertos de N anos atrás até agora.
        filtros.append(f"opened_atRELATIVEGT@year@ago@{anos}")
    # ORDERBYnumber garante paginação estável entre as páginas.
    filtros.append("ORDERBYnumber")
    return filtros


def valor_display(campo):
    if isinstance(campo, dict):
        return campo.get("display_value") or campo.get("value")
    return campo


def extrair_id_departamento(campo_departamento):
    if isinstance(campo_departamento, dict):
        link = campo_departamento.get("link")
        if link:
            return link.split("/")[-1]
        return campo_departamento.get("value")
    return campo_departamento


def mapear_registro(problem):
    """Mesmo mapeamento de campos do api.py."""
    return {
        "numero": problem.get("number"),
        "organizacao": valor_display(problem.get("company")),
        "task_for": valor_display(problem.get("task_for")),
        "servidor": valor_display(problem.get("cmdb_ci")),
        "grupo_designado": valor_display(problem.get("assignment_group")),
        "designado_para": valor_display(problem.get("assigned_to")),
        "prioridade": problem.get("priority"),
        "produto": valor_display(problem.get("u_produto")),
        "categoria": problem.get("u_categoria"),
        "subcategoria": problem.get("u_subcategoria"),
        "status": problem.get("state"),
        "origem": problem.get("u_origem"),
        "data_abertura": problem.get("opened_at"),
        "aberto_por": valor_display(problem.get("opened_by")),
        "data_encerrado": problem.get("closed_at"),
        "fechado_por": valor_display(problem.get("closed_by")),
        "codigo_encerramento": problem.get("u_codigo_de_encerramento"),
        "chamado_externo": problem.get("u_chamado_externo"),
        "prb_revisado": problem.get("u_prb_revisado"),
        "descricao_curta": problem.get("short_description"),
        "descricao": problem.get("description"),
        "solucao_alternativa": problem.get("u_solucao_alternativo"),
        "fechamento": problem.get("close_notes"),
        "atualizacoes": problem.get("sys_mod_count"),
        "id_departamento": extrair_id_departamento(problem.get("opened_by.department")),
    }


def extrair_paginado(base_url, auth, headers, params_base, page_size, timeout):
    """
    Itera sobre as páginas da API até receber menos que page_size registros.
    Retorna a lista completa de registros já mapeados.
    """
    carga = []
    offset = 0
    pagina = 0

    while True:
        params = dict(params_base)
        params["sysparm_limit"] = page_size
        params["sysparm_offset"] = offset
        url = f"{base_url}?{urlencode(params, safe='^@=!')}"

        try:
            response = requests.get(url, auth=auth, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout:
            logger.error(f"Timeout na página offset={offset} após {timeout}s")
            raise Exception("Timeout na requisição para API Service Now")
        except requests.exceptions.ConnectionError:
            logger.error("Erro de conexão com a API Service Now")
            raise Exception("Erro de conexão com a API Service Now")
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição (offset={offset}): {e}")
            raise Exception(f"Erro na requisição para API Service Now: {e}")

        if response.status_code != 200:
            logger.error(
                f"Erro na API Service Now: {response.status_code} - {response.text}"
            )
            raise Exception(f"API retornou erro: {response.status_code}")

        resultados = response.json().get("result", [])
        recebidos = len(resultados)
        pagina += 1

        for problem in resultados:
            carga.append(mapear_registro(problem))

        msg = (
            f"Página {pagina}: {recebidos} registros "
            f"(offset {offset}); acumulado {len(carga)}"
        )
        print(msg)
        logger.info(msg)

        # IMPORTANTE: no Service-Now o filtro de ACL é aplicado DEPOIS do
        # sysparm_limit, então uma página pode vir com menos que page_size mesmo
        # havendo mais registros adiante. Por isso só paramos quando a página vem
        # vazia, e sempre avançamos o offset pelo page_size (não pelo recebidos).
        if recebidos == 0:
            break
        offset += page_size

    return carga


def main():
    args = parse_args()

    try:
        config = carregar_config()
        username = config["service_now"]["username"]
        senha = config["service_now"]["pwd"]
        instance = config["service_now"]["instance"]
        timeout = int(config["service_now"]["timeout"])

        server = config["database"]["server"]
        database = config["database"]["database"]
        uid = config["database"]["uid"]
        pwd = config["database"]["pwd"]

        conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
        engine = create_engine(conn_string)
        logger.info("Banco conectado com sucesso")
    except Exception as e:
        print("Ocorreu um erro:", e)
        logger.error(f"Ocorreu um erro de conexão: {e}")
        raise

    base_url = f"https://{instance}.service-now.com/api/now/table/problem"

    fields = [
        "number", "company", "task_for", "cmdb_ci", "assignment_group",
        "assigned_to", "priority", "u_produto", "u_categoria", "u_subcategoria",
        "state", "u_origem", "opened_at", "opened_by", "closed_at", "closed_by",
        "u_codigo_de_encerramento", "u_chamado_externo", "u_prb_revisado",
        "short_description", "description", "u_solucao_alternativo", "close_notes",
        "sys_mod_count", "opened_by.department",
    ]

    query_filters = montar_query_filters(args.anos)
    params_base = {
        "sysparm_query": "^".join(query_filters),
        "sysparm_display_value": "true",
        "sysparm_fields": ",".join(fields),
    }
    headers = {"Content-Type": "application/json"}
    auth = HTTPBasicAuth(username, senha)

    janela = f"últimos {args.anos} anos" if args.anos else "histórico completo"
    print(f"Iniciando backfill ({janela}), página de {args.page_size} registros...")
    logger.info(f"Backfill iniciado — janela: {janela}, page_size={args.page_size}")

    total_linhas_inseridas = 0
    total_linhas_atualizadas = 0
    table_name = "lwsa.service_now_problems"

    try:
        carga = extrair_paginado(
            base_url, auth, headers, params_base, args.page_size, timeout
        )

        df_content = pd.DataFrame(carga)
        df_content.to_csv(sql_path / "dados_backfill.csv", index=False)
        print(f"Total extraído: {len(df_content)} registros (CSV: dados_backfill.csv)")

        if df_content.empty:
            msg = "Nenhum PRB retornado no backfill. DataFrame vazio."
            print(msg)
            logger.warning(msg)
            notify_slack_success(f"{msg} :lwsa:", 0, 0, ROTINA)
            engine.dispose()
            return

        if args.dry_run:
            print("--dry-run ativo: nada foi escrito no banco.")
            logger.info("Backfill em dry-run; banco não alterado.")
            engine.dispose()
            return

        # Mesmo pipeline do api.py: raw (replace) -> stg (truncate+insert) -> final
        df_content.to_sql(
            TABELA_RAW, con=engine, if_exists="replace", index=False, schema=SCHEMA
        )
        print(f"Dados carregados na tabela: {TABELA_RAW}...")

        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE lwsa.stg_service_now_problems"))
            conn.commit()
            print("Tabela lwsa.stg_service_now_problems truncada com sucesso")

        linhas = executar_sql(
            engine,
            f"{sql_path}/StgInsereDados.sql",
            "Inserção na tabela lwsa.stg_service_now_problems",
        )
        print(f"{linhas} linhas inseridas na staging.")

        total_linhas_inseridas = executar_sql(
            engine, f"{sql_path}/InsereDados.sql", f"Inserção na tabela {table_name}"
        )
        print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")

        total_linhas_atualizadas = executar_sql(
            engine, f"{sql_path}/AtualizaDados.sql", f"Atualização da tabela {table_name}"
        )
        print(f"{total_linhas_atualizadas} linhas atualizadas na tabela {table_name}.")

    except Exception as e:
        print("Ocorreu um erro:", e)
        logger.error(f"Ocorreu um erro: {e}")
        notify_slack(f"Erro na execução da {ROTINA}: {e}", ROTINA)
        engine.dispose()
        raise

    notify_slack_success(
        f"{total_linhas_inseridas} linhas inseridas e "
        f"{total_linhas_atualizadas} linhas atualizadas na tabela {table_name} :lwsa:",
        total_linhas_inseridas,
        total_linhas_atualizadas,
        ROTINA,
    )

    print(f"Fim : {datetime.now()}")
    engine.dispose()
    logger.info("Conexão com banco encerrada")


if __name__ == "__main__":
    main()
