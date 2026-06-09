# =============================================================================
# LocaPredict — motor prescritivo (clusterização semântica de incidentes).
# =============================================================================
# Este arquivo: certificados HTTPS (módulo compartilhado), PostgreSQL, embeddings,
# HDBSCAN, scores, gravação de insights e Slack opcional.
# =============================================================================
from __future__ import annotations

import logging
import re
import sys
import warnings
import threading
from collections import Counter
from typing import Optional

from certificados_https import configurar_certificados_https

# Antes de libs que usam HTTPS (ex.: download do modelo Hugging Face)
configurar_certificados_https()

# --- Bibliotecas de dados, ML e integração ---
import numpy as np
import psycopg2
import hdbscan
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from locapredict_db import get_table_columns, load_db_config, resolve_config_path
from locapredict_log import get_logger, setup_locapredict_logging
from alertas_slack import load_slack_settings, post_insight_alerts
from guardiao_saude_cliente import executar_guardiao_saude_cliente
from prescricao_prb import prescrever_acao_prb


def _quiet_nlp_loggers():
    """Reduz ruído no console (logs INFO das libs de NLP e aviso do Hugging Face Hub)."""
    for nome in ("sentence_transformers", "transformers", "huggingface_hub"):
        logging.getLogger(nome).setLevel(logging.ERROR)
    warnings.filterwarnings(
        "ignore",
        message=r".*unauthenticated requests to the HF Hub.*",
        category=UserWarning,
    )


_quiet_nlp_loggers()

# Stop-words em PT-BR removidas antes do embedding para enfatizar termos discriminativos
PALAVRAS_VAZIAS_PORTUGUES = {
    "a", "ao", "aos", "aquela", "aquelas", "aquele", "aqueles", "aquilo", "as", "ate",
    "com", "como", "da", "das", "de", "dela", "delas", "dele", "deles", "depois", "do",
    "dos", "e", "ela", "elas", "ele", "eles", "em", "entre", "era", "eram", "essa",
    "essas", "esse", "esses", "esta", "estao", "estas", "estava", "estavam", "este",
    "estes", "eu", "foi", "foram", "ha", "isso", "isto", "ja", "la", "lhe", "lhes",
    "mais", "mas", "me", "mesmo", "meu", "meus", "minha", "minhas", "muito", "na",
    "nas", "nem", "no", "nos", "nossa", "nossas", "nosso", "nossos", "num", "numa",
    "o", "os", "ou", "para", "pela", "pelas", "pelo", "pelos", "por", "qual", "quando",
    "que", "quem", "se", "sem", "ser", "seu", "seus", "sua", "suas", "tambem", "te",
    "tem", "tendo", "tenho", "ter", "teu", "teus", "tinha", "tinham", "tu", "um", "uma",
    "voce", "voces",
}


def remover_stopwords_pt(texto_entrada) -> str:
    """Normaliza texto, remove stop-words em português e devolve string pronta para embedding."""
    if not texto_entrada or not isinstance(texto_entrada, str):
        return ""
    texto = texto_entrada.strip().lower()
    if not texto:
        return ""
    texto = re.sub(r"\s+", " ", texto)
    tokens = [t for t in texto.split(" ") if t and t not in PALAVRAS_VAZIAS_PORTUGUES]
    if not tokens:
        return texto
    return " ".join(tokens)


def texto_para_embedding(inc: dict) -> str:
    """Junta descrição tratada com rótulos de negócio (produto, grupo, categoria) para o vetor semântico."""
    if not inc or not isinstance(inc, dict):
        return ""
    desc = remover_stopwords_pt(inc.get("desc_clean"))
    produto = str(inc.get("produto") or "").strip()
    grupo = str(inc.get("grupo_designado") or "").strip()
    categoria = str(inc.get("categoria") or "").strip()
    partes = [desc]
    if produto:
        partes.append(f"produto:{produto}")
    if grupo:
        partes.append(f"grupo:{grupo}")
    if categoria:
        partes.append(f"categoria:{categoria}")
    texto_final = " | ".join(partes)
    return texto_final.strip()


def _mean_pairwise_similarity(embeddings_cluster: np.ndarray) -> float:
    """Coerência semântica do cluster: média da similaridade de cossenos fora da diagonal."""
    if embeddings_cluster is None or embeddings_cluster.size == 0:
        return 0.0
    n = embeddings_cluster.shape[0]
    if n < 2:
        return 1.0
    sim = cosine_similarity(embeddings_cluster)
    return float((sim.sum() - n) / (n * n - n))


# Recorrência por servidor (Service Operation): pesos e thresholds
_BONUS_SCORE_SERVIDOR_RECORRENTE = 0.15
_MIN_INCS_PARA_BONUS_SERVIDOR = 2
_MIN_INCS_PARA_ACAO_SERVIDOR = 3


def _calcular_recorrencia_servidor(cluster_data: list[dict]) -> tuple[float, Optional[str]]:
    """
    Analisa concentração de incidentes por servidor no cluster.

    Retorna (bonus_severidade, servidor_concentrador):
      - bonus = +0.15 se o servidor mais frequente aparece em >= 2 INCs do cluster
        (sinal de recorrência intra-cluster — mesmo ativo físico afetado várias vezes).
      - servidor_concentrador = nome do servidor com > 3 INCs (gatilho da sugestão
        operacional dedicada), ou None se nenhum servidor concentra esse volume.

    Incidentes sem `servidor` preenchido são ignorados.
    """
    servidores = [
        str(inc.get("servidor")).strip()
        for inc in cluster_data
        if inc.get("servidor") and str(inc.get("servidor")).strip()
    ]
    if not servidores:
        return 0.0, None
    servidor_top, ocorrencias = Counter(servidores).most_common(1)[0]
    bonus = _BONUS_SCORE_SERVIDOR_RECORRENTE if ocorrencias >= _MIN_INCS_PARA_BONUS_SERVIDOR else 0.0
    concentrador = servidor_top if ocorrencias > _MIN_INCS_PARA_ACAO_SERVIDOR else None
    return bonus, concentrador


def score_cluster(
    cluster_data: list[dict],
    embeddings_cluster: np.ndarray,
    volume_produto: int,
) -> tuple[float, float]:
    """
    Calcula score_severidade e ineficiencia_score conforme fórmulas do README.

    score_severidade = min(1, 0.4*mean_sim + 0.3*(cluster_size/volume_produto)
                              + 0.3*fator_esforco + bonus_servidor)
        fator_esforco   = min(1, log1p(soma_atualizacoes_cluster) / 5)
        bonus_servidor  = +0.15 quando o mesmo servidor físico aparece em >= 2 INCs
                          (recorrência intra-cluster sinalizada pelo Service Operation).

    ineficiencia_score = min(1, fator_interacoes * fator_lentidao)
        fator_interacoes = min(1, log1p(atualizacoes_medias) / 3)
        fator_lentidao   = min(1, log1p(tempo_medio_resolucao) / 5)
    """
    if not cluster_data:
        return 0.0, 0.0

    n = len(cluster_data)
    mean_sim = _mean_pairwise_similarity(embeddings_cluster)

    soma_atualizacoes = sum(float(inc.get("total_atualizacoes") or 0) for inc in cluster_data)
    fator_esforco = min(1.0, float(np.log1p(soma_atualizacoes)) / 5.0)
    fator_volume = min(1.0, n / float(volume_produto)) if volume_produto and volume_produto > 0 else 0.0

    bonus_servidor, _ = _calcular_recorrencia_servidor(cluster_data)
    score_severidade = min(
        1.0,
        0.4 * mean_sim + 0.3 * fator_volume + 0.3 * fator_esforco + bonus_servidor,
    )

    atualizacoes_medias = soma_atualizacoes / n if n else 0.0
    tempos = [float(inc.get("tempo_medio_resolucao") or 0) for inc in cluster_data]
    tempo_medio = (sum(tempos) / len(tempos)) if tempos else 0.0

    fator_interacoes = min(1.0, float(np.log1p(atualizacoes_medias)) / 3.0)
    fator_lentidao = min(1.0, float(np.log1p(tempo_medio)) / 5.0)
    ineficiencia_score = min(1.0, fator_interacoes * fator_lentidao)

    return score_severidade, ineficiencia_score


def build_cluster_label(cluster_data: list[dict], produto: str) -> str:
    """
    Cria rótulo descritivo do cluster usando palavras-chave frequentes.

    Recebe `produto` já resolvido pelo chamador (tipicamente o produto majoritário
    do cluster), para manter consistência com `produto_afetado` persistido nos insights.
    Filtra stop-words PT-BR, tokens curtos (<=2 chars) e numéricos puros antes de
    escolher os 3 termos mais frequentes — evita rótulos dominados por conectivos.
    """
    if not cluster_data:
        return "Cluster vazio"

    termos: list[str] = []
    for inc in cluster_data:
        desc = inc.get("desc_clean", "") or ""
        for token in desc.split():
            if len(token) <= 2:
                continue
            if token in PALAVRAS_VAZIAS_PORTUGUES:
                continue
            if token.isdigit():
                continue
            termos.append(token)

    freq = Counter(termos)
    top_termos = [t for t, _ in freq.most_common(3)]
    produto_final = produto or "Desconhecido"
    return f"Incidentes em {produto_final}: {' '.join(top_termos)}".rstrip(": ").rstrip()


# Termos para detecção de "sem contorno" no SQL histórico (espelham _TERMOS_SEM_CONTORNO
# de prescricao_prb.py — se mudar lá, atualizar aqui também).
_TERMOS_SQL_SEM_CONTORNO = [
    "%sem contorno%",
    "%sem solucao%",
    "%sem solução%",
    "%nenhum contorno%",
    "%no workaround%",
]


def contar_incidentes_historicos_por_produto(
    conexao_banco, produto: str, dias: int = 30
) -> tuple[int, int]:
    """
    Conta INCs de um produto nos últimos N dias separando por presença de
    indicação de ausência de solução de contorno.

    Retorna (total_com_contorno, total_sem_contorno).

    Heurística por substring em descricao_curta (case-insensitive) — pode ter
    falsos positivos/negativos. Os termos devem ficar sincronizados com
    _TERMOS_SEM_CONTORNO em prescricao_prb.py.

    SQL compatível com PostgreSQL 9.2 (usa SUM(CASE) em vez de FILTER).
    """
    sql = """
        SELECT
            SUM(CASE WHEN LOWER(descricao_curta) LIKE ANY (%s) THEN 0 ELSE 1 END) AS com_contorno,
            SUM(CASE WHEN LOWER(descricao_curta) LIKE ANY (%s) THEN 1 ELSE 0 END) AS sem_contorno
        FROM lwsa.service_now_incidentes
        WHERE data_abertura >= NOW() - (INTERVAL '1 day' * %s)
          AND produto = %s
          AND descricao_curta IS NOT NULL
    """
    with conexao_banco.cursor() as cur:
        cur.execute(sql, (_TERMOS_SQL_SEM_CONTORNO, _TERMOS_SQL_SEM_CONTORNO, dias, produto))
        row = cur.fetchone()
        if not row:
            return 0, 0
        return int(row[0] or 0), int(row[1] or 0)


def insert_insights(conexao_banco, tuplas: list):
    """Persiste linhas em lwsa.locapredict_insights (uma tupla por cluster)."""
    sql = """INSERT INTO lwsa.locapredict_insights
        (cluster_nome, quantidade_inc_afetados, produto_afetado, score_severidade, ineficiencia_score, sugestao_acao, incidentes_relacionados, servidores_afetados)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""
    with conexao_banco.cursor() as cur:
        cur.executemany(sql, tuplas)
    conexao_banco.commit()


def build_embeddings(incidentes: list[dict]) -> np.ndarray:
    """
    Gera embeddings com texto enriquecido (desc + produto + grupo + categoria, sem stop-words).

    Vetores são L2-normalizados: distância euclidiana entre vetores unitários é equivalente
    a distância de cosseno (||u-v||² = 2·(1 - cos(u,v))), então o HDBSCAN com metric="euclidean"
    passa a refletir similaridade semântica em vez de magnitude.
    """
    if not incidentes:
        return np.array([])
    textos = [texto_para_embedding(inc) for inc in incidentes]
    modelo = get_modelo()
    return modelo.encode(textos, normalize_embeddings=True)


def cluster_incidentes(
    embeddings: np.ndarray, min_cluster_size: int = 3
) -> tuple[np.ndarray, Optional[hdbscan.HDBSCAN]]:
    """Aplica HDBSCAN nos embeddings para clusterizar incidentes (params alinhados com README)."""
    if embeddings is None or embeddings.size == 0:
        return np.array([]), None

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=1,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    labels = clusterer.fit_predict(embeddings)
    return labels, clusterer


# Cache global do modelo (evita recarregar a cada execução dentro do mesmo processo)
_modelo_embeddings = None
_modelo_lock = threading.Lock()


def get_modelo():
    """Carrega o SentenceTransformer multilíngue uma única vez (singleton em memória, thread-safe)."""
    global _modelo_embeddings
    with _modelo_lock:
        if _modelo_embeddings is None:
            print("Carregando modelo de embeddings multilíngue...")
            _modelo_embeddings = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            print("Modelo de embeddings carregado com sucesso.")
    return _modelo_embeddings


def build_select_incidentes_sql(expressao_tempo_sql: str, nome_coluna_atualizacoes: Optional[str]) -> str:
    """
    Monta o SQL dos incidentes das últimas 24h (não cancelados/encerrados).

    Inclui volume por produto (para normalizar o score) e usa expressões dinâmicas
    para tempo de resolução e contagem de atualizações conforme colunas existentes.

    Otimizações para grandes volumes:
    - Recomenda índices em: data_abertura, produto, status, descricao_curta.
    - CTEs são eficientes, mas monitore plano de execução com EXPLAIN ANALYZE.
    """
    expr_atual = nome_coluna_atualizacoes if nome_coluna_atualizacoes else "0"
    return f"""
-- Índices recomendados para otimização: CREATE INDEX ON lwsa.service_now_incidentes (data_abertura); CREATE INDEX ON lwsa.service_now_incidentes (produto); CREATE INDEX ON lwsa.service_now_incidentes (status);
WITH base_incidentes AS (
    SELECT
        numero,
        produto,
        LOWER(TRIM(regexp_replace(descricao_curta, '[^a-zA-Z0-9\\s]', '', 'g'))) AS desc_clean,
        data_abertura,
        prioridade,
        grupo_designado,
        servidor,
        login_cliente,
        categoria,
        subcategoria,
        {expressao_tempo_sql} AS tempo_medio_resolucao,
        {expr_atual} AS total_atualizacoes,
        EXTRACT(HOUR FROM data_abertura) AS hora_abertura,
        EXTRACT(DOW FROM data_abertura) AS dia_semana
    FROM
        lwsa.service_now_incidentes
    WHERE
        data_abertura >= NOW() - INTERVAL '24 hours'
        AND status NOT IN ('Cancelled', 'Resolved', 'Closed')
        AND descricao_curta IS NOT NULL
),
contagem_por_produto AS (
    SELECT
        produto,
        COUNT(*) AS volume_atual
    FROM base_incidentes
    GROUP BY produto
)
SELECT
    b.numero,
    b.produto,
    b.desc_clean,
    b.data_abertura,
    b.prioridade,
    b.grupo_designado,
    b.servidor,
    b.login_cliente,
    b.categoria,
    b.subcategoria,
    b.tempo_medio_resolucao,
    b.total_atualizacoes,
    c.volume_atual
FROM
    base_incidentes b
JOIN
    contagem_por_produto c ON b.produto = c.produto
ORDER BY
    b.data_abertura DESC;
"""


def fetch_incidentes(conexao_banco):
    """
    Consulta incidentes recentes: detecta colunas reais no banco e monta expressões SQL compatíveis.

    Retorna lista de dicts (uma linha por incidente) com aliases padronizados.
    """
    registrador = get_logger()
    colunas = get_table_columns(conexao_banco, "lwsa", "service_now_incidentes")

    # Escolhe como obter horas de resolução (coluna direta, data_resolvido ou idade da INC)
    if "tempo_medio_resolucao" in colunas:
        expressao_tempo = "tempo_medio_resolucao"
        msg_tempo = "LocaPredict: usando coluna de tempo 'tempo_medio_resolucao'."
    elif "data_resolvido" in colunas:
        expressao_tempo = "EXTRACT(EPOCH FROM (COALESCE(data_resolvido, NOW()) - data_abertura)) / 3600.0"
        msg_tempo = (
            "LocaPredict: coluna 'tempo_medio_resolucao' ausente; "
            "calculando tempo por (COALESCE(data_resolvido, NOW()) - data_abertura)."
        )
    else:
        expressao_tempo = "EXTRACT(EPOCH FROM (NOW() - data_abertura)) / 3600.0"
        msg_tempo = (
            "LocaPredict: coluna 'tempo_medio_resolucao' ausente; usando fallback por idade da INC."
        )

    # Coluna de interações/atualizações (impacta ineficiencia_score)
    if "total_atualizacoes" in colunas:
        col_atual = "total_atualizacoes"
    elif "atualizacoes" in colunas:
        col_atual = "atualizacoes"
    else:
        col_atual = None
        registrador.warning(
            "Schema DB: nenhuma coluna de atualizações encontrada (total_atualizacoes ou atualizacoes). "
            "Usando 0 para scores. Considere atualizar o schema ServiceNow."
        )

    print(msg_tempo)
    registrador.info("Origem incidentes: %s", msg_tempo)

    if col_atual:
        msg_atual = f"usando coluna de atualizacoes '{col_atual}'."
        print(f"LocaPredict: {msg_atual}")
        registrador.info("Origem incidentes: %s", msg_atual)
    else:
        msg_atual = "coluna de atualizacoes ausente; usando 0 para score de ineficiencia."
        print(f"LocaPredict: {msg_atual}")
        registrador.warning("Origem incidentes: %s", msg_atual)

    sql = build_select_incidentes_sql(expressao_tempo, col_atual)
    registrador.info(
        "Executando consulta de incidentes (24h, ativos): tempo_expr=%r atualizacoes=%r",
        expressao_tempo,
        col_atual or "literal 0",
    )
    with conexao_banco.cursor() as cur:
        cur.execute(sql)
        linhas = cur.fetchall()
        nomes = [d.name for d in cur.description]
    lista = [dict(zip(nomes, linha)) for linha in linhas]
    registrador.info("Consulta incidentes concluída: %s linha(s) retornada(s).", len(lista))
    return lista


def _produto_majoritario_e_volume(cluster_data: list[dict]) -> tuple[str, int]:
    """
    Identifica o produto mais frequente do cluster e seu volume_atual correspondente.

    HDBSCAN pode misturar produtos no mesmo cluster; o denominador do score precisa
    ser o volume daquele produto específico, não do primeiro incidente arbitrário.
    """
    contagem = Counter(inc.get("produto", "Desconhecido") for inc in cluster_data)
    produto_top, _ = contagem.most_common(1)[0]
    volume = next(
        (int(inc.get("volume_atual") or 1) for inc in cluster_data if inc.get("produto") == produto_top),
        1,
    )
    return produto_top, max(1, volume)


def main():
    """Ponto de entrada: configura log, pré-carrega modelo e executa pipeline."""
    setup_locapredict_logging()
    registrador = get_logger()
    registrador.info("Início da execução LocaPredict.")
    try:
        # Pré-carregamento do modelo
        get_modelo()
        caminho_config = resolve_config_path()
        config = load_db_config(caminho_config)
        with psycopg2.connect(**config) as conexao_banco:
            # Buscar incidentes
            incidentes = fetch_incidentes(conexao_banco)
            if not incidentes:
                registrador.info("Nenhum incidente encontrado para análise.")
                return

            # Gerar embeddings (texto enriquecido + stop-words removidas)
            embeddings = build_embeddings(incidentes)

            # Clusterizar (min_cluster_size=3, min_samples=1 — alinhado com README)
            labels, _ = cluster_incidentes(embeddings)

            # Cache de contagem histórica por produto (F3) — várias clusters podem
            # compartilhar o mesmo produto majoritário; evita consultas duplicadas.
            JANELA_HISTORICA_DIAS = 30
            cache_historico: dict[str, tuple[int, int]] = {}

            # Gerar insights por cluster
            insights = []
            for cluster_id in sorted({int(lbl) for lbl in labels}):
                if cluster_id == -1:  # Outliers
                    continue
                indices = [i for i, lbl in enumerate(labels) if lbl == cluster_id]
                cluster_data = [incidentes[i] for i in indices]
                if not cluster_data:
                    continue

                embeddings_cluster = embeddings[indices]
                produto, volume_produto = _produto_majoritario_e_volume(cluster_data)
                severidade, ineficiencia = score_cluster(cluster_data, embeddings_cluster, volume_produto)
                label = build_cluster_label(cluster_data, produto)

                # Servidores distintos do cluster (ordenados para resultado determinístico).
                # `servidor` pode ser None/vazio quando o ServiceNow não preenche — filtramos esses casos.
                servidores_afetados = sorted({
                    str(inc.get("servidor")).strip()
                    for inc in cluster_data
                    if inc.get("servidor") and str(inc.get("servidor")).strip()
                })

                # Volumetria histórica por produto (F3): conta INCs com/sem contorno
                # nos últimos JANELA_HISTORICA_DIAS dias. Cacheada por produto.
                if produto not in cache_historico:
                    try:
                        cache_historico[produto] = contar_incidentes_historicos_por_produto(
                            conexao_banco, produto, dias=JANELA_HISTORICA_DIAS
                        )
                    except Exception:
                        # Falha na consulta histórica não deve derrubar o pipeline;
                        # cai em (0,0) e a regra P-level age sem esse sinal.
                        registrador.exception(
                            "Falha ao contar histórico de '%s' — usando (0,0).", produto
                        )
                        cache_historico[produto] = (0, 0)
                total_com_contorno, total_sem_contorno = cache_historico[produto]

                prescricao = prescrever_acao_prb(
                    cluster_data=cluster_data,
                    score_severidade=severidade,
                    ineficiencia_score=ineficiencia,
                    produto=produto,
                    servidores=servidores_afetados,
                    total_historico_com_contorno=total_com_contorno,
                    total_historico_sem_contorno=total_sem_contorno,
                    janela_historica_dias=JANELA_HISTORICA_DIAS,
                )

                # Sinalização operacional do Service Operation: se um único servidor concentra
                # > 3 INCs do cluster, a sugestão dedicada substitui o texto da prescrição PRB
                # (urgência/decisão/evidências permanecem — o redirecionamento é só na ação).
                _, servidor_concentrador = _calcular_recorrencia_servidor(cluster_data)
                if servidor_concentrador:
                    acao_anterior = prescricao.acao
                    prescricao.acao = (
                        f"Solicitar análise de desempenho/PRB para o servidor específico: "
                        f"{servidor_concentrador}"
                    )
                    registrador.info(
                        "Cluster %s — acao sobrescrita por concentração no servidor %s: %r -> %r",
                        cluster_id,
                        servidor_concentrador,
                        acao_anterior,
                        prescricao.acao,
                    )

                registrador.info(
                    "Cluster %s — %s (urg=%s, OLA<=%sh) abrir_prb=%s composto=%.3f grupo=%s upgrade=%s",
                    cluster_id,
                    prescricao.prioridade,
                    prescricao.urgencia,
                    prescricao.ola_target_horas,
                    prescricao.deve_abrir_prb,
                    prescricao.score_composto,
                    prescricao.grupo_destino,
                    prescricao.upgrade_aplicado or "—",
                )

                # 9 elementos: os 8 primeiros vão para o banco (insert_insights faz [:8]);
                # o 9º (PrescricaoPRB) viaja só até o Slack para o alerta rico.
                insights.append((
                    label,
                    len(cluster_data),
                    produto,
                    severidade,
                    ineficiencia,
                    prescricao.acao,
                    [str(inc.get("numero")) for inc in cluster_data],
                    servidores_afetados,
                    prescricao,
                ))

            # Salvar insights
            if insights:
                # O 9º elemento (PrescricaoPRB) é cortado — só os 8 primeiros são persistidos.
                insert_insights(conexao_banco, [row[:8] for row in insights])
                registrador.info("Persistidos %s insights no banco.", len(insights))

                # Notificar Slack
                slack_config, slack_msg = load_slack_settings(caminho_config)
                if slack_config:
                    post_insight_alerts(slack_config, insights)
                    registrador.info("Notificações Slack enviadas.")
                elif slack_msg:
                    registrador.warning("Slack desabilitado: %s", slack_msg)
            else:
                registrador.info("Nenhum insight gerado.")
    except Exception:
        registrador.exception("Erro na execução LocaPredict.")
        raise
    finally:
        registrador.info("Fim da execução LocaPredict.")


if __name__ == "__main__":
    # main() levanta exceção em caso de erro fatal — nesse caso, Python
    # interrompe aqui e o Guardião não roda (comportamento desejado:
    # só conferir recorrência se o pipeline principal tiver sucesso).
    main()
    sys.exit(executar_guardiao_saude_cliente())
