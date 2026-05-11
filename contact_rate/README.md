# 📊 Contact Rate - Suporte N1

Sistema automatizado de processamento e atualização de métricas de taxa de contato para o suporte de nível 1.

## 📌 Visão Geral

O script processa dados de contato em formato CSV e atualiza um banco de dados PostgreSQL com as métricas calculadas. Inclui tratamento robusto de erros, logging detalhado e foi otimizado para performance e manutenibilidade.

### Fluxo de Dados
```
CSV File → Parse & Validate → Transform → Staging Table → Insert/Update → Main Table
                                                    ↓
                                              Log File
```

## 🚀 Instalação Rápida

```bash
# 1. Clonar ou navegar para o diretório
cd contact_rate

# 2. Criar ambiente virtual (recomendado)
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar credenciais
cp config_example.ini config.ini
# Editar config.ini com suas credenciais reais (NUNCA commit sensíveis dados!)
```

## 📋 Requisitos

- Python 3.9+
- PostgreSQL 12+
- pandas
- psycopg2-binary

## ⚙️ Configuração

### Via Arquivo (config.ini)

```ini
[database]
host=seu_host
port=5432
dbname=seu_db
user=seu_usuario
password=sua_senha

[paths]
csv_file=Contact Rate_ Suporte N1.csv
log_file=logs/contact_logfile.log
```

### Variáveis de Ambiente (Recomendado para Produção)

```bash
export DB_HOST=seu_host
export DB_NAME=seu_db
export DB_USER=seu_usuario
export DB_PASSWORD=sua_senha
```

## 🏃 Execução

```bash
python contact_rate.py
```

### Output Esperado
```
2026-02-04 10:15:30,123 - INFO - Conexão com o banco de dados estabelecida com sucesso.
2026-02-04 10:15:30,124 - INFO - Arquivo CSV processado com sucesso. 24 linhas lidas.
2026-02-04 10:15:30,125 - INFO - Transformações aplicadas com sucesso.
...
2026-02-04 10:15:31,456 - INFO - Pipeline executado com sucesso!
```

## 📊 Estrutura de Arquivos

```
contact_rate/
├── contact_rate.py              # Script principal (otimizado)
├── config_example.ini           # Exemplo de configuração
├── requirements.txt             # Dependências Python
├── INSERT.sql                   # Script de inserção
├── UPDATE.sql                   # Script de atualização
├── Contact Rate_ Suporte N1.csv # Dados de entrada
├── logs/                        # Pasta de logs
│   └── contact_logfile.log     # Log de execução
├── OTIMIZACOES.md              # Documentação de melhorias
└── README.md                    # Este arquivo
```

## 🔍 Estrutura do CSV de Entrada

O arquivo CSV deve ter a seguinte estrutura:

| AnoMes | Clientes | Contatos | Contact Rate (%) |
|--------|----------|----------|-----------------|
| 2025/01| 1.234    | 5.678    | 12,50%          |
| 2025/02| 1.250    | 5.800    | 13,20%          |

**Nota:** O script trata automaticamente:
- Separadores de milhares (pontos)
- Decimais com vírgula
- Percentuais com símbolo %

## 📊 Transformações Aplicadas

1. **Data:** Formato `YYYY/MM` → Mantém `YYYY/MM`
2. **Clientes:** Numero com pontos (1.234) → Inteiro (1234)
3. **Contatos:** Numero com pontos (5.678) → Inteiro (5678)
4. **Contact Rate:** "12,50%" → 0.1250 (decimal)

## 📝 Logs

Os logs são salvos em `logs/contact_logfile.log` e contêm:

- ✅ Mensagens de sucesso
- ⚠️ Avisos importantes
- ❌ Erros detalhados com stack trace
- 📊 Quantidade de linhas processadas/afetadas

### Exemplo de Log
```
2026-02-04 10:15:30,123 - INFO - Conexão com o banco de dados estabelecida com sucesso.
2026-02-04 10:15:30,451 - INFO - Arquivo CSV processado com sucesso. 24 linhas lidas.
2026-02-04 10:15:30,523 - INFO - Transformações aplicadas com sucesso.
2026-02-04 10:15:31,124 - INFO - Tabela staging truncada com sucesso!
2026-02-04 10:15:31,256 - INFO - 24 linhas inseridas na tabela staging com sucesso.
2026-02-04 10:15:31,412 - INFO - 5 linhas afetadas na inserção final.
2026-02-04 10:15:31,523 - INFO - 3 linhas afetadas na atualização final.
```

## 🛡️ Tratamento de Erros

O script trata os seguintes cenários:

| Erro | Ação |
|------|------|
| Arquivo CSV não encontrado | Log de erro + Exit |
| Erro de conexão BD | Log de erro + Exit |
| Erro no parsing do CSV | Log de erro + Exit |
| Erro em INSERT/UPDATE | Rollback + Log + Exit |

## 🔒 Segurança

### ⚠️ IMPORTANTE
- **NUNCA** commitar arquivos com credenciais (`config.ini`, `.env`)
- Usar `.gitignore` para arquivo de configuração
- Para produção, usar serviços de secrets (AWS Secrets Manager, etc)

### .gitignore (recomendado)
```
config.ini
.env
*.pyc
__pycache__/
.venv/
venv/
logs/*.log
```

## 📈 Otimizações Implementadas

Veja [OTIMIZACOES.md](OTIMIZACOES.md) para detalhes técnicos completos das melhorias.

**Resumo:**
- ✅ Funções reutilizáveis com type hints
- ✅ Type hints e docstrings completas
- ✅ Melhor tratamento de exceções
- ✅ Logging estruturado
- ✅ Uso de `pathlib.Path` para portabilidade
- ✅ Padrão `if __name__ == '__main__'` para testabilidade

## 🐛 Troubleshooting

### "Erro ao conectar ao banco de dados"
```
Verificar:
1. Credenciais em config.ini
2. Conectividade de rede para o servidor
3. Porta PostgreSQL (padrão: 5432)
4. Usuário tem permissões no banco
```

### "Arquivo CSV não encontrado"
```
Verificar:
1. Arquivo existe em contact_rate/
2. Nome exato: "Contact Rate_ Suporte N1.csv"
3. Permissões de leitura
```

### "Transformação falhou"
```
Verificar:
1. Formato do CSV está correto
2. Valores de percentual incluem "%" (ex: 12,50%)
3. Decimais usam vírgula, não ponto
```

## 📞 Suporte

Para dúvidas ou problemas:
1. Verificar `logs/contact_logfile.log`
2. Validar formato do CSV
3. Testar conexão com banco de dados manualmente

## 📄 Licença

Copyright © 2026 - Todos os direitos reservados.

## 🚀 Próximos Passos

- [ ] Implementar schema validation
- [ ] Adicionar testes unitários
- [ ] Configurar CI/CD pipeline
- [ ] Adicionar suporte a múltiplos setores
- [ ] Criar dashboard de monitoramento
