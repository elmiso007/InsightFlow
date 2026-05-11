-- ==================================================================================
-- SCRIPT PARA CRIAÇÃO DAS TABELAS NECESSÁRIAS PARA O SISTEMA DE ANÁLISE NPS
-- COMPATÍVEL COM POSTGRESQL
-- ==================================================================================

-- Criar schema se não existir
CREATE SCHEMA IF NOT EXISTS kinghost_octadesk;

-- 1. TABELA PARA DADOS BRUTOS DA ANÁLISE DE IA (RAW DATA)
-- Esta tabela recebe diretamente os dados da API do Gemini
CREATE TABLE kinghost_octadesk.rawdata_analise_nps_analistas (
    id BIGSERIAL PRIMARY KEY,
    request TIMESTAMP NOT NULL,                   -- Data/hora da requisição
    dados_de DATE NOT NULL,                       -- Data inicial do período analisado
    dados_ate DATE NOT NULL,                      -- Data final do período analisado
    lista_protocolos TEXT,                        -- JSON com lista de protocolos
    analistas_criticos TEXT NOT NULL,            -- Nomes dos analistas com NPS baixo
    analise VARCHAR(100) NOT NULL,               -- Tipo de análise: 'monitoramento_nps_analistas'
    setor VARCHAR(100) DEFAULT 'Todos os setores', -- Setor analisado
    input_text TEXT NOT NULL,                    -- Prompt enviado para a IA
    request_id VARCHAR(100) UNIQUE NOT NULL,     -- ID único da requisição
    resposta_json TEXT,                          -- Resposta completa em JSON
    resposta_text TEXT NOT NULL,                 -- Resposta em texto da IA
    token_prompt INTEGER DEFAULT 0,             -- Tokens usados no prompt
    token_completion INTEGER DEFAULT 0,         -- Tokens usados na resposta
    model VARCHAR(50) DEFAULT 'gemini-pro',     -- Modelo de IA utilizado
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Data de criação do registro
);

-- Índices para performance na tabela rawdata
CREATE INDEX IX_rawdata_nps_request_date ON kinghost_octadesk.rawdata_analise_nps_analistas (request);
CREATE INDEX IX_rawdata_nps_periodo ON kinghost_octadesk.rawdata_analise_nps_analistas (dados_de, dados_ate);
CREATE INDEX IX_rawdata_nps_request_id ON kinghost_octadesk.rawdata_analise_nps_analistas (request_id);

-- 2. TABELA DEFINITIVA (Para dados processados e limpos)
-- Esta tabela recebe dados tratados da tabela RAW através do script insereDadosAnaliseNPS.sql
CREATE TABLE kinghost_octadesk.analise_nps_analistas (
    id BIGSERIAL PRIMARY KEY,
    request_datetime TIMESTAMP NOT NULL,         -- Data/hora da requisição original
    data_inicio DATE NOT NULL,                   -- Data inicial do período
    data_fim DATE NOT NULL,                      -- Data final do período
    analistas_criticos TEXT NOT NULL,           -- Lista de analistas com problema
    lista_protocolos TEXT,                      -- Lista de protocolos analisados (JSON ou texto)
    total_protocolos INTEGER DEFAULT 0,         -- Número total de protocolos analisados
    analise_tipo VARCHAR(100) NOT NULL,         -- Tipo de análise realizada
    setor VARCHAR(100),                         -- Setor dos analistas
    prompt_enviado TEXT,                        -- Prompt que foi enviado à IA
    request_id VARCHAR(100) UNIQUE NOT NULL,    -- ID único da requisição
    resposta_completa TEXT NOT NULL,            -- Resposta completa da IA
    
    -- Seções estruturadas da análise de IA
    resumo_geral TEXT,                          -- Seção: Resumo Geral da análise
    problemas_nps TEXT,                         -- Seção: Problemas Identificados por Dimensão NPS
    padroes_comportamentais TEXT,               -- Seção: Padrões Comportamentais dos Analistas
    comentarios_vs_conversas TEXT,              -- Seção: Comentários NPS vs Conversas
    recomendacoes_melhoria TEXT,                -- Seção: Recomendações de Melhoria
    casos_criticos TEXT,                        -- Seção: Casos Críticos
    
    tokens_prompt INTEGER DEFAULT 0,           -- Tokens do prompt
    tokens_resposta INTEGER DEFAULT 0,         -- Tokens da resposta
    modelo_ia VARCHAR(50),                      -- Modelo de IA usado
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Data de processamento
);

-- Índices para performance e consultas na tabela definitiva
CREATE INDEX IX_analise_nps_data_periodo ON kinghost_octadesk.analise_nps_analistas (data_inicio, data_fim);
CREATE INDEX IX_analise_nps_request_datetime ON kinghost_octadesk.analise_nps_analistas (request_datetime);
CREATE INDEX IX_analise_nps_analistas ON kinghost_octadesk.analise_nps_analistas (analistas_criticos);
CREATE INDEX IX_analise_nps_tipo ON kinghost_octadesk.analise_nps_analistas (analise_tipo);
CREATE INDEX IX_analise_nps_created_at ON kinghost_octadesk.analise_nps_analistas (created_at);

-- ==================================================================================
-- COMENTÁRIOS E OBSERVAÇÕES
-- ==================================================================================

-- FLUXO DE DADOS:
-- 1. analise_ia.py salva dados brutos em 'rawdata_analise_nps_analistas'
-- 2. insereDadosAnaliseNPS.sql processa e move dados para 'analise_nps_analistas'
-- 3. A tabela definitiva tem dados limpos e estruturados para relatórios

-- CAMPOS IMPORTANTES:
-- • analistas_criticos: String com nomes separados por vírgula
-- • lista_protocolos: JSON com array de protocolos analisados
-- • request_id: UUID único para evitar duplicatas
-- • resposta_completa: Markdown completo com análise da IA
-- • resumo_geral, problemas_nps, padroes_comportamentais, etc: Seções estruturadas da análise
-- • total_protocolos: Calculado automaticamente via JSON_ARRAY_LENGTH

-- MANUTENÇÃO:
-- • Execute insereDadosAnaliseNPS.sql periodicamente para processar dados brutos
-- • Monitore o crescimento das tabelas e implemente rotinas de limpeza se necessário
-- • A tabela RAW pode acumular dados; considere arquivamento após processamento

-- Log de criação
DO $$
BEGIN
    RAISE NOTICE '✅ Tabelas para análise NPS criadas com sucesso!';
    RAISE NOTICE '📊 kinghost_octadesk.rawdata_analise_nps_analistas - Para dados brutos da IA';
    RAISE NOTICE '📈 kinghost_octadesk.analise_nps_analistas - Para dados processados e relatórios';
END $$;
