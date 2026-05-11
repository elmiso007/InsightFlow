--CRIAÇÃO DO INSERT NA TABELA FINAL
INSERT INTO kinghost_octadesk.chat (id,
protocolo,agent_id,agent_name,agent_email,canal,
data_inicio_interacao,data_ultima_interacao,data_fim_interacao,
tempo_atendimento_segundos,tempo_atendimento_formatado, contact_name,
contact_id,iniciado_por,tags,tag_1,tag_2,tag_3,tag_4,tag_5,tag_6,tag_7,
tag_8,com_bot,status,grupo_id,grupo_nome,nao_lidas,tempo_espera,tempo_atendimento_analista,origem,status_detail,
data_inicio_interacao_agente,atribuicao_agente,atribuicao_grupo,pesquisa,
comentario,fonte_de_dados,data_insercao,data_modificacao)
SELECT 
id,protocolo,agent_id,agent_name,agent_email,canal,data_inicio_interacao,
data_ultima_interacao,data_fim_interacao,tempo_atendimento_segundos,
tempo_atendimento_formatado, contact_name,contact_id,iniciado_por,
tags,tag_1,tag_2,tag_3,tag_4,tag_5,tag_6,tag_7,tag_8,com_bot,
status,grupo_id,grupo_nome,nao_lidas,tempo_espera,tempo_atendimento_analista,origem,status_detail,
data_inicio_interacao_agente,atribuicao_agente,atribuicao_grupo,
pesquisa,comentario,fonte_de_dados,data_insercao,data_modificacao
FROM kinghost_octadesk.stgchat SI
WHERE NOT EXISTS (
    SELECT 1 
    FROM kinghost_octadesk.chat AS I 
    WHERE 
	SI.id = I.id	
);
