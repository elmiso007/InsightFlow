--CRIAÇÃO DO UPDATE TABELA FINAL

UPDATE lw_octadesk.login_do_cliente I
SET
login_usuario = SI.login_usuario,
customer_id = SI.customer_id,
data_ultima_interacao = SI.data_ultima_interacao,
qtd_interacoes = SI.qtd_interacoes,
motivo_de_contato = SI.motivo_de_contato,
nivel1 = SI.nivel1 ,
nivel2 = SI.nivel2 ,
nivel3 = SI.nivel3 ,
nivel4 = SI.nivel4 ,
nivel5 = SI.nivel5 ,
data_modificacao = NOW()
FROM lw_octadesk.stg_login_do_cliente SI
WHERE
 I.chat_id = SI.chat_id AND
 SI.data_ultima_interacao > I.data_ultima_interacao
