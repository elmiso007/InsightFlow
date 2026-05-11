# -*- coding: utf-8 -*-
"""
Converte o relatório em Markdown para PDF (UTF-8).
Geração por seções (h2) + merge evita truncamento do xhtml2pdf em documentos grandes.
"""

import io
import os
import re
import markdown
from pathlib import Path
from xhtml2pdf import pisa
from pypdf import PdfReader, PdfWriter


def _html_document(body_html: str) -> str:
    """Envolve o HTML do corpo em documento com meta UTF-8 e estilos básicos."""
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8"/>
    <style>
        body {{ font-family: DejaVu Sans, Arial, sans-serif; font-size: 11pt; line-height: 1.4; margin: 2cm; color: #333; }}
        h1 {{ font-size: 18pt; margin-top: 0; border-bottom: 1px solid #ccc; padding-bottom: 0.3em; page-break-after: avoid; }}
        h2 {{ font-size: 14pt; margin-top: 1.2em; page-break-after: avoid; }}
        .quebra-pagina-secao {{ page-break-before: always; break-before: page; height: 0; margin: 0; padding: 0; }}
        h3 {{ font-size: 12pt; margin-top: 1em; page-break-after: avoid; }}
        table {{ border-collapse: collapse; width: 100%; margin: 0.8em 0; font-size: 9pt; page-break-inside: auto; }}
        tr {{ page-break-inside: avoid; page-break-after: auto; }}
        th, td {{ border: 1px solid #ccc; padding: 5px 6px; text-align: left; word-wrap: break-word; max-width: 280px; }}
        th {{ background: #f5f5f5; font-weight: bold; }}
        ul {{ margin: 0.5em 0; padding-left: 1.5em; }}
        li {{ margin: 0.25em 0; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 1em 0; }}
        p {{ margin: 0.5em 0; }}
    </style>
</head>
<body>
{body_html}
</body>
</html>"""


def _adicionar_quebra_pagina_secoes(html_body: str) -> str:
    """Insere quebra de página antes de cada seção a partir da 2ª (cada <h2> após o primeiro)."""
    pat = re.compile(r"(<h2\b[^>]*>)", re.IGNORECASE)
    parts = pat.split(html_body)
    if len(parts) < 3:
        return html_body
    quebra = (
        '<div class="quebra-pagina-secao" '
        'style="page-break-before: always; break-before: page;"></div>'
    )
    out = [parts[0], parts[1], parts[2]]
    i = 3
    while i < len(parts):
        out.append(quebra)
        out.append(parts[i])
        if i + 1 < len(parts):
            out.append(parts[i + 1])
        i += 2
    return "".join(out)

def _img_tag_grafico(img_base64: str, alt: str, width_style: str = "max-width: 55%; width: 10cm;") -> str:
    return (
        f'<p style="margin: 1em 0; text-align: center;">'
        f'<img src="data:image/png;base64,{img_base64}" alt="{alt}" '
        f'style="{width_style} height: auto; display: block; margin: 1em auto;" /></p>'
    )


def _inserir_grafico_antes_percepcoes(html_body: str, img_base64: str) -> str:
    """
    Insere o gráfico do Sumário **somente na seção 1** (entre o h2 «1. Sumário…» e o h2 da seção 2).
    Antes de «Resumo dos dados…» ou «Percepções…» quando existir; senão após o último </ul> da seção (lista de métricas).
    Nunca coloca o gráfico antes do título principal (h1).
    """
    img_tag = _img_tag_grafico(img_base64, "Gráfico - Concluídos e planejados")
    h2_iter = list(re.finditer(r"<h2\b[^>]*>", html_body, flags=re.IGNORECASE))
    s1_start: int | None = None
    s2_start: int | None = None
    for i, m in enumerate(h2_iter):
        end_t = html_body.lower().find("</h2>", m.end())
        if end_t == -1:
            continue
        title = html_body[m.end() : end_t].lower()
        is_s1 = bool(
            re.search(r"\b1\s*\.", title)
            and ("sumário" in title or "sumario" in title or "executivo" in title)
        )
        if is_s1:
            s1_start = m.start()
            if i + 1 < len(h2_iter):
                s2_start = h2_iter[i + 1].start()
            else:
                s2_start = len(html_body)
            break
    if s1_start is None:
        for i, m in enumerate(h2_iter):
            end_t = html_body.lower().find("</h2>", m.end())
            if end_t == -1:
                continue
            title = html_body[m.end() : end_t].lower()
            if i == 0 and ("sumário" in title or "sumario" in title):
                s1_start = m.start()
                s2_start = h2_iter[i + 1].start() if i + 1 < len(h2_iter) else len(html_body)
                break
    if s1_start is None:
        h1e = html_body.lower().find("</h1>")
        if h1e != -1:
            pos = h1e + len("</h1>")
            return html_body[:pos] + "\n" + img_tag + "\n" + html_body[pos:]
        return html_body
    chunk = html_body[s1_start:s2_start]
    cl = chunk.lower()
    insert_before: int | None = None
    for alvo in (
        "resumo dos dados para coordenação",
        "resumo dos dados para coordenacao",
        "resumo dos dados",
        "percepções do desempenho",
        "percepcoes do desempenho",
        "desempenho obtido na sprint",
        "<strong>resumo dos dados",
        "<strong>percepções",
        "<strong>percepcoes",
    ):
        j = cl.find(alvo)
        if j != -1 and (insert_before is None or j < insert_before):
            insert_before = j
    if insert_before is not None:
        pos_abs = s1_start + insert_before
        return html_body[:pos_abs] + img_tag + "\n" + html_body[pos_abs:]
    last_ul = cl.rfind("</ul>")
    if last_ul != -1:
        pos_rel = last_ul + len("</ul>")
        pos_abs = s1_start + pos_rel
        return html_body[:pos_abs] + "\n" + img_tag + "\n" + html_body[pos_abs:]
    hc = cl.find("</h2>")
    pos_rel = (hc + len("</h2>")) if hc != -1 else 0
    pos_abs = s1_start + pos_rel
    return html_body[:pos_abs] + "\n" + img_tag + "\n" + html_body[pos_abs:]


def _inserir_grafico_alinhamento(html_body: str, img_base64: str) -> str:
    """
    Insere o gráfico 70/20/10 **somente dentro da seção 3** (entre o h2 da seção 3 e o h2 da seção 4).
    Se a seção tiver tabela (Categoria | %), o gráfico vai logo após essa tabela.
    Se não houver tabela (só lista de %), insere após o primeiro </ul> — evita pegar o </table> da seção 7.
    """
    img_tag = _img_tag_grafico(img_base64, "Gráfico 70/20/10 - Alvo x Realizado")
    h2_iter = list(re.finditer(r"<h2\b[^>]*>", html_body, flags=re.IGNORECASE))
    s3_start: int | None = None
    s4_start: int | None = None
    for i, m in enumerate(h2_iter):
        end_t = html_body.lower().find("</h2>", m.end())
        if end_t == -1:
            continue
        title = html_body[m.end() : end_t].lower()
        # Seção 3: "3." + Alinhamento ou 70/20 (não confundir com seção 2 BU)
        is_s3 = bool(
            re.search(r"\b3\s*\.", title)
            and (
                "alinhamento" in title
                or "70/20" in title
                or ("70" in title and "20" in title and "10" in title)
            )
        )
        if is_s3:
            s3_start = m.start()
            if i + 1 < len(h2_iter):
                s4_start = h2_iter[i + 1].start()
            else:
                s4_start = len(html_body)
            break
    if s3_start is None:
        return html_body
    chunk = html_body[s3_start:s4_start]
    pos_rel: int
    te = chunk.lower().find("</table>")
    if te != -1:
        pos_rel = te + len("</table>")
    else:
        ul_end = chunk.lower().find("</ul>")
        if ul_end != -1:
            pos_rel = ul_end + len("</ul>")
        else:
            hc = chunk.lower().find("</h2>")
            pos_rel = (hc + len("</h2>")) if hc != -1 else 0
    pos_inserir = s3_start + pos_rel
    return html_body[:pos_inserir] + "\n" + img_tag + "\n" + html_body[pos_inserir:]


def _espacamento_secao_2_bu(html_body: str) -> str:
    """
    Seção 2 (BU): espaço proporcional via margens (pt), não <br/> — o xhtml2pdf
    costuma inflar vários <br/> em buracos enormes na página.
    """
    idem = "<!--sec2-bu-v2-->"
    if idem in html_body:
        return html_body
    h2_iter = list(re.finditer(r"<h2\b[^>]*>", html_body, flags=re.IGNORECASE))
    s2: int | None = None
    s3: int | None = None
    for i, m in enumerate(h2_iter):
        end_t = html_body.lower().find("</h2>", m.end())
        if end_t == -1:
            continue
        title = html_body[m.end() : end_t].lower()
        is_s2 = bool(
            re.search(r"\b2\s*\.", title)
            and (
                "bu" in title
                or "unidade" in title
                or "negócio" in title
                or "negocio" in title
            )
        )
        if is_s2:
            s2 = m.start()
            s3 = h2_iter[i + 1].start() if i + 1 < len(h2_iter) else len(html_body)
            break
    if s2 is None:
        return html_body
    chunk = html_body[s2:s3]
    chunk = chunk.replace("<!--sec2-bu-espaco-->", "")
    m_tbl = re.search(r"<table\b", chunk, flags=re.IGNORECASE)
    if not m_tbl:
        return html_body
    t0 = m_tbl.start()
    te = chunk.lower().find("</table>", t0)
    if te < 0:
        return html_body
    te += len("</table>")
    before = chunk[:t0]
    before = re.sub(r"(?:<br\s*/?>\s*)+$", "", before.rstrip())
    table_html = chunk[t0:te]
    after = chunk[te:]
    after = re.sub(r"^(?:\s*<br\s*/?>\s*)+", "", after)
    wrap = (
        f'{idem}<div style="margin-top:10pt;margin-bottom:10pt;">'
        f"{table_html}</div>"
    )
    chunk = before + wrap + after

    def _margin_resumo(m: re.Match[str]) -> str:
        ws, attrs, rest = m.group(1), m.group(2), m.group(3)
        a = (attrs or "").strip()
        add = "margin-top:8pt"
        if re.search(r"style\s*=", a, re.I):
            a = re.sub(
                r'style\s*=\s*"([^"]*)"',
                lambda x: f'style="{x.group(1).strip().rstrip(";")};{add}"',
                a,
                count=1,
                flags=re.I,
            )
        elif a:
            a = f'{a} style="{add}"'
        else:
            a = f'style="{add}"'
        return f"</p>{ws}<p {a}>{rest}"

    chunk = re.sub(
        r"</p>(\s*)<p([^>]*)>(\s*(?:<strong>\s*)?Resumo\s+do\s+desempenho)",
        _margin_resumo,
        chunk,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return html_body[:s2] + chunk + html_body[s3:]


def _html_chunks_por_h2(html_body: str) -> list[str]:
    """Divide o corpo HTML em blocos: trecho antes do 1º h2 + um bloco por cada h2."""
    parts = re.split(r"(?=<h2\b)", html_body.strip(), flags=re.IGNORECASE)
    return [p for p in parts if p and p.strip()]


def _dividir_html_tabela_grande(html_chunk: str, max_chars: int = 85_000) -> list[str]:
    """
    Se um bloco excede max_chars e a maior <table> do trecho é enorme,
    divide em várias tabelas (mesmo cabeçalho em cada parte) para o xhtml2pdf renderizar tudo.
    """
    if len(html_chunk) <= max_chars:
        return [html_chunk]
    lo = html_chunk.lower()
    best_start, best_len = -1, 0
    pos = 0
    while True:
        t0 = lo.find("<table", pos)
        if t0 == -1:
            break
        t1 = lo.find("</table>", t0)
        if t1 == -1:
            break
        t1 += len("</table>")
        if t1 - t0 > best_len:
            best_start, best_len = t0, t1 - t0
        pos = t0 + 6
    if best_start < 0 or best_len <= max_chars:
        return [html_chunk]

    before = html_chunk[:best_start]
    table_full = html_chunk[best_start : best_start + best_len]
    after = html_chunk[best_start + best_len :]

    m_open = re.match(r"(<table\b[^>]*>)", table_full, re.IGNORECASE)
    if not m_open:
        return [html_chunk]
    open_tag = m_open.group(1)
    inner = table_full[len(open_tag) : -len("</table>")].strip()
    il = inner.lower()
    idx = il.find("</tr>")
    if idx == -1:
        return [html_chunk]
    header_tr = inner[: idx + len("</tr>")]
    body = inner[idx + len("</tr>") :]
    data_rows: list[str] = []
    p = 0
    for m in re.finditer(r"</tr>", body, flags=re.IGNORECASE):
        data_rows.append(body[p : m.end()])
        p = m.end()
    if len(data_rows) < 12:
        return [html_chunk]

    out: list[str] = []
    prefix = before
    acc = open_tag + header_tr
    close = "</table>"
    for row in data_rows:
        if (
            len(prefix) + len(acc) + len(row) + len(close) > max_chars
            and len(acc) > len(open_tag) + len(header_tr)
        ):
            out.append(prefix + acc + close)
            prefix = ""
            acc = open_tag + header_tr
        acc += row
    out.append(prefix + acc + close + after)
    return out if len(out) > 1 else [html_chunk]


def _criar_pdf_partes(html_chunks: list[str], pdf_path: Path) -> None:
    writer = PdfWriter()
    for chunk in html_chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        for sub in _dividir_html_tabela_grande(chunk):
            sub = sub.strip()
            if not sub:
                continue
            full_html = _html_document(sub)
            bio = io.BytesIO()
            status = pisa.CreatePDF(full_html, dest=bio, encoding="utf-8")
            if status.err:
                raise RuntimeError(f"Erro ao gerar PDF (parte): {status.err}")
            bio.seek(0)
            reader = PdfReader(bio)
            for page in reader.pages:
                writer.add_page(page)
    with open(pdf_path, "wb") as f:
        writer.write(f)
    try:
        writer.close()
    except Exception:
        pass
    with open(pdf_path, "r+b") as f:
        os.fsync(f.fileno())


def markdown_to_pdf(md_content: str, pdf_path: str | Path, sumario_chart_base64: str | None = None, alinhamento_chart_base64: str | None = None) -> None:
    """
    Converte o texto em Markdown para um arquivo PDF.
    Suporta tabelas e caracteres UTF-8 (pt-BR).
    sumario_chart_base64: gráfico no item 1 (Sumário). alinhamento_chart_base64: gráfico na seção Alinhamento Estratégico (70/20/10).
    """
    pdf_path = Path(pdf_path)
    html_body = markdown.markdown(
        md_content,
        extensions=["tables", "nl2br"],
        output_format="html5",
    )
    if sumario_chart_base64:
        html_body = _inserir_grafico_antes_percepcoes(html_body, sumario_chart_base64)
    if alinhamento_chart_base64:
        html_body = _inserir_grafico_alinhamento(html_body, alinhamento_chart_base64)
    html_body = _espacamento_secao_2_bu(html_body)

    chunks = _html_chunks_por_h2(html_body)
    # Se o modelo não usou ##: HTML grande vira um bloco só — tentar partir por <hr> (---)
    if len(chunks) < 2 and len(html_body) > 45_000:
        alt = re.split(r"(?=<hr\b[^>]*/?>)", html_body, flags=re.IGNORECASE)
        alt = [x.strip() for x in alt if x.strip()]
        if len(alt) >= 3:
            chunks = alt
    # Várias seções OU HTML muito grande (ex.: uma só seção 7 gigante): partes + merge
    if len(chunks) >= 2 or (len(chunks) == 1 and len(html_body) > 65_000):
        _criar_pdf_partes(chunks if len(chunks) >= 2 else [html_body], pdf_path)
        return

    html_body = _adicionar_quebra_pagina_secoes(html_body)
    full_html = _html_document(html_body)
    with open(pdf_path, "wb") as f:
        status = pisa.CreatePDF(
            full_html,
            dest=f,
            encoding="utf-8",
        )
        f.flush()
        os.fsync(f.fileno())
    if status.err:
        raise RuntimeError(f"Erro ao gerar PDF: {status.err}")
