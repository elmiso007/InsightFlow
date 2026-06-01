# Glossário — Motor Prescritivo PRB

Referência rápida dos termos usados no código, comentários e logs do motor.
Organizado em 5 categorias. Termos em sigla incluem expansão; definições curtas.

---

## 1. ITSM / ITIL (framework universal)

- **ITSM** — _Information Technology Service Management_. Conjunto de práticas
  para gerenciar serviços de TI. ITIL é o framework mais conhecido.

- **ITIL** — _Information Technology Infrastructure Library_. Framework de
  boas práticas para ITSM. Define termos como Incidente, Problema, Mudança,
  Item de Configuração, etc.

- **CI** — _Configuration Item_ (Item de Configuração). Qualquer componente
  gerenciado pela TI que pode ser causa ou alvo de um incidente: servidor,
  VPS, serviço, banco, roteador, software. No nosso código corresponde ao
  campo `servidor` no `Incidente`.

- **CMDB** — _Configuration Management Database_. Base que centraliza todos
  os CIs e suas relações. No ServiceNow é a tabela `cmdb_ci`.

- **OLA** — _Operational Level Agreement_. Acordo interno (time A entrega para
  time B em X horas). Usado nas regras: "Reclame Aqui sem contorno e OLA
  estourado → P1".

- **SLA** — _Service Level Agreement_. Acordo entre Locaweb e cliente (resolver
  em X horas). Mais visível externamente que OLA.

- **Incident (INC)** — Evento que interrompe ou degrada serviço. Resolvido com
  o objetivo de **restaurar o serviço**, não necessariamente entender a causa.

- **Problem (PRB)** — Causa raiz de um ou mais incidentes. Resolvido com o
  objetivo de **eliminar permanentemente** a recorrência.

- **Request (RITM)** — _Request Item_. Solicitação de serviço (não é falha):
  pedido de upgrade, instalação, acesso. Não tratado por este motor.

- **Workaround / Solução de Contorno** — Solução temporária que mitiga o
  sintoma sem eliminar a causa. Campo crítico para a matriz P1-P5.

- **Work notes** — Anotações cronológicas adicionadas à INC/PRB durante o
  atendimento. No banco vem na coluna `atualizacoes` (texto livre).

---

## 2. ServiceNow & Dynamics (ferramentas)

- **ServiceNow (SNow)** — Plataforma de ITSM da Locaweb. Origem das tabelas
  `lwsa.service_now_incidentes` e `lwsa.service_now_problemas`.

- **sysparm_query** — Query DSL nativa do ServiceNow para REST API. Não usado
  neste projeto (lemos do banco via ETL upstream).

- **cmdb_ci** — Coluna padrão do SNow que referencia o CI afetado. Aparece no
  banco como `servidor`.

- **breach_time** — Campo nativo do SNow que indica quando o SLA será estourado.
  Hoje não está na nossa DDL — substituído por heurística
  `_ola_estourado_implicito` em `rules_engine.py`.

- **Dynamics 365** — CRM da Microsoft, usado pela Locaweb para chamados de
  cliente. No banco está como `dynamics.chamados`.

- **OData / Web API** — Protocolo de consulta REST do Dynamics. Não usado
  diretamente — lemos via banco já ingerido.

---

## 3. Conceitos do Motor PRB-INC (projeto interno)

- **Cluster** — Grupo de INCs semanticamente similares, formado por TF-IDF +
  DBSCAN. Carrega métricas agregadas (qtd_incs, scores, CIs recorrentes).

- **Score de Criticidade** — Número 0-1 que reflete a gravidade do cluster.
  Composição de 4 sinais: volume + indisponibilidade + sem contorno +
  recorrência. Pesos em `config.py`.

- **Score de Ineficiência** — Número 0-1 que reflete o quanto o time está
  "patinando" no cluster. Composição de 2 sinais: volume de updates +
  velocidade (updates/hora).

- **Saúde do Cliente** — Módulo que avalia clientes recorrentes (≥3 INCs em
  6 meses) e emite veredicto operacional via `alerta_recorrencia_alta`.
  Consolida histórico ServiceNow + chamados em linha do tempo cronológica.
  Inspirado em "customer health score" de plataformas CSM (Gainsight,
  HubSpot). Implementado em `customer_monitor.py` via classe `SaudeCliente`
  e função `gerar_saude_clientes`. Requisito Emerson/Bruno.

- **Gatilho Proativo** — Regra do motor: ≥5 INCs P3 idênticas no mesmo cluster
  → promove para P2 e sugere abertura de PRB **antes** que escale.

- **Repriorização** — Quando o motor detecta que um PRB existente em P3 já
  bate critérios de P2 (ou similar), sugere "mudar de P3 para P2". Requisito
  Jéssica.

- **Janela móvel** — Período relativo ao instante atual: "últimas 24h",
  "últimos 15 dias". Recalculada a cada execução. Diferente de janela fixa
  ("janeiro de 2026").

- **Mock mode** — Quando `USAR_MOCKS=true`, os extractors devolvem dados
  sintéticos coerentes em vez de tocar o banco. Default em desenvolvimento.

- **Registry declarativo** — `TABELAS_CHAMADOS_POR_ORGANIZACAO` no `config.py`.
  Cada organização declara schema/tabela/colunas; o extractor itera o dict.
  Adicionar nova organização = editar dict, sem código novo.

- **Roteamento por organização** — Coluna `organizacao` em INCs/PRBs determina
  qual tabela de chamados consultar (Locaweb → `dynamics.chamados`,
  Kinghost → `kinghost.chamados`).

- **OLA estourado implícito** — Heurística no `rules_engine` que infere
  estouro de OLA via `score_ineficiencia >= 0.6 + qtd_sem_contorno > 0`. Proxy
  para o campo `breach_time` que não temos no banco.

- **Singleton (em clusterização)** — Cluster de tamanho 1. INC isolada que o
  DBSCAN marcou como `label=-1`. Convertida em cluster próprio com chave
  `singleton-INCxxxx` para não perder o sinal.

- **ValidadorEntrega (prisma retrospectivo)** — Módulo que olha PRBs já
  encerrados pelo Change Team e verifica se o problema realmente foi
  resolvido. Implementado em `validador_entrega.py`, entry-point separado
  `validar_entregas.py` (cadência default 6h). Complementa o prisma
  preventivo do `rules_engine` — fecha o loop de qualidade do fix.

- **Veredictos do ValidadorEntrega**
  - `REINCIDENCIA` — ≥`LIMIAR_INCS_REINCIDENCIA` (3) INCs no mesmo
    (produto, servidor) **após** `data_encerrado`. Dispara Slack para CT.
  - `ENTREGA_VALIDADA` — 0 INCs pós-resolução **E** janela ≥
    `MIN_DIAS_PARA_VALIDAR` (7 dias) decorridos. Confirma que o fix segurou.
  - `INCONCLUSIVO` — caso intermediário (janela curta, INCs sub-limiar). Continua
    sob observação até próxima rodada.

---

## 4. ML / NLP (analyzer)

- **TF-IDF** — _Term Frequency × Inverse Document Frequency_. Técnica para
  transformar texto em vetores numéricos ponderando palavras por sua
  raridade entre documentos. Implementação via `sklearn.TfidfVectorizer`.

- **DBSCAN** — _Density-Based Spatial Clustering of Applications with Noise_.
  Algoritmo de clusterização que descobre o número de clusters automaticamente
  e identifica outliers como "ruído". Parâmetros: `eps` (raio) e `min_samples`.

- **eps** (DBSCAN) — Raio de vizinhança. Dois pontos são vizinhos se distância
  cosseno < eps. Calibrado em 0.55 (config). Mais alto = clusters maiores.

- **k-means** — Alternativa clássica ao DBSCAN. Descartada aqui porque exige
  número fixo de clusters (não temos como saber antecipadamente).

- **Cosine similarity / distance** — Mede ângulo entre vetores em vez de
  distância euclidiana. Padrão em NLP — ignora magnitude (tamanho do texto)
  e foca em direção (tema).

- **Bag of Words** — Representação simples: contar quantas vezes cada palavra
  aparece no documento. TF-IDF é um refinamento que ponderado por raridade.

- **N-gram** — Sequência de N palavras consecutivas. `ngram_range=(1,2)` no
  TF-IDF gera unigrams (palavras) e bigrams (pares como "kernel panic").

- **Stop-words** — Palavras gramaticais de alta frequência mas baixo valor
  semântico (artigos, preposições, conjunções). Removidas antes do TF-IDF.
  Lista PT-BR customizada em `analyzer._STOP_WORDS_PT`.

- **Stemming** — Reduzir palavras à raiz (`servidores` → `servidor`). **Não
  usado neste projeto** — vocabulário técnico já é consistente.

- **Jaccard similarity** — Medida simples: `|interseção| / |união|` entre
  conjuntos de tokens. Fallback se sklearn não estiver disponível.

- **NFKD** — Forma de normalização Unicode (Decomposição Compatível). Usada
  para separar letras acentuadas em "letra base + sinal diacrítico" e
  remover o sinal — efetivamente eliminando acentos.

---

## 5. Locaweb-específico

- **CAL** — Central de Atendimento Locaweb. Produto do portfolio. Aparece
  em `config.TERMOS_CONTRATACAO` por estar associada a fluxos de contratação.

- **Painel do Produto** — Interface do cliente para gerenciar serviços
  contratados. Indisponibilidade → critério P1 ou P2.

- **Central do Cliente** — Portal de autoatendimento da Locaweb.

- **Reclame Aqui** — Site público de avaliação de empresas. Cliente que abre
  reclamação no RA tem prioridade elevada na matriz oficial P1-P5 ("Reclame
  Aqui sem contorno → P2", "Reclame Aqui + OLA estourado → P1").

- **Locaweb / Kinghost** — Duas organizações cujos chamados moram em tabelas
  separadas no mesmo banco (`dynamics.chamados` e `kinghost.chamados`).

- **NOC** — _Network Operations Center_. Time de plantão 24/7 que monitora
  infraestrutura. Aparece como valor típico em `grupo_designado`.

- **Service Operation** — Time responsável pela operação cotidiana dos
  serviços. Outro valor comum em `grupo_designado`.

- **lw_octadesk.classificacoes** — Tabela auxiliar usada para derivar o
  `produto` em chamados Locaweb via JOIN pelos 5 níveis hierárquicos
  (`nivel1` … `nivel5`).

- **locapredict** — Projeto irmão do Motor PRB-INC (em
  `MRP para PRB/locapredict`). Foco em insights históricos semanais com
  sentence-transformers + HDBSCAN. Compartilha o `config.ini` para acesso ao
  banco.

---

## Limitações reais (revisitar com evidência de uso)

Coisas que **podem virar problema** em produção e merecem revisão quando houver
dados reais. Cada uma tem caminho técnico para mitigar.

### Motor stateless (sem persistência entre ciclos)

Cada ciclo recalcula do zero. Não detecta escalada gradual, não evita alertas
repetidos, não rastreia tendência do cliente.

**Quando resolver:** quando o feedback de uso indicar necessidade específica
(ex.: time pedir "quero ver tendência de saúde do cliente nas últimas semanas").

**Caminho:** persistir `ExecucaoMotor` em banco ou arquivo. Adicionar comparação
entre ciclos.

### Repetição de alertas Slack entre ciclos (alert fatigue)

Cluster crítico dispara o mesmo alerta a cada 15 min até alguém abrir o PRB.
Em 1 dia: 96 mensagens idênticas. Problema operacional real.

**Mitigação imediata (sem código):** configurar canal Slack para silenciar
mensagens similares por 1 hora.

**Caminho real:**
- Persistir hash do alerta enviado por N ciclos.
- OU integrar com SNow para verificar se PRB foi aberto/atualizado.

**Nota:** o problema análogo na Saúde do Cliente já foi resolvido via critério
de recência. Para PRBs, recência não funciona — o PRB **deveria** ser tratado,
não "acalmar sozinho".

### Sem retry/backoff em falhas de rede

Se SNow/Slack/banco falhar uma vez, o motor abandona aquela operação. Próximo
ciclo (15 min) tenta de novo.

**Quando resolver:** se aparecer evidência de muitos `WARNING` de falha
transitória nos logs.

**Caminho:** lib `tenacity` com `@retry(stop=stop_after_attempt(3))`.

### Sem health check endpoint

Não há `GET /health` para load balancer/k8s consultar.

**Mitigação atual:** monitorar timestamp de `output/dashboard_state.json` (se
não atualizou em > 20 min, motor está caído).

**Caminho:** Flask/FastAPI minimalista em thread separada.

### Limiar de Saúde do Cliente único (independente de porte)

Cliente pequeno (1 servidor) e cliente enterprise (50 servidores) usam o
mesmo `LIMIAR_INCS_SAUDE_CLIENTE = 3`. Para enterprise, 3 INCs em 6m pode
ser proporcionalmente trivial.

**Quando resolver:** se time reclamar de alertas excessivos para clientes
grandes.

**Caminho:** limiar ajustado por porte (exige dado de porte no banco).

---

## Decisões de design (não revisitar — comportamento correto)

Itens que **parecem limitações mas são escolhas deliberadas**. Cada um tem
justificativa explícita. Mudar seria **piorar** o motor.

### Sem integração bidirecional com ServiceNow

Motor **lê** do data warehouse, mas não **escreve** no SNow. Não cria PRBs
automaticamente.

**Por que é correto:**
- **Princípio de produto:** motor sugere, humano decide.
- **Segurança:** escrever no SNow exige permissões maiores + auditoria.
- **Risco:** bug no motor poderia criar PRBs falsos em massa.

**Quando reconsiderar:** somente após meses de uso validando que sugestões são
consistentes. Mesmo assim, scope restrito (ex.: só comentários, não criação).

### Sem agrupamento de timeline por dia

50 eventos no histórico do cliente ficam linha por linha no JSON.

**Por que é correto:**
- Agrupamento visual é **responsabilidade do front-end**, não do motor.
- Motor entrega dados estruturados; UI define como apresentar.

**Sem ação necessária.** Front-end implementa quando precisar.

### Cleanup TTL desabilitado por default (sem permissão DELETE)

A conta de banco da Locaweb usada pelo motor **não tem permissão DELETE** nas
tabelas `lwsa.motor_*`. Política comum em ambientes com mínimo privilégio.

**Decisão:** `CLEANUP_TTL_HABILITADO=false` no default. Motor não tenta DELETE
(evita warnings de permissão negada). Tabelas crescem indefinidamente.

**Por que é correto neste contexto:**
- Postgres lida bem com tabelas de até milhões de rows.
- Volume estimado em 1 ano: ~800k rows. Trivial.
- Cleanup pode ser feito **externamente** pela DBA quando necessário:
  ```sql
  DELETE FROM lwsa.motor_execucao
  WHERE timestamp_utc < NOW() - INTERVAL '30 days';
  -- ON DELETE CASCADE remove clusters/prescrições/saúdes vinculados.
  ```
- Para habilitar cleanup no motor: definir env `CLEANUP_TTL_HABILITADO=true`
  E garantir GRANT DELETE para a conta do motor:
  ```sql
  GRANT DELETE ON lwsa.motor_execucao TO <usuario_motor>;
  -- (CASCADE faz o resto)
  ```

### Funções puras no `customer_monitor` (sem persistência/comunicação)

`gerar_saude_clientes` apenas avalia e devolve lista. Não envia, não persiste.

**Por que é correto:**
- Single Responsibility (avalia, não comunica).
- Testabilidade (função pura aceita mocks).
- Reuso (qualquer caller pode invocar sem efeitos colaterais).

---

## Trade-offs em aberto (decisão do time)

Itens onde **não há solução claramente melhor** — depende da cultura ou
preferência operacional do time.

### Agrupamento de alertas Slack (individuais vs. batch)

**Hoje:** cada cluster crítico = 1 mensagem (individual).

**Trade-off:**
- **Individual (atual):** permite thread por cluster, atribuição individual, discussão.
- **Batch:** canal mais limpo em pico, mas perde affordances do Slack.

**Decisão pendente:** depende de cultura do time. Padrão atual é conservador
(individual).

### Canal único vs. múltiplos canais

**Hoje:** tudo vai para `cfg.canal_criticos`.

**Trade-off:**
- **Canal único:** simples, fácil de moderar.
- **Múltiplos canais:** PRBs separados de Saúde do Cliente, mas exige criar
  estrutura no Slack + manter assinaturas.

**Decisão pendente:** esperar demanda concreta antes de fragmentar.

---

## Compatibilidade e migração de versões

Notas técnicas sobre escolhas que dependem de versão de infraestrutura.

### Postgres: `json` em vez de `jsonb` (compatibilidade 9.2/9.3)

**Estado atual:** as tabelas `lwsa.motor_*` usam o tipo `json` (não `jsonb`),
porque o Postgres atual da Locaweb é versão **9.2 ou 9.3**.

**Por que isso importa:**
- `jsonb` foi introduzido no Postgres **9.4** (dezembro/2014).
- Em 9.2/9.3, só existe o tipo `json` (armazena texto literal validado).
- `jsonb` é binário, comprimido, indexável com GIN, e suporta operador `@>`
  (contains). `json` não tem essas vantagens.

**Impacto operacional hoje:** zero. O motor apenas serializa Python → JSON
e armazena. Nenhuma query interna usa operadores específicos de `jsonb`.

**Quando migrar:** quando a infra atualizar para Postgres 9.4+ (recomendado
por motivos de segurança — todas as versões 9 estão EOL desde nov/2021).

**Como migrar (DDL):**

```sql
ALTER TABLE lwsa.motor_execucao
    ALTER COLUMN erros TYPE jsonb USING erros::jsonb;

ALTER TABLE lwsa.motor_cluster
    ALTER COLUMN cis_recorrentes_15d TYPE jsonb USING cis_recorrentes_15d::jsonb,
    ALTER COLUMN termos_dominantes TYPE jsonb USING termos_dominantes::jsonb,
    ALTER COLUMN inc_ids TYPE jsonb USING inc_ids::jsonb;

ALTER TABLE lwsa.motor_prescricao
    ALTER COLUMN justificativa TYPE jsonb USING justificativa::jsonb;

ALTER TABLE lwsa.motor_saude_cliente
    ALTER COLUMN linha_do_tempo TYPE jsonb USING linha_do_tempo::jsonb;
```

**Como migrar (código Python):** em `notifier_db.py`, trocar todos os
`%s::json` por `%s::jsonb` (5 ocorrências). O helper `_jsonb()` mantém o
nome — já foi escolhido pensando nessa migração.

**Após migração, queries possíveis:**
- `WHERE inc_ids @> '["INC0001234"]'::jsonb` — cluster contém INC específica.
- `WHERE erros ?& array['extrair_chamados']` — execução com erro específico.
- Index GIN em colunas json para queries rápidas.

---

## Convenções de nomenclatura no código

- **Variáveis e funções:** `snake_case` em PT-BR (`listar_incidentes_recentes`,
  `score_criticidade`).
- **Classes:** `PascalCase` em PT-BR (`Incidente`, `ServiceNowExtractor`).
- **Constantes:** `UPPER_SNAKE_CASE` em PT-BR (`LIMIAR_P2_INCS_SEM_CONTORNO`).
- **Logs:** PT-BR, narrativos ("INCs lidas (24h): 91.").
- **Docstrings:** PT-BR, explicam o "por quê" (não o "como").

Bilíngue intencional: variáveis em PT-BR para alinhar com domínio Locaweb;
nomes técnicos universais (TF-IDF, DBSCAN) preservados em inglês.