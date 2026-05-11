--CRIAÇÃO DO INSERT NA TABELA FINAL
INSERT INTO tray.chat (id,
protocolo,agent_id,agent_name,agent_email,canal,
data_inicio_interacao,data_ultima_interacao,data_fim_interacao,
tempo_atendimento_segundos,tempo_atendimento_formatado, contact_name,
contact_id,iniciado_por,tags,tag_1,tag_2,tag_3,tag_4,tag_5,com_bot,status,
grupo_id,grupo_nome,nao_lidas,tempo_espera,tempo_atendimento_analista,origem,bot_name,conversation_origin,status_detail,
data_inicio_interacao_agente,atribuicao_agente,atribuicao_grupo,pesquisa,
comentario,fonte_de_dados,data_insercao,data_modificacao)
SELECT DISTINCT ON (SI.id)
    id,protocolo,agent_id,agent_name,agent_email,canal,
    data_inicio_interacao,data_ultima_interacao,data_fim_interacao,
    tempo_atendimento_segundos,tempo_atendimento_formatado, contact_name,
    contact_id,iniciado_por,tags,tag_1,tag_2,tag_3,tag_4,tag_5,com_bot,status,
    grupo_id,grupo_nome,nao_lidas,tempo_espera,tempo_atendimento_analista,origem,bot_name,conversation_origin,status_detail,
    data_inicio_interacao_agente,atribuicao_agente,atribuicao_grupo,pesquisa,
    comentario,fonte_de_dados,data_insercao,data_modificacao
FROM tray.stgchat SI
WHERE NOT EXISTS (
    SELECT 1 
    FROM tray.chat AS I 
    WHERE SI.id = I.id
)
ORDER BY SI.id, SI.data_ultima_interacao DESC;