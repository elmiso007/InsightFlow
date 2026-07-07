import os
import re
from collections import Counter, defaultdict
from datetime import date, timedelta

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap, to_hex, to_rgb
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from branding_lwsa import load_branding_for_pdf

# Identidade visual LWSA (exceto gráfico de gargalos, que mantém tema próprio)
LWSA_PALETTE_HEX = [
    "#011431",
    "#0065AC",
    "#0091C2",
    "#00BCC7",
    "#02E5C2",
    "#929FAC",
    "#EEEEEE",
]

# Mapa de calor: do mais claro ao mais escuro (sem usar #EEEEEE como cor forte de célula)
LWSA_HEATMAP_COLORS = ["#EEEEEE", "#929FAC", "#02E5C2", "#00BCC7", "#0091C2", "#0065AC", "#011431"]
LWSA_CMAP = LinearSegmentedColormap.from_list("lwsa_heatmap", LWSA_HEATMAP_COLORS)

# Interpolação ao longo dos tons principais (variações harmónicas, não só os 6 hex fixos)
LWSA_HARMONY_ANCHORS = ["#011431", "#0065AC", "#0091C2", "#00BCC7", "#02E5C2", "#929FAC"]
_LWSA_HARMONY_CMAP = LinearSegmentedColormap.from_list("lwsa_harmony", LWSA_HARMONY_ANCHORS, N=256)


def _lwsa_harmony_colors(n: int) -> list[str]:
    """N cores para gráficos: variações ao longo do espectro LWSA (interpolação suave)."""
    if n <= 0:
        return []
    if n == 1:
        return [to_hex(_LWSA_HARMONY_CMAP(0.5))]
    lo, hi = 0.04, 0.96
    return [
        to_hex(_LWSA_HARMONY_CMAP(lo + (hi - lo) * i / (n - 1)))
        for i in range(n)
    ]


def _toward_white(hex_c: str, amount: float) -> tuple[int, int, int]:
    """Mistura a cor com branco (amount 0 = cor, 1 = branco) — tons claros para títulos."""
    r, g, b = to_rgb(hex_c)
    a = max(0.0, min(1.0, amount))
    return (
        int(round(255 * a + r * 255 * (1 - a))),
        int(round(255 * a + g * 255 * (1 - a))),
        int(round(255 * a + b * 255 * (1 - a))),
    )


# Fundo único dos títulos de secção (tom claro derivado da paleta LWSA)
LWSA_SECTION_TITLE_FILL_RGB: tuple[int, int, int] = _toward_white("#0091C2", 0.72)


def _label_color_for_bar(hex_color: str) -> str:
    """Texto claro ou escuro sobre barras da paleta."""
    r, g, b = to_rgb(hex_color)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return "#ffffff" if lum < 0.55 else "#1a1a1a"


# Configuração de estilo: fundo transparente para o PNG (ver página do PDF por baixo)
sns.set_theme(
    style="whitegrid",
    rc={
        "figure.figsize": (10, 6),
        "figure.facecolor": "none",
        "axes.facecolor": "none",
        "savefig.facecolor": "none",
        "savefig.transparent": True,
        "grid.alpha": 0.35,
        "text.color": "#1a1a1a",
        "axes.labelcolor": "#1a1a1a",
        "xtick.color": "#1a1a1a",
        "ytick.color": "#1a1a1a",
    },
)
plt.rcParams["figure.figsize"] = (10, 6)


def _finalize_figure_transparent(fig=None):
    fig = fig or plt.gcf()
    fig.patch.set_facecolor("none")
    fig.patch.set_alpha(0.0)
    for ax in fig.axes:
        ax.set_facecolor("none")
        ax.patch.set_alpha(0.0)


def _savefig_transparent(path: str, fig=None, dpi: int = 150, tight: bool = True):
    _finalize_figure_transparent(fig)
    if fig is not None:
        if tight:
            fig.savefig(
                path,
                dpi=dpi,
                transparent=True,
                bbox_inches="tight",
                pad_inches=0.12,
            )
        else:
            fig.savefig(
                path,
                dpi=dpi,
                transparent=True,
            )
        plt.close(fig)
    else:
        plt.savefig(
            path,
            dpi=dpi,
            transparent=True,
            bbox_inches="tight",
            pad_inches=0.12,
        )
        plt.close()


def _pdf_core_font_safe(s) -> str:
    """Helvetica (núcleo fpdf) só aceita Latin-1; normaliza travessões e aspas tipográficas do Jira/CSV."""
    if s is None:
        return ''
    t = str(s)
    for a, b in (
        ('\u2013', '-'),
        ('\u2014', '-'),
        ('\u2212', '-'),
        ('\u2018', "'"),
        ('\u2019', "'"),
        ('\u201c', '"'),
        ('\u201d', '"'),
        ('\u2026', '...'),
        ('\u00a0', ' '),
    ):
        t = t.replace(a, b)
    try:
        t.encode('latin-1')
        return t
    except UnicodeEncodeError:
        return t.encode('latin-1', errors='replace').decode('latin-1')


COL_BUSINESS_UNITY = 'Campo personalizado (Business Unity)'
COL_AREA_ATENDIDA = 'Campo personalizado (Área Atendida (Business Analytics))'
COL_TIPO_ITEM = 'Tipo de item'
COL_SOLICITANTE_SLACK = 'Campo personalizado (Solicitante (Slack))'
COL_RELATOR = 'Relator'
COL_CATEGORIA_ATUACAO = 'Campo personalizado (Categoria de Atuação)'
COL_NATUREZA_ITEM = 'Campo personalizado (Natureza do item)'

# Databoard — acompanhamento de tarefas (coordenadores); link na capa do PDF
DATABOARD_URL = "https://sites.google.com/locaweb.com.br/databoard/"

ALVO_PRODUTO = 70.0
ALVO_MELHORIAS = 20.0
ALVO_INOVACAO = 10.0

# Calendário de sprints (ajuste aqui se mudar a cadência ou a referência)
# Referência alinhada ao fecho da Sprint #4: termina 14/04/2026; Sprint #5 inicia 15/04/2026 (ciclos de 14 dias).
SPRINT_DURACAO_DIAS = 14
SPRINT_REFERENCIA_NUMERO = 10
SPRINT_REFERENCIA_INICIO = date(2026, 6, 22)  # início da Sprint #10 (dd/mm/aaaa); fim = +13 dias

# Limite vertical seguro para conteúdo (A4 ~297 mm, margens e rodapé)
PDF_Y_CONTEUDO_MAX = 276

# Secção 2 (pizza tipo de item + barras solicitantes, mesmo w no PDF): mesmo figsize
# garante a mesma altura em mm ao escalar as imagens para a mesma largura.
FIGSIZE_SECAO2_ORIGEM_TIPO_INCHES = (6.4, 4.8)

# Rodape: "Pagina N" em preto sobre fundo branco; faixa fina #011431 colada ao fundo da pagina
FOOTER_BAR_COLOR = (1, 20, 49)  # #011431
FOOTER_TEXT_LINE_MM = 5.5
FOOTER_PAGE_NUM_GAP_MM = 2.0  # espaco entre o texto e a faixa azul
# Altura da faixa azul: fracao da altura total lida no slide 8 do template (~1/4), com limites
FOOTER_BLUE_STRIP_RATIO_TEMPLATE = 0.22
FOOTER_BLUE_STRIP_MIN_MM = 4.0
FOOTER_BLUE_STRIP_MAX_MM = 8.0
FOOTER_BLUE_STRIP_FALLBACK_MM = 6.0  # sem .pptx / sem medicao

# Fundo estatico Templete - LWSA.png ja inclui faixa de rodape: nao redesenhar faixa azul
FOOTER_RESERVED_STATIC_BG_MM = 14.0  # margem inferior segura para o conteudo (acima do numero)
FOOTER_PAGE_NUM_ON_STATIC_BG_FROM_BOTTOM_MM = 9.0  # texto "Pagina N" branco junto a faixa do PNG

# Marca de agua (slide 6 do template): direita, ~80% altura da pagina, alinhada ao centro vertical
WATERMARK_PAGE_HEIGHT_FRAC = 0.80
# Desloca ligeiramente para dentro da pagina (mm); negativo = mais para a direita (pode sair da folha)
WATERMARK_RIGHT_INSET_MM = 3.0


def _footer_blue_strip_mm(branding) -> float:
    if branding and branding.get("footer_bar_height_mm") is not None:
        h = float(branding["footer_bar_height_mm"]) * FOOTER_BLUE_STRIP_RATIO_TEMPLATE
        return max(
            FOOTER_BLUE_STRIP_MIN_MM,
            min(FOOTER_BLUE_STRIP_MAX_MM, round(h, 3)),
        )
    return FOOTER_BLUE_STRIP_FALLBACK_MM


def _footer_reserved_height_mm(branding) -> float:
    if branding and branding.get("skip_footer_bar"):
        return FOOTER_RESERVED_STATIC_BG_MM
    return FOOTER_TEXT_LINE_MM + FOOTER_PAGE_NUM_GAP_MM + _footer_blue_strip_mm(branding)


def _altura_imagem_mm(caminho, largura_mm):
    """Altura em mm ao inserir a imagem com `largura_mm` (mantém proporção do ficheiro)."""
    if not caminho or not os.path.exists(caminho):
        return largura_mm * 0.6
    try:
        from PIL import Image
        with Image.open(caminho) as im:
            pw, ph = im.size
            if pw <= 0:
                return largura_mm * 0.6
            return largura_mm * (ph / pw)
    except Exception:
        return largura_mm * 0.6


def _resolve_col_bu(df):
    for c in df.columns:
        sc = str(c)
        if sc == COL_BUSINESS_UNITY: return c
        if sc.startswith(COL_BUSINESS_UNITY): return c
    return None

def _resolve_col_area_atendida(df):
    if COL_AREA_ATENDIDA in df.columns: return COL_AREA_ATENDIDA
    for c in df.columns:
        sc = str(c)
        if 'Business Analytics))' in sc and 'tendida' in sc.lower(): return c
    return None

def _resolve_col_solicitante_slack(df):
    """Coluna opcional Campo personalizado (Solicitante (Slack))."""
    if COL_SOLICITANTE_SLACK in df.columns:
        return COL_SOLICITANTE_SLACK
    for c in df.columns:
        if 'Solicitante (Slack)' in str(c):
            return c
    return None

def _texto_celula_solicitante(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if not s or s.lower() == 'nan':
        return None
    return s

def _serie_solicitante_efetivo(df):
    """
    Identificação do solicitante por linha: preenche com Slack quando existir;
    senão usa Relator do Jira. Assim o gráfico não fica só com quem veio pelo Slack.
    """
    col_slack = _resolve_col_solicitante_slack(df)
    col_relator = COL_RELATOR if COL_RELATOR in df.columns else None
    if not col_slack and not col_relator:
        return None

    def um(r):
        if col_slack and col_slack in r.index:
            t = _texto_celula_solicitante(r[col_slack])
            if t: return t
        if col_relator and col_relator in r.index:
            t = _texto_celula_solicitante(r[col_relator])
            if t: return t
        return 'Não Informado'

    return df.apply(um, axis=1)


def _normalize_solicitante_key(s: str) -> str | None:
    """Chave única para agrupar e-mail, nome com pontos e variações de maiúsculas."""
    s = str(s).strip()
    if not s or s.lower() in ('nan', 'não informado', 'nao informado'):
        return None
    if '@' in s:
        local = s.split('@', 1)[0].strip().lower()
    else:
        local = s.lower()
    local = re.sub(r'\.+', ' ', local)
    local = re.sub(r'\s+', ' ', local).strip()
    return local if local else None


def _display_from_local_part(local: str) -> str:
    """Nome para exibição: primeira letra maiúscula por palavra (a partir do local do e-mail ou texto normalizado)."""
    t = local.replace('_', ' ')
    t = re.sub(r'\.+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    if not t:
        return 'Não Informado'
    words = [w for w in t.split() if w]
    out = []
    for w in words:
        if len(w) == 1:
            out.append(w.upper())
        else:
            out.append(w[0].upper() + w[1:].lower())
    return ' '.join(out)


def _canonical_display_for_group(members: list[str]) -> str:
    """Prefere derivar o nome a partir do e-mail (local); senão usa a forma textual mais longa."""
    emails = [m for m in members if '@' in str(m)]
    if emails:
        local = str(sorted(emails, key=len)[0]).split('@', 1)[0].strip()
        return _display_from_local_part(local.lower())
    non_email = [str(m).strip() for m in members if '@' not in str(m)]
    if non_email:
        best = max(non_email, key=len)
        k = _normalize_solicitante_key(best)
        return _display_from_local_part(k) if k else 'Não Informado'
    return 'Não Informado'


def _unificar_rotulos_solicitante(serie: pd.Series) -> pd.Series:
    """
    Agrupa a mesma pessoa: e-mail vs nome (mesmo local do e-mail), nomes com '.' (ex.: Roberto.Coelho),
    e normaliza capitalização para exibição (ex.: ELDER SILVA → Elder Silva).
    """
    groups: dict[str, list[str]] = defaultdict(list)
    for x in serie:
        s = str(x).strip()
        if not s or s.lower() in ('nan', 'não informado', 'nao informado'):
            groups['__ni__'].append(s)
            continue
        k = _normalize_solicitante_key(s)
        if not k:
            groups['__ni__'].append(s)
            continue
        groups[k].append(s)

    key_to_display: dict[str, str] = {}
    for k, members in groups.items():
        if k == '__ni__':
            key_to_display[k] = 'Não Informado'
        else:
            key_to_display[k] = _canonical_display_for_group(members)

    def map_um(x):
        s = str(x).strip()
        if not s or s.lower() in ('nan', 'não informado', 'nao informado'):
            return 'Não Informado'
        k = _normalize_solicitante_key(s)
        if not k:
            return 'Não Informado'
        return key_to_display.get(k, _display_from_local_part(k))

    return serie.map(map_um)


def _resolve_col_categoria_atuacao(df):
    """Campo Jira com 70/20/10 (ex.: Desenvolvimento de Produto (70%))."""
    if COL_CATEGORIA_ATUACAO in df.columns:
        return COL_CATEGORIA_ATUACAO
    for c in df.columns:
        sc = str(c).lower()
        if 'categoria de atua' in sc or 'categoria de atuacao' in sc:
            return c
    return None

def _resolve_col_natureza_item(df):
    if COL_NATUREZA_ITEM in df.columns:
        return COL_NATUREZA_ITEM
    for c in df.columns:
        if 'Natureza do item' in str(c):
            return c
    return None

def _classificar_natureza_planejamento(val):
    """Planejada vs Não-planejada (campo Natureza do item no Jira)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip().lower()
    if not s or s == 'nan':
        return None
    if s.startswith('não') or s.startswith('nao'):
        if 'planejada' in s: return 'nao_planejada'
        return 'outro'
    if s == 'planejada' or (s.startswith('planejada') and 'não' not in s and not s.startswith('nao')):
        return 'planejada'
    return 'outro'

def _metricas_sumario_executivo(df):
    total = len(df)
    if total == 0:
        return {'total': 0, 'pct_conclusao': 0.0, 'planejadas': 0, 'nao_planejadas': 0, 'sem_natureza': 0}
    
    st = df['Status'].astype(str)
    concl = st.str.contains('conclu', case=False, na=False).sum()
    pct = float(100.0 * concl / total)
    col = _resolve_col_natureza_item(df)
    
    planejadas = nao_planejadas = sem_natureza = 0
    if col and col in df.columns:
        for v in df[col]:
            c = _classificar_natureza_planejamento(v)
            if c == 'planejada': planejadas += 1
            elif c == 'nao_planejada': nao_planejadas += 1
            else: sem_natureza += 1
    else:
        sem_natureza = total
        
    return {
        'total': total, 'pct_conclusao': pct, 'planejadas': planejadas, 
        'nao_planejadas': nao_planejadas, 'sem_natureza': sem_natureza
    }

def _pdf_sumario_executivo(pdf, m):
    pdf.set_font('Helvetica', '', 10)
    linhas = [
        f"- Total de itens (sprint atual): {m['total']}",
        f"- Percentual de conclusão: {m['pct_conclusao']:.2f}%",
        f"- Demandas Planejadas: {m['planejadas']}",
        f"- Demandas Não-planejadas: {m['nao_planejadas']}",
    ]
    if m.get('sem_natureza', 0) > 0:
        linhas.append(f"- Demandas sem natureza informada: {m['sem_natureza']}")
    for texto_linha in linhas:
        pdf.cell(
            0,
            7,
            texto_linha,
            border=0,
            align='L',
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
    pdf.ln(4)

def _bucket_702010(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)): return None
    s = str(valor).strip().lower()
    if not s: return None
    if 'desenvolvimento de produto' in s or s.endswith('(70%)') and 'melhoria' not in s and 'inova' not in s: return 'produto'
    if 'melhorias técnicas' in s or 'melhorias tecnicas' in s: return 'melhorias'
    if 'inova' in s or 'experimenta' in s: return 'inovacao'
    if '(70%)' in s: return 'produto'
    if '(20%)' in s: return 'melhorias'
    if '(10%)' in s: return 'inovacao'
    return 'outros'

def _metricas_alinhamento_702010(df_atual):
    col = _resolve_col_categoria_atuacao(df_atual)
    if col is None or col not in df_atual.columns: return None
    buckets = df_atual[col].apply(_bucket_702010)
    valid = buckets.dropna()
    valid = valid[valid != 'outros']
    outros = (buckets == 'outros').sum()
    na = buckets.isna().sum()
    n = len(valid)
    if n == 0: return None
    
    vc = valid.value_counts()
    np_ = int(vc.get('produto', 0))
    nm = int(vc.get('melhorias', 0))
    ni = int(vc.get('inovacao', 0))
    pp = 100.0 * np_ / n
    pm = 100.0 * nm / n
    pi = 100.0 * ni / n
    
    return {
        'coluna': col, 'n_classificados': n, 'n_sem_categoria': int(na), 'n_outros_rotulo': int(outros),
        'produto_n': np_, 'melhorias_n': nm, 'inovacao_n': ni, 
        'produto_pct': pp, 'melhorias_pct': pm, 'inovacao_pct': pi,
    }

def _colunas_sprint(df):
    return [c for c in df.columns if str(c) == 'Sprint' or str(c).startswith('Sprint.')]

def _sprint_numero(nome):
    m = re.search(r"#\s*(\d+)", str(nome), re.I)
    return int(m.group(1)) if m else -1

def _numero_sprint_na_data(d):
    delta = (d - SPRINT_REFERENCIA_INICIO).days
    blocos = delta // SPRINT_DURACAO_DIAS
    return SPRINT_REFERENCIA_NUMERO + blocos

def _inicio_sprint_numero(n):
    idx = n - SPRINT_REFERENCIA_NUMERO
    return SPRINT_REFERENCIA_INICIO + timedelta(days=idx * SPRINT_DURACAO_DIAS)

def _fim_sprint_numero(n):
    return _inicio_sprint_numero(n) + timedelta(days=SPRINT_DURACAO_DIAS - 1)

def _rotulo_sprint_atual_no_csv(df, sprint_cols, n_cal):
    if not sprint_cols: return f"Sprint #{n_cal}"
    prim = sprint_cols[0]
    if prim not in df.columns: return f"Sprint #{n_cal}"
    rotulos = []
    for v in df[prim].dropna():
        s = _celula_sprint_escalar(v)
        if s and _sprint_numero(s) == n_cal: rotulos.append(s)
    if not rotulos: return f"Sprint #{n_cal}"
    return Counter(rotulos).most_common(1)[0][0]


def _sanitize_filename_component(s: str) -> str:
    """Remove caracteres inválidos em nomes de ficheiro (Windows e uso geral)."""
    t = str(s).strip()
    if not t:
        return ''
    t = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', '_', t)
    t = t.rstrip(' .')
    return t or 'Sprint'


def _nome_pdf_report_sprint(sprint_label: str) -> str:
    """Nome do PDF: 'Report' seguido do nome da sprint em vigor."""
    safe = _sanitize_filename_component(sprint_label)
    return f"Report {safe}.pdf"


def _status_eh_downstream_backlog(val) -> bool:
    """Status de workflow [Downstream] Backlog (exclui [Upstream] Backlog)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    s = str(val).strip().lower()
    return '[downstream]' in s and 'backlog' in s


def _linha_escopo_relatorio(row, sprint_cols, n_cal):
    """
    Inclui linhas da sprint de calendário atual OU com status [Downstream] Backlog.
    Não inclui mais todas as linhas sem sprint (ex.: [Upstream] Backlog).
    """
    if _status_eh_downstream_backlog(row.get('Status')):
        return True
    if not sprint_cols:
        return False
    vs = _todos_sprints_linha(row, sprint_cols)
    return any(_sprint_numero(v) == n_cal for v in vs)

def _celula_sprint_escalar(val):
    if isinstance(val, pd.Series):
        for x in val:
            if pd.notna(x) and str(x).strip() != '': return str(x).strip()
        return None
    if pd.notna(val) and str(val).strip() != '': return str(val).strip()
    return None

def _todos_sprints_linha(row, sprint_cols):
    vistos = []
    for c in sprint_cols:
        if c not in row.index: continue
        s = _celula_sprint_escalar(row[c])
        if s and s not in vistos: vistos.append(s)
    return vistos

def _sprint_label_tabela(row, sprint_cols, sprint_ordem):
    vs = _todos_sprints_linha(row, sprint_cols)
    if not vs: return 'Backlog'
    if sprint_ordem:
        conhecidas = [v for v in vs if v in sprint_ordem]
        if conhecidas: return max(conhecidas, key=lambda v: sprint_ordem.index(v))
    return max(vs, key=_sprint_numero)

def _texto_status_jira(row):
    """Valor exibido na coluna Situação: Status do Jira (texto completo do CSV)."""
    st = row.get('Status', '')
    if st is None or (isinstance(st, float) and pd.isna(st)):
        return 'Não informado'
    s = str(st).strip()
    return s if s else 'Não informado'


def _rotulo_tarefa_ticket(row):
    """Chave do ticket + resumo (nome da tarefa)."""
    ck = row.get('Chave da item', '')
    if ck is None or (isinstance(ck, float) and pd.isna(ck)):
        ck = ''
    else:
        ck = str(ck).strip()
    rs = row.get('Resumo', '')
    if rs is None or (isinstance(rs, float) and pd.isna(rs)):
        rs = ''
    else:
        rs = str(rs).strip()
    if ck and rs:
        return f'{ck} - {rs}'
    return ck or rs or '(sem título)'

def _valores_sprint_unicos_ordenados(df, sprint_cols):
    vals = set()
    for c in sprint_cols:
        if c not in df.columns: continue
        for v in df[c].dropna():
            s = str(v).strip()
            if s: vals.add(s)
    return sorted(vals, key=lambda x: (_sprint_numero(x), str(x)))

def _dataframe_proximas_etapas(df, sprint_cols, sprint_ordem):
    """Ordenação para a tabela: sprint (backlog por último entre sprints), depois chave/resumo."""
    out = df.copy()
    def chave_ord_str(r):
        label = _sprint_label_tabela(r, sprint_cols, sprint_ordem)
        ck = str(r.get('Chave da item', '') or '').strip()
        res = str(r.get('Resumo', '') or '').strip()
        chave_estavel = f'{ck}|{res}'
        if label == 'Backlog':
            return f'2|||{chave_estavel}'
        if sprint_ordem and label in sprint_ordem:
            return f'0|{sprint_ordem.index(label):05d}|{label}|{chave_estavel}'
        return f'1|{label}|{chave_estavel}'
    out['_ord'] = out.apply(chave_ord_str, axis=1)
    out = out.sort_values('_ord', kind='mergesort').drop(columns='_ord')
    return out


def _status_jira_concluido(row) -> bool:
    st = row.get('Status', '')
    if st is None or (isinstance(st, float) and pd.isna(st)):
        return False
    return 'conclu' in str(st).lower()


def _linha_na_sprint_calendario(row, sprint_cols, n_cal) -> bool:
    vs = _todos_sprints_linha(row, sprint_cols)
    return any(_sprint_numero(v) == n_cal for v in vs)


def _merge_backlog_e_proximas_sprints(blocos, sprint_cols, sprint_ordem, colunas_ref):
    """Une backlog e outras sprints (próximas) num único DataFrame, mesma ordenação da tabela geral."""
    b, o = blocos.get('backlog'), blocos.get('outras')
    parts = [x for x in (b, o) if x is not None and len(x) > 0]
    if not parts:
        return pd.DataFrame(columns=colunas_ref)
    merged = pd.concat(parts, ignore_index=True)
    return _dataframe_proximas_etapas(merged, sprint_cols, sprint_ordem)


def _split_dataframe_secao7_tarefas(df, sprint_cols, sprint_ordem, n_cal):
    """
    Divide o export em grupos para a secção 7 (sem duplicar linhas):
    - concluídas: status com 'Concluído' (qualquer sprint/backlog);
    - sprint_atual: não concluídas e com Sprint #n_cal nas colunas (sprint do relatório / encerrada);
    - backlog: não concluídas, sem sprint do relatório, etiqueta de sprint = Backlog;
    - outras: não concluídas noutras sprints (fundidas com backlog na apresentação do PDF).
    """
    concluidas, sprint_atual, backlog, outras = [], [], [], []
    for _, row in df.iterrows():
        if _status_jira_concluido(row):
            concluidas.append(row)
            continue
        if _linha_na_sprint_calendario(row, sprint_cols, n_cal):
            sprint_atual.append(row)
            continue
        if _sprint_label_tabela(row, sprint_cols, sprint_ordem) == 'Backlog':
            backlog.append(row)
            continue
        outras.append(row)

    def _df(rows):
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=df.columns)

    return {
        'concluidas': _df(concluidas),
        'sprint_atual': _df(sprint_atual),
        'backlog': _df(backlog),
        'outras': _df(outras),
    }

class PDFReport(FPDF):

    def __init__(self, branding=None):
        super().__init__()
        self.branding = branding
        self._skip_footer_bar = bool((branding or {}).get("skip_footer_bar"))
        self._footer_blue_mm = _footer_blue_strip_mm(branding)
        self._footer_reserved_mm = _footer_reserved_height_mm(branding)
        self._page_background_path = None
        self._page_background_px = None
        self._watermark_path = None
        self._watermark_px = None
        bg = (branding or {}).get("page_background_path") if branding else None
        if bg and os.path.isfile(bg):
            try:
                from PIL import Image
                with Image.open(bg) as im:
                    self._page_background_px = im.size
                self._page_background_path = bg
            except Exception:
                pass
        if not self._page_background_path:
            wp = (branding or {}).get("watermark_path") if branding else None
            if wp and os.path.isfile(wp):
                try:
                    from PIL import Image
                    with Image.open(wp) as im:
                        self._watermark_px = im.size
                    self._watermark_path = wp
                except Exception:
                    pass
        self.set_auto_page_break(True, margin=max(25.0, self._footer_reserved_mm + 6))

    def header(self):
        if self._page_background_path and self._page_background_px:
            self.image(
                self._page_background_path,
                x=0,
                y=0,
                w=self.w,
                h=self.h,
            )
            return
        if self._watermark_path and self._watermark_px:
            pw, ph = self._watermark_px
            if ph <= 0:
                return
            h_t = self.h * WATERMARK_PAGE_HEIGHT_FRAC
            w_t = h_t * (pw / float(ph))
            x = self.w - w_t + WATERMARK_RIGHT_INSET_MM
            y = (self.h - h_t) / 2.0
            self.image(self._watermark_path, x=x, y=y, w=w_t, h=h_t)

    def footer(self):
        if self._skip_footer_bar:
            self.set_text_color(0, 0, 0)
            self.set_font('Helvetica', 'I', 9)
            y_text = (
                self.h
                - FOOTER_PAGE_NUM_ON_STATIC_BG_FROM_BOTTOM_MM
                - FOOTER_TEXT_LINE_MM
            )
            self.set_xy(0, y_text)
            self.cell(
                self.w,
                FOOTER_TEXT_LINE_MM,
                f'Pagina {self.page_no()}',
                border=0,
                align='C',
                new_x=XPos.RIGHT,
                new_y=YPos.TOP,
            )
            self.set_text_color(0, 0, 0)
            return
        y_blue = self.h - self._footer_blue_mm
        self.set_fill_color(*FOOTER_BAR_COLOR)
        self.rect(0, y_blue, self.w, self._footer_blue_mm, style='F')
        y_text = y_blue - FOOTER_PAGE_NUM_GAP_MM - FOOTER_TEXT_LINE_MM
        self.set_text_color(0, 0, 0)
        self.set_font('Helvetica', 'I', 9)
        self.set_xy(0, y_text)
        self.cell(
            self.w,
            FOOTER_TEXT_LINE_MM,
            f'Pagina {self.page_no()}',
            border=0,
            align='C',
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )
    def chapter_title(self, title, fill=True):
        self.set_font('Helvetica', 'B', 16)
        if fill:
            self.set_fill_color(*LWSA_SECTION_TITLE_FILL_RGB)
            self.set_text_color(0, 0, 0)
            self.cell(
                0,
                10,
                title,
                border=0,
                align='L',
                fill=True,
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
        else:
            self.cell(
                0,
                10,
                title,
                border=0,
                align='L',
                fill=False,
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
        self.ln(5)

def gerar_grafico_702010(m, filename):
    if not m: return False
    cats = ['Desenvolvimento\nde Produto', 'Melhorias\nTécnicas', 'Inovação /\nExperimentação']
    actual = [m['produto_pct'], m['melhorias_pct'], m['inovacao_pct']]
    alvos = [ALVO_PRODUTO, ALVO_MELHORIAS, ALVO_INOVACAO]
    x = [0, 1, 2]
    w = 0.35
    c_real = "#0065AC"
    c_alvo = "#929FAC"
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x1 = [i - w / 2 for i in x]
    x2 = [i + w / 2 for i in x]
    b1 = ax.bar(x1, actual, width=w, label='Realizado (sprint)', color=c_real)
    b2 = ax.bar(x2, alvos, width=w, label='Alvo 70/20/10', color=c_alvo, alpha=0.92)
    ax.bar_label(
        b1,
        labels=[f'{v:.1f}%' for v in actual],
        label_type='center',
        fontsize=9,
        color=_label_color_for_bar(c_real),
        fontweight='bold',
    )
    ax.bar_label(
        b2,
        labels=[f'{v:.0f}%' for v in alvos],
        label_type='center',
        fontsize=9,
        color=_label_color_for_bar(c_alvo),
        fontweight='bold',
    )
    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=9)
    ax.set_ylabel('% das demandas (por quantidade)')
    ax.set_title('Alinhamento Estratégico 70 / 20 / 10')
    ax.legend(loc='upper right')
    ax.set_ylim(0, max(max(actual), max(alvos)) * 1.25 + 5)
    fig.tight_layout()
    _savefig_transparent(filename, fig=fig)
    return True

def gerar_grafico_comparativo_solicitantes(df_atual, filename, figsize=None):
    solicitantes = _serie_solicitante_efetivo(df_atual)
    if solicitantes is None:
        return False
    solicitantes = _unificar_rotulos_solicitante(solicitantes)
    counts = solicitantes.value_counts()
    if len(counts) > 8:
        top = counts.head(7)
        outros_val = counts.iloc[7:].sum()
        counts = pd.concat([top, pd.Series({'Outros': outros_val})])
    fs = figsize if figsize is not None else FIGSIZE_SECAO2_ORIGEM_TIPO_INCHES
    fig, ax = plt.subplots(figsize=fs)
    n = len(counts)
    y_pos = list(range(n))
    colors = _lwsa_harmony_colors(n)
    # Barras mais altas quando há poucas categorias, para ocupar o espaço vertical do painel
    h_bar = min(0.82, max(0.38, 5.5 / max(n, 1)))
    bars = ax.barh(y_pos, counts.values, height=h_bar, color=colors)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([str(i) for i in counts.index], fontsize=10)
    vals = [int(round(v)) for v in counts.values]
    ax.bar_label(
        bars,
        labels=[str(v) for v in vals],
        padding=4,
        fontsize=10,
        fontweight='bold',
        color='#1a1a1a',
    )
    ax.set_title('Visão Comparativa: Volume por Solicitante', fontsize=13)
    ax.set_xlabel('Quantidade de Demandas')
    ax.set_ylabel('Solicitante')
    xmax = max(vals) if vals else 0
    ax.set_xlim(0, xmax * 1.12 + 0.5)
    ax.margins(y=0.02)
    fig.subplots_adjust(left=0.28, right=0.96, top=0.90, bottom=0.14)
    _savefig_transparent(filename, fig=fig, tight=False)
    return True

def gerar_grafico_gargalos_funil(df_atual, filename):
    """Gera um gráfico de barras focado apenas nas tarefas pendentes (WIP)."""
    df_pendente = df_atual[~df_atual['Status'].astype(str).str.contains('conclu|cancel', case=False, na=False)]
    if df_pendente.empty:
        return False
    contagem = df_pendente['Status'].value_counts()
    fig, ax = plt.subplots(figsize=(10, 6))
    df_g = pd.DataFrame({'qtd': contagem.values, 'status': contagem.index})
    sns.barplot(
        data=df_g,
        x='qtd',
        y='status',
        hue='status',
        palette='OrRd_r',
        legend=False,
        ax=ax,
    )
    ax.set_title('Análise de Gargalos: Onde estão as tarefas pendentes?', fontsize=14, fontweight='bold')
    ax.set_xlabel('Quantidade de Tarefas Retidas', fontsize=12)
    ax.set_ylabel('Fase do Fluxo (Status)', fontsize=12)
    for i, v in enumerate(contagem.values):
        ax.text(v + 0.1, i, str(v), color='black', va='center', fontweight='bold')
    fig.tight_layout()
    _savefig_transparent(filename, fig=fig, dpi=150)
    return True

def gerar_graficos(df_atual):
    arquivos_graficos = []
    bu_col = _resolve_col_bu(df_atual)
    area_col = _resolve_col_area_atendida(df_atual)

    # 1. Status
    fig, ax = plt.subplots()
    vc_s = df_atual['Status'].value_counts()
    vals = [int(round(v)) for v in vc_s.values]
    bars = ax.barh(range(len(vc_s)), vc_s.values, color=_lwsa_harmony_colors(len(vc_s)))
    ax.set_yticks(range(len(vc_s)))
    ax.set_yticklabels(vc_s.index)
    ax.set_title('Progresso da Sprint (Status)')
    ax.bar_label(
        bars,
        labels=[str(v) for v in vals],
        padding=4,
        fontsize=9,
        fontweight='bold',
        color='#1a1a1a',
    )
    xmax = max(vals) if vals else 0
    ax.set_xlim(0, xmax * 1.12 + 0.5)
    fig.tight_layout()
    _savefig_transparent('g1_status.png', fig=fig)
    arquivos_graficos.append('g1_status.png')

    # 2. Tipo de item (sem rótulos à volta; legenda abaixo com cores)
    fig, ax = plt.subplots(figsize=FIGSIZE_SECAO2_ORIGEM_TIPO_INCHES)
    if COL_TIPO_ITEM in df_atual.columns:
        tipo = df_atual[COL_TIPO_ITEM].fillna('(sem tipo)').astype(str).str.strip()
        vc_t = tipo.value_counts()
        cols = _lwsa_harmony_colors(len(vc_t))
        rotulos = [str(x) for x in vc_t.index]
        wedges, _texts_ext, autotexts = ax.pie(
            vc_t.values,
            labels=None,
            autopct='%1.1f%%',
            colors=cols,
            startangle=90,
            radius=0.88,
            pctdistance=1.14,
        )
        for at in autotexts:
            at.set_color('#1a1a1a')
            at.set_fontsize(9)
            at.set_fontweight('bold')
        ax.set_title('Distribuição por Tipo de Item', pad=10)
        ncol = min(3, max(1, len(rotulos)))
        ax.legend(
            wedges,
            rotulos,
            loc='upper center',
            bbox_to_anchor=(0.5, 0.05),
            ncol=ncol,
            fontsize=9,
            frameon=True,
            fancybox=False,
            edgecolor='#d0d0d0',
            facecolor='#fafafa',
        )
        ax.set_aspect('equal')
        fig.subplots_adjust(left=0.06, right=0.96, top=0.90, bottom=0.22)
    _savefig_transparent('g2_tipo_item.png', fig=fig, tight=False)
    arquivos_graficos.append('g2_tipo_item.png')

    # 3. Solicitantes (Visão Comparativa)
    if gerar_grafico_comparativo_solicitantes(df_atual, 'g3_solicitantes.png'):
        arquivos_graficos.append('g3_solicitantes.png')

    # 4. Impacto por BU (figura nova; evita sobrepor pizza ou outros gráficos abertos)
    if bu_col:
        vc_bu = df_atual[bu_col].value_counts()
        fig, ax = plt.subplots()
        vc_bu.plot(kind='bar', ax=ax, color=_lwsa_harmony_colors(len(vc_bu)))
        ax.set_title('Demandas por Unidade de Negócio')
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        ax.bar_label(
            ax.containers[0],
            labels=[str(int(round(v))) for v in vc_bu.values],
            padding=2,
            fontsize=10,
            fontweight='bold',
            color='#1a1a1a',
        )
        fig.tight_layout()
        _savefig_transparent('g4_bu.png', fig=fig)
        arquivos_graficos.append('g4_bu.png')

    # 5. Heatmap
    if bu_col and area_col:
        par = df_atual[[bu_col, area_col]].dropna()
        if len(par) > 0:
            ct = pd.crosstab(par[bu_col], par[area_col])
            fig, ax = plt.subplots(figsize=(10, 5))
            sns.heatmap(
                ct,
                annot=True,
                fmt='d',
                cmap=LWSA_CMAP,
                linewidths=0.5,
                linecolor='#ffffff',
                ax=ax,
            )
            ax.set_title('Intersecção: Unidade de Negócio vs. Área Atendida')
            fig.tight_layout()
            _savefig_transparent('g5_heatmap_bu_area.png', fig=fig)
            arquivos_graficos.append('g5_heatmap_bu_area.png')

    # Gargalos WIP (PDF: secção 3, com secção 4 BU na mesma página quando existir)
    if gerar_grafico_gargalos_funil(df_atual, 'g7_gargalos.png'):
        arquivos_graficos.append('g7_gargalos.png')

    return arquivos_graficos

def processar_e_gerar_pdf(csv_path, sprint_numero=None):
    """
    Gera o PDF do Sprint Review.
    sprint_numero: se informado (ex.: 3), usa essa sprint no calendário em vez da data de hoje
    (útil para relatório de fechamento após a sprint já ter terminado no calendário).
    """
    df = pd.read_csv(csv_path, encoding='utf-8')
    sprint_cols = _colunas_sprint(df)
    sprint_ordem = _valores_sprint_unicos_ordenados(df, sprint_cols)
    n_cal = (
        sprint_numero
        if sprint_numero is not None
        else _numero_sprint_na_data(date.today())
    )

    df_atual = df[df.apply(lambda r: _linha_escopo_relatorio(r, sprint_cols, n_cal), axis=1)].copy()
    sprint_atual = _rotulo_sprint_atual_no_csv(df_atual, sprint_cols, n_cal)

    # Tabela secção 7: todas as linhas do export (inclui upstream), não só sprint atual
    df_proximas = _dataframe_proximas_etapas(df, sprint_cols, sprint_ordem)
    graficos = gerar_graficos(df_atual)
    metricas_70 = _metricas_alinhamento_702010(df_atual)
    
    if metricas_70 and gerar_grafico_702010(metricas_70, 'g6_702010.png'):
        graficos.append('g6_702010.png')

    branding = load_branding_for_pdf()
    tem_g4 = os.path.exists('g4_bu.png')
    tem_g5 = os.path.exists('g5_heatmap_bu_area.png')
    tem_g7 = os.path.exists('g7_gargalos.png')

    pdf = PDFReport(branding=branding)
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 24); pdf.ln(60)
    pdf.cell(
        0,
        20,
        'Sprint Review - Data Analytics',
        border=0,
        align='C',
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_font('Helvetica', '', 18)
    pdf.cell(
        0,
        10,
        f'Relatório Automático: {_pdf_core_font_safe(sprint_atual)}',
        border=0,
        align='C',
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_font('Helvetica', '', 11)
    ini, fim = _inicio_sprint_numero(n_cal), _fim_sprint_numero(n_cal)
    pdf.cell(
        0,
        8,
        f'Sprint #{n_cal} | {ini.strftime("%d/%m/%Y")} - {fim.strftime("%d/%m/%Y")} '
        f'({SPRINT_DURACAO_DIAS} dias por ciclo)',
        border=0,
        align='C',
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(14)
    pdf.set_font('Helvetica', '', 10)
    pdf.multi_cell(
        0,
        5,
        'Coordenadores: acompanhe as tarefas também no Databoard.',
        align='C',
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(2)
    pdf.set_font('Helvetica', 'U', 10)
    pdf.set_text_color(0, 101, 194)
    pdf.cell(
        0,
        6,
        DATABOARD_URL,
        border=0,
        align='C',
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
        link=DATABOARD_URL,
    )
    pdf.set_text_color(0, 0, 0)

    # 1. e 2. na mesma página (sumário + g1 + origem/tipo)
    pdf.add_page()
    pdf.chapter_title('1. Sumário Executivo')
    sumario = _metricas_sumario_executivo(df_atual)
    _pdf_sumario_executivo(pdf, sumario)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.multi_cell(
        0, 4,
        'Indicadores apenas dos itens desta sprint ou com status [Downstream] Backlog no Jira: '
        'o percentual de conclusão usa status com "Concluído"; planejada / não planejada vêm do campo '
        'Natureza do item no Jira (Planejada / Não-planejada).'
    )
    pdf.ln(2)
    y_graf = pdf.get_y()
    w_g1 = 180.0
    h_g1 = _altura_imagem_mm('g1_status.png', w_g1)
    # Espaço reservado: título secção 2 + dois gráficos lado a lado (~mesma altura)
    espaco_sec2 = 68.0
    while y_graf + h_g1 + espaco_sec2 > PDF_Y_CONTEUDO_MAX and w_g1 >= 125:
        w_g1 -= 8
        h_g1 = _altura_imagem_mm('g1_status.png', w_g1)
    x_g1 = 10 + max(0.0, (180.0 - w_g1) / 2)
    pdf.image('g1_status.png', x=x_g1, y=y_graf, w=w_g1)
    pdf.set_y(y_graf + h_g1 + 4)

    pdf.chapter_title('2. Análise de Origem e Tipo')
    y_row2 = pdf.get_y()
    w_lado = 90
    pdf.image('g2_tipo_item.png', x=10, y=y_row2, w=w_lado)
    h2 = _altura_imagem_mm('g2_tipo_item.png', w_lado)
    h3 = 0.0
    if os.path.exists('g3_solicitantes.png'):
        pdf.image('g3_solicitantes.png', x=105, y=y_row2, w=w_lado)
        h3 = _altura_imagem_mm('g3_solicitantes.png', w_lado)
    h_row = max(h2, h3)
    pdf.set_y(y_row2 + h_row + 3)

    # 3. e 4. na mesma página (gargalos + BU)
    if tem_g7 or tem_g4:
        pdf.add_page()
    if tem_g7:
        pdf.chapter_title('3. Análise de Gargalos no Fluxo (WIP)')
        pdf.set_font('Helvetica', '', 11)
        pdf.multi_cell(
            0, 6,
            'Este gráfico isola as tarefas que ainda não foram concluídas nem canceladas. '
            'O objetivo é identificar em que etapa do processo as entregas estão a acumular '
            '(gargalos), o que pode indicar bloqueios técnicos, dependência de outras equipas '
            'ou lentidão nas validações de negócio.'
        )
        pdf.ln(3)
        y_g7 = pdf.get_y()
        w_g7 = 180.0
        h_g7 = _altura_imagem_mm('g7_gargalos.png', w_g7)
        if tem_g4 and y_g7 + h_g7 + 52 > PDF_Y_CONTEUDO_MAX:
            fator = max(0.45, (PDF_Y_CONTEUDO_MAX - y_g7 - 52) / h_g7)
            w_g7 = max(95.0, w_g7 * fator)
            h_g7 = _altura_imagem_mm('g7_gargalos.png', w_g7)
        elif not tem_g4 and y_g7 + h_g7 > PDF_Y_CONTEUDO_MAX:
            fator = max(0.45, (PDF_Y_CONTEUDO_MAX - y_g7 - 2) / h_g7)
            w_g7 = max(95.0, w_g7 * fator)
            h_g7 = _altura_imagem_mm('g7_gargalos.png', w_g7)
        pdf.image('g7_gargalos.png', x=10, y=y_g7, w=w_g7)
        pdf.set_y(y_g7 + h_g7 + 4)

    if tem_g4:
        pdf.chapter_title('4. Demandas por Unidade de Negócio')
        y_g4 = pdf.get_y()
        w_bu = 180.0
        h4 = _altura_imagem_mm('g4_bu.png', w_bu)
        if y_g4 + h4 > PDF_Y_CONTEUDO_MAX:
            fator = max(0.45, (PDF_Y_CONTEUDO_MAX - y_g4 - 2) / h4)
            w_bu = max(95.0, w_bu * fator)
        pdf.image('g4_bu.png', x=10, y=y_g4, w=w_bu)
        pdf.set_y(y_g4 + _altura_imagem_mm('g4_bu.png', w_bu) + 4)

    # 5. Alinhamento Estratégico (70/20/10) — página própria após 3 e 4 (BU)
    pdf.add_page()
    pdf.chapter_title('5. Alinhamento Estratégico (70/20/10)')
    if metricas_70:
        pp, pm, pi = metricas_70['produto_pct'], metricas_70['melhorias_pct'], metricas_70['inovacao_pct']
        pdf.set_font('Helvetica', '', 11)
        pdf.multi_cell(
            0, 7,
            f"- % Desenvolvimento de Produto: {pp:.2f}% (Alvo: {ALVO_PRODUTO:.0f}%)\n"
            f"- % Melhorias Técnicas: {pm:.2f}% (Alvo: {ALVO_MELHORIAS:.0f}%)\n"
            f"- % Inovação / Experimentação: {pi:.2f}% (Alvo: {ALVO_INOVACAO:.0f}%)"
        )
        pdf.ln(4)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(
            0,
            8,
            'Alinhamento Estratégico (Regra 70/20/10):',
            border=0,
            align='L',
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.set_font('Helvetica', '', 10)
        pdf.multi_cell(
            0, 5,
            'A regra 70/20/10 é uma diretriz estratégica que visa otimizar a alocação de recursos '
            'da equipa, destinando aproximadamente 70% do tempo para o desenvolvimento de '
            'novos produtos e funcionalidades que impulsionam o crescimento do negócio, 20% '
            'para melhorias técnicas e otimização de sistemas existentes (garantindo estabilidade '
            'e eficiência), e 10% para inovação e experimentação, explorando novas ideias e '
            'tecnologias. Essa distribuição é crucial para equilibrar a entrega de valor imediato com '
            'a sustentabilidade técnica e a capacidade de inovação a longo prazo.'
        )
        pdf.ln(2)
        pdf.multi_cell(
            0, 5,
            f"Nesta sprint, a equipa dedicou {pp:.2f}% ao Desenvolvimento de Produto, {pm:.2f}% a "
            f"Melhorias Técnicas e {pi:.2f}% a Inovação/Experimentação."
        )
        pdf.ln(2)
        if metricas_70['n_sem_categoria'] or metricas_70['n_outros_rotulo']:
            pdf.set_font('Helvetica', 'I', 9)
            texto_nota = (f"Nota: percentuais calculadas sobre {metricas_70['n_classificados']} itens com categoria "
                          f"no campo de atuação. {metricas_70['n_sem_categoria']} sem classificação")
            if metricas_70['n_outros_rotulo']:
                texto_nota += f", {metricas_70['n_outros_rotulo']} com rótulo não padrão 70/20/10."
            else:
                texto_nota += "."
            pdf.multi_cell(0, 5, texto_nota)
            
        if os.path.exists('g6_702010.png'):
            pdf.ln(4)
            pdf.image('g6_702010.png', x=10, y=pdf.get_y(), w=180)
    else:
        pdf.set_font('Helvetica', '', 10)
        pdf.multi_cell(
            0, 6,
            'Não foi possível calcular o 70/20/10: verifique se o CSV contém a coluna '
            '"Campo personalizado (Categoria de Atuação)" com valores como '
            '"Desenvolvimento de Produto (70%)", "Melhorias Técnicas (20%)" e '
            '"Inovação / Experimentação (10%)".'
        )

    # 6. Heatmap BU × Área — página própria após secção 5 (70/20/10)
    if tem_g5:
        pdf.add_page()
        pdf.chapter_title('6. Intersecção Negócio vs. Área')
        y_g5 = pdf.get_y()
        w_hm = 180.0
        h5 = _altura_imagem_mm('g5_heatmap_bu_area.png', w_hm)
        if y_g5 + h5 > PDF_Y_CONTEUDO_MAX:
            fator = max(0.45, (PDF_Y_CONTEUDO_MAX - y_g5 - 2) / h5)
            w_hm = max(95.0, w_hm * fator)
            h5 = _altura_imagem_mm('g5_heatmap_bu_area.png', w_hm)
        pdf.image('g5_heatmap_bu_area.png', x=10, y=y_g5, w=w_hm)
        pdf.set_y(y_g5 + h5 + 4)

    # 7. Tabela de tarefas (subtabelas: sprint atual, backlog, concluídas)
    pdf.add_page()
    pdf.chapter_title('7. Tabela de tarefas')
    pdf.set_font('Helvetica', 'I', 8)
    pdf.multi_cell(
        0, 4,
        'Tarefas do ficheiro exportado, agrupadas por contexto. '
        'Tarefa: chave e resumo; Sprint: colunas Sprint do Jira ou Backlog; '
        'Situação: campo Status. A sprint encerrada é a do período do relatório; '
        'backlog e próximas sprints agrupam o que não está nessa sprint. '
        'Concluídas incluem qualquer sprint.',
    )
    pdf.ln(2)

    blocos_secao7 = _split_dataframe_secao7_tarefas(
        df_proximas, sprint_cols, sprint_ordem, n_cal
    )
    y_lim_proximas = 275
    w_tarefa, w_sprint, w_situacao = 98, 36, 56

    def _cabecalho_tabela_proximas():
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(
            w_tarefa,
            10,
            'Tarefa',
            border=1,
            align='C',
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )
        pdf.cell(
            w_sprint,
            10,
            'Sprint',
            border=1,
            align='C',
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )
        pdf.cell(
            w_situacao,
            10,
            'Situação',
            border=1,
            align='C',
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.set_font('Helvetica', '', 7)

    def _trunc(txt, n):
        t = str(txt).strip()
        return t if len(t) <= n else t[: n - 3] + '...'

    def _emitir_linhas_tabela(df_part):
        for _, row in df_part.iterrows():
            if pdf.get_y() + 9 > y_lim_proximas:
                pdf.add_page()
                _cabecalho_tabela_proximas()
            pdf.cell(
                w_tarefa,
                8,
                f" {_trunc(_pdf_core_font_safe(_rotulo_tarefa_ticket(row)), 58)}",
                border=1,
                new_x=XPos.RIGHT,
                new_y=YPos.TOP,
            )
            pdf.cell(
                w_sprint,
                8,
                f" {_trunc(_pdf_core_font_safe(_sprint_label_tabela(row, sprint_cols, sprint_ordem)), 14)}",
                border=1,
                align='C',
                new_x=XPos.RIGHT,
                new_y=YPos.TOP,
            )
            pdf.cell(
                w_situacao,
                8,
                f" {_trunc(_pdf_core_font_safe(_texto_status_jira(row)), 38)}",
                border=1,
                align='L',
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )

    def _subtabela_titulo_e_corpo(titulo: str, df_part: pd.DataFrame):
        if pdf.get_y() > 245:
            pdf.add_page()
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(
            0,
            7,
            titulo,
            border=0,
            align='L',
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(1)
        if df_part is None or len(df_part) == 0:
            pdf.set_font('Helvetica', 'I', 8)
            pdf.multi_cell(0, 4, 'Nenhuma tarefa nesta categoria.')
            pdf.ln(3)
            return
        _cabecalho_tabela_proximas()
        _emitir_linhas_tabela(df_part)
        pdf.ln(4)

    df_backlog_proximas = _merge_backlog_e_proximas_sprints(
        blocos_secao7, sprint_cols, sprint_ordem, df_proximas.columns
    )
    _subtabela_titulo_e_corpo(
        f'7.1 Tarefas na sprint encerrada (Sprint #{n_cal})',
        blocos_secao7['sprint_atual'],
    )
    _subtabela_titulo_e_corpo(
        '7.3 Tarefas em backlog e próximas sprints',
        df_backlog_proximas,
    )
    pdf.add_page()
    _subtabela_titulo_e_corpo('7.4 Tarefas concluídas', blocos_secao7['concluidas'])

    nome_pdf = _nome_pdf_report_sprint(sprint_atual)
    out_pdf = nome_pdf
    try:
        pdf.output(out_pdf)
    except PermissionError:
        stem = nome_pdf[:-4] if nome_pdf.lower().endswith('.pdf') else nome_pdf
        out_pdf = f"{stem}_novo.pdf"
        pdf.output(out_pdf)
        print(f"Aviso: ficheiro principal em uso; gravado como {out_pdf}")
    
    # Limpeza de ficheiros
    for g in graficos:
        if os.path.exists(g): os.remove(g)

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Gera o PDF Sprint Review a partir do CSV do Jira.")
    ap.add_argument("csv", nargs="?", default="Jira.csv", help="Caminho do CSV exportado (default: Jira.csv)")
    ap.add_argument(
        "--sprint",
        "-s",
        type=int,
        default=None,
        metavar="N",
        help="Número da sprint no calendário (ex.: 3 para relatório final da Sprint #3)",
    )
    args = ap.parse_args()
    from pathlib import Path
    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = Path(__file__).resolve().parent / csv_path
    processar_e_gerar_pdf(str(csv_path), sprint_numero=args.sprint)