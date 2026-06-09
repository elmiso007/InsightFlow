--CRIAÇÃO DO UPDATE TABELA FINAL

UPDATE lwsa.service_now_problems I
SET
numero = SI.numero,
organizacao = SI.organizacao,
task_for = SI.task_for,
servidor = SI.servidor,
grupo_designado = SI.grupo_designado,
designado_para = SI.designado_para,
prioridade = SI.prioridade,
produto = SI.produto,
categoria = SI.categoria,
subcategoria = SI.subcategoria,
status = SI.status,
origem = SI.origem,
data_abertura = SI.data_abertura,
aberto_por = SI.aberto_por,
data_encerrado = SI.data_encerrado,
fechado_por = SI.fechado_por,
codigo_encerramento = SI.codigo_encerramento,
chamado_externo = SI.chamado_externo,
prb_revisado = SI.prb_revisado,
descricao_curta = SI.descricao_curta,
descricao = SI.descricao,
solucao_alternativa = SI.solucao_alternativa,
fechamento = SI.fechamento,
atualizacoes = SI.atualizacoes,
id_departamento = SI.id_departamento,
tipo_usuario = SI.tipo_usuario,
fonte_de_dados = SI.fonte_de_dados,
data_modificacao = NOW()
FROM lwsa.stg_service_now_problems SI
WHERE
 I.numero = SI.numero
AND SI.atualizacoes > I.atualizacoes