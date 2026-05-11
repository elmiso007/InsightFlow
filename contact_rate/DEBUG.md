# 🐛 GUIA DE DEBUG E TROUBLESHOOTING

## 📊 Visualizar Logs

### Opção 1: Acompanhar em tempo real (Windows PowerShell)
```powershell
Get-Content -Path logs/contact_logfile.log -Wait
```

### Opção 2: Ver últimas linhas
```powershell
Get-Content logs/contact_logfile.log -Tail 50
```

### Opção 3: Filtrar por erro
```powershell
Get-Content logs/contact_logfile.log | Select-String "ERROR"
```

---

## 🔍 Erros Comuns & Soluções

### ❌ "ModuleNotFoundError: No module named 'pandas'"

**Causa:** Dependências não instaladas

**Solução:**
```bash
pip install -r requirements.txt
```

**Verificação:**
```bash
python -c "import pandas; print(pandas.__version__)"
```

---

### ❌ "ConnectionRefusedError: [WinError 10061] Nenhuma conexão pôde ser estabelecida"

**Causa:** Banco de dados não acessível

**Checklist:**
1. Servidor BD está online?
   ```bash
   ping cpro23221.publiccloud.com.br
   ```

2. Porta 5432 aberta?
   ```bash
   telnet cpro23221.publiccloud.com.br 5432
   ```

3. Credenciais corretas em `config.ini`?
   ```ini
   host=cpro23221.publiccloud.com.br
   port=5432
   dbname=report_requesttracker
   user=a_report
   password=Eequ8ohc
   ```

4. Testar conexão com psql:
   ```bash
   psql -h cpro23221.publiccloud.com.br -U a_report -d report_requesttracker
   ```

---

### ❌ "FileNotFoundError: [Errno 2] No such file or directory"

**Causa:** Arquivo CSV não encontrado

**Verificação:**
```bash
# Windows
dir "Contact Rate_ Suporte N1.csv"

# Linux/Mac
ls -la "Contact Rate_ Suporte N1.csv"
```

**Nome EXATO:**
- ✅ Correto: `Contact Rate_ Suporte N1.csv`
- ❌ Errado: `ContactRate_SuporteN1.csv`
- ❌ Errado: `Contact Rate Suporte N1.csv`

---

### ❌ "ValueError: time data '2025/99' does not match format '%Y/%m'"

**Causa:** Formato de data inválido no CSV

**Solução:**
```bash
python validate_csv.py
```

**Formato esperado:**
- ✅ Correto: `2025/01`, `2025/02`
- ❌ Errado: `01/2025`, `2025-01`, `2025/1`

---

### ❌ "ValueError: could not convert string to float"

**Causa:** Formato de número/percentual inválido

**Validar CSV:**
```bash
python validate_csv.py
```

**Formatos esperados:**
- Números: `1.234` (ponto como separador de milhares)
- Percentuais: `12,50%` (vírgula como decimal)

---

### ❌ "psycopg2.IntegrityError: duplicate key value violates unique constraint"

**Causa:** Dados duplicados no INSERT

**Diagnóstico:**
```sql
SELECT AnoMes, COUNT(*) 
FROM public.contact_rate_kinghost 
GROUP BY AnoMes 
HAVING COUNT(*) > 1;
```

**Solução:**
```sql
-- Se permitido, truncar tabela
TRUNCATE TABLE public.contact_rate_kinghost;

-- Ou atualizar em vez de inserir
-- UPDATE.sql já tem essa lógica
```

---

### ❌ Tabela staging não criada

**Erro:** "relation 'public.stg_contact_rate_kinghost' does not exist"

**Solução:**
```sql
-- Criar tabela staging
CREATE TABLE public.stg_contact_rate_kinghost (
    data VARCHAR(7),
    contratos INTEGER,
    contatos INTEGER,
    contactrate NUMERIC(5,4)
);
```

---

## 🧪 TESTES MANUAIS

### Teste 1: Validar ambiente
```bash
python setup.py
```

### Teste 2: Validar CSV
```bash
python validate_csv.py
```

**Saída esperada:**
```
✅ Arquivo encontrado
✅ Arquivo lido com sucesso
✅ Colunas válidas
✅ Total de linhas: 24
✅ Datas válidas
✅ Coluna 'Clientes' válida
✅ Coluna 'Contatos' válida
✅ Coluna 'Contact Rate (%)' válida
✅ CSV VÁLIDO
```

### Teste 3: Executar pipeline
```bash
python contact_rate.py
```

**Saída esperada:**
```
2026-02-04 10:15:30,123 - INFO - Conexão com o banco de dados estabelecida com sucesso.
2026-02-04 10:15:30,451 - INFO - Arquivo CSV processado com sucesso. 24 linhas lidas.
2026-02-04 10:15:30,523 - INFO - Transformações aplicadas com sucesso.
2026-02-04 10:15:31,124 - INFO - Tabela staging truncada com sucesso!
2026-02-04 10:15:31,256 - INFO - 24 linhas inseridas na tabela staging com sucesso.
2026-02-04 10:15:31,412 - INFO - 5 linhas afetadas na inserção final.
2026-02-04 10:15:31,523 - INFO - 3 linhas afetadas na atualização final.
2026-02-04 10:15:31,655 - INFO - Pipeline executado com sucesso!
```

---

## 🔍 DEBUG AVANÇADO

### Ativar modo verbose em Python

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Debugar transformações de dados

```python
import pandas as pd
from contact_rate import read_csv_file, transform_dataframe

# Ler CSV
df = read_csv_file(Path('Contact Rate_ Suporte N1.csv'))
print("CSV bruto:")
print(df.head())
print(df.dtypes)

# Transformar
df_trans = transform_dataframe(df)
print("\nTransformado:")
print(df_trans.head())
print(df_trans.dtypes)
```

### Testar conexão BD manualmente

```python
import psycopg2

try:
    conn = psycopg2.connect(
        host='cpro23221.publiccloud.com.br',
        port='5432',
        dbname='report_requesttracker',
        user='a_report',
        password='Eequ8ohc'
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM public.contact_rate_kinghost;")
    print(f"Total de registros: {cur.fetchone()[0]}")
    cur.close()
    conn.close()
    print("✅ Conexão OK")
except Exception as e:
    print(f"❌ Erro: {e}")
```

---

## 📊 CONSULTAS SQL ÚTEIS

### Verificar dados inseridos

```sql
SELECT * FROM public.contact_rate_kinghost 
ORDER BY AnoMes DESC LIMIT 10;
```

### Verificar tabela staging

```sql
SELECT * FROM public.stg_contact_rate_kinghost;
```

### Contar registros por setor

```sql
SELECT setor, COUNT(*) as total 
FROM public.contact_rate_kinghost 
GROUP BY setor;
```

### Ver histórico de modificações

```sql
SELECT AnoMes, data_insercao, data_modificacao 
FROM public.contact_rate_kinghost 
WHERE data_modificacao > NOW() - INTERVAL '1 day';
```

### Comparar dados

```sql
SELECT 
    A.AnoMes,
    A.Clientes as clientes_atual,
    B.contratos as clientes_antigo,
    A.Contatos as contatos_atual,
    B.contatos as contatos_antigo
FROM public.contact_rate_kinghost A
LEFT JOIN public.stg_contact_rate_kinghost B ON A.AnoMes = B.data;
```

---

## 🎓 LOGGING EXPLICADO

### Níveis de Log

| Nível | Quando Usar | Exemplo |
|-------|------------|---------|
| DEBUG | Informações detalhadas para debug | `logger.debug(f"Valor: {x}")` |
| INFO | Informações gerais | `logger.info("Pipeline iniciado")` |
| WARNING | Avisos de situações anormais | `logger.warning("Valor nulo detectado")` |
| ERROR | Erros que precisam atenção | `logger.error(f"Erro: {e}")` |
| CRITICAL | Erros que causam parada | `logger.critical("BD offline!")` |

### Lendo Logs Estruturados

```
2026-02-04 10:15:30,123 - INFO - Mensagem
^                          ^     ^
Data/Hora              Nível  Mensagem
```

---

## 💡 DICAS PRÓ

### 1. Use environment variables para produção

```bash
# Antes de executar
set DB_PASSWORD=sua_senha_real
python contact_rate.py
```

### 2. Redirecionar logs para arquivo externo

```powershell
python contact_rate.py | Tee-Object -FilePath output.log
```

### 3. Executar com timeout

```bash
timeout 300 python contact_rate.py
```

### 4. Gerar relatório de erro

```python
import traceback
try:
    # seu código
except Exception as e:
    with open('error_report.txt', 'w') as f:
        f.write(traceback.format_exc())
```

### 5. Backup de dados antes de executar

```bash
# Windows
copy logs/contact_logfile.log logs/contact_logfile.backup.log

# Linux
cp logs/contact_logfile.log logs/contact_logfile.backup.log
```

---

## 📞 QUANDO TUDO FALHAR

1. **Coletar informações:**
   ```bash
   python -c "import sys; print(sys.version)"
   pip show pandas psycopg2-binary
   ```

2. **Validar arquivo CSV:**
   ```bash
   python validate_csv.py
   ```

3. **Verificar logs:**
   ```bash
   Get-Content logs/contact_logfile.log | Tail -100
   ```

4. **Testar componentes isoladamente:**
   - Testar conexão BD
   - Testar leitura CSV
   - Testar transformações

5. **Criar issue detalhado com:**
   - Mensagem de erro exata
   - Saída de `python validate_csv.py`
   - Últimas 50 linhas do log
   - Versão Python e pacotes

---

**Última atualização:** 4 de Fevereiro de 2026
