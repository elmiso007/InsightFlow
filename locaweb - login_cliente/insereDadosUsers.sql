INSERT INTO lw_octadesk.login_do_cliente
  (chat_id, login_usuario, customer_id, data_ultima_interacao,qtd_interacoes,motivo_de_contato,nivel1,nivel2,nivel3,nivel4,nivel5, fonte_de_dados, data_insercao, data_modificacao)
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
  fonte_de_dados,
  data_insercao,
  data_modificacao
FROM lw_octadesk.stg_login_do_cliente B
WHERE NOT EXISTS (
  SELECT 1
  FROM lw_octadesk.login_do_cliente L
  WHERE L.chat_id = B.chat_id
);
