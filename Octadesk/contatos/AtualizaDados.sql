UPDATE octadesk.contatos I
SET 
contact_name = SI.contact_name,
contact_email = SI.contact_email,
numeros_tel = SI.numeros_tel,
chat_id = SI.chat_id,
subdominio_octadesk = SI.subdominio_octadesk,
nome_da_empresa = SI.nome_da_empresa,
cnpj = SI.cnpj,
v2_cnpj = SI.v2_cnpj,
"cluster" = SI."cluster",
id_do_contato_no_hubspot = SI.id_do_contato_no_hubspot,
periodo_de_onboarding = SI.periodo_de_onboarding,
cs_responsavel = SI.cs_responsavel,
organization_id = SI.organization_id ,
organization_name = SI.organization_name,
data_modificacao = now()
FROM octadesk.stgcontatos SI
WHERE 
 I.contact_id = SI.contact_id