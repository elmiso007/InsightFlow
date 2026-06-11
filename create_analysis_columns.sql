-- ============================================================================
-- SCRIPT PARA ADICIONAR COLUNAS DE SEÇÕES NA TABELA DE ANÁLISE NPS
-- ============================================================================
-- 
-- Este script deve ser executado pelo PROPRIETÁRIO da tabela no PostgreSQL
-- para adicionar as colunas específicas para cada seção da análise de IA
--
-- Data: 2025-10-06
-- Objetivo: Estruturar análises de NPS por seções específicas
-- ============================================================================

-- IMPORTANTE: Execute como proprietário da tabela no PostgreSQL

-- 1. Adicionar colunas para seções da análise IA na tabela RAW
ALTER TABLE kinghost_octadesk.rawdata_analise_nps_analistas 
ADD COLUMN IF NOT EXISTS resumo_geral TEXT,
ADD COLUMN IF NOT EXISTS problemas_nps TEXT,
ADD COLUMN IF NOT EXISTS padroes_comportamentais TEXT,
ADD COLUMN IF NOT EXISTS comentarios_vs_conversas TEXT,
ADD COLUMN IF NOT EXISTS recomendacoes_melhoria TEXT,
ADD COLUMN IF NOT EXISTS casos_criticos TEXT;

-- 2. Adicionar comentários para documentar as colunas
COMMENT ON COLUMN kinghost_octadesk.rawdata_analise_nps_analistas.resumo_geral IS 'Seção: Resumo Geral da análise IA';
COMMENT ON COLUMN kinghost_octadesk.rawdata_analise_nps_analistas.problemas_nps IS 'Seção: Problemas Identificados por Dimensão NPS';
COMMENT ON COLUMN kinghost_octadesk.rawdata_analise_nps_analistas.padroes_comportamentais IS 'Seção: Padrões Comportamentais dos Analistas';
COMMENT ON COLUMN kinghost_octadesk.rawdata_analise_nps_analistas.comentarios_vs_conversas IS 'Seção: Comentários NPS vs Conversas';
COMMENT ON COLUMN kinghost_octadesk.rawdata_analise_nps_analistas.recomendacoes_melhoria IS 'Seção: Recomendações de Melhoria';
COMMENT ON COLUMN kinghost_octadesk.rawdata_analise_nps_analistas.casos_criticos IS 'Seção: Casos Críticos';

-- 3. Opcional: Adicionar as mesmas colunas na tabela definitiva
-- ALTER TABLE kinghost_octadesk.analise_nps_analistas 
-- ADD COLUMN IF NOT EXISTS resumo_geral TEXT,
-- ADD COLUMN IF NOT EXISTS problemas_nps TEXT,
-- ADD COLUMN IF NOT EXISTS padroes_comportamentais TEXT,
-- ADD COLUMN IF NOT EXISTS comentarios_vs_conversas TEXT,
-- ADD COLUMN IF NOT EXISTS recomendacoes_melhoria TEXT,
-- ADD COLUMN IF NOT EXISTS casos_criticos TEXT;

-- 4. Verificar se as colunas foram criadas
SELECT 
    column_name, 
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'rawdata_analise_nps_analistas' 
  AND table_schema = 'kinghost_octadesk'
  AND column_name IN (
      'resumo_geral', 
      'problemas_nps', 
      'padroes_comportamentais',
      'comentarios_vs_conversas', 
      'recomendacoes_melhoria', 
      'casos_criticos'
  )
ORDER BY column_name;

-- ============================================================================
-- INSTRUÇÕES DE USO:
-- ============================================================================
-- 
-- 1. Conecte-se ao PostgreSQL como proprietário da tabela
-- 2. Execute este script completo
-- 3. Execute novamente a aplicação Python
-- 4. A aplicação detectará automaticamente as novas colunas e salvará
--    as seções estruturadas
-- 
-- RESULTADO ESPERADO:
-- - 6 novas colunas criadas na tabela
-- - Análises futuras salvas com seções separadas
-- - Possibilidade de queries específicas por seção
-- 
-- EXEMPLO DE QUERY APÓS IMPLEMENTAÇÃO:
-- SELECT 
--     analistas_criticos,
--     resumo_geral,
--     casos_criticos
-- FROM kinghost_octadesk.rawdata_analise_nps_analistas 
-- WHERE DATE(created_at) = CURRENT_DATE
-- ORDER BY created_at DESC;
-- 
-- ============================================================================
