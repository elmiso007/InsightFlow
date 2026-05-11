# 🔄 Sistema de Canais Slack - Oficial vs Teste

## Descrição

O aplicativo agora suporta dois canais Slack configuráveis:
- **Canal Oficial**: Para notificações em produção
- **Canal Teste**: Para validar alterações antes de publicar em produção

## Configuração

### 1. Via Variável de Ambiente `.env`

Adicione ao seu arquivo `.env`:

```dotenv
SLACK_CHANNEL_MODE=official
```

Valores aceitos:
- `official` (padrão) - Envia para o canal oficial
- `test` - Envia para o canal de teste

### 2. Direto no Código

No arquivo `app.py`, você pode alterar o modo manualmente:

```python
CHANNEL_MODE = "test"  # ou "official"
```

## Canais Configurados

| Tipo | ID do Canal | Uso |
|------|------------|-----|
| Oficial | Configurado em `SLACK_CHANNEL` | Notificações em produção |
| Teste | C07NSPQ69TL | Testes antes de publicação |

## Exemplos de Uso

### Executar em Modo Teste

```bash
# Opção 1: Via .env
echo "SLACK_CHANNEL_MODE=test" >> .env
python app.py

# Opção 2: Via variável de ambiente
set SLACK_CHANNEL_MODE=test
python app.py
```

### Executar em Modo Oficial (Padrão)

```bash
# Opção 1: Via .env
echo "SLACK_CHANNEL_MODE=official" >> .env
python app.py

# Opção 2: Padrão (sem configuração)
python app.py
```

## Como Saber Qual Canal Está Sendo Usado?

1. **Na Saída do Console**: `✅ Mensagem enviada ao Slack (Canal: TESTE) com sucesso.`
2. **Na Mensagem do Slack**: A mensagem incluirá `📢 *Canal:* 'TESTE'` ou `📢 *Canal:* 'OFICIAL'`
3. **No Log**: Verifique o arquivo de log em `logs/auditoria_YYYY-MM-DD.log`

## Fluxo de Trabalho Recomendado

1. **Desenvolvimento/Testes**: Use `SLACK_CHANNEL_MODE=test`
   ```bash
   set SLACK_CHANNEL_MODE=test
   python app.py
   ```

2. **Validação**: Verifique a mensagem no canal de teste

3. **Produção**: Altere para `SLACK_CHANNEL_MODE=official`
   ```bash
   set SLACK_CHANNEL_MODE=official
   python app.py
   ```

## Estrutura de Log

Cada execução gera logs em `logs/auditoria_YYYY-MM-DD.log`:

```json
{
  "timestamp": "2026-02-04T14:30:45",
  "level": "INFO",
  "message": "Enviando mensagem para canal TESTE",
  "context": {
    "channel": "C07NSPQ69TL"
  }
}
```

## Dúvidas Frequentes

**P: Qual é o padrão se não configurar nada?**  
R: O padrão é `official`, que usa o canal oficial configurado em `SLACK_CHANNEL`.

**P: Posso mudar o canal de teste?**  
R: Sim! Altere a variável `CHANNEL_ID_TEST` no `app.py`:
```python
CHANNEL_ID_TEST = "NOVO_ID_DO_CANAL"
```

**P: Como verificar qual canal está ativo antes de executar?**  
R: Verifique seu arquivo `.env` ou execute o comando:
```bash
echo %SLACK_CHANNEL_MODE%
```
