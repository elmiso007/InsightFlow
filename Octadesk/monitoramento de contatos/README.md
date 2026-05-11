# Monitoramento de Contatos

Aplicação para monitorar volume recente de contatos no Octadesk, comparar com a média histórica da mesma janela de horário e, quando houver variação relevante, gerar análise automática por IA e notificar no Slack.

## Visão geral do fluxo

1. **Consulta no banco** dos atendimentos de Suporte na última janela de 30 minutos.
2. **Cálculo de média** dos últimos 7 dias úteis para a mesma janela de horário.
3. **Comparação** entre o volume atual e a média histórica.
4. **Quando a variação atende aos critérios**, coleta mensagens, anonimiza dados sensíveis, envia para IA e publica o resumo no Slack.
5. **Persistência** dos resultados no banco para auditoria.

## Estrutura do diretório

- `verifica.py`  
  Orquestra o processo: consulta, cálculo de média, comparação, acionamento da IA e gravação no banco.
- `get_atendimentos.py`  
  Busca conversas e monta dataset anonimizado para análise.
- `PromptOpenAi.py`  
  Chama a API da OpenAI, salva resposta e grava histórico no banco.
- `notifica.py`  
  Envia mensagem formatada para canais/usuários no Slack.
- `conecta_banco.py`  
  Conexões com PostgreSQL (SQLAlchemy, pyodbc, psycopg2).
- `insereDados.sql`  
  Merge/insert dos dados de monitoramento.
- `insereDadosAnaliseIA.sql`  
  Merge/insert das análises da IA.
- `ExecutaVerificacao.bat`  
  Executa o monitoramento via `python verifica.py`.
- `dados.txt`  
  Arquivo gerado com dataset anonimizado (entrada para a IA).
- `resposta_openai.md`  
  Saída da análise gerada pela IA.

## Regras de execução

- **Janela de execução**: 06:00–20:00 (fora disso o script encerra).
- **Dias úteis**: execução ocorre somente em dias úteis (feriados e fins de semana são ignorados).
- **Janela de comparação**: últimos 30 minutos.
- **Média histórica**: últimos 7 dias úteis (mesma janela de horário).

## Critério para disparar análise e notificação

A análise e notificação são disparadas quando:

- A variação percentual em relação à média não é extremamente negativa, e
- O volume atual é maior que 3 atendimentos.

Esses critérios estão definidos em `verifica.py`.

## Requisitos

- Python 3.10+
- PostgreSQL (banco `report_requesttracker`)
- Slack Bot Token válido
- Acesso à API da OpenAI

### Dependências principais (pip)

- `pandas`
- `sqlalchemy`
- `pyodbc`
- `psycopg2`
- `requests`
- `slack_sdk`
- `holidays`
- `beautifulsoup4`
- `numpy`

## Configuração

Hoje as credenciais estão **hardcoded** no código. Recomenda-se mover para variáveis de ambiente.

Locais atuais:

- **Banco**: `conecta_banco.py`
- **Slack Token**: `notifica.py`
- **OpenAI Key**: `PromptOpenAi.py`

## Execução

Via BAT:

```
ExecutaVerificacao.bat
```

Via Python:

```
python verifica.py
```

## Saídas e persistência

- **Banco**:
  - `octadesk.rawdata_monitoramento_contatos` (execuções e métricas)
  - `octadesk.rawdata_analise_monitoramento_contatos` (análises IA)
- **Arquivos**:
  - `dados.txt` (dataset anonimizado)
  - `resposta_openai.md` (resposta da IA)

## Anonimização de dados

O módulo `get_atendimentos.py` remove ou mascara dados sensíveis como:

- e-mails, CPFs, CNPJs, telefones
- IPs, links e domínios
- nomes de empresas específicas e concorrentes
- informações de login/senha

Esse dataset anonimizado é o que é enviado à IA.

## Troubleshooting rápido

- Sem dados retornados: valida se a query está correta e se o horário está dentro do intervalo permitido.
- Erros de autenticação: confira credenciais do banco, Slack e OpenAI.
- Falha no Slack: valide se o token tem permissão para postar no canal configurado.


