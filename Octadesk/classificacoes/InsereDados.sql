INSERT INTO octadesk.classificacoes
SELECT  
B.chat_id,
B.data_ultima_interacao,
B.contact_id,
B.contact_name,
B.contact_email,
B.organization_number,
B.organization_name,
B.top_mrr_atritado,
B.tipo_uso_pri,
B.tipo_uso_sec,
B.plano,
B.mrr,
B.codigo_do_plano,
B.motivo_de_contato_name,
B.motivo_de_contato,
B.nivel1,
B.nivel2,
B.nivel3,
B.nivel4,
B.nivel5,
B.fonte_de_dados,
B.data_insercao,
B.data_modificacao
FROM octadesk.stg_classificacoes B
WHERE NOT EXISTS (SELECT 1 FROM octadesk.classificacoes A WHERE A.chat_id = B.chat_id)