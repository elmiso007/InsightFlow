"""
Análise de Detratores WOZ — Comparativo Trimestral (Locaweb)
=============================================================

Identifica comentários NPS que mencionam atendimento automatizado/robótico
(Woz, robô, bot, automático, etc.) e compara entre trimestres.

Uso:
    python analise_woz_detratores.py                        # T1 vs T2 do ano atual
    python analise_woz_detratores.py --ano 2026 --t1 1 --t2 2
    python analise_woz_detratores.py --ano 2026 --t1 2 --t2 3
"""

import argparse
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

# Padrão compilado para uso em Python (filtragem de linhas)
_REGEX_WOZ = re.compile('|'.join(TERMOS_WOZ), re.IGNORECASE)

# Padrão SQL: constrói cláusula ILIKE
def _sql_ilike_woz():
    termos_simples = [
        'rob_', 'robo', 'robô', 'robotizado', 'automatico', 'automático',
        'automatizada', 'automatizado', 'automatização', 'automatizacao',
        'woz', 'chatbot', 'maquina', 'máquina',
        'atendimento virtual', 'atendente virtual',
        'não é humano', 'nao e humano', 'sem humano',
        'nao foi humano', 'não foi humano',
        'inteligencia artificial', 'inteligência artificial',
    ]
    clauses = ' OR\n          '.join(
        f'"Comentários" ILIKE \'%{t}%\'' for t in termos_simples
    )
    return clauses


# ---------------------------------------------------------------------------
# Utilitários de data/trimestre
# ---------------------------------------------------------------------------

def periodo_trimestre(ano: int, trimestre: int):
    """Retorna (data_inicio str, data_fim str) de um trimestre."""
    mes_inicio = (trimestre - 1) * 3 + 1
    mes_fim = mes_inicio + 2
    data_inicio = datetime(ano, mes_inicio, 1)
    if mes_fim == 12:
        data_fim = datetime(ano, 12, 31)
    else:
        data_fim = datetime(ano, mes_fim + 1, 1) - timedelta(days=1)
    return data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d')


def nome_trimestre(ano: int, trimestre: int) -> str:
    meses = {1: 'Jan–Mar', 2: 'Abr–Jun', 3: 'Jul–Set', 4: 'Out–Dez'}
    return f"T{trimestre}/{ano} ({meses[trimestre]})"


# ---------------------------------------------------------------------------
# Busca de dados
# ---------------------------------------------------------------------------

def buscar_comentarios_woz(ano: int, trimestre: int) -> pd.DataFrame:
    """Retorna DataFrame com comentários que mencionam atendimento automatizado."""
    schema = config.DB_SCHEMA
    data_inicio, data_fim = periodo_trimestre(ano, trimestre)
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
        logger.info(f"T{trimestre}/{ano}: {len(df)} comentários WOZ encontrados ({data_inicio} → {data_fim})")
        return df
    except Exception as e:
        logger.error(f"Erro ao buscar comentários WOZ T{trimestre}/{ano}: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


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

def resumo_trimestre(df: pd.DataFrame, ano: int, trimestre: int) -> dict:
    """Gera resumo estatístico de um trimestre."""
    if df.empty:
        return {
            'label': nome_trimestre(ano, trimestre),
            'total': 0,
            'detratores': 0,
            'neutros': 0,
            'promotores': 0,
            'pct_detratores': 0.0,
            'score_medio': None,
            'top_comentarios': [],
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
        'label': nome_trimestre(ano, trimestre),
        'total': total,
        'detratores': detratores,
        'neutros': neutros,
        'promotores': promotores,
        'pct_detratores': round(detratores / total * 100, 1) if total else 0.0,
        'score_medio': round(float(df['score_medio'].mean()), 2) if not df['score_medio'].isna().all() else None,
        'top_comentarios': top,
    }


def calcular_variacao(r1: dict, r2: dict) -> dict:
    """Calcula a variação absoluta e percentual entre dois resumos."""
    delta_total = r2['total'] - r1['total']
    delta_pct = round(r2['pct_detratores'] - r1['pct_detratores'], 1)

    if r1['total']:
        variacao_relativa = round((r2['total'] - r1['total']) / r1['total'] * 100, 1)
    else:
        variacao_relativa = None

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

def gerar_html(r1: dict, r2: dict, variacao: dict, ano: int, t1: int, t2: int) -> str:
    tendencia_cor = {'piora': '#e74c3c', 'melhora': '#27ae60', 'estável': '#f39c12'}
    cor = tendencia_cor.get(variacao['tendencia'], '#888')
    seta = {'piora': '▲', 'melhora': '▼', 'estável': '—'}[variacao['tendencia']]

    def card_trimestre(r: dict) -> str:
        rows = ''.join(
            f"""<tr>
                  <td style="padding:6px 10px;border-bottom:1px solid #eee;font-size:.82em;color:#555">{c.get('Protocolo','—')}</td>
                  <td style="padding:6px 10px;border-bottom:1px solid #eee;font-size:.82em">{str(c.get('Comentários',''))[:180]}</td>
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
        Um aumento no volume de comentários WOZ entre trimestres indica crescimento<br>
        da percepção de atendimento não-humano — sinal direto de deterioração da experiência.
      </div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Detratores WOZ — Comparativo Trimestral</title>
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
    <h1>Detratores WOZ — Comparativo Trimestral (Locaweb)</h1>
    <p class="subtitle">
      Comentários NPS contendo termos de atendimento automatizado (robô, woz, bot, automático…) &nbsp;|&nbsp;
      Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </p>

    {variacao_bloco}

    <div class="cards">
      {card_trimestre(r1)}
      {card_trimestre(r2)}
    </div>

    <div style="margin-top:32px;background:#fff;border-radius:10px;padding:20px 24px;box-shadow:0 2px 8px rgba(0,0,0,.08);font-size:.82em;color:#666;line-height:1.7">
      <strong>Metodologia:</strong> São contabilizados comentários da view <code>vw_report_diario</code> ({config.DB_SCHEMA})
      que contenham pelo menos um dos termos: robô, robotizado, automático, automatizado, automatização,
      woz, bot, chatbot, máquina, atendimento virtual, "não é humano", "sem humano", inteligência artificial.
      Detratores = score médio (Velocidade + Solução + Relacionamento) ≤ 6.
    </div>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Persistência no banco (analise_nps_analistas)
# ---------------------------------------------------------------------------

def salvar_no_banco(r1: dict, r2: dict, variacao: dict, ano: int, t1: int, t2: int):
    """Insere os resultados WOZ na tabela analise_nps_analistas. Idempotente por request_id."""
    schema = config.DB_SCHEMA
    request_id = f'woz_{ano}_T{t1}_vs_T{t2}'

    data_inicio, _ = periodo_trimestre(ano, t1)
    _, data_fim = periodo_trimestre(ano, t2)

    tendencia_txt = (
        f"{variacao['tendencia'].upper()}: {r1['label']} → {r2['label']} | "
        f"{variacao['delta_total']:+d} comentários WOZ | "
        f"{variacao['delta_pct_detratores']:+.1f}pp detratores"
    )

    resumo_geral = (
        f"Comparativo de comentários WOZ entre {r1['label']} e {r2['label']}.\n"
        f"{r1['label']}: {r1['total']} comentários, {r1['pct_detratores']}% detratores, score médio {r1['score_medio']}.\n"
        f"{r2['label']}: {r2['total']} comentários, {r2['pct_detratores']}% detratores, score médio {r2['score_medio']}.\n"
        f"Tendência: {variacao['tendencia'].upper()}."
    )

    problemas_nps = json.dumps({
        'trimestre_1': {k: v for k, v in r1.items() if k != 'top_comentarios'},
        'trimestre_2': {k: v for k, v in r2.items() if k != 'top_comentarios'},
    }, ensure_ascii=False, indent=2)

    recomendacoes = (
        f"Variação absoluta de volume: {variacao['delta_total']:+d} comentários WOZ.\n"
        f"Variação relativa: {('+' if (variacao['variacao_relativa_pct'] or 0) >= 0 else '')}"
        f"{variacao['variacao_relativa_pct']}%.\n"
        f"Variação percentual de detratores: {variacao['delta_pct_detratores']:+.1f}pp.\n"
        f"Recomendação: {'Investigar causa do aumento de menções ao WOZ e avaliar ajustes no fluxo automatizado.' if variacao['tendencia'] == 'piora' else 'Manter monitoramento trimestral para confirmar tendência de melhora.' if variacao['tendencia'] == 'melhora' else 'Volume estável — continuar monitoramento.'}"
    )

    casos_criticos = json.dumps(
        r2['top_comentarios'],
        ensure_ascii=False, indent=2, default=str
    )

    resposta_completa = json.dumps(
        {'trimestre_1': r1, 'trimestre_2': r2, 'variacao': variacao},
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
        datetime.now(), data_inicio, data_fim,
        tendencia_txt, protocolos_top, r2['total'],
        'woz_detratores_trimestral', 'WOZ/Chatbot',
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
            logger.info(f"Resultado WOZ salvo no banco: {schema}.analise_nps_analistas (request_id={request_id})")
        else:
            logger.info(f"Registro já existe no banco para request_id={request_id} — ignorado.")
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

def salvar_historico(r1: dict, r2: dict, variacao: dict, ano: int, t1: int, t2: int):
    """Salva o resultado em JSON para acompanhamento histórico."""
    historico_path = OUTPUT_DIR / 'historico.json'
    historico = []
    if historico_path.exists():
        try:
            historico = json.loads(historico_path.read_text(encoding='utf-8'))
        except Exception:
            historico = []

    entrada = {
        'gerado_em': datetime.now().isoformat(),
        'ano': ano,
        'comparacao': f'T{t1} vs T{t2}',
        'trimestre_1': r1,
        'trimestre_2': r2,
        'variacao': variacao,
    }
    # Remove entrada anterior com o mesmo ano+comparação para não duplicar
    historico = [h for h in historico if not (h.get('ano') == ano and h.get('comparacao') == entrada['comparacao'])]
    historico.append(entrada)

    historico_path.write_text(json.dumps(historico, ensure_ascii=False, indent=2), encoding='utf-8')
    logger.info(f"Histórico atualizado: {historico_path}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Análise de detratores WOZ — comparativo trimestral Locaweb')
    parser.add_argument('--ano', type=int, default=datetime.now().year, help='Ano base (padrão: ano atual)')
    parser.add_argument('--t1', type=int, default=1, choices=[1, 2, 3, 4], help='Primeiro trimestre (padrão: 1)')
    parser.add_argument('--t2', type=int, default=2, choices=[1, 2, 3, 4], help='Segundo trimestre (padrão: 2)')
    args = parser.parse_args()

    ano, t1, t2 = args.ano, args.t1, args.t2

    if t1 == t2:
        logger.error('--t1 e --t2 devem ser trimestres diferentes.')
        sys.exit(1)

    logger.info(f'=== Análise WOZ Detratores: {nome_trimestre(ano, t1)} vs {nome_trimestre(ano, t2)} ===')

    df1 = enriquecer_df(buscar_comentarios_woz(ano, t1))
    df2 = enriquecer_df(buscar_comentarios_woz(ano, t2))

    r1 = resumo_trimestre(df1, ano, t1)
    r2 = resumo_trimestre(df2, ano, t2)
    variacao = calcular_variacao(r1, r2)

    logger.info(f'{r1["label"]}: {r1["total"]} comentários WOZ ({r1["pct_detratores"]}% detratores)')
    logger.info(f'{r2["label"]}: {r2["total"]} comentários WOZ ({r2["pct_detratores"]}% detratores)')
    logger.info(f'Tendência: {variacao["tendencia"].upper()} | Δ volume: {variacao["delta_total"]:+d} | Δ %detratores: {variacao["delta_pct_detratores"]:+.1f}pp')

    html = gerar_html(r1, r2, variacao, ano, t1, t2)
    nome_arquivo = f'woz_detratores_{ano}_T{t1}_vs_T{t2}.html'
    saida = OUTPUT_DIR / nome_arquivo
    saida.write_text(html, encoding='utf-8')
    logger.info(f'Relatório salvo: {saida}')

    banco_ok = salvar_no_banco(r1, r2, variacao, ano, t1, t2)
    if banco_ok:
        salvar_historico(r1, r2, variacao, ano, t1, t2)
    else:
        logger.warning("Histórico JSON não atualizado pois o banco falhou — evitando divergência.")

    print(f'\nComparativo {nome_trimestre(ano, t1)} vs {nome_trimestre(ano, t2)}')
    print(f'  {r1["label"]}: {r1["total"]} comentários WOZ | {r1["pct_detratores"]}% detratores')
    print(f'  {r2["label"]}: {r2["total"]} comentários WOZ | {r2["pct_detratores"]}% detratores')
    print(f'  Tendência: {variacao["tendencia"].upper()} ({variacao["delta_total"]:+d} comentários, {variacao["delta_pct_detratores"]:+.1f}pp detratores)')
    print(f'\n  Relatório: {saida}')


if __name__ == '__main__':
    main()
