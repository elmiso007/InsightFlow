# -*- coding: utf-8 -*-
"""
Carregador de CSV com detecção flexível de colunas para o relatório de sprint.
"""

import pandas as pd
from pathlib import Path


# Mapeamento de possíveis nomes de coluna -> nome interno
COLUMN_ALIASES = {
    "status": ["status", "Status", "STATUS", "situação", "Situação"],
    "natureza": [
        "natureza do item",
        "Natureza do Item",
        "Campo personalizado (Natureza do item)",
        "Natureza",
        "natureza",
        "tipo",
    ],
    "bu": [
        "unidade de negócio",
        "Unidade de Negócio",
        "Campo personalizado (Business Unity)",
        "campo personalizado (business unity)",
        "BU",
        "bu",
        "unidade",
        "Unidade",
        "empresa",
    ],
    "categoria": [
        "categoria de atuação",
        "Categoria de Atuação",
        "Campo personalizado (Categoria de Atuação)",
        "campo personalizado (categoria de atuação)",
        "Categoria",
        "categoria",
        "tipo de atuação",
    ],
    "titulo": [
        "título",
        "Título",
        "titulo",
        "descrição",
        "Descrição",
        "descricao",
        "item",
        "Item",
        "nome",
        "Nome",
        "titulo da tarefa",
    ],
    "comentarios": [
        "comentários",
        "Comentários",
        "comentarios",
        "observações",
        "Observações",
        "observacoes",
        "notas",
    ],
    "sprint": ["sprint", "Sprint"],
    "sprint_proxima": [],  # preenchido por lógica: segunda coluna "Sprint" no CSV
    "solicitante": [
        "solicitante",
        "Solicitante",
        "relator",
        "Relator",
        "reporter",
        "Reporter",
        "criador",
        "Criador",
        "Campo personalizado (Solicitante)",
        "campo personalizado (solicitante)",
        "Campo personalizado (Relator)",
        "campo personalizado (relator)",
    ],
}


def _find_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    """Retorna o nome da coluna no DataFrame que corresponde a um dos aliases."""
    cols_lower = {c.strip().lower(): c for c in df.columns}
    for a in aliases:
        if a.lower() in cols_lower:
            return cols_lower[a.lower()]
    for col in df.columns:
        if col.strip().lower() in [x.lower() for x in aliases]:
            return col
    return None


def load_sprint_csv(
    path: str | Path,
    encoding: str = "utf-8",
    sep: str | None = None,
) -> pd.DataFrame:
    """
    Carrega o CSV e normaliza os nomes das colunas para os nomes internos.
    Retorna o DataFrame com colunas: status, natureza, bu, categoria, titulo, comentarios.
    Colunas não encontradas ficarão como None e serão tratadas na análise.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    # Tenta detectar separador
    if sep is None:
        with open(path, "r", encoding=encoding, errors="replace") as f:
            first_line = f.readline()
        if ";" in first_line and first_line.count(";") > first_line.count(","):
            sep = ";"
        else:
            sep = ","

    df = pd.read_csv(path, encoding=encoding, sep=sep, dtype=str)
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    # Tratar colunas "Sprint" (podem vir em duplicata: sprint atual e próxima sprint)
    sprint_indices = [i for i, c in enumerate(df.columns) if str(c).strip().lower() == "sprint"]
    if len(sprint_indices) >= 2:
        new_cols = list(df.columns)
        new_cols[sprint_indices[0]] = "sprint"
        new_cols[sprint_indices[1]] = "sprint_proxima"
        df.columns = new_cols
    elif len(sprint_indices) == 1:
        df = df.rename(columns={df.columns[sprint_indices[0]]: "sprint"})

    mapping = {}
    for internal, aliases in COLUMN_ALIASES.items():
        if internal == "sprint_proxima":
            continue  # já tratado acima
        if not aliases and internal != "sprint_proxima":
            continue
        found = _find_column(df, aliases)
        if found:
            mapping[found] = internal

    df = df.rename(columns=mapping)

    # Manter apenas colunas mapeadas + qualquer outra com nome original
    wanted = set(COLUMN_ALIASES.keys())
    existing = [c for c in df.columns if c in wanted]
    for c in list(df.columns):
        if c not in wanted and c not in mapping.values():
            # Coluna original não mapeada: manter com nome em minúsculo
            df = df.rename(columns={c: f"_orig_{c}"})

    return df
