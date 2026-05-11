UPDATE public.contact_rate_kinghost B
SET 
    Clientes = A.contratos,
    Contatos = A.contatos,
    "Contact Rate (%)" = A.contactrate,
    data_modificacao = NOW()
FROM public.stg_contact_rate_kinghost A
WHERE 
    B.AnoMes = A.data
    AND (
        B.Clientes IS DISTINCT FROM A.contratos
        OR B.Contatos IS DISTINCT FROM A.contatos
        OR B."Contact Rate (%)" IS DISTINCT FROM A.contactrate
    );
