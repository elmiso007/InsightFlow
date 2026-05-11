
INSERT INTO tray.mensagens 
(id,data_ultima_interacao, mensagens,fonte_de_dados,data_insercao, data_modificacao)
SELECT 
id,
data_ultima_interacao,
mensagens::JSON,
'Endpoint /id/messages' AS fonte_de_dados,
NOW() AS data_insercao,
Now() AS data_modificacao
FROM tray.rawdata_mensagens B
WHERE NOT EXISTS (SELECT 1 FROM tray.mensagens AS L WHERE L.id = B.id )