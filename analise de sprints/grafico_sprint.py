# -*- coding: utf-8 -*-
"""
Gera gráficos para o relatório: Sumário Executivo (colunas empilhadas) e
Alinhamento Estratégico 70/20/10 (Alvo vs Realizado).
"""

import io
import pandas as pd

from relatorio_sprint import _is_concluido, _is_planejada, _classificar_categoria


def gerar_grafico_pizza_sumario(df: pd.DataFrame) -> bytes | None:
    """
    Gera um gráfico de colunas empilhadas com a distribuição:
    - Eixo X: Concluídos | Não concluídos
    - Cada coluna empilhada: Planejados (base) + Não-planejados (topo).
    Retorna os bytes da imagem PNG ou None se não houver dados/colunas.
    """
    if df.empty:
        return None
    has_status = "status" in df.columns
    has_natureza = "natureza" in df.columns
    for c in ["status", "natureza"]:
        if c in df.columns:
            df[c] = df[c].fillna("")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return None

    if has_status and has_natureza:
        concluido = df["status"].apply(_is_concluido)
        planejada = df["natureza"].apply(_is_planejada)
        cp = ((concluido) & (planejada)).sum()
        cnp = ((concluido) & (~planejada)).sum()
        ncp = ((~concluido) & (planejada)).sum()
        ncnp = ((~concluido) & (~planejada)).sum()
        # Duas colunas: Concluídos, Não concluídos. Cada uma empilhada: planejados (baixo), não-planejados (cima)
        categorias = ["Concluídos", "Não concluídos"]
        planejados = [cp, ncp]
        nao_planejados = [cnp, ncnp]
        if sum(planejados) + sum(nao_planejados) == 0:
            return None
    elif has_status:
        concluidos = df["status"].apply(_is_concluido).sum()
        nao_concluidos = len(df) - concluidos
        categorias = ["Concluídos", "Não concluídos"]
        planejados = [concluidos, nao_concluidos]
        nao_planejados = [0, 0]
        if concluidos == 0 and nao_concluidos == 0:
            return None
    else:
        return None

    x = np.arange(len(categorias))
    largura = 0.5

    fig, ax = plt.subplots(figsize=(4, 3.2))
    bar_planejados = ax.bar(x, planejados, largura, label="Planejados", color="#2ecc71")
    bar_nao_planejados = ax.bar(x, nao_planejados, largura, bottom=planejados, label="Não-planejados", color="#e74c3c")

    ax.set_ylabel("Quantidade")
    ax.set_title("Distribuição dos tickets: Concluídos x Não concluídos\n(Planejados x Não-planejados)", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(categorias, fontsize=8)
    ax.tick_params(axis="y", labelsize=8)
    # Legenda fora do quadro, abaixo do gráfico e centralizada
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=7, frameon=True)

    # Valores em cima de cada segmento
    for i, (p, np_val) in enumerate(zip(planejados, nao_planejados)):
        if p > 0:
            ax.text(i, p / 2, str(p), ha="center", va="center", fontsize=8, fontweight="bold", color="white")
        if np_val > 0:
            ax.text(i, p + np_val / 2, str(np_val), ha="center", va="center", fontsize=8, fontweight="bold", color="white")

    plt.tight_layout(pad=1.2)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def gerar_grafico_702010(df: pd.DataFrame) -> bytes | None:
    """
    Gera gráfico de barras horizontais para Alinhamento Estratégico (Regra 70/20/10):
    compara Alvo (70%, 20%, 10%) com o Realizado (percentual efetivo por categoria).
    Retorna os bytes da imagem PNG ou None se não houver coluna de categoria.
    """
    if df.empty or "categoria" not in df.columns:
        return None
    df = df.copy()
    df["categoria"] = df["categoria"].fillna("")
    df["_cat"] = df["categoria"].apply(_classificar_categoria)
    cat_counts = df["_cat"].value_counts()
    total = cat_counts.sum()
    if total == 0:
        return None

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return None

    categorias_nomes = [
        "Desenvolvimento de Produto",
        "Melhorias Técnicas",
        "Inovação / Experimentação",
    ]
    alvos = [70, 20, 10]
    realizados = [(cat_counts.get(c, 0) / total * 100) for c in categorias_nomes]
    categorias_short = ["Produto (70%)", "Melhorias (20%)", "Inovação (10%)"]

    x = np.arange(len(categorias_short))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(4, 3.2))
    bars_alvo = ax.bar(x - largura / 2, alvos, largura, label="Alvo", color="#95a5a6", alpha=0.8)
    bars_real = ax.bar(x + largura / 2, realizados, largura, label="Realizado", color="#3498db")

    ax.set_ylabel("% do tempo", fontsize=8)
    ax.set_title("Alinhamento Estratégico 70/20/10: Alvo x Realizado", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(categorias_short, fontsize=8)
    ax.set_ylim(0, 85)
    ax.tick_params(axis="y", labelsize=8)
    # Legenda abaixo do gráfico (bbox_extra_artists no savefig evita que seja cortada)
    leg = ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.22),
        ncol=2,
        fontsize=7,
        frameon=True,
        fancybox=True,
    )

    for i, (a, r) in enumerate(zip(alvos, realizados)):
        if a > 0:
            ax.text(i - largura / 2, a / 2, f"{a:.0f}%", ha="center", va="center", fontsize=7, fontweight="bold", color="white")
        if r > 0:
            ax.text(i + largura / 2, r / 2, f"{r:.0f}%", ha="center", va="center", fontsize=7, fontweight="bold", color="white")

    plt.tight_layout(pad=1.0)
    buf = io.BytesIO()
    plt.savefig(
        buf,
        format="png",
        dpi=100,
        bbox_inches="tight",
        bbox_extra_artists=(leg,),
        pad_inches=0.35,
    )
    plt.close(fig)
    buf.seek(0)
    return buf.read()
