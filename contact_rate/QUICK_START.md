# 🎯 GUIA RÁPIDO - Contact Rate Otimizado

## ⚡ 5 Passos para Começar

### 1️⃣ **Instalar Dependências**
```bash
pip install -r requirements.txt
```

### 2️⃣ **Configurar Credenciais**
```bash
# Copiar exemplo
copy config_example.ini config.ini

# Editar com suas credenciais reais
# IMPORTANTE: Nunca fazer commit de config.ini!
```

### 3️⃣ **Validar CSV (Recomendado)**
```bash
python validate_csv.py
```

Exemplo de sucesso:
```
============================================================
Validando CSV: Contact Rate_ Suporte N1.csv
============================================================

✅ Arquivo encontrado
✅ Arquivo lido com sucesso
✅ Colunas válidas
✅ Total de linhas: 24
✅ Datas válidas
✅ Coluna 'Clientes' válida
✅ Coluna 'Contatos' válida
✅ Coluna 'Contact Rate (%)' válida

============================================================
✅ CSV VÁLIDO - Pronto para processamento
============================================================
```

### 4️⃣ **Executar Pipeline**
```bash
python contact_rate.py
```

### 5️⃣ **Verificar Logs**
```bash
tail -f logs/contact_logfile.log
```

---

## 🐛 Troubleshooting Rápido

### ❌ "ModuleNotFoundError: No module named 'pandas'"
```bash
pip install -r requirements.txt
```

### ❌ "Erro ao conectar ao banco de dados"
**Verificar:**
- ✓ config.ini com credenciais corretas
- ✓ Host do banco acessível (ping)
- ✓ Porta 5432 aberta
- ✓ Usuário tem permissões

**Testar conexão:**
```bash
psql -h [HOST] -U [USER] -d [DBNAME]
```

### ❌ "Arquivo CSV não encontrado"
**Verificar:**
- ✓ Arquivo existe na pasta: `Contact Rate_ Suporte N1.csv`
- ✓ Nome exato (maiúsculas/minúsculas)
- ✓ Permissões de leitura

### ❌ "Transformação falhou"
**Verificar:**
- ✓ Formato do CSV está correto
- ✓ Percentuais incluem "%" (ex: 12,50%)
- ✓ Executar `python validate_csv.py` para detalhes

---

## 📊 Arquivos Importantes

| Arquivo | Propósito |
|---------|-----------|
| `contact_rate.py` | Script principal |
| `config.ini` | Credenciais (não commit!) |
| `requirements.txt` | Dependências |
| `INSERT.sql` | Inserção de novos registros |
| `UPDATE.sql` | Atualização de registros |
| `validate_csv.py` | Validador de CSV |
| `logs/` | Pasta de logs |

---

## 🔄 Fluxo de Execução

```
contact_rate.py
    ↓
1. setup_logging()           → Configura logging
    ↓
2. create_database_connection() → Conecta ao BD
    ↓
3. read_csv_file()           → Lê CSV
    ↓
4. transform_dataframe()     → Transforma dados
    ↓
5. load_to_staging()         → Carrega em staging
    ↓
6. execute_sql_script()      → Executa INSERT
    ↓
7. execute_sql_script()      → Executa UPDATE
    ↓
8. Logs gerados             ← logs/contact_logfile.log
```

---

## 📈 Monitoramento

### Ver logs em tempo real
```bash
# Windows PowerShell
Get-Content -Path logs/contact_logfile.log -Wait

# Linux/Mac
tail -f logs/contact_logfile.log
```

### Verificar últimas linhas
```bash
# Windows
Get-Content logs/contact_logfile.log -Tail 20

# Linux/Mac
tail -20 logs/contact_logfile.log
```

---

## 💡 Dicas Profissionais

### ✅ Use `.gitignore` para segurança
```
config.ini
.env
*.log
__pycache__/
.venv/
venv/
```

### ✅ Execute de forma agendada (Windows)
```batch
# Criar arquivo agendador.bat
@echo off
cd C:\Users\emerson.ramos\Desktop\projetos\contact_rate
C:\Users\emerson.ramos\Desktop\projetos\.venv\Scripts\python.exe contact_rate.py
```

### ✅ Execute de forma agendada (Linux/Mac)
```bash
# Adicionar ao crontab
0 8 * * * cd ~/projetos/contact_rate && ./venv/bin/python contact_rate.py
```

### ✅ Usar variáveis de ambiente (Seguro)
```bash
export DB_HOST=seu_host
export DB_NAME=seu_db
export DB_USER=seu_usuario
export DB_PASSWORD=sua_senha

python contact_rate.py
```

---

## 🚀 Próximas Melhorias

- [ ] Adicionar retry logic
- [ ] Notificações por email
- [ ] Dashboard web
- [ ] Testes automatizados
- [ ] Docker support

---

## 📞 Documentação Completa

Consulte:
- **README.md** - Documentação detalhada
- **OTIMIZACOES.md** - Detalhes técnicos
- **RESUMO_OTIMIZACOES.md** - Resumo visual

---

**✅ Tudo pronto! Execute: `python contact_rate.py`**
