UPDATE cplug.chat I
SET
agent_id = SI.agent_id,
agent_name = SI.agent_name,
agent_email = SI.agent_email,
canal = SI.canal,
data_ultima_interacao = SI.data_ultima_interacao,
data_fim_interacao = SI.data_fim_interacao,
tempo_atendimento_segundos = SI.tempo_atendimento_segundos,
tempo_atendimento_formatado = SI.tempo_atendimento_formatado,
contact_name = SI.contact_name,
contact_id = SI.contact_id,
iniciado_por = SI.iniciado_por,
tags = SI.tags,
tag_1 = SI.tag_1,
tag_2 = SI.tag_2,
tag_3 = SI.tag_3,
tag_4 = SI.tag_4,
tag_5 = SI.tag_5,
com_bot = SI.com_bot,
status = SI.status,
grupo_id = SI.grupo_id,
grupo_nome = SI.grupo_nome,
nao_lidas = SI.nao_lidas,
tempo_espera = SI.tempo_espera,
tempo_atendimento_analista = SI.tempo_atendimento_analista,
origem = SI.origem,
bot_name = SI.bot_name,
conversation_origin = SI.conversation_origin,
status_detail = SI.status_detail,
data_inicio_interacao_agente = SI.data_inicio_interacao_agente,
atribuicao_agente = SI.atribuicao_agente,
atribuicao_grupo = SI.atribuicao_grupo,
pesquisa = SI.pesquisa,
comentario = SI.comentario,
bot_contact_started_at = SI.bot_contact_started_at,
bot_assigned_at = SI.bot_assigned_at,
bot_id = SI.bot_id,
bot_transferred_to_human_at = SI.bot_transferred_to_human_at,
bot_resolved_by_bot = SI.bot_resolved_by_bot,
fonte_de_dados = SI.fonte_de_dados,
data_modificacao = NOW()
FROM (
    SELECT DISTINCT ON (id) *
    FROM cplug.stg_chat
    ORDER BY id, data_ultima_interacao DESC
) SI
WHERE
    I.id = SI.id
    AND SI.data_ultima_interacao > I.data_ultima_interacao;

