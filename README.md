# 📊 Sistema de Análise NPS de Analistas

Sistema inteligente de monitoramento e análise de NPS (Net Promoter Score) para analistas de atendimento, com análise automática via Google Gemini AI. O projeto foi estruturado para apoiar a rotina de suporte e gestão de qualidade, convertendo avaliações, comentários e histórico de atendimento em relatórios acionáveis para liderança e analistas.

## 🎯 Objetivo do projeto

Este fluxo foi desenhado para:
- calcular o NPS por analista e por dimensão (Velocidade, Solução e Relacionamento);
- detectar analistas com desempenho abaixo da meta configurada;
- buscar o histórico de atendimentos e conversas relacionadas;
- anonimizar dados sensíveis antes de enviar conteúdo para IA;
- gerar relatórios estruturados que ajudam a priorizar intervenção, coaching ou revisão de processo.

## 🧭 Visão rápida da documentação

A documentação foi organizada em três camadas para facilitar manutenção e uso:
- Manual operacional: como instalar, configurar e executar a aplicação;
- Regras de negócio: critérios, limiares, políticas e decisões do fluxo;
- Arquitetura: módulos, fluxo de dados, dependências e pontos de extensão.

> Recomendação de leitura: comece pelo README, depois siga para os documentos em docs/ conforme a necessidade.

## 📚 Documentação detalhada

Identificar analistas com NPS baixo (< 70), analisar conversas de atendimento e gerar insights acionáveis usando IA para melhorar a qualidade do atendimento.

---

## ✨ Principais Funcionalidades

- ✅ **Cálculo Automático de NPS** por analista (Velocidade, Solução, Relacionamento)
- ✅ **Análise de IA (Google Gemini)** de conversas e comentários
- ✅ **Anonimização de Dados Sensíveis** (CPF, email, senhas, etc.)
- ✅ **Análise Individual por Analista** com insights específicos
- ✅ **Processamento Paralelo** — até N analistas processados simultaneamente (configurável)
- ✅ **Idempotência** — re-execução segura: analistas já analisados são pulados automaticamente
- ✅ **Deduplicação de Conversas** — protocolos duplicados removidos antes da análise
- ✅ **Relatórios Estruturados** em Markdown e TXT
- ✅ **Logging Profissional** com rotação automática
- ✅ **Configuração via .env** (seguro e flexível)
- ✅ **Push seguro** com `.env` e saídas ignoradas no Git
- ✅ **Salvamento em PostgreSQL** com dados estruturados
- ✅ **Análise de Detratores WOZ** — comparativo mensal de comentários sobre atendimento automatizado
- ✅ **Gravação de Comentários WOZ** — cada comentário individual persistido em `lw_octadesk.woz_comentarios`

---

## 🏗️ Arquitetura

```
┌─────────────────────────┐    ┌──────────────────────────────┐
│   verifica_nps.py       │    │  analise_woz_detratores.py   │
│   Orquestrador NPS      │    │  Comparativo mensal WOZ      │
│   Calcula NPS, críticos │    │  --ano1 --mes1 --ano2 --mes2 │
└───────────┬─────────────┘    └──────┬───────────────────────┘
            │                         │
    ┌───────┴────────┐                ├──────────────────────┐
    │                │                │                      │
    ▼                ▼                ▼                      ▼
┌────────────┐  ┌────────────┐  ┌─────────────┐   ┌────────────────┐
│ get_       │  │ analise_   │  │ conecta_    │   │  woz_detrato-  │
│ atendimen  │  │ ia.py      │  │ banco.py    │   │  res/          │
│ tos_nps.py │  │ Gemini AI  │  └──────┬──────┘   │  *.html + JSON │
└─────┬──────┘  └─────┬──────┘         │           └────────────────┘
      │               │                │
      └───────┬───────┘                │
              ▼                        │
      ┌───────────────┐                │
      │ conecta_      │                │
      │ banco.py      ├────────────────┘
      └───────┬───────┘
              ▼
      ┌─────────────────────────────────┐
      │  PostgreSQL — lw_octadesk       │
      │  • rawdata_analise_nps_analistas│
      │  • analise_nps_analistas        │
      │    (NPS analistas + WOZ resumo) │
      │  • woz_comentarios              │
      │    (comentários individuais)    │
      └─────────────────────────────────┘
```

---

## 📋 Pré-requisitos

- **Python 3.8+**
- **PostgreSQL 12+**
- **API Key do Google Gemini**
- Acesso ao banco de dados com as views:
  - `vw_report_diario`
  - `vw_nps`
  - `mensagens`

---

## 🚀 Instalação Rápida

### 1. Clone o Repositório

```bash
git clone <seu-repo>
cd "Feedback Woz-Analista"
```

### 2. Crie Ambiente Virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate   # Windows
```

### 3. Instale Dependências

```bash
pip install -r requirements.txt
```

### 4. Configure o .env

> Importante: o arquivo real `.env` nunca deve ser enviado ao GitHub. Use o modelo `.env.example` como referência.

```bash
# Copie o exemplo para o arquivo local real
copy .env.example .env

# Edite com suas credenciais
notepad .env
```

**⚠️ IMPORTANTE:** Configure estas variáveis:

```env
# Banco de Dados
DB_HOST=seu_host
DB_PASSWORD=sua_senha

# API Gemini (CRÍTICO - GERE NOVA CHAVE!)
GEMINI_API_KEY=sua_nova_chave_aqui
```

### 5. Crie as Tabelas

> Os scripts já estão configurados para o schema `lw_octadesk`.

```bash
psql -U seu_usuario -d seu_banco -f create_tables_nps.sql
psql -U seu_usuario -d seu_banco -f create_analysis_columns.sql
```

### 6. Teste a Instalação

```bash
python teste_conexao.py
```

### 7. Execute!

```bash
python verifica_nps.py
```

---

## ⚙️ Configuração Detalhada

### Arquivo .env

Todas as configurações são feitas via `.env`:

```env
# Banco de Dados
DB_HOST=seu_host
DB_PORT=5432
DB_NAME=seu_banco
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
DB_SCHEMA=seu_schema

# API Gemini
GEMINI_API_KEY=sua_chave
GEMINI_MODEL=gemini-flash-latest

# Configurações NPS
NPS_META=70.0                    # Meta mínima de NPS
NPS_MIN_AVALIACOES=3            # Mínimo de avaliações
NPS_PERIODO_TIPO=mes_anterior   # ou ultimos_30_dias

# Análise IA
ANALISE_MAX_DATASET_SIZE=12000              # Tamanho máximo do contexto enviado ao Gemini
ANALISE_MAX_TENTATIVAS=5                    # Tentativas em caso de erro
ANALISE_DELAY_TENTATIVA=5                   # Delay entre tentativas (seg)
ANALISE_RETENTION_DAYS=90                   # Dias de retenção do rawdata
ANALISE_MAX_ATENDIMENTOS_POR_ANALISTA=30    # Limite de conversas por analista (controla tamanho do prompt)

# Processamento paralelo
PARALELO_MAX_WORKERS=4          # Analistas processados simultaneamente (free tier: 1, paid: até 4+)

# Logging
LOG_FILE_LEVEL=DEBUG            # DEBUG, INFO, WARNING, ERROR
LOG_CONSOLE_LEVEL=INFO
LOG_MAX_SIZE_MB=10
LOG_BACKUP_COUNT=5
```

### Validar Configurações

```bash
python config.py
```

Mostra todas as configurações e valida se estão corretas.

---

## 📊 Como Funciona

### Fluxo de Execução

```
FLUXO A — Análise NPS por Analista (verifica_nps.py)
─────────────────────────────────────────────────────
1. COLETA DE DADOS
   └─> Busca avaliações NPS do período (mês anterior)
   └─> Calcula NPS por analista (fórmula padrão)

2. IDENTIFICAÇÃO DE CRÍTICOS
   └─> Analistas com NPS < 70 (configurável)
   └─> Mínimo de 3 avaliações (configurável)

3. BUSCA DE CONVERSAS (por analista, em paralelo)
   └─> Query individual por analista com LIMIT configurável
   └─> Deduplicação de protocolos duplicados
   └─> Anonimiza dados sensíveis (CPF, email, etc.)

4. ANÁLISE DE IA (ThreadPoolExecutor — N workers simultâneos)
   └─> Verifica idempotência: pula analistas já analisados no período
   └─> Envia para Google Gemini
   └─> Extrai 6 seções estruturadas:
       • Resumo Geral / Problemas por Dimensão NPS
       • Padrões Comportamentais / Comentários vs Conversas
       • Recomendações de Melhoria / Casos Críticos

5. SALVAMENTO
   └─> Banco: rawdata_analise_nps_analistas
   └─> HTML: analistas_criticos/{analista}.html
   └─> Logs: logs/nps_verificacao.log

6. LIMPEZA AUTOMÁTICA
   └─> Remove registros do rawdata mais antigos que ANALISE_RETENTION_DAYS

7. PROCESSAMENTO FINAL
   └─> SQL: insereDadosAnaliseNPS.sql
   └─> Copia para: analise_nps_analistas (analise_tipo='monitoramento_nps_analistas')

8. NOTIFICAÇÃO
   └─> Alertas ou boas notícias


FLUXO B — Análise de Detratores WOZ (analise_woz_detratores.py)
────────────────────────────────────────────────────────────────
1. COLETA
   └─> Busca comentários NPS com termos WOZ/robô/bot via SQL ILIKE
   └─> Filtra por mês (--ano1 --mes1 --ano2 --mes2 ou auto: últimos 2 meses)

2. CLASSIFICAÇÃO
   └─> Calcula score médio (Velocidade + Solução + Relacionamento)
   └─> Classifica: Promotor (≥9) / Neutro (7-8) / Detrator (≤6)

3. COMPARATIVO
   └─> Calcula delta de volume, % detratores e tendência entre os dois meses

4. SAÍDAS
   └─> Banco: woz_comentarios (cada comentário individual — idempotente por protocolo+período)
   └─> HTML: woz_detratores/woz_mensal_{data_inicio_1}_vs_{data_inicio_2}.html
   └─> JSON: woz_detratores/historico.json (acumulativo)
   └─> Banco: analise_nps_analistas (analise_tipo='woz_detratores_mensal')
       — idempotente por request_id=woz_{data_inicio_1}_vs_{data_inicio_2}
```

### Cálculo de NPS

Fórmula padrão do NPS:

```
NPS = ((Promotores - Detratores) / Total de Respostas) × 100

Onde:
• Promotores: notas 9-10
• Neutros: notas 7-8
• Detratores: notas 0-6
```

---

## 📁 Estrutura de Arquivos

```
Feedback Woz-Analista/
├── .env                          # ⚠️  Configurações (NÃO versionar!)
├── env.example                   # Template de configuração
├── config.py                     # Carrega configurações do .env (DB_SCHEMA=lw_octadesk)
├── conecta_banco.py              # Conexões PostgreSQL
├── verifica_nps.py               # Script principal — análise NPS por analista
├── analise_ia.py                 # Integração com Gemini AI
├── get_atendimentos_nps.py       # Busca e anonimiza conversas
├── analise_woz_detratores.py     # Comparativo mensal de detratores WOZ
├── teste_conexao.py              # Script de teste
│
├── requirements.txt              # Dependências Python
├── .gitignore                    # Arquivos ignorados pelo Git
│
├── create_tables_nps.sql         # Criação das tabelas
├── create_analysis_columns.sql   # Colunas de análise estruturada
├── insereDadosAnaliseNPS.sql     # Processamento dos dados
├── woz_cria_tabela.sql           # Cria lw_octadesk.woz_comentarios (execute 1x)
│
├── README.md                     # Este arquivo
├── GUIA_INSTALACAO.md           # Guia detalhado de instalação
├── docs/                        # Documentação distribuída (manual, regras e arquitetura)
│   ├── MANUAL.md                # Guia operacional completo
│   ├── REGRAS.md                # Regras de negócio, limiares e políticas
│   └── ARQUITETURA.md           # Fluxo, módulos e dependências
├── README_ALTERACOES.md         # Histórico de mudanças
└── README_LOGGING.md            # Documentação do logging
│
├── logs/                         # Logs da aplicação
│   └── nps_verificacao.log
│
├── woz_detratores/ (gerados)     # Relatórios WOZ
│   ├── woz_mensal_2026-05-01_vs_2026-06-01.html
│   └── historico.json
│
└── outputs/ (gerados)            # Arquivos de saída NPS
    ├── atendimentos_nps_baixo.txt
    └── resposta_nps_gemini.md
```

---

## 🔒 Segurança

### Proteção de Credenciais

✅ **Implementado:**
- Credenciais no `.env` (fora do versionamento)
- `.gitignore` configurado para não versionar informações sensíveis
- Validação de configurações obrigatórias
- Nenhuma credencial hardcoded no código
- API Keys gerenciadas via variáveis de ambiente

### Dados Sensíveis

O sistema anonimiza automaticamente:
- 📧 Emails
- 🆔 CPF/CNPJ
- 📞 Telefones
- 🔐 Senhas/Logins
- 🌐 IPs e Domínios
- 💬 Palavrões

---

## 📈 Uso

### Execução Manual

```bash
# Ativar ambiente virtual
source venv/bin/activate   # Linux/Mac
.\venv\Scripts\activate    # Windows

# Análise NPS por analista
python verifica_nps.py

# Análise de detratores WOZ (comparativo mensal)
python analise_woz_detratores.py                                          # auto: últimos 2 meses
python analise_woz_detratores.py --ano1 2026 --mes1 5 --ano2 2026 --mes2 6   # Mai vs Jun/2026
python analise_woz_detratores.py --inicio1 2026-05-01 --fim1 2026-05-31 \
                                 --inicio2 2026-06-01 --fim2 2026-06-30      # override completo
```

### Execução Agendada

**Linux (cron):**
```bash
# Executar dia 1 de cada mês às 8h
0 8 1 * * cd /caminho/projeto && /caminho/venv/bin/python verifica_nps.py
```

**Windows (Task Scheduler):**
```powershell
schtasks /create /tn "NPS_Mensal" /tr "C:\caminho\venv\Scripts\python.exe C:\caminho\verifica_nps.py" /sc monthly /d 1 /st 08:00
```

### Consultar Resultados

```sql
-- Últimas análises (qualquer tipo)
SELECT
    request_datetime,
    analise_tipo,
    analistas_criticos,
    total_protocolos,
    setor
FROM lw_octadesk.analise_nps_analistas
ORDER BY request_datetime DESC
LIMIT 10;

-- Apenas análises NPS de analistas
SELECT
    analistas_criticos,
    resumo_geral,
    casos_criticos,
    recomendacoes_melhoria
FROM lw_octadesk.analise_nps_analistas
WHERE analise_tipo = 'monitoramento_nps_analistas'
  AND DATE(request_datetime) = CURRENT_DATE;

-- Resumo mensal WOZ (comparativo entre dois meses)
SELECT
    request_id,
    data_inicio,
    data_fim,
    analistas_criticos   AS tendencia,
    total_protocolos     AS comentarios_woz_mes2,
    resumo_geral,
    recomendacoes_melhoria,
    casos_criticos
FROM lw_octadesk.analise_nps_analistas
WHERE analise_tipo = 'woz_detratores_mensal'
ORDER BY request_datetime DESC;

-- Comentários WOZ individuais
SELECT
    protocolo,
    analista,
    fila,
    data_encerramento,
    velocidade, solucao, relacionamento,
    score_medio,
    classificacao,
    comentario,
    data_inicio_periodo,
    data_fim_periodo
FROM lw_octadesk.woz_comentarios
ORDER BY data_encerramento DESC
LIMIT 50;
```

---

## 🛠️ Solução de Problemas

### Erro: "GEMINI_API_KEY não configurada"

```bash
# Verifique o .env
cat .env | grep GEMINI

# Configure a chave
echo "GEMINI_API_KEY=sua_chave" >> .env
```

### Erro de Conexão com Banco

```bash
# Teste manualmente
psql -h SEU_HOST -U SEU_USER -d SEU_BANCO

# Verifique as variáveis
python config.py
```

### Módulo não encontrado

```bash
# Reinstale dependências
pip install -r requirements.txt --upgrade
```

### Ver logs detalhados

```bash
# Última execução
tail -f logs/nps_verificacao.log

# Buscar erros
grep "ERROR" logs/nps_verificacao.log
```

---

## 📚 Documentação

- **[GUIA_INSTALACAO.md](GUIA_INSTALACAO.md)** - Instalação passo a passo
- **[README_LOGGING.md](README_LOGGING.md)** - Sistema de logging
- **[README_ALTERACOES.md](README_ALTERACOES.md)** - Histórico de mudanças e correções
- **[docs/ARQUITETURA.md](docs/ARQUITETURA.md)** - Módulos, fluxo de dados e decisões de design
- **[docs/MANUAL.md](docs/MANUAL.md)** - Manual operacional detalhado
- **[docs/REGRAS.md](docs/REGRAS.md)** - Regras de negócio, idempotência e persistência

---

## 🎯 Roadmap Futuro

- [ ] Dashboard web para visualização
- [ ] Notificações via Slack/Email
- [x] Análise comparativa histórica — `analise_woz_detratores.py` + `historico.json`
- [x] Comparativo mensal WOZ — `--ano1 --mes1 --ano2 --mes2`
- [x] Gravação de comentários WOZ individuais — tabela `woz_comentarios`
- [ ] API REST para integração
- [ ] Testes automatizados
- [ ] Docker container

---

## 📊 Estatísticas do Projeto

- **Linguagem:** Python 3.8+
- **Linhas de Código:** ~2.200 linhas Python + 200 SQL
- **Módulos:** 9 arquivos principais
- **Dependências:** 10 pacotes Python
- **Banco de Dados:** PostgreSQL (`lw_octadesk`)
- **IA:** Google Gemini Flash
- **Tabelas:** `analise_nps_analistas` (resumo NPS + WOZ) · `woz_comentarios` (comentários individuais WOZ) · `rawdata_analise_nps_analistas` (rascunho NPS)

---

## 👤 Autor

**Sistema desenvolvido para análise de NPS de analistas de atendimento**

- Implementação inicial: Outubro 2025
- Versão atual: 2.4 (correções de integridade e segurança — ver README_ALTERACOES.md)

---

## 📝 Licença

[Definir licença conforme necessidade da empresa]

---

## 🤝 Contribuições

Para reportar bugs ou sugerir melhorias:

1. Verifique os logs: `logs/nps_verificacao.log`
2. Execute teste: `python teste_conexao.py`
3. Valide config: `python config.py`

---

**⚡ Sistema Pronto para Uso!**

Após configurar o `.env`, execute:

```bash
python teste_conexao.py  # Valida tudo
python verifica_nps.py   # Executa análise
```

---

*Última atualização: Julho 2026 | Versão 2.5 — análise WOZ convertida para comparativo mensal; nova tabela `woz_comentarios` para comentários individuais; CLI WOZ atualizado para `--ano1 --mes1 --ano2 --mes2`*

