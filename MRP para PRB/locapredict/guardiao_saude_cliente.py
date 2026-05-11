"""
Aplicação **Guardião da Saúde do Cliente** — monitora recorrência de incidentes por `login_cliente` e `produto`.

O campo `login_cliente` é **normalizado** no SQL antes de agrupar, para unificar formatos distintos
(URLs com `ficha=`, código numérico, texto simples, texto com ``(Cód. NNN)``). Ver
``_expressao_sql_normalizar_login_cliente``.

O script identifica pares com volume elevado em uma janela de N meses, grava histórico opcional
e envia alertas ao Slack usando a mesma configuração `[slack]` do LocaPredict.

**Arquivo:** `guardiao_saude_cliente.py`.

**Configuração:** seção `[customer_health_guardian]` no `config.ini` (nome da seção mantido por
compatibilidade com instalações existentes). Chaves preferencialmente em português; equivalentes
em inglês ainda são aceitas.
"""

from __future__ import annotations

import configparser
import os
import sys
from typing import Optional

from certificados_https import configurar_certificados_https

configurar_certificados_https()

import psycopg2

from locapredict_db import get_table_columns, load_db_config
from locapredict_log import get_logger, setup_locapredict_logging
from alertas_slack import enviar_alertas_slack_guardiao_saude_cliente, load_slack_settings


def resolver_caminho_configuracao() -> str:
    """Localiza o `config.ini` (variáveis de ambiente ou caminhos relativos a este script)."""
    caminho = (os.environ.get("CAMINHO_ARQUIVO_CONFIGURACAO") or os.environ.get("CONFIG_PATH") or "").strip()
    if caminho and os.path.isfile(caminho):
        return caminho
    pasta_script = os.path.dirname(os.path.abspath(__file__))
    for rel in ("../config.ini", "../../config.ini", "./config.ini"):
        candidato = os.path.abspath(os.path.join(pasta_script, rel))
        if os.path.isfile(candidato):
            return candidato
    raise FileNotFoundError("config.ini não encontrado.")


def _ler_booleano_secao(secao: configparser.SectionProxy, chave_pt: str, chave_en: str, padrao: bool) -> bool:
    """Lê booleano: tenta a chave em português e, se não houver, a equivalente em inglês."""
    for chave in (chave_pt, chave_en):
        if secao.has_option(chave):
            try:
                return secao.getboolean(chave)
            except ValueError:
                return padrao
    return padrao


def _ler_inteiro_secao(
    secao: configparser.SectionProxy,
    chave_pt: str,
    chave_en: str,
    padrao: int,
    *,
    minimo: Optional[int] = None,
    maximo: Optional[int] = None,
) -> int:
    """Lê inteiro com fallback PT/EN e limita ao intervalo opcional (mínimo/máximo)."""
    for chave in (chave_pt, chave_en):
        if secao.has_option(chave):
            try:
                v = secao.getint(chave)
                break
            except ValueError:
                continue
    else:
        v = padrao
    if minimo is not None:
        v = max(minimo, v)
    if maximo is not None:
        v = min(maximo, v)
    return v


def carregar_configuracao_guardiao(caminho_config: str) -> dict:
    """
    Lê a seção do Guardião no INI (`[customer_health_guardian]`). Se ausente, usa valores padrão.

    O identificador da seção no arquivo permanece em inglês para não quebrar configs já implantadas.
    """
    padrao = {
        "habilitado": True,
        "meses_janela": 6,
        "minimo_incidentes": 5,
        "gravar_snapshots": True,
        "alertas_slack": True,
        "apenas_incidentes_abertos": False,
        "max_linhas_slack": 25,
    }
    parser = configparser.ConfigParser()
    if not os.path.isfile(caminho_config):
        return padrao
    parser.read(caminho_config)
    if "customer_health_guardian" not in parser:
        return padrao
    secao = parser["customer_health_guardian"]
    return {
        "habilitado": _ler_booleano_secao(secao, "habilitado", "enabled", True),
        "meses_janela": _ler_inteiro_secao(secao, "meses_janela", "window_months", 6, minimo=1, maximo=24),
        "minimo_incidentes": _ler_inteiro_secao(secao, "minimo_incidentes", "min_incidents", 5, minimo=1),
        "gravar_snapshots": _ler_booleano_secao(secao, "gravar_snapshots", "persist_snapshots", True),
        "alertas_slack": _ler_booleano_secao(secao, "alertas_slack", "slack_alerts", True),
        "apenas_incidentes_abertos": _ler_booleano_secao(
            secao, "apenas_incidentes_abertos", "only_open_incidents", False
        ),
        "max_linhas_slack": _ler_inteiro_secao(
            secao, "max_linhas_slack", "slack_max_rows", 25, minimo=5, maximo=50
        ),
    }


def _expressao_sql_coluna_atualizacoes(colunas: set) -> str:
    """Devolve o nome da coluna de atualizações no SQL ou o literal 0 se não existir no schema."""
    if "total_atualizacoes" in colunas:
        return "total_atualizacoes"
    if "atualizacoes" in colunas:
        return "atualizacoes"
    return "0"


def _expressao_sql_normalizar_login_cliente(coluna: str = "login_cliente") -> str:
    """
    Fragmento PostgreSQL que devolve um identificador canônico para agrupar o mesmo cliente.

    Ordem de precedência:

    1. Parâmetro ``ficha=`` (URLs intranet / CGI), apenas os dígitos.
    2. Padrão ``(Cód. 123)`` ou ``(Cod. 123)`` (com ou sem acento em Cód).
    3. Valor só com dígitos (após trim) — código do cliente.
    4. URL ``http(s)://...`` sem match anterior — último ``=`` seguido de dígitos até o fim da string.
    5. Demais textos — minúsculas e remoção de caracteres que não sejam letras ou números (ex.: ``mzviagens``).
    """
    c = coluna
    return f"""NULLIF(
  TRIM(
    COALESCE(
      (regexp_match(TRIM({c}), '(?i)ficha=(\\d+)'))[1],
      (regexp_match(TRIM({c}), '(?i)\\(\\s*C[oó]d\\.?\\s*(\\d+)\\s*\\)'))[1],
      CASE WHEN TRIM({c}) ~ '^\\d+$' THEN TRIM({c}) END,
      CASE
        WHEN TRIM({c}) ~* '^https?://'
        THEN (regexp_match(TRIM({c}), '.*=(\\d+)\\s*$'))[1]
      END,
      CASE
        WHEN TRIM({c}) !~* '^https?://'
        THEN NULLIF(lower(regexp_replace(TRIM({c}), '[^a-zA-Z0-9]', '', 'g')), '')
      END
    )
  ),
  ''
)"""


def montar_sql_recorrencia_guardiao(expr_atualizacoes: str, meses: int, apenas_abertos: bool) -> str:
    """
    Monta o SQL da janela temporal: frequência por login canônico + produto, agregados e filtro pelo limiar.

    O login é normalizado na CTE ``linhas_origem``; linhas sem identificador válido após normalização são ignoradas.

    O placeholder %s na execução corresponde ao número mínimo de incidentes configurado.
    """
    esforco = f"COALESCE(({expr_atualizacoes})::numeric, 0)"
    filtro_abertos = ""
    if apenas_abertos:
        filtro_abertos = "AND status NOT IN ('Cancelled', 'Resolved', 'Closed')"
    norm = _expressao_sql_normalizar_login_cliente("login_cliente")
    return f"""
WITH linhas_origem AS (
    SELECT
        login_cliente,
        produto,
        numero,
        data_abertura,
        categoria,
        {esforco} AS esforco_inc,
        {norm} AS login_normalizado
    FROM lwsa.service_now_incidentes
    WHERE
        data_abertura >= NOW() - INTERVAL '{meses} months'
        AND login_cliente IS NOT NULL
        AND TRIM(login_cliente) <> ''
        {filtro_abertos}
),
base AS (
    SELECT
        login_normalizado AS login_cliente,
        produto,
        numero,
        data_abertura,
        categoria,
        esforco_inc,
        COUNT(*) OVER (PARTITION BY login_normalizado, produto) AS freq_cliente_produto
    FROM linhas_origem
    WHERE login_normalizado IS NOT NULL AND TRIM(login_normalizado) <> ''
)
SELECT
    login_cliente,
    produto,
    MAX(freq_cliente_produto)::bigint AS total_inc_6meses,
    COUNT(DISTINCT NULLIF(TRIM(COALESCE(categoria::text, '')), '')) AS diversidade_problemas,
    MAX(data_abertura) AS ultimo_contato,
    ROUND(AVG(esforco_inc), 2) AS media_esforco_cliente
FROM base
GROUP BY login_cliente, produto
HAVING MAX(freq_cliente_produto) >= %s
ORDER BY total_inc_6meses DESC, login_cliente ASC
"""


def buscar_pares_login_produto_acima_limiar(
    conexao_banco, meses_janela: int, min_inc: int, apenas_abertos: bool
) -> list:
    """Executa a consulta de recorrência e retorna uma lista de dicionários (um por par login × produto)."""
    colunas = get_table_columns(conexao_banco, "lwsa", "service_now_incidentes")
    if "login_cliente" not in colunas:
        raise RuntimeError("Tabela service_now_incidentes sem coluna login_cliente.")
    expr = _expressao_sql_coluna_atualizacoes(colunas)
    sql = montar_sql_recorrencia_guardiao(expr, meses_janela, apenas_abertos)
    registrador = get_logger()
    registrador.info(
        "Guardião da Saúde do Cliente — consulta de recorrência (login_cliente normalizado: ficha=, Cód., "
        "URL, só dígitos ou slug): meses_janela=%s | minimo_incidentes=%s | "
        "apenas_incidentes_abertos=%s | coluna_atualizacoes=%s",
        meses_janela,
        min_inc,
        apenas_abertos,
        expr or "0",
    )
    with conexao_banco.cursor() as cur:
        cur.execute(sql, (min_inc,))
        nomes = [d.name for d in cur.description]
        linhas = [dict(zip(nomes, row)) for row in cur.fetchall()]
    registrador.info(
        "Guardião da Saúde do Cliente — %s par(es) login_cliente+produto acima do limiar.", len(linhas)
    )
    return linhas


def gravar_snapshots_historico_guardiao(conexao_banco, registros: list) -> None:
    """
    Persiste cada par encontrado na tabela de histórico do Guardião.

    Nome físico da tabela no PostgreSQL: `lwsa.customer_health_guardian_snapshots` (legado).
    """
    if not registros:
        return
    registrador = get_logger()
    sql = """
    INSERT INTO lwsa.customer_health_guardian_snapshots
        (login_cliente, produto, total_inc_janela, diversidade_problemas, ultimo_contato, media_esforco_cliente)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    valores = [
        (
            r["login_cliente"],
            r["produto"],
            int(r["total_inc_6meses"]),
            int(r["diversidade_problemas"]),
            r["ultimo_contato"],
            r["media_esforco_cliente"],
        )
        for r in registros
    ]
    try:
        with conexao_banco.cursor() as cur:
            cur.executemany(sql, valores)
        conexao_banco.commit()
        registrador.info(
            "Guardião da Saúde do Cliente — %s registro(s) gravados na tabela de snapshots.", len(valores)
        )
    except psycopg2.Error as e:
        conexao_banco.rollback()
        if getattr(e, "pgcode", None) == "42P01":
            registrador.warning(
                "Guardião da Saúde do Cliente — tabela de snapshots inexistente no schema lwsa; "
                "execute o DDL em queries.sql ou desative gravar_snapshots."
            )
        else:
            registrador.exception("Guardião da Saúde do Cliente — falha ao gravar snapshots: %s", e)


def executar_guardiao_saude_cliente() -> int:
    """
    Fluxo completo: log em arquivo → configuração → banco → consulta → snapshots opcionais → Slack opcional.

    Retorna 0 em sucesso e 1 em erro fatal (detalhes no arquivo de log).
    """
    setup_locapredict_logging()
    registrador = get_logger()
    registrador.info("Início da aplicação Guardião da Saúde do Cliente.")
    lista_resultados: list = []

    try:
        caminho_config = resolver_caminho_configuracao()
        cfg = carregar_configuracao_guardiao(caminho_config)
        if not cfg["habilitado"]:
            registrador.info("Guardião da Saúde do Cliente desligado (habilitado=false).")
            print("Guardião da Saúde do Cliente: desabilitado na configuração.")
            return 0

        registrador.info("Arquivo de configuração: %s", os.path.abspath(caminho_config))
        db_params = load_db_config(caminho_config)

        with psycopg2.connect(**db_params) as conexao_banco:
            lista_resultados = buscar_pares_login_produto_acima_limiar(
                conexao_banco,
                meses_janela=cfg["meses_janela"],
                min_inc=cfg["minimo_incidentes"],
                apenas_abertos=cfg["apenas_incidentes_abertos"],
            )
            if lista_resultados and cfg["gravar_snapshots"]:
                gravar_snapshots_historico_guardiao(conexao_banco, lista_resultados)

        if not lista_resultados:
            print(
                f"Guardião da Saúde do Cliente: nenhum par acima do limiar "
                f"({cfg['minimo_incidentes']}+ INC em {cfg['meses_janela']} meses)."
            )
            registrador.info("Guardião da Saúde do Cliente — nenhum resultado acima do limiar.")
        else:
            print(
                f"Guardião da Saúde do Cliente: {len(lista_resultados)} par(es) login×produto "
                "com alta recorrência."
            )
            if cfg["alertas_slack"]:
                slack_cfg, motivo = load_slack_settings(caminho_config)
                if slack_cfg:
                    enviar_alertas_slack_guardiao_saude_cliente(
                        slack_cfg,
                        lista_resultados,
                        meses_janela=cfg["meses_janela"],
                        minimo_incidentes=cfg["minimo_incidentes"],
                        max_linhas_slack=cfg["max_linhas_slack"],
                    )
                else:
                    print(f"Guardião da Saúde do Cliente: Slack não enviado — {motivo}")
                    registrador.warning("Guardião da Saúde do Cliente — Slack omitido: %s", motivo)
            else:
                registrador.info("Guardião da Saúde do Cliente — alertas_slack=false; sem envio.")

    except Exception as e:
        registrador.exception("Guardião da Saúde do Cliente — erro fatal: %s", e)
        print(f"Guardião da Saúde do Cliente: erro — {e}", file=sys.stderr)
        return 1
    finally:
        registrador.info("Fim da aplicação Guardião da Saúde do Cliente.")

    return 0


if __name__ == "__main__":
    sys.exit(executar_guardiao_saude_cliente())
