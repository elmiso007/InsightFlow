INSERT INTO kinghost.classificacoes (
    	idHistorico,
	idCliente,
	id_sessao,
	servicoLw,
	servicoTipoLw,
    	plano,
	data_hora_historico,
	analista,
	login_cliente,
	nome_cliente,
	canal,
	nivel1,
	nivel2,
	nivel3,
	nivel4,
	nivel5,
	produto,
	setor,
	rede,
	chat_id,
	data_inicio_interacao,
    data_fim_interacao,
	fonte_de_dados,
	data_insercao,
	data_modificacao
) 
SELECT
SI.idHistorico,
SI.idCliente,
SI.id_sessao AS id_sessao,
SI.servicoLw,
SI.servicoTipoLw,
SI.plano,
SI.data_hora_historico,
SI.analista,
SI.login_cliente,
SI.nome_cliente,
SI.canal,
SI.nivel1,
SI.nivel2,
SI.nivel3,
SI.nivel4,
SI.nivel5,
NULL AS produto,
SI.setor, 
SI.rede,
SI.chat_id,
SI.data_inicio_interacao,
SI.data_fim_interacao,
'D-1' AS fonte_de_dados,
NOW() AS data_insercao,
NOW() AS data_modificacao
FROM kinghost.stgclassificacoes SI
WHERE NOT EXISTS (
    SELECT 1
    FROM kinghost.classificacoes IB
    WHERE IB.idHistorico = SI.idHistorico
    AND SI.id_sessao = IB.id_sessao
);