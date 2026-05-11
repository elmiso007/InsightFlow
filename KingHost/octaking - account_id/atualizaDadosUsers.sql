--CRIAÇÃO DO UPDATE TABELA FINAL

UPDATE kinghost_octadesk.ficha_do_cliente I
SET
chat_id = SI.id,
account_id = SI.account_id,
data_ultima_interacao = SI.data_ultima_interacao,
data_modificacao = NOW()
FROM kinghost_octadesk.rawdata_ficha_do_cliente SI
WHERE
 I.chat_id = SI.id AND
 SI.data_ultima_interacao > I.data_ultima_interacao
