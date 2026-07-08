-- Script SQL para inserir dados da análise de NPS na tabela definitiva
-- Arquivo: insereDadosAnaliseNPS.sql
-- COMPATÍVEL COM POSTGRESQL

INSERT INTO lw_octadesk.analise_nps_analistas (
    id,
    request_datetime,
    data_inicio,
    data_fim,
    analistas_criticos,
    lista_protocolos,
    total_protocolos,
    analise_tipo,
    setor,
    prompt_enviado,
    request_id,
    resposta_completa,
    
    -- Seções estruturadas da análise
    resumo_geral,
    problemas_nps,
    padroes_comportamentais,
    comentarios_vs_conversas,
    recomendacoes_melhoria,
    casos_criticos,
    
    tokens_prompt,
    tokens_resposta,
    modelo_ia,
    created_at
)
SELECT 
    (SELECT COALESCE(MAX(id), 0) FROM lw_octadesk.analise_nps_analistas) + ROW_NUMBER() OVER (ORDER BY r.id) as id,
    r.request as request_datetime,
    r.dados_de as data_inicio,
    r.dados_ate as data_fim,
    LEFT(r.analistas_criticos, 500) as analistas_criticos,
    r.lista_protocolos as lista_protocolos,
    CASE 
        WHEN r.lista_protocolos IS NOT NULL AND r.lista_protocolos != '' 
        THEN LENGTH(r.lista_protocolos) - LENGTH(REPLACE(r.lista_protocolos, ',', '')) + 1
        ELSE 0 
    END as total_protocolos,
    LEFT(r.analise, 100) as analise_tipo,
    LEFT(r.setor, 100) as setor,
    r.input_text as prompt_enviado,
    r.request_id,
    r.resposta_text as resposta_completa,
    
    -- Seções estruturadas da análise (copiadas da rawdata)
    r.resumo_geral,
    r.problemas_nps,
    r.padroes_comportamentais,
    r.comentarios_vs_conversas,
    r.recomendacoes_melhoria,
    r.casos_criticos,
    
    r.token_prompt as tokens_prompt,
    r.token_completion as tokens_resposta,
    r.model as modelo_ia,
    CURRENT_TIMESTAMP as created_at
    
FROM lw_octadesk.rawdata_analise_nps_analistas r
WHERE r.request_id NOT IN (
    SELECT request_id 
    FROM lw_octadesk.analise_nps_analistas 
    WHERE request_id IS NOT NULL
);

-- Atualizar estatísticas da tabela (PostgreSQL)
ANALYZE lw_octadesk.analise_nps_analistas;

-- Log da execução
DO $$
DECLARE
    row_count INTEGER;
BEGIN
    GET DIAGNOSTICS row_count = ROW_COUNT;
    RAISE NOTICE 'Dados de análise NPS inseridos com sucesso na tabela definitiva.';
    RAISE NOTICE 'Total de registros processados: %', row_count;
END $$;
