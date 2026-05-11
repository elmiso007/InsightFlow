INSERT INTO kinghost_octadesk.analise_monitoramento_contatos
(data_processamento, data_inicio, data_fim, lista_protocolos, analise, setor, input_text, request_id , resposta_json, resposta_text, token_solicitacao, token_resposta, model, data_insercao, data_modificacao)
SELECT 
a.request::TIMESTAMP,
a.dados_de::TIMESTAMP,
a.dados_ate::TIMESTAMP, 
a.lista_protocolos::TEXT,
a.analise::VARCHAR,
a.setor::VARCHAR,
a.input_text::TEXT,
a.request_id::VARCHAR,
a.resposta_json::JSON,
a.resposta_text::TEXT,
a.token_prompt::INTEGER,
a.token_completion::INTEGER,
a.model::VARCHAR,
now() AS data_insercao,
now() AS data_modificacao
FROM kinghost_octadesk.rawdata_analise_monitoramento_contatos a




