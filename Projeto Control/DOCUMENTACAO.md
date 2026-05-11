# Documentação - Projeto Control

## 📋 Visão Geral

O **Projeto Control** é uma aplicação de automação que gerencia escalas operacionais de equipes de atendimento. A aplicação sincroniza dados de uma planilha Google Sheets com um banco de dados PostgreSQL e notifica os analistas sobre suas escalas de trabalho através do Slack.

**Data da Análise:** 6 de fevereiro de 2026  
**Última Atualização:** 3 de fevereiro de 2025

---

## 🏗️ Arquitetura do Sistema

### Componentes Principais

```
┌─────────────────────────────────────────────────────────────┐
│                   Google Sheets                              │
│         (Planilha: Pausas Proc N1)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │    get_escala.py         │
        │  (Google Sheets API)     │
        └────────┬─────────────────┘
                 │
                 ▼
        ┌──────────────────────────┐
        │      app.py              │
        │   (Lógica Principal)     │
        └────┬─────────────────────┘
             │
             ├─────────┬─────────────────┐
             ▼         ▼                 ▼
        PostgreSQL  Slack API      Log File
        (Database) (Notificações) (logfile.txt)
```

---

## 📁 Estrutura de Arquivos

```
Projeto Control/
├── app.py                    # Aplicação principal
├── get_escala.py            # Integração com Google Sheets
├── notifica.py              # Integração com Slack
├── config.toml              # Configurações da aplicação
├── InsereDados.sql          # Script de inserção de dados
├── AtualizaDados.sql        # Script de atualização de dados
├── InativaDados.sql         # Script de inativação de dados
├── ExecutaApp.bat           # Script de execução (Windows)
├── escala.json              # Cache de dados (opcional)
├── token.json               # Token de autenticação
├── logfile.txt              # Registro de execuções
└── __pycache__/             # Cache Python
```

---

## 🔧 Detalhamento dos Componentes

### 1. **app.py** - Aplicação Principal

#### Responsabilidades:
- Orquestrar todo o fluxo de sincronização
- Conectar ao banco de dados PostgreSQL
- Chamar a função de obtenção de dados da planilha
- Executar scripts SQL de sincronização
- Disparar notificações via Slack
- Gerar logs de execução

#### Fluxo de Execução:

```
1. Ler configurações do arquivo config.ini
   ↓
2. Conectar ao banco de dados PostgreSQL
   ↓
3. Chamar get_escala() para obter dados da planilha
   ↓
4. Converter dados para DataFrame do Pandas
   ↓
5. Renomear colunas do DataFrame
   ↓
6. Inserir dados brutos na tabela 'control_desk.rawdata'
   ↓
7. Verificar se é o primeiro dia do mês
   ├─ SIM: Notificar TODOS os analistas ativos
   └─ NÃO: Notificar apenas novos registros e atualizações
```

#### Verificação de Data Especial (Dia 1º do mês):
- **Se é o 1º dia:** Executa operações completas (INSERT + UPDATE + DELETE) e notifica TODOS
- **Se não é o 1º dia:** Executa apenas operações de sincronização incremental

#### Estrutura da Tabela PostgreSQL (control_desk.mapa_operacional):
```
- id (Primary Key)
- login
- matricula
- status (Ativo/Inativado)
- equipe
- skill
- funcao
- coordenador
- horario
- pausa1
- intervalo
- pausa3
- saida
- observacoes
- id_slack
- fonte_de_dados
- data_insercao
- data_modificacao
```

#### Variáveis Importantes:
- `server`, `database`, `uid`, `pwd`: Credenciais do banco de dados
- `tabela`: Nome da tabela destino ('rawdata' ou 'mapa_operacional')
- `schema`: Schema do banco ('control_desk')
- `data_hora`: Timestamp da execução

---

### 2. **get_escala.py** - Integração Google Sheets

#### Responsabilidades:
- Autenticar na API do Google Sheets
- Conectar à planilha especificada
- Extrair dados da aba "Pausas Proc N1"
- Formatar os dados extraídos
- Retornar uma lista de dicionários com os dados

#### Configurações Google Sheets:
```python
SAMPLE_SPREADSHEET_ID = "1MmL9p4Hyn2DIYJKzY7vsbVM9h1Hw4wB0s-SMJMUFLhU"
SAMPLE_RANGE_NAME = "Pausas Proc N1!A1:N"
```

#### Fluxo de Operação:
```
1. Importar módulo de autenticação (../API Google/auth.py)
   ↓
2. Obter credenciais através da função authenticate()
   ↓
3. Construir serviço Sheets API v4
   ↓
4. Chamar API para obter dados da planilha
   ↓
5. Mapear índices das colunas relevantes
   ↓
6. Extrair dados linha por linha
   ↓
7. Retornar lista de dicionários com os dados
```

#### Colunas Extraídas:
- Login
- Matrícula
- Status
- Equipe
- Skill
- Função
- Coordenador
- Horário
- Pausa 1
- Almoço (intervalo)
- Pausa 3
- Saída
- Observações
- ID Slack

#### Tratamento de Erros:
- Captura erros HTTP da API Google
- Exibe mensagem de erro no console
- Retorna lista vazia se não houver dados

---

### 3. **notifica.py** - Integração Slack

#### Responsabilidades:
- Autenticar no Slack
- Montar mensagens formatadas para cada analista
- Enviar notificações via Direct Message
- Lidar com erros de envio

#### Token Slack:
```python
client = WebClient('[REDACTED_SLACK_TOKEN]')
```

#### Estrutura da Mensagem Slack:
A mensagem é formatada usando **Block Kit** (formato de blocos do Slack) com:

1. **Header:** Saudação personalizada com menção ao usuário
2. **Seção Principal:** Informações da escala (mês, função, equipe)
3. **Divisor:** Separador visual
4. **Seção Horários:** Detalhes dos horários de trabalho:
   - Horário de início
   - Primeira pausa
   - Intervalo/Almoço
   - Segunda pausa
   - Saída
   - Imagem logo Locaweb
5. **Divisor:** Separador visual
6. **Seção Final:** Instruções para ajustes e menção ao coordenador

#### Informações da Notificação:
```
Função da Notificação: notifica_analista()

Parâmetros:
- login: Login do usuário (usado para menção @)
- horario: Horário de início
- pausa1: Primeira pausa
- intervalo: Intervalo de almoço
- pausa3: Segunda pausa
- saida: Horário de saída
- id_slack: ID único do usuário no Slack (começa com 'U')
- funcao: Função do analista
- equipe: Nome da equipe
- coordenador: Login do coordenador (para menção @)
- skill: Habilidade/especialidade (opcional)
```

#### Validações:
- Verifica se ID Slack começa com 'U' (válido para usuários)
- Abre conversation com o usuário via `conversations_open()`
- Envia mensagem via `chat_postMessage()`

#### Tratamento de Erros:
- Try/Except para capturar exceções ao enviar
- Exibe mensagem de erro no console se falhar

---

### 4. **Scripts SQL**

#### InsereDados.sql
**Objetivo:** Inserir novos registros de analistas que ainda não existem no sistema

**Lógica:**
- Seleciona dados da tabela `rawdata`
- Faz LEFT JOIN com `mapa_operacional` para encontrar ausentes
- Converte tipos de dados apropriados:
  - Logins em minúsculas
  - Matrícula como INTEGER
  - Horários como TIME
- Retorna os campos inseridos para envio de notificações

```sql
WHERE NOT EXISTS (
    SELECT 1 
    FROM control_desk.mapa_operacional AS i
    WHERE i.matricula = CAST(r.matricula AS INTEGER)
)
```

#### AtualizaDados.sql
**Objetivo:** Atualizar registros que sofreram alterações nos dados

**Lógica:**
- Compara valores atuais com novos valores
- Atualiza apenas campos que realmente mudaram
- Registra `data_modificacao` como NOW()
- Retorna registros modificados para notificação

**Campos Verificados:**
- status
- equipe
- skill
- funcao
- coordenador
- horario
- pausa1
- intervalo
- pausa3
- saida
- observacoes
- id_slack

#### InativaDados.sql
**Objetivo:** Inativar registros que desapareceram da planilha

**Lógica:**
- Encontra registros que estão em `mapa_operacional` mas NÃO estão em `rawdata`
- Muda status para 'Inativado'
- Atualiza `data_modificacao`
- Apenas afeta registros com status 'Ativo'

```sql
WHERE NOT EXISTS (
    SELECT 1
    FROM control_desk.rawdata r
    WHERE i.matricula = CAST(r.matricula AS INTEGER)
) AND status in ('Ativo')
```

---

### 5. **config.toml** - Arquivo de Configuração

```toml
[database]
SERVER="10.30.138.28"          # IP do servidor PostgreSQL
DATABASE = "report_requesttracker"
USER = "a_report"
PWD = "Eequ8ohc"

[app]
debug = true
```

**Observação:** O app.py lê configurações de `config.ini` no caminho:
```
C:\Users\lucas.abner\Desktop\Rotinas Python\config.ini
```

---

### 6. **ExecutaApp.bat** - Script de Execução

```batch
python app.py
```

Script simples que executa a aplicação Python no Windows.

**Uso típico:**
- Agendado via Task Scheduler do Windows
- Executado diariamente

---

## 📊 Fluxo de Dados Completo

```
Google Sheets (Planilha)
        │
        ▼
get_escala.py
(API Google Sheets)
        │
        ▼
    DataFrame
    (Pandas)
        │
        ▼
control_desk.rawdata (INSERT)
        │
        ▼
InsereDados.sql
├─ Inserir novos analistas
└─ Retornar lista de inseridos
        │
        ▼
AtualizaDados.sql
├─ Atualizar registros modificados
└─ Retornar lista de atualizados
        │
        ▼
InativaDados.sql
├─ Inativar ausentes
└─ Sem retorno
        │
        ▼
notifica.py (Slack)
├─ Enviar DM para cada analista
└─ Registrar no log
        │
        ▼
logfile.txt
(Registro de execuções)
```

---

## 🔄 Ciclo de Execução

### Dia 1º do Mês (Notificação Completa)
1. Obtém dados da planilha
2. Carrega na tabela rawdata
3. **Executa InsereDados.sql** → Insere novos analistas
4. **Executa AtualizaDados.sql** → Atualiza modificados
5. **Executa InativaDados.sql** → Inativa ausentes
6. **Consulta mapa_operacional** onde status = 'Ativo'
7. **Notifica TODOS os analistas ativos** via Slack
8. Registra todas as notificações no logfile.txt

### Outros Dias do Mês (Notificação Incremental)
1. Obtém dados da planilha
2. Carrega na tabela rawdata
3. **Executa InsereDados.sql** → Insere novos (retorna lista)
4. **Notifica apenas os novos** via Slack
5. **Executa AtualizaDados.sql** → Atualiza modificados (retorna lista)
6. **Notifica apenas os atualizados** via Slack
7. Registra as notificações no logfile.txt

---

## 📝 Sistema de Logs

### Arquivo: logfile.txt

**Formato:**
```
YYYY-MM-DD HH:MM:SS - Tipo de Evento | ID Slack: XXXXXXXXX | Login: nome.usuario
```

**Exemplos:**
```
2025-02-03 11:38:02 - Notificação Enviada | ID Slack: U0715F6AAM8 | Login: arthur.favero
2025-02-03 11:38:02 - Registro Inserido | ID Slack: U06V9FQJE6B | Login: vanderlei.cardoso
2025-02-03 11:38:02 - Registro Atualizado | ID Slack: U0747C7KEBA | Login: mauricio.junior
```

**Tipos de Eventos:**
- Notificação Enviada
- Registro Inserido
- Registro Atualizado

---

## 🔐 Autenticação e Segurança

### Google Sheets API
- Autentica via arquivo de credenciais
- Localizado em: `../API Google/auth.py`
- Usa OAuth 2.0

### Slack API
- Token hardcoded no arquivo notifica.py
- Token type: Bot Token (xoxb-...)
- **RISCO DE SEGURANÇA:** Token exposto no código

### PostgreSQL
- Usuário: a_report
- Autenticação via password
- **RISCO DE SEGURANÇA:** Credenciais em arquivo de configuração

---

## ⚠️ Pontos de Atenção

### 1. **Caminhos Hardcoded**
- `C:\Users\lucas.abner\Desktop\Rotinas Python\config.ini`
- Não funciona em outras máquinas sem ajustes
- Dependência de estrutura de diretórios específica

### 2. **Token de Slack Exposto**
- Token do Slack está visível no código
- Deve ser movido para variável de ambiente

### 3. **Configuração Duplicada**
- Existe `config.toml` mas o código lê `config.ini`
- `config.toml` não está sendo usado

### 4. **Dependências Python Não Documentadas**
- Não há arquivo `requirements.txt`
- Pacotes necessários:
  - sqlalchemy
  - psycopg2
  - pandas
  - toml
  - slack-sdk
  - google-auth-oauthlib
  - google-auth-httplib2
  - google-api-python-client

### 5. **Falta de Tratamento de Erros Robusta**
- Try/Except genérica em app.py
- Falhas silenciosas podem ocorrer
- Sem retenção de dados em caso de erro

### 6. **Sincronismo com Google Sheets**
- Se planilha não estiver atualizada, dados desatualizados são propagados
- Sem validação de integridade dos dados

### 7. **Validação de ID Slack**
- Apenas verifica se começa com 'U'
- Poderia validar melhor o formato

### 8. **Performance**
- Loop iterativo de notificações pode ser lento com muitos usuários
- Sem paralelização ou batch processing

---

## 🚀 Melhorias Sugeridas

1. **Usar variáveis de ambiente** para credenciais
2. **Criar arquivo requirements.txt** com todas as dependências
3. **Mover configurações** para arquivo centralizado
4. **Implementar logging robusto** com níveis (DEBUG, INFO, WARNING, ERROR)
5. **Adicionar retry logic** para chamadas à API
6. **Validar integridade dos dados** antes de inserir
7. **Paralelizar notificações** via threads/asyncio
8. **Criar testes unitários** para validar fluxos
9. **Documentar regra de negócio** de quando executar
10. **Usar context managers** para conexões de banco de dados

---

## 📌 Dependências

### Bibliotecas Python
```
sqlalchemy>=1.4.0
psycopg2>=2.9.0
pandas>=1.3.0
toml>=0.10.0
slack-sdk>=3.0.0
google-auth-oauthlib>=0.4.0
google-auth-httplib2>=0.1.0
google-api-python-client>=2.0.0
```

### Recursos Externos
- **Google Sheets API:** Para leitura de dados
- **PostgreSQL Database:** Para armazenamento
- **Slack API:** Para envio de notificações
- **Google OAuth 2.0:** Para autenticação

---

## 📌 Resumo Executivo

O **Projeto Control** é uma automação de escalas operacionais que:

✅ **O que faz:**
- Sincroniza dados de planilha Google com PostgreSQL
- Gerencia ciclo de vida dos analistas (Inserir, Atualizar, Inativar)
- Notifica analistas sobre suas escalas via Slack
- Mantém auditoria de execuções em arquivo de log

✅ **Quando executa:**
- Diariamente (horário deve ser definido em Task Scheduler)
- Comportamento especial no 1º dia do mês (notifica todos)

✅ **Tecnologias:**
- Python 3.x
- PostgreSQL
- Google Sheets API
- Slack API
- Pandas para manipulação de dados

✅ **Status de Operação:**
- Última execução bem-sucedida: 3 de fevereiro de 2025
- Mais de 50 analistas sendo notificados regularmente

---

**Documentação Criada em:** 6 de fevereiro de 2026
