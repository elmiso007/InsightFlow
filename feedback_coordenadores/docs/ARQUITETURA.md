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

Funções principais:
- `get_atendimentos_analista_individual(analista, inicio, fim)` — query individual por analista com `LIMIT ANALISE_MAX_ATENDIMENTOS_POR_ANALISTA`, executa em thread própria com conexão isolada;
- `_dados_sensiveis(interacoes)` — anonimizador compartilhado entre as funções de busca;
- `drop_duplicates(subset=['Protocolo'])` aplicado após cada query para eliminar protocolos duplicados de JOINs.

### 2.4 analise_ia.py
Responsável por:
- construir prompts para a API Gemini;
- processar a resposta da IA e extrair as 6 seções estruturadas via regex tolerante a `*` e `**`;
- converter markdown para HTML com tabelas coloridas por tipo;
- gerar relatórios HTML individuais por analista e índice geral;
- calcular a análise comparativa usando a fórmula NPS real (promotores − detratores) / total, em vez de média de notas;
- executar a limpeza automática de registros antigos (`limpar_rawdata_antigos`).

Função de idempotência:
- `analise_ja_existe(analista, inicio, fim)` — consulta `rawdata_analise_nps_analistas` antes de processar; retorna `True` se já há registro para o analista no período, evitando duplicação e permitindo re-execução segura.

### 2.5 verifica_nps.py
É o orquestrador principal do fluxo.

Ele executa:
1. configuração e logging;
2. leitura das avaliações (query inicial — `vw_report_diario` + NPS);
3. cálculo de NPS por analista;
4. identificação de analistas críticos (NPS < meta);
5. para cada analista, via `ThreadPoolExecutor(max_workers=PARALELO_MAX_WORKERS)`:
   - verifica idempotência (`analise_ja_existe`) — pula se já existe;
   - busca conversas individuais com `LIMIT ANALISE_MAX_ATENDIMENTOS_POR_ANALISTA`;
   - envia para análise de IA (Gemini);
   - grava resultado no banco;
6. análise comparativa consolidada;
7. limpeza automática de rawdata antigos.

O uso de `ThreadPoolExecutor` garante que múltiplos analistas sejam processados simultaneamente, e cada thread abre e fecha sua própria conexão com o banco (thread-safe).

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
