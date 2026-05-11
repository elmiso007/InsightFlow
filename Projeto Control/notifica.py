from slack_sdk import WebClient
import pandas as pd
from datetime import date, datetime
import locale


# Configurando o idioma para português
locale.setlocale(locale.LC_TIME, "pt_BR.utf8")

# Criação do cliente Slack com seu token
client = WebClient('[REDACTED_SLACK_TOKEN]')

def notifica_analista(login, horario, pausa1, intervalo, pausa3, saida, id_slack,funcao, equipe,coordenador,skill=None):
    # Obtendo o nome do mês
    mes_atual = datetime.now().strftime("%B")

    mensagem = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Olá <@{login}>!"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"Sua escala de trabalho de *{mes_atual}* já está disponível!\n"
                        f"Você esta escalado para atender: *{funcao}*  |  *{equipe}*."
                        )
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
                        f"Sua jornada deverá iniciar as *`{horario}`*\n"
                        f"Sua primeira pausa será as *`{pausa1}`*\n"
                        f"Seu intervalo será as *`{intervalo}`*\n"
                        f"Sua segunda pausa será as *`{pausa3}`*\n"
                        f"E deverá encerrar seu expediente as *`{saida}`*"
                    )
                },
                "accessory": {
                    "type": "image",
                    "image_url": "https://www.locaweb.com.br/images/open-graph.jpg",
                    "alt_text": "logo locaweb"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text":(
                        f"Caso tenha alguma dúvida ou necessite de ajustes, basta chamar seu coordenador <@{coordenador}>.\n"
                        f"Tenha um ótimo dia!"
                    )
                }
            }
        ]
    }

    # Verificar se o destinatário começa com 'U'
    try:
        if id_slack.startswith('U'):
            response_dm = client.conversations_open(users=id_slack)
            channel_id = response_dm["channel"]["id"]
            response_message = client.chat_postMessage(channel=channel_id, blocks=mensagem["blocks"], text="Sua Escala Chegou!")
            print(f"Mensagem enviada para o direct do usuário {id_slack}.")
        else:
            print(f"ID Slack inválido: {id_slack}")
    except Exception as e:
        print(f"Erro ao enviar notificação para {id_slack}: {e}")
