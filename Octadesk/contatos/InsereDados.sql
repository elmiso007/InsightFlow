
INSERT INTO octadesk.contatos 
SELECT DISTINCT 
	S.contact_id,
    S.contact_name,
    S.contact_email,
    S.country_code,
    S.telefone,
    S.numeros_tel,
    S.chat_id,
    S.subdominio_octadesk,
    S.nome_da_empresa,
    S.cnpj,
    S.v2_cnpj,
    S."cluster",
    S.id_do_contato_no_hubspot,
    S.periodo_de_onboarding,
    S.cs_responsavel,
    S.organization_id,
    S.organization_name,
    S.fonte_de_dados,
    S.data_insercao,
    S.data_modificacao
    FROM 
(SELECT 
    SI.contact_id,
    SI.contact_name,
    SI.contact_email,
    SI.country_code,
    SI.telefone,
    SI.numeros_tel::TEXT,
    SI.chat_id,
    SI.subdominio_octadesk,
    SI.nome_da_empresa,
    SI.cnpj,
    SI.v2_cnpj,
    SI."cluster",
    SI.id_do_contato_no_hubspot,
    SI.periodo_de_onboarding,
    SI.cs_responsavel,
    SI.organization_id,
    SI.organization_name,
    SI.fonte_de_dados,
    SI.data_insercao,
    SI.data_modificacao
FROM octadesk.stgcontatos SI) S
WHERE NOT EXISTS (SELECT 1 FROM octadesk.contatos I WHERE S.contact_id = I.contact_id);