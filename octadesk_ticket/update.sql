UPDATE octadesk.stickets s 
SET 
ticket = a.ticket,
data_entrada = a.data_entrada,
data_resolucao = a.data_resolucao,
titulo_ticket = a.titulo_ticket,
usuario_criador_ticket = a.usuario_criador_ticket,
status = a.status,
grupo_responsavel = a.grupo_responsavel,
responsavel_ticket = a.responsavel_ticket,
tags_ticket = a.tags_ticket,
total_de_interacoes = a.total_de_interacoes
FROM octadesk.stg_ticketscriados a 
WHERE s.ticket = a.ticket AND a.total_de_interacoes >s.total_de_interacoes