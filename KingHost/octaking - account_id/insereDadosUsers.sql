
INSERT INTO kinghost_octadesk.ficha_do_cliente 
(chat_id, account_id, data_ultima_interacao, data_insercao, fonte_de_dados, data_modificacao)
SELECT 
id,
account_id,
data_ultima_interacao,
NOW() AS data_insercao,
'Endpoint /chat/id' AS fonte_de_dados,
NOW() AS data_modificacao
FROM kinghost_octadesk.rawdata_ficha_do_cliente B
WHERE NOT EXISTS (SELECT 1 FROM kinghost_octadesk.ficha_do_cliente AS L WHERE L.chat_id = B.id )