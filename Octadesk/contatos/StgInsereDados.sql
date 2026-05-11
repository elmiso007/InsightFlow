INSERT INTO octadesk.stgcontatos 
    SELECT 
        a.contact_id::VARCHAR,
        CASE 
            WHEN LENGTH(a.contact_name) > 255 THEN NULL 
            ELSE REGEXP_REPLACE(a.contact_name, '[^\u0000-\u007F]', '', 'g')
        END AS contact_name,
        contact_email::VARCHAR,
        NULLIF(a.country_code::VARCHAR,'') AS country_code,
        NULLIF(a.telefone::VARCHAR,'') AS telefone,
        a.numeros_tel::JSON,
        NULLIF(a.chat_id::VARCHAR,'') AS chat_id,
        NULLIF(a.subdominio_octadesk::VARCHAR,'') AS subdominio_octadesk,
        NULLIF(a.nome_da_empresa,'') AS nome_da_empresa,
        NULLIF(REGEXP_REPLACE(a.cnpj, '[./-]', '', 'g'), '') AS cnpj,
        CASE 
        	WHEN LENGTH(NULLIF(REGEXP_REPLACE(a.v2_cnpj, '[./-]', '', 'g'), '')) > 15 THEN NULL
        	ELSE v2_cnpj
        END AS v2_cnpj,
        NULLIF(a."cluster",'') AS "cluster",
        CASE 
        	WHEN LENGTH(NULLIF(a.id_do_contato_no_hubspot,'')) > 50 THEN NULL 
        END AS id_do_contato_no_hubspot,
        NULLIF(a.periodo_de_onboarding,'') AS periodo_de_onboarding,
        NULLIF(a.cs_responsavel,'') AS cs_responsavel,
        NULLIF(a.organization_id,'') AS organization_id,
        NULLIF(a.organization_name,'') AS organization_name,
        'API Contacts Octadesk' AS fonte_de_dados,
        NOW() AS data_insercao,
        Now() AS data_modificacao
    FROM octadesk.rawdata_contacts a