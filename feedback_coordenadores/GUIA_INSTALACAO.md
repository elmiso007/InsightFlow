# 🚀 Guia de Instalação - Sistema de Análise NPS

## 📋 Pré-requisitos

- Python 3.8 ou superior
- PostgreSQL 12 ou superior
- Acesso ao banco de dados
- API Key do Google Gemini

---

## 🔧 Instalação Passo a Passo

### 1. Clone ou Baixe o Projeto

```bash
cd feedback_coordenadores
```

### 2. Crie um Ambiente Virtual (Recomendado)

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

**Pacotes principais instalados:**
- pandas, numpy - Manipulação de dados
- sqlalchemy, psycopg2, pyodbc - Banco de dados
- google-generativeai - API Gemini
- python-dotenv - Variáveis de ambiente
- beautifulsoup4 - Parse HTML
- holidays - Calendário

---

## ⚙️ Configuração

### 4. Configure o Arquivo .env

**a) Renomeie o arquivo de exemplo:**

```bash
# Opção 1: Renomear o env.production
mv env.production .env

# Opção 2: Copiar do exemplo
cp env.example .env
```

**b) Edite o arquivo .env:**

```bash
# Windows
notepad .env

# Linux/Mac
nano .env
```

**c) Configure as variáveis essenciais:**

```env
# ⚠️  IMPORTANTE: Configure estas variáveis obrigatórias

# Banco de Dados
DB_HOST=seu_host             # configure seu ambiente
DB_PASSWORD=sua_senha_real    # configure sua senha local

# API Gemini (CRÍTICO!)
GEMINI_API_KEY=sua_nova_chave_aqui  # ❌ GERE NOVA CHAVE!
```

**⚠️ ATENÇÃO DE SEGURANÇA:**

Nunca compartilhe ou versione suas API Keys!

**Como obter sua API Key do Google Gemini:**
1. Acesse: https://makersuite.google.com/app/apikey
2. Faça login com sua conta Google
3. Crie uma nova API Key
4. Cole a chave no arquivo `.env`
5. Adicione `.env` ao `.gitignore` (já configurado)

### 5. Valide a Configuração

```bash
python config.py
```

**Saída esperada:**
```
✅ Todas as configurações essenciais estão presentes!

⚙️  CONFIGURAÇÕES DO SISTEMA
======================================================================
📊 Banco de Dados:
  Host: SEU_HOST:5432
  Database: SEU_BANCO
  ...
```

Se houver erros, corrija as variáveis no `.env`.

---

## 🗄️ Preparação do Banco de Dados

### 6. Crie as Tabelas Necessárias

**Execute os scripts SQL na ordem:**

```bash
# 1. Criar tabelas principais
psql -U automatizacoes -d report_requesttracker -f create_tables_nps.sql

# 2. Adicionar colunas de análise estruturada
psql -U automatizacoes -d report_requesttracker -f create_analysis_columns.sql
```

**Ou execute diretamente no PostgreSQL:**

```sql
-- Conecte ao banco e execute os scripts
\i create_tables_nps.sql
\i create_analysis_columns.sql
```

### 7. Verifique se as Tabelas Foram Criadas

```sql
-- Liste as tabelas criadas
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'kinghost_octadesk'
  AND table_name LIKE '%nps%';
```

**Tabelas esperadas:**
- `rawdata_analise_nps_analistas` ✅
- `analise_nps_analistas` ✅

---

## ✅ Teste a Instalação

### 8. Teste a Conexão com o Banco

```bash
python teste_conexao.py
```

**Saída esperada:**
```
✅ Conexão com banco de dados OK!
✅ Schema kinghost_octadesk encontrado
✅ Tabelas necessárias existem
```

### 9. Execute um Teste Rápido (Dry Run)

Crie um arquivo `teste_rapido.py`:

```python
from config import config
from conecta_banco import get_psycopg2_connection

# Valida configurações
if config.validate():
    print("✅ Configurações OK!")
    
# Testa conexão
try:
    conn = get_psycopg2_connection()
    print("✅ Conexão com banco OK!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM kinghost_octadesk.vw_report_diario")
    count = cursor.fetchone()[0]
    print(f"✅ Registros na vw_report_diario: {count}")
    
    conn.close()
except Exception as e:
    print(f"❌ Erro: {e}")
```

Execute:
```bash
python teste_rapido.py
```

---

## 🎯 Primeira Execução

### 10. Execute o Sistema

```bash
python verifica_nps.py
```

**O que acontece:**
1. ✅ Carrega configurações do `.env`
2. ✅ Conecta ao banco de dados
3. ✅ Busca dados de NPS do mês anterior
4. ✅ Calcula NPS por analista
5. ✅ Identifica analistas críticos (NPS < 70)
6. ✅ Busca conversas completas
7. ✅ Envia para análise de IA (Gemini)
8. ✅ Salva resultados no banco
9. ✅ Gera relatórios em MD e TXT
10. ✅ Envia notificações

**Arquivos gerados:**
- `logs/nps_verificacao.log` - Log completo
- `atendimentos_nps_baixo.txt` - Conversas analisadas
- `resposta_nps_gemini.md` - Análise da IA

---

## 📊 Verificando Resultados

### 11. Consulte os Dados Salvos

```sql
-- Últimas análises realizadas
SELECT 
    id,
    request_datetime,
    analistas_criticos,
    total_protocolos,
    setor
FROM kinghost_octadesk.analise_nps_analistas
ORDER BY request_datetime DESC
LIMIT 5;

-- Ver análise completa
SELECT 
    analistas_criticos,
    resumo_geral,
    casos_criticos
FROM kinghost_octadesk.analise_nps_analistas
WHERE DATE(request_datetime) = CURRENT_DATE;
```

---

## 🔄 Automação (Opcional)

### 12. Agendar Execução Automática

**Windows Task Scheduler:**

```powershell
# Criar tarefa agendada
schtasks /create /tn "NPS_Mensal" /tr "C:\caminho\venv\Scripts\python.exe C:\caminho\verifica_nps.py" /sc monthly /d 1 /st 08:00
```

**Linux Cron:**

```bash
# Editar crontab
crontab -e

# Adicionar linha (executa dia 1 de cada mês às 8h)
0 8 1 * * cd /caminho/feedback_coordenadores && /caminho/venv/bin/python verifica_nps.py
```

---

## 🛠️ Solução de Problemas

### Erro: "GEMINI_API_KEY não configurada"
```bash
# Verifique se o .env existe e está no diretório correto
ls -la .env

# Verifique se a variável está definida
grep GEMINI_API_KEY .env
```

### Erro: Conexão com banco de dados
```bash
# Teste a conexão manualmente
psql -h 10.30.138.28 -U automatizacoes -d report_requesttracker

# Verifique as credenciais no .env
cat .env | grep DB_
```

### Erro: "ModuleNotFoundError"
```bash
# Reinstale as dependências
pip install -r requirements.txt --upgrade
```

### Logs não são gerados
```bash
# Crie o diretório manualmente
mkdir logs

# Verifique permissões
chmod 755 logs
```

---

## 📝 Configurações Avançadas

### Personalizar Meta de NPS

Edite `.env`:
```env
NPS_META=75.0              # Altere para sua meta
NPS_MIN_AVALIACOES=5       # Mínimo de avaliações
```

### Ajustar Tamanho de Análise

```env
ANALISE_MAX_DATASET_SIZE=15000  # Aumentar para mais contexto
ANALISE_MAX_TENTATIVAS=10       # Mais tentativas
```

### Mudar Nível de Logging

```env
LOG_FILE_LEVEL=INFO        # Menos detalhes no arquivo
LOG_CONSOLE_LEVEL=WARNING  # Apenas alertas no console
```

---

## ✅ Checklist Final

Antes de usar em produção:

- [ ] Ambiente virtual criado e ativado
- [ ] Dependências instaladas (`requirements.txt`)
- [ ] Arquivo `.env` configurado corretamente
- [ ] **API Key Gemini gerada e configurada**
- [ ] Conexão com banco testada
- [ ] Tabelas criadas no banco
- [ ] Primeira execução bem-sucedida
- [ ] Logs sendo gerados corretamente
- [ ] `.env` adicionado ao `.gitignore`
- [ ] Backup das configurações feito

---

## 📞 Suporte

Em caso de problemas:

1. Verifique os logs: `logs/nps_verificacao.log`
2. Execute com mais detalhes: `LOG_CONSOLE_LEVEL=DEBUG python verifica_nps.py`
3. Valide configurações: `python config.py`

---

**Última Atualização:** Outubro 2025  
**Versão:** 2.0 (com suporte a .env)

