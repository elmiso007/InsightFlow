# Documentação - Sistema de Relatórios Semanais

## Visão Executiva

O **Sistema de Relatórios Semanais** é uma solução automatizada que processa dados de atendimento ao cliente, gera análises via Inteligência Artificial e produz relatórios executivos em PDF. O sistema opera com dados dos setores de **Suporte** e **Cobrança**, fornecendo insights sobre performance operacional.

## Fluxo de Processo

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Conexão BD    │───▶│  Extração Dados  │───▶│ Processamento   │
│   PostgreSQL    │    │  Views Semanais  │    │   por Setor     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Geração PDF    │◀───│  Análises via IA │◀───│  Cálculo de     │
│   e Envio       │    │    (OpenAI)      │    │   Métricas      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Principais Funcionalidades

### 📊 Análise de Métricas
- **TMA/TME**: Tempo Médio de Atendimento e Espera
- **Taxa de Abandono**: Percentual de contatos não atendidos
- **Volume de Atendimentos**: Por período, canal e equipe
- **Comparações Temporais**: Semana atual vs anterior vs média anual

### 🤖 Sistema WOZ (Wizard of Oz)
- **25+ Tipos de WOZ** para Suporte (Linux, WordPress, SSL, etc.)
- **Taxa de Resolução** automática por categoria
- **Análise Comparativa** entre períodos
- **Mapeamento Inteligente** de tags para tipos WOZ

### 📈 Net Promoter Score (NPS)
- **Cálculo Automático** baseado em 3 perguntas (P1, P2, P3)
- **Categorização** em Promotores, Neutros e Detratores
- **Análise de Comentários** via IA para insights qualitativos

### 🤖 Inteligência Artificial Integrada
- **4 Tipos de Análises**:
  1. Análise de Contatos Semanal
  2. Análise de Contatos Anual  
  3. Análise de NPS
  4. Análise de Comentários dos Clientes

## Arquitetura Técnica

### Fontes de Dados
```sql
-- View principal de dados semanais
SELECT * FROM teste.vw_report_semanal;

-- View específica para análise WOZ
SELECT * FROM lw_octadesk.vw_woz;
```

### Estrutura de Processamento

#### 1. **Configuração Inicial**
```python
setores = ['Suporte', 'Cobrança']
feriados_brasil = holidays.Brazil()
client = WebClient('slack_token')
```

#### 2. **Processamento Multi-Nível**
- **Por Setor** → **Por Canal** → **Por Equipe** (apenas Suporte)
- **Três Períodos**: Semana Atual, Semana Anterior, Média Anual
- **Múltiplas Métricas**: Operacionais, NPS, WOZ

#### 3. **Saída Automatizada**
- **PDF Estruturado** com gráficos e análises
- **Armazenamento** em diretório organizado

## Benefícios Operacionais

### ⚡ Automação Completa
- **Zero Intervenção Manual** no processo de geração
- **Execução Programada** via scripts batch
- **Tratamento de Erros** robusto com logs detalhados

### 📊 Insights Acionáveis
- **Comparações Temporais** para identificar tendências
- **Análises por IA** com recomendações específicas
- **Drill-down** até nível de equipe/canal

### 🎯 Precisão de Dados
- **Validação Automática** de dados de entrada
- **Cálculos Padronizados** para todas as métricas
- **Controle de Qualidade** integrado

## Indicadores-Chave (KPIs) Monitorados

### Operacionais
| Métrica | Descrição | Frequência |
|---------|-----------|------------|
| **TMA** | Tempo Médio de Atendimento | Semanal |
| **TME** | Tempo Médio de Espera | Semanal |
| **Taxa de Abandono** | % de contatos não atendidos | Semanal |
| **Volume Total** | Contatos recebidos/atendidos | Semanal |

### Qualidade
| Métrica | Descrição | Frequência |
|---------|-----------|------------|
| **NPS P1** | Satisfação com atendimento | Semanal |
| **NPS P2** | Satisfação com resolução | Semanal |
| **NPS P3** | Recomendação da empresa | Semanal |
| **Comentários** | Feedback qualitativo | Semanal |

### Eficiência (WOZ)
| Métrica | Descrição | Frequência |
|---------|-----------|------------|
| **Taxa de Resolução WOZ** | % resolvidos automaticamente | Semanal |
| **Volume por Tipo** | Distribuição por categoria | Semanal |
| **Eficiência Comparativa** | Variação entre períodos | Semanal |

## Outputs Gerados

### 📄 Relatório PDF Executivo
**Estrutura do Relatório:**
1. **Resumo Executivo** - Métricas principais
2. **Análise Semanal** - Comparação com semana anterior
3. **Análise Anual** - Comparação com média do ano
4. **Breakdown por Canal** - Performance por canal
5. **Análise por Equipe** - Detalhamento (apenas Suporte)
6. **NPS e Satisfação** - Indicadores de qualidade
7. **Análise WOZ** - Eficiência da automação
8. **Comentários dos Clientes** - Insights qualitativos

## Manutenção e Monitoramento

### 🔍 Sistema de Logs
```python
logger = configurar_logger()
# Logs detalhados de cada etapa do processo
# Tratamento específico para diferentes tipos de erro
# Notificação automática em caso de falha
```

### ⚠️ Tratamento de Erros
- **Validação de Dados** antes do processamento
- **Fallback Automático** para análises com erro
- **Continuidade de Processo** mesmo com falhas parciais
- **Logs Estruturados** para debugging

### 📊 Métricas de Sistema
- **Tempo de Processamento** por setor
- **Taxa de Sucesso** na geração de relatórios
- **Volume de Dados** processados
- **Performance da IA** nas análises

## Roadmap e Melhorias

### 🔧 Otimizações Planejadas
1. **Cache de Dados** para melhor performance
2. **Paralelização** do processamento por setor
3. **Compressão de PDFs** para otimizar storage
4. **API RESTful** para integração com outros sistemas

## ROI e Impacto

### ⏱️ Economia de Tempo
- **Antes**: ~8 horas/semana de trabalho manual
- **Depois**: ~15 minutos/semana de supervisão
- **Economia**: 95% de redução de tempo

### 📈 Qualidade dos Insights
- **Padronização** completa de métricas
- **Análises via IA** que antes não existiam
- **Comparações Históricas** automáticas
- **Detalhamento Granular** por canal/equipe

### 🎯 Tomada de Decisão
- **Dados em Tempo Real** (semanalmente)
- **Insights Acionáveis** com recomendações específicas
- **Tendências Claras** para planejamento estratégico
- **Visibilidade Total** da operação

---

## Contatos Técnicos
- **Desenvolvedor**: Equipe de Automatizações
- **Banco de Dados**: PostgreSQL (10.30.138.28)
- **Logs**: `logs.log` e `function_logger`
- **Ambiente**: Produção - Locaweb

---
*Última atualização: Setembro 2025*
