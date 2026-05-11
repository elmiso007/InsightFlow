import feedparser
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime
import pytz

# Configurações do Slack
slack_token = "[REDACTED_SLACK_TOKEN]"
channel_id = "C08KQ4P015K"
client = WebClient(token=slack_token)

# Feed RSS da Data Hackers
rss_url = "https://towardsdatascience.com/feed"
feed = feedparser.parse(rss_url)

# Palavras-chave relevantes em Data Analytics
palavras_chave = [
    "dbt", "airflow", "snowflake", "bigquery", "data warehouse", "data lake",
    "ETL", "ELT", "analytics engineering", "engenharia de dados", "data analytics",
    "cientista de dados", "BI", "business intelligence", "data pipeline",
    "modelagem de dados", "stack de dados", "dashboards", "data lakehouse","llm"
]

# Função para verificar se o texto contém alguma palavra-chave
def contem_palavra_chave(titulo, resumo=""):
    texto = f"{titulo} {resumo}".lower()
    return any(palavra.lower() in texto for palavra in palavras_chave)

# Data de hoje (ajustada para o fuso horário de Brasília)
hoje = datetime.now(pytz.timezone("America/Sao_Paulo")).date()

# Processar o feed
for entry in feed.entries:
    # Extrai data de publicação e converte para data no formato date
    if hasattr(entry, 'published_parsed'):
        data_pub = datetime(*entry.published_parsed[:6]).date()
    else:
        continue  # ignora se não tiver data

    # Só processa se foi publicado hoje
    if data_pub == hoje:
        titulo = entry.title
        resumo = entry.summary if hasattr(entry, 'summary') else ""
        link = entry.link

        # Verifica se o artigo é relevante
        if contem_palavra_chave(titulo, resumo):
            mensagem = f"*{titulo}*\n{link}"
            try:
                client.chat_postMessage(channel=channel_id, text=mensagem)
                print(f"Enviado: {titulo}")
            except SlackApiError as e:
                print(f"Erro ao enviar para o Slack: {e}")
