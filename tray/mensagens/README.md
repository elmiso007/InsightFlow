# Documentação da Aplicação de Ingestão de Mensagens Tray

## Visão Geral

Esta aplicação é um script Python responsável por coletar mensagens de chats da plataforma Tray via API, processar os dados e inseri-los em um banco de dados PostgreSQL. O processo inclui:

- Consulta de chats com interação recente (última hora)
- Recuperação de mensagens via API REST
- Armazenamento temporário em tabela `rawdata_mensagens`
- Processamento e inserção final na tabela `mensagens`
- Atualização de dados existentes

## Pré-requisitos

- **Python 3.7+**
- **Bibliotecas Python**:
  - pandas
  - sqlalchemy
  - psycopg2
  - requests
  - urllib3
  - configparser
  - pathlib

- **Banco de Dados**: PostgreSQL
- **Arquivo de Configuração**: `config.ini` no diretório pai

## Instalação

1. Instale as dependências Python:
   ```bash
   pip install pandas sqlalchemy psycopg2-binary requests urllib3
   ```

2. Configure o arquivo `config.ini` com as seguintes seções:
   ```ini
   [tray]
   DDL_URL = https://api.tray.com.br
   TOKEN = seu_token_aqui
   verify_ssl = true

   [database]
   server = localhost
   database = nome_do_banco
   uid = usuario
   pwd = senha
   ```

## Estrutura dos Arquivos

- `api.py`: Script principal de execução
- `function_logger.py`: Módulo para configuração de logging
- `insereDadosMensagens.sql`: Script SQL para inserção de dados processados
- `AtualizaDados.sql`: Script SQL para atualização de dados existentes
- `CarregaChatApi.bat`: Script batch para execução automatizada (Windows)

## Como Executar

### Execução Manual
```bash
python api.py
```

### Execução via Batch (Windows)
```bash
CarregaChatApi.bat
```

## Fluxo de Execução

1. **Conexão**: Estabelece conexão com PostgreSQL
2. **Consulta**: Busca chats com `data_ultima_interacao` na última hora
3. **API Calls**: Para cada chat, chama a API Tray para obter mensagens
4. **Processamento**: Converte dados JSON e armazena em DataFrame
5. **Inserção**: Grava dados brutos na tabela `tray.rawdata_mensagens`
6. **Processamento SQL**: Executa `insereDadosMensagens.sql` para inserir dados limpos
7. **Atualização**: Executa `AtualizaDados.sql` para atualizar registros existentes

## Logs

A aplicação utiliza logging configurado em `function_logger.py`. Os logs incluem:
- Conexão bem-sucedida ao banco
- Número de linhas inseridas/atualizadas
- Erros de execução

## Tratamento de Erros

- **Conexão DB**: Falha na conexão com PostgreSQL
- **API**: Falha na autenticação ou timeout (30s)
- **SQL**: Erros na execução de queries
- **SSL**: Desabilitação de verificação SSL se configurado

## Configurações Avançadas

- **Limite de Mensagens**: Fixo em 100 por chat
- **Fuso Horário**: Ajuste automático de UTC para BRT (-3h)
- **Timeout API**: 30 segundos por requisição

## Monitoramento

- Verifique os logs para acompanhar o progresso
- Monitore o banco para verificar inserções
- Em caso de falhas, verifique conectividade de rede e credenciais

## Suporte

Para dúvidas ou problemas, verifique:
1. Configurações em `config.ini`
2. Logs de execução
3. Conectividade com API Tray
4. Acesso ao banco PostgreSQL</content>
<filePath>c:\Users\emerson.ramos\Desktop\projetos\tray\mensagens\README.md