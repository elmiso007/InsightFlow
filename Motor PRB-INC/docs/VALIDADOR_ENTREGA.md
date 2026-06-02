# ValidadorEntrega — Processo Completo (V3)

> **Audiência:** Change Team, PO, coordenadores, analistas que vão consumir
> os veredictos. Para detalhe de implementação ver [ARQUITETURA.md](ARQUITETURA.md).
> Para regras de thresholds ver [REGRAS.md](REGRAS.md). Para termos
> técnicos ver [../GLOSSARIO.md](../GLOSSARIO.md).

Este documento descreve **ponta a ponta** como o motor avalia retrospectivamente
PRBs entregues pelo Change Team — fechando o loop de qualidade do fix.

---

## Sumário

1. [O que é](#1-o-que-é)
2. [Por que existe (preventivo vs retrospectivo)](#2-por-que-existe-preventivo-vs-retrospectivo)
3. [Fluxo do processo](#3-fluxo-do-processo)
4. [Quais PRBs entram](#4-quais-prbs-entram)
5. [Os 4 sinais coletados por PRB](#5-os-4-sinais-coletados-por-prb)
6. [Veredicto (REINCIDENCIA / ENTREGA_VALIDADA / INCONCLUSIVO)](#6-veredicto-reincidencia--entrega_validada--inconclusivo)
7. [Volumetria pré-resolução](#7-volumetria-pré-resolução)
8. [Δ chamados vinculados (V3)](#8-δ-chamados-vinculados-v3)
9. [PRBs novos pós-resolução](#9-prbs-novos-pós-resolução)
10. [O que aparece no dashboard / banco / Slack](#10-o-que-aparece-no-dashboard--banco--slack)
11. [Como interpretar (operacional)](#11-como-interpretar-operacional)
12. [Cadência e agendamento](#12-cadência-e-agendamento)
13. [Como ajustar](#13-como-ajustar)
14. [Histórico de versões (V1 → V2 → V3)](#14-histórico-de-versões-v1--v2--v3)
15. [Limitações conhecidas](#15-limitações-conhecidas)

---

## 1. O que é

Módulo automático que, a cada **6 horas** (entry-point separado do motor
preventivo), lista os PRBs **encerrados pelo Change Team nos últimos 14
dias** e emite um **veredicto** sobre cada um:

- `REINCIDENCIA` — o problema voltou (≥3 INCs novas no mesmo CI)
- `ENTREGA_VALIDADA` — o fix segurou (0 INCs novas + ≥7 dias decorridos)
- `INCONCLUSIVO` — ainda cedo pra decidir (janela curta, sinais ambíguos)

Além do veredicto, cada PRB carrega **3 sinais adicionais** (V3):
volumetria pré-resolução, Δ de chamados vinculados pré/pós, e lista de
PRBs novos abertos no mesmo CI.

**Implementação:**
- Módulo: [validador_entrega.py](../validador_entrega.py)
- Entry-point: [validar_entregas.py](../validar_entregas.py)
- Wrapper Windows: [Motor-PRB-Validador.bat](../Motor-PRB-Validador.bat)
- Persistência: tabela `lwsa.motor_validacao_entrega` (21 colunas)

---

## 2. Por que existe (preventivo vs retrospectivo)

O motor opera em **2 prismas independentes**:

| Prisma | Quando olha | Pergunta que responde |
|---|---|---|
| **Preventivo** (`main.py` + `rules_engine.py`) | INCs ativas das últimas 24h | "**Quais PRBs eu deveria abrir AGORA?**" |
| **Retrospectivo** (`validar_entregas.py` + `validador_entrega.py`) | PRBs já entregues nos últimos 14d | "**Os PRBs que o CT entregou realmente resolveram?**" |

**Por que separar:** se o CT fecha um PRB hoje, é cedo demais pra saber se
o fix segurou. Olhar uma vez ao dia (na verdade, a cada 6h) basta. Já o
preventivo precisa rodar de 15 em 15 min pra capturar escaladas.

**Requisito original:** a Diretoria/PO queria saber "**dos PRBs que abrimos,
quantos realmente resolveram o problema?**" Essa pergunta é o coração do
ValidadorEntrega.

---

## 3. Fluxo do processo

```
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 1 — Listar PRBs candidatos                                     │
└─────────────────────────────────────────────────────────────────────┘

  fonte_inc.listar_prbs_para_validacao(dias=14)
        ↓
  SELECT ... FROM lwsa.service_now_problems
  WHERE status IN ('Encerrado Automaticamente', 'Concluído')
    AND data_encerrado IS NOT NULL
    AND data_encerrado >= NOW() - INTERVAL '14 days'
    AND organizacao IN ('Locaweb')
        ↓
  ~10 PRBs candidatos

┌─────────────────────────────────────────────────────────────────────┐
│  FASE 2 — Avaliar cada PRB (4 sinais)                                │
└─────────────────────────────────────────────────────────────────────┘

  para cada PRB:
    ├─ SINAL 1: Veredicto
    │     INCs no (produto, servidor) com data_abertura >= data_encerrado
    │     _classificar(qtd_pos, dias_pos) → REINCIDENCIA/VALIDADA/INCONCLUSIVO
    │
    ├─ SINAL 2: Volumetria pré-resolução (60 dias antes)
    │     contar_incidentes_no_ci_periodo
    │     → {qtd, clientes_unicos, categorias}
    │
    ├─ SINAL 3: Δ chamados VINCULADOS (V3)
    │     listar_incidentes_por_produto_servidor(janela_pre)  → incs_pre
    │     listar_incidentes_por_produto_servidor(janela_pos)  → incs_pos
    │     contar_chamados_vinculados(prb_id, incs_pre, ...)   → chamados_pre
    │     contar_chamados_vinculados(prb_id, incs_pos, ...)   → chamados_pos
    │     delta_chamados_pct = (pos - pre) / pre
    │
    └─ SINAL 4: PRBs novos pós-resolução
          listar_prbs_novos_no_ci_periodo(produto, servidor,
                                           desde=data_resolucao,
                                           ignorar_prb_id=prb.prb_id)
          → ["PRB0012345", ...]

┌─────────────────────────────────────────────────────────────────────┐
│  FASE 3 — Saída (3 destinos, defesa em camadas)                      │
└─────────────────────────────────────────────────────────────────────┘

  ┌── output/validacoes_entrega.json (JSON do dashboard)
  ├── lwsa.motor_validacao_entrega   (21 colunas persistidas)
  └── Slack                           (1 mensagem POR REINCIDENCIA detectada)
```

**Tempo medido:** ~20-30s para 10 PRBs (com índices no DW).

---

## 4. Quais PRBs entram

Os PRBs candidatos atendem **4 critérios cumulativos**:

| Critério | Configuração | Por quê |
|---|---|---|
| Status encerrado | `STATUS_PRB_ENCERRADOS = ("Encerrado Automaticamente", "Concluído")` | Outros status como "Aguardando Validação" têm `data_encerrado` NULL no DW |
| `data_encerrado` não nula | implícito | Sem data confiável não dá pra calcular janela |
| Janela de 14 dias | `JANELA_VALIDACAO_ENTREGA_DIAS = 14` | PRB de mais de 14d já foi avaliado em ciclos anteriores |
| Organização ativa | `ORGANIZACOES_ATIVAS = ("Locaweb",)` | Foco atual; KingHost desligado |

PRBs **sem `produto` ou sem `servidor`** entram, mas viram `INCONCLUSIVO`
direto (sem `CI` confiável não dá pra match).

---

## 5. Os 4 sinais coletados por PRB

Cada `ValidacaoEntrega` carrega:

### Sinal 1 — Veredicto (campo `veredicto`)

`REINCIDENCIA`, `ENTREGA_VALIDADA` ou `INCONCLUSIVO` — ver §6.

### Sinal 2 — Volumetria pré-resolução

3 campos: `qtd_incs_pre_resolucao`, `clientes_unicos_pre`, `categorias_pre`.
Ver §7.

### Sinal 3 — Δ chamados vinculados

3 campos: `chamados_pre`, `chamados_pos`, `delta_chamados_pct`. Ver §8.

### Sinal 4 — PRBs novos pós-resolução

2 campos: `qtd_prbs_novos_pos_resolucao`, `prbs_novos` (lista de
`numero`). Ver §9.

---

## 6. Veredicto (REINCIDENCIA / ENTREGA_VALIDADA / INCONCLUSIVO)

Classificação aplicada via `_classificar(qtd_incs, dias_pos)`:

```python
if qtd_incs >= LIMIAR_INCS_REINCIDENCIA:          # 3
    return "REINCIDENCIA"
if qtd_incs == 0 and dias_pos >= MIN_DIAS_PARA_VALIDAR:  # 7
    return "ENTREGA_VALIDADA"
return "INCONCLUSIVO"
```

| Veredicto | Condição | Slack? |
|---|---|---|
| `REINCIDENCIA` | ≥ 3 INCs novas em `(produto, servidor)` após `data_encerrado` | ✅ |
| `ENTREGA_VALIDADA` | 0 INCs novas E ≥ 7 dias decorridos desde resolução | ❌ |
| `INCONCLUSIVO` | Casos intermediários (janela < 7d, INCs sub-limiar) | ❌ |

**Reincidência tem precedência sobre tempo:** se aparecem 3+ INCs no 2º dia,
ainda é reincidência. O time precisa ver isso rápido.

### O match (produto, servidor)

INC nova é detectada via:

```sql
SELECT * FROM lwsa.service_now_incidentes
WHERE produto = %s    -- prb.produto
  AND servidor = %s   -- prb.servidor
  AND data_abertura >= %s   -- data_encerrado do PRB
  AND organizacao IN ('Locaweb');
```

Match **exato**. PRB e INC compartilham o mesmo schema, então a taxonomia
bate. Sem fuzzy matching.

---

## 7. Volumetria pré-resolução

**Janela:** `JANELA_VOLUMETRIA_PRE_DIAS = 60` dias **antes** de `data_encerrado`.

```sql
SELECT
    COUNT(*) AS qtd,
    COUNT(DISTINCT login_cliente) AS clientes_unicos,
    COUNT(DISTINCT categoria) AS categorias
FROM lwsa.service_now_incidentes
WHERE produto = %s AND servidor = %s
  AND data_abertura >= %s   -- data_encerrado - 60d
  AND data_abertura <  %s   -- data_encerrado
  AND organizacao IN ('Locaweb');
```

**Por que esse sinal:** diferencia "PRB que apagou 50 INCs em 60 dias" de
"PRB que apagou 2 INCs". O tamanho do problema resolvido é uma métrica de
**impacto** do Change Team.

**Como interpretar:**

| qtd_incs_pre | clientes_unicos_pre | Leitura |
|---|---|---|
| Alto (≥ 20) + alta diversidade de clientes | ≥ 10 | Problema **sistêmico** — afetava muitos clientes |
| Alto (≥ 20) + poucos clientes | < 5 | Cliente específico ruidoso (1-2 enterprise rebobinando) |
| Baixo (< 5) | qualquer | PRB pequeno — pouco impacto |

---

## 8. Δ chamados vinculados (V3)

**Janela:** `JANELA_CHAMADOS_DELTA_DIAS = 14` dias em cada lado de
`data_encerrado` (simétrica).

### O match (V3 — substituiu V2)

```sql
SELECT COUNT(*) FROM dynamics.chamados
WHERE datacriacao >= %s            -- início da janela (pré OU pós)
  AND datacriacao <  %s            -- fim da janela
  AND (
        prb = %s                       -- chamado vinculado direto ao PRB
        OR (
            inc IS NOT NULL
            AND inc IN (%s, %s, ...)   -- vinculado a INC do CI no período
        )
      );
```

### Por que esse match e não outro

| Estratégia | Cobertura | Precisão | Decisão |
|---|---|---|---|
| Match por palavra-chave no produto | Alta | Baixa (falsos positivos) | V2 original — descartada |
| Match exato `chamados.produto = prb.produto` | Alta | Média (taxonomia raramente bate) | V2 (2026-06-02 cedo) — substituída |
| `chamados.prb = prb.numero` apenas | Baixa (1.4%) | Alta | Descartada (muitos `0/0`) |
| **`chamados.prb` OR `chamados.inc IN(...)`** | Média (~5%) | **Alta** | **V3 (atual)** |

O **OR** é importante: captura chamados rotulados explicitamente com o PRB
(`prb = 'PRB0070000'`) **e** chamados que falam de qualquer INC do CI no
período (`inc IN (incs_pre)`).

### Como interpretar

`delta_chamados_pct = (chamados_pos - chamados_pre) / chamados_pre`

| Δ | Significado | Slack |
|---|---|---|
| `< -0.5` (queda ≥ 50%) | Fix funcionou — contato caiu | ↓ |
| `~0` | Sem mudança ou sem cobertura | sem seta |
| `> +0.5` (subida ≥ 50%) | Fix não funcionou ou piorou | ↑ |

**`0/0` é informação válida:** indica que esse PRB não tem chamados
vinculados explícitos — o que pode significar "fix sem ruído" OU "ETL não
está rotulando bem". Não tente "encher" o sinal com match aproximado.

### Exemplo real (execução do DB de produção)

```
PRB0055135 (REINCIDENCIA, 13 INCs novas):
  chamados_pre = 6, chamados_pos = 8, delta = +33%
  → fix falhou DUPLAMENTE (volume de INCs + contato subindo)
```

Esse é o tipo de sinal que justifica **reabrir o caso** com o CT.

---

## 9. PRBs novos pós-resolução

**Janela:** mesma do veredicto (de `data_encerrado` até `NOW()`).

```sql
SELECT numero FROM lwsa.service_now_problems
WHERE produto = %s AND servidor = %s
  AND data_abertura >= %s   -- data_encerrado do PRB original
  AND numero <> %s          -- defensivo: não conta o próprio PRB
  AND organizacao IN ('Locaweb')
ORDER BY data_abertura DESC;
```

### Por que esse sinal

Reincidência por INCs já é capturada no Sinal 1. Mas se o problema voltou
**como um PRB novo** (em vez de só INCs soltas), é um **sinal mais grave**:
indica que o Change Team teve que reabrir o caso formalmente — provavelmente
porque o fix original tratou sintoma, não causa raiz.

### Como o coordenador usa

| Situação | Leitura |
|---|---|
| `qtd_prbs_novos = 0` | Bom. Nenhum PRB reaberto pro mesmo CI |
| `qtd_prbs_novos = 1` | Atenção. Problema voltou em outra forma |
| `qtd_prbs_novos ≥ 2` | **Alerta.** Padrão de fix falho — investigar causa raiz |

No Slack: `*PRBs novos no CI:* N (PRB123, PRB456)` quando ≥ 1.

---

## 10. O que aparece no dashboard / banco / Slack

### `lwsa.motor_validacao_entrega` (21 colunas)

| Grupo | Colunas |
|---|---|
| Identificação | `id`, `execucao_id`, `prb_id`, `descricao_curta`, `produto`, `servidor`, `status_prb`, `data_resolucao` |
| Veredicto | `dias_pos_resolucao`, `qtd_incs_pos_resolucao`, `veredicto`, `incs_reincidentes` (JSON) |
| Contexto PRB | `grupo_designado`, `data_abertura_prb` |
| **Volumetria pré** | `qtd_incs_pre_resolucao`, `clientes_unicos_pre`, `categorias_pre` |
| **Δ chamados V3** | `chamados_pre`, `chamados_pos`, `delta_chamados_pct` |
| **PRBs novos** | `qtd_prbs_novos_pos_resolucao`, `prbs_novos` (JSON) |

### `output/validacoes_entrega.json`

Mesma estrutura, em JSON. Consumido pelo front-end / Power BI.

### Slack (quando habilitado)

```
⚠️🔁 PRB PRB0055135 — REINCIDÊNCIA DETECTADA
Descrição: Ações do Post-Mortem INC4629249 - RITM0296949
Produto: Locaweb - Email
Servidor/CI: Email Locaweb
Grupo designado: NOC
Resolvido em: 2026-05-28 (5d atrás)
Pré-resolução (60d): 25 INCs · 8 clientes · 3 categorias
Pós-resolução: 13 novas INCs no mesmo (produto, servidor)
Δ Chamados vinculados (14d): 6 → 8 (+33.3%) ↑
PRBs novos no CI: 1 (PRB0072001)
INCs: INC8847001 (P3), INC8847002 (P3), INC8847005 (P2) (+10)
_Change Team: validar se o fix entregue cobre os novos casos._
```

Disparo somente para `veredicto = REINCIDENCIA`. Validações OK ou
inconclusivas não geram Slack (evita ruído).

---

## 11. Como interpretar (operacional)

| Cenário | Volumetria pré | Δ chamados | PRBs novos | Veredicto | Leitura |
|---|---|---|---|---|---|
| Fix excelente — grande problema resolvido | Alta (50+ INCs) | ↓ (>50%) | 0 | ENTREGA_VALIDADA | **Modelo a replicar.** |
| Fix limpo de PRB pequeno | Baixa (2-5 INCs) | 0/0 | 0 | ENTREGA_VALIDADA | OK. Sem cobertura no Dynamics, mas sem reincidência. |
| Problema voltou em outra forma | Qualquer | Qualquer | ≥ 1 PRB | REINCIDENCIA OU INCONCLUSIVO | **Reabrir/investigar causa raiz.** |
| Fix piorou (contato subiu) | Qualquer | ↑ (>50%) | 0 | REINCIDENCIA | **Re-investigar URGENTE.** |
| Janela curta, sem dado | — | — | 0 | INCONCLUSIVO | Aguardar próximo ciclo. |
| Fix segurou as INCs mas contato subiu | Qualquer | ↑ (>50%) | 0 | ENTREGA_VALIDADA | Estranho. Talvez chamados não relacionados — auditar manualmente. |

---

## 12. Cadência e agendamento

### Cadência default

`DEFAULT_INTERVALO_HORAS = 6` em [validar_entregas.py](../validar_entregas.py).

Disparos sugeridos no Task Scheduler: **00:05, 06:05, 12:05, 18:05** (fora
do horário de pico).

### Por que 6h e não 15min como o preventivo

| Motivo | Detalhe |
|---|---|
| **PRBs mudam devagar** | Status de PRB resolvido não vira hora em hora — olhar a cada 6h é o suficiente |
| **Janela de 14d é grande** | Mesmo PRB candidato sai do ciclo 14 dias depois — variações entre olhares de 6h são desprezíveis |
| **Performance** | Avaliar 10 PRBs com 4 sinais leva ~20-30s; pagar isso 96×/dia (a cada 15min) é desperdício |
| **Isolamento de falha** | Se ValidadorEntrega bugar, o preventivo (`main.py`) continua intacto |

### Como agendar (Windows Task Scheduler)

Ver passo a passo completo em **[MANUAL.md §2.7](MANUAL.md#27-agendamento-do-validadorentrega-prisma-retrospectivo)**.

Resumo: criar 2ª task no Task Scheduler apontando para
`Motor-PRB-Validador.bat`, disparo `Daily 00:05` com `Repeat every 6 hours`.

---

## 13. Como ajustar

Todos os ajustes em [config.py](../config.py):

### Mais sensível a reincidência

```python
LIMIAR_INCS_REINCIDENCIA = 2   # antes: 3
```

Cuidado: pode aumentar muito o volume de alertas Slack.

### Janela maior pra "validar" um PRB

```python
MIN_DIAS_PARA_VALIDAR = 14   # antes: 7
```

Útil se sentir que 7d é cedo demais pra confirmar que o fix segurou.

### Janela de visibilidade de PRBs

```python
JANELA_VALIDACAO_ENTREGA_DIAS = 30   # antes: 14
```

PRBs mais antigos voltam a ser avaliados todo ciclo. Cuidado com volume.

### Janela maior pra volumetria pré

```python
JANELA_VOLUMETRIA_PRE_DIAS = 90   # antes: 60
```

Pra capturar PRBs lentos (problema crescendo por meses antes do fix).

### Janela do Δ chamados

```python
JANELA_CHAMADOS_DELTA_DIAS = 7   # antes: 14
```

Janela menor é mais sensível a mudança imediata pós-fix.

### Limiar de redução pra mostrar ↓ no Slack

```python
LIMIAR_REDUCAO_CHAMADOS_PCT = -0.3   # antes: -0.5
```

Default conservador (queda ≥ 50% pra marcar ↓). Reduzir pra `-0.3` deixa
a seta aparecer com queda ≥ 30%.

### Status considerados "encerrados"

```python
STATUS_PRB_ENCERRADOS = (
    "Encerrado Automaticamente",
    "Concluído",
    "Aguardando Validação da Resolução",   # adicionar se DW começar a popular data_encerrado
)
```

Verificar se o status tem `data_encerrado` confiável no DW antes de
adicionar — senão vira INCONCLUSIVO eterno.

---

## 14. Histórico de versões (V1 → V2 → V3)

### V1 (motor original)

- Apenas veredicto (`REINCIDENCIA` / `ENTREGA_VALIDADA` / `INCONCLUSIVO`)
- 11 colunas em `motor_validacao_entrega`

### V2 (2026-06-02, ValidadorEntrega V2)

- Adiciona contexto enriquecedor:
  - Volumetria pré-resolução (60d antes)
  - Δ chamados pré/pós (14d simétrico) com match por `produto`
- Adiciona `grupo_designado` e `data_abertura_prb`
- 19 colunas em `motor_validacao_entrega` (+8 da V2)
- **Limitação observada:** match por produto trazia ruído (falsos positivos
  de chamados em outros assuntos do mesmo produto)

### V3 (2026-06-02, ValidadorEntrega V3 atual)

- Substitui match por produto: agora `chamados.prb = prb_id` **OU**
  `chamados.inc IN (incs)` — match explícito via vínculo
- Adiciona rastreamento de **PRBs novos pós-resolução** (`qtd_prbs_novos_pos_resolucao`,
  `prbs_novos`)
- 21 colunas em `motor_validacao_entrega` (+2 da V3)
- **Ganho mensurado:** `0/0` honesto quando não há vínculo (em vez de
  inflar com ruído). PRBs com vínculo real revelam Δ preciso (ex.:
  PRB0055135 mostrou +33% com 13 INCs reincidentes — sinal duplo de falha).

### Versão "Radar CT" (revertida)

Tentamos uma V2 antes com heurística de palavra-chave pra delta de chamados
e outras métricas complementares. Revertida em commit `b0ff9c4` —
heurística era frágil. Snapshot preservado no commit `6f0d783` se quiser
recuperar.

---

## 15. Limitações conhecidas

### Match de chamados depende do ETL

O Δ chamados V3 só funciona se `dynamics.chamados.prb` e
`dynamics.chamados.inc` estiverem preenchidos no DW. Cobertura observada:
~1.4% dos chamados têm `prb`, ~5.4% têm `inc`. Pra PRBs sem nenhum chamado
vinculado, o sinal fica `0/0`.

**Mitigação:** o **OR** entre `prb` e `inc` amplia a recuperação. Mas
sempre haverá PRBs sem chamados vinculados.

### Sem relação direta INC→PRB no DW

O DW não tem coluna que liga uma INC ao PRB que a consolidou. Por isso o
match `(produto, servidor)` é a única forma de "INC pertence ao escopo
deste PRB" — pode levar falsos positivos quando 2 PRBs cobrem o mesmo CI
ao mesmo tempo.

### Match exato produto/servidor (sem fuzzy)

Se o CT cria o PRB com produto/servidor ligeiramente diferente das INCs
originais, o validador não encontra reincidência. Aplicação real funciona
porque a taxonomia do SNow é consistente, mas casos limite existem.

### PRBs sem `data_encerrado` confiável ficam fora

Status como "Aguardando Validação da Resolução" no DW da Locaweb sempre
têm `data_encerrado` NULL. Ficam fora da janela de avaliação por design
(`STATUS_PRB_ENCERRADOS` exclui esse status).

### Volumetria pré não considera PRBs anteriores

Se um PRB anterior já tratou parte das INCs no período de 60d antes do
fix, a volumetria pré conta TODAS as INCs do CI no período — pode
**inflar** o sinal de "tamanho do problema". Não diferencia "INCs que
o PRB anterior já resolveu" de "INCs que este PRB resolveu".

**Mitigação:** olhar `data_abertura_prb` (idade do PRB) ajuda a contextualizar.

### Sem feedback do Change Team

O motor emite veredicto, mas não recebe retroalimentação ("foi falso
positivo", "este PRB é especial"). Não aprende. Pra calibrar é preciso
ajustar thresholds no `config.py` manualmente.

---

## Referências cruzadas

- **[REGRAS.md §14](REGRAS.md#14-validadorentrega--prisma-retrospectivo):** matriz operacional resumida
- **[ARQUITETURA.md](ARQUITETURA.md):** detalhes de implementação (`validador_entrega.py`)
- **[MANUAL.md §2.7](MANUAL.md#27-agendamento-do-validadorentrega-prisma-retrospectivo):** como agendar via Task Scheduler
- **[../GLOSSARIO.md](../GLOSSARIO.md):** termos técnicos (veredictos, volumetria, Δ chamados)
- **`config.py`:** todos os thresholds em um lugar
- **`sql/motor_tables.sql`:** DDL completa da `motor_validacao_entrega`

---

_Documento mantido por contribuidores do motor. Última atualização: 2026-06-02 (V3)._
