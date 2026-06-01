<!--
Slides executivos do Motor Prescritivo PRB.

Formato: cada slide separado por `---` (linha horizontal).
Compatível com:
  - Marp / Reveal.js / Pandoc para gerar PDF/PPT.
  - Leitura direta no GitHub/VSCode (renderiza como sequência de seções).

Para gerar PDF (opcional):
  npx @marp-team/marp-cli APRESENTACAO.md --pdf
-->

# Motor Prescritivo PRB

### Antecipação de problemas via análise semântica de incidentes

**Apresentação executiva** · Maio/2026
**Audiência:** Jéssica, Victor, Bruno + Coordenação

---

## O problema (antes do motor)

**Cenário operacional típico:**

- Analista A pega INC: "VPS-01 não pinga" → reinicia → fecha em 30 min.
- 8h depois, Analista B (plantão noite): mesma INC, mesmo servidor → reinicia → fecha.
- 36h depois, Analista C: idem.
- **Sábado, madrugada:** servidor cai de vez. Crise P1.

**Cada analista tratou um evento isolado.** Ninguém viu o padrão.

**Custo:**
- 🔥 Crise inevitável.
- ⏰ Tempo desperdiçado em ações repetitivas.
- 📉 Cliente impactado várias vezes antes da resolução real.

---

## A solução em 1 minuto

A cada **15 minutos**, o motor:

1. 📥 Lê todas as INCs/chamados das últimas 24h (Postgres).
2. 🧩 **Agrupa por similaridade semântica** — INCs do "mesmo assunto" viram um cluster.
3. 📊 Calcula **scores** (criticidade, ineficiência do time).
4. ⚖️ Aplica a **matriz oficial P1-P5** automaticamente.
5. 💡 **Sugere ação:** abrir PRB / repriorizar PRB existente / monitorar.
6. 🌡️ **Avalia saúde dos clientes recorrentes** (≥3 INCs em 6 meses).
7. 📤 Notifica: **Slack** (críticos) + **Dashboard** (todos) + **Postgres** (histórico).

**Resultado operacional:** plantão recebe alerta proativo **antes** do problema escalar.

---

## Como funciona — visão geral

```
┌──────────────────────────────────────────────────────┐
│  POSTGRES (lwsa.* + dynamics.* + kinghost.*)         │
└──────────────────────┬───────────────────────────────┘
                       ↓ (a cada 15 min)
┌──────────────────────────────────────────────────────┐
│  MOTOR PRB-INC                                       │
│                                                      │
│  ① Lê INCs + chamados + PRBs                         │
│  ② Agrupa INCs similares (NLP)                       │
│  ③ Calcula scores                                    │
│  ④ Aplica matriz P1-P5                               │
│  ⑤ Avalia Saúde do Cliente                           │
│                                                      │
└────────┬──────────────┬──────────────┬───────────────┘
         ↓              ↓              ↓
    ┌────────┐    ┌──────────┐    ┌─────────┐
    │ Slack  │    │Dashboard │    │Postgres │
    │(crítico)│   │  (JSON)  │    │(histórico)│
    └────────┘    └──────────┘    └─────────┘
```

---

## Requisitos atendidos

Levantados na reunião original:

| Requisito | Quem pediu | Status |
|---|---|---|
| Agrupar INCs por similaridade (não só por texto literal) | Jéssica | ✅ |
| Detectar **mesmo CI** gerando INCs repetidas em dias diferentes | Victor | ✅ |
| **Sugerir repriorização** de PRB existente (ex.: P3 → P2) | Jéssica | ✅ |
| Cruzar com **volume de chamados** Locaweb + Kinghost | Jéssica | ✅ |
| **Saúde do Cliente** — clientes com ≥3 INCs em 6 meses | Emerson/Bruno | ✅ |
| Slack para crítico + Dashboard tabulado | Reunião | ✅ |
| Antecipar com **5 INCs P3 idênticas** | Reunião | ✅ Gatilho proativo |

**Todos os 7 requisitos do levantamento original implementados.**

---

## Exemplo concreto — Alerta crítico

**O que o time recebe no Slack quando o motor detecta crise:**

```
🚨🆘 *Motor Prescritivo PRB — Alerta CRITICA*
_Ação sugerida: *ABRIR_PRB* | Prioridade: *P1*_

*Cluster:* checkout indisponivel contratacao
*Produto:* CAL
*Servidor/CI:* cal-frontend-03.locaweb.local
*INCs no cluster:* 3
*Score Criticidade:* 0.66 | *Ineficiência:* 0.38
*Chamados (24h, produto):* 16
*CIs recorrentes (15d):* cal-frontend-03.locaweb.local

*Justificativas:*
    • Contratação indisponível, sem solução de contorno total (P1).
    • CI(s) com recorrência em 15 dias: cal-frontend-03.locaweb.local.
    • 16 chamados no último dia para o produto CAL (impacto real).
```

**🆘 = abrir PRB novo. 🔧 = repriorizar PRB existente.** Identificação visual em 1 segundo.

---

## Saúde do Cliente — antes vs. depois

### Antes (manual)

Cliente liga no plantão noturno. Analista precisa:
1. Abrir ServiceNow, buscar INCs do cliente, exportar histórico (~5 min).
2. Abrir Dynamics, buscar chamados, exportar (~5 min).
3. Intercalar manualmente por data num Excel (~5 min).

**Total: 10-15 min de garimpagem por cliente.**

### Depois (motor)

Coordenador abre dashboard. Card do cliente já mostra:

```
🌡️ cliente005 — RECORRÊNCIA ALTA
22 INCs em 6 meses · 18 chamados · Severidade 0.48

🟢 INC1000050  ServiceNow   2h atrás · P3
💬 CAS-500023  Locaweb      3h atrás
🟢 INC1000047  ServiceNow   8h atrás · P3
💬 CAS-500012  Kinghost     2 dias atrás
🟢 INC0900150  ServiceNow   1 mês atrás · P2
                                            [...]
```

**Tempo: 5 segundos.**

---

## Onde os dados vivem — 3 saídas em paralelo

| Saída | Quem consome | Latência |
|---|---|---|
| **Slack** | Plantão (push de crítico) | Instantâneo |
| **Dashboard JSON** | Coordenadores (front-end visual) | A cada 15 min |
| **Postgres** | PO/Liderança (análise histórica via SQL) | A cada 15 min |

**Por que 3 saídas:**
- Cada audiência tem necessidade diferente.
- Se Slack cair, dashboard ainda existe.
- Se banco cair, JSON ainda existe.
- **Resiliência** garantida.

---

## Análises possíveis pelo histórico Postgres

Queries SQL ricas habilitadas pelo histórico de 30 dias:

**📈 Tendência semanal:**
> "Quantos alertas críticos por dia na última semana?"

**👥 Clientes piorando:**
> "Quais clientes tiveram severidade média subindo nos últimos 30 dias?"

**🖥️ CIs crônicos:**
> "Quais servidores aparecem em mais de 50 ciclos do motor (recorrência sistêmica)?"

**⏱️ Saúde do motor:**
> "Tempo médio de cada ciclo nas últimas 24h? Algum pico?"

**Sem o motor:** essas perguntas exigiriam horas de análise manual.

---

## Resultados do MVP (mock de validação)

**Dataset sintético com 91 INCs simuladas:**

| Métrica | Valor |
|---|---|
| INCs processadas | 91 em 4,5 segundos |
| Clusters identificados | 5 (todos com tema coerente) |
| Prescrições geradas | 5 (1 crítica, 2 altas, 1 média) |
| Clientes em recorrência alta | 13 |
| CIs recorrentes detectados | 4 servidores |
| Erros | 0 |

**Validação técnica:**

- ✅ **54 testes automatizados** passando (cobertura de regras, scores, parsers).
- ✅ **Bug de regressão protegido** (caso "ra" / "fora" não pode voltar).
- ✅ **Persistência funcional** em Postgres + JSON paralelo.

---

## Decisões de produto preservadas

O que o motor **NÃO faz** — por princípio:

| O que NÃO faz | Por quê |
|---|---|
| Abrir PRB automaticamente no SNow | Motor **sugere**, humano decide |
| Repriorizar PRB sem aprovação humana | Princípio de segurança operacional |
| Rebaixar prioridade automaticamente | Conservadorismo — só sugere upgrade |
| Decidir P5 sozinho | P5 exige confirmação de Coordenador/PO |
| Aprender por feedback (ML) | Regras determinísticas auditáveis > caixa-preta |

**Auditabilidade é prioridade.** Toda decisão automatizada explica-se em texto livre (justificativas no Slack/dashboard).

---

## O que falta para subir em produção

Pendências **não-técnicas** (apenas configuração):

- [ ] **Webhook Slack** real (env `SLACK_WEBHOOK_URL`).
- [ ] **Canal Slack** criado (sugestão: `#prb-alertas` ou `#noc-alertas`).
- [ ] **Conta de banco** com `SELECT` nos schemas relevantes + `INSERT` em `lwsa.motor_*`.
- [ ] **Supervisor** (systemd/Docker) para restart automático.
- [ ] **Monitoração externa** (Site24x7) com query "motor está vivo?".

**Pendências técnicas:** zero. Código validado e pronto.

---

## Próximos passos sugeridos

### Curto prazo (0–4 semanas)

1. **Deploy em staging:** apontar para banco real, validar dados reais por 1 semana.
2. **Calibrar `DBSCAN_EPS`** se clusters não fizerem sentido com volume real.
3. **Habilitar Slack** após validação no dashboard.

### Médio prazo (1–3 meses)

4. **Front-end visual** consumindo o JSON/Postgres (dashboard de coordenadores).
5. **Monitoração externa** integrada.
6. **Cleanup TTL automático** após DBA conceder permissão DELETE.

### Longo prazo (3+ meses)

7. **Análise de tendência** (motor stateful — comparar ciclos).
8. **Integração bidirecional com SNow** (escrever PRBs) — somente após validação extensa.

---

## Métricas de sucesso propostas

Para acompanhar o ROI do motor após 30 dias em produção:

| Métrica | Como medir |
|---|---|
| **Antecipação de PRBs** | Quantos PRBs foram abertos via sugestão proativa (5+ P3 idênticas)? |
| **Repriorização correta** | Quantos PRBs subiram de P3 para P2 via sugestão do motor? |
| **Redução de garimpagem** | Tempo médio de plantão por incidente complexo (antes vs. depois) |
| **Saúde do Cliente** | Clientes com recorrência alta identificados / total de alertas P1 mensais |

**Hipótese a validar:** motor identifica 60-80% das crises antes delas virarem P1, ganhando 24-72h de antecedência.

---

## Resumo executivo

**O que entregamos:**
- ✅ MVP funcional rodando localmente.
- ✅ Atende **todos os 7 requisitos** do levantamento original.
- ✅ Lógica de negócio **auditável** (matriz P1-P5 + justificativas textuais).
- ✅ **Resiliente** (defesa em 4 camadas, motor sempre funciona).
- ✅ **Documentado** (3 docs separadas para 3 audiências + glossário).
- ✅ **Testado** (54 testes automatizados, regressão protegida).
- ✅ Compatível com infra atual (Postgres 9.2/9.3, sem upgrade necessário).

**Próximo passo concreto:** decisão sobre subir staging.

---

## Perguntas / discussão

**Pontos para alinhar:**

1. **Calibração:** os thresholds atuais (P2 = 5 sem contorno, gatilho = 5 P3, etc.) batem com a realidade operacional?

2. **Canal Slack:** time prefere alertas individuais (atual) ou consolidados num resumo de 15 min?

3. **Cleanup TTL:** vale solicitar GRANT DELETE para a conta do motor ou DBA cuida manualmente?

4. **Próxima fase:** front-end visual ou expansão das regras P1-P5?

5. **Métricas de sucesso:** quais critérios para considerar o motor "validado"?

---

## Obrigado

**Motor Prescritivo PRB** · Emerson Ramos · Maio/2026

**Para detalhes técnicos:**
- `docs/ARQUITETURA.md` — como o motor foi construído
- `docs/MANUAL.md` — como usar
- `docs/REGRAS.md` — matriz oficial P1-P5
- `GLOSSARIO.md` — termos técnicos

**Código:** `Motor PRB-INC/` (12 módulos Python, 3.205 linhas)

**Testes:** `python -m pytest tests/` (54 testes, 0.13s)