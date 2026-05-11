# Monitoramento de Atendimentos Vindi

Este projeto é uma ferramenta de automação desenvolvida para monitorar o volume de atendimentos do suporte em tempo real, identificar picos de demanda e utilizar Inteligência Artificial para analisar os motivos de contato, notificando a equipe via Slack.

## 📋 Funcionalidades

- **Monitoramento em Tempo Real**: Verifica a cada execução o volume de atendimentos nos últimos 30 minutos.
- **Detecção de Anomalias**: Compara o volume atual com a média dos últimos 7 dias para o mesmo horário.
- **Análise com IA**: Em caso de pico de atendimentos (> 15% acima da média e volume relevante), utiliza a API da OpenAI para categorizar os principais motivos de contato.
- **Anonimização de Dados**: Processa os textos dos chats para remover dados sensíveis (CPF, E-mail, Cartão, etc.) antes do envio para a IA.
- **Notificações automáticas**: Envia alertas no Slack com o resumo da análise e estatísticas.
- **Registro em Banco de Dados**: Armazena históricos de monitoramento e análises para relatórios futuros.

## 🛠️ Estrutura do Projeto

*   **`verificador.py`**: Script principal que orquestra o monitoramento. Verifica horários, conecta ao banco, calcula métricas e decide se deve acionar a análise de IA.
*   **`get_atendimentos.py`**: Responsável por extrair os dados das conversas do banco de dados e aplicar regras de anonimização (LGPD) para proteger dados sensíveis.
*   **`openai.py`**: Módulo de integração com a API da OpenAI (GPT-4o-mini). Envia os dados anonimizados e recebe a análise estruturada.
*   **`notifica.py`**: Gerencia a integração com o Slack para envio de alertas para canais ou usuários específicos.
*   **`conecta_banco.py`**: Centraliza as conexões com o banco de dados PostgreSQL (usando SQLAlchemy, PyODBC e Psycopg2).
*   **`insereDados.sql`**: Script SQL auxiliar para inserção/atualização de dados de monitoramento.
*   **`insereDadosAnaliseIA.sql`**: Script SQL auxiliar para registro das análises da IA.

## 🚀 Como Executar

### Pré-requisitos

*   Python 3.x
*   Acesso ao banco de dados PostgreSQL da aplicação.
*   Dependências listadas (instale via pip):
    ```bash
    pip install pandas sqlalchemy psycopg2 pyodbc slack_sdk requests spacy holidays beautifulsoup4 numpy
    ```
    *Nota: Para o spacy, pode ser necessário baixar o modelo de linguagem: `python -m spacy download pt_core_news_sm`*

### Configuração

**Atenção**: As credenciais de banco de dados e tokens de API estão configuradas diretamente nos arquivos `.py`. Certifique-se de que os seguintes acessos estão corretos antes de executar:

1.  **Banco de Dados**: Verifique as configurações em `conecta_banco.py`.
2.  **Slack Token**: Verifique o token do bot em `notifica.py`.
3.  **OpenAI API Key**: Verifique a chave da API em `openai.py`.

### Execução Manual

Para rodar a verificação manualmente:

```bash
python verificador.py
```

O script irá:
1. Validar se hoje é dia útil.
2. Consultar o banco de dados para obter estatísticas.
3. Se detectar um pico anormal, realizará a análise de IA e enviará a notificação no Slack.
4. Salvará os resultados no banco de dados.

## 🛡️ Segurança e Privacidade

O módulo `get_atendimentos.py` possui uma camada robusta de "sanitização" de dados que remove:
*   CPFs e CNPJs
*   Endereços de E-mail
*   Números de Telefone
*   IPs e Domínios
*   Nomes de empresas concorrentes e termos sensíveis (login, senha)
*   Palavras impróprias

Isso garante que dados pessoais dos clientes não sejam enviados para a API externa da OpenAI.
