# Documentação do `cplug/mensagens`

## Visão geral

Esta aplicação coleta mensagens de chats da API CPlug/Tray para atender ao histórico de mensagens por atendimento.

O fluxo principal é executado por `CarregaMensagensi.bat`, que chama `python api.py`.

## Objetivos

- consultar chats recentes em `cplug.chat`
- buscar mensagens de cada atendimento via endpoint `/chat/{id}/messages`
- armazenar JSON bruto em `cplug.rawdata_mensagens`
- consolidar registros novos e atualizações em `cplug.mensagens`
- manter histórico atualizado no banco PostgreSQL

## Estrutura dos arquivos

- `api.py`: script principal de extração, tratamento e carregamento
- `CarregaMensagensi.bat`: wrapper Windows para executar `python api.py`
- `function_logger.py`: gerador de logger com saída em arquivo e console
- `insereDadosMensagens.sql`: inserção de novos registros em `cplug.mensagens`
- `AtualizaDados.sql`: atualização de registros existentes em `cplug.mensagens`
- `README.md`: documentação do processo

## Dependências Python

O script depende de:

- `pandas`
- `sqlalchemy`
- `psycopg2`
- `requests`
- `urllib3`

## Configuração necessária

O script lê o arquivo `config.ini` a partir da raiz do repositório:

```python
config_file_path = Path(__file__).resolve().parent.parent.parent / 'config.ini'
```

O arquivo deve conter as seções abaixo:

```ini
[cplug]
DDL_URL = https://sua-instancia.octadesk.services
TOKEN = seu_token_api
verify_ssl = true

[database]
server = <host>
database = <nome_do_banco>
uid = <usuario>
pwd = <senha>
```

### Observação

- `verify_ssl` é opcional; se `false`, o script desabilita avisos de SSL inseguros.
- Garanta que o `config.ini` esteja acessível a partir da raiz do workspace.

## Fluxo completo de execução

### 1. Inicialização

- configura logger usando `function_logger.configurar_logger`
- lê `config.ini`
- estabelece conexões PostgreSQL via SQLAlchemy e `psycopg2`
- calcula a janela de consulta para chats recentes:
  - `data_hora = datetime.now()`
  - `hora_anterior = data_hora - timedelta(hours=1)`

### 2. Selecionar chats a processar

O script executa:

```python
query = f"SELECT id , data_ultima_interacao FROM cplug.chat WHERE data_ultima_interacao >= '{data} {hora_anterior}'"
```

Isso seleciona atendimentos com última interação na última hora.

### 3. Buscar mensagens por atendimento

Para cada `id` retornado, chama `get_message`:

```python
endpoint = f"{DDL_URL}/chat/{ID}/messages?limit={limit}"
```

- limite fixo de 100 mensagens por requisição
- autenticação via `X-API-KEY`
- timeout de 30 segundos

### 4. Ajuste de datas

A função `ajusta_formato_data` transforma timestamps ISO UTC em `YYYY-MM-DD HH:MM:SS` no fuso -3h (BRT).

### 5. Gravar JSON bruto em `rawdata_mensagens`

O script monta um DataFrame `df_content` com colunas:

- `id`
- `data_ultima_interacao`
- `mensagens` (JSON serializado)

Em seguida, insere em `cplug.rawdata_mensagens` usando `to_sql` com `if_exists='replace'`. Se falhar, tenta `if_exists='append'`.

### 6. Garantir tabela temporária

O script executa um `DROP TABLE IF EXISTS cplug.rawdata_mensagens` e tenta conceder privilégios ao usuário.

### 7. Inserir novos registros em `cplug.mensagens`

Executa `insereDadosMensagens.sql`, que insere apenas registros cuja chave `id` não exista ainda em `cplug.mensagens`.

### 8. Atualizar registros existentes

Executa `AtualizaDados.sql`, que atualiza `mensagens` e `data_ultima_interacao` quando o registro em `rawdata_mensagens` estiver mais atualizado.

### 9. Encerramento

- fecha conexão `connection`
- libera `engine`
- imprime timestamp final

## Descrição dos scripts SQL

### `insereDadosMensagens.sql`

Insere dados em `cplug.mensagens` a partir de `cplug.rawdata_mensagens`:

- transforma `mensagens` em JSON
- mantém `id`, `data_ultima_interacao`
- define `fonte_de_dados = 'Endpoint /id/messages'`
- registra `data_insercao` e `data_modificacao`
- apenas novos `id`

### `AtualizaDados.sql`

Atualiza registros existentes em `cplug.mensagens` quando:

- `rawdata_mensagens.id = mensagens.id`
- `rawdata_mensagens.data_ultima_interacao > mensagens.data_ultima_interacao`

Atualiza:

- `data_ultima_interacao`
- `mensagens`
- `data_modificacao`

## Tabelas envolvidas

- `cplug.chat`: fonte inicial de atendimentos recentes
- `cplug.rawdata_mensagens`: tabela temporária / staging com JSON bruto
- `cplug.mensagens`: tabela final com mensagens consolidadas

## Execução

No Windows, use:

```bat
CarregaMensagensi.bat
```

Ou execute diretamente:

```powershell
python api.py
```

## Observações importantes

- O script depende do schema `cplug` existir no banco PostgreSQL.
- A janela de seleção é de 1 hora; se precisar processar mais dados, altere `hora_anterior`.
- `limit = 100` é fixo para o endpoint de mensagens.
- A conversão de `mensagens` usa `json.dumps` antes de gravar no DataFrame.
- `rawdata_mensagens` é substituída a cada execução.

## Possíveis melhorias

- parametrizar a janela de busca via argumentos de linha de comando
- adicionar tratamento de paginação quando houver mais de 100 mensagens
- extrair `config_file_path` para variável de ambiente
- melhorar logs para incluir contagem de chats processados e falhas por atendimento
