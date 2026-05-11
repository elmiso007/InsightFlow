# 🔄 Guia de Migração - Report Diário Locaweb

## ⚠️ AÇÃO IMEDIATA NECESSÁRIA

Seu código **contém informações sensíveis expostas** que precisam ser protegidas IMEDIATAMENTE.

---

## 🚨 **Credenciais Comprometidas**

As seguintes informações estão expostas no código e precisam ser renovadas:

### 1. **Token do Slack**
```
Token exposto: [REDACTED_SLACK_TOKEN]
```

**AÇÃO NECESSÁRIA**:
1. Acesse https://api.slack.com/apps
2. Selecione seu app
3. Vá em "OAuth & Permissions"
4. Clique em "Revoke" no token atual
5. Gere um novo token
6. Adicione o novo token ao arquivo `.env`

### 2. **Credenciais do Banco de Dados**
```
Servidor: 10.30.138.28
Banco: report_requesttracker
Usuário: automatizacoes
Senha: [REDACTED_DB_PASSWORD] (EXPOSTA!)
```

**AÇÃO NECESSÁRIA**:
1. Entre em contato com o administrador do banco
2. Solicite a troca da senha do usuário `automatizacoes`
3. Atualize a senha no arquivo `.env`

### 3. **Credenciais do ServiceNow**
```
Usuário: integracao.atendimento.locaweb
Senha: [REDACTED_SERVICENOW_PWD] (EXPOSTA!)
```

**AÇÃO NECESSÁRIA**:
1. Entre em contato com o administrador do ServiceNow
2. Solicite a troca da senha
3. Atualize no arquivo `.env`

---

## 📋 **Passo a Passo da Migração**

### **Passo 1: Criar arquivo .env**

```bash
copy env.example .env
```

Abra o arquivo `.env` e preencha com as credenciais:

```ini
# ==============================================
# BANCO DE DADOS
# ==============================================
DB_SERVER=10.30.138.28
DB_DATABASE=report_requesttracker
DB_USER=automatizacoes
DB_PASSWORD=NOVA_SENHA_AQUI

# ==============================================
# SLACK
# ==============================================
SLACK_BOT_TOKEN=NOVO_TOKEN_AQUI
SLACK_CHANNEL_ID=C08AZTJB8JV

# ==============================================
# PERÍODO PADRÃO
# ==============================================
PADRAO_DATA_INICIO=2025-08-01
PADRAO_DATA_FIM=2025-10-31

# ==============================================
# LOGGING
# ==============================================
LOG_LEVEL=INFO
LOG_FILE=report_diario.log
```

### **Passo 2: Testar a aplicação**

```bash
python app.py
```

Verifique se:
- ✅ Conecta ao banco de dados
- ✅ Lê os dados corretamente
- ✅ Gera o relatório
- ✅ Envia para o Slack

### **Passo 3: Proteger arquivos sensíveis**

Verifique se o `.gitignore` está funcionando:

```bash
git status
```

**NÃO DEVE APARECER**:
- `.env`
- `config.ini`
- `*.log`
- `*.png`

### **Passo 4: Limpar histórico do Git (OPCIONAL mas RECOMENDADO)**

⚠️ **CUIDADO**: Isso reescreve o histórico do Git!

Se as credenciais já foram commitadas anteriormente:

```bash
# 1. Instalar BFG Repo-Cleaner
# Baixe de: https://rtyley.github.io/bfg-repo-cleaner/

# 2. Remover credenciais do histórico
java -jar bfg.jar --delete-files config.ini
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 3. Forçar push (CUIDADO!)
git push --force
```

**ALTERNATIVA MAIS SEGURA**: Criar um repositório novo do zero sem o histórico comprometido.

---

## 🔒 **Checklist de Segurança**

Antes de considerar a migração completa, confirme:

- [ ] Token do Slack foi revogado e renovado
- [ ] Senha do banco de dados foi alterada
- [ ] Senha do ServiceNow foi alterada
- [ ] Arquivo `.env` foi criado com as novas credenciais
- [ ] Arquivo `.env` está no `.gitignore`
- [ ] Arquivo `config.ini` foi removido ou adicionado ao `.gitignore`
- [ ] A aplicação foi testada e funciona corretamente
- [ ] Logs não contêm informações sensíveis
- [ ] Histórico do Git foi limpo (opcional)

---

## 🆕 **Diferenças da Nova Versão**

### O que mudou:

| Antes | Agora |
|-------|-------|
| `config.ini` | `.env` |
| Path hardcoded | Path relativo |
| Sem logging | Logging completo |
| Sem tratamento de erros | Try/except em todo código |
| Print() para debug | Logger estruturado |
| Valores fixos | Constantes configuráveis |
| Dias úteis fixos (103) | Cálculo dinâmico |
| SSL desabilitado | SSL configurado corretamente |

### O que permaneceu igual:

- ✅ Lógica de cálculo dos indicadores
- ✅ Estrutura das mensagens do Slack
- ✅ Formato dos gráficos
- ✅ Comparações (padrão, D-7, hoje)

---

## 📞 **Suporte**

### Em caso de problemas:

1. **Verificar logs**: `report_diario.log`
2. **Ativar DEBUG**: No `.env`, configure `LOG_LEVEL=DEBUG`
3. **Testar conexões**:
   - Banco de dados
   - Slack API
4. **Contatar equipe de infraestrutura** se necessário

---

## ⏰ **Cronograma Sugerido**

### Fase 1: URGENTE (Hoje)
- ⚠️ Revogar token do Slack comprometido
- ⚠️ Alterar senhas do banco e ServiceNow
- ⚠️ Criar arquivo `.env`

### Fase 2: Imediato (Esta semana)
- ✅ Testar a nova versão em ambiente de desenvolvimento
- ✅ Validar todas as funcionalidades
- ✅ Configurar `.gitignore`

### Fase 3: Produção (Próxima semana)
- ✅ Migrar para produção
- ✅ Atualizar agendador de tarefas
- ✅ Monitorar logs por 1 semana
- ✅ Limpar histórico do Git (opcional)

---

## 🎯 **Benefícios da Migração**

### Segurança:
- 🔒 Credenciais não expostas no código
- 🔒 Token pode ser renovado facilmente
- 🔒 `.gitignore` protege arquivos sensíveis

### Manutenibilidade:
- 🔧 Configuração centralizada
- 🔧 Fácil de debugar com logs
- 🔧 Código mais limpo e organizado

### Confiabilidade:
- 🛡️ Tratamento de erros robusto
- 🛡️ Validação de configurações
- 🛡️ Logs detalhados de execução

---

## ✅ **Após a Migração**

Quando tudo estiver funcionando:

1. **Remover arquivos antigos**:
   ```bash
   del bkp.py
   del config.ini
   ```

2. **Documentar mudanças** para a equipe

3. **Monitorar execução** por alguns dias

4. **Celebrar!** 🎉 Seu sistema está mais seguro!

---

**Última atualização**: 04 de Janeiro de 2025  
**Autor**: Emerson Ramos

