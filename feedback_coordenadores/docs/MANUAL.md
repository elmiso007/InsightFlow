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

## 5. Execução do fluxo principal

```bash
python verifica_nps.py
```

### 5.1 O que acontece em execução

1. Carrega parâmetros do `.env`
2. Conecta ao PostgreSQL
3. Consulta avaliações do período definido
4. Calcula NPS por analista
5. Identifica analistas abaixo da meta
6. Busca atendimentos e comentários associados
7. Aplica anonimização de dados sensíveis
8. Envia contexto para IA do Gemini
9. Gera relatórios e salva os resultados

## 6. Saídas esperadas

- `logs/nps_verificacao.log` — log detalhado do processo
- `atendimentos_nps_baixo.txt` — conversas e atendimento dos analistas críticos
- `resposta_nps_gemini.md` — relatório da IA em markdown
- registros nas tabelas de análise no banco

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
- revisar logs após cada execução;
- usar o período configurado com atenção para não gerar relatórios incompletos;
- manter o `requirements.txt` atualizado quando adicionar dependências.
