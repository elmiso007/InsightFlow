# -*- coding: utf-8 -*-
"""
Envia o CSV para o Gemini e obtém relatório com insights para coordenação e gerência.
"""

import os
import time
from pathlib import Path

# Tamanho máximo do conteúdo enviado ao Gemini (evitar estouro)
MAX_CSV_CHARS = 150_000

PROMPT_BASE = """Você é um analista de operações. Analise o arquivo CSV anexo (dados da sprint) e gere um **Relatório de Status da Equipe** voltado para **coordenação e gerência**. Nas seções 2 a 7, além dos dados solicitados, inclua comentários ou percepções sobre o ponto em questão quando indicado. **No Sumário Executivo (seção 1),** após os números, faça apenas uma **síntese descritiva dos dados**, sem avaliar desempenho (veja item 1 abaixo).

**Formatação obrigatória para o relatório:** comece com um título `# Relatório de Sprint` (ou similar). Use **exatamente sete cabeçalhos de nível 2 em Markdown**, um por seção principal, nesta ordem: `## 1. Sumário Executivo`, `## 2. Visão por Unidade de Negócio (BU)`, `## 3. Alinhamento Estratégico (70/20/10)`, `## 4. Destaques da Sprint`, `## 5. Análise de Saúde e Riscos`, `## 6. Próximos Passos`, `## 7. Tabela: Tarefas da sprint`. Na seção 7 use **duas tabelas separadas** (cada uma com título em `###` e um parágrafo explicando o critério), ambas com colunas: **Nome da tarefa** | **BU** | **Sprint** | **Solicitante**. Isso é necessário para o PDF sair completo.

Siga esta estrutura e preencha **todas** as seções por completo:

1. **Sumário Executivo**
   - Total de itens na base.
   - Percentual de conclusão (itens com status equivalente a "Concluído").
   - Comparativo entre demandas "Planejadas" vs "Não-planejadas" (natureza do item).
   - **Resumo dos dados para coordenação e gerência:** Escreva um **parágrafo que sintetize os números já apresentados acima** (total de itens, conclusão, planejadas vs não planejadas), em **linguagem clara para líderes e coordenadores** — tom direto, sem jargão técnico. **Não avalie nem comente o desempenho obtido** (não diga se foi bom, ruim, preocupante ou excelente; não recomende ações nem interprete causa e efeito). Limite-se a **reorganizar e contextualizar os fatos** com os mesmos dados (ex.: proporções, peso relativo do que é planejado e do que não é). Use o rótulo exato: `**Resumo dos dados para coordenação e gerência:**` antes do texto.

2. **Visão por Unidade de Negócio (BU)**
   - Texto introdutório: "Quantidade de entregas por BU (considerando itens concluídos e em andamento):"
   - Inclua uma **tabela em Markdown** com duas colunas: **Unidade de Negócio** | **Quantidade de Itens**. Preencha uma linha por BU (ex.: Locaweb, KingHost, Octadesk, Vindi). Se houver itens multi-BU ou com mais de uma BU, inclua uma linha "(Multi-BU)" ou agrupe conforme os dados do CSV.
   - Em seguida: qual BU recebeu mais esforço no período (em texto).
   - **Resumo do desempenho obtido na sprint:** Crie um resumo sobre a distribuição por BU (balanceamento, priorização, desvios).

3. **Alinhamento Estratégico (Regra 70/20/10)**
   - Com base na "Categoria de Atuação", distribuição do tempo:
     - % Desenvolvimento de Produto (Alvo: 70%)
     - % Melhorias Técnicas (Alvo: 20%)
     - % Inovação / Experimentação (Alvo: 10%)
   - **Alinhamento Estratégico (Regra 70/20/10):** Inclua: (1) um breve texto explicando o conceito da regra 70/20/10 — ou seja, que a meta é destinar cerca de 70% do tempo da equipe a Desenvolvimento de Produto, 20% a Melhorias Técnicas e 10% a Inovação/Experimentação, e por que isso importa para a estratégia. (2) Em seguida, comente o desempenho da equipe na sprint em relação a essa distribuição (se está dentro ou fora da meta e o que isso indica para coordenação e gerência).

4. **Destaques da Sprint**
   - Até 5 tarefas mais relevantes concluídas (maior impacto ou descrições mais substantivas), sempre agrupade por BU.
   - **Comentarios sobre os destaques:** Faça um breve comentário sobre os destaques da sprint.

5. **Análise de Saúde e Riscos**
   - Volume de demandas "Não-planejadas" e impacto no cronograma.
   - Observações importantes das tarefas da sprint.
   - **Comentarios sobre os riscos:** Faça um breve comentário sobre os riscos da sprint.

6. **Próximos Passos**
   - Itens não concluídos ou planejados para a próxima sprint.
   - **Comentarios sobre os proximos passos:** Faça um breve comentário sobre os proximos passos da sprint.

7. **Tabela: Tarefas da sprint**
   - **Primeira tabela:** título `### Tarefas concluídas na sprint` e um parágrafo curto explicando que são itens com status equivalente a concluído/feito. Depois a tabela Markdown (colunas: Nome da tarefa | BU | Sprint | Solicitante).
   - **Segunda tabela:** título `### Tarefas não concluídas e/ou com continuidade na próxima sprint` e um parágrafo explicando que são itens ainda em andamento, não finalizados ou já previstos para a sprint seguinte (use coluna de próxima sprint quando existir). Mesmas quatro colunas. **Toda linha do CSV** deve aparecer em **uma** das duas tabelas (sem duplicar a mesma tarefa nas duas).
   - **Sprint:** pode mostrar sprint atual e, se houver, próxima sprint no mesmo campo (ex.: "Sprint A → Sprint B"). Use "—" quando faltar dado.
   - **Percepções do desempenho obtido na sprint:** Breve avaliação (aderência ao escopo, carry-over, volume pendente).

---
**IMPORTANTE:** Responda o relatório **inteiro**, sem cortar nenhuma seção. Use **Markdown** com tabelas para números e bullet points. Seja objetivo. Na **seção 1**, o bloco após os bullets deve ser só **resumo descritivo dos dados** (rótulo `**Resumo dos dados para coordenação e gerência:**`), sem julgamento de desempenho. Nas demais seções, siga as instruções de comentário ou percepção indicadas em cada item."""


def _get_api_key() -> str | None:
    """Obtém a chave da API do Gemini: variável de ambiente GEMINI_API_KEY ou config.ini."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    config_path = Path(__file__).resolve().parent / "config.ini"
    if config_path.exists():
        try:
            import configparser
            cfg = configparser.ConfigParser()
            cfg.read(config_path, encoding="utf-8")
            if cfg.has_section("gemini") and cfg.has_option("gemini", "api_key"):
                return cfg.get("gemini", "api_key").strip()
        except Exception:
            pass
    return None


def analisar_com_gemini(csv_conteudo: str, titulo_sprint: str = "Sprint") -> str:
    """
    Envia o conteúdo do CSV para o Gemini e retorna o relatório em Markdown.
    Levanta exceção se a API key não estiver configurada ou se a chamada falhar.
    """
    api_key = _get_api_key()
    if not api_key:
        raise ValueError(
            "Chave do Gemini não configurada. Defina a variável de ambiente GEMINI_API_KEY "
            "ou crie config.ini na pasta da aplicação com a seção [gemini] e api_key=SUA_CHAVE"
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError(
            "Pacote google-genai não instalado. Execute: pip install google-genai"
        ) from None

    # Limitar tamanho para não estourar contexto
    if len(csv_conteudo) > MAX_CSV_CHARS:
        csv_conteudo = csv_conteudo[:MAX_CSV_CHARS] + "\n\n... (dados truncados por limite de caracteres)"

    prompt_completo = f"""{PROMPT_BASE}

**Título da sprint para o relatório:** {titulo_sprint}

**Dados do CSV (conteúdo bruto):**
```
{csv_conteudo}
```
"""

    client = genai.Client(api_key=api_key)
    model = "gemini-2.5-flash"

    for tentativa in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt_completo,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=65536,
                ),
            )
            if response.text:
                texto = response.text.strip()
                if response.candidates and response.candidates[0].finish_reason:
                    fr = str(response.candidates[0].finish_reason)
                    if "MAX_TOKENS" in fr.upper():
                        import sys
                        print(
                            "Aviso: resposta do Gemini pode estar truncada (limite de tokens). "
                            "O arquivo relatorio_sprint.md terá o texto completo disponível.",
                            file=sys.stderr,
                        )
                return texto
            # Resposta vazia (ex.: safety)
            if response.candidates and response.candidates[0].finish_reason:
                reason = response.candidates[0].finish_reason.name
                if tentativa < 2:
                    time.sleep(5 * (tentativa + 1))
                    continue
                raise RuntimeError(f"Resposta vazia do Gemini. Motivo: {reason}")
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                time.sleep(10 * (tentativa + 1))
                continue
            raise
    raise RuntimeError("Falha ao obter resposta do Gemini após 3 tentativas.")
