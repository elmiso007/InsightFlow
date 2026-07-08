# Arquitetura — Sistema de Análise NPS

## 1. Visão geral

A aplicação é composta por módulos para:
- leitura de configurações;
- conexão com o banco de dados;
- extração de atendimentos e avaliações;
- cálculo de NPS;
- análise de IA via Gemini;
- análise estatística de detratores WOZ (sem IA);
- geração de relatórios e logs.

## 2. Módulos principais

### 2.1 config.py
Responsável por carregar variáveis de ambiente e centralizar regras de configuração.
O schema do banco é controlado por `DB_SCHEMA` (padrão: `lw_octadesk`).

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
- executar a limpeza automática de registros antigos (`limpar_rawdata_antigos`);
- promover rawdata → `analise_nps_analistas` via `executar_sql_pos_analise(conn)`.

Função de idempotência:
- `analise_ja_existe(analista, inicio, fim)` — consulta `rawdata_analise_nps_analistas` antes de processar; retorna `True` se já há registro para o analista no período.

Função de promoção (chamada uma única vez por execução, não por analista):
- `executar_sql_pos_analise(conn)` — executa `insereDadosAnaliseNPS.sql` após todos os analistas serem processados, promovendo rawdata → `analise_nps_analistas`.

Contagem de tokens: valores reais lidos de `response.usage_metadata.prompt_token_count` e
`candidates_token_count`; estimativa por palavras usada apenas como fallback.

### 2.5 verifica_nps.py
É o orquestrador principal do fluxo. Todo o código de execução está encapsulado em `main()`;
o módulo não executa nada quando importado.

Ele executa:
1. configuração e logging;
2. leitura das avaliações (query inicial — `vw_report_diario` + NPS);
3. cálculo de NPS por analista;
4. identificação de analistas críticos (NPS < meta);
5. para cada analista, via `ThreadPoolExecutor(max_workers=PARALELO_MAX_WORKERS)`:
   - verifica idempotência com lock de threading (`_analise_lock` + `_analises_em_andamento`) — pula se já existe ou já está sendo processado por outro worker;
   - busca conversas individuais com `LIMIT ANALISE_MAX_ATENDIMENTOS_POR_ANALISTA`;
   - envia para análise de IA (Gemini);
   - grava resultado no banco;
6. chama `executar_sql_pos_analise(conn)` uma única vez após todos os futures completarem;
7. análise comparativa consolidada;
8. limpeza automática de rawdata antigos.

O threading lock (`_analise_lock`) garante que dois workers não iniciem a análise do mesmo
analista simultaneamente, mesmo que ambos passem pela verificação de banco ao mesmo tempo.

### 2.6 analise_woz_detratores.py
Script independente para análise estatística de comentários sobre atendimento automatizado.
Não usa IA — opera exclusivamente sobre os dados do banco.

Fluxo:
1. recebe `--ano`, `--t1`, `--t2` via argparse;
2. busca comentários NPS com termos WOZ via SQL ILIKE (woz, robô, chatbot, automático, virtual, etc.);
3. classifica cada comentário: Promotor (≥9) / Neutro (7-8) / Detrator (≤6);
4. calcula métricas por trimestre e variação entre T1 e T2;
5. gera relatório HTML em `woz_detratores/`;
6. persiste em `analise_nps_analistas` com `analise_tipo = 'woz_detratores_trimestral'` — idempotente por `request_id = woz_{ano}_T{t1}_vs_T{t2}`;
7. atualiza `woz_detratores/historico.json` somente se o banco persistiu com sucesso.

## 3. Tabela unificada e discriminador `analise_tipo`

Todos os resultados de análise vivem em uma única tabela: `lw_octadesk.analise_nps_analistas`.
O campo `analise_tipo` distingue a origem:

| `analise_tipo` | Script | Descrição |
|---|---|---|
| `monitoramento_nps_analistas` | `analise_ia.py` via `verifica_nps.py` | Análise por analista gerada pelo Gemini |
| `woz_detratores_trimestral` | `analise_woz_detratores.py` | Comparativo trimestral WOZ (estatístico) |

O rawdata (`rawdata_analise_nps_analistas`) é usado apenas como rascunho intermediário para
o fluxo NPS de analistas — não pelo fluxo WOZ.

## 4. Fluxo de dados

```text
.env
  ↓
config.py
  ↓
┌───────────────────────────────┐   ┌─────────────────────────────────┐
│  verifica_nps.py  (main())    │   │  analise_woz_detratores.py      │
│                               │   │  python script.py --ano --t1 --t2│
│  conecta_banco.py → PostgreSQL│   │  conecta_banco.py → PostgreSQL  │
│  get_atendimentos_nps.py      │   │  SQL ILIKE termos WOZ           │
│  analise_ia.py → Gemini       │   │  classificação + métricas       │
│  executar_sql_pos_analise()   │   │  salvar_no_banco() → banco      │
│  (uma vez, pós-ThreadPool)    │   │  salvar_historico() → JSON      │
└───────────────────────────────┘   └─────────────────────────────────┘
               ↓                                   ↓
       ┌───────────────────────────────────────────────┐
       │  PostgreSQL — lw_octadesk                     │
       │  • rawdata_analise_nps_analistas (rascunho)   │
       │  • analise_nps_analistas                      │
       │    analise_tipo='monitoramento_nps_analistas' │
       │    analise_tipo='woz_detratores_trimestral'   │
       └───────────────────────────────────────────────┘
```

## 5. Dependências externas

- PostgreSQL (schema `lw_octadesk`)
- Google Gemini API (apenas no fluxo NPS de analistas)
- pandas para tratamento de dados
- SQLAlchemy / psycopg2 para conexão
- python-dotenv para configuração
- holidays para calendário

## 6. Pontos de extensão

A arquitetura permite evoluir o sistema com:
- novas fontes de dados;
- novas regras de filtro e meta;
- novos formatos de saída (HTML, PDF, Slack, e-mail);
- novos modelos de IA ou múltiplas fontes de análise;
- novos tipos de análise estatística adicionando um novo `analise_tipo`.

## 7. Observações de manutenção

- o fluxo principal deve permanecer orquestrado em `verifica_nps.py` (dentro de `main()`);
- regras e configurações devem permanecer centralizadas em `config.py`;
- `executar_sql_pos_analise()` deve ser chamado **uma única vez** por execução, após o ThreadPoolExecutor — nunca dentro de loops por analista;
- toda nova lógica de negócio deve ser documentada em `docs/`.
