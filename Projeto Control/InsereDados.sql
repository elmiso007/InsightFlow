INSERT INTO control_desk.mapa_operacional (
    login,
    matricula,
    status,
    equipe,
    skill,
    funcao,
    coordenador,
    horario,
    pausa1,
    intervalo,
    pausa3,
    saida,
    observacoes,
    id_slack,
    fonte_de_dados,
    data_insercao,
    data_modificacao
)
SELECT 
    lower(r.login::VARCHAR) AS login,
    CAST(r.matricula AS INTEGER) AS matricula ,
    r.status::VARCHAR,
    r.equipe::VARCHAR,
    r.skill::VARCHAR,
    r.funcao::VARCHAR,
    LOWER(r.coordenador::VARCHAR) AS coordenador,
    r.horario::TIME,
    r.pausa1::TIME,
    r.intervalo::TIME,
    r.pausa3::TIME,
    r.saida::TIME,
    r.observacoes::TEXT,
    r.id_slack::VARCHAR,
    'Mapa Operacional' AS fonte_de_dados,
    NOW() AS data_insercao,
    NOW() AS data_modificacao
FROM control_desk.rawdata r
WHERE NOT EXISTS (
    SELECT 1 
    FROM control_desk.mapa_operacional AS i
    WHERE i.matricula = CAST(r.matricula AS INTEGER)
)
RETURNING 
    id_slack,
    login,
    skill,
    funcao,
    horario,
    coordenador,
    pausa1,
    intervalo,
    pausa3,
    saida,
    equipe;
