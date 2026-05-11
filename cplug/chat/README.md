# Documentação do `cplug/chat`

## Visão geral

Esta aplicação carrega dados de chat da API externa da Tray/CPlug e alimenta tabelas PostgreSQL no schema `cplug`.

O fluxo principal é executado a partir de `CarregaChatApi.bat`, que chama `python api.py`.

## Objetivo

- coletar interações de chat atualizadas nas últimas 6 horas
- persistir dados em tabelas intermediárias e finais no banco de dados
- transformar e normalizar campos de chat
- inserir novos registros e atualizar registros existentes
- registrar logs e enviar notificações de sucesso ou erro

## Estrutura dos arquivos

- `api.py`: script principal de extração, transformação e carregamento (ETL)
- `CarregaChatApi.bat`: comando para iniciar o script Python
- `chat_cplug.json`: exemplo de payload JSON retornado pela API
- `StgInsereDados.sql`: script que popula a tabela staging `cplug.stg_chat`
- `InsereDados.sql`: script que insere novos registros em `cplug.chat`
- `AtualizaDados.sql`: script que atualiza registros existentes em `cplug.chat`
- `erro_execucao.log`: arquivo de logs da execução

## Dependências Python

O script usa os seguintes pacotes:

- `requests`
- `pandas`
- `sqlalchemy`
- `psycopg2`
- `configparser`

Além disso, importa funções de notificação Slack de `notifica.py`:

- `notify_slack`
- `notify_slack_success`

> O módulo `notifica.py` precisa estar disponível no PYTHONPATH ou em um diretório superior acessível por `sys.path.append`.

## Configuração necessária

### Arquivo `config.ini`

O script lê o arquivo de configuração em um caminho fixo:

```python
config_folder = r'C:\Users\lucas.abner\Desktop\Rotinas Python'
config_file_path = os.path.join(config_folder, 'config.ini')
```

O `config.ini` deve conter pelo menos as seções:

```ini
[database]
server = <host>
database = <nome_do_banco>
uid = <usuario>
pwd = <senha>

[cplug]
DDL_URL = <url_da_api>
TOKEN = <chave_api>
```

### Observação

- Atualize `config_folder` para o caminho correto do arquivo de configuração no ambiente de produção.
- Se o arquivo `notifica.py` não estiver em `cplug`, garanta que o import `from notifica import ...` funcione corretamente.

## Fluxo completo de execução

### 1. Iniciar a rotina

Execute `CarregaChatApi.bat` ou rode diretamente `python api.py` no diretório `cplug/chat`.

### 2. Inicialização do script

- Configura logging para `erro_execucao.log`
- Lê configurações do `config.ini`
- Cria conexões PostgreSQL com SQLAlchemy e psycopg2
- Define a rotina como `Cplug (Carrega data Chat)`

### 3. Montar período de busca

O script calcula o período inicial como UTC atual menos 6 horas:

```python
periodo = (agora_utc - timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
```

Esse valor é usado para filtrar registros pela data `updatedAt`.

### 4. Consultar API paginada

A função `get_interactions` monta a URL:

```python
endpoint = f"{DDL_URL}/chat?filters[0][operator]=ge&filters[0][property]=updatedAt&filters[0][value]={periodo}&page={page}&limit={limit}&sort[direction]=asc"
```

- `limit` padrão: 100
- `sort[direction]=asc`
- autenticação via header `X-API-KEY`

### 5. Paginação

O script faz loop em páginas enquanto houver dados:

- obtém `X-Total-Pages` do cabeçalho HTTP
- processa cada página
- incrementa `current_page`
- encerra quando `current_page >= total_pages`

### 6. Processar registros retornados

Para cada registro retornado pela API, o script:

- captura `id`, `number`, `channel`, `createdAt`, `updatedAt`, `closedAt`
- ajusta timestamps ISO com `ajusta_formato_data`
- extrai dados de `contact`, `group`, `agent`, `bot`, `survey`
- cria dois objetos:
  - `registro_bruto`: registro completo guardado em `raw_data_chat`
  - `registro`: dados normalizados guardados em `payload_chat`

### 7. Gravacao no banco de dados

Após coletar todas as páginas:

- grava `df_payload` em `cplug.payload_chat` com `if_exists='replace'`
- grava `df_bruto` em `cplug.raw_data_chat` com `if_exists='append'`

### 8. Truncar tabela de stage

O script executa:

```sql
TRUNCATE TABLE cplug.stg_chat
```

### 9. Inserir dados no stage

Executa `StgInsereDados.sql`, que transforma e popula `cplug.stg_chat` a partir de `cplug.payload_chat`.

Principais transformações:

- conversão de strings para `TIMESTAMP`
- cálculo de `tempo_atendimento_segundos`
- normalização de `contact_name` e `contact_id`
- extração de até 5 tags em `tag_1` a `tag_5`
- marcação de `fonte_de_dados = 'API Pública - Endpoint /chat'`

### 10. Inserir registros novos em `cplug.chat`

Executa `InsereDados.sql` para inserir somente registros que ainda não existem em `cplug.chat`.

### 11. Atualizar registros existentes

Executa `AtualizaDados.sql` para atualizar linhas em `cplug.chat` quando `data_ultima_interacao` do stage for mais recente do que a existente.

### 12. Notificação e finalização

- em caso de erro: envia mensagem via `notify_slack` e escreve no `erro_execucao.log`
- ao final: chama `notify_slack_success`
- fecha conexões e encerra o programa

## Tabelas envolvidas

- `cplug.payload_chat`
- `cplug.raw_data_chat`
- `cplug.stg_chat`
- `cplug.chat`

### Função das tabelas

- `payload_chat`: versão normalizada/tabular dos dados brutos do JSON
- `raw_data_chat`: captura de payload completo em coluna JSON
- `stg_chat`: tabela staging com transformações e cálculos adicionais
- `chat`: tabela final que recebe inserções e atualizações

## Observações importantes

- O script usa `if_exists='replace'` para `payload_chat`, portanto o conteúdo é renovado a cada execução.
- `raw_data_chat` é append-only e pode crescer rapidamente se executado várias vezes.
- As queries SQL assumem que as colunas estão corretamente tipadas no schema `cplug`.
- O arquivo `config.ini` e o token da API devem ser mantidos seguros.

## Como rodar

1. Abra o prompt de comando no diretório `cplug/chat`
2. Execute:

```bat
CarregaChatApi.bat
```

ou

```powershell
python api.py
```

3. Verifique os resultados em PostgreSQL e os arquivos de log.

## Problemas comuns

- `config.ini` não encontrado: ajuste `config_folder`
- erro de conexão PostgreSQL: confira `server`, `database`, `uid`, `pwd`
- erro de autenticação da API: valide `DDL_URL` e `TOKEN`
- caminho da importação `notifica.py` incorreto: garanta que o módulo esteja disponível

## Próximos passos sugeridos

- mover o caminho de configuração para variável de ambiente ou argumento de linha de comando
- parametrizar o `periodo` de busca e o `limit`
- armazenar o JSON completo por página em arquivos separados para auditoria
- adicionar tratamento de paginação por `next page` mais robusto se a API mudar
