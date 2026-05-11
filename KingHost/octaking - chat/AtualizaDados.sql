--CRIAÇÃO DO UPDATE TABELA FINAL

UPDATE kinghost_octadesk.chat I
SET
agent_id = SI.agent_id,
agent_name = SI.agent_name,
agent_email = SI.agent_email,
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
tag_6 = SI.tag_6,
tag_7 = SI.tag_7,
tag_8 = SI.tag_8,
com_bot = SI.com_bot,
status = SI.status,
grupo_id = SI.grupo_id,
grupo_nome = SI.grupo_nome,
nao_lidas = SI.nao_lidas,
fonte_de_dados = SI.fonte_de_dados,
data_modificacao = NOW(),
tempo_espera = SI.tempo_espera,
tempo_atendimento_analista = SI.tempo_atendimento_analista,
origem = SI.origem,
status_detail = SI.status_detail,
data_inicio_interacao_agente = SI.data_inicio_interacao_agente,
atribuicao_agente = SI.atribuicao_agente,
atribuicao_grupo = SI.atribuicao_grupo,
pesquisa = SI.pesquisa,
comentario = SI.comentario
FROM kinghost_octadesk.stgchat SI
WHERE
 I.id = SI.id AND
 SI.data_ultima_interacao > I.data_ultima_interacao
