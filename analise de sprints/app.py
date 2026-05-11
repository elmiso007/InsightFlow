# -*- coding: utf-8 -*-
"""
Aplicação para gerar Relatório de Status da Sprint para gerência e coordenação.
Por padrão envia o CSV ao Gemini para análise com insights (produtividade e alinhamento estratégico).
Use --local para gerar apenas o relatório programático, sem IA.
"""

import argparse
import base64
import sys
import time
from pathlib import Path

from csv_loader import load_sprint_csv
from relatorio_sprint import gerar_relatorio
from md_to_pdf import markdown_to_pdf
from gemini_analise import _get_api_key, analisar_com_gemini
from grafico_sprint import gerar_grafico_pizza_sumario, gerar_grafico_702010

# Pasta base da aplicação (onde está este script) — o CSV e o PDF ficam sempre aqui
PASTA_BASE = Path(__file__).resolve().parent
PDF_PADRAO = PASTA_BASE / "relatorio_sprint.pdf"


def main():
    parser = argparse.ArgumentParser(
        description="Gera Relatório de Status da Sprint a partir de um arquivo CSV exportado."
    )
    parser.add_argument(
        "csv",
        type=str,
        nargs="?",
        default="Jira.csv",
        help="Nome ou caminho do arquivo CSV (ex.: Jira.csv). Se omitido, usa Jira.csv na pasta da aplicação.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Arquivo de saída (ex.: relatorio_sprint.pdf ou .md). Se omitido, gera relatorio_sprint.pdf na pasta da aplicação.",
    )
    parser.add_argument(
        "-t", "--titulo",
        type=str,
        default="Sprint",
        help="Título da sprint para o relatório (ex.: 'Sprint 12 - Mar/2025').",
    )
    parser.add_argument(
        "-e", "--encoding",
        type=str,
        default="utf-8",
        help="Encoding do arquivo CSV (padrão: utf-8). Use latin-1 ou cp1252 se o CSV for exportado no Excel em português.",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Gera apenas o relatório programático (sem enviar dados ao Gemini). Use quando não houver API key ou para teste.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    # Se não for caminho absoluto ou não existir no caminho informado, procura na pasta base da aplicação
    if not csv_path.is_absolute() or not csv_path.is_file():
        csv_na_pasta_base = PASTA_BASE / csv_path.name
        if csv_na_pasta_base.is_file():
            csv_path = csv_na_pasta_base
        elif not csv_path.is_file():
            csv_path = PASTA_BASE / csv_path.name
    if not csv_path.is_file():
        print(f"Erro: arquivo não encontrado: {csv_path}", file=sys.stderr)
        print(f"Dica: coloque o CSV na pasta da aplicação: {PASTA_BASE}", file=sys.stderr)
        sys.exit(1)

    try:
        df = load_sprint_csv(csv_path, encoding=args.encoding)
    except Exception as e:
        print(f"Erro ao carregar CSV: {e}", file=sys.stderr)
        sys.exit(1)

    if df.empty:
        print("Aviso: o CSV está vazio ou não possui linhas de dados.", file=sys.stderr)

    # Relatório: por padrão usa Gemini (insights para coordenação/gerência); --local usa só o programático
    use_gemini = not args.local and _get_api_key() is not None
    if use_gemini:
        try:
            print("Enviando dados ao Gemini para análise com percepções do desempenho obtido...", file=sys.stderr)
            csv_bruto = csv_path.read_text(encoding=args.encoding, errors="replace")
            relatorio = analisar_com_gemini(csv_bruto, titulo_sprint=args.titulo)
        except Exception as e:
            print(f"Aviso: análise com Gemini falhou ({e}). Gerando relatório programático.", file=sys.stderr)
            relatorio = gerar_relatorio(df, titulo_sprint=args.titulo)
    else:
        if not args.local and _get_api_key() is None:
            print("Dica: configure GEMINI_API_KEY ou config.ini para relatório com insights da IA. Usando relatório local.", file=sys.stderr)
        relatorio = gerar_relatorio(df, titulo_sprint=args.titulo)

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = PASTA_BASE / out_path.name
    else:
        out_path = PDF_PADRAO

    # Gerar PDF na pasta base (ou no caminho informado por -o)
    out_path = out_path.resolve()
    if out_path.suffix.lower() == ".md":
        out_path.write_text(relatorio, encoding="utf-8")
        print(f"Relatório Markdown salvo em: {out_path}", file=sys.stderr)
    else:
        # Garante extensão .pdf se não tiver
        if out_path.suffix.lower() != ".pdf":
            out_path = out_path.with_suffix(".pdf")
        # Sempre grava o Markdown completo (conteúdo íntegro, mesmo se o PDF falhar)
        md_completo = PASTA_BASE / "relatorio_sprint.md"
        md_completo.write_text(relatorio, encoding="utf-8")
        print(f"Relatório Markdown completo salvo em: {md_completo}", file=sys.stderr)
        # Gráficos: Sumário Executivo e Alinhamento Estratégico (70/20/10)
        sumario_b64 = None
        alinhamento_b64 = None
        if not df.empty:
            chart_sumario = gerar_grafico_pizza_sumario(df.copy())
            if chart_sumario:
                sumario_b64 = base64.b64encode(chart_sumario).decode("ascii")
            chart_702010 = gerar_grafico_702010(df.copy())
            if chart_702010:
                alinhamento_b64 = base64.b64encode(chart_702010).decode("ascii")
        markdown_to_pdf(relatorio, out_path, sumario_chart_base64=sumario_b64, alinhamento_chart_base64=alinhamento_b64)
        # Pequena pausa para o SO liberar o handle do arquivo (antivírus / visualizador)
        time.sleep(2)
        if hasattr(out_path, "exists") and out_path.exists():
            try:
                out_path.resolve().stat().st_size
            except OSError:
                pass
        print(f"Relatório PDF salvo em: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
