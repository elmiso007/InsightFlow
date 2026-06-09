# LocaPredict — motor prescritivo para PRB

Motor de análise de incidentes do ServiceNow com NLP + clusterização para identificar padrões recorrentes e sugerir ação operacional.

## Estrutura do Projeto

- `main.py`: Ponto de entrada, funções de DB, embeddings e pipeline completo.
- `prescricao_prb.py`: Motor prescritivo — `PrescricaoPRB` (dataclass) e `prescrever_acao_prb()` com 5 regras em cascata.
- `locapredict_db.py`: Configuração e acesso ao PostgreSQL.
- `locapredict_log.py`: Logging rotativo.
- `alertas_slack.py`: Notificações Slack com alerta rico (urgência, decisão de PRB, evidências).
- `certificados_https.py`: Configuração SSL.
- `guardiao_saude_cliente.py`: Sub-aplicação para recorrência por cliente.

- Busca incidentes ativos das últimas 24h no PostgreSQL.
- Gera embeddings semânticos com `SentenceTransformer` (**modelo multilíngue** para textos em português).
- Enriquece o texto do embedding com contexto de negócio (`produto`, `grupo_designado`, `categoria`).
- Remove stop-words em português antes da vetorização para reduzir ruído.
- Agrupa chamados com HDBSCAN (`min_cluster_size=3`).
- Calcula dois indicadores (0 a 1):
  - `score_severidade` — impacto técnico-operacional do cluster (com bônus de **+0.15 quando há recorrência de servidor** intra-cluster).
  - `ineficiencia_score` — sinal de patinação (muitas interações + lentidão).
- Aplica **motor prescritivo** (`prescrever_acao_prb()`) com a **matriz oficial P1-P4 da Locaweb Varejo** — decide a prioridade combinando 4 sinais heurísticos do cluster (Reclame Aqui, sem solução de contorno, indisponibilidade, monitoração automática), o OLA estourado e a **volumetria histórica do produto nos últimos 30 dias** (consulta auxiliar). Devolve `PrescricaoPRB` rica: prioridade (P1..P5), OLA target em horas, decisão `deve_abrir_prb`, grupo destino, evidências, descrição, `score_composto` e flag `upgrade_aplicado` (sinaliza elevações P3 → P2 por volumetria).
- Persiste insights em `lwsa.locapredict_insights` (schema do banco não muda — apenas o texto de `sugestao_acao` reflete a nova ação prescritiva).
- Envia alerta opcional no Slack quando `score_severidade` atinge o limiar `notify_min_score` em `[slack]` (padrão `0.7`; `pontuacao_minima_severidade` também é aceita). O alerta exibe **prioridade + OLA target** (`P2 ⏱ OLA ≤ 4h`), urgência, decisão `Abrir PRB? ✅ SIM / ❌ não`, grupo destino, dois bullets-chave (Volume + Servidores) e linha `⚠ UPGRADE` quando houver elevação. Insights ordenados por `score_composto`; cabeçalho conta `📌 N PRB(s) recomendado(s)`.
- **Guardião da Saúde do Cliente** (`guardiao_saude_cliente.py`): recorrência por `login_cliente` + `produto` em janela de meses, restrita aos clientes com INC nas últimas 24h; configuração em `[customer_health_guardian]` (chaves em português).

## Arquitetura — fluxo de alto nível

```mermaid
flowchart TD
    SN[(ServiceNow<br/>service_now_incidentes)]

    subgraph LP[LocaPredict — pipeline NLP + matriz P1-P4]
        direction TB
        A[Embeddings multilíngue PT-BR<br/>+ remoção de stop-words] --> B[HDBSCAN<br/>min_cluster_size=3]
        B --> C[Scores<br/>severidade + ineficiência<br/>+ bônus servidor recorrente]
        H[Detectores heurísticos<br/>Reclame Aqui / Sem Contorno /<br/>Indisponibilidade / Monitoração] --> D
        VOL[Consulta histórica<br/>contagem com/sem contorno<br/>últimos 30d por produto] --> D
        C --> D{prescrever_acao_prb<br/>matriz P1-P4 + upgrade}
    end

    subgraph GD[Guardião da Saúde do Cliente]
        direction TB
        E[Normalização SQL<br/>de login_cliente] --> F[Agregação por<br/>login + produto +<br/>inc_timeline 100 INCs]
    end

    SN --> A
    SN --> H
    SN --> VOL
    SN --> E

    D -->|P1 / P2| OUT1[✅ Abrir PRB]
    D -->|P3| OUT2[🔍 Investigar candidato]
    D -->|P4 / P5| OUT3[👀 Monitorar / 🔧 Análise de servidor]

    OUT1 --> DB1[(locapredict_insights)]
    OUT2 --> DB1
    OUT3 --> DB1

    OUT1 --> SL1[📊 Slack — P-level + OLA<br/>+ ⚠ UPGRADE quando aplicável]
    OUT2 --> SL1
    OUT3 --> SL1

    F --> DB2[(guardiao_saude_cliente_snapshots<br/>com inc_timeline TEXT[])]
    F --> SL2[🛡️ Slack Guardião]

    classDef pipeline fill:#e1f5ff,stroke:#0366d6,color:#000
    classDef storage fill:#fff4d6,stroke:#b08800,color:#000
    classDef output fill:#d4f3d4,stroke:#22863a,color:#000
    class A,B,C,D,E,F,H,VOL pipeline
    class DB1,DB2,SN storage
    class OUT1,OUT2,OUT3,SL1,SL2 output
```

## Pré-requisitos

- Python 3.8+
- PostgreSQL com acesso à tabela `lwsa.service_now_incidentes`
- Permissão de `INSERT` na tabela `lwsa.locapredict_insights`
- Permissão de `USAGE/SELECT/UPDATE` na sequence `lwsa.locapredict_insights_insight_id_seq` (quando `insight_id` é `SERIAL`)

## Instalação

1. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

2. Configure `config.ini` (seção `[database]`).
3. Crie/atualize a tabela de saída com o DDL de `queries.sql`.
4. Aplique as permissões abaixo no PostgreSQL (com um usuário com privilégio de `GRANT`).

## Permissões no PostgreSQL

O usuário da aplicação (no exemplo, o mesmo do `config.ini`: `automatizacoes`) precisa ler a origem e gravar os insights. Execute como superuser ou dono dos objetos; se usar outro login, troque `automatizacoes` pelo `uid`/`user` do seu INI.

```sql
-- Leitura dos incidentes (origem do pipeline)
GRANT SELECT ON TABLE lwsa.service_now_incidentes TO automatizacoes;

-- Gravação dos insights
GRANT SELECT, INSERT, UPDATE ON TABLE lwsa.locapredict_insights TO automatizacoes;

-- Sequence do SERIAL insight_id (obrigatório para INSERT funcionar)
GRANT USAGE, SELECT, UPDATE ON SEQUENCE lwsa.locapredict_insights_insight_id_seq TO automatizacoes;
```

Opcional — objetos novos no schema `lwsa` passam a herdar privilégios para o usuário da app:

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA lwsa
GRANT SELECT, INSERT, UPDATE ON TABLES TO automatizacoes;

ALTER DEFAULT PRIVILEGES IN SCHEMA lwsa
GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO automatizacoes;
```

Validação rápida (no mesmo banco em que a app conecta):

```sql
SELECT has_table_privilege('automatizacoes', 'lwsa.service_now_incidentes', 'SELECT');
SELECT has_table_privilege('automatizacoes', 'lwsa.locapredict_insights', 'INSERT');
SELECT has_sequence_privilege('automatizacoes', 'lwsa.locapredict_insights_insight_id_seq', 'USAGE');
```

## Configuração

### `config.ini` — banco

`main.py` usa `resolve_config_path()` e `guardiao_saude_cliente.py` usa `resolver_caminho_configuracao()` — mesma ordem de busca (se `CAMINHO_ARQUIVO_CONFIGURACAO` / `CONFIG_PATH` não estiverem definidos):

1. `../config.ini`
2. `../../config.ini`
3. `./config.ini`

Exemplo:

```ini
[database]
server=10.30.138.28
port=5432
database=report_requesttracker
uid=automatizacoes
pwd=******
```

Também são aceitos: `host` / `dbname` / `user` / `password`.

### `config.ini` — Slack (opcional)

Chaves típicas em inglês; equivalentes em português também são lidas.

```ini
[slack]
bot_token=xoxb-...
channels=C1234567890,U1234567890
notify_min_score=0.7
```

Alternativas aceitas: `token_robot`, `canais`, `pontuacao_minima_severidade`.

- `SLACK_BOT_TOKEN` no ambiente tem prioridade sobre o token do arquivo.
- Se token ou lista de destinos estiverem ausentes, o envio ao Slack é ignorado sem derrubar o job.
- `canais` / `channels`: IDs `C...` (canal) ou `U...` (DM).

### HTTPS em rede corporativa

Para ambientes com inspeção SSL/proxy:

- `REQUESTS_CA_BUNDLE` ou `SSL_CERT_FILE` (prioridade)
- ou `CORPORATE_CA_BUNDLE` apontando para o PEM corporativo.

A função `configurar_certificados_https()` em `certificados_https.py` é chamada no início de `main.py` e de `guardiao_saude_cliente.py` antes das bibliotecas de rede.

Exemplo PowerShell:

```powershell
$env:CORPORATE_CA_BUNDLE = 'C:\caminho\empresa.pem'
python main.py
```

## Estrutura esperada da origem (`service_now_incidentes`)

Colunas usadas diretamente:

- `numero`, `produto`, `descricao_curta`, `data_abertura`, `status`, `prioridade`
- `grupo_designado`, `servidor`, `login_cliente`, `categoria`, `subcategoria`

### Tempo (para `ineficiencia_score` e métricas)

O pipeline detecta colunas em `information_schema` e monta o SQL assim:

1. Se existir `tempo_medio_resolucao` → usa a coluna.
2. Senão, se existir `data_resolvido` → calcula em horas:  
   `(COALESCE(data_resolvido, NOW()) - data_abertura)`.
3. Senão → fallback: idade da INC em horas, `NOW() - data_abertura`.

O resultado sempre aparece no resultado da query como alias `tempo_medio_resolucao`.

### Atualizações (contagem por INC)

1. Se existir `total_atualizacoes` → usa a coluna.
2. Senão, se existir `atualizacoes` → usa essa coluna (nome comum em bases legadas).
3. Senão → literal `0` (nesse caso `ineficiencia_score` tende a ficar **zero**).

O resultado sempre aparece como alias `total_atualizacoes` no `SELECT`, para o restante do código não precisar de nomes diferentes.

### Logs de auditoria

Na subida dos dados, o console imprime qual regra de **tempo** e qual coluna de **atualizações** foram usadas, para facilitar diagnóstico em produção.

## Pipeline (resumo técnico)

1. Carrega CA bundle (quando configurado).
2. Carrega modelo **`paraphrase-multilingual-MiniLM-L12-v2`** (singleton; melhor para PT-BR que o MiniLM monolíngue).
3. Reduz ruído de log das libs de NLP no console.
4. Lê `config.ini` e conecta no PostgreSQL.
5. Detecta colunas da tabela origem e monta SQL dinâmico (tempo + atualizações).
6. Limpa a descrição (`desc_clean`) + remove stop-words em português.
7. Monta texto do embedding com contexto:  
   `desc_clean | produto:<...> | grupo:<...> | categoria:<...>`
8. Gera embeddings.
9. Clusteriza com HDBSCAN (`metric='euclidean'`, `min_cluster_size=3`, `min_samples=1`).
10. Descarta outliers (`label = -1`).
11. Para cada cluster:
    - calcula `mean_sim` (coerência semântica),
    - calcula `score_severidade` (com **bônus +0.15 se algum servidor aparece em ≥ 2 INCs** do cluster — sinal de recorrência intra-cluster do Service Operation),
    - calcula `ineficiencia_score`,
    - gera `cluster_nome` (rótulo descritivo a partir das palavras-chave),
    - **consulta a volumetria histórica do produto** (`contar_incidentes_historicos_por_produto`) — INCs com/sem solução de contorno nos últimos 30 dias. Cacheada por produto na execução.
    - **avalia `prescrever_acao_prb()`** com a **matriz P1-P4 da Locaweb Varejo** (ver seção dedicada). Produz `PrescricaoPRB` com prioridade, OLA target, decisão de PRB, grupo destino, evidências, `score_composto` e `upgrade_aplicado` (quando P3 → P2 por volumetria).
    - **Sobrescrita por servidor concentrador**: se um único servidor concentra > 3 INCs do cluster, a `prescricao.acao` é trocada por `"Solicitar análise de desempenho/PRB para o servidor específico: <nome>"` (os outros campos da prescrição ficam intactos).
12. Persiste em `lwsa.locapredict_insights` (o `PrescricaoPRB` viaja apenas em memória até o Slack — o INSERT usa `[row[:8]]` e mantém o schema do banco intacto).
13. Envia resumo ao Slack (opcional), apenas insights com `score_severidade >= notify_min_score` configurada em `[slack]`. Insights elegíveis são **ordenados por `score_composto`** e o cabeçalho mostra `📌 N PRB(s) recomendado(s)`. Cada insight exibe `P-level + OLA target` no cabeçalho e linha `⚠ UPGRADE` quando aplicável.

## Fórmulas de score

### `score_severidade`

Combina coesão semântica, peso do cluster no volume do produto e esforço (atualizações no cluster):

`score = min(1.0, 0.4*mean_sim + 0.3*(cluster_size/volume_atual) + 0.3*fator_esforco)`

onde:

`fator_esforco = min(1.0, log1p(total_atualizacoes)/5)`  
(`total_atualizacoes` aqui é a **soma** das atualizações dos incidentes do cluster.)

### `ineficiencia_score`

Alto quando há **muita interação média** e **tempo alto** ao mesmo tempo (produto dos dois fatores):

- `fator_interacoes = min(1.0, log1p(atualizacoes_medias)/3)`
- `fator_lentidao = min(1.0, log1p(tempo_medio_resolucao)/5)`
- `ineficiencia_score = min(1.0, fator_interacoes * fator_lentidao)`

`atualizacoes_medias` = soma das atualizações do cluster ÷ tamanho do cluster.

## Classificação SEV / OPS (leitura operacional)

Usada na mensagem do Slack (e alinhada às faixas abaixo):

| Rótulo | Critério (`score_severidade`) |
|--------|-------------------------------|
| SEV:ALTA | ≥ 0,75 |
| SEV:MEDIA | 0,50 – 0,74 |
| SEV:BAIXA | abaixo de 0,50 |

| Rótulo | Critério (`ineficiencia_score`) |
|--------|----------------------------------|
| OPS:CRITICO | ≥ 0,60 |
| OPS:ATENCAO | 0,30 – 0,59 |
| OPS:SAUDAVEL | abaixo de 0,30 |

## Motor prescritivo (`prescrever_acao_prb`) — matriz P1-P4 Locaweb Varejo

Reside em `prescricao_prb.py`. Substitui a lógica anterior (que mapeava urgência → P-level via scores semânticos) pela matriz oficial da ata Locaweb Varejo, combinando heurísticas de texto, volumetria histórica e OLA.

### Dataclass `PrescricaoPRB`

10 campos viajam na tupla de insight até o Slack:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `acao` | `str` | Texto curto (gravado em `sugestao_acao` no banco) |
| `urgencia` | `str` | `CRITICA` / `ALTA` / `MEDIA` / `BAIXA` (rotulação textual) |
| `deve_abrir_prb` | `bool` | Decisão direta para o time de Problem Management |
| `grupo_destino` | `str` | Grupo do ServiceNow mais frequente no cluster |
| `evidencias` | `List[str]` | Bullets explicativos (sinais ativados) |
| `descricao_rica` | `str` | Parágrafo em linguagem natural |
| `score_composto` | `float` | 0–1, usado para ordenar clusters no alerta |
| **`prioridade`** | `str` | **P1 / P2 / P3 / P4 / P5** — atribuído diretamente pela matriz |
| **`ola_target_horas`** | `int` | Tempo de resolução máximo (horas) por diretriz oficial |
| **`upgrade_aplicado`** | `Optional[str]` | `"P3->P2 por <razão>"` quando a regra de volumetria elevou P3 → P2; `None` caso contrário |

### OLA targets por prioridade

| Prioridade | OLA máximo |
|---|---|
| P1 | 4 horas |
| P2 | 4 horas |
| P3 | 12 horas |
| P4 | 24 horas |
| P5 | 96 horas |

Constantes em `OLA_TARGETS_HORAS` (dict no topo de `prescricao_prb.py`). A urgência rotular continua existindo (CRITICA/ALTA/MEDIA/BAIXA) e mapeia 1-1 com P1/P2/P3/P4 — P5 fica reservado para a próxima fase (monitoração automática expandida).

### Matriz P1-P4 (a primeira regra que casa decide)

| Prioridade | Critério (qualquer um basta dentro do "OU") | Abre PRB? | Texto da ação |
|---|---|---|---|
| **P1 — CRITICA** | "Reclame Aqui" presente **E** "sem solução de contorno" presente **E** OLA P1 (4h) estourado por algum INC | ✅ SIM | `Abrir PRB P1 (Reclame Aqui sem contorno + OLA estourado) — <produto>` |
| **P2 — ALTA** | Indisponibilidade detectada **OU** `n_sem_contorno_no_cluster ≥ 5` **OU** `total_historico_com_contorno_30d ≥ 1000` | ✅ SIM | `Abrir PRB P2 (<razões>) — <produto>` |
| **P3 — MEDIA** | `severidade ≥ 0.5` **OU** `1 ≤ n_sem_contorno_no_cluster < 5` **OU** `100 ≤ total_historico_com_contorno_30d < 1000` | ❌ não | `Investigar candidato a PRB P3 em <produto>` |
| **P4 — BAIXA** | Monitoração automática (todos os INCs com `grupo_designado` contendo `"monit"` OU `login_cliente` contendo `"monit"/"automat"/"alert"`) **OU** caso isolado sem demais sinais | ❌ não | `Monitorar <produto>` (com nota "origem: monitoração automática" quando aplicável) |

### UPGRADE de prioridade (P3 → P2)

Quando uma regra de volumetria (≥ 5 sem contorno no cluster ou ≥ 1000 com contorno no histórico) eleva um cluster que sem essas condições cairia em P3, o campo `upgrade_aplicado` é preenchido com o motivo. No Slack vira a linha `⚠ *UPGRADE*: P3->P2 por <razão>`. Indisponibilidade não dispara upgrade (P2 nativo).

### Limiares calibrados (constantes no topo de `prescricao_prb.py`)

```python
LIMIAR_P2_HISTORICO_COM_CONTORNO     = 1000  # >= este número em 30d → P2
LIMIAR_P3_HISTORICO_COM_CONTORNO_MIN = 100   # faixa P3 começa aqui
LIMIAR_P3_HISTORICO_COM_CONTORNO_MAX = 1000  # exclusivo (igual ao P2)
LIMIAR_P2_SEM_CONTORNO_NO_CLUSTER    = 5     # >= INCs sem contorno no cluster → P2
LIMIAR_P3_SEVERIDADE_PERCEPTIVEL     = 0.5   # severidade >= → "falha perceptível"
```

A calibração inicial da ata (`>= 100 com contorno em 30d`) revelou-se permissiva — 5000+ INCs/mês em alguns produtos da Locaweb fazem o threshold ser estourado trivialmente. Valores atuais são calibração empírica após primeira execução.

### Detectores heurísticos (substring case-insensitive em `desc_clean` + `descricao_curta`)

| Sinal | Termos buscados |
|---|---|
| **Reclame Aqui** | `"reclame aqui"`, `"reclameaqui"`, `"reclame-aqui"` |
| **Sem Contorno** | `"sem contorno"`, `"sem solucao"`, `"sem solução"`, `"nenhum contorno"`, `"no workaround"` |
| **Indisponibilidade** | `"indisponivel"`, `"indisponível"`, `"fora do ar"`, `"ambiente fora"`, `"tudo fora"`, `"todos fora"` |
| **Monitoração Automática** | `grupo_designado` contém `"monit"` **OU** `login_cliente` contém `"monit"`/`"automat"`/`"alert"` |
| **OLA estourado** | `tempo_medio_resolucao` (em horas) > OLA target da prioridade base avaliada |

Ajustes nos termos: editar as constantes `_TERMOS_*` no topo de `prescricao_prb.py`. Os mesmos termos de "sem contorno" são espelhados em `_TERMOS_SQL_SEM_CONTORNO` em `main.py` (consulta histórica) — alterações precisam ser feitas nos dois lugares.

### Score composto (mantido como contexto)

Os scores `severidade`/`ineficiencia`/`composto` continuam sendo calculados — não decidem mais a prioridade (a matriz P1-P4 decide), mas são exibidos no Slack como diagnóstico:

```
score_composto = min(1, 0.5*score_severidade + 0.5*ineficiencia_score + bonus_volume)
bonus_volume   = +0.10 se n_incidentes >= 10
                 +0.05 se n_incidentes >= 5
                  0   caso contrário
```

### Evidências automáticas

`_coletar_evidencias()` adiciona bullets quando o sinal está ativo:

- Volume do cluster (sempre).
- Faixa de severidade + score (sempre).
- Faixa de ineficiência + score (sempre).
- Servidores afetados (se houver, mostra até 3 + `(+N)`).
- INCs com prioridade crítica/alta (heurística por substring).
- Categorias distintas (só se > 1).
- Clientes distintos impactados (`login_cliente`).
- **Reclame Aqui mencionado** (F3).
- **N INC(s) sem contorno no cluster** (F3, quando > 0).
- **Indisponibilidade detectada** (F3).
- **Origem: monitoração automática** (F3).
- **Histórico de 30d em `<produto>`: X com contorno · Y sem contorno** (F3, quando há dado).

### Texto que vai para o banco

O campo `sugestao_acao` continua sendo a string curta da `PrescricaoPRB.acao`. **O schema do banco não muda** — só o conteúdo do campo reflete a nova prescrição. O objeto `PrescricaoPRB` completo viaja apenas até o Slack (banco persiste 8 colunas, Slack usa as 10 da dataclass).

## Recorrência por servidor (sinal do Service Operation)

Pedido do time de Service Operation para cruzar a análise de cluster com Item de Configuração / servidores específicos. Implementado em `main.py` (`_calcular_recorrencia_servidor`).

| Gatilho | Efeito |
|---|---|
| **Servidor presente em ≥ 2 INCs do cluster** | Aplica bônus **+0.15 em `score_severidade`** (limitado pelo `min(1.0, ...)`) |
| **Servidor presente em > 3 INCs do cluster** | Sobrescreve `prescricao.acao` para `"Solicitar análise de desempenho/PRB para o servidor específico: <nome>"` e troca o emoji para 🔧 |

A sobrescrita atua **apenas no campo `acao`** — os demais campos da `PrescricaoPRB` (prioridade P-level, OLA target, decisão de PRB, evidências, descrição rica) ficam intactos. Resultado: o Slack mostra simultaneamente o contexto PRB (matriz P1-P4) e o direcionamento operacional ao servidor. O cluster log registra a sobrescrita para auditoria.

Thresholds em constantes nomeadas no topo do `main.py`:
```python
_BONUS_SCORE_SERVIDOR_RECORRENTE = 0.15
_MIN_INCS_PARA_BONUS_SERVIDOR    = 2
_MIN_INCS_PARA_ACAO_SERVIDOR     = 3
```

## Slack: formato e limitações

- Mensagens usam **Block Kit** (`header` + `section` com `mrkdwn`). Não há cor de texto ou fundo personalizável como em HTML; o visual segue o tema do cliente.
- Para leitura rápida, o alerta usa **emojis** (severidade, operação, ação, cluster, INCs) e os rótulos **SEV** / **OPS**.
- Textos longos são **quebrados em vários blocos** `section` para não ultrapassar o limite do Slack (~3000 caracteres por `section`), evitando o erro `invalid_blocks`.

### Emojis em `alertas_slack.py`

O Block Kit não aplica cores no texto; os emojis dão pista visual rápida. Mapeamento usado no código:

| Uso | Emoji |
|-----|-------|
| **Urgência PRB**: CRITICA / ALTA / MEDIA / BAIXA | 🆘 / 🔺 / 🔶 / 🔹 |
| Severidade ALTA / MÉDIA / BAIXA | 🔴 / 🟡 / 🟢 |
| Operação CRÍTICO / ATENÇÃO / SAUDÁVEL | 🚨 / ⚠️ / ✅ |
| Ação: Abrir PRB / Investigar / Revisar fluxo / Monitorar / **Solicitar análise de servidor** | 📌 / 🔍 / 🔄 / 👀 / **🔧** |
| Decisão "Abrir PRB?" SIM / não | ✅ / ❌ |
| **UPGRADE de prioridade (P3 → P2)** | **⚠** |
| **OLA target (Tempo de Resolução Máximo)** | **⏱** |
| Cluster (contexto) | 📍 |
| Lista de INCs | 🎫 |
| Título do alerta + contagem | 📊 / 📌 |
| Intro "Insights com score…" | 📋 |

### Formato do bloco (corte cirúrgico — F2)

Para manter alertas "cirúrgicos" (coordenação consome análise densa via dashboards), o bloco rico foi enxugado:

- **Remove** o parágrafo `descricao_rica` do bloco visual.
- **Mantém** apenas dois bullets de evidência: Volume e Servidores afetados. Os demais sinais (severidade/ineficiência/categorias/clientes/Reclame Aqui/etc.) continuam no campo `evidencias` da `PrescricaoPRB`, disponíveis para outros consumidores (banco, dashboard).
- **Adiciona** prioridade + OLA target no cabeçalho (`*P2* ⏱ OLA ≤ 4h`).
- **Adiciona** linha `⚠ *UPGRADE*: ...` quando `upgrade_aplicado` está preenchido.

**Exemplo de mensagem completa renderizada no Slack** (dados ofuscados, formato F2/F3 atual):

> 📊 **LocaPredict — alerta PRB · 📌 1 PRB(s) recomendado(s)**
>
> 📋 Insights com score >= **0.70**:
>
> • 🔺 **Produto-Exemplo** — **P2** ⏱ OLA ≤ 4h · 🔴 **SEV:ALTA** · ✅ **OPS:SAUDAVEL** · 🔺 **PRB:ALTA** — **16** inc.
> &nbsp;&nbsp;📌 Abrir PRB P2 (>=1234 com contorno em 30d) — Produto-Exemplo → grupo **Grupo Nivel 1**
> &nbsp;&nbsp;Abrir PRB? **✅ SIM** · sev **0.89** · inef **0.03** · composto **0.56**
> &nbsp;&nbsp;⚠ **UPGRADE**: P3->P2 por 1234 INCs com contorno em 30d
> &nbsp;&nbsp;• Volume: 16 incidente(s) no cluster
> &nbsp;&nbsp;• Servidores afetados: 1 — *srv-ofuscado*
> &nbsp;&nbsp;📍 *Incidentes em Produto-Exemplo: problem nfs client*
> &nbsp;&nbsp;🎫 INC: `INC*****73, INC*****72, INC*****71, … (+13)`

E quando F1 dispara (servidor concentrando > 3 INCs do cluster), a `prescricao.acao` muda para a sugestão dedicada e o emoji vira 🔧:

> &nbsp;&nbsp;🔧 Solicitar análise de desempenho/PRB para o servidor específico: *srv-ofuscado* → grupo **Grupo Nivel 1**

**Screenshot real do alerta no Slack:**

<img width="1194" height="326" alt="Alerta PRB renderizado no Slack" src="https://github.com/user-attachments/assets/cbd64a52-2c8e-4128-bdbe-54c5bd88eea6" />

### Retrocompatibilidade do alerta

O import de `PrescricaoPRB` em `alertas_slack.py` é feito em `try/except ImportError`. Se o módulo `prescricao_prb.py` não estiver presente (deploy parcial / teste isolado), a tupla de insight cai automaticamente no **formato legado** — uma linha mais simples sem urgência/evidências/composto, baseada apenas em `score_severidade` e `ineficiencia_score`. O usuário não precisa configurar nada para a retrocompat funcionar.

Na próxima execução de `main.py`, o layout atualizado aparece no canal configurado em `[slack]`.

## Tabela de saída (`lwsa.locapredict_insights`)

Colunas gravadas (o INSERT segue exatamente esta ordem — `[row[:8]]`):

- `cluster_nome`
- `quantidade_inc_afetados`
- `produto_afetado`
- `score_severidade`
- `ineficiencia_score`
- `sugestao_acao` — texto curto da `PrescricaoPRB.acao` (motor prescritivo)
- `incidentes_relacionados`
- `servidores_afetados`

O objeto `PrescricaoPRB` completo (urgência, decisão de PRB, evidências, descrição rica, score composto) **não é persistido** — viaja em memória só até o alerta Slack. Se no futuro for útil persistir esses campos para análise histórica, basta um `ALTER TABLE ADD COLUMN IF NOT EXISTS` — nada quebra na versão atual.

## Guardião da Saúde do Cliente (recorrência / risco de churn)

Script independente do motor NLP — foco em **volume histórico** por cliente (`login_cliente`) e produto, **com gatilho de atividade recente** (INC nas últimas 24h).

- O valor de `login_cliente` é **normalizado no PostgreSQL** antes do `GROUP BY`, para o mesmo cliente não ser contado várias vezes quando o campo vem em formatos diferentes:
  - URL com `ficha=` (ex.: intranet `...?ficha=100894`) → usa só o número;
  - texto com `(Cód. NNN)` ou `(Cod. NNN)` → usa o número entre parênteses;
  - somente dígitos → mantém o código;
  - outras URLs `http(s)://` → tenta o último `=` com número no fim da string;
  - demais textos → minúsculas e apenas letras/números (ex.: `mzviagens`).
- Consulta agrega direto com `GROUP BY login_normalizado, produto` + `HAVING COUNT(*) >= minimo_incidentes` na janela temporal, e calcula `diversidade_problemas` (categorias distintas), `ultimo_contato`, `ultima_inc`, `media_esforco_cliente` (média de atualizações por INC) e **`inc_timeline`** (array com até 100 INCs mais recentes do par, do mais novo para o mais antigo).
- **Filtro de atividade recente (configurável, default 24h):** o `HAVING` exige também `MAX(data_abertura) >= NOW() - (INTERVAL '1 hour' * horas_inc_recente)`. Ou seja, só aparecem no resultado pares `login × produto` que (1) acumularam ≥ `minimo_incidentes` na janela de meses **e** (2) têm pelo menos uma INC aberta nas últimas N horas (N vem de `horas_inc_recente`, default 24, limites 1–720). Como o `MAX(data_abertura)` já é calculado para `ultimo_contato`, esse filtro tem custo desprezível.
- Coluna de atualizações: mesmo mapeamento do LocaPredict (`total_atualizacoes` ou `atualizacoes`).

### Jornada de contato do cliente (`inc_timeline`)

Resolve a dor de "encontrar a capivara do cliente" — em vez de só saber **quantos** INCs ele abriu na janela, agora se sabe **quais** e **em que ordem**. Implementado em F1.

- Coluna `inc_timeline TEXT[]` na tabela `lwsa.guardiao_saude_cliente_snapshots` (DDL atualizado em `queries.sql` com bloco `DO $$` idempotente compatível com PG 9.2).
- Persiste **até 100 INCs mais recentes** do par `login_cliente × produto`, ordenados do mais novo para o mais antigo (`(array_agg(numero ORDER BY data_abertura DESC))[1:100]`).
- Alimenta análise temporal nos dashboards (Power BI / Superset) sem precisar re-consultar o ServiceNow para reconstruir a linha do tempo.
- Tratamento gracioso de DDL pendente: se a coluna ainda não existe no banco, o pgcode `42703` é capturado em `gravar_snapshots_historico_guardiao` e vira warning no log — o resto do pipeline continua normal.

### Configuração opcional (`config.ini`)

```ini
[customer_health_guardian]
habilitado = true
meses_janela = 6
minimo_incidentes = 5
horas_inc_recente = 24
gravar_snapshots = true
alertas_slack = true
apenas_incidentes_abertos = false
max_linhas_slack = 25
```

- Chaves em inglês (`enabled`, `window_months`, …) também continuam válidas como alternativa.
- `apenas_incidentes_abertos = true` restringe a incidentes **não** encerrados/cancelados (como no pipeline 24h). Padrão `false` inclui todo histórico na janela (visão típica de “dor acumulada” do cliente). O filtro das últimas N horas se aplica em cima desse recorte: com `true` exige uma INC ativa nas N horas, com `false` basta uma INC criada nas N horas.
- `horas_inc_recente` (default `24`, limites `1–720`) define o tamanho da janela de atividade recente em horas. Equivalente em inglês: `recent_inc_hours`. Valores típicos: `24` (dia anterior), `48` (fim de semana), `72` (feriado prolongado).
- Snapshots exigem a tabela `lwsa.guardiao_saude_cliente_snapshots` (DDL em `queries.sql`). Sem tabela, o job continua e registra aviso no log (desative com `gravar_snapshots = false` se não for usar).
- Slack reutiliza `[slack]` (mesmos canais do LocaPredict). O cabeçalho do alerta exibe a janela em meses + a indicação `_com INC nas últimas 24h_` para deixar o critério explícito.

### Execução

```bash
python guardiao_saude_cliente.py
```

Logs: mesmo arquivo `logs/locapredict.log` (`locapredict_log.setup_locapredict_logging`).

### Permissões PostgreSQL (snapshots)

```sql
GRANT SELECT ON TABLE lwsa.service_now_incidentes TO automatizacoes;
GRANT INSERT ON TABLE lwsa.guardiao_saude_cliente_snapshots TO automatizacoes;
GRANT USAGE, SELECT ON SEQUENCE lwsa.guardiao_saude_cliente_snapshots_snapshot_id_seq TO automatizacoes;
```

## Execução

```bash
python main.py
```

Saída esperada (exemplos):

- `LocaPredict: ...` (origem de tempo e coluna de atualizações)
- `<N> insights gravados com sucesso!`
- `Slack: enviado ao canal ...` ou mensagem explícita do motivo quando não envia

## Log em arquivo (auditoria)

Cada execução registra em arquivo rotativo:

- Caminho padrão: `locapredict/logs/locapredict.log` (pasta criada automaticamente).
- Personalize com `CAMINHO_ARQUIVO_REGISTRO_LOCAPREDICT` (recomendado) ou `LOCAPREDICT_LOG_PATH` (legado).

O log inclui, entre outros:

- caminho do `config.ini` usado;
- resumo da consulta de incidentes (tipo de expressão de tempo / coluna de atualizações, quantidade de linhas);
- estatísticas dos insights da rodada (min/máx de `score_severidade`, quantos ≥ 0,70 / ≥ 0,75);
- **motivo** quando o Slack não é enviado (seção ausente, token vazio, destinos vazios, limiar `notify_min_score`, erro da API com detalhe);
- confirmação de envio por canal ou usuário.

Arquivos antigos: rotação automática (~5 MB por arquivo, até 10 backups). A pasta `logs/` está listada em `.gitignore` para não versionar dados de execução.

## Por que há insights altos no banco e nada no Slack?

O PostgreSQL guarda **tudo** o que a rodada inseriu; o Slack só recebe o que passar **na mesma execução** e **pelos filtros**:

1. **`notify_min_score`** em `[slack]` (ou `pontuacao_minima_severidade`): só entram insights com `score_severidade >=` esse valor (padrão `0.7`). Se naquela execução todos ficaram abaixo do limiar, não há post (o log registra o maior score da rodada).
2. **Slack desligado naquele ambiente**: sem `[slack]`, token ou lista de destinos — a gravação no banco ocorre, o envio não. O console e o log mostram o motivo retornado por `load_slack_settings`.
3. **Erro da API Slack** (token revogado, app fora do canal, rate limit): o job continua; o erro aparece no console e no `locapredict.log` com `detalhe=...`.
4. **Rodadas diferentes**: linhas antigas no banco podem ser de outra execução em que o Slack funcionou ou falhou; compare `data_geracao` com o horário das linhas do log.

Para diagnosticar sempre: abra `logs/locapredict.log` logo após a execução problemática.

## Troubleshooting rápido

| Sintoma | Causa provável | O que fazer |
|--------|----------------|-------------|
| `ineficiencia_score` sempre `0` | Coluna de atualizações não mapeada (só existe `atualizacoes` ou nome diferente) | Garantir coluna `atualizacoes` ou `total_atualizacoes`; ver log no console |
| Slack sem mensagem com scores altos no banco | Limiar, config ausente ou erro API em outra rodada | Ver seção acima e `logs/locapredict.log` |
| `Slack API ... invalid_blocks` | Texto do bloco muito longo | Versão atual particiona blocos em `alertas_slack.py` |
| `UndefinedColumn ...` | SQL desatualizado ou coluna obrigatória ausente | Usar `main.py` com detecção dinâmica de colunas |
| `permission denied for sequence ...` | Falta `GRANT` na sequence | Conceder `USAGE, SELECT, UPDATE` na sequence do `insight_id` |
| Erro de certificado ao baixar modelo | Proxy MITM | `CORPORATE_CA_BUNDLE` / `REQUESTS_CA_BUNDLE` |

## Arquivos

- `main.py` — LocaPredict: pipeline NLP, scores, `locapredict_insights`, Slack opcional.
- `prescricao_prb.py` — motor prescritivo: dataclass `PrescricaoPRB` e função `prescrever_acao_prb()` com 5 regras em cascata, evidências automáticas e `score_composto`.
- `certificados_https.py` — `configurar_certificados_https()` (CA bundle corporativo, compartilhado).
- `locapredict_db.py` — `load_db_config`, `get_table_columns`.
- `locapredict_log.py` — log em arquivo rotativo (`setup_locapredict_logging`, `get_logger`).
- `alertas_slack.py` — `[slack]`, alertas do LocaPredict (formato rico com urgência/decisão/evidências) e do Guardião (`WebClient`); import opcional de `PrescricaoPRB` para retrocompat.
- `guardiao_saude_cliente.py` — aplicação **Guardião da Saúde do Cliente**: recorrência por `login_cliente` + produto; ponto de entrada `executar_guardiao_saude_cliente()`; configuração na seção `[customer_health_guardian]` do INI.
- `queries.sql` — SQL de referência e DDLs.
- `requirements.txt` — dependências Python.
