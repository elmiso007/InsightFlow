INSERT INTO public.contact_rate_kinghost (
    AnoMes, Clientes, Contatos, "Contact Rate (%)", setor, data_insercao,data_modificacao
)
SELECT 
    A.data::VARCHAR,
    A.contratos::INTEGER,
    A.contatos::INTEGER,
    A.contactrate::NUMERIC(10, 4),
    'suporte',
    NOW(),
    NOW()
FROM public.stg_contact_rate_kinghost A
WHERE NOT EXISTS (
    SELECT 1 FROM public.contact_rate_kinghost B WHERE B.AnoMes = A.data
);
