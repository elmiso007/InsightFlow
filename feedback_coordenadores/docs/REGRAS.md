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

- os resultados são escritos em tabelas de análise no banco;
- os relatórios gerados servem como auditoria e histórico de acompanhamento;
- o processo deve manter o histórico para comparação entre ciclos.

## 6. Regras de operação

- se não houver dados no período, o processo deve encerrar com mensagem clara;
- se houver falha de conexão ou API, o log deve registrar o erro com contexto;
- o sistema deve priorizar consistência e rastreabilidade sobre velocidade.

## 7. Regras de manutenção

- alterações em limiares devem ser feitas no `.env` ou no arquivo de configuração central;
- alterações em lógica de consulta ou processamento devem ser documentadas no README e em docs/;
- alterações em dependências precisam atualizar o `requirements.txt`.
