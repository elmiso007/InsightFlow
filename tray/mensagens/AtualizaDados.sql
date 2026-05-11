UPDATE tray.mensagens a
SET
data_ultima_interacao = SI.data_ultima_interacao,
mensagens = SI.mensagens::JSON,
data_modificacao = NOW()
FROM tray.rawdata_mensagens SI
WHERE 
SI.id = a.id AND 
SI.data_ultima_interacao > a.data_ultima_interacao