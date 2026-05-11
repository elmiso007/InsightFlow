Atualizacao das Tabelas
=======================

Aplicacao em Python que consulta uma view no PostgreSQL e envia um resumo
formatado para o Slack com o status de atualizacao das tabelas (D-1, D-2 e
quantitativos).

✨ **Novidades:**
- 📝 Sistema de logging centralizado integrado
- 📢 Suporte para canal oficial e canal de teste no Slack
- 🔄 Rotação automática de arquivos de log

Visao geral
-----------
1. Conecta no banco PostgreSQL.
2. Executa a view `aplicacao.atualizacao_das_tabelas`.
3. Valida se as colunas esperadas foram retornadas.
4. Formata a tabela com `tabulate` e envia para o Slack (oficial ou teste).
5. Registra todas as operacoes em logs estruturados.

Estrutura de arquivos
---------------------
- `app.py`                Logica principal.
- `config.ini`            Fallback de configuracao (sem segredos).
- `.env`                  Credenciais e tokens (na mesma pasta do app).
- `.env.example`          Exemplo de variaveis.
- `logger.py`             Sistema centralizado de logging.
- `exemplo_logger.py`     Exemplos de uso do logger.
- `requirements.txt`      Dependencias.
- `VerificaTabelas.bat`   Execucao no Windows.
- `logs/`                 Diretorio com logs estruturados.

Requisitos
----------
- Python 3.10+
- Dependencias: `pip install -r requirements.txt`

Configuracao
------------
1. Copie `.env.example` para `.env` (mesma pasta do `app.py`).
2. Preencha as variaveis abaixo:

PG_SERVER=...
PG_DATABASE=...
PG_USER=...
PG_PASSWORD=...
SLACK_TOKEN=...
SLACK_CHANNEL=...

Observacoes:
- `config.ini` e opcional e serve como fallback, mas deve ficar sem segredos.
- Se `.env` tiver valores vazios ou placeholders, o app encerra com erro.

Detalhes de conexao
-------------------
O script monta a connection string no formato:

postgresql://PG_USER:PG_PASSWORD@PG_SERVER/PG_DATABASE

View esperada
-------------
A view `aplicacao.atualizacao_das_tabelas` deve retornar as colunas:
- `tabela`
- `atualizacao`
- `d_1`
- `qtd_d1`
- `qtd_d2`

Se alguma delas estiver ausente, o script encerra com erro.

Canais do Slack
---------------
A aplicacao agora suporta dois canais Slack:

**Canal Oficial** (padrão)
- ID: Configurado em `SLACK_CHANNEL` no `.env`
- Uso: Notificacoes em produção
- Ativo por padrao

**Canal de Teste**
- ID: `C07NSPQ69TL`
- Uso: Validar alteracoes antes de publicar em producao
- Para ativar: Descomente as linhas indicadas em `app.py`

Como trocar de canal
~~~~~~~~~~~~~~~~~~~~
1. Abra `app.py` e localize a secao:

   ```
   # ===== ESCOLHA O CANAL: COMENTE/DESCOMENTE AS LINHAS ABAIXO =====
   # Canal Oficial (padrão)
   CHANNEL_ID = get_setting("SLACK_CHANNEL", "slack", "channel_id", config)
   canal_selecionado = "OFICIAL"

   # Canal de Teste - descomente as duas linhas abaixo para usar o canal de teste
   # CHANNEL_ID = "C07NSPQ69TL"
   # canal_selecionado = "TESTE"
   # ================================================================
   ```

2. **Para usar o canal TESTE:** Comente as 2 linhas do oficial e descomente o teste.
3. **Para usar o canal OFICIAL:** Mantenha como está (padrão).
4. A mensagem no Slack indicará qual canal está sendo usado.

Sistema de Logging
------------------
Um sistema centralizado de logging foi integrado com as seguintes funcionalidades:

**Arquivos de Log**
- Localizacao: `logs/auditoria_YYYY-MM-DD.log`
- Formato: JSON estruturado
- Rotacao automatica a cada 5MB
- Mantém até 5 backups de arquivo

**Eventos Registrados**
- Inicio e fim de execucao
- Consulta à view
- Envio de mensagem ao Slack
- Erros e avisos
- Tentativas de reconexao

**Exemplo de Uso do Logger em seu codigo**
```python
from logger import get_logger

# Criar logger para seu modulo
logger = get_logger(__name__, "meu_app.log")

# Usar o logger
logger.info("Operacao iniciada")
logger.warning("Aviso importante")
logger.error("Erro encontrado")
logger.debug("Informacao de debug")
```

Para mais detalhes, veja `LOGGER_README.md` e `CANAIS_SLACK.md`.

Definicao da view (referencia)
------------------------------
```
CREATE OR REPLACE VIEW aplicacao.atualizacao_das_tabelas AS (
    SELECT 'log_ura'::text AS tabela,
           max(log_ura.datetime)::date AS atualizacao,
           max(log_ura.datetime)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN log_ura.datetime::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN log_ura.datetime::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM log_ura
    UNION ALL
    SELECT 'login_logout_tel'::text AS tabela,
           max(login_logout_tel.dia)::date AS atualizacao,
           max(login_logout_tel.dia)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN login_logout_tel.dia::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN login_logout_tel.dia::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM login_logout_tel
    UNION ALL
    SELECT 'pesquisa_tel_is'::text AS tabela,
           max(pesquisa_tel_is.dia)::date AS atualizacao,
           max(pesquisa_tel_is.dia)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN pesquisa_tel_is.dia::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN pesquisa_tel_is.dia::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM pesquisa_tel_is
    UNION ALL
    SELECT 'contatos_chat_fila'::text AS tabela,
           max(contatos_chat_fila.dia)::date AS atualizacao,
           max(contatos_chat_fila.dia)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN contatos_chat_fila.dia::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN contatos_chat_fila.dia::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM contatos_chat_fila
    UNION ALL
    SELECT 'contatos_chat_fila_s_whats'::text AS tabela,
           max(contatos_chat_fila_s_whats.dia)::date AS atualizacao,
           max(contatos_chat_fila_s_whats.dia)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN contatos_chat_fila_s_whats.dia::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN contatos_chat_fila_s_whats.dia::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM contatos_chat_fila_s_whats
    UNION ALL
    SELECT 'nps_chat_fila'::text AS tabela,
           max(nps_chat_fila.recebido)::date AS atualizacao,
           max(nps_chat_fila.recebido)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN nps_chat_fila.recebido::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN nps_chat_fila.recebido::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM nps_chat_fila
    UNION ALL
    SELECT 'lp_motivo_finalizacao'::text AS tabela,
           max(lp_motivo_finalizacao.starttime)::date AS atualizacao,
           max(lp_motivo_finalizacao.starttime)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN lp_motivo_finalizacao.starttime::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN lp_motivo_finalizacao.starttime::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM lp_motivo_finalizacao
    UNION ALL
    SELECT 'ps_chat_inside'::text AS tabela,
           max(ps_chat_inside.recebido)::date AS atualizacao,
           max(ps_chat_inside.recebido)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN ps_chat_inside.recebido::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN ps_chat_inside.recebido::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM ps_chat_inside
    UNION ALL
    SELECT 'satisfacao_atendimento_cc'::text AS tabela,
           max(satisfacao_atendimento_cc.dia)::date AS atualizacao,
           max(satisfacao_atendimento_cc.dia)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN satisfacao_atendimento_cc.dia::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN satisfacao_atendimento_cc.dia::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM satisfacao_atendimento_cc
    UNION ALL
    SELECT 'fcr_chat_analista'::text AS tabela,
           max(fcr_chat_analista.dia)::date AS atualizacao,
           max(fcr_chat_analista.dia)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN fcr_chat_analista.dia::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN fcr_chat_analista.dia::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM fcr_chat_analista
    UNION ALL
    SELECT 'fcr_chat_fila'::text AS tabela,
           max(fcr_chat_fila.dia)::date AS atualizacao,
           max(fcr_chat_fila.dia)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN fcr_chat_fila.dia::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN fcr_chat_fila.dia::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM fcr_chat_fila
    UNION ALL
    SELECT 'fcr_whats_analista'::text AS tabela,
           max(fcr_whats_analista.dia)::date AS atualizacao,
           max(fcr_whats_analista.dia)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN fcr_whats_analista.dia::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN fcr_whats_analista.dia::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM fcr_whats_analista
    UNION ALL
    SELECT 'fcr_whatsapp_fila'::text AS tabela,
           max(fcr_whatsapp_fila.dia)::date AS atualizacao,
           max(fcr_whatsapp_fila.dia)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN fcr_whatsapp_fila.dia::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN fcr_whatsapp_fila.dia::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM fcr_whatsapp_fila
    UNION ALL
    SELECT 'fcr_tel_fila'::text AS tabela,
           max(fcr_tel_fila.dia)::date AS atualizacao,
           max(fcr_tel_fila.dia)::date = (now()::date - 1) AS d_1,
           sum(CASE WHEN fcr_tel_fila.dia::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN fcr_tel_fila.dia::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM fcr_tel_fila
    UNION ALL
    SELECT 'dynamics.chamados'::text AS tabela,
           max(chamados.dataultimainteracao)::date AS atualizacao,
           sum(CASE WHEN chamados.dataultimainteracao::date = (now()::date - 1) THEN 1 ELSE 0 END) > 0 AS d_1,
           sum(CASE WHEN chamados.dataultimainteracao::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN chamados.dataultimainteracao::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM dynamics.chamados
    UNION ALL
    SELECT 'kinghost_octadesk.ficha_do_cliente'::text AS tabela,
           max(ficha_do_cliente.data_ultima_interacao)::date AS atualizacao,
           max(ficha_do_cliente.data_ultima_interacao)::date >= (now()::date - 1) AS d_1,
           sum(CASE WHEN ficha_do_cliente.data_ultima_interacao::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN ficha_do_cliente.data_ultima_interacao::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM kinghost_octadesk.ficha_do_cliente
    UNION ALL
    SELECT 'lw_octadesk.login_do_cliente'::text AS tabela,
           max(login_do_cliente.data_ultima_interacao)::date AS atualizacao,
           max(login_do_cliente.data_ultima_interacao)::date >= (now()::date - 1) AS d_1,
           sum(CASE WHEN login_do_cliente.data_ultima_interacao::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN login_do_cliente.data_ultima_interacao::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM lw_octadesk.login_do_cliente
    UNION ALL
    SELECT 'lw_octadesk.bus_atendimentos'::text AS tabela,
           max(bus_atendimentos.data_inicio_interacao)::date AS atualizacao,
           max(bus_atendimentos.data_inicio_interacao)::date >= (now()::date - 1) AS d_1,
           sum(CASE WHEN bus_atendimentos.data_inicio_interacao::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN bus_atendimentos.data_inicio_interacao::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM lw_octadesk.bus_atendimentos
    UNION ALL
    SELECT 'public.onboarding'::text AS tabela,
           max(onboarding.data_insercao)::date AS atualizacao,
           max(onboarding.data_insercao)::date >= (now()::date - 1) AS d_1,
           sum(CASE WHEN onboarding.data_insercao::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN onboarding.data_insercao::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM onboarding
    UNION ALL
    SELECT 'public.vwmps_ps_cal'::text AS tabela,
           max(vwmps_ps_cal.dia)::date AS atualizacao,
           max(vwmps_ps_cal.dia)::date >= (now()::date - 1) AS d_1,
           sum(CASE WHEN vwmps_ps_cal.dia::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN vwmps_ps_cal.dia::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM vwmps_ps_cal
    UNION ALL
    SELECT 'transfer_pesq_npstel_is'::text AS tabela,
           max(transfer_pesq_npstel_is.dia)::date AS atualizacao,
           max(transfer_pesq_npstel_is.dia)::date >= (now()::date - 1) AS d_1,
           sum(CASE WHEN transfer_pesq_npstel_is.dia::date = (now()::date - 1) THEN 1 ELSE 0 END) AS qtd_d1,
           sum(CASE WHEN transfer_pesq_npstel_is.dia::date = (now()::date - 2) THEN 1 ELSE 0 END) AS qtd_d2
      FROM transfer_pesq_npstel_is
);
```

Formato da mensagem no Slack
----------------------------
- Header com a data do dia.
- Indicacao de qual canal esta sendo usado (OFICIAL ou TESTE).
- Tabela formatada em bloco markdown (fenced code).
- `d_1` vira emoji:
  - `True` -> "✅"
  - `False` -> "❌"

**Exemplo de mensagem:**
```
*Resumo das atualizacoes das tabelas e quantitativos D-1 e D-2 em:* `2026-02-04`
📢 *Canal:* `OFICIAL`
(tabela formatada aqui)
```

Execucao
--------
No Windows (recomendado):
`VerificaTabelas.bat`

Ou diretamente:
`python "Atualizacao das Tabelas/app.py"`

Agendamento
-----------
Este processo ja esta configurado na VM para rodar de segunda a sexta as 08:00.
Caso precise ajustar no futuro, edite a tarefa existente no Agendador de Tarefas
e mantenha a acao apontando para `VerificaTabelas.bat`.

**Nota importante:** Se quiser testar o script antes de agendar em producao, 
altere o canal para TESTE em `app.py` para validar as mensagens no canal de teste.

Tratamento de erros
-------------------
- Falta de variaveis: o script encerra informando quais faltam.
- Erros no Slack: retorna o erro da API no console e registra nos logs.
- Colunas ausentes: encerra com mensagem de inconsistencias na view.
- Envio ao Slack: 3 tentativas com backoff exponencial (2s, 4s, 8s).
- Todos os erros sao registrados em `logs/auditoria_YYYY-MM-DD.log`.

Seguranca
---------
- Nao versionar `.env`.
- Guarde credenciais apenas na VM que executa a rotina.
- Revise o acesso ao Slack e ao banco periodicamente.
- Os logs sao salvos em formato estruturado para auditoria.

Documentacao Adicional
----------------------
- `CANAIS_SLACK.md` - Guia detalhado sobre os canais oficial e teste.
- `LOGGER_README.md` - Documentacao completa do sistema de logging.
 - `LOGGER_README.md` - Documentacao completa do sistema de logging.
 - Exemplo de uso do logger: `exemplo_logger.py`

Limpeza de arquivos e backups
-----------------------------
Alguns arquivos auxiliares foram removidos da pasta principal e arquivados em `archive_removed/` para evitar exposição de segredos e manter o repositório enxuto:

- `.env` -> `archive_removed/.env.bak`  (contém credenciais sensíveis)
- `exemplo_logger.py` -> `archive_removed/exemplo_logger.py.bak`
- `teste_dependencias.py` -> `archive_removed/teste_dependencias.py.bak`
- `teste.py` -> `archive_removed/teste.py.bak`

Como restaurar um arquivo do backup
1. Copie o arquivo do diretório de backup para a pasta do projeto (localmente):

```
copy archive_removed\\.env.bak .\\.env
```

2. Ajuste permissões e valores sensíveis antes de usar.

Observações de segurança
- O repositório contém um arquivo `.gitignore` configurado para ignorar `.env`, `archive_removed/` e `logs/`.
- Nunca commit credenciais em repositórios públicos.

