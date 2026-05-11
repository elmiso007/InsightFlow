INSERT INTO public.ch_login_logout_chat 
(analista, login, data_login, data_logout, tempo_em_pausa, tempo_logado)
SELECT 
    S.analista::varchar,
    S.login::varchar,
    S.data_login::timestamp,
    S.data_logout::timestamp,
    S.tempo_em_pausa::varchar,
    S.tempo_logado::varchar
FROM 
    public.stg_ch_login_logout_chat S
WHERE 
    S.analista NOT IN ('Giba', 'Giba 1', 'Giba 2', 'Giba 3', 'Giba 4', 'Giba 5');
