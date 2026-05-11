INSERT INTO tray.login_do_cliente
  (chat_id, login_usuario, customer_id, data_ultima_interacao,qtd_interacoes,motivo_de_contato,nivel1,nivel2,nivel3,nivel4,nivel5,
   lista_agentes,from_number,from_name,to_number,fonte_de_dados, data_insercao, data_modificacao)
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
  from_number,
  from_name,
  to_number,
  fonte_de_dados,
  data_insercao,
  data_modificacao
FROM tray.stg_login_do_cliente B
WHERE NOT EXISTS (
  SELECT 1
  FROM tray.login_do_cliente L
  WHERE L.chat_id = B.chat_id
);
