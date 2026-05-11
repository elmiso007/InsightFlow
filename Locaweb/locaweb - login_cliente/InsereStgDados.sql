INSERT INTO lw_octadesk.stg_login_do_cliente
  (chat_id, login_usuario, customer_id, data_ultima_interacao, qtd_interacoes,motivo_de_contato,nivel1,nivel2,nivel3,nivel4,nivel5, fonte_de_dados, data_insercao, data_modificacao)
 SELECT
  B.id::VARCHAR,
  NULLIF(BTRIM(B.login_usuario::text), '') AS login_usuario,
  NULLIF(BTRIM(B.customer_id::text), '')  AS customer_id,
  B.data_ultima_interacao,
  B.messages_count::INTEGER as qtd_interacoes,
  B.motivo_de_contato::VARCHAR as motivo_de_contato,
  NULLIF(TRIM(SPLIT_PART(REGEXP_REPLACE(B.motivo_de_contato, '[{}"\[\]\*]', '', 'g'), '>', 1)), '') AS nivel1,
  NULLIF(TRIM(SPLIT_PART(REGEXP_REPLACE(B.motivo_de_contato, '[{}"\[\]\*]', '', 'g'), '>', 2)), '') AS nivel2,
  NULLIF(TRIM(SPLIT_PART(REGEXP_REPLACE(B.motivo_de_contato, '[{}"\[\]\*]', '', 'g'), '>', 3)), '') AS nivel3,
  NULLIF(TRIM(SPLIT_PART(REGEXP_REPLACE(B.motivo_de_contato, '[{}"\[\]\*]', '', 'g'), '>', 4)), '') AS nivel4,
  NULLIF(TRIM(SPLIT_PART(REGEXP_REPLACE(B.motivo_de_contato, '[{}"\[\]\*]', '', 'g'), '>', 5)), '') AS nivel5,
  'Endpoint /chat/id' AS fonte_de_dados,
  NOW() AS data_insercao,
  NOW() AS data_modificacao
FROM lw_octadesk.rawdata_login_do_cliente B