# LocaPredict — motor prescritivo para PRB

Motor de análise de incidentes do ServiceNow com NLP + clusterização para identificar padrões recorrentes e sugerir ação operacional.

## Estrutura do Projeto

- `main.py`: Ponto de entrada, funções de DB, embeddings e pipeline completo.
- `locapredict_db.py`: Configuração e acesso ao PostgreSQL.
- `locapredict_log.py`: Logging rotativo.
- `alertas_slack.py`: Notificações Slack.
- `certificados_https.py`: Configuração SSL.
- `guardiao_saude_cliente.py`: Sub-aplicação para recorrência por cliente.

- Busca incidentes ativos das últimas 24h no PostgreSQL.
- Gera embeddings semânticos com `SentenceTransformer` (**modelo multilíngue** para textos em português).
- Enriquece o texto do embedding com contexto de negócio (`produto`, `grupo_designado`, `categoria`).
- Remove stop-words em português antes da vetorização para reduzir ruído.
- Agrupa chamados com HDBSCAN (`min_cluster_size=3`).
- Calcula dois indicadores (0 a 1):
  - `score_severidade` — impacto técnico-operacional do cluster.
  - `ineficiencia_score` — sinal de patinação (muitas interações + lentidão).
- Persiste insights em `lwsa.locapredict_insights`.
- Envia alerta opcional no Slack quando `score_severidade` atinge o limiar `notify_min_score` em `[slack]` (padrão `0.7`; `pontuacao_minima_severidade` também é aceita), com rótulos **SEV/OPS**, emojis e blocos particionados.
- **Guardião da Saúde do Cliente** (`guardiao_saude_cliente.py`): recorrência por `login_cliente` + `produto` em janela de meses; configuração em `[customer_health_guardian]` (chaves em português).

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
    - calcula `score_severidade`,
    - calcula `ineficiencia_score`,
    - gera `cluster_nome` com fallback: `SRV` → `GRP` → `CAT` → `PRD`.
12. Persiste em `lwsa.locapredict_insights`.
13. Envia resumo ao Slack (opcional), apenas insights com `score_severidade >= notify_min_score` configurada em `[slack]`.

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

## Regras de ação (`suggest_action`)

Ordem de prioridade:

1. Se `ineficiencia_score >= 0.6` →  
   `Revisar fluxo de atendimento: Alta reincidência de interações`
2. Senão, se `score_severidade >= 0.75` →  
   `Abrir PRB para <produto>`
3. Caso contrário →  
   `Monitorar <produto> + revisão em 15 minutos`

O nome de contexto do cluster (`cluster_nome`) continua gravado na tabela e aparece no Slack em linha separada; a sugestão fica curta para evitar repetição.

## Slack: formato e limitações

- Mensagens usam **Block Kit** (`header` + `section` com `mrkdwn`). Não há cor de texto ou fundo personalizável como em HTML; o visual segue o tema do cliente.
- Para leitura rápida, o alerta usa **emojis** (severidade, operação, ação, cluster, INCs) e os rótulos **SEV** / **OPS**.
- Textos longos são **quebrados em vários blocos** `section` para não ultrapassar o limite do Slack (~3000 caracteres por `section`), evitando o erro `invalid_blocks`.

### Emojis em `alertas_slack.py`

O Block Kit não aplica cores no texto; os emojis dão pista visual rápida. Mapeamento usado no código:

| Uso | Emoji |
|-----|-------|
| Severidade ALTA / MÉDIA / BAIXA | 🔴 / 🟡 / 🟢 |
| Operação CRÍTICO / ATENÇÃO / SAUDÁVEL | 🚨 / ⚠️ / ✅ |
| Ação: Abrir PRB / Monitorar / Revisar fluxo | 📌 / 👀 / 🔄 |
| Cluster (contexto) | 📍 |
| Lista de INCs | 🎫 |
| Título do alerta | 📊 |
| Intro “Insights com score…” | 📋 |

**Exemplo (resumo de uma linha de insight):**  
`• 🔴✅ *Produto* — 🔴 *SEV:ALTA* · ✅ *OPS:SAUDAVEL* — score … — ineficiência … — *N* inc.`  
As linhas seguintes trazem a ação com o emoji correspondente (📌 / 👀 / 🔄), o cluster com 📍 e os INCs com 🎫.

Na próxima execução de `main.py`, o layout atualizado aparece no canal configurado em `[slack]`.

## Tabela de saída (`lwsa.locapredict_insights`)

Colunas gravadas:

- `cluster_nome`
- `quantidade_inc_afetados`
- `produto_afetado`
- `score_severidade`
- `ineficiencia_score`
- `sugestao_acao`
- `incidentes_relacionados`

## Guardião da Saúde do Cliente (recorrência / risco de churn)

Script independente do motor NLP — foco em **volume histórico** por cliente (`login_cliente`) e produto.

- O valor de `login_cliente` é **normalizado no PostgreSQL** antes do `PARTITION BY`, para o mesmo cliente não ser contado várias vezes quando o campo vem em formatos diferentes:
  - URL com `ficha=` (ex.: intranet `...?ficha=100894`) → usa só o número;
  - texto com `(Cód. NNN)` ou `(Cod. NNN)` → usa o número entre parênteses;
  - somente dígitos → mantém o código;
  - outras URLs `http(s)://` → tenta o último `=` com número no fim da string;
  - demais textos → minúsculas e apenas letras/números (ex.: `mzviagens`).
- Consulta usa **window function** `COUNT(*) OVER (PARTITION BY login_normalizado, produto)` na janela temporal, depois agrega `diversidade_problemas` (categorias distintas) e `media_esforco_cliente` (média de atualizações por INC).
- Coluna de atualizações: mesmo mapeamento do LocaPredict (`total_atualizacoes` ou `atualizacoes`).

### Configuração opcional (`config.ini`)

```ini
[customer_health_guardian]
habilitado = true
meses_janela = 6
minimo_incidentes = 5
gravar_snapshots = true
alertas_slack = true
apenas_incidentes_abertos = false
max_linhas_slack = 25
```

- Chaves em inglês (`enabled`, `window_months`, …) também continuam válidas como alternativa.
- `apenas_incidentes_abertos = true` restringe a incidentes **não** encerrados/cancelados (como no pipeline 24h). Padrão `false` inclui todo histórico na janela (visão típica de “dor acumulada” do cliente).
- Snapshots exigem a tabela `lwsa.guardiao_saude_cliente_snapshots` (DDL em `queries.sql`). Sem tabela, o job continua e registra aviso no log (desative com `gravar_snapshots = false` se não for usar).
- Slack reutiliza `[slack]` (mesmos canais do LocaPredict).

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
- `certificados_https.py` — `configurar_certificados_https()` (CA bundle corporativo, compartilhado).
- `locapredict_db.py` — `load_db_config`, `get_table_columns`.
- `locapredict_log.py` — log em arquivo rotativo (`setup_locapredict_logging`, `get_logger`).
- `alertas_slack.py` — `[slack]`, alertas do LocaPredict e do Guardião (`WebClient`).
- `guardiao_saude_cliente.py` — aplicação **Guardião da Saúde do Cliente**: recorrência por `login_cliente` + produto; ponto de entrada `executar_guardiao_saude_cliente()`; configuração na seção `[customer_health_guardian]` do INI.
- `queries.sql` — SQL de referência e DDLs.
- `requirements.txt` — dependências Python.
