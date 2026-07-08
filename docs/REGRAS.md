# Regras de Negócio — Sistema de Análise NPS

## 1. Critérios de análise

O sistema considera:
- notas de Velocidade, Solução e Relacionamento;
- analistas com pelo menos um número mínimo de avaliações configurado;
- analistas com NPS abaixo da meta definida em `.env`.

## 2. Fórmula de NPS

O cálculo segue a lógica padrão:

- Promotores: notas 9 e 10
- Neutros: notas 7 e 8
- Detratores: notas de 0 a 6

Fórmula:

$$
NPS = \frac{(Promotores - Detratores)}{Total\ de\ respostas} \times 100
$$

## 3. Regras de classificação

- Se um analista tiver NPS menor que a meta, ele é considerado crítico para análise;
- A meta padrão é 70.0;
- O mínimo de avaliações padrão é 3;
- O sistema avalia cada dimensão individualmente, mas também considera o conjunto da avaliação do cliente.

## 4. Regras de segurança e privacidade

- os dados sensíveis de conversas devem ser anonimizados antes do envio para IA;
- e-mails, CPFs, CNPJs, telefones, IPs, links, senhas e nomes de domínios devem ser mascarados;
- os arquivos resultantes devem ser tratados como conteúdo operacional interno.

## 5. Regras de persistência

- os resultados são escritos em uma única tabela `lw_octadesk.analise_nps_analistas`, discriminados pela coluna `analise_tipo`:
  - `'monitoramento_nps_analistas'` para análises por analista (via Gemini);
  - `'woz_detratores_trimestral'` para comparativos WOZ (estatístico, sem IA);
- registros na tabela `rawdata_analise_nps_analistas` mais antigos que `ANALISE_RETENTION_DAYS` (padrão 90 dias) são removidos automaticamente a cada execução do fluxo NPS;
- a tabela `analise_nps_analistas` (dados processados) não é afetada pela limpeza automática;
- o arquivo `woz_detratores/historico.json` é atualizado somente após confirmação de sucesso na persistência do banco — banco e JSON devem sempre estar em sincronia;
- os relatórios HTML gerados servem como auditoria e histórico de acompanhamento.

## 6. Regras de idempotência

- o fluxo NPS (`verifica_nps.py`) é idempotente: analistas já analisados no período são detectados via `analise_ja_existe()` e pulados, sem nova chamada à API Gemini;
- o fluxo WOZ (`analise_woz_detratores.py`) é idempotente: cada execução usa `request_id = woz_{ano}_T{t1}_vs_T{t2}` com `WHERE NOT EXISTS` para evitar duplicatas;
- o lock de threading `_analise_lock` em `verifica_nps.py` garante que dois workers paralelos não iniciem a análise do mesmo analista simultaneamente — o lock cobre tanto a verificação no banco quanto a marcação como "em andamento".

## 7. Regras de operação

- se não houver dados no período, o processo deve encerrar com mensagem clara;
- se houver falha de conexão ou API, o log deve registrar o erro com contexto;
- o SQL de promoção (`insereDadosAnaliseNPS.sql`) deve ser executado **uma única vez** por execução do fluxo NPS, após todos os analistas serem processados — nunca dentro de um loop por analista;
- o sistema deve priorizar consistência e rastreabilidade sobre velocidade.

## 8. Regras de manutenção

- alterações em limiares devem ser feitas no `.env` ou no arquivo de configuração central;
- alterações em lógica de consulta ou processamento devem ser documentadas no README e em docs/;
- alterações em dependências precisam atualizar o `requirements.txt`;
- ao adicionar novos termos de detecção WOZ, validar que o padrão SQL ILIKE não gera falsos positivos em palavras comuns do português antes de incluir.
