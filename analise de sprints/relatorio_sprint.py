# -*- coding: utf-8 -*-
"""
Geração do Relatório de Status da Sprint em Markdown.
"""

import pandas as pd
from pathlib import Path


# Valores considerados "Concluído" (flexível)
STATUS_CONCLUIDO = ["concluído", "concluido", "concluida", "concluída", "done", "fechado", "encerrado"]

# Categorias para regra 70/20/10 (podem ser ajustadas conforme o CSV)
CATEGORIA_PRODUTO = ["desenvolvimento de produto", "produto", "produto novo", "feature"]
CATEGORIA_MELHORIAS = ["melhorias técnicas", "melhoria técnica", "débito técnico", "tecnico", "manutenção"]
CATEGORIA_INOVACAO = ["inovação", "inovacao", "experimentação", "experimentacao", "pesquisa", "poc", "prova de conceito"]


def _normalize(s: str) -> str:
    if pd.isna(s) or s is None:
        return ""
    return str(s).strip().lower()


def _is_concluido(status: str) -> bool:
    return _normalize(status) in [x.lower() for x in STATUS_CONCLUIDO]


def _classificar_categoria(cat: str) -> str:
    c = _normalize(cat)
    if not c:
        return "Outros"
    for x in CATEGORIA_PRODUTO:
        if x in c:
            return "Desenvolvimento de Produto"
    for x in CATEGORIA_MELHORIAS:
        if x in c:
            return "Melhorias Técnicas"
    for x in CATEGORIA_INOVACAO:
        if x in c:
            return "Inovação / Experimentação"
    return "Outros"


def _is_planejada(natureza: str) -> bool:
    n = _normalize(natureza)
    return "não-planejada" not in n and "nao-planejada" not in n and "não planejada" not in n and "nao planejada" not in n


def gerar_relatorio(df: pd.DataFrame, titulo_sprint: str = "Sprint") -> str:
    """
    Gera o relatório completo em Markdown a partir do DataFrame já normalizado.
    """
    if df.empty:
        return "# Relatório de Status da Sprint\n\n*Nenhum dado carregado.*"

    # Colunas disponíveis
    has_status = "status" in df.columns
    has_natureza = "natureza" in df.columns
    has_bu = "bu" in df.columns
    has_categoria = "categoria" in df.columns
    has_titulo = "titulo" in df.columns
    has_comentarios = "comentarios" in df.columns
    has_sprint = "sprint" in df.columns
    has_sprint_proxima = "sprint_proxima" in df.columns
    has_solicitante = "solicitante" in df.columns

    # Preencher NaN para evitar erros
    for c in [
        "status",
        "natureza",
        "bu",
        "categoria",
        "titulo",
        "comentarios",
        "sprint",
        "sprint_proxima",
        "solicitante",
    ]:
        if c in df.columns:
            df[c] = df[c].fillna("")

    linhas = []
    linhas.append(f"# Relatório de Status da Equipe – {titulo_sprint}")
    linhas.append("")
    linhas.append("---")
    linhas.append("")

    # ----- 1. Sumário Executivo -----
    linhas.append("## 1. Sumário Executivo")
    linhas.append("")
    total = len(df)
    linhas.append(f"- **Total de itens na base:** {total}")

    if has_status:
        concluidos = df["status"].apply(_is_concluido).sum()
        pct = (concluidos / total * 100) if total else 0
        linhas.append(f"- **Percentual de conclusão (Status 'Concluído'):** {concluidos} itens ({pct:.1f}%)")
    else:
        linhas.append("- **Percentual de conclusão:** *(coluna Status não identificada no CSV)*")

    if has_natureza:
        planejadas = df["natureza"].apply(_is_planejada).sum()
        nao_planejadas = total - planejadas
        linhas.append(f"- **Comparativo Planejadas vs Não-planejadas:**")
        linhas.append(f"  - Planejadas: {planejadas} itens ({planejadas/total*100:.1f}%)" if total else "  - Planejadas: 0")
        linhas.append(f"  - Não-planejadas: {nao_planejadas} itens ({nao_planejadas/total*100:.1f}%)" if total else "  - Não-planejadas: 0")
    else:
        linhas.append("- **Comparativo Planejadas vs Não-planejadas:** *(coluna 'Natureza do Item' não identificada)*")

    linhas.append("")
    linhas.append("---")
    linhas.append("")

    # ----- 2. Visão por BU -----
    linhas.append("## 2. Visão por Unidade de Negócio (BU)")
    linhas.append("")
    if has_bu:
        linhas.append("- Quantidade de entregas por BU (considerando itens concluídos e em andamento):")
        linhas.append("")
        bu_counts = df["bu"].replace("", "Não informado").value_counts()
        linhas.append("| Unidade de Negócio | Quantidade de Itens |")
        linhas.append("|--------------------|---------------------|")
        for bu, qtd in bu_counts.items():
            linhas.append(f"| {bu} | {qtd} |")
        if not bu_counts.empty:
            maior_bu = bu_counts.index[0]
            linhas.append("")
            linhas.append(f"- Qual BU recebeu mais esforço no período: **{maior_bu}** ({bu_counts.iloc[0]} itens).")
    else:
        linhas.append("*Coluna de Unidade de Negócio (BU) não identificada no CSV.*")
    linhas.append("")
    linhas.append("---")
    linhas.append("")

    # ----- 3. Alinhamento Estratégico (70/20/10) -----
    linhas.append("## 3. Alinhamento Estratégico (Regra 70/20/10)")
    linhas.append("")
    if has_categoria:
        df["_cat_class"] = df["categoria"].apply(_classificar_categoria)
        cat_counts = df["_cat_class"].value_counts()
        total_cat = cat_counts.sum()
        linhas.append("| Categoria de Atuação | Quantidade | % | Alvo |")
        linhas.append("|----------------------|------------|---|------|")
        for cat, alvo in [
            ("Desenvolvimento de Produto", "70%"),
            ("Melhorias Técnicas", "20%"),
            ("Inovação / Experimentação", "10%"),
            ("Outros", "-"),
        ]:
            qtd = cat_counts.get(cat, 0)
            pct = (qtd / total_cat * 100) if total_cat else 0
            linhas.append(f"| {cat} | {qtd} | {pct:.1f}% | {alvo} |")
        pct_prod = (cat_counts.get("Desenvolvimento de Produto", 0) / total_cat * 100) if total_cat else 0
        pct_tec = (cat_counts.get("Melhorias Técnicas", 0) / total_cat * 100) if total_cat else 0
        pct_inov = (cat_counts.get("Inovação / Experimentação", 0) / total_cat * 100) if total_cat else 0
        dentro_meta = (60 <= pct_prod <= 80) and (10 <= pct_tec <= 30) and (5 <= pct_inov <= 15)
        linhas.append("")
        linhas.append("**Alinhamento Estratégico (Regra 70/20/10):** A regra 70/20/10 define uma meta de distribuição do tempo da equipe: cerca de 70% em Desenvolvimento de Produto, 20% em Melhorias Técnicas e 10% em Inovação/Experimentação, para equilibrar entrega de valor, qualidade e inovação.")
        linhas.append("")
        if dentro_meta:
            linhas.append("**Desempenho na sprint:** A distribuição está **dentro da meta estratégica** 70/20/10.")
        else:
            linhas.append("**Desempenho na sprint:** A distribuição está **fora da meta estratégica** 70/20/10. Recomenda-se revisar o balanceamento entre Desenvolvimento de Produto, Melhorias Técnicas e Inovação.")
    else:
        linhas.append("*Coluna 'Categoria de Atuação' não identificada no CSV.*")
    linhas.append("")
    linhas.append("---")
    linhas.append("")

    # ----- 4. Destaques da Sprint -----
    linhas.append("## 4. Destaques da Sprint")
    linhas.append("")
    linhas.append("As 5 tarefas mais relevantes concluídas (por BU):")
    linhas.append("")
    if has_status and has_titulo:
        concluidos_df = df[df["status"].apply(_is_concluido)].copy()
        if has_titulo:
            concluidos_df = concluidos_df[concluidos_df["titulo"].str.len() > 3]
        if not concluidos_df.empty and has_bu:
            for bu in concluidos_df["bu"].dropna().unique():
                if bu == "":
                    continue
                bu_df = concluidos_df[concluidos_df["bu"] == bu]
                # Ordenar por tamanho da descrição (proxy de relevância) e pegar até 5
                bu_df = bu_df.copy()
                bu_df["_len"] = bu_df["titulo"].fillna("").str.len()
                bu_df = bu_df.nlargest(5, "_len")
                linhas.append(f"### {bu}")
                for _, row in bu_df.head(5).iterrows():
                    tit = (row.get("titulo") or "").strip() or "(sem título)"
                    if len(tit) > 120:
                        tit = tit[:117] + "..."
                    linhas.append(f"- {tit}")
                linhas.append("")
            # Itens sem BU
            sem_bu = concluidos_df[concluidos_df["bu"].fillna("") == ""]
            if not sem_bu.empty:
                linhas.append("### Não informado / Outros")
                for _, row in sem_bu.head(5).iterrows():
                    tit = (row.get("titulo") or "").strip() or "(sem título)"
                    if len(tit) > 120:
                        tit = tit[:117] + "..."
                    linhas.append(f"- {tit}")
        elif not concluidos_df.empty:
            for _, row in concluidos_df.head(5).iterrows():
                tit = (row.get("titulo") or "").strip() or "(sem título)"
                if len(tit) > 120:
                    tit = tit[:117] + "..."
                linhas.append(f"- {tit}")
        else:
            linhas.append("*Nenhum item concluído com título disponível para destaque.*")
    else:
        linhas.append("*Dados insuficientes (Status ou Título) para listar destaques.*")
    linhas.append("")
    linhas.append("---")
    linhas.append("")

    # ----- 5. Análise de Saúde e Riscos -----
    linhas.append("## 5. Análise de Saúde e Riscos")
    linhas.append("")
    if has_natureza:
        nao_planejadas = df[~df["natureza"].apply(_is_planejada)]
        n_np = len(nao_planejadas)
        if n_np > total // 2 and total >= 4:
            linhas.append(f"- **Volume de demandas não-planejadas:** Há um volume **alto** de itens não-planejados ({n_np} de {total}), o que pode estar impactando o cronograma e a previsibilidade.")
        elif n_np > 0:
            linhas.append(f"- **Volume de demandas não-planejadas:** {n_np} itens não-planejados. " + (
                "Monitorar se esse percentual não aumentar nas próximas sprints." if total else ""
            ))
        else:
            linhas.append("- **Volume de demandas não-planejadas:** Baixo; sprint alinhada ao planejado.")
    if has_comentarios:
        comentados = df[df["comentarios"].fillna("").str.strip() != ""]
        if not comentados.empty:
            linhas.append("")
            linhas.append("**Observações encontradas na coluna Comentários:**")
            for _, row in comentados.head(15).iterrows():
                c = (row.get("comentarios") or "").strip()
                if c and len(c) > 2:
                    if len(c) > 200:
                        c = c[:197] + "..."
                    linhas.append(f"- {c}")
        else:
            linhas.append("")
            linhas.append("*Nenhum comentário preenchido na base.*")
    else:
        linhas.append("*Coluna 'Comentários' não identificada no CSV.*")
    linhas.append("")
    linhas.append("---")
    linhas.append("")

    # ----- 6. Próximos Passos -----
    linhas.append("## 6. Próximos Passos")
    linhas.append("")
    linhas.append("Itens não concluídos ou planejados para a próxima Sprint:")
    linhas.append("")
    if has_status:
        pendentes = df[~df["status"].apply(_is_concluido)]
        if not pendentes.empty:
            if has_titulo:
                for _, row in pendentes.iterrows():
                    tit = (row.get("titulo") or "").strip() or "(sem título)"
                    st = (row.get("status") or "").strip() or "—"
                    linhas.append(f"- **{tit[:80]}** — Status: {st}")
            else:
                for _, row in pendentes.iterrows():
                    st = (row.get("status") or "").strip() or "—"
                    linhas.append(f"- Status: {st}")
        else:
            linhas.append("*Todos os itens da base estão marcados como concluídos.*")
    else:
        linhas.append("*Coluna Status não identificada; não foi possível listar próximos passos.*")

    linhas.append("")
    linhas.append("---")
    linhas.append("")

    def _linha_tabela_sec7(row) -> str:
        tit = (row.get("titulo") or "").strip() if has_titulo else ""
        if not tit:
            tit = "(sem descrição)"
        if len(tit) > 80:
            tit = tit[:77] + "..."
        bu = (row.get("bu") or "").strip() if has_bu else ""
        if not bu:
            bu = "—"
        sp = (row.get("sprint") or "").strip() if has_sprint else ""
        prox = (row.get("sprint_proxima") or "").strip() if has_sprint_proxima else ""
        if sp and prox and sp != prox:
            sprint_txt = f"{sp} → {prox}"
        elif sp:
            sprint_txt = sp
        elif prox:
            sprint_txt = prox
        else:
            sprint_txt = "—"
        sol = (row.get("solicitante") or "").strip() if has_solicitante else ""
        if not sol:
            sol = "—"
        tit = str(tit).replace("|", "/")
        bu = str(bu).replace("|", "/")
        sprint_txt = str(sprint_txt).replace("|", "/")
        sol = str(sol).replace("|", "/")
        return f"| {tit} | {bu} | {sprint_txt} | {sol} |"

    def _emitir_tabela_sec7(rows) -> None:
        linhas.append("| Nome da tarefa | BU | Sprint | Solicitante |")
        linhas.append("|----------------|----|--------|-------------|")
        if rows is None or rows.empty:
            linhas.append("| *Nenhum item nesta lista.* | — | — | — |")
        else:
            for _, row in rows.iterrows():
                linhas.append(_linha_tabela_sec7(row))

    # ----- 7. Duas tabelas: concluídas | não concluídas / próxima sprint -----
    linhas.append("## 7. Tabela: Tarefas da sprint")
    linhas.append("")
    linhas.append("### Tarefas concluídas na sprint")
    linhas.append("")
    linhas.append(
        "*Itens com status equivalente a **Concluído** (feito, encerrado, done etc.), considerando entregas finalizadas neste recorte.*"
    )
    linhas.append("")
    if has_status:
        mask_ok = df["status"].apply(_is_concluido)
        concluidas = df[mask_ok]
        pendentes = df[~mask_ok]
    else:
        concluidas = pd.DataFrame()
        pendentes = df
        linhas.append(
            "*A coluna Status não foi identificada no CSV; todos os itens aparecem na segunda tabela.*"
        )
        linhas.append("")
    _emitir_tabela_sec7(concluidas)
    linhas.append("")
    linhas.append("### Tarefas não concluídas e/ou com continuidade na próxima sprint")
    linhas.append("")
    linhas.append(
        "*Demandas ainda em andamento, não finalizadas nesta sprint ou com indicação de **próxima sprint** / carry-over — o que permanece ou avança para o ciclo seguinte.*"
    )
    linhas.append("")
    _emitir_tabela_sec7(pendentes if has_status else df)

    linhas.append("")
    linhas.append("---")
    linhas.append("")
    linhas.append("*Relatório gerado automaticamente a partir do arquivo CSV.*")
    return "\n".join(linhas)
