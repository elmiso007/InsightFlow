UPDATE control_desk.mapa_operacional i
SET 
    status = r.status::VARCHAR,
    equipe = r.equipe::VARCHAR,
    skill = r.skill::VARCHAR,
    funcao = r.funcao::VARCHAR,
    coordenador = LOWER(r.coordenador::VARCHAR),
    horario = r.horario::TIME,
    pausa1 = r.pausa1::TIME,
    intervalo = r.intervalo::TIME,
    pausa3 = r.pausa3::TIME,
    saida = r.saida::TIME,
    observacoes = r.observacoes::TEXT,
    id_slack = r.id_slack::VARCHAR,
    data_modificacao = NOW()
FROM control_desk.rawdata r
WHERE 
    i.login = LOWER(r.login::VARCHAR)
    AND i.matricula = CAST(r.matricula AS INTEGER)
    AND (
        i.status <> r.status::VARCHAR OR
        i.equipe <> r.equipe::VARCHAR OR
        i.skill <> r.skill::VARCHAR OR
        i.funcao <> r.funcao::VARCHAR OR
        i.coordenador <> LOWER(r.coordenador::VARCHAR) OR
        i.horario <> r.horario::TIME OR
        i.pausa1 <> r.pausa1::TIME OR
        i.intervalo <> r.intervalo::TIME OR
        i.pausa3 <> r.pausa3::TIME OR
        i.saida <> r.saida::TIME OR
        i.observacoes <> r.observacoes::TEXT OR
        i.id_slack <> r.id_slack::VARCHAR
    )
RETURNING i.id_slack, i.login,i.skill,i.funcao,i.horario,i.coordenador,i.pausa1,i.pausa3,i.intervalo,i.saida,i.equipe;