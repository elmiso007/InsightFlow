# Relatório de Sprint

## 1. Sumário Executivo
- Total de itens na base: **34**
- Percentual de conclusão: **35.29%**
- Demandas Planejadas: **28**
- Demandas Não-planejadas: **6**

**Percepções do desempenho obtido na sprint:**
A sprint atual demonstrou uma taxa de conclusão de **35.29%** sobre um total de 34 itens, indicando uma capacidade de entrega que pode ser otimizada. No entanto, o volume de **6 demandas não-planejadas** (17.65% do total) é um ponto de atenção. Esse desvio pode impactar a previsibilidade do planejamento e a capacidade da equipe de focar em iniciativas estratégicas de longo prazo, exigindo uma análise sobre a origem e a gestão dessas interrupções para otimizar a alocação de recursos nas próximas sprints. A baixa taxa de conclusão geral também sugere que a equipe pode estar enfrentando desafios na execução ou que o escopo da sprint foi ambicioso demais, necessitando de um ajuste no planejamento para sprints futuras.

## 2. Visão por Unidade de Negócio (BU)
Quantidade de entregas por BU (considerando itens concluídos e em andamento):

| Unidade de Negócio | Quantidade de Itens |
|--------------------|---------------------|
| (Multi-BU)         | 4                   |
| KingHost           | 10                  |
| Locaweb            | 7                   |
| Octadesk           | 8                   |
| Vindi              | 5                   |
| —                  | 2                   |

A BU que recebeu mais esforço no período foi **KingHost**, com 10 itens.

**Resumo do desempenho obtido na sprint:**
A distribuição de esforço entre as BUs mostra uma concentração significativa em **KingHost**, que recebeu 10 itens. Embora isso possa refletir prioridades estratégicas da sprint, é importante avaliar se essa alocação está balanceada em relação às necessidades de outras unidades, como Vindi e Locaweb, que apresentaram menor volume de itens individuais. O volume de itens Multi-BU (4) também indica iniciativas que beneficiam mais de uma unidade. Desvios de foco podem surgir se as demandas de uma única BU dominam a capacidade da equipe, potencialmente atrasando entregas importantes para outras áreas. Recomenda-se revisar a priorização e o balanceamento da carga de trabalho para garantir que todas as BUs recebam a atenção necessária para seus objetivos de negócio.

## 3. Alinhamento Estratégico (70/20/10)
- % Desenvolvimento de Produto: **79.31%** (Alvo: 70%)
- % Melhorias Técnicas: **10.34%** (Alvo: 20%)
- % Inovação / Experimentação: **10.34%** (Alvo: 10%)

**Alinhamento Estratégico (Regra 70/20/10):**
A regra 70/20/10 é uma diretriz estratégica que visa otimizar a alocação de recursos da equipe, destinando aproximadamente 70% do tempo para o desenvolvimento de novos produtos e funcionalidades que impulsionam o crescimento do negócio, 20% para melhorias técnicas e otimização de sistemas existentes (garantindo estabilidade e eficiência), e 10% para inovação e experimentação, explorando novas ideias e tecnologias. Essa distribuição é crucial para equilibrar a entrega de valor imediato com a sustentabilidade técnica e a capacidade de inovação a longo prazo.

Nesta sprint, a equipe dedicou **79.31%** ao Desenvolvimento de Produto, **10.34%** a Melhorias Técnicas e **10.34%** a Inovação/Experimentação.
O desempenho da equipe nesta sprint mostra um **desalinhamento** com a regra 70/20/10. A baixa porcentagem em Melhorias Técnicas (10.34%) pode levar a um acúmulo de débito técnico, impactando a estabilidade e a performance dos sistemas a médio e longo prazo. Embora o foco em Desenvolvimento de Produto esteja acima da meta, é fundamental revisar a priorização das demandas para realinhar a alocação de esforço com os objetivos estratégicos, garantindo que o foco em produto, saúde técnica e inovação seja devidamente balanceado.

## 4. Destaques da Sprint

### KingHost
- Motivação:

Aocmpanhar performance de final de semana

Dores (Problema de Negocio):

Não tenho visibilidade dos sabados e domingos do time

Proposta:

Incluir os fins de semana nos paineis

Dados Necessários:

os dados de sabado e domingo

----------------------------

Solicitante: roberto.coelho@vindi.com.br
- Motivação:

Diagnostico rápido das filas ofensoras

Dores (Problema de Negocio):

Não é possivel ter um diagostico rapido de fila ofensora no NPS. para saber é necessário realizar varios filtros dificultando o diagonostico

Proposta:

No painel de 'PESQUISA DE SATISFAÇÃO' quebrar a visão por fila.

Podem criar mais uma ABA no canto esquerdo, sem mexer nas visões atuais.

Nessa nova ABA criar uma COLUNA com a FILA e ao lado Colocar os P1 - P2 - P3 somente os termometros. Nao precisa colocar os indicadores em percentual.

Os termometros podem ficar menores para que caibam numa unica página.

Dados Necessários:

FILA e P1 - P2 - P3 somente os termometros.

----------------------------

Solicitante: roberto.coelho@vindi.com.br

### Locaweb
- *Objetivo:* Replicar a estrutura de monitoramento de contatos existente para a vertical de *Cancelamento*, garantindo visibilidade sobre o volume e comportamento dessas interações.

*Ações Principais:*

* *Replicação Técnica:* Adaptar os dashboards/queries atuais para filtrar e exibir dados específicos do fluxo de cancelamento.
* *Gestão de Acessos:* Garantir permissões de visualização para os solicitantes:
** Tais Silva
** Glauco Oliveira
** Michelle Gusmão

*Entrega Esperada:*

* Monitoramento ativo com dados atualizados.
* Confirmação de acesso realizado para todos os stakeholders listados..

### (Multi-BU)
- *Objetivo:* Centralizar e automatizar a ingestão dos dados de atendimento das unidades de negócio no Google Cloud Platform (GCP) da LWSA, garantindo a disponibilidade das bases para análise.

*Escopo da Ingestão (Prioridade):*

# *Locaweb*
# *KingHost*
# *Octadesk*

*Contexto e Referências:*

* O alinhamento técnico e as definições de conectores/APIs estão sendo discutidos no canal Slack: {{#locaweb-squad-business-analytics_atendimento}}.
* A tarefa consiste em facilitar ou executar o pipeline de dados (ETL/ELT) para o ambiente de BigQuery/GCP.

*Resultados Esperados:*

* Tabelas de atendimento ingeridas e atualizadas conforme a frequência necessária.
* Documentação mínima da origem dos dados e processo de carga.

### Vindi
- Criar painel com indicadores:
Tickets em aberto por departamento
Sla médio em dias por departamento
analíticos
Ticket em aberto por prazo que está em aberto
NPS por grupo

**Comentarios sobre os destaques:**
Os destaques desta sprint refletem um esforço concentrado em melhorias de visibilidade e automação para as BUs, com ênfase em dashboards de volumetria e classificação de contatos. A centralização da ingestão de dados no GCP é um avanço técnico importante que beneficia todas as unidades. Esses itens demonstram a capacidade da equipe em entregar soluções que otimizam operações e fornecem insights valiosos para a tomada de decisão, contribuindo diretamente para a eficiência e a gestão de performance das BUs.

## 5. Análise de Saúde e Riscos
- Volume de demandas Não-planejadas: **6** (17.65% do total)

- Observações importantes e potenciais riscos:
- **Ajuste dos dados de abandono de Chat/WhatsApp da loca a partir da identificação de um bug na query.** (Status: [Downstream] Em andamento, BU: Locaweb)
- **Construir um site que centralize todos os agentes de Inteligência Artificial que foram treinados e estão disponíveis para atuar nas unidades de negócio: Locaweb, KingHost, Octadesk e Vindi** (Status: [Downstream] Em andamento, BU: (Multi-BU))
- **Criação de uma versão 2.0 da Gem mostrada pelo Arthur. buscando trazer por meio desta Gem versões gráficas da performance da equipe.** (Status: [Downstream] Validação PO, BU: Locaweb)
- **Criar no Superset um dash para ver métricas da classificação por IA dos contatos
Niveis de classificação, Motivos de contato e etc.** (Status: [Downstream] Aguardando testes, BU: Octadesk)
- **Desenvolver o dashboard de coordenação para a unidade *Octadesk* no Superset, utilizando como benchmark o modelo ""Dashboard Locaweb Coordenação"".** (Status: [Downstream] Selecionadas, BU: Octadesk)
- **Entender o perfil de cliente que mais consomem os produtos de Octadesk por meio da classificação Cnae class, ferramentas de identificação do e informações já conhecidas por meio do Painel do Cliente Octa.** (Status: [Downstream] Em andamento, BU: Octadesk)
- **Estudo para a classificar persona Octa.** (Status: [Downstream] Em code review, BU: Octadesk)
- **Este épico engloba a configuração, migração de rotinas e estabelecimento de governança para o novo banco de dados PostgreSQL. O foco é garantir uma transição segura do banco CPRO23221 para o PGDB0104, utilizando Airflow para orquestração e aplicando políticas rigorosas de acesso (PoLP).** (Status: [Downstream] Backlog, BU: (Multi-BU)) - Risco explícito na descrição/comentário.
- **Implementar um fluxo de automação via *n8n* utilizando *Agentes de IA* para a classificação automática de tickets de atendimento. O projeto visa testar a eficácia da árvore de classificação atual e reduzir o esforço manual.** (Status: [Downstream] Aguardando code review, BU: —)
- **Motivação:
Centralização do atendimento
Dores (Problema de Negocio):
Acesso aos dados unificados com a Vindi e padronização de indicadores
Proposta:
Trazer os dados para MB e replicar indicadores
Dados Necessários:
IDEM aos da Vindi
----------------------------
Solicitante: roberto.coelho@vindi.com.br** (Status: [Downstream] Em andamento, BU: Vindi)
- **Motivação:
Concentrar os links de NotebookLM e Gems criados pela equipe
Dores (Problema de Negocio):
Concentrar os links em um único local
Proposta:
Criar um portal contendo os links e descrições
Dados Necessários:
Links
----------------------------
Solicitante: thiago.josetti@locaweb.com.br** (Status: [Downstream] Em andamento, BU: (Multi-BU))
- **Motivação:
Indicadores centralizados
Dores (Problema de Negocio):
falta do indicador centralizado após a migração da plataforma
Proposta:
Trazer o basico, somente, de dados do Zendesk para a octa
Dados Necessários:
os que estão nesse painel
https://analytics.vindi.com.br/dashboard/876-macro-dados-gerenciais-cx?agente_gateway=&agente_payments=&data_final=2026-01-31&data_inicial=2025-10-10&tab=541-cx---geral-%28em-desenvolvimento%29 (https://analytics.vindi.com.br/dashboard/876-macro-dados-gerenciais-cx?agente_gateway=&a[…]al=2025-10-10&tab=541-cx---geral-%28em-desenvolvimento%29)
----------------------------
Solicitante: roberto.coelho@vindi.com.br** (Status: [Downstream] Em andamento, BU: Vindi)
- **Motivação:
Indicadores pendentes
Dores (Problema de Negocio):
Sem visão para esses dados ou visão feita manualmente.
Proposta:
Aging
FAR
Taxa de escalonamento
Backlog
Response Rate (atual para NPS)
SLA Primeira resposta
Taxa Recontato
SLA Resolução
Aging solução contorno (Incidente)
Aging solução raiz (Problema)
kpi's da central de ajuda
Dados Necessários:
Aging
FAR
Taxa de escalonamento
Backlog
Response Rate (atual para NPS)
SLA Primeira resposta
Taxa Recontato
SLA Resolução
Aging solução contorno (Incidente)
Aging solução raiz (Problema)
kpi's da central de ajuda
----------------------------
Solicitante: murilo.morgado@vindi.com.br** (Status: [Downstream] Selecionadas, BU: Vindi)
- **O objetivo desta demanda é criar um dashboard de coordenação para a marca *KingHost* dentro do Superset. O painel deve seguir o padrão visual e funcional do relatório já existente da Locaweb Coordenação, permitindo o acompanhamento de performance em diferentes níveis hierárquicos.
h3. Regras de Negócio e Requisitos
h4. 1. Módulo de Recontatos (Relatório Separado)
Conforme alinhamento inicial, as métricas de recontato devem ser apresentadas em um relatório ou aba distinta.
* *Recontato do Dia:* Interações que retornaram dentro do mesmo dia civil.
* *Recontato da Semana:* Interações que retornaram dentro da mesma semana epidemiológica/calendário.
* *Recontato do Mês:* Interações que retornaram dentro do mesmo mês.
* *Ponto de Atenção:* Validar a regra de extração/cálculo específica com *@Maria Castro* para garantir paridade com os dados da Locaweb.
h4. 2. Regra de FRC (First Response Contact / FCR alternativo)
* *Definição:* Considerar recontato na mesma fila dentro de um intervalo de *72 horas*.
h3. Critérios de Aceitação
* [ ] Dashboard criado no ambiente de produção do *Superset*.
* [ ] Filtros de Time, Coordenador e Analista funcionando corretamente e cruzando dados.
* [ ] Relatório de Recontatos validado pela área técnica (Maria Castro).
* [ ] Dados de FRC (72h) validado e batendo com a base de dados KingHost.
* [ ] Documentação da query/tabela de origem adicionada ao card ou Wiki.** (Status: [Downstream] Validação PO, BU: KingHost)
- **Replicar a GEM criada para a Octa para as demais unidades.** (Status: [Downstream] Em andamento, BU: Locaweb)
- **Replicar a GEM criada para a Octa para as demais unidades.** (Status: [Downstream] Validação PO, BU: KingHost)
- **Replicar a GEM criada para a Octa para as demais unidades.** (Status: [Downstream] Selecionadas, BU: Vindi)
- **Resumo
Replicar o Relatório Semanal de Atendimento do setor de Suporte para o sistema King. O objetivo é ter informações precisas através de IA, similar ao que é feito para LOCA.
Contexto
A motivação para esta solicitação é garantir o acesso a dados TOP, assim como ocorre na LOCA. O problema identificado é a falta de acesso a informações equivalentes.
Critérios de Aceitação
* Replicar o relatório semanal de atendimento da LOCA.
* Granularizar o motivo de contato, proporcionalizando em volume pela entrada.
Outras informações
Solicitante: [roberto.coelho@vindi.com.br|mailto:roberto.coelho@vindi.com.br]** (Status: [Downstream] Em andamento, BU: (Multi-BU))
- **Subtarefa,Octadesk,,,,[Downstream] Backlog,,Planejada,,Sprint #02,Sprint #03,,,,,,198468,DAPT-112,Classificação de Persona** (Status: [Downstream] Backlog, BU: Octadesk)
- **Subtarefa,Octadesk,,,,[Downstream] Backlog,,Planejada,,Sprint #02,Sprint #03,,,,,,198468,DAPT-112,Classificação de Persona** (Status: [Downstream] Backlog, BU: Octadesk)
- **Subtarefa,Octadesk,,,,[Downstream] Backlog,,Planejada,,Sprint #02,Sprint #03,,,,,,198468,DAPT-112,Classificação de Persona** (Status: [Downstream] Backlog, BU: Octadesk)
- **Visualizador: Looker
*[DESCRIÇÃO]* *Objetivo:* Migrar e refazer o relatório de Contact Rate da KingHost para o Looker, corrigindo as divergências identificadas na volumetria de contatos de suporte.
*Ponto de Atenção Técnico:*
* Atualmente, o relatório utiliza apenas a base de clientes, pois os números de contatos de suporte estão subestimados (contagem a menor).
* O novo desenvolvimento deve garantir que o número de contatos esteja 100% correto no Looker.
*Referência para Migração:*
* *Dashboard Atual (Power BI):* [Link do Relatório|https://app.powerbi.com/reportEmbed?reportId=d0aa48f6-61c7-412b-b9e0-12c56a865938&autoAuth=true&ctid=700a4e08-ed6d-4401-835a-4e4fe805c8ca]
*Entrega Esperada:*
* Relatório no Looker com paridade de dados e métricas de Contact Rate validadas frente às fontes de origem de suporte.** (Status: [Downstream] Aguardando publicação, BU: KingHost)
- ***Objetivo:* Criar relatório de coordenação para a KingHost, seguindo o modelo do Dashboard Locaweb Coordenação.
*Estrutura de Visualização:*
* Resultados por Time, Coordenador e Analista.
*Regras de Recontato (Relatório Separado):*
* *Escopo:* Recontato do dia (mesmo dia), semana e mês.
* *Ação:* Validar lógica de extração com @Maria Castro [Locaweb - Data Analytics/Atendimento].
*Regra de FRC:*
* Recontato na mesma fila dentro de um intervalo de 72 horas.** (Status: [Downstream] Validação PO, BU: Locaweb)
- ***Objetivo:* Estabelecer e manter a rotina de monitoramento e envio do report diário com os indicadores de atendimento da operação *Vindi*.
*Escopo do Report:*
* Acompanhamento de KPIs críticos de atendimento (ex: Volume, SLA, TMA).
* Monitoramento de anomalias ou desvios de performance no dia anterior e acumulado.
*Entregas Esperadas:*
* Atualização diária dos dados para os stakeholders da unidade Vindi.
* Garantia de integridade das fontes de dados que alimentam este monitoramento.
*Canais de Notificação:*
* [Definir se o report é via E-mail, Slack ou Dashboard específico].** (Status: [Downstream] Aguardando code review, BU: —)

**Comentarios sobre os riscos:**
O volume de **6 demandas não-planejadas** representa um risco à previsibilidade e ao foco da equipe, desviando recursos de iniciativas planejadas. Além disso, a presença de múltiplos itens em status de `[Downstream] Em andamento`, `[Downstream] Validação PO`, `[Downstream] Aguardando testes` e `[Downstream] Backlog` indica dependências externas ou gargalos internos que podem atrasar a conclusão. A existência de um bug identificado e a necessidade de aguardar endpoints de outras equipes (Vindi/Octadesk) são pontos críticos que exigem acompanhamento proativo para evitar impactos no cronograma e na capacidade de entrega das próximas sprints. O épico de migração para PostgreSQL também apresenta riscos importantes de indisponibilidade e incompatibilidade, que devem ser mitigados com um plano de rollback robusto.

## 6. Próximos Passos
- **Ajuste dos dados de abandono de Chat/WhatsApp da loca a partir da identificação de um bug na query.** (BU: Locaweb, Status: [Downstream] Em andamento, Sprint: Sprint #02 -> Sprint #03)
- **Construir um site que centralize todos os agentes de Inteligência Artificial que foram treinados e estão disponíveis para atuar nas unidades de negócio: Locaweb, KingHost, Octadesk e Vindi** (BU: (Multi-BU), Status: [Downstream] Em andamento, Sprint: Sprint #02 -> Sprint #03)
- **Criação de uma versão 2.0 da Gem mostrada pelo Arthur. buscando trazer por meio desta Gem versões gráficas da performance da equipe.** (BU: Locaweb, Status: [Downstream] Validação PO, Sprint: Sprint #02 -> Sprint #03)
- **Criar no Superset um dash para ver métricas da classificação por IA dos contatos
Niveis de classificação, Motivos de contato e etc.** (BU: Octadesk, Status: [Downstream] Aguardando testes, Sprint: Sprint #02 -> Sprint #03)
- **Desenvolver o dashboard de coordenação para a unidade *Octadesk* no Superset, utilizando como benchmark o modelo ""Dashboard Locaweb Coordenação"".** (BU: Octadesk, Status: [Downstream] Selecionadas, Sprint: Sprint #02 -> Sprint #03)
- **Entender o perfil de cliente que mais consomem os produtos de Octadesk por meio da classificação Cnae class, ferramentas de identificação do e informações já conhecidas por meio do Painel do Cliente Octa.** (BU: Octadesk, Status: [Downstream] Em andamento, Sprint: Sprint #02 -> Sprint #03)
- **Estudo para a classificar persona Octa.** (BU: Octadesk, Status: [Downstream] Em code review, Sprint: Sprint #01 -> Sprint #02 -> Sprint #03)
- **Este épico engloba a configuração, migração de rotinas e estabelecimento de governança para o novo banco de dados PostgreSQL. O foco é garantir uma transição segura do banco CPRO23221 para o PGDB0104, utilizando Airflow para orquestração e aplicando políticas rigorosas de acesso (PoLP).** (BU: (Multi-BU), Status: [Downstream] Backlog, Sprint: Sprint #01 -> Sprint #02 -> Sprint #03)
- **Implementar um fluxo de automação via *n8n* utilizando *Agentes de IA* para a classificação automática de tickets de atendimento. O projeto visa testar a eficácia da árvore de classificação atual e reduzir o esforço manual.** (BU: —, Status: [Downstream] Aguardando code review, Sprint: Sprint #02 -> Sprint #03)
- **Motivação:
Centralização do atendimento
Dores (Problema de Negocio):
Acesso aos dados unificados com a Vindi e padronização de indicadores
Proposta:
Trazer os dados para MB e replicar indicadores
Dados Necessários:
IDEM aos da Vindi
----------------------------
Solicitante: roberto.coelho@vindi.com.br** (BU: Vindi, Status: [Downstream] Em andamento, Sprint: Sprint #02 -> Sprint #03)
- **Motivação:
Concentrar os links de NotebookLM e Gems criados pela equipe
Dores (Problema de Negocio):
Concentrar os links em um único local
Proposta:
Criar um portal contendo os links e descrições
Dados Necessários:
Links
----------------------------
Solicitante: thiago.josetti@locaweb.com.br** (BU: (Multi-BU), Status: [Downstream] Em andamento, Sprint: Sprint #02 -> Sprint #03)
- **Motivação:
Indicadores centralizados
Dores (Problema de Negocio):
falta do indicador centralizado após a migração da plataforma
Proposta:
Trazer o basico, somente, de dados do Zendesk para a octa
Dados Necessários:
os que estão nesse painel
https://analytics.vindi.com.br/dashboard/876-macro-dados-gerenciais-cx?agente_gateway=&agente_payments=&data_final=2026-01-31&data_inicial=2025-10-10&tab=541-cx---geral-%28em-desenvolvimento%29 (https://analytics.vindi.com.br/dashboard/876-macro-dados-gerenciais-cx?agente_gateway=&a[…]al=2025-10-10&tab=541-cx---geral-%28em-desenvolvimento%29)
----------------------------
Solicitante: roberto.coelho@vindi.com.br** (BU: Vindi, Status: [Downstream] Em andamento, Sprint: Sprint #02 -> Sprint #03)
- **Motivação:
Indicadores pendentes
Dores (Problema de Negocio):
Sem visão para esses dados ou visão feita manualmente.
Proposta:
Aging
FAR
Taxa de escalonamento
Backlog
Response Rate (atual para NPS)
SLA Primeira resposta
Taxa Recontato
SLA Resolução
Aging solução contorno (Incidente)
Aging solução raiz (Problema)
kpi's da central de ajuda
Dados Necessários:
Aging
FAR
Taxa de escalonamento
Backlog
Response Rate (atual para NPS)
SLA Primeira resposta
Taxa Recontato
SLA Resolução
Aging solução contorno (Incidente)
Aging solução raiz (Problema)
kpi's da central de ajuda
----------------------------
Solicitante: murilo.morgado@vindi.com.br** (BU: Vindi, Status: [Downstream] Selecionadas, Sprint: Sprint #02 -> Sprint #03)
- **O objetivo desta demanda é criar um dashboard de coordenação para a marca *KingHost* dentro do Superset. O painel deve seguir o padrão visual e funcional do relatório já existente da Locaweb Coordenação, permitindo o acompanhamento de performance em diferentes níveis hierárquicos.
h3. Regras de Negócio e Requisitos
h4. 1. Módulo de Recontatos (Relatório Separado)
Conforme alinhamento inicial, as métricas de recontato devem ser apresentadas em um relatório ou aba distinta.
* *Recontato do Dia:* Interações que retornaram dentro do mesmo dia civil.
* *Recontato da Semana:* Interações que retornaram dentro da mesma semana epidemiológica/calendário.
* *Recontato do Mês:* Interações que retornaram dentro do mesmo mês.
* *Ponto de Atenção:* Validar a regra de extração/cálculo específica com *@Maria Castro* para garantir paridade com os dados da Locaweb.
h4. 2. Regra de FRC (First Response Contact / FCR alternativo)
* *Definição:* Considerar recontato na mesma fila dentro de um intervalo de *72 horas*.
h3. Critérios de Aceitação
* [ ] Dashboard criado no ambiente de produção do *Superset*.
* [ ] Filtros de Time, Coordenador e Analista funcionando corretamente e cruzando dados.
* [ ] Relatório de Recontatos validado pela área técnica (Maria Castro).
* [ ] Dados de FRC (72h) validado e batendo com a base de dados KingHost.
* [ ] Documentação da query/tabela de origem adicionada ao card ou Wiki.** (BU: KingHost, Status: [Downstream] Validação PO, Sprint: Sprint #01 -> Sprint #02 -> Sprint #03)
- **Replicar a GEM criada para a Octa para as demais unidades.** (BU: Locaweb, Status: [Downstream] Em andamento, Sprint: Sprint #02 -> Sprint #03)
- **Replicar a GEM criada para a Octa para as demais unidades.** (BU: KingHost, Status: [Downstream] Validação PO, Sprint: Sprint #02 -> Sprint #03)
- **Replicar a GEM criada para a Octa para as demais unidades.** (BU: Vindi, Status: [Downstream] Selecionadas, Sprint: Sprint #02 -> Sprint #03)
- **Resumo
Replicar o Relatório Semanal de Atendimento do setor de Suporte para o sistema King. O objetivo é ter informações precisas através de IA, similar ao que é feito para LOCA.
Contexto
A motivação para esta solicitação é garantir o acesso a dados TOP, assim como ocorre na LOCA. O problema identificado é a falta de acesso a informações equivalentes.
Critérios de Aceitação
* Replicar o relatório semanal de atendimento da LOCA.
* Granularizar o motivo de contato, proporcionalizando em volume pela entrada.
Outras informações
Solicitante: [roberto.coelho@vindi.com.br|mailto:roberto.coelho@vindi.com.br]** (BU: (Multi-BU), Status: [Downstream] Em andamento, Sprint: Sprint #02 -> Sprint #03)
- **Classificação de Persona** (BU: Octadesk, Status: [Downstream] Backlog, Sprint: Sprint #02 -> Sprint #03)
- **Classificação de Persona** (BU: Octadesk, Status: [Downstream] Backlog, Sprint: Sprint #02 -> Sprint #03)
- **Classificação de Persona** (BU: Octadesk, Status: [Downstream] Backlog, Sprint: Sprint #02 -> Sprint #03)
- **Visualizador: Looker
*[DESCRIÇÃO]* *Objetivo:* Migrar e refazer o relatório de Contact Rate da KingHost para o Looker, corrigindo as divergências identificadas na volumetria de contatos de suporte.
*Ponto de Atenção Técnico:*
* Atualmente, o relatório utiliza apenas a base de clientes, pois os números de contatos de suporte estão subestimados (contagem a menor).
* O novo desenvolvimento deve garantir que o número de contatos esteja 100% correto no Looker.
*Referência para Migração:*
* *Dashboard Atual (Power BI):* [Link do Relatório|https://app.powerbi.com/reportEmbed?reportId=d0aa48f6-61c7-412b-b9e0-12c56a865938&autoAuth=true&ctid=700a4e08-ed6d-4401-835a-4e4fe805c8ca]
*Entrega Esperada:*
* Relatório no Looker com paridade de dados e métricas de Contact Rate validadas frente às fontes de origem de suporte.** (BU: KingHost, Status: [Downstream] Aguardando publicação, Sprint: Sprint #01 -> Sprint #02 -> Sprint #03)
- ***Objetivo:* Criar relatório de coordenação para a KingHost, seguindo o modelo do Dashboard Locaweb Coordenação.
*Estrutura de Visualização:*
* Resultados por Time, Coordenador e Analista.
*Regras de Recontato (Relatório Separado):*
* *Escopo:* Recontato do dia (mesmo dia), semana e mês.
* *Ação:* Validar lógica de extração com @Maria Castro [Locaweb - Data Analytics/Atendimento].
*Regra de FRC:*
* Recontato na mesma fila dentro de um intervalo de 72 horas.** (BU: Locaweb, Status: [Downstream] Validação PO, Sprint: Sprint #01 -> Sprint #02 -> Sprint #03)
- ***Objetivo:* Estabelecer e manter a rotina de monitoramento e envio do report diário com os indicadores de atendimento da operação *Vindi*.
*Escopo do Report:*
* Acompanhamento de KPIs críticos de atendimento (ex: Volume, SLA, TMA).
* Monitoramento de anomalias ou desvios de performance no dia anterior e acumulado.
*Entregas Esperadas:*
* Atualização diária dos dados para os stakeholders da unidade Vindi.
* Garantia de integridade das fontes de dados que alimentam este monitoramento.
*Canais de Notificação:*
* [Definir se o report é via E-mail, Slack ou Dashboard específico].** (BU: —, Status: [Downstream] Aguardando code review, Sprint: Sprint #02 -> Sprint #03)

**Comentarios sobre os proximos passos:**
A próxima sprint já conta com **24 itens em continuidade ou com previsão de avanço**, incluindo tarefas importantes como a replicação de GEMs, a criação de dashboards de coordenação e a automação de classificação por IA. O volume de `carry-over` e itens `[Downstream]` exige atenção para garantir que as dependências sejam resolvidas e que o planejamento da próxima sprint considere a capacidade real da equipe, evitando sobrecarga e novos atrasos. É crucial que a coordenação valide as prioridades e o alinhamento com as BUs para otimizar o fluxo de trabalho.

## 7. Tabela: Tarefas da sprint

### Tarefas concluídas na sprint
Esta tabela lista todos os itens que foram finalizados e tiveram seu status marcado como 'Concluído' durante a sprint.

| Nome da tarefa | BU | Sprint | Solicitante |
|----------------|----|--------|-------------|
| Criação de visão hora a hora no dash de volumetria de locaweb para controldesk | Locaweb | Sprint #02 | — |
| Extração de classificação dos contatos do time de aep no mes de março pro Eliseu | Locaweb | Sprint #02 | — |
| Ajuste de filtro de data no dash de pesquisa de satisfação da King solicitado pela Mih | KingHost | Sprint #02 | Atendimento |
| Inclusão de abas separadas de Locaweb e KingHost no Dash de Contact Rate | (Multi-BU) | Sprint #02 | Atendimento |
| Classificação de Persona | Octadesk | Sprint #02 -> Sprint #03 | — |
| A equipe de produtos solicitou auxilio para realizar os disparos de cobrança durante as férias da Fernanda Jesus. Disparos de ativos via ferramenta da octadesk. | Locaweb | Sprint #02 | Inside Sales |
| | Vindi | Sprint #02 | Atendimento |
| Os dados de volumetria dos contatos da king não estavam contemplando os chamados. Ajustado e agora os dados estão de acordo com os valores do dash de KPI. | KingHost | Sprint #02 | Atendimento |
| Criar painel com indicadores: Tickets em aberto por departamento Sla médio em dias por departamento analíticos Ticket em aberto por prazo que está em aberto NPS por grupo | Vindi | Sprint #02 | Atendimento |
| Motivação: Preciso ter acesso ao % de retenção do BOT por setor Dores (Problema de Negocio): No formato atual não é possivel diagnosticar o % de retenção no bot por setor Proposta: incluir um filtro de SETOR no painel - https://app.powerbi.com/groups/259b0a6f-b89b-4c74-aa62-c76cc5f36092/reports/170f173f-ae3b-4511-ac71-13f711141ece/eaca10b69f2e53858a67?ctid=700a4e08-ed6d-4401-835a-4e4fe805c8ca&experience=power-bi&bookmarkGuid=2f14e8a2f622cf03f699 (https://app.powerbi.com/groups/259b0a6f-b89b-4c74-aa62-c76cc5f36092/reports/170f173f[…]805c8ca&experience=power-bi&bookmarkGuid=2f14e8a2f622cf03f699) Dados Necessários: Só incluir o filtro de setor ---------------------------- Solicitante: roberto.coelho@vindi.com.br | KingHost | Sprint #02 | roberto.coelho@vindi.com.br |
| Motivação: Aocmpanhar performance de final de semana Dores (Problema de Negocio): Não tenho visibilidade dos sabados e domingos do time Proposta: Incluir os fins de semana nos paineis Dados Necessários: os dados de sabado e domingo ---------------------------- Solicitante: roberto.coelho@vindi.com.br | KingHost | Sprint #02 | roberto.coelho@vindi.com.br |
| Motivação: Diagnostico rápido das filas ofensoras Dores (Problema de Negocio): Não é possivel ter um diagostico rapido de fila ofensora no NPS. para saber é necessário realizar varios filtros dificultando o diagonostico Proposta: No painel de 'PESQUISA DE SATISFAÇÃO' quebrar a visão por fila. Podem criar mais uma ABA no canto esquerdo, sem mexer nas visões atuais. Nessa nova ABA criar uma COLUNA com a FILA e ao lado Colocar os P1 - P2 - P3 somente os termometros. Nao precisa colocar os indicadores em percentual. Os termometros podem ficar menores para que caibam numa unica página. Dados Necessários: FILA e P1 - P2 - P3 somente os termometros. ---------------------------- Solicitante: roberto.coelho@vindi.com.br | KingHost | Sprint #02 | roberto.coelho@vindi.com.br |
| *Objetivo:* Replicar a estrutura de monitoramento de contatos existente para a vertical de *Cancelamento*, garantindo visibilidade sobre o volume e comportamento dessas interações. *Ações Principais:* * *Replicação Técnica:* Adaptar os dashboards/queries atuais para filtrar e exibir dados específicos do fluxo de cancelamento. * *Gestão de Acessos:* Garantir permissões de visualização para os solicitantes: ** Tais Silva ** Glauco Oliveira ** Michelle Gusmão *Entrega Esperada:* * Monitoramento ativo com dados atualizados. * Confirmação de acesso realizado para todos os stakeholders listados.. | Locaweb | Sprint #01 -> Sprint #02 | Data Analytics |
| *Objetivo:* Centralizar e automatizar a ingestão dos dados de atendimento das unidades de negócio no Google Cloud Platform (GCP) da LWSA, garantindo a disponibilidade das bases para análise. *Escopo da Ingestão (Prioridade):* # *Locaweb* # *KingHost* # *Octadesk* *Contexto e Referências:* * O alinhamento técnico e as definições de conectores/APIs estão sendo discutidos no canal Slack: {{#locaweb-squad-business-analytics_atendimento}}. * A tarefa consiste em facilitar ou executar o pipeline de dados (ETL/ELT) para o ambiente de BigQuery/GCP. *Resultados Esperados:* * Tabelas de atendimento ingeridas e atualizadas conforme a frequência necessária. * Documentação mínima da origem dos dados e processo de carga. | (Multi-BU) | Sprint #02 | — |

### Tarefas não concluídas e/ou com continuidade na próxima sprint
Esta tabela apresenta os itens que ainda estão em andamento, não foram finalizados ou já estão previstos para terem continuidade na próxima sprint, indicando o status atual e a BU relacionada.

| Nome da tarefa | BU | Sprint | Solicitante |
|----------------|----|--------|-------------|
| Ajuste dos dados de abandono de Chat/WhatsApp da loca a partir da identificação de um bug na query. | Locaweb | Sprint #02 -> Sprint #03 | Atendimento |
| Criação de uma versão 2.0 da Gem mostrada pelo Arthur. buscando trazer por meio desta Gem versões gráficas da performance da equipe. | Locaweb | Sprint #02 -> Sprint #03 | Atendimento |
| Classificação de Persona | Octadesk | Sprint #02 -> Sprint #03 | — |
| Classificação de Persona | Octadesk | Sprint #02 -> Sprint #03 | — |
| Classificação de Persona | Octadesk | Sprint #02 -> Sprint #03 | — |
| Criar no Superset um dash para ver métricas da classificação por IA dos contatos Niveis de classificação, Motivos de contato e etc. | Octadesk | Sprint #02 -> Sprint #03 | Data Analytics |
| Replicar a GEM criada para a Octa para as demais unidades. | Vindi | Sprint #02 -> Sprint #03 | Data Analytics |
| Replicar a GEM criada para a Octa para as demais unidades. | Locaweb | Sprint #02 -> Sprint #03 | Data Analytics |
| Replicar a GEM criada para a Octa para as demais unidades. | KingHost | Sprint #02 -> Sprint #03 | Data Analytics |
| Construir um site que centralize todos os agentes de Inteligência Artificial que foram treinados e estão disponíveis para atuar nas unidades de negócio: Locaweb, KingHost, Octadesk e Vindi | (Multi-BU) | Sprint #02 -> Sprint #03 | — |
| Motivação: Concentrar os links de NotebookLM e Gems criados pela equipe Dores (Problema de Negocio): Concentrar os links em um único local Proposta: Criar um portal contendo os links e descrições Dados Necessários: Links ---------------------------- Solicitante: thiago.josetti@locaweb.com.br | (Multi-BU) | Sprint #02 -> Sprint #03 | thiago.josetti@locaweb.com.br |
| Entender o perfil de cliente que mais consomem os produtos de Octadesk por meio da classificação Cnae class, ferramentas de identificação do e informações já conhecidas por meio do Painel do Cliente Octa. | Octadesk | Sprint #02 -> Sprint #03 | — |
| Estudo para a classificar persona Octa. | Octadesk | Sprint #01 -> Sprint #02 -> Sprint #03 | — |
| Motivação: Indicadores pendentes Dores (Problema de Negocio): Sem visão para esses dados ou visão feita manualmente. Proposta: Aging FAR Taxa de escalonamento Backlog Response Rate (atual para NPS) SLA Primeira resposta Taxa Recontato SLA Resolução Aging solução contorno (Incidente) Aging solução raiz (Problema) kpi's da central de ajuda Dados Necessários: Aging FAR Taxa de escalonamento Backlog Response Rate (atual para NPS) SLA Primeira resposta Taxa Recontato SLA Resolução Aging solução contorno (Incidente) Aging solução raiz (Problema) kpi's da central de ajuda ---------------------------- Solicitante: murilo.morgado@vindi.com.br | Vindi | Sprint #02 -> Sprint #03 | murilo.morgado@vindi.com.br |
| Visualizador: Looker *[DESCRIÇÃO]* *Objetivo:* Migrar e refazer o relatório de Contact Rate da KingHost para o Looker, corrigindo as divergências identificadas na volumetria de contatos de suporte. *Ponto de Atenção Técnico:* * Atualmente, o relatório utiliza apenas a base de clientes, pois os números de contatos de suporte estão subestimados (contagem a menor). * O novo desenvolvimento deve garantir que o número de contatos esteja 100% correto no Looker. *Referência para Migração:* * *Dashboard Atual (Power BI):* [Link do Relatório|https://app.powerbi.com/reportEmbed?reportId=d0aa48f6-61c7-412b-b9e0-12c56a865938&autoAuth=true&ctid=700a4e08-ed6d-4401-835a-4e4fe805c8ca] *Entrega Esperada:* * Relatório no Looker com paridade de dados e métricas de Contact Rate validadas frente às fontes de origem de suporte. | KingHost | Sprint #01 -> Sprint #02 -> Sprint #03 | — |
| Este épico engloba a configuração, migração de rotinas e estabelecimento de governança para o novo banco de dados PostgreSQL. O foco é garantir uma transição segura do banco CPRO23221 para o PGDB0104, utilizando Airflow para orquestração e aplicando políticas rigorosas de acesso (PoLP). *Objetivos do Épico:* # Configurar infraestrutura de leitura/escrita (Primary & Replica). # Orquestrar pipelines de dados via Apache Airflow. # Estabelecer governança de usuários e acessos. # Definir padrões de documentação e qualidade de código. h3. ✅ Critérios de Aceite * As rotinas de dados migrados com 100% de integridade comprovada por logs de auditoria no Airflow. * Nenhum usuário nominal (exceto os 3 autorizados) deve ter acesso de escrita no banco primário. * Documentação técnica e diagrama de entidade-relacionamento atualizados no Confluence. * Plano de _Rollback_ testado e validado. * Sistema de monitoramento e alertas configurado. * O banco CPRO23221 só poderá ser desativado após aprovação formal dos stakeholders de BI. h3. ⚠️ Riscos Identificados * Indisponibilidade prolongada durante a janela de migração. * Incompatibilidade de drivers ou bibliotecas de conexão no backend atual. * Perda de performance em queries específicas que não foram otimizadas para o novo motor. | (Multi-BU) | Sprint #01 -> Sprint #02 -> Sprint #03 | Data Analytics |
| Desenvolver o dashboard de coordenação para a unidade *Octadesk* no Superset, utilizando como benchmark o modelo ""Dashboard Locaweb Coordenação"". *Estrutura de Visualização e Filtros:* * Visão de performance segmentada por: *Time*, *Coordenador* e *Analista*. *Métricas de Recontato (Relatório Separado):* * *Janelas de acompanhamento:* Mesmo dia, mesma semana e mesmo mês. * *Ação:* Validar especificidades da regra com @Maria Castro [Locaweb - Data Analytics/Atendimento]. *Regra de FRC:* * Considerar recontato ocorrido na mesma fila em um intervalo de até 72 horas. *Entrega Esperada:* * Dashboard funcional no Superset integrado à base de dados Octadesk, com as regras de recontato e FRC devidamente aplicadas. | Octadesk | Sprint #02 -> Sprint #03 | — |
| *Objetivo:* Estabelecer e manter a rotina de monitoramento e envio do report diário com os indicadores de atendimento da operação *Vindi*. *Escopo do Report:* * Acompanhamento de KPIs críticos de atendimento (ex: Volume, SLA, TMA). * Monitoramento de anomalias ou desvios de performance no dia anterior e acumulado. *Entregas Esperadas:* * Atualização diária dos dados para os stakeholders da unidade Vindi. * Garantia de integridade das fontes de dados que alimentam este monitoramento. *Canais de Notificação:* * [Definir se o report é via E-mail, Slack ou Dashboard específico]. | — | Sprint #02 -> Sprint #03 | — |
| *Objetivo:* Implementar um fluxo de automação via *n8n* utilizando *Agentes de IA* para a classificação automática de tickets de atendimento. O projeto visa testar a eficácia da árvore de classificação atual e reduzir o esforço manual. *Estratégia de Rollout (POC):* A implementação seguirá uma ordem crescente de complexidade e volume: # *Octadesk (Fase Atual):* Unidade piloto por possuir o menor volume. # *KingHost:* Segunda fase de validação (Volume médio). # *Locaweb:* Fase final de escala (Maior volume). *Requisitos Técnicos:* * Integração do n8n com as APIs do Octadesk. * Configuração de Agente de IA para interpretação de logs/transcrições de atendimento. * Mapeamento e validação da árvore de classificação atual frente aos outputs da IA. *Critérios de Sucesso:* * Acurácia da classificação da IA comparada à classificação humana. * Estabilidade do fluxo no n8n para a BU Octadesk. | — | Sprint #02 -> Sprint #03 | — |
| *Objetivo:* Criar relatório de coordenação para a KingHost, seguindo o modelo do Dashboard Locaweb Coordenação. *Estrutura de Visualização:* * Resultados por Time, Coordenador e Analista. *Regras de Recontato (Relatório Separado):* * *Escopo:* Recontato do dia (mesmo dia), semana e mês. * *Ação:* Validar lógica de extração com @Maria Castro [Locaweb - Data Analytics/Atendimento]. *Regra de FRC:* * Recontato na mesma fila dentro de um intervalo de 72 horas. | Locaweb | Sprint #01 -> Sprint #02 -> Sprint #03 | Data Analytics |
| O objetivo desta demanda é criar um dashboard de coordenação para a marca *KingHost* dentro do Superset. O painel deve seguir o padrão visual e funcional do relatório já existente da Locaweb Coordenação, permitindo o acompanhamento de performance em diferentes níveis hierárquicos. h3. Regras de Negócio e Requisitos h4. 1. Módulo de Recontatos (Relatório Separado) Conforme alinhamento inicial, as métricas de recontato devem ser apresentadas em um relatório ou aba distinta. * *Recontato do Dia:* Interações que retornaram dentro do mesmo dia civil. * *Recontato da Semana:* Interações que retornaram dentro da mesma semana epidemiológica/calendário. * *Recontato do Mês:* Interações que retornaram dentro do mesmo mês. * *Ponto de Atenção:* Validar a regra de extração/cálculo específica com *@Maria Castro* para garantir paridade com os dados da Locaweb. h4. 2. Regra de FRC (First Response Contact / FCR alternativo) * *Definição:* Considerar recontato na mesma fila dentro de um intervalo de *72 horas*. h3. Critérios de Aceitação * [ ] Dashboard criado no ambiente de produção do *Superset*. * [ ] Filtros de Time, Coordenador e Analista funcionando corretamente e cruzando dados. * [ ] Relatório de Recontatos validado pela área técnica (Maria Castro). * [ ] Dados de FRC (72h) validado e batendo com a base de dados KingHost. * [ ] Documentação da query/tabela de origem adicionada ao card ou Wiki. | KingHost | Sprint #01 -> Sprint #02 -> Sprint #03 | Atendimento |
| Motivação: Centralização do atendimento Dores (Problema de Negocio): Acesso aos dados unificados com a Vindi e padronização de indicadores Proposta: Trazer os dados para MB e replicar indicadores Dados Necessários: IDEM aos da Vindi ---------------------------- Solicitante: roberto.coelho@vindi.com.br | Vindi | Sprint #02 -> Sprint #03 | Atendimento |
| Motivação: Indicadores centralizados Dores (Problema de Negocio): falta do indicador centralizado após a migração da plataforma Proposta: Trazer o basico, somente, de dados do Zendesk para a octa Dados Necessários: os que estão nesse painel https://analytics.vindi.com.br/dashboard/876-macro-dados-gerenciais-cx?agente_gateway=&agente_payments=&data_final=2026-01-31&data_inicial=2025-10-10&tab=541-cx---geral-%28em-desenvolvimento%29 (https://analytics.vindi.com.br/dashboard/876-macro-dados-gerenciais-cx?agente_gateway=&a[…]al=2025-10-10&tab=541-cx---geral-%28em-desenvolvimento%29) ---------------------------- Solicitante: roberto.coelho@vindi.com.br | Vindi | Sprint #02 -> Sprint #03 | Atendimento |
| Resumo Replicar o Relatório Semanal de Atendimento do setor de Suporte para o sistema King. O objetivo é ter informações precisas através de IA, similar ao que é feito para LOCA. Contexto A motivação para esta solicitação é garantir o acesso a dados TOP, assim como ocorre na LOCA. O problema identificado é a falta de acesso a informações equivalentes. Critérios de Aceitação * Replicar o relatório semanal de atendimento da LOCA. * Granularizar o motivo de contato, proporcionalizando em volume pela entrada. Outras informações Solicitante: [roberto.coelho@vindi.com.br|mailto:roberto.coelho@vindi.com.br] | (Multi-BU) | Sprint #02 -> Sprint #03 | Atendimento |

**Percepções do desempenho obtido na sprint:**
A análise das tabelas revela que **12 tarefas foram concluídas**, demonstrando a capacidade de entrega da equipe. No entanto, **22 itens permanecem em aberto**, com diversos status `[Downstream]`, indicando um volume considerável de `carry-over` e dependências. A aderência ao escopo original foi impactada pelas demandas não-planejadas e pela necessidade de aguardar validações ou entregas de outras equipes. O volume pendente exige uma revisão cuidadosa do planejamento da próxima sprint para garantir que esses itens sejam devidamente priorizados e que os bloqueios sejam proativamente gerenciados, minimizando o impacto na capacidade de entrega futura.