INSERT INTO kinghost.interacoes
SELECT * FROM kinghost.vw_insereinteracoes II 
WHERE NOT EXISTS (SELECT 1 FROM kinghost.interacoes AS I WHERE II.protocolo = I.protocolo);