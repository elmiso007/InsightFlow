INSERT INTO kinghost.chamados (
    idchamado,
    idefetivo,
    idcliente,
    categoriafila,
    fila,
    logincliente,
    abertopor,
    proprietario,
    equipeproprietaria,
    assunto,
    status,
    datainiciado,
    dataresolvido,
    agenteultimainteracao,
    criador,
    datacriacao,
    p1,
    p2,
    p3,
    comentarios,
    canal,
    origem,
    fontedados,
    quantidadedeinteracoeskinghost,
    quantidadedeinteracoescliente,
    quantidadeinteracoes,
    analista
)

WITH CTE_atendimentos_ordenados AS (
    SELECT 
        idchamado, idefetivo, idcliente, categoriafila, fila,
        logincliente, abertopor, proprietario, equipeproprietaria,
        assunto, status, datainiciado, dataresolvido, agenteultimainteracao,
        criador, datacriacao, p1, p2, p3, comentarios, canal, origem, fontedados, analista,
        ROW_NUMBER() OVER (PARTITION BY idchamado ORDER BY dataultimainteracao DESC) AS rn
    FROM kinghost.chamadosbacklog BK
    WHERE analista IS NOT NULL 
)
SELECT
    c.idchamado,
    MAX(c.idefetivo) AS idefetivo,
    MAX(c.idcliente) AS idcliente,
    MAX(a.categoriafila) AS categoriafila,
    MAX(a.fila) AS fila,
    MAX(a.logincliente) AS logincliente,
    MAX(a.abertopor) AS abertopor,
    MAX(a.proprietario) AS proprietario,
    MAX(a.equipeproprietaria) AS equipeproprietaria,
    MAX(a.assunto) AS assunto,
    MAX(a.status) AS status,
    MAX(c.datainiciado) AS datainiciado,
    MAX(c.dataresolvido) AS dataresolvido,
    MAX(a.agenteultimainteracao) AS agenteultimainteracao,
    MAX(c.criador) AS criador,
    MAX(c.datacriacao) AS datacriacao,
    MAX(c.p1) AS p1,
    MAX(c.p2) AS p2,
    MAX(c.p3) AS p3,
    MAX(c.comentarios) AS comentarios,
    MAX(c.canal) AS canal,
    MAX(c.origem) AS origem,
    MAX(c.fontedados) AS fontedados,
    f.quantidadedeinteracoeskinghost,
    f.quantidadedeinteracoescliente,
    f.quantidadeinteracoes,
    MAX(a.analista) AS analista
FROM kinghost.chamadosbacklog c 
LEFT JOIN CTE_atendimentos_ordenados a 
    ON c.idchamado = a.idchamado 
    AND a.rn = 1
LEFT JOIN (
    SELECT idchamado,
           SUM(quantidadedeinteracoeskinghost) AS quantidadedeinteracoeskinghost,
           SUM(quantidadedeinteracoescliente) AS quantidadedeinteracoescliente,
           SUM(quantidadeinteracoes) AS quantidadeinteracoes 
    FROM kinghost.chamadosbacklog 
    WHERE datacriacao >= '2025-01-01 00:00:00' 
    GROUP BY idchamado 
) f ON c.idchamado = f.idchamado
WHERE c.dataresolvido IS NOT NULL AND c.datacriacao >= '2025-01-01 00:00:00' AND NOT EXISTS (SELECT 1 FROM kinghost.chamados p WHERE c.idefetivo = p.idefetivo)
GROUP BY c.idchamado,    f.quantidadedeinteracoeskinghost,
    f.quantidadedeinteracoescliente,
    f.quantidadeinteracoes;
