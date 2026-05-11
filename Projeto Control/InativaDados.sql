UPDATE control_desk.mapa_operacional i
SET 
    status = 'Inativado',
    data_modificacao = NOW()
WHERE NOT EXISTS (
    SELECT 1
    FROM control_desk.rawdata r
    WHERE i.matricula = CAST(r.matricula AS INTEGER)
) AND status in ('Ativo');
