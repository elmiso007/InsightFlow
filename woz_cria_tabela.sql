-- Tabela dedicada para comentários NPS que mencionam o WOZ/bot
-- Schema: lw_octadesk
-- Idempotência: ON CONFLICT (protocolo) DO NOTHING — o mesmo protocolo não é duplicado
-- Execute uma única vez no banco para criar a tabela.

CREATE TABLE IF NOT EXISTS lw_octadesk.woz_comentarios (
    id                  SERIAL PRIMARY KEY,
    data_insercao       TIMESTAMP           DEFAULT NOW(),
    protocolo           TEXT                NOT NULL,
    analista            TEXT,
    fila                TEXT,
    data_encerramento   TIMESTAMP,
    velocidade          NUMERIC(4,1),
    solucao             NUMERIC(4,1),
    relacionamento      NUMERIC(4,1),
    score_medio         NUMERIC(5,2),
    classificacao       TEXT,               -- Promotor | Neutro | Detrator | Sem nota
    comentario          TEXT,
    data_inicio_periodo DATE                NOT NULL,
    data_fim_periodo    DATE                NOT NULL,
    UNIQUE (protocolo, data_inicio_periodo, data_fim_periodo)
);

COMMENT ON TABLE  lw_octadesk.woz_comentarios                    IS 'Comentários NPS que mencionam atendimento automatizado (WOZ/bot). Populado por analise_woz_detratores.py.';
COMMENT ON COLUMN lw_octadesk.woz_comentarios.classificacao      IS 'Promotor (score>=9) | Neutro (7-8) | Detrator (<=6) | Sem nota';
COMMENT ON COLUMN lw_octadesk.woz_comentarios.data_inicio_periodo IS 'Início do período da análise que capturou este comentário';
COMMENT ON COLUMN lw_octadesk.woz_comentarios.data_fim_periodo    IS 'Fim do período da análise que capturou este comentário';
