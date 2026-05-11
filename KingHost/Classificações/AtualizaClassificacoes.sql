UPDATE kinghost.classificacoes AS TB
SET
idHistorico = CL.idHistorico, 
idCliente = CL.idCliente,
id_sessao = CL.id_sessao,
servicoLw = CL.servicoLw,
servicoTipoLw = CL.servicoTipoLw,
plano = CL.plano,
data_hora_historico = CL.data_hora_historico,
analista = CL.analista,
login_cliente = CL.login_cliente,
nome_cliente = CL.nome_cliente,
canal = CL.canal,
nivel1 = CL.nivel1,
nivel2 = CL.nivel2,
nivel3 = CL.nivel3,
nivel4 = CL.nivel4,
nivel5 = CL.nivel5,
produto = CL.produto,
setor = CL.setor,
rede = CL.rede,
chat_id = CL.chat_id,
data_inicio_interacao = CL.data_inicio_interacao,
data_fim_interacao = CL.data_fim_interacao,
fonte_de_dados = CL.fonte_de_dados,
data_modificacao = NOW()
FROM kinghost.stgclassificacoes CL
WHERE TB.idHistorico = CL.idHistorico and
TB.id_sessao = CL.id_sessao
;
