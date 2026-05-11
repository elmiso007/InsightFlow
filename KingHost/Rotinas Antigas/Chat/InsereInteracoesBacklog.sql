INSERT INTO kinghost.chat_backlog
SELECT 
	protocolo::VARCHAR,
	id_sessao::VARCHAR,
	login_agente,
	fila,
	cliente,
	email,
	telefone_1,
	telefone_2,
	navegador,
	data_inicio_interacao,
	data_desvio_interacao,
	data_resposta_interacao,
	data_encerramento_interacao AS data_fim_interacao,
	duracao_espera AS tempo_espera,
	duracao_atendimento AS tempo_atendimento,
	status,	
	quantidade_interacoes,
	nivel1,
	nivel2,
	nivel3,
	nivel4,
	nivel5,
	p1::INTEGER,
	p2::INTEGER,
	p3::INTEGER,	
	comentarios,
	login_cliente,
	autorizacao_requisitada,
	autorizacao_aceita,
	autorizacao_erro,
	boleto,
	canal,
	ip,
	data_criacao_do_arquivo,
	'D-1' AS fonte_de_dados,
	NOW() AS data_insercao,
	NOW() AS data_modificacao
FROM teste.stginteracoes SI
WHERE NOT EXISTS (
    SELECT 1 
    FROM kinghost.chat_backlog AS I 
    WHERE 
	SI.protocolo::varchar = I.protocolo AND	
        SI.id_sessao::varchar = I.id_sessao AND  
	SI.fila = I.fila AND
        SI.data_inicio_interacao = I.data_inicio_interacao AND 
        SI.status = I.status
);