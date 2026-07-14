"""
Análise de Detratores WOZ — Comparativo Mensal (Locaweb)
=========================================================

Identifica comentários NPS que mencionam atendimento automatizado/robótico
(Woz, robô, bot, automático, etc.) e compara entre dois meses.
Os comentários individuais são gravados na tabela lw_octadesk.woz_comentarios.

Uso:
    python analise_woz_detratores.py                                          # auto: últimos 2 meses completos
    python analise_woz_detratores.py --ano1 2026 --mes1 5 --ano2 2026 --mes2 6  # Mai/2026 vs Jun/2026
    python analise_woz_detratores.py --inicio1 2026-05-01 --fim1 2026-05-31 \\
                                     --inicio2 2026-06-01 --fim2 2026-06-30
"""

import argparse
import calendar
import json
import logging
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import psycopg2

from config import config
from conecta_banco import get_psycopg2_connection

logger = logging.getLogger('nps_monitor.woz_detratores')
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

OUTPUT_DIR = Path(__file__).parent / 'woz_detratores'
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Termos que remetem a atendimento não-humano / automatizado
# ---------------------------------------------------------------------------
TERMOS_WOZ = [
    r'rob[oô]',
    r'robotizado[as]?',
    r'autom[aá]tic[oa][as]?',
    r'automatizado[as]?',
    r'automatiza[cç][aã]o',
    r'\bwoz\b',
    r'\bbot\b',
    r'\bchatbot\b',
    r'm[aá]quina',
    r'atendimento virtual',
    r'atendente virtual',
    r'n[aã]o [eé] humano',
    r'sem humano',
    r'n[aã]o foi humano',
    r'intelig[eê]ncia artificial',
    r'\bIA\b',
]

_REGEX_WOZ = re.compile('|'.join(TERMOS_WOZ), re.IGNORECASE)


def _sql_ilike_woz():
    """Gera cláusulas ILIKE para o WHERE SQL — executado no banco para melhor desempenho."""
    termos_simples = [
        'rob_', 'robo', 'robô', 'robotizado', 'automatico', 'automático',
        'automatizada', 'automatizado', 'automatização', 'automatizacao',
        'woz', 'chatbot', 'maquina', 'máquina',
        'atendimento virtual', 'atendente virtual',
        'não é humano', 'nao e humano', 'sem humano',
        'nao foi humano', 'não foi humano',
        'inteligencia artificial', 'inteligência artificial',
    ]
    return ' OR\n          '.join(
        f'"Comentários" ILIKE \'%{t}%\'' for t in termos_simples
    )


# ---------------------------------------------------------------------------
# Utilitários de data/quinzena
# ---------------------------------------------------------------------------

def periodo_mes(ano: int, mes: int):
    """Retorna (data_inicio str, data_fim str) do mês completo."""
    data_inicio = datetime(ano, mes, 1)
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    data_fim = datetime(ano, mes, ultimo_dia)
    return data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d')


def nome_mes(ano: int, mes: int) -> str:
    meses = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
             7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    return f"{meses.get(mes, str(mes))}/{ano}"


def _auto_meses():
    """Retorna os dois últimos meses completos como ((ano1, mes1), (ano2, mes2)).
    Exemplo: se hoje é julho/2026 → retorna (maio/2026, junho/2026).
    """
    hoje = datetime.now()
    if hoje.month == 1:
        ano2, mes2 = hoje.year - 1, 12
    else:
        ano2, mes2 = hoje.year, hoje.month - 1
    if mes2 == 1:
        ano1, mes1 = ano2 - 1, 12
    else:
        ano1, mes1 = ano2, mes2 - 1
    return (ano1, mes1), (ano2, mes2)


# ---------------------------------------------------------------------------
# Busca de dados
# ---------------------------------------------------------------------------

def buscar_comentarios_woz_periodo(data_inicio: str, data_fim: str) -> pd.DataFrame:
    """Busca comentários WOZ para qualquer período arbitrário (base de todas as buscas)."""
    schema = config.DB_SCHEMA
    ilike_clauses = _sql_ilike_woz()

    query = f"""
    SELECT
        "Protocolo",
        "Analista",
        "Fila",
        "Data Encerramento",
        "Velocidade",
        "Solução",
        "Relacionamento",
        "Comentários"
    FROM {schema}.vw_report_diario
    WHERE "Data Encerramento" BETWEEN %s AND %s
      AND "Comentários" IS NOT NULL
      AND "Comentários" <> ''
      AND (
          {ilike_clauses}
      )
    ORDER BY "Data Encerramento" DESC;
    """

    conn = None
    try:
        conn = get_psycopg2_connection()
        df = pd.read_sql(query, conn, params=(data_inicio, f'{data_fim} 23:59:59'))
        logger.info(f"WOZ ({data_inicio} → {data_fim}): {len(df)} comentários encontrados")
        return df
    except Exception as e:
        logger.error(f"Erro ao buscar comentários WOZ ({data_inicio} → {data_fim}): {e}")
        return pd.DataFrame()
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def buscar_comentarios_woz_mes(ano: int, mes: int) -> pd.DataFrame:
    """Busca comentários WOZ de um mês completo."""
    data_inicio, data_fim = periodo_mes(ano, mes)
    return buscar_comentarios_woz_periodo(data_inicio, data_fim)


def classificar_nps(nota):
    """Classifica uma nota NPS em Promotor, Neutro ou Detrator."""
    try:
        n = float(nota)
        if n >= 9:
            return 'Promotor'
        if n >= 7:
            return 'Neutro'
        return 'Detrator'
    except (TypeError, ValueError):
        return 'Sem nota'


def enriquecer_df(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona colunas de classificação e score médio."""
    if df.empty:
        return df
    for col in ('Velocidade', 'Solução', 'Relacionamento'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['score_medio'] = df[['Velocidade', 'Solução', 'Relacionamento']].mean(axis=1)
    df['classificacao'] = df['score_medio'].apply(classificar_nps)
    return df


# ---------------------------------------------------------------------------
# Análise comparativa
# ---------------------------------------------------------------------------

def resumo_quinzena(df: pd.DataFrame, label: str) -> dict:
    """Gera resumo estatístico de uma quinzena."""
    if df.empty:
        return {
            'label': label,
            'total': 0, 'detratores': 0, 'neutros': 0, 'promotores': 0,
            'pct_detratores': 0.0, 'score_medio': None, 'top_comentarios': [],
        }

    contagens = df['classificacao'].value_counts()
    total = len(df)
    detratores = int(contagens.get('Detrator', 0))
    neutros = int(contagens.get('Neutro', 0))
    promotores = int(contagens.get('Promotor', 0))

    top = (
        df[df['classificacao'] == 'Detrator']
        .nsmallest(5, 'score_medio')[['Protocolo', 'Comentários', 'score_medio']]
        .to_dict(orient='records')
    )

    return {
        'label': label,
        'total': total,
        'detratores': detratores,
        'neutros': neutros,
        'promotores': promotores,
        'pct_detratores': round(detratores / total * 100, 1) if total else 0.0,
        'score_medio': round(float(df['score_medio'].mean()), 2) if not df['score_medio'].isna().all() else None,
        'top_comentarios': top,
    }


def calcular_variacao(r1: dict, r2: dict) -> dict:
    """Calcula a variação absoluta e percentual entre duas quinzenas."""
    delta_total = r2['total'] - r1['total']
    delta_pct = round(r2['pct_detratores'] - r1['pct_detratores'], 1)

    variacao_relativa = (
        round((r2['total'] - r1['total']) / r1['total'] * 100, 1) if r1['total'] else None
    )
    tendencia = 'piora' if delta_total > 0 else ('melhora' if delta_total < 0 else 'estável')

    return {
        'delta_total': delta_total,
        'delta_pct_detratores': delta_pct,
        'variacao_relativa_pct': variacao_relativa,
        'tendencia': tendencia,
    }


# ---------------------------------------------------------------------------
# Geração de HTML
# ---------------------------------------------------------------------------

def gerar_html(r1: dict, r2: dict, variacao: dict,
               data_inicio_1: str, data_fim_1: str,
               data_inicio_2: str, data_fim_2: str) -> str:
    tendencia_cor = {'piora': '#e74c3c', 'melhora': '#27ae60', 'estável': '#f39c12'}
    cor = tendencia_cor.get(variacao['tendencia'], '#888')
    seta = {'piora': '▲', 'melhora': '▼', 'estável': '—'}[variacao['tendencia']]

    def card_quinzena(r: dict) -> str:
        rows = ''.join(
            f"""<tr>
                  <td style="padding:6px 10px;border-bottom:1px solid #eee;font-size:.82em;color:#555">{c.get('Protocolo', '—')}</td>
                  <td style="padding:6px 10px;border-bottom:1px solid #eee;font-size:.82em">{str(c.get('Comentários', ''))[:180]}</td>
                  <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;font-size:.82em">{round(c.get('score_medio', 0), 1)}</td>
                </tr>"""
            for c in r['top_comentarios']
        )
        tabela = f"""
        <table style="width:100%;border-collapse:collapse;margin-top:12px">
          <thead>
            <tr style="background:#f5f5f5">
              <th style="padding:8px 10px;text-align:left;font-size:.8em;color:#666">Protocolo</th>
              <th style="padding:8px 10px;text-align:left;font-size:.8em;color:#666">Comentário</th>
              <th style="padding:8px 10px;text-align:center;font-size:.8em;color:#666">Score</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>""" if rows else '<p style="color:#999;font-size:.85em;margin-top:8px">Nenhum detrator encontrado.</p>'

        return f"""
        <div style="background:#fff;border-radius:10px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.08);flex:1;min-width:300px">
          <h2 style="margin:0 0 16px;font-size:1.1em;color:#2c3e50">{r['label']}</h2>
          <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">
            <div style="background:#fdf2f2;border-radius:8px;padding:12px 18px;text-align:center;flex:1">
              <div style="font-size:2em;font-weight:700;color:#e74c3c">{r['total']}</div>
              <div style="font-size:.78em;color:#666">comentários WOZ</div>
            </div>
            <div style="background:#fdf2f2;border-radius:8px;padding:12px 18px;text-align:center;flex:1">
              <div style="font-size:2em;font-weight:700;color:#e74c3c">{r['pct_detratores']}%</div>
              <div style="font-size:.78em;color:#666">detratores</div>
            </div>
            <div style="background:#f0faf4;border-radius:8px;padding:12px 18px;text-align:center;flex:1">
              <div style="font-size:2em;font-weight:700;color:#27ae60">{r['promotores']}</div>
              <div style="font-size:.78em;color:#666">promotores</div>
            </div>
          </div>
          <div style="font-size:.85em;color:#666;margin-bottom:8px">
            Detratores: <strong>{r['detratores']}</strong> &nbsp;|&nbsp;
            Neutros: <strong>{r['neutros']}</strong> &nbsp;|&nbsp;
            Score médio: <strong>{r['score_medio'] if r['score_medio'] is not None else '—'}</strong>
          </div>
          <h3 style="font-size:.9em;color:#444;margin:16px 0 4px">Top piores casos (detratores)</h3>
          {tabela}
        </div>"""

    variacao_bloco = f"""
    <div style="background:#fff;border-radius:10px;padding:20px 28px;box-shadow:0 2px 8px rgba(0,0,0,.08);margin:28px 0;display:flex;align-items:center;gap:32px;flex-wrap:wrap">
      <div style="font-size:2.2em;color:{cor};font-weight:700">{seta} {variacao['tendencia'].upper()}</div>
      <div>
        <div style="font-size:.9em;color:#555">Variação de volume: <strong style="color:{cor}">{'+' if variacao['delta_total'] >= 0 else ''}{variacao['delta_total']}</strong>
          {f"({'+' if (variacao['variacao_relativa_pct'] or 0) >= 0 else ''}{variacao['variacao_relativa_pct']}%)" if variacao['variacao_relativa_pct'] is not None else ''}
        </div>
        <div style="font-size:.9em;color:#555;margin-top:4px">Variação % detratores: <strong style="color:{cor}">{'+' if variacao['delta_pct_detratores'] >= 0 else ''}{variacao['delta_pct_detratores']}pp</strong></div>
      </div>
      <div style="font-size:.82em;color:#888;border-left:2px solid #eee;padding-left:20px">
        Um aumento no volume de comentários WOZ entre quinzenas indica crescimento<br>
        da percepção de atendimento não-humano — sinal direto de deterioração da experiência.
      </div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Detratores WOZ — Comparativo Mensal</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', sans-serif; background: #f4f6f9; padding: 24px; color: #333; }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    h1 {{ font-size: 1.5em; color: #2c3e50; margin-bottom: 6px; }}
    .subtitle {{ font-size: .9em; color: #888; margin-bottom: 28px; }}
    .cards {{ display: flex; gap: 20px; flex-wrap: wrap; }}
    @media (max-width: 700px) {{ .cards {{ flex-direction: column; }} }}
    @media print {{ body {{ background: #fff; }} }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Detratores WOZ — Comparativo Mensal (Locaweb)</h1>
    <p class="subtitle">
      Comentários NPS contendo termos de atendimento automatizado (robô, woz, bot, automático…) &nbsp;|&nbsp;
      Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </p>

    {variacao_bloco}

    <div class="cards">
      {card_quinzena(r1)}
      {card_quinzena(r2)}
    </div>

    <div style="margin-top:32px;background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 2px 8px rgba(0,0,0,.08);font-size:.82em;color:#666;line-height:1.7">
      <strong>Metodologia:</strong> São contabilizados comentários da view <code>vw_report_diario</code> ({config.DB_SCHEMA})
      que contenham pelo menos um dos termos: robô, robotizado, automático, automatizado, automatização,
      woz, bot, chatbot, máquina, atendimento virtual, "não é humano", "sem humano", inteligência artificial.
      Detratores = score médio (Velocidade + Solução + Relacionamento) ≤ 6.
      <br><strong>Períodos:</strong>
      {r1['label']} ({data_inicio_1} a {data_fim_1}) vs {r2['label']} ({data_inicio_2} a {data_fim_2}).
    </div>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Persistência de comentários individuais (woz_comentarios)
# ---------------------------------------------------------------------------

def salvar_comentarios_woz(df: pd.DataFrame, data_inicio: str, data_fim: str) -> int:
    """Insere os comentários WOZ na tabela woz_comentarios.
    Idempotente: ON CONFLICT (protocolo, data_inicio_periodo, data_fim_periodo) DO NOTHING.

    Returns:
        int: número de linhas efetivamente inseridas.
    """
    if df.empty:
        logger.info(f"WOZ: DataFrame vazio — nenhum comentário para salvar ({data_inicio} → {data_fim})")
        return 0

    schema = config.DB_SCHEMA
    sql = f"""
        INSERT INTO {schema}.woz_comentarios
            (protocolo, analista, fila, data_encerramento,
             velocidade, solucao, relacionamento, score_medio, classificacao,
             comentario, data_inicio_periodo, data_fim_periodo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (protocolo, data_inicio_periodo, data_fim_periodo) DO NOTHING;
    """

    def _val(v):
        """Converte NaN/NaT para None (NULL no banco)."""
        import math
        if v is None:
            return None
        try:
            if math.isnan(float(v)):
                return None
        except (TypeError, ValueError):
            pass
        return v

    registros = [
        (
            row.get('Protocolo'),
            row.get('Analista'),
            row.get('Fila'),
            row.get('Data Encerramento') if pd.notna(row.get('Data Encerramento')) else None,
            _val(row.get('Velocidade')),
            _val(row.get('Solução')),
            _val(row.get('Relacionamento')),
            _val(row.get('score_medio')),
            row.get('classificacao'),
            row.get('Comentários'),
            data_inicio,
            data_fim,
        )
        for _, row in df.iterrows()
    ]

    conn = None
    try:
        conn = get_psycopg2_connection()
        with conn.cursor() as cur:
            cur.executemany(sql, registros)
            inseridos = cur.rowcount
        conn.commit()
        logger.info(f"WOZ: {inseridos}/{len(registros)} comentários salvos em {schema}.woz_comentarios ({data_inicio} → {data_fim})")
        return inseridos
    except Exception as e:
        logger.error(f"Erro ao salvar comentários WOZ no banco: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Persistência no banco (analise_nps_analistas)
# ---------------------------------------------------------------------------

def salvar_no_banco(r1: dict, r2: dict, variacao: dict,
                    data_inicio_1: str, data_fim_1: str,
                    data_inicio_2: str, data_fim_2: str):
    """Insere os resultados WOZ na tabela analise_nps_analistas. Idempotente por request_id."""
    schema = config.DB_SCHEMA
    request_id = f'woz_{data_inicio_1}_vs_{data_inicio_2}'

    tendencia_txt = (
        f"{variacao['tendencia'].upper()}: {r1['label']} → {r2['label']} | "
        f"{variacao['delta_total']:+d} comentários WOZ | "
        f"{variacao['delta_pct_detratores']:+.1f}pp detratores"
    )

    resumo_geral = (
        f"Comparativo quinzenal de comentários WOZ: {r1['label']} vs {r2['label']}.\n"
        f"{r1['label']}: {r1['total']} comentários, {r1['pct_detratores']}% detratores, score médio {r1['score_medio']}.\n"
        f"{r2['label']}: {r2['total']} comentários, {r2['pct_detratores']}% detratores, score médio {r2['score_medio']}.\n"
        f"Tendência: {variacao['tendencia'].upper()}."
    )

    problemas_nps = json.dumps({
        'quinzena_1': {k: v for k, v in r1.items() if k != 'top_comentarios'},
        'quinzena_2': {k: v for k, v in r2.items() if k != 'top_comentarios'},
    }, ensure_ascii=False, indent=2)

    recomendacoes = (
        f"Variação absoluta de volume: {variacao['delta_total']:+d} comentários WOZ.\n"
        f"Variação relativa: {('+' if (variacao['variacao_relativa_pct'] or 0) >= 0 else '')}"
        f"{variacao['variacao_relativa_pct']}%.\n"
        f"Variação percentual de detratores: {variacao['delta_pct_detratores']:+.1f}pp.\n"
        f"Recomendação: "
        + ('Investigar causa do aumento de menções ao WOZ e avaliar ajustes no fluxo automatizado.'
           if variacao['tendencia'] == 'piora'
           else 'Manter monitoramento quinzenal para confirmar tendência de melhora.'
           if variacao['tendencia'] == 'melhora'
           else 'Volume estável — continuar monitoramento.')
    )

    casos_criticos = json.dumps(r2['top_comentarios'], ensure_ascii=False, indent=2, default=str)
    resposta_completa = json.dumps(
        {'quinzena_1': r1, 'quinzena_2': r2, 'variacao': variacao},
        ensure_ascii=False, indent=2, default=str
    )
    protocolos_top = json.dumps(
        [c.get('Protocolo') for c in r2['top_comentarios'] if c.get('Protocolo')],
        ensure_ascii=False
    )

    sql = f"""
    INSERT INTO {schema}.analise_nps_analistas (
        request_datetime, data_inicio, data_fim,
        analistas_criticos, lista_protocolos, total_protocolos,
        analise_tipo, setor,
        prompt_enviado, request_id, resposta_completa,
        resumo_geral, problemas_nps, padroes_comportamentais,
        comentarios_vs_conversas, recomendacoes_melhoria, casos_criticos,
        tokens_prompt, tokens_resposta, modelo_ia
    )
    SELECT
        %s, %s, %s,
        %s, %s, %s,
        %s, %s,
        NULL, %s, %s,
        %s, %s, NULL,
        NULL, %s, %s,
        0, 0, %s
    WHERE NOT EXISTS (
        SELECT 1 FROM {schema}.analise_nps_analistas WHERE request_id = %s
    );
    """

    params = (
        datetime.now(), data_inicio_1, data_fim_2,
        tendencia_txt, protocolos_top, r2['total'],
        'woz_detratores_mensal', 'WOZ/Chatbot',
        request_id, resposta_completa,
        resumo_geral, problemas_nps,
        recomendacoes, casos_criticos,
        'n/a (análise estatística)',
        request_id,
    )

    conn = None
    try:
        conn = get_psycopg2_connection()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            inserted = cur.rowcount
        conn.commit()
        if inserted:
            logger.info(f"Resultado WOZ salvo no banco (request_id={request_id})")
        else:
            logger.info(f"Já existe registro para request_id={request_id} — ignorado.")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar resultado WOZ no banco: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Persistência de histórico
# ---------------------------------------------------------------------------

def salvar_historico(r1: dict, r2: dict, variacao: dict,
                     data_inicio_1: str, data_inicio_2: str):
    """Salva o resultado em JSON para acompanhamento histórico."""
    historico_path = OUTPUT_DIR / 'historico.json'
    historico = []
    if historico_path.exists():
        try:
            historico = json.loads(historico_path.read_text(encoding='utf-8'))
        except Exception:
            historico = []

    chave_comparacao = f'{data_inicio_1} vs {data_inicio_2}'
    entrada = {
        'gerado_em': datetime.now().isoformat(),
        'comparacao': chave_comparacao,
        'quinzena_1': r1,
        'quinzena_2': r2,
        'variacao': variacao,
    }
    historico = [h for h in historico if h.get('comparacao') != chave_comparacao]
    historico.append(entrada)
    historico_path.write_text(json.dumps(historico, ensure_ascii=False, indent=2), encoding='utf-8')
    logger.info(f"Histórico atualizado: {historico_path}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Análise de detratores WOZ — comparativo mensal Locaweb')
    parser.add_argument('--ano1',    type=int, default=None, help='Ano do 1º mês (mais antigo). Ex: 2026')
    parser.add_argument('--mes1',    type=int, default=None, choices=range(1, 13), metavar='MES1',
                        help='1º mês a comparar (1–12).')
    parser.add_argument('--ano2',    type=int, default=None, help='Ano do 2º mês (mais recente). Ex: 2026')
    parser.add_argument('--mes2',    type=int, default=None, choices=range(1, 13), metavar='MES2',
                        help='2º mês a comparar (1–12).')
    parser.add_argument('--inicio1', default=None, help='Início do 1º período (override completo). Ex: 2026-05-01')
    parser.add_argument('--fim1',    default=None, help='Fim do 1º período. Ex: 2026-05-31')
    parser.add_argument('--inicio2', default=None, help='Início do 2º período. Ex: 2026-06-01')
    parser.add_argument('--fim2',    default=None, help='Fim do 2º período. Ex: 2026-06-30')
    args = parser.parse_args()

    # Resolução dos períodos — 3 modos em ordem de prioridade
    if args.inicio1 and args.fim1 and args.inicio2 and args.fim2:
        # Modo manual completo: datas explícitas
        data_inicio_1, data_fim_1 = args.inicio1, args.fim1
        data_inicio_2, data_fim_2 = args.inicio2, args.fim2
        label1 = f"{data_inicio_1} → {data_fim_1}"
        label2 = f"{data_inicio_2} → {data_fim_2}"

    elif args.ano1 and args.mes1 and args.ano2 and args.mes2:
        # Modo mês explícito: dois meses informados
        data_inicio_1, data_fim_1 = periodo_mes(args.ano1, args.mes1)
        data_inicio_2, data_fim_2 = periodo_mes(args.ano2, args.mes2)
        label1 = nome_mes(args.ano1, args.mes1)
        label2 = nome_mes(args.ano2, args.mes2)

    else:
        # Auto: últimos dois meses completos
        (ano1, mes1), (ano2, mes2) = _auto_meses()
        data_inicio_1, data_fim_1 = periodo_mes(ano1, mes1)
        data_inicio_2, data_fim_2 = periodo_mes(ano2, mes2)
        label1 = nome_mes(ano1, mes1)
        label2 = nome_mes(ano2, mes2)

    logger.info(f'=== Análise WOZ Mensal: {label1} vs {label2} ===')

    df1 = enriquecer_df(buscar_comentarios_woz_periodo(data_inicio_1, data_fim_1))
    df2 = enriquecer_df(buscar_comentarios_woz_periodo(data_inicio_2, data_fim_2))

    r1 = resumo_quinzena(df1, label1)
    r2 = resumo_quinzena(df2, label2)
    variacao = calcular_variacao(r1, r2)

    logger.info(f'{label1}: {r1["total"]} comentários WOZ ({r1["pct_detratores"]}% detratores)')
    logger.info(f'{label2}: {r2["total"]} comentários WOZ ({r2["pct_detratores"]}% detratores)')
    logger.info(f'Tendência: {variacao["tendencia"].upper()} | Δ volume: {variacao["delta_total"]:+d} | Δ %detratores: {variacao["delta_pct_detratores"]:+.1f}pp')

    html = gerar_html(r1, r2, variacao, data_inicio_1, data_fim_1, data_inicio_2, data_fim_2)
    nome_arquivo = f'woz_mensal_{data_inicio_1}_vs_{data_inicio_2}.html'
    saida = OUTPUT_DIR / nome_arquivo
    saida.write_text(html, encoding='utf-8')
    logger.info(f'Relatório salvo: {saida}')

    salvar_comentarios_woz(df1, data_inicio_1, data_fim_1)
    salvar_comentarios_woz(df2, data_inicio_2, data_fim_2)

    banco_ok = salvar_no_banco(r1, r2, variacao, data_inicio_1, data_fim_1, data_inicio_2, data_fim_2)
    if banco_ok:
        salvar_historico(r1, r2, variacao, data_inicio_1, data_inicio_2)
    else:
        logger.warning("Histórico JSON não atualizado pois o banco falhou — evitando divergência.")

    print(f'\nComparativo mensal WOZ')
    print(f'  {label1}: {r1["total"]} comentários | {r1["pct_detratores"]}% detratores')
    print(f'  {label2}: {r2["total"]} comentários | {r2["pct_detratores"]}% detratores')
    print(f'  Tendência: {variacao["tendencia"].upper()} ({variacao["delta_total"]:+d} comentários, {variacao["delta_pct_detratores"]:+.1f}pp detratores)')
    print(f'\n  Relatório: {saida}')


if __name__ == '__main__':
    main()
