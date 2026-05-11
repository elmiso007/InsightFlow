UPDATE kinghost.chat_backlog I
SET
    login_agente = SI.login_agente,
    fila = SI.fila,
    cliente = SI.cliente,
    email = SI.email,
    telefone_1 = SI.telefone_1,
    telefone_2 = SI.telefone_2,
    navegador = SI.navegador,
    data_inicio_interacao = SI.data_inicio_interacao,
    data_desvio_interacao = SI.data_desvio_interacao,
    data_resposta_interacao = SI.data_resposta_interacao,
    data_fim_interacao = SI.data_encerramento_interacao,
    tempo_espera = SI.duracao_espera,
    tempo_atendimento = SI.duracao_atendimento,
    status = SI.status,
    quantidade_interacoes = SI.quantidade_interacoes,
    nivel1 = SI.nivel1,	
    nivel2 = SI.nivel2,		
    nivel3 = SI.nivel3,	
    nivel4 = SI.nivel4,	
    nivel5 = SI.nivel5,	
    p1 = SI.p1::INTEGER,
    p2 = SI.p2::INTEGER,
    p3 = SI.p3::INTEGER,
    comentarios = SI.comentarios,
    login_cliente = SI.login_cliente,
    autorizacao_requisitada = SI.autorizacao_requisitada,
    autorizacao_aceita = SI.autorizacao_aceita,
    autorizacao_erro = SI.autorizacao_erro,
    boleto = SI.boleto,
    canal = SI.canal,
    ip = SI.ip,
    fonte_de_dados = SI.fonte_de_dados,
    data_criacao_do_arquivo = SI.data_criacao_do_arquivo,
    data_modificacao = NOW()
FROM teste.stginteracoes SI
WHERE SI.protocolo::varchar = I.protocolo AND
      SI.id_sessao::varchar = I.id_sessao AND  
      (SI.fila = I.fila OR I.status IN ('Em atendimento')) AND
      SI.data_inicio_interacao = I.data_inicio_interacao AND 
      (SI.duracao_atendimento > I.tempo_atendimento OR
      I.data_fim_interacao IS NULL);

