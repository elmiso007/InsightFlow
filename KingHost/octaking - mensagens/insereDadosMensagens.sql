
INSERT INTO kinghost_octadesk.mensagens 
(id,data_ultima_interacao, mensagens,fonte_de_dados,data_insercao, data_modificacao)
SELECT 
id,
data_ultima_interacao,
mensagens::JSON,
'Endpoint /id/messages' AS fonte_de_dados,
NOW() AS data_insercao,
Now() AS data_modificacao
FROM kinghost_octadesk.rawdata_messages B
WHERE NOT EXISTS (SELECT 1 FROM kinghost_octadesk.mensagens AS L WHERE L.id = B.id )