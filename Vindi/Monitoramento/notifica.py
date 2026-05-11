from slack_sdk import WebClient
import pandas as pd
from datetime import date, datetime
import locale


from config import Config

# Configurando o idioma para português
locale.setlocale(locale.LC_TIME, "pt_BR.utf8")

# Criação do cliente Slack com seu token
client = WebClient(token=Config.SLACK_BOT_TOKEN)

destinatarios = Config.SLACK_CHANNELS
#destinatarios = ['C07NSPQ69TL'] #Canal teste


def notifica(content,percentual,media):
    """
    Envia uma notificação de alerta para o Slack.

    Informa sobre o aumento no volume de contatos e inclui a análise gerada pela IA.

    Args:
        content (str): Conteúdo da análise da IA.
        percentual (float): Percentual de aumento identificado.
        media (float): Média histórica de atendimentos para o período.
    """
    # Obtendo o nome do mês
    mes_atual = datetime.now().strftime("%B")

    mensagem = {
	"blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":-alert:  Monitoramento de contatos Recebidos :vindi:",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"O sistema de monitoramento de contatos identificou um aumento de *`{percentual}`%* na quantidade de contatos recebidos em relação a média de *`{media}`* contatos da última semana. "
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{content}"
                }
            }
        ]
    }

    for destinatario in destinatarios:
        # Verificar se o destinatário começa com 'U'
        if destinatario.startswith('U'):
            # Abrir um direct com o usuário do Slack
            response_dm = client.conversations_open(users=destinatario)
            channel_id = response_dm["channel"]["id"]

            # Enviar a mensagem no direct
            response_message = client.chat_postMessage(channel=channel_id, blocks=mensagem["blocks"], text= f"Monitoramento de Contatos Vindi")
            print(f"Mensagem enviada para o direct do usuário {destinatario}.")
        # Verificar se o destinatário começa com 'C'
        elif destinatario.startswith('C'):
            # Usar o código que já possui para destinatários que começam com 'C'
            response_message = client.chat_postMessage(channel=destinatario, blocks=mensagem["blocks"], text=f"Monitoramento de Contatos Vindi")
            print(f"Mensagem enviada para {destinatario}.")




def notifica_boas_noticias(hora_inicio, hora_fim,percentual):
    """
    Envia uma notificação informativa ("boas notícias") para o Slack.

    Pode ser usada para informar redução de demanda ou estabilidade (lógica a ser implementada/utilizada).

    Args:
        hora_inicio (str): Hora inicial do período.
        hora_fim (str): Hora final do período.
        percentual (float): Percentual comparativo.
    """

    mensagem = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Monitoramento de Contatos de Chat"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"O monitoramento de contatos das *`{hora_inicio}`* as *`{hora_fim}`* identificou que estamos com uma demanda de *{percentual} *% em relação ao mesmo período dos ultimos 7 dias!\n"
                                )
                        },
                        "accessory": {
                            "type": "image",
                            "image_url": "https://www.locaweb.com.br/images/open-graph.jpg",
                            "alt_text": "logo locaweb"
                        }
                    }
                ]
            }
    
    for destinatario in destinatarios:
        # Verificar se o destinatário começa com 'U'
        if destinatario.startswith('U'):
            # Abrir um direct com o usuário do Slack
            response_dm = client.conversations_open(users=destinatario)
            channel_id = response_dm["channel"]["id"]

            # Enviar a mensagem no direct
            response_message = client.chat_postMessage(channel=channel_id, blocks=mensagem["blocks"], text= f"Monitoramento de Contatos")
            print(f"Mensagem enviada para o direct do usuário {destinatario}.")
        # Verificar se o destinatário começa com 'C'
        elif destinatario.startswith('C'):
            # Usar o código que já possui para destinatários que começam com 'C'
            response_message = client.chat_postMessage(channel=destinatario, blocks=mensagem["blocks"], text=f"Monitoramento de Contatos")
            print(f"Mensagem enviada para {destinatario}.")
