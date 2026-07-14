# Manual Operacional — Sistema de Análise NPS

## 1. Finalidade

Este manual descreve como configurar, executar e monitorar o fluxo de análise de NPS dos analistas de atendimento.

## 2. Pré-requisitos

- Python 3.9+ recomendado
- Ambiente virtual configurado
- Acesso ao PostgreSQL
- Chave de API do Google Gemini
- Permissões de leitura nas views do banco e escrita na pasta do projeto

## 3. Instalação

### 3.1 Criar ambiente virtual

Windows:
```powershell
python -m venv venv
.\venv\Scripts\activate
```

Linux/Mac:
```bash
python -m venv venv
source venv/bin/activate
```

### 3.2 Instalar dependências

```bash
pip install -r requirements.txt
```

### 3.3 Configurar variáveis de ambiente

Crie ou edite o arquivo `.env` na raiz do projeto com as variáveis essenciais:

```env
DB_HOST=seu_host
DB_PORT=5432
DB_NAME=seu_banco
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
DB_SCHEMA=seu_schema
GEMINI_API_KEY=sua_chave
GEMINI_MODEL=gemini-flash-latest
NPS_META=70.0
NPS_MIN_AVALIACOES=3
NPS_PERIODO_TIPO=mes_anterior
ANALISE_MAX_DATASET_SIZE=12000
ANALISE_MAX_TENTATIVAS=5
ANALISE_DELAY_TENTATIVA=5
ANALISE_RETENTION_DAYS=90
LOG_FILE_LEVEL=DEBUG
LOG_CONSOLE_LEVEL=INFO
LOG_MAX_SIZE_MB=10
LOG_BACKUP_COUNT=5
```

## 4. Validação inicial

Execute:

```bash
python config.py
python teste_conexao.py
```

O objetivo é confirmar:
- importações corretas;
- leitura do `.env`;
- conexão ao banco;
- disponibilidade da API Gemini;
- permissões de escrita em logs e diretório principal.

## 5. Execução

### 5.1 Fluxo NPS por analista

```bash
python verifica_nps.py
```

O que acontece em execução:

1. Carrega parâmetros do `.env`
2. Conecta ao PostgreSQL
3. Consulta avaliações do período definido (`vw_report_diario`)
4. Calcula NPS por analista (fórmula padrão: promotores − detratores / total × 100)
5. Identifica analistas abaixo da meta
6. Busca atendimentos e comentários associados (paralelo, N workers)
7. Aplica anonimização de dados sensíveis antes de enviar para a IA
8. Envia contexto para Google Gemini — idempotente: analistas já analisados no período são pulados
9. Após todos os workers concluírem, executa `insereDadosAnaliseNPS.sql` uma única vez
10. Gera relatórios HTML e salva no banco

### 5.2 Análise de detratores WOZ (comparativo mensal)

```bash
# Auto: últimos 2 meses completos
python analise_woz_detratores.py

# Especificar dois meses manualmente
python analise_woz_detratores.py --ano1 2026 --mes1 5 --ano2 2026 --mes2 6

# Override completo de datas
python analise_woz_detratores.py --inicio1 2026-05-01 --fim1 2026-05-31 \
                                 --inicio2 2026-06-01 --fim2 2026-06-30
```

O que acontece em execução:

1. Busca comentários NPS com termos WOZ via SQL ILIKE para cada mês
2. Classifica cada comentário em Promotor / Neutro / Detrator
3. Calcula métricas por mês e variação entre os dois períodos
4. Persiste comentários individuais em `woz_comentarios` (idempotente por protocolo+período)
5. Gera HTML em `woz_detratores/woz_mensal_{data_inicio_1}_vs_{data_inicio_2}.html`
6. Persiste resumo em `analise_nps_analistas` com `analise_tipo = 'woz_detratores_mensal'`
7. Atualiza `woz_detratores/historico.json` (somente se o banco persistiu com sucesso)

## 6. Saídas esperadas

**Fluxo NPS (`verifica_nps.py`):**
- `logs/nps_verificacao.log` — log detalhado do processo
- `analistas_criticos/{analista}.html` — relatório HTML individual por analista
- `analistas_criticos/index.html` — índice de todos os analistas analisados
- banco: `rawdata_analise_nps_analistas` (rascunho) e `analise_nps_analistas` (final, `analise_tipo='monitoramento_nps_analistas'`)

**Fluxo WOZ (`analise_woz_detratores.py`):**
- banco: `woz_comentarios` — cada comentário WOZ individual com protocolo, notas, classificação e score
- `woz_detratores/woz_mensal_{data_inicio_1}_vs_{data_inicio_2}.html` — relatório HTML do comparativo
- `woz_detratores/historico.json` — histórico acumulativo de todos os comparativos executados
- banco: `analise_nps_analistas` (`analise_tipo='woz_detratores_mensal'`) — resumo do comparativo

## 7. Solução de problemas

### Erro de importação

```bash
pip install -r requirements.txt
```

### Erro de conexão com banco

- confirme host, porta, usuário e senha;
- confirme que o schema está disponível;
- valide se a view `vw_report_diario` está acessível.

### Erro na API Gemini

- valide a chave em `.env`;
- confirme que o modelo configurado está disponível;
- teste com `teste_conexao.py`.

## 8. Boas práticas

- não versionar o arquivo `.env`;
- manter as chaves de API protegidas;
- revisar logs após cada execução — erros na extração das 6 seções da IA aparecem como `ERROR`;
- usar o período configurado com atenção para não gerar relatórios incompletos;
- ajustar `ANALISE_RETENTION_DAYS` conforme a política de retenção da empresa (padrão: 90 dias);
- manter o `requirements.txt` atualizado quando adicionar dependências;
- ao executar `analise_woz_detratores.py`, confirmar que o banco está acessível antes — os comentários em `woz_comentarios` e o `historico.json` só são persistidos se o banco responder com sucesso;
- a tabela `woz_comentarios` deve ser criada antes da primeira execução: `psql -f woz_cria_tabela.sql`;
- o script `verifica_nps.py` é seguro para re-execução: analistas já analisados no período são detectados e pulados automaticamente (idempotência via `request_id`).
