UPDATE octadesk.classificacoes I
SET  
data_ultima_interacao = B.data_ultima_interacao,
contact_id = B.contact_id,
contact_name = B.contact_name,
contact_email = B.contact_email,
organization_number = B.organization_number,
organization_name = B.organization_name,
top_mrr_atritado = B.top_mrr_atritado,
tipo_uso_pri = B.tipo_uso_pri,
tipo_uso_sec = B.tipo_uso_sec,
plano = B.plano,
mrr = B.mrr,
codigo_do_plano = B.codigo_do_plano,
motivo_de_contato_name = B.motivo_de_contato_name,
motivo_de_contato = B.motivo_de_contato,
nivel1 = B.nivel1,
nivel2 = B.nivel2,
nivel3 = B.nivel3,
nivel4 = B.nivel4,
nivel5 = B.nivel5,
data_modificacao = B.data_modificacao
FROM octadesk.stg_classificacoes B
WHERE I.chat_id = B.chat_id AND B.data_ultima_interacao > I.data_ultima_interacao ;
