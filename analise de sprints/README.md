# Relatório de Status da Sprint

Aplicação para gerar **Relatório de Status da Equipe** para gerência e coordenação, a partir de um arquivo CSV exportado. **Por padrão**, o CSV é enviado ao **Gemini** para análise: o relatório traz **insights sobre produtividade e alinhamento estratégico**, não apenas listas de tarefas. A saída é gerada em **PDF** na pasta da aplicação.

## Requisitos

- Python 3.10+
- pandas, markdown, xhtml2pdf, **pypdf** (união das páginas do PDF)
- **Gemini (recomendado):** `google-genai` e chave de API para relatório com insights

Sempre que o PDF é gerado, o texto completo do relatório também é salvo em **`relatorio_sprint.md`** na mesma pasta (útil se o PDF parecer cortado ou para revisar o conteúdo integral).

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

### Onde fica o CSV

O arquivo CSV deve ficar na **pasta base da aplicação** (a mesma pasta onde está o `app.py`), por exemplo:

- `C:\Users\...\analise de sprints\Jira.csv`

Se você informar só o nome do arquivo (ex.: `Jira.csv`), a aplicação procura esse arquivo nessa pasta. Se omitir o nome do arquivo, é usado **Jira.csv** por padrão.

### Configurar o Gemini (relatório com insights)

Para o relatório com **insights de produtividade e alinhamento estratégico**, configure a chave do Gemini:

1. Obtenha uma chave em [Google AI Studio](https://aistudio.google.com/apikey).
2. Crie o arquivo `config.ini` na pasta da aplicação (copie de `config.example.ini`) e preencha:
   ```ini
   [gemini]
   api_key=SUA_CHAVE_AQUI
   ```
   Ou defina a variável de ambiente: `GEMINI_API_KEY=SUA_CHAVE_AQUI`.

Se a chave não estiver configurada, a aplicação gera o relatório **programático** (sem IA) e exibe uma dica.

### Linha de comando

```bash
# Gera relatório com Gemini (insights) e salva relatorio_sprint.pdf na pasta da aplicação
python app.py

# Com título da sprint
python app.py -t "Sprint 02 - Mar/2025"

# Relatório apenas programático (sem enviar dados ao Gemini)
python app.py --local

# Salvar em outro arquivo
python app.py -o meu_relatorio.pdf
```

### Parâmetros

| Parâmetro | Descrição |
|-----------|-----------|
| `csv` | Nome ou caminho do arquivo CSV (opcional; padrão: **Jira.csv** na pasta da aplicação) |
| `-o`, `--output` | Arquivo de saída PDF ou .md (opcional; padrão: **relatorio_sprint.pdf** na pasta da aplicação) |
| `-t`, `--titulo` | Título da sprint no relatório (ex.: "Sprint 12 - Mar/2025") |
| `-e`, `--encoding` | Encoding do CSV (`utf-8`, `latin-1`, `cp1252`, etc.) |
| `--local` | Gera só o relatório programático, sem enviar dados ao Gemini |

## Formato esperado do CSV

O CSV deve conter colunas que serão reconhecidas automaticamente (nomes flexíveis). Exemplos de nomes aceitos:

| Conceito | Exemplos de nome da coluna no CSV |
|----------|-----------------------------------|
| **Status** | `Status`, `Situação` |
| **Natureza** | `Natureza do Item`, `Campo personalizado (Natureza do item)`, `Natureza`, `Tipo` |
| **BU** | `Unidade de Negócio`, `Campo personalizado (Business Unity)`, `BU`, `Unidade` |
| **Categoria** | `Categoria de Atuação`, `Campo personalizado (Categoria de Atuação)`, `Categoria` |
| **Título** | `Título`, `Descrição`, `Item`, `Nome` |
| **Comentários** | `Comentários`, `Observações`, `Notas` |

### Valores esperados (orientação)

- **Status:** itens com valor equivalente a "Concluído" (ex.: Concluído, concluido, Done) entram no percentual de conclusão e nos destaques.
- **Natureza do Item:** "Planejada" vs "Não-planejada" (ou "Não planejada") para o comparativo e análise de riscos.
- **Unidade de Negócio:** Locaweb, KingHost, Octadesk, Vindi (ou outros que você usar).
- **Categoria de Atuação:** para a regra 70/20/10, use categorias que contenham, por exemplo:
  - *Desenvolvimento de Produto* (alvo 70%)
  - *Melhorias Técnicas* (alvo 20%)
  - *Inovação / Experimentação* (alvo 10%)

Separador do CSV: vírgula (`,`) ou ponto e vírgula (`;`) são detectados automaticamente.

## Estrutura do relatório gerado

1. **Sumário Executivo** – Total de itens, % conclusão, Planejadas vs Não-planejadas  
2. **Visão por BU** – Quantidade por Locaweb, KingHost, Octadesk, Vindi e destaque da BU com mais esforço  
3. **Alinhamento Estratégico (70/20/10)** – Distribuição por Categoria de Atuação e comentário sobre a meta  
4. **Destaques da Sprint** – Até 5 tarefas mais relevantes concluídas, agrupadas por BU  
5. **Análise de Saúde e Riscos** – Volume de não-planejadas e observações da coluna Comentários  
6. **Próximos Passos** – Itens não concluídos ou planejados para a próxima sprint  

O arquivo de saída é gerado em **PDF** (ou .md se `-o arquivo.md`). Com o Gemini, cada seção inclui **insights** e **recomendações** para coordenação e gerência.

## Exemplo mínimo de CSV

```csv
Status;Natureza do Item;Unidade de Negócio;Categoria de Atuação;Título;Comentários
Concluído;Planejada;Locaweb;Desenvolvimento de Produto;Nova API de assinaturas;
Concluído;Não-planejada;KingHost;Melhorias Técnicas;Ajuste performance DB;Urgente
Em andamento;Planejada;Octadesk;Inovação;POC novo chat;
```

Há um arquivo de exemplo em `exemplo_sprint.csv` para teste.
