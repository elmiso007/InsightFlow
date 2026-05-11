# Octadesk Pesquisas

Aplicacao em Python para coletar pesquisas de satisfacao do Octadesk via API e
carregar em banco PostgreSQL. O fluxo completo inclui:
1) requisicao paginada na API,
2) normalizacao de datas,
3) persistencia do JSON bruto,
4) carga em tabela staging,
5) insercao na tabela final via SQL,
6) notificacoes.

## Estrutura da pasta

- `api.py`: ponto de entrada da rotina
- `function_logger.py`: configuracao do logger com rotacao
- `insereDados.sql`: insert/normalizacao para tabela final
- `AlimentaPesquisas.bat`: script de execucao no Windows
- `.env`: variaveis de ambiente (nao versionar)
- `requirements.txt`: dependencias do projeto
- `pesquisas.json`: cache JSON gerado pela execucao
- `logs.log`: log principal (com rotacao)

## Requisitos

- Python 3.x
- PostgreSQL acessivel a partir do host de execucao
- Acesso a API do Octadesk
- Dependencias Python (veja `requirements.txt`)

Instalacao das dependencias:

```
pip install -r requirements.txt
```

## Configuracao (.env)

Crie um arquivo `.env` na raiz da pasta com as variaveis abaixo:

```
OCTADESK_DB_HOST=...
OCTADESK_DB_NAME=...
OCTADESK_DB_USER=...
OCTADESK_DB_PASSWORD=...
OCTADESK_API_BASE_URL=https://help.apibeta.octadesk.services
OCTADESK_API_TOKEN=...
OCTADESK_LOG_LEVEL=INFO
OCTADESK_LOG_MAX_BYTES=5242880
OCTADESK_LOG_BACKUP_COUNT=5
```

## Como executar

### Windows (batch)

```
AlimentaPesquisas.bat
```

### Python

```
python api.py
```

## Etapas da rotina (fluxo completo)

1. **Carregamento do .env**
   - O `api.py` le o arquivo `.env` e injeta as variaveis no ambiente.
   - Variaveis obrigatorias: `OCTADESK_DB_HOST`, `OCTADESK_DB_NAME`,
     `OCTADESK_DB_USER`, `OCTADESK_DB_PASSWORD`, `OCTADESK_API_TOKEN`.

2. **Inicializacao do logger**
   - Log em arquivo e console.
   - Rotacao configuravel por tamanho e quantidade de backups.

3. **Conexao com PostgreSQL**
   - Cria `engine` SQLAlchemy e conexao psycopg2.
   - Falhas de conexao sao registradas no log.

4. **Requisicao paginada na API**
   - Endpoint: `/survey/submissions`
   - Filtros: `type=chat`, `isAnswered=true`, janela de datas (ultimos 5 dias).
   - Paginas de 1 a 15, interrompe quando a API nao retorna dados.

5. **Normalizacao e modelagem**
   - Conversao de datas ISO para formato Postgres.
   - Extracao de campos e respostas (p1 a p4).

6. **Persistencia do JSON bruto**
   - Salva `pesquisas.json` com todos os registros retornados.

7. **Carga na tabela staging**
   - Gera DataFrame com os registros.
   - Carrega em `octadesk.rawdata_pesquisas` (replace).

8. **Insercao na tabela final**
   - Executa `insereDados.sql`.
   - Tabela final: `octadesk.pesquisa_de_satisfacao`.

9. **Notificacoes**
   - Envia notificacao de sucesso/erro via modulo `notifica`.

10. **Metrica de tempo**
   - Registra tempo por pagina, por etapa e tempo total.

## Logs e rotacao

- Arquivo principal: `logs.log`
- Quando o arquivo atinge `OCTADESK_LOG_MAX_BYTES`, ele e rotacionado:
  `logs.log.1`, `logs.log.2`, etc.
- Mantem no maximo `OCTADESK_LOG_BACKUP_COUNT` arquivos de backup.

## Observacoes

- O modulo `notifica` e importado de um diretorio acima do projeto.
- Recomenda-se nao versionar o `.env` por conter segredos.
