INSERT INTO lw_octadesk.login_do_cliente
  (chat_id, login_usuario, customer_id, data_ultima_interacao,qtd_interacoes,motivo_de_contato,nivel1,nivel2,nivel3,nivel4,nivel5,
   lista_agentes,agente1,agente2,agente3,agente4,agente5,agente6,agente7,agente8,agente9,agente10,from_number,from_name,to_number,fonte_de_dados, data_insercao, data_modificacao)
 SELECT
  chat_id,
  login_usuario,
  customer_id,
  data_ultima_interacao,
  qtd_interacoes,
  motivo_de_contato,
  nivel1,
  nivel2,
  nivel3,
  nivel4,
  nivel5, 
  lista_agentes,
  agente1,
  agente2,
  agente3,
  agente4,
  agente5,
  agente6,
  agente7,
  agente8,
  agente9,
  agente10,
  from_number,
  from_name,
  to_number,
  fonte_de_dados,
  data_insercao,
  data_modificacao
FROM lw_octadesk.stg_login_do_cliente B
WHERE NOT EXISTS (
  SELECT 1
  FROM lw_octadesk.login_do_cliente L
  WHERE L.chat_id = B.chat_id
);
