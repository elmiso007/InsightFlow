# 📊 Report Diário Locaweb

Sistema automatizado para geração e envio de relatórios diários de atendimento via Slack, com métricas de desempenho para os setores de Suporte e Cobrança da Locaweb.

> **Status:** ✅ Produção | **Versão:** 2.0.1 | **Última Atualização:** 04 de Novembro de 2024

---

## 📑 **Índice**

- [⚡ Quick Start](#-quick-start)
- [🎯 Funcionalidades](#-funcionalidades)
- [📋 Pré-requisitos](#-pré-requisitos)
- [🚀 Instalação](#-instalação)
- [🔐 Segurança](#-segurança)
- [▶️ Como Usar](#️-como-usar)
  - [🧪 Alternando entre Teste e Produção](#-alternando-entre-teste-e-produção)
  - [🚀 Execução Manual](#-execução-manual)
  - [⏰ Agendar Execução](#-agendar-execução-automática)
- [📊 Estrutura dos Relatórios](#-estrutura-dos-relatórios)
- [🎨 Interpretação de Cores](#-interpretação-de-cores)
- [📂 Estrutura de Arquivos](#-estrutura-de-arquivos)
- [📝 Logs e Monitoramento](#-logs-e-monitoramento)
- [🛠️ Solução de Problemas](#️-solução-de-problemas)
- [📖 Exemplos Práticos](#-exemplos-práticos)
- [🎓 Boas Práticas](#-boas-práticas)
- [🔄 Changelog](#-changelog)
- [📞 Suporte](#-suporte)

---

## ⚡ **Quick Start**

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar credenciais
copy env.example .env
# Edite o .env com suas credenciais

# 3. Executar em modo TESTE (padrão)
python app.py

# 4. Verificar log
notepad report_diario.log
```

**✅ Pronto!** Se funcionou no teste, veja [como alternar para produção](#-alternando-entre-teste-e-produção).

---

## 🎯 **Funcionalidades**

- ✅ Geração automática de relatórios diários
- ✅ Comparação com período padrão (Ago-Out 2025) - cálculo dinâmico
- ✅ Comparação com semana anterior (D-7)
- ✅ Métricas por canal (WhatsApp, Chat, Telefone)
- ✅ Análise de TMA (Tempo Médio de Atendimento) e TME (Tempo Médio de Espera)
- ✅ Verificação automática de dias úteis e feriados brasileiros
- ✅ Envio via Slack com visualizações profissionais
- ✅ Sistema de logging completo e estruturado
- ✅ Alternância fácil entre ambientes (Teste/Produção)
- ✅ Suporte a múltiplos destinatários
- ✅ Cálculo dinâmico de médias e dias úteis

---

## 📋 **Pré-requisitos**

- Python 3.8 ou superior
- PostgreSQL com acesso à view `lw_octadesk.vw_report_diario_filtrada`
- Slack Workspace com bot configurado
- Windows (o script usa locale pt_BR)

---

## 🚀 **Instalação**

### 1. Clone o repositório ou baixe os arquivos

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

Copie o arquivo `env.example` para `.env`:

```bash
copy env.example .env
```

**⚠️ IMPORTANTE**: Edite o arquivo `.env` e configure suas credenciais:

```ini
# Banco de Dados
DB_SERVER=seu_servidor
DB_DATABASE=seu_banco
DB_USER=seu_usuario
DB_PASSWORD=sua_senha

# Slack
SLACK_BOT_TOKEN=xoxb-seu-token-aqui
SLACK_CHANNEL_ID=C08AZTJB8JV

# Período Padrão
PADRAO_DATA_INICIO=2025-08-01
PADRAO_DATA_FIM=2025-10-31
```

---

## 🔐 **Segurança**

### ⚠️ NUNCA COMMITE:
- Arquivo `.env`
- Arquivo `config.ini`
- Tokens do Slack
- Senhas do banco de dados

O arquivo `.gitignore` já está configurado para proteger esses arquivos.

### 🔑 Como obter o Token do Slack:

1. Acesse https://api.slack.com/apps
2. Selecione seu app ou crie um novo
3. Vá em "OAuth & Permissions"
4. Copie o "Bot User OAuth Token" (começa com `xoxb-`)
5. Cole no arquivo `.env`

### 📝 Permissões necessárias no Slack:
- `chat:write`
- `files:write`
- `channels:read`
- `groups:read`
- `im:write`

---

## ▶️ **Como Usar**

### 🧪 Alternando entre Teste e Produção

**IMPORTANTE**: Por padrão, o sistema está configurado para **TESTE**.

Para alternar, edite o arquivo `app.py` nas **linhas 538-542**:

#### Para TESTE (padrão):
```python
# 🧪 AMBIENTE DE TESTE (Canal: C07NSPQ69TL)
destinatarios = [SLACK_CHANNEL_TESTE]  # ✅ ATIVO

# 🚀 AMBIENTE DE PRODUÇÃO (Canal: C08AZTJB8JV)
# destinatarios = [SLACK_CHANNEL]  # ❌ COMENTADO
```

#### Para PRODUÇÃO:
```python
# 🧪 AMBIENTE DE TESTE (Canal: C07NSPQ69TL)
# destinatarios = [SLACK_CHANNEL_TESTE]  # ❌ COMENTADO

# 🚀 AMBIENTE DE PRODUÇÃO (Canal: C08AZTJB8JV)
destinatarios = [SLACK_CHANNEL]  # ✅ ATIVO
```

#### Para Múltiplos Destinatários:
```python
# 🔀 Enviar para ambos os canais
destinatarios = [SLACK_CHANNEL_TESTE, SLACK_CHANNEL]

# 📨 Ou incluir usuários específicos
# destinatarios = ['U070386L98T', SLACK_CHANNEL_TESTE]
```

---

### 🚀 Execução Manual:

```bash
python app.py
```

### 🪟 Execução via Batch (Windows):

```batch
ExecutaApp.bat
```

### ⏰ Agendar Execução Automática:

**Opção 1 - Via PowerShell (Recomendado):**
```powershell
# Executar como Administrador
$action = New-ScheduledTaskAction -Execute "python" -Argument "app.py" -WorkingDirectory "C:\Users\emerson.ramos\Desktop\projetos\Locaweb\Report Diario"
$trigger = New-ScheduledTaskTrigger -Daily -At "10:00AM"
Register-ScheduledTask -TaskName "Report Diário Locaweb" -Action $action -Trigger $trigger -Description "Envio automático do relatório diário"
```

**Opção 2 - Via Interface Gráfica:**
1. Abra o "Agendador de Tarefas" (Task Scheduler)
2. Criar Tarefa Básica
3. **Nome:** Report Diário Locaweb
4. **Gatilho:** Diário às 10h, 14h ou 18h (escolha um ou mais)
5. **Ação:** Iniciar programa
6. **Programa:** `C:\Users\emerson.ramos\Desktop\projetos\Locaweb\Report Diario\ExecutaApp.bat`

---

## 📊 **Estrutura dos Relatórios**

### Indicadores Calculados:

| Métrica | Descrição |
|---------|-----------|
| **TMA** | Tempo Médio de Atendimento |
| **TME** | Tempo Médio de Espera |
| **Recebidos** | Total de atendimentos recebidos |
| **Atendidos** | Atendimentos efetivados (sem bot) |
| **Abandonos** | Atendimentos não concluídos |
| **% Abandono** | Percentual de abandonos |

### Períodos de Análise:

- **00:00 às 10:00** - Primeira medição do dia
- **00:00 às 14:00** - Segunda medição (após 14h)
- **00:00 às 18:00** - Medição final (após 18h)

### Comparações:

1. **Padrão** - Média de dias úteis entre Ago-Out 2025
2. **D-7** - Mesmo dia da semana anterior
3. **Hoje** - Dados do dia atual

---

## 🎨 **Interpretação de Cores**

- 🟢 **Verde**: Abaixo do padrão (BOM - menos atendimentos que o esperado)
- 🔴 **Vermelho**: Acima do padrão (RUIM - mais atendimentos que o esperado)
- ⚪ **Branco**: Neutro (sem variação)

---

## 📂 **Estrutura de Arquivos**

```
Report Diario/
├── app.py                    # Script principal
├── requirements.txt          # Dependências Python
├── .env                      # Variáveis de ambiente (NÃO COMMITAR)
├── env.example               # Template de configuração
├── .gitignore                # Arquivos ignorados pelo Git
├── ExecutaApp.bat            # Script de execução Windows
├── README.md                 # Este arquivo
├── config.ini                # Configuração legada (DEPRECATED)
├── bkp.py                    # Backup do código anterior
└── report_diario.log         # Log de execução (gerado automaticamente)
```

---

## 📝 **Logs e Monitoramento**

### 📋 Arquivo de Log

Os logs são salvos automaticamente em `report_diario.log` com encoding UTF-8.

### 🔍 Níveis de Log:

| Nível | Descrição | Quando Usar |
|-------|-----------|-------------|
| **INFO** | Informações gerais de execução | Produção (padrão) |
| **WARNING** | Avisos (ex: modo teste ativo) | Produção |
| **ERROR** | Erros que impediram a execução | Sempre |
| **DEBUG** | Informações detalhadas (valores calculados) | Desenvolvimento |

### ⚙️ Configurar Nível de Log:

No arquivo `.env`:

```ini
LOG_LEVEL=INFO  # ou DEBUG, WARNING, ERROR
LOG_FILE=report_diario.log
```

### 🔎 Visualizar Logs:

**Ver últimas 50 linhas:**
```powershell
Get-Content report_diario.log -Tail 50
```

**Monitorar em tempo real:**
```powershell
Get-Content report_diario.log -Wait -Tail 10
```

**Abrir no Notepad:**
```powershell
notepad report_diario.log
```

### 📊 Indicadores no Log:

- ⚠️ **MODO TESTE ATIVO** - Enviando para canal de teste
- ✅ **MODO PRODUÇÃO ATIVO** - Enviando para canal oficial
- 🔀 **MODO MÚLTIPLOS DESTINATÁRIOS** - Enviando para vários canais
- 📤 **Destinatários configurados** - Lista de IDs de canais/usuários

---

## 🛠️ **Solução de Problemas**

### ❌ Erro: "Token do Slack não configurado"
```
ValueError: Configure a variável SLACK_BOT_TOKEN no arquivo .env
```
**Solução**: 
1. Certifique-se que o arquivo `.env` existe
2. Configure `SLACK_BOT_TOKEN=xoxb-seu-token-aqui`
3. Reinicie a aplicação

---

### ❌ Erro: "Credenciais do banco de dados não configuradas"
```
ValueError: Configure as variáveis DB_SERVER, DB_DATABASE, DB_USER e DB_PASSWORD no arquivo .env
```
**Solução**: 
1. Verifique se todas as 4 variáveis estão no `.env`
2. Certifique-se de não ter espaços extras
3. Formato correto: `DB_USER=automatizacoes` (sem aspas)

---

### ⚠️ Warning: "Não foi possível configurar locale"
```
WARNING - Não foi possível configurar locale em português, usando padrão do sistema
```
**Solução**: Isso é apenas um aviso. O script continuará funcionando normalmente. Os nomes dos dias da semana podem aparecer em inglês.

---

### ❌ Erro: "password authentication failed"
```
FATAL: password authentication failed for user "automatizacoes"
```
**Solução**: 
1. Verifique se a senha no `.env` está correta
2. Confirme o nome do usuário (deve ser `automatizacoes`)
3. Teste conectando com outro cliente (pgAdmin, DBeaver)
4. Verifique se o IP está liberado no firewall

---

### ❌ Erro: "SSL error: dh key too small"
**Solução**: Este erro está relacionado à configuração SSL do PostgreSQL. A aplicação já tenta contornar isso, mas se persistir:
1. Atualize o `psycopg2`: `pip install --upgrade psycopg2-binary`
2. Contate o administrador do banco

---

### 📨 Imagem não é enviada no Slack
**Solução**: 
1. Verifique se o bot tem permissão `files:write`
2. Confirme que a imagem foi gerada: procure `report_diario_Locaweb.png`
3. Verifique os logs: `Get-Content report_diario.log -Tail 20`
4. Teste manualmente: `python app.py` e observe a saída

---

### 🔄 Relatório não está sendo enviado
**Possíveis causas:**
1. **Ambiente errado**: Verifique se está em TESTE ou PRODUÇÃO
2. **Canal incorreto**: Confirme o ID no `.env`
3. **Token expirado**: Gere um novo token no Slack
4. **Bot não está no canal**: Adicione o bot ao canal do Slack

**Debug:**
```powershell
# Verificar últimos logs
Get-Content report_diario.log -Tail 30

# Ver ambiente ativo (deve aparecer TESTE ou PRODUÇÃO)
python app.py | Select-String "MODO"
```

---

## 🔄 **Migração do Sistema Antigo**

Se você está migrando do sistema anterior (`config.ini`):

1. ✅ Copie as credenciais do `config.ini` para o `.env`
2. ✅ Revogue e regenere o token do Slack (o anterior está comprometido)
3. ✅ Delete o arquivo `config.ini` após migração
4. ✅ Adicione `config.ini` ao `.gitignore`

---

## 📈 **Melhorias Implementadas**

### ✨ Segurança:
- ✅ Credenciais em variáveis de ambiente
- ✅ `.gitignore` configurado
- ✅ Tokens não expostos no código

### 🚀 Performance:
- ✅ Cálculo dinâmico de dias úteis
- ✅ Uso eficiente de memória (plt.close())
- ✅ Queries otimizadas

### 📊 Qualidade de Código:
- ✅ Constantes para valores mágicos
- ✅ Funções documentadas (docstrings)
- ✅ Logging estruturado
- ✅ Tratamento de erros (try/except)
- ✅ Code style consistente

### 🔧 Manutenibilidade:
- ✅ Paths relativos (portável)
- ✅ Configuração centralizada
- ✅ Código modular
- ✅ Documentação completa

---

## 📞 **Suporte**

Para dúvidas sobre os relatórios:
- 📧 Email: trafego@locaweb.com.br
- 💬 Slack: Mencione um analista da equipe

---

## 👨‍💻 **Autor**

**Emerson Ramos**  
Desenvolvedor - Locaweb

---

## 📄 **Licença**

Uso interno - Locaweb © 2024-2025

---

## 📖 **Exemplos Práticos**

### Exemplo 1: Primeira Execução (Teste)
```bash
# 1. Verificar que está em modo TESTE
python app.py

# 2. Observar no log:
# ⚠️ MODO TESTE ATIVO - Enviando para canal de TESTE (C07NSPQ69TL)

# 3. Verificar no Slack se chegou no canal de teste
```

### Exemplo 2: Testar e depois ir para Produção
```bash
# 1. Executar em teste
python app.py

# 2. Validar no canal de teste

# 3. Editar app.py (linhas 538-542):
#    Comentar: destinatarios = [SLACK_CHANNEL_TESTE]
#    Descomentar: destinatarios = [SLACK_CHANNEL]

# 4. Executar em produção
python app.py

# 5. Confirmar no log:
# ✅ MODO PRODUÇÃO ATIVO - Enviando para canal OFICIAL (C08AZTJB8JV)
```

### Exemplo 3: Enviar para Múltiplos Canais
```bash
# 1. Editar app.py linha 545:
# destinatarios = [SLACK_CHANNEL_TESTE, SLACK_CHANNEL]

# 2. Executar
python app.py

# 3. Verificar no log:
# 🔀 MODO MÚLTIPLOS DESTINATÁRIOS - Enviando para 2 canais
```

### Exemplo 4: Monitorar Execução Agendada
```powershell
# Verificar última execução
Get-Content report_diario.log -Tail 50

# Filtrar apenas erros
Get-Content report_diario.log | Select-String "ERROR"

# Ver status de hoje
Get-Content report_diario.log | Select-String (Get-Date -Format "yyyy-MM-dd")
```

---

## 🔄 **Changelog**

### v2.0.1 (2024-11-04) - Melhorias e Correções
- ✅ Sistema de alternância Teste/Produção aprimorado
- ✅ Logs mais informativos com emojis
- ✅ Suporte a múltiplos destinatários
- ✅ Documentação atualizada e expandida
- ✅ Correção de encoding UTF-8
- ✅ Validação de credenciais melhorada

### v2.0 (2024-11-04) - Refatoração Completa
- ✅ Migração para variáveis de ambiente (.env)
- ✅ Sistema de logging estruturado implementado
- ✅ Cálculo dinâmico de dias úteis
- ✅ Melhorias críticas de segurança
- ✅ Tratamento de erros robusto com try/except
- ✅ Constantes para valores mágicos
- ✅ Funções documentadas com docstrings
- ✅ Paths relativos (código portável)
- ✅ `.gitignore` configurado
- ✅ Documentação completa (README + MIGRATION_GUIDE)

### v1.0 (2024-2025) - Versão Inicial
- ✅ Sistema de relatórios funcionando
- ✅ Integração com Slack
- ✅ Geração de gráficos com matplotlib
- ✅ Comparações com período padrão e D-7
- ✅ Suporte a múltiplos setores

---

## 🎓 **Boas Práticas**

### ✅ DO:
- ✔️ Sempre testar em ambiente de TESTE antes de produção
- ✔️ Verificar logs após cada execução
- ✔️ Manter o `.env` sempre atualizado
- ✔️ Renovar tokens periodicamente (a cada 6 meses)
- ✔️ Fazer backup do `.env` em local seguro
- ✔️ Documentar mudanças no código

### ❌ DON'T:
- ✖️ Nunca commitar o arquivo `.env`
- ✖️ Nunca compartilhar tokens do Slack
- ✖️ Nunca executar direto em produção sem testar
- ✖️ Nunca desabilitar logs (sempre mantenha em INFO)
- ✖️ Nunca usar senhas fracas ou padrão
- ✖️ Nunca ignorar mensagens de ERROR nos logs

---

**🎉 Pronto! Seu sistema está configurado, protegido e documentado!**

