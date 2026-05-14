# Report Semanal

Pipeline em Python que gera relatórios semanais de atendimento (Suporte e Cobrança),
combinando métricas operacionais com análises geradas por IA (GPT-4o-mini), e envia
o resultado em PDF por e-mail.

## Funcionalidades

- Extrai dados de atendimento, NPS e incidentes de um banco PostgreSQL
- Calcula métricas operacionais (TMA, TME, taxa de abandono, volume) por setor, canal e equipe
- Gera análises qualitativas via OpenAI (contatos, NPS, comentários, WOZ)
- Produz PDF executivo com tabelas, gráficos e seções narrativas
- Envia o PDF por e-mail (Gmail SMTP) para uma lista configurável

## Pré-requisitos

- Python 3.10 ou superior
- PostgreSQL acessível com as views/tabelas esperadas (ver seção "Schemas")
- Conta Gmail com App Password habilitada
- Bot do Slack com `chat:write` (caso queira notificar canal)
- Chave de API da OpenAI

## Instalação

```bash
# 1. Clone o repositorio
git clone <url-do-repo>
cd report_semanal

# 2. Crie e ative um virtualenv (recomendado)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# 3. Instale as dependencias
pip install -r requirements.txt
```

## Configuração

1. Copie o modelo:

   ```bash
   cp config.ini.example config.ini
   ```

2. Preencha o `config.ini` com seus valores reais (banco, OpenAI, Slack, Gmail, destinatários).

3. **Onde colocar o `config.ini`**: por padrão, o `app.py` procura o arquivo
   em `../../config.ini` (dois níveis acima do diretório onde está o script).
   Isso é uma convenção do monorepo original. Se você for usar este projeto
   como repositório standalone, mova o `config.ini` para essa localização ou
   ajuste a linha em `app.py`:

   ```python
   config_file_path = sql_path.parent.parent / 'config.ini'   # padrão
   # config_file_path = sql_path / 'config.ini'                # standalone na raiz
   ```

4. O `config.ini` **nunca deve ser versionado** — já está no `.gitignore`.

## Execução

```bash
python app.py
```

Ou via o utilitário:

```cmd
ExecutaApp.bat
```

O script vai:

1. Conectar no Postgres e extrair os dados das views
2. Calcular métricas para Suporte e Cobrança
3. Chamar a OpenAI 4 vezes por setor (contatos semanal, anual, NPS, comentários, WOZ)
4. Gerar PDFs em `Reports/`
5. Enviar os PDFs por e-mail para os destinatários configurados

## Estrutura de arquivos

```
report_semanal/
├── app.py                  # Orquestrador principal
├── openai.py               # Cliente da API OpenAI
├── gerarpdf.py             # Montagem do PDF (reportlab + matplotlib)
├── function_logger.py      # Configuração de logging
├── ExecutaApp.bat          # Atalho de execução (Windows)
├── requirements.txt        # Dependências Python
├── config.ini.example      # Modelo de configuração
├── prompts/                # Prompts em Markdown para as análises de IA
│   ├── analise_contatos_semanal.md
│   ├── analise_contatos_anual.md
│   ├── analise_contatos_cobranca.md
│   ├── analise_nps_semanal.md
│   ├── analise_nps_cobranca.md
│   ├── analise_comentarios.md
│   ├── analise_comentarios_cobranca.md
│   └── analise_woz_semanal.md
├── Documentação/
│   └── Documentacao_Report_Semanal.md
└── Reports/                # PDFs gerados (criado em runtime, gitignored)
```

## Schemas e tabelas esperadas

O `app.py` consulta três objetos no Postgres:

| Query | Objeto | Conteúdo esperado |
|-------|--------|-------------------|
| `query` | `<schema_octadesk>.vw_report_semanal` | View com contatos do Octadesk |
| `query_2` | `<schema_octadesk>.vw_woz` | View com casos WOZ resolvidos |
| `query_3` | `<schema_servicenow>.service_now_incidentes` | Tabela de incidentes do ServiceNow |

Os schemas são configuráveis em `[report_semanal]` do `config.ini`.

## Logs

A aplicação grava em `logs.log` (no mesmo diretório do `app.py`).
O arquivo é ignorado pelo `.gitignore` (regra `*.log`).

## Segurança

- **Não commite o `config.ini`** — ele contém credenciais
- **Não commite PDFs gerados** — eles podem conter dados de clientes (LGPD)
- A pasta `Reports/` deve estar no `.gitignore`
- Para rotacionar credenciais expostas previamente, use `git filter-repo`
