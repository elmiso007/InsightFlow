# Monitoramento PRB

## Visão geral

Este diretório contém uma solução para identificar reincidências de PRBs a partir de dois fluxos principais:

1. **Carga histórica de gabaritos**: lê PRBs encerrados no ServiceNow, usa IA para padronizar o sintoma principal e grava o resultado na tabela `lwsa.gabarito_prb`.
2. **Monitoramento diário**: lê atendimentos encerrados em um período definido, compara o texto com os gabaritos já carregados e grava possíveis reincidências na tabela `lwsa.ocorrencia_reincidencia`.

A lógica depende de três fontes principais:

- Banco PostgreSQL configurado em `c:\Users\emerson.ramos\Desktop\projetos\config.ini`
- OpenAI para geração de embeddings e validação semântica
- Tabelas operacionais do banco, principalmente `lw_octadesk.chat`, `dynamics.chamados`, `lwsa.service_now_problems` e `lwsa.gabarito_prb`

## Arquivos principais

### `gabarito_prb.py`
Responsável por construir a base semântica dos PRBs conhecidos.

Fluxo executado:

1. Lê as credenciais do arquivo `config.ini`.
2. Abre conexão com o PostgreSQL.
3. Busca os PRBs da lista fixa `PRBS_ALVO` na tabela `lwsa.service_now_problems`.
4. Consulta `lwsa.gabarito_prb` para identificar quais PRBs já foram processados anteriormente.
5. Filtra apenas os PRBs **pendentes** (ainda não presentes no gabarito), evitando chamadas desnecessárias à IA.
6. Para cada PRB pendente:
   - monta um prompt com o título e a descrição original;
   - chama o modelo `gpt-4o-mini` para extrair uma estrutura padronizada com:
     - `categoria`
     - `tag`
     - `descricao_resumida`
     - `termos_relacionados`
   - cria um texto auxiliar com resumo + termos relacionados;
   - gera embedding com `text-embedding-3-small`;
   - insere o novo registro em `lwsa.gabarito_prb`.
7. Faz `commit` a cada PRB processado.
8. Registra a execução em arquivo de log dentro da pasta `logs/` do diretório do módulo.

Objetivo prático: transformar o histórico de problemas resolvidos em uma base vetorial e estruturada para comparação futura.

### `monitoramento_diario.py`
Responsável por localizar atendimentos recentes e compará-los com os gabaritos de PRB.

Fluxo executado:

1. Lê as credenciais do `config.ini`.
2. Define o período do monitoramento por dois campos manuais no próprio código:
   - `DATA_INICIO_MANUAL`
   - `DATA_FIM_MANUAL`
3. Se os dois campos ficarem vazios, o script usa automaticamente **D-1**.
4. Você também pode passar o intervalo diretamente pela linha de comando usando `--inicio` e `--fim`.
5. Abre conexão com o PostgreSQL.
5. Carrega os gabaritos salvos em `lwsa.gabarito_prb`.
6. Busca atendimentos encerrados no período definido em:
   - `lw_octadesk.chat`
   - `dynamics.chamados`
7. Para cada atendimento encontrado:
   - junta título + conteúdo;
   - gera embedding com `text-embedding-3-small`;
   - compara com todos os gabaritos;
   - ignora casos em que o atendimento ocorreu antes ou no mesmo dia do PRB resolvido;
   - calcula similaridade de cosseno;
   - se a similaridade for alta, envia o texto para o `gpt-4o-mini` validar se o caso é realmente reincidente.
8. Se a origem for `chat`, lê a coluna `canal` da tabela `lw_octadesk.chat` e grava o valor normalizado em `origem_tipo`.
  - `web` é gravado como `chat`
  - `whatsapp` é gravado como `whatsapp`
9. Antes de gravar, verifica se o `origem_id` já existe em `lwsa.ocorrencia_reincidencia` para evitar duplicidade.
10. Se a IA confirmar a reincidência e o `origem_id` ainda nao tiver sido gravado, salva o evento em `lwsa.ocorrencia_reincidencia`.
11. Exibe no console o total de alertas gravados.
12. Registra os eventos principais em arquivo de log dentro da pasta `logs/` do diretório do módulo.

## Como a validação funciona

A detecção de reincidência usa duas camadas:

### Camada 1: Similaridade vetorial
O texto do atendimento é convertido em embedding e comparado com o embedding do gabarito salvo.

- Se a similaridade ficar abaixo de `0.72`, o caso é descartado.
- Se ficar acima ou igual a `0.72`, o atendimento segue para a validação de IA.

### Camada 2: Validação com LLM
O modelo `gpt-4o-mini` recebe:

- o texto completo do atendimento;
- a `descricao_resumida` do gabarito candidato.

Ele responde em JSON com:

- `reincidente`:
- `confianca`:
- `justificativa`:

Se `reincidente = true`, o sistema grava o alerta no banco.

## Tabelas utilizadas

### Entrada

- `lwsa.service_now_problems`
  - usada para carregar os PRBs históricos encerrados;
  - colunas principais usadas: `numero`, `data_encerrado`, `descricao_curta`, `descricao`.

- `lwsa.gabarito_prb`
  - usada como base de comparação no monitoramento;
  - colunas principais usadas: `prb_id`, `data_conclusao`, `categoria`, `tag`, `descricao_resumida`, `termos_relacionados`, `embedding_sintoma`.

- `lw_octadesk.chat`
  - usada para ler chats encerrados no período.

- `dynamics.chamados`
  - usada para ler chamados encerrados no período.

### Saída

- `lwsa.ocorrencia_reincidencia`
  - recebe os alertas confirmados pela análise;
  - armazena origem, data, texto analisado, score de similaridade, score de confiança e justificativa da IA;
  - evita duplicidade quando o mesmo `origem_id` já foi registrado.

## Configuração de datas no monitoramento

No arquivo `monitoramento_diario.py`, existem dois campos para edição manual:

```python
DATA_INICIO_MANUAL = "2026-06-01"
DATA_FIM_MANUAL = "2026-06-05"
```

Regras de uso:

- Se preencher os dois campos, o monitoramento usa o intervalo informado.
- Se preencher apenas a data inicial, o script usa apenas aquele dia.
- Se deixar os dois como `None`, o monitoramento usa D-1.
- Alternativamente, você pode passar as datas pela linha de comando com `--inicio` e `--fim`.

## Normalização de origem

Quando a linha vem da tabela `lw_octadesk.chat`, o valor da coluna `canal` é usado para preencher `origem_tipo` na tabela `lwsa.ocorrencia_reincidencia`.

Regra atual:

- `web` vira `chat`
- `whatsapp` permanece `whatsapp`
- qualquer valor sem preenchimento é tratado como `chat`

## Execução

### 1. Carga histórica dos gabaritos

Execute o arquivo `gabarito_prb.py` para popular ou atualizar a tabela de gabaritos:

```bash
python gabarito_prb.py
```

### 2. Monitoramento diário

Execute o arquivo `monitoramento_diario.py` para analisar os atendimentos do período configurado:

```bash
python monitoramento_diario.py
```

Para comparar dados históricos sem aplicar a regra de data de conclusão do gabarito, use:

```bash
python monitoramento_diario.py --historic
```

Você também pode passar o intervalo diretamente pela linha de comando:

```bash
python monitoramento_diario.py --inicio 2026-05-01 --fim 2026-05-31
```

## Dependências

Os scripts usam principalmente:

- `psycopg2`
- `numpy`
- `openai`
- `configparser`
- `argparse`

## Saída esperada

Durante a execução, o monitoramento imprime mensagens como:

- início do processamento;
- quantidade de gabaritos carregados;
- período analisado;
- quantidade de atendimentos capturados;
- quantidade de reincidências gravadas;
- erros críticos, se houver.

Além disso, o monitoramento também grava um arquivo de log diário em `Monitoramento PRB/logs/`, com nome no formato `monitoramento_diario_YYYYMMDD.log`.

O script de carga histórica `gabarito_prb.py` também grava um arquivo de log diário em `Monitoramento PRB/logs/`, com nome no formato `gabarito_prb_YYYYMMDD.log`.

## Estrutura resumida do sistema

### Etapa 1: carga histórica

O script `gabarito_prb.py` lê os PRBs encerrados do ServiceNow, filtra os que ainda não possuem gabarito, usa IA para extrair um resumo padronizado do sintoma e insere o novo conteúdo com embedding em `lwsa.gabarito_prb`. PRBs já processados são ignorados para evitar custo desnecessário com a API.

### Etapa 2: monitoramento diário

O script `monitoramento_diario.py` busca chats e chamados encerrados no período definido, compara o texto com os gabaritos carregados e grava reincidências confirmadas em `lwsa.ocorrencia_reincidencia`.

Antes da gravação, o script consulta a tabela de ocorrências para impedir que o mesmo `origem_id` seja inserido duas vezes.

### Etapa 3: decisão semântica

O sistema só grava o alerta quando duas condições acontecem ao mesmo tempo:

- a similaridade vetorial é alta;
- o LLM confirma que o caso é realmente reincidente.

## Observações importantes

- O monitoramento depende de dados já carregados em `lwsa.gabarito_prb`.
- Se a tabela de gabaritos estiver vazia, o monitoramento não prossegue.
- O sistema usa IA tanto para estruturar os PRBs históricos quanto para validar alertas de reincidência.
- A precisão do resultado depende da qualidade do texto registrado nas bases operacionais.
