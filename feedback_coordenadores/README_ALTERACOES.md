# Histórico de Alterações

---

## v2.2 — Julho 2026 — Correções de integridade e segurança

Esta versão resolve 7 problemas encontrados em análise arquitetural do `analise_ia.py`.
Nenhum bug visível ao usuário final, mas todos com potencial de causar dados errados,
falhas silenciosas ou consumo desnecessário de recursos em produção.

### Correções aplicadas

---

#### Fix #1 — Schema do banco hardcoded em múltiplas funções
**Arquivo:** `analise_ia.py`

`analise_ja_existe()`, `limpar_rawdata_antigos()` e os dois INSERTs dentro de `analise_ia_nps()`
usavam `kinghost_octadesk` diretamente, ignorando `config.DB_SCHEMA`. Qualquer mudança de
schema no `.env` era ignorada nessas funções — o código sempre apontava para o schema antigo.

**Correção:** todas as referências substituídas por `config.DB_SCHEMA` ou pela variável local
`schema = config.DB_SCHEMA` já definida no início de `analise_ia_nps()`.

---

#### Fix #2 — `analise_tipo` persistido com valor errado
**Arquivo:** `analise_ia.py`

O campo `analise_tipo` era gravado como `'NPS'` no INSERT para `rawdata_analise_nps_analistas`.
O SQL de promoção copiava o valor literal para `analise_nps_analistas`, então qualquer consulta
com `WHERE analise_tipo = 'monitoramento_nps_analistas'` retornava zero resultados.

**Correção:** valor alterado para `'monitoramento_nps_analistas'` em ambos os INSERTs
(completo e fallback sem seções).

---

#### Fix #3 — Injeção de format string via dado de cliente
**Arquivo:** `analise_ia.py`

O prompt era montado com `prompt_estrutura.format(dataset=dataset, ...)`. Se qualquer conversa
de cliente contivesse `{algo}` — comum em JSON, templates ou trechos de código — o Python
levantava `KeyError` ou `IndexError`. O analista falhava silenciosamente com "Erro na API"
e ninguém identificava a causa raiz.

**Correção:** dataset escapado antes do `format()`:
```python
dataset_safe = dataset.replace('{', '{{').replace('}', '}}')
```

---

#### Fix #4 — Contagem de tokens era estimativa por contagem de palavras
**Arquivo:** `analise_ia.py`

`token_prompt` e `token_completion` eram calculados como `len(texto.split()) * 1.3`,
uma heurística imprecisa que subestimava prompts estruturados.

**Correção:** valores lidos de `response.usage_metadata.prompt_token_count` e
`candidates_token_count`. A estimativa por palavras permanece apenas como fallback.

---

#### Fix #5 — `@lru_cache` em strings únicas (cache nunca atingido)
**Arquivo:** `analise_ia.py`

`converter_tabela_markdown_para_html_cached` e `converter_markdown_para_html` tinham
`@lru_cache(maxsize=128)` e `@lru_cache(maxsize=256)`. As entradas eram strings únicas
geradas pelo Gemini — o cache nunca tinha hits e apenas acumulava entradas na RAM.
O wrapper que convertia lista → tupla para satisfazer a exigência de hashable do cache
também foi removido.

**Correção:** decorators removidos; wrapper eliminado; função renomeada para
`converter_tabela_markdown_para_html` aceitando lista diretamente.

---

#### Fix #6 — `extrair_secoes_analise()` era código morto
**Arquivo:** `analise_ia.py`

A função de ~60 linhas estava definida mas nunca chamada desde que a saída estruturada
via Pydantic (`SecoesAnaliseNPS`) foi adicionada. O fluxo atual vai direto para
`json.loads(response.text)`, tornando a extração por regex completamente desnecessária.

**Correção:** função removida.

---

#### Fix #7 — SQL de promoção executado N vezes (uma por analista)
**Arquivo:** `analise_ia.py`

O script `insereDadosAnaliseNPS.sql` era chamado dentro de `analise_ia_nps()`, executada
uma vez por analista pelo `ThreadPoolExecutor`. Com 5 analistas críticos = 5 execuções
do SQL, causando tentativas de inserção duplicada para os primeiros analistas processados.

**Correção:**
- O bloco SQL foi removido de dentro de `analise_ia_nps()`.
- Adicionada a função `executar_sql_pos_analise(conn)` em `analise_ia.py`.
- O orquestrador (`verifica_nps.py`) deve chamar `executar_sql_pos_analise(conn)`
  **uma única vez** após todos os futures do `ThreadPoolExecutor` completarem.

---

### Arquivos modificados nesta versão

| Arquivo | Fixes |
|---------|-------|
| `analise_ia.py` | #1, #2, #3, #4, #5, #6, #7 |

---

## v2.1 — Julho 2026

- Atualização de configurações para suporte a múltiplos ambientes via `.env`
- Ajustes de estabilidade no processamento paralelo

## v2.0 — Outubro 2025

- Implementação inicial com suporte a `.env`
- Processamento paralelo com `ThreadPoolExecutor`
- Integração Google Gemini
- Idempotência via `request_id` UNIQUE constraint
- Saída estruturada em JSON via schema Pydantic `SecoesAnaliseNPS`
