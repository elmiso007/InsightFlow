# Arquitetura — Sistema de Análise NPS

## 1. Visão geral

A aplicação é composta por módulos para:
- leitura de configurações;
- conexão com o banco de dados;
- extração de atendimentos e avaliações;
- cálculo de NPS;
- análise de IA via Gemini;
- geração de relatórios e logs.

## 2. Módulos principais

### 2.1 config.py
Responsável por carregar variáveis de ambiente e centralizar regras de configuração.

### 2.2 conecta_banco.py
Responsável por criar e reutilizar conexões ao PostgreSQL, com suporte a SQLAlchemy e psycopg2.

### 2.3 get_atendimentos_nps.py
Responsável por:
- recuperar atendimentos e comentários dos analistas críticos;
- aplicar anonimização de dados sensíveis;
- montar o conteúdo textual consumido pela IA.

### 2.4 analise_ia.py
Responsável por:
- construir prompts para a API Gemini;
- processar a resposta da IA;
- gerar conteúdo estruturado para relatórios e análises.

### 2.5 verifica_nps.py
É o orquestrador principal do fluxo.

Ele executa:
1. configuração e logging;
2. leitura das avaliações;
3. cálculo de NPS;
4. identificação de analistas críticos;
5. busca de conversas;
6. análise por IA;
7. gravação do resultado.

## 3. Fluxo de dados

```text
.env
  ↓
config.py
  ↓
verifica_nps.py
  ↓
conecta_banco.py → PostgreSQL
  ↓
get_atendimentos_nps.py → conversas e contexto
  ↓
analise_ia.py → Google Gemini
  ↓
relatórios / logs / banco
```

## 4. Dependências externas

- PostgreSQL
- Google Gemini API
- biblioteca pandas para tratamento de dados
- SQLAlchemy / psycopg2 para conexão
- python-dotenv para configuração
- holidays para calendário

## 5. Pontos de extensão

A arquitetura permite evoluir o sistema com:
- novas fontes de dados;
- novas regras de filtro e meta;
- novos formatos de saída (HTML, PDF, Slack, e-mail);
- novos modelos de IA ou múltiplas fontes de análise.

## 6. Observações de manutenção

- o fluxo principal deve permanecer orquestrado em `verifica_nps.py`;
- regras e configurações devem permanecer centralizadas;
- toda nova lógica de negócio deve ser documentada em `docs/`.
