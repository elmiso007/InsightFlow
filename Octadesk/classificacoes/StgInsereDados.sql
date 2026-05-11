INSERT INTO octadesk.stg_classificacoes
SELECT  
chat_id::VARCHAR AS chat_id,
data_ultima_interacao::TIMESTAMP AS data_ultima_interacao,
NULLIF(contact_id::VARCHAR, '') AS contact_id,
CASE 
    WHEN LENGTH(contact_name) > 255 THEN NULL 
    ELSE REGEXP_REPLACE(contact_name, '[^\u0000-\u007F]', '', 'g')
END AS contact_name,
NULLIF(contact_email::VARCHAR, '') AS contact_email,
NULLIF(organization_number::VARCHAR, '')::INTEGER AS organization_number,
NULLIF(organization_name::VARCHAR, '') AS organization_name,
NULLIF(org_cf_topmrr_atritado::VARCHAR, '') AS top_mrr_atritado,
NULLIF(org_cf_tipo_uso_pri::VARCHAR, '') AS tipo_uso_pri,
NULLIF(org_cf_tipo_uso_sec::VARCHAR, '') AS tipo_uso_sec,
NULLIF(org_cf_plano::VARCHAR, '') AS plano,
NULLIF(REPLACE(REGEXP_REPLACE(org_cf_mrr::VARCHAR, '[^0-9,]', '', 'g'),',', '.'), '')::FLOAT AS mrr,
NULLIF(codigo_do_plano::VARCHAR, '')::INTEGER AS codigo_do_plano,
NULLIF(motivo_de_contato_name::VARCHAR, '') AS motivo_de_contato_name,
NULLIF(cf_motivo_de_contato::VARCHAR, '') AS motivo_de_contato,
NULLIF(TRIM(SPLIT_PART(REGEXP_REPLACE(cf_motivo_de_contato, '[{}"\[\]\*]', '', 'g'), '>', 1)), '') AS nivel1,
NULLIF(TRIM(SPLIT_PART(REGEXP_REPLACE(cf_motivo_de_contato, '[{}"\[\]\*]', '', 'g'), '>', 2)), '') AS nivel2,
NULLIF(TRIM(SPLIT_PART(REGEXP_REPLACE(cf_motivo_de_contato, '[{}"\[\]\*]', '', 'g'), '>', 3)), '') AS nivel3,
NULLIF(TRIM(SPLIT_PART(REGEXP_REPLACE(cf_motivo_de_contato, '[{}"\[\]\*]', '', 'g'), '>', 4)), '') AS nivel4,
NULLIF(TRIM(SPLIT_PART(REGEXP_REPLACE(cf_motivo_de_contato, '[{}"\[\]\*]', '', 'g'), '>', 5)), '') AS nivel5,
'Endpoint /chat/id' AS fonte_de_dados,
NOW() AS data_insercao,
NOW() AS data_modificacao
FROM octadesk.rawdata_classificacoes
