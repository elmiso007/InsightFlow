INSERT INTO lwsa.stg_service_now_problems
(numero,
organizacao,
task_for,
servidor,
grupo_designado,
designado_para,
prioridade,
produto,
categoria,
subcategoria,
status,
origem,
data_abertura,
aberto_por,
data_encerrado,
fechado_por,
codigo_encerramento,
chamado_externo,
prb_revisado,
descricao_curta,
descricao,
solucao_alternativa,
fechamento,
atualizacoes,
id_departamento,
tipo_usuario,
fonte_de_dados,
data_insercao,
data_modificacao
)
SELECT
 distinct
 numero::VARCHAR,
 organizacao::VARCHAR,
 NULLIF(task_for::VARCHAR, '') AS task_for,
 NULLIF(servidor::VARCHAR, '') AS servidor,
 NULLIF(grupo_designado::VARCHAR, '') AS grupo_designado,
 NULLIF(designado_para::VARCHAR, '') AS designado_para,
 prioridade::VARCHAR,
 NULLIF(produto::VARCHAR, '') AS produto,
 NULLIF(categoria::VARCHAR, '') AS categoria,
 NULLIF(subcategoria::VARCHAR, '') AS subcategoria,
 status::VARCHAR,
 NULLIF(origem::VARCHAR, '') AS origem,
 CASE WHEN data_abertura = '' THEN NULL
  ELSE TO_TIMESTAMP(data_abertura, 'DD/MM/YYYY HH24:MI:SS')
 END AS data_abertura,
 aberto_por::VARCHAR,
 CASE WHEN data_encerrado = '' THEN NULL
  ELSE TO_TIMESTAMP(data_encerrado, 'DD/MM/YYYY HH24:MI:SS')
 END AS data_encerrado,
 NULLIF(fechado_por::VARCHAR, '') AS fechado_por,
 NULLIF(codigo_encerramento::VARCHAR, '') AS codigo_encerramento,
 NULLIF(chamado_externo::VARCHAR, '') AS chamado_externo,
 NULLIF(prb_revisado::VARCHAR, '') AS prb_revisado,
 descricao_curta::TEXT,
 descricao::TEXT,
 NULLIF(solucao_alternativa::TEXT, '') AS solucao_alternativa,
 NULLIF(fechamento::TEXT, '') AS fechamento,
 NULLIF(translate(atualizacoes, ',', ''), '')::INTEGER AS atualizacoes,
 id_departamento::VARCHAR,
 CASE
  WHEN aberto_por ilike '%Integração%' THEN 'Integração'
  ELSE 'Nominal'
 END AS tipo_usuario,
 'API Service-Now - Endpoint /api/now/table/problem' AS fonte_de_dados,
 NOW() AS data_insercao,
 NOW() AS data_modificacao
FROM lwsa.rawdata_service_now_problems r;