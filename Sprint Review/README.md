# Sprint Review — Relatório executivo (PDF)

## Objetivo

Esta aplicação **automatiza a produção do material de apoio à Sprint Review** da equipa Data Analytics. O objetivo é transformar um export **CSV do Jira** (UTF-8) num **único relatório em PDF**, pronto para partilha e discussão em reunião, sem montagem manual de gráficos ou cópias de tabelas.

Com isso, pretende-se:

- **Dar visibilidade** ao que foi e está a ser trabalhado na sprint corrente (e no backlog associado ao escopo definido no código), com indicadores de conclusão, planeamento e distribuição por tipo, solicitante, unidade de negócio e alinhamento 70/20/10.
- **Apoiar a análise de fluxo**, com destaque para tarefas pendentes (WIP) e possíveis gargalos por estado.
- **Centralizar a lista de tarefas** do export (incluindo upstream), com chave, sprint, e status tal como no Jira, para acompanhamento das próximas etapas.

Em resumo: **reduzir esforço repetitivo, padronizar o formato do relatório e basear a conversa da review em dados extraídos diretamente do Jira.**

## Requisitos

- Python 3.10+ (testado com 3.13)
- Dependências: ver `requirements.txt`

```bash
pip install -r requirements.txt
```

Pacotes principais: `pandas`, `matplotlib`, `seaborn`, `fpdf2`, `Pillow` (usada para calcular dimensões de imagens no PDF).

## Execução

Pode ser executado de **qualquer diretório** — o script localiza o `Jira.csv` sempre **relativo à sua própria pasta**:

```bash
python gerador_report.py
# ou de outro diretório:
python "c:/caminho/para/Sprint Review/gerador_report.py"
```

Para gerar o relatório de uma sprint já encerrada (ex.: sprint 10):

```bash
python gerador_report.py --sprint 10
```

### Saída

- Ficheiro PDF: **`Report Sprint #<N>.pdf`**, onde `<N>` é o número da sprint calculado para a **data de hoje** (ou o valor passado em `--sprint`, ver calendário abaixo).
- Se o PDF com o mesmo nome estiver **aberto** ou bloqueado noutra aplicação, o script grava **`Report Sprint #<N>_novo.pdf`** e imprime um aviso no consola.
- Imagens temporárias (`g1_status.png`, `g2_tipo_item.png`, …) são **apagadas** no fim da execução.

## Ficheiro de entrada (`Jira.csv`)

- Codificação: **UTF-8**.
- Formato típico: export CSV do Jira com cabeçalhos em português (ex.: `Resumo`, `Status`, `Chave da item`, colunas `Sprint` / `Sprint.1`, …).

O script tenta **resolver colunas** quando o Jira duplica nomes (várias colunas `Sprint`, `Business Unity`, etc.), usando o nome base ou prefixos conhecidos.

### Colunas usadas (referência)

| Área | Colunas / lógica |
|------|-------------------|
| Geral | `Status`, `Resumo`, `Chave da item`, `Tipo de item` |
| Sprints | Todas as colunas cujo nome é `Sprint` ou começa por `Sprint.` |
| BU / Área | `Campo personalizado (Business Unity)` e `Campo personalizado (Área Atendida (Business Analytics))` (com resolução de duplicados) |
| Solicitante (gráfico) | `Campo personalizado (Solicitante (Slack))` se preenchido; senão `Relator` |
| Sumário (planejamento) | `Campo personalizado (Natureza do item)` (Planejada / Não-planejada) |
| 70/20/10 | `Campo personalizado (Categoria de Atuação)` |

## Calendário de sprints

A “sprint atual” **não** vem só do CSV: é calculada a partir de constantes no topo de `gerador_report.py`:

- `SPRINT_DURACAO_DIAS` — duração de cada sprint (ex.: 14).
- `SPRINT_REFERENCIA_NUMERO` — número da sprint de referência (ex.: 3).
- `SPRINT_REFERENCIA_INICIO` — data de **início** dessa sprint (`date(ano, mês, dia)`).

A sprint do dia `D` é: `SPRINT_REFERENCIA_NUMERO + (D - SPRINT_REFERENCIA_INICIO).days // SPRINT_DURACAO_DIAS`.

**Atualize estas constantes** quando mudar a cadência ou a referência do calendário.

## Escopo dos dados

- **Gráficos e sumário executivo (secções 1–6)** usam **`df_atual`**: linhas em que  
  - não há sprint em nenhuma coluna Sprint → tratadas como *backlog* no escopo, **ou**  
  - alguma coluna Sprint contém o **mesmo número** (`#N`) que a sprint do calendário para hoje.

- **Secção 7 — Próximas etapas** usa o **`DataFrame` completo** do CSV: **todas** as linhas exportadas (inclui upstream), com tabela **Tarefa** (`Chave - Resumo`), **Sprint** (rótulo derivado das colunas Sprint ou `Backlog`) e **Situação** (texto de **`Status`** do Jira). Textos longos são truncados para caber no PDF (fonte core Helvetica / Latin-1).

## Estrutura do PDF

| Secção | Conteúdo |
|--------|-----------|
| Capa | Título, sprint atual (rótulo do CSV quando possível), intervalo de datas da sprint |
| 1. Sumário executivo | Métricas sobre `df_atual`; gráfico de barras horizontais por **Status** (mesma página que a seção 2) |
| 2. Análise de Origem e Tipo | Pizza por **tipo de item**; barras por **solicitante** (Slack → Relator, com **unificação** `user` / `user@domínio` e rótulos de quantidade) |
| 3. Análise de Gargalos no Fluxo (WIP) | Texto explicativo + gráfico de barras com tarefas pendentes por status (exclui concluídas/canceladas) (mesma página que a seção 4, quando existir) |
| 4. Demandas por Unidade de Negócio | Gráfico de barras por BU (com valores nas barras) |
| 5. Alinhamento Estratégico (70/20/10) | Texto e gráfico comparando realizado vs alvos 70/20/10 (Categoria de Atuação) |
| 6. Intersecção Negócio vs. Área | **Heatmap** BU × Área Atendida (exibido apenas se ambas as colunas existirem no CSV) |
| 7. Tabela de tarefas | Subtabelas: sprint encerrada (7.1), backlog e próximas sprints (7.3), concluídas (7.4) — todo o CSV |

## Regras de negócio resumidas

- **Conclusão (sumário):** contagem de linhas cujo `Status` contém a substring `conclu` (ex.: “Concluído”), case insensitive.
- **Solicitantes:** depois de escolher Slack ou Relator, os rótulos são **unificados**: e-mails em minúsculas; se existir `local@domínio` e também só `local`, agregam-se ao mesmo e-mail canónico (menor string lexicográfica entre e-mails da mesma parte local). No gráfico, no máximo **8** categorias visíveis; o resto entra em **Outros**.
- **Gargalos:** exclui status com `conclu` ou `cancel` no texto.
- **matplotlib:** cada gráfico deve usar figura própria com `plt.close()` após `savefig`, para não sobrepor gráficos (ex.: pizza + barras BU no mesmo PNG).

## Identidade visual LWSA (template PowerPoint)

Se existir um dos ficheiros abaixo **na pasta do projeto** (ou em `assets/`), o PDF usa automaticamente a **paleta do tema** e até **dois logótipos** extraídos das imagens embutidas no `.pptx`:

- `Templete - LWSA.pptx`
- `Template - LWSA.pptx`
- `assets/Templete - LWSA.pptx`
- `assets/Template - LWSA.pptx`

Comportamento:

- Cores lidas de `ppt/theme/theme*.xml` (destaque em **accent1** / **accent2**).
- **Plano de fundo**: **prioridade** ao ficheiro **`Templete - LWSA.png`** (ou `Template - LWSA.png`, também em `assets/`) na pasta do projeto — A4 em retrato, desenhado em **todas as páginas** a página inteira, por baixo do conteúdo. O rodapé (faixa escura, linha ciano) já vem no PNG: o PDF **não** redesenha a faixa azul e coloca **“Pagina N”** em branco sobre a zona inferior. **Se** não existir esse PNG mas existir o `.pptx`, usa-se o **slide 9** rasterizado para `._lwsa_cache/slide9_background.png` (Pillow por defeito; opcional **`LWSA_USE_PPT_COM=1`** no Windows com PowerPoint para maior fidelidade).
- **Marca de água (slide 6)**: só é usada **se** não houver **nem** o PNG estático **nem** o fundo gerado a partir do slide 9.
- **Topo**: sem faixa nem logótipos de cabeçalho além do fundo quando existe template.
- **Rodapé**: o texto **“Pagina N”** vai em **preto** sobre o **fundo branco** da página, **por cima** de uma **faixa fina** em **#011431** (RGB 1, 20, 49) colada ao fundo. A espessura da faixa é **proporcional** à altura medida no **slide 8** do `.pptx` (~22 %, entre 4 e 8 mm). **Sem o PowerPoint** ou se a leitura falhar, a faixa usa **~6 mm** (constantes em `gerador_report.py`).
- **Títulos de capítulo** com faixa colorida: versão mais clara do accent (paleta do tema).

Os ficheiros extraídos em `._lwsa_cache/` (logos, `slide9_background.png` se aplicável, `watermark_slide6.png` se aplicável) mantêm-se para uso futuro. A **cor** do rodapé mantém-se **#011431** em `gerador_report.py`. Os títulos de secção usam **um único** fundo claro LWSA (`LWSA_SECTION_TITLE_FILL_RGB` em `gerador_report.py`).

## Personalização rápida

- Alvos 70/20/10: constantes `ALVO_PRODUTO`, `ALVO_MELHORIAS`, `ALVO_INOVACAO`.
- Limite vertical no PDF para encaixar imagens: `PDF_Y_CONTEUDO_MAX`.
- Fundo PNG estático: coloque `Templete - LWSA.png` junto ao script; ajuste `FOOTER_PAGE_NUM_ON_STATIC_BG_FROM_BOTTOM_MM` em `gerador_report.py` se o número da página desalinhado da faixa.
- Fundo via slide 9 (fallback): `LWSA_USE_PPT_COM` (ver acima); resolução Pillow em `render_slide_to_png_pillow` (`px_width`).
- Marca de água (fallback slide 6): `WATERMARK_PAGE_HEIGHT_FRAC` e `WATERMARK_RIGHT_INSET_MM` em `gerador_report.py`; `alpha_mult` em `extract_watermark_from_slide` (`branding_lwsa.py`).
- Outro ficheiro CSV: altere a chamada em `if __name__ == "__main__":` ou importe `processar_e_gerar_pdf` noutro módulo.

## Limitações conhecidas

- PDF com fontes core (Helvetica): caracteres fora de Latin-1 nas células podem falhar; o código evita alguns símbolos problemáticos na tabela (ex.: separador `-` entre chave e resumo).
- Nome das colunas deve ser compatível com o export Jira em português; colunas em inglês podem exigir ajuste das constantes ou da lógica `_resolve_col_*`.

## Ficheiros do projeto

| Ficheiro | Função |
|----------|--------|
| `gerador_report.py` | Lógica completa: leitura CSV, gráficos, montagem PDF |
| `branding_lwsa.py` | Leitura do template LWSA (`.pptx` + `Templete - LWSA.png`, cores, logos, fundos) para o PDF |
| `Jira.csv` | Dados de entrada (exemplo / export atual) |
| `requirements.txt` | Dependências pip |
| `README.md` | Esta documentação |
