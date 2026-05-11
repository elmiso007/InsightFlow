INSERT INTO octadesk.stickets 
(ticket,data_entrada,data_resolucao,titulo_ticket,usuario_criador_ticket,status,grupo_responsavel,responsavel_ticket,tags_ticket,total_de_interacoes)
SELECT 
	S.ticket::bigint,
	S.data_entrada::timestamp,
	S.data_resolucao::timestamp,
	S.titulo_ticket::text,
	S.usuario_criador_ticket::text,
	S.status::text,
	S.grupo_responsavel::text,
	S.responsavel_ticket::text,
	S.tags_ticket::text,
	S.total_de_interacoes::bigint
FROM octadesk.stg_ticketscriados S
WHERE NOT EXISTS(SELECT 1 FROM octadesk.stickets A WHERE A.ticket = S.ticket)