INSERT INTO kinghost.interacoesbacklog
   (protocolo,id_sessao,login_agente,fila,cliente,email,telefone_1,telefone_2,navegador,data_inicio_interacao,data_desvio_interacao,data_resposta_interacao,
    data_fim_interacao,tempo_espera,tempo_atendimento,status,quantidade_interacoes,nivel1,nivel2,nivel3,nivel4,nivel5,login_cliente,autorizacao_requisitada,
    autorizacao_aceita,autorizacao_erro,boleto,canal,ip,data_criacao_do_arquivo,fonte_de_dados,data_insercao,data_modificacao, p1, p2, p3, comentarios)
SELECT 
    SI.protocolo,
    SI.id_sessao,
    SI.login_agente,
    SI.fila,
    SI.cliente,
    SI.email,
    SI.telefone_1,
    SI.telefone_2,
    SI.navegador,
    SI.data_inicio_interacao,
    SI.data_desvio_interacao,
    SI.data_resposta_interacao,
    SI.data_fim_interacao,
    SI.tempo_espera,
    SI.tempo_atendimento,
    SI.status,
    SI.quantidade_interacoes,
    SI.nivel1,
    SI.nivel2,
    SI.nivel3,
    SI.nivel4,
    SI.nivel5,
    SI.login_cliente,
    CAST(SI.autorizacao_requisitada AS BOOLEAN),
    CAST(SI.autorizacao_aceita AS BOOLEAN),
    CAST(SI.autorizacao_erro AS BOOLEAN),
    CAST(SI.boleto AS BOOLEAN),
    SI.canal,
    SI.ip,
    CAST(SI.data_criacao_do_arquivo AS TIMESTAMP),
    'H-2' AS fonte_de_dados,
    NOW() - INTERVAL '3 hour' AS data_insercao,
    NOW() - INTERVAL '3 hour' AS data_modificacao,
    SI.p1,
    SI.p2,
    SI.p3,
    SI.comentarios
FROM kinghost.stginteracoes SI
WHERE NOT EXISTS (
    SELECT 1
    FROM kinghost.interacoesbacklog IB
    WHERE SI.protocolo = IB.protocolo 
    AND SI.id_sessao = IB.id_sessao
);