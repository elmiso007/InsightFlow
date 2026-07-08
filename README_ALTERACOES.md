# Histórico de Alterações

---

## v2.4 — Julho 2026 — Correções de integridade e segurança

Esta versão resolve 9 problemas encontrados em análise arquitetural — nenhum bug visível
ao usuário final, mas todos com potencial de causar dados errados, falhas silenciosas ou
consumo desnecessário de recursos em produção.

### Correções aplicadas

---

#### Fix #1 — `analise_tipo` persistido com valor errado
**Arquivo:** `analise_ia.py`

O campo `analise_tipo` era gravado como `'NPS'` na tabela `rawdata_analise_nps_analistas`,
mas o SQL de promoção `insereDadosAnaliseNPS.sql` copiava o valor literalmente para a tabela
final `analise_nps_analistas`. Qualquer consulta com `WHERE analise_tipo = 'monitoramento_nps_analistas'`
retornava zero resultados.

**Correção:** valor alterado para `'monitoramento_nps_analistas'` no `cursor.execute()`.

---

#### Fix #2 — Código de execução no escopo do módulo (import bomb)
**Arquivo:** `verifica_nps.py`

O bloco principal de execução — abertura de conexão, query, processamento, análise IA,
notificação — estava no escopo global do módulo. Qualquer `import verifica_nps` em
outro script (ex.: testes, utilitários) disparava toda a análise imediatamente, com efeitos
colaterais no banco e na API Gemini.

**Correção:** todo o bloco foi encapsulado em `def main():`; adicionado guard
`if __name__ == '__main__': main()` no final do arquivo.

---

#### Fix #3 — `%bot%` causava falsos positivos em português
**Arquivo:** `analise_woz_detratores.py`

O padrão SQL `ILIKE '%bot%'` capturava palavras portuguesas legítimas como "trabalho",
"absolutamente", "robot" (sem acepção técnica), gerando comentários não relacionados ao
chatbot WOZ na amostra de detratores.

**Correção:** `'%bot%'` removido de `termos_simples`. Os termos `'%chatbot%'` e `'%woz%'`
já cobriam os casos legítimos com precisão suficiente.

---

#### Fix #4 — Contagem de tokens era estimativa por contagem de palavras
**Arquivo:** `analise_ia.py`

Os campos `token_prompt` e `token_completion` eram calculados como
`len(texto.split()) * 1.3`, uma heurística imprecisa que subestimava tokens de prompts
estruturados e superestimava tokens de respostas curtas.

**Correção:** os valores agora são lidos diretamente de `response.usage_metadata`
(`prompt_token_count` e `candidates_token_count`) disponibilizado pelo SDK do Gemini.
A estimativa por palavras permanece apenas como fallback quando a API não retorna metadados.

---

#### Fix #5 — Race condition em workers paralelos
**Arquivo:** `verifica_nps.py`

Com `PARALELO_MAX_WORKERS > 1`, dois workers podiam iniciar simultaneamente a análise do
mesmo analista: ambos passavam pela verificação `analise_ja_existe()` antes que qualquer um
dos dois gravasse o resultado, resultando em duas chamadas à API Gemini para o mesmo analista
no mesmo período.

**Correção:** adicionado `threading.Lock` (`_analise_lock`) e conjunto `_analises_em_andamento`.
O check de existência e a marcação como "em andamento" ocorrem dentro do mesmo lock, eliminando
a janela de corrida.

```
with _analise_lock:
    if nome in _analises_em_andamento or analise_ja_existe(...):
        return nome, "PULADO", []
    _analises_em_andamento.add(nome)
```

---

#### Fix #6 — Import morto de `slack_sdk`
**Arquivo:** `verifica_nps.py`

`import slack_sdk as sd` estava presente mas o módulo nunca era usado. A integração Slack
nunca foi implementada no arquivo. O import causava `ModuleNotFoundError` em ambientes sem
o pacote instalado e poluía o namespace do módulo.

**Correção:** import removido.

---

#### Fix #7 — SQL de promoção executado N vezes (uma por analista)
**Arquivos:** `analise_ia.py`, `verifica_nps.py`

O script `insereDadosAnaliseNPS.sql` (que copia rawdata → `analise_nps_analistas`) era
chamado dentro de `analise_ia_nps()`, função executada uma vez por analista pelo
`ThreadPoolExecutor`. Com 5 analistas críticos, o SQL rodava 5 vezes, causando tentativas
de inserção duplicada no período coberto pelos primeiros analistas.

**Correção:**
- `analise_ia_nps()` não executa mais o SQL de promoção.
- Extraída a função `executar_sql_pos_analise(conn)` em `analise_ia.py`.
- `verifica_nps.py` chama `executar_sql_pos_analise(conn)` uma única vez, após todos os
  `futures` do `ThreadPoolExecutor` completarem.

---

#### Fix #8 — `@lru_cache` em strings únicas (cache nunca atingido)
**Arquivo:** `analise_ia.py`

Duas funções de conversão de markdown para HTML tinham decorator `@lru_cache(maxsize=128)`
e `@lru_cache(maxsize=256)`. As entradas eram strings completas de markdown geradas pelo
Gemini — cada analista produzia uma string única, então o cache nunca tinha hits e apenas
acumulava entradas na memória sem nenhum benefício.

**Correção:** decorators removidos; a função wrapper que convertia lista → tupla para ser
hashável foi eliminada; a função foi simplificada para aceitar a lista diretamente.

---

#### Fix #9 — `historico.json` atualizado mesmo quando o banco falhou
**Arquivo:** `analise_woz_detratores.py`

`salvar_historico()` era chamado incondicionalmente após `salvar_no_banco()`, independente
do resultado. Se o banco falhasse (ex.: erro de conexão, constraint violation), o JSON local
seria atualizado, criando divergência entre as duas fontes de verdade.

**Correção:** `salvar_no_banco()` agora retorna `True`/`False`. `salvar_historico()` só é
chamado se `banco_ok is True`. Em caso de falha no banco, um `WARNING` é logado explicando
que o JSON não foi atualizado para evitar divergência.

---

### Arquivos modificados nesta versão

| Arquivo | Fixes |
|---------|-------|
| `analise_ia.py` | #1, #4, #7, #8 |
| `verifica_nps.py` | #2, #5, #6, #7 |
| `analise_woz_detratores.py` | #3, #9 |

---

## v2.3 — Julho 2026

- Persistência WOZ em `analise_nps_analistas` com `analise_tipo = 'woz_detratores_trimestral'`
- SQLs de criação (`create_tables_nps.sql`, `create_analysis_columns.sql`) corrigidos para schema `lw_octadesk`
- `create_tables_nps.sql` com cabeçalho TL;DR para leitura rápida
- README atualizado para v2.3

## v2.2 — Julho 2026

- Criado `analise_woz_detratores.py` — comparativo trimestral de detratores WOZ
- Saídas: HTML individual + `historico.json` acumulativo
- Termos de detecção: woz, robô, bot, automático, chatbot, atendimento automático, virtual, IA (via SQL ILIKE)

## v2.1 — Julho 2026

- Migração do schema `kinghost_octadesk` → `lw_octadesk`
- `DB_SCHEMA` controlado por variável de ambiente em `config.py`
- Todos os SQLs e queries atualizados

## v2.0 — Outubro 2025

- Implementação inicial com suporte a `.env`
- Processamento paralelo com `ThreadPoolExecutor`
- Integração Google Gemini
- Idempotência via `request_id` UNIQUE constraint
