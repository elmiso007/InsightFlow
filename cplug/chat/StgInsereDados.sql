INSERT INTO cplug.stg_chat
SELECT 
    distinct
    id::VARCHAR,
    protocolo::BIGINT,
    agent_id::VARCHAR,
    LOWER(NULLIF(agent_name::VARCHAR, '')) AS agent_name,
    NULLIF(agent_email::VARCHAR, '') AS agent_email,
    canal::VARCHAR,
	data_inicio_interacao::TIMESTAMP(0) AS data_inicio_interacao,
    data_ultima_interacao::TIMESTAMP,
    data_fim_interacao::TIMESTAMP, 
    EXTRACT(EPOCH FROM (CAST(data_fim_interacao AS TIMESTAMP) - CAST(atribuicao_agente AS TIMESTAMP))) AS tempo_atendimento_segundos,
    (CAST(data_fim_interacao AS TIMESTAMP) - CAST(atribuicao_agente AS TIMESTAMP)) AS tempo_atendimento_formatado,
    CASE 
        WHEN LENGTH(contact_name) > 255 THEN NULL 
        ELSE REGEXP_REPLACE(contact_name, '[^\u0000-\u007F]', '', 'g')
    END AS contact_name,
    CASE 
        WHEN LENGTH(contact_id) < 4 THEN NULL 
        ELSE contact_id
    END AS contact_id,
    CASE 
        WHEN REGEXP_REPLACE(contact_name, '[^\u0000-\u007F]', '', 'g') = agent_name THEN 'lw_octadesk'
        ELSE 'Cliente'
    END AS iniciado_por,
    tags::TEXT ,
    NULLIF(UPPER(SPLIT_PART(REGEXP_REPLACE(tags, '[{}"]', '', 'g'), ',', 1)), '') AS tag_1,
    NULLIF(UPPER(SPLIT_PART(REGEXP_REPLACE(tags, '[{}"]', '', 'g'), ',', 2)), '') AS tag_2,
    NULLIF(UPPER(SPLIT_PART(REGEXP_REPLACE(tags, '[{}"]', '', 'g'), ',', 3)), '') AS tag_3,
    NULLIF(UPPER(SPLIT_PART(REGEXP_REPLACE(tags, '[{}"]', '', 'g'), ',', 4)), '') AS tag_4,
    NULLIF(UPPER(SPLIT_PART(REGEXP_REPLACE(tags, '[{}"]', '', 'g'), ',', 5)), '') AS tag_5,
    com_bot::BOOLEAN,
    status::VARCHAR,
    grupo_id::VARCHAR,
    grupo_nome::VARCHAR,
    nao_lidas::BOOLEAN,
    EXTRACT(EPOCH FROM (CAST(atribuicao_agente AS TIMESTAMP) - CAST(atribuicao_grupo AS TIMESTAMP))) AS tempo_espera,
    EXTRACT(EPOCH FROM (CAST(data_fim_interacao AS TIMESTAMP) - CAST(data_inicio_interacao_agente AS TIMESTAMP))) AS tempo_atendimento_analista,
    origem::VARCHAR,
    bot_name::VARCHAR,
    conversation_origin::VARCHAR,
    status_detail::VARCHAR,
    data_inicio_interacao_agente::TIMESTAMP,
    atribuicao_agente::TIMESTAMP,
    atribuicao_grupo::TIMESTAMP,
    pesquisa::VARCHAR,
    NULLIF(comentario::TEXT, '') AS comentario,
    bot_contact_started_at::timestamptz AS bot_contact_started_at,
    bot_assigned_at::timestamptz AS bot_assigned_at,
    NULLIF(TRIM(bot_id), '')::VARCHAR AS bot_id,
    bot_transferred_to_human_at::timestamptz AS bot_transferred_to_human_at,
    bot_resolved_by_bot::BOOLEAN AS bot_resolved_by_bot,
    'API Pública - Endpoint /chat' AS fonte_de_dados,
    NOW() AS data_insercao,
    NOW() AS data_modificacao
FROM cplug.payload_chat r;
