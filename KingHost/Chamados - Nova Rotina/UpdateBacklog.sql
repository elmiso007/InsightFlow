UPDATE kinghost.chamadosbacklog c
SET 
    p1 = s."P1",
    p2 = s."P2",
    p3 = s."P3",
    comentarios = s."Comentario",
    datamodificacao = now()
FROM kinghost.stgchamadosking s
WHERE c.idefetivo = s."idChamado" 
  AND c.dataultimainteracao = s."DataUltimaInteracao"::TIMESTAMP
