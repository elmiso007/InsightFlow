-- ======================================================================
-- Tabela: gravacoes_telefone
-- Schema: lw_octadesk (PG17)
-- Propósito: Armazena gravações telefônicas com transcrição de áudio.
--            Pipeline A escreve (transcricao_*).
--            Pipeline B (Feedback Woz-Analista) lê WHERE transcricao_texto IS NOT NULL.
-- ======================================================================

CREATE TABLE IF NOT EXISTS lw_octadesk.gravacoes_telefone (
    -- Identificação da gravação
    id               BIGSERIAL       NOT NULL,
    call_id          TEXT            NOT NULL,          -- ID único da gravação no Yeastar
    arquivo_original TEXT,                              -- nome do arquivo no PBX

    -- Temporalidade da chamada
    iniciada_em      TIMESTAMPTZ     NOT NULL,
    encerrada_em     TIMESTAMPTZ,
    duracao_segundos INTEGER,

    -- Identificação do agente
    ramal_agente     TEXT,                              -- ramal (extensão) do analista
    agente           TEXT,                              -- nome do analista (quando disponível)

    -- Transcrição (preenchida pela Pipeline A)
    transcricao_texto  TEXT,                            -- texto plano para exibição e análise
    transcricao_raw    JSONB,                           -- JSON completo com segmentos e timestamps
    transcricao_idioma TEXT,                            -- idioma detectado pelo Whisper
    transcricao_modelo TEXT,                            -- modelo Whisper utilizado

    -- NPS (preenchida pela Pipeline A — originadas de perg1/perg2/perg3 em contatos_telefone)
    nps_velocidade    NUMERIC(5,2),
    nps_solucao       NUMERIC(5,2),
    nps_relacionamento NUMERIC(5,2),
    classificacao_nps TEXT,                            -- 'Promotor', 'Neutro', 'Detrator' — preenchida pela Pipeline B

    -- Controle
    criado_em        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- Constraints
    PRIMARY KEY (id),
    UNIQUE (call_id)
);

-- Índice para busca por período (usado pela Pipeline B)
CREATE INDEX IF NOT EXISTS idx_gravacoes_iniciada_em
    ON lw_octadesk.gravacoes_telefone (iniciada_em DESC);

-- Índice para busca por analista + período
CREATE INDEX IF NOT EXISTS idx_gravacoes_agente_iniciada
    ON lw_octadesk.gravacoes_telefone (agente, iniciada_em DESC);

-- Índice para busca por ramal + período
CREATE INDEX IF NOT EXISTS idx_gravacoes_ramal_iniciada
    ON lw_octadesk.gravacoes_telefone (ramal_agente, iniciada_em DESC);

-- Full-text search sobre a transcrição (gerado automaticamente)
-- Descomente após confirmar versão do PostgreSQL e necessidade de FTS:
-- ALTER TABLE lw_octadesk.gravacoes_telefone
--     ADD COLUMN IF NOT EXISTS transcricao_tsv TSVECTOR
--     GENERATED ALWAYS AS (to_tsvector('portuguese', COALESCE(transcricao_texto, ''))) STORED;
--
-- CREATE INDEX IF NOT EXISTS idx_gravacoes_fts
--     ON lw_octadesk.gravacoes_telefone USING GIN (transcricao_tsv);

COMMENT ON TABLE  lw_octadesk.gravacoes_telefone IS 'Gravações telefônicas com transcrição via faster-whisper. Alimentada pela Pipeline A (Carga de Áudios).';
COMMENT ON COLUMN lw_octadesk.gravacoes_telefone.call_id IS 'ID único da gravação no Yeastar PBX — chave de idempotência da pipeline.';
COMMENT ON COLUMN lw_octadesk.gravacoes_telefone.transcricao_raw IS 'JSON com segmentos, timestamps, idioma e probabilidade retornados pelo Whisper.';