SELECT 
    CAST(protocolo AS BIGINT) AS protocolo,
    CASE WHEN agentlogin = 'nan' THEN NULL ELSE agentlogin END AS login_agente,
    calltype AS fila,
    REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(guest, 'Ã¡', 'á'), 'Ã¢', 'â'), 'Ã£', 'ã'), 'Ã©', 'é'), 'Ã§', 'ç'), 'ÃA', 'É'), 'Ã¶', 'ö'), 'Ãº', 'ú'), 'Ã³', 'ó'), 'Ã­', 'í'), 'Ã¼', 'u') AS cliente,
    CASE WHEN email LIKE '%@%' THEN email ELSE NULL END AS email,
    CASE WHEN email LIKE '%@%' THEN NULL ELSE email END AS telefone_1,
    CASE WHEN fone = 'nan' THEN NULL ELSE fone END AS telefone_2,
    navigator AS navegador,
    to_timestamp(datestartedinteraction, 'DD/MM/YYYY HH24:MI:SS') - INTERVAL '3 HOURS' AS data_inicio_interacao,
    CASE WHEN datedivertedinteraction = 'nan' THEN NULL ELSE to_timestamp(datedivertedinteraction, 'DD/MM/YYYY HH24:MI:SS') END - INTERVAL '3 HOURS' AS data_desvio_interacao,
    CASE WHEN dateansweredinteraction = 'nan' THEN NULL ELSE to_timestamp(dateansweredinteraction, 'DD/MM/YYYY HH24:MI:SS') END - INTERVAL '3 HOURS' AS data_resposta_interacao,
    CASE WHEN datereleasedinteraction = 'nan' THEN NULL ELSE TO_TIMESTAMP(datereleasedinteraction, 'DD/MM/YYYY HH24:MI:SS') END - INTERVAL '3 HOURS' AS data_encerramento_ligacao,
    CAST(handletimeinteraction AS INT) AS duracao_atendimento,
    EXTRACT(EPOCH FROM (CASE WHEN dateansweredinteraction = 'nan' THEN NULL ELSE to_timestamp(dateansweredinteraction, 'DD/MM/YYYY HH24:MI:SS') END) - to_timestamp(datestartedinteraction, 'DD/MM/YYYY HH24:MI:SS')) as duracao_espera,
    steptypename AS status,
    CAST(countmsginteraction AS INT) AS quantidade_interacoes,
    CASE WHEN qualify1 = 'nan' THEN NULL ELSE qualify1 END AS nivel1,
    CASE WHEN qualify2 = 'nan' THEN NULL ELSE qualify2 END AS nivel2,
    CASE WHEN qualify3 = 'nan' THEN NULL ELSE qualify3 END AS nivel3,
    CASE WHEN qualify4 = 'nan' THEN NULL ELSE qualify4 END AS nivel4,
    CASE WHEN qualify5 = 'nan' THEN NULL ELSE qualify5 END AS nivel5,

    CASE 
        WHEN survey1 = 'nan' THEN NULL 
        WHEN regexp_replace(REPLACE(survey1, '.0', ''), '[0-9]', '', 'g') != '' THEN NULL 
        ELSE CAST(REPLACE(survey1, '.0', '') AS INT) 
    END AS p1,
    CASE 
        WHEN survey2 = 'nan' THEN NULL 
        WHEN regexp_replace(REPLACE(survey2, '.0', ''), '[0-9]', '', 'g') != '' THEN NULL 
        ELSE CAST(REPLACE(survey2, '.0', '') AS INT) 
    END AS p2,
    CASE 
        WHEN survey3 = 'nan' THEN NULL 
        WHEN regexp_replace(REPLACE(survey3, '.0', ''), '[0-9]', '', 'g') != '' THEN NULL 
        ELSE CAST(REPLACE(survey3, '.0', '') AS INT) 
    END AS p3,
    CASE WHEN survey4 = 'nan' THEN NULL ELSE survey4 END AS comentarios,

    CASE WHEN LENGTH(survey2) > 4 THEN survey2 END AS comentarios_2,
    CASE WHEN LENGTH(survey3) > 4 THEN survey3 END AS comentarios_3,
    CASE WHEN ud_1 = 'nan' THEN NULL ELSE ud_1 END AS login_cliente,
    CASE WHEN authrequest = 'nan' THEN NULL WHEN authrequest = 'SIM' THEN TRUE ELSE FALSE END AS autorizacao_requisitada,
    CASE WHEN authsuccess = 'nan' THEN NULL WHEN authsuccess = 'SIM' THEN TRUE ELSE FALSE END AS autorizacao_aceita,
    CASE WHEN autherror = 'nan' THEN NULL WHEN autherror = 'SIM' THEN TRUE ELSE FALSE END AS autorizacao_erro,
    CASE WHEN boleto = 'nan' THEN NULL WHEN boleto = 'Sim' THEN TRUE ELSE FALSE END AS boleto,
    mediasourcename AS canal,
    ip,
    to_Date(dateprocess, 'DD/MM/YYYY') AS data_processamento,
    to_timestamp(datefilecreation, 'DD/MM/YYYY HH24:MI:SS') - INTERVAL '3 HOURS' AS data_criacao_do_arquivo,
    CAST(sessionid AS INT) AS id_sessao,
    'D-1' AS fonte_de_dados    
FROM 
    teste.rawdata;
