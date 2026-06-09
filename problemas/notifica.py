"""Notificacoes Slack para a rotina LWSA Problems."""

import configparser
import os
from pathlib import Path

from slack_sdk import WebClient

CANAL = "C07F5RCHK16"

_client = None


def _carregar_token_slack():
    """Le o bot_token de [slack] do config.ini (../config.ini). SLACK_BOT_TOKEN no ambiente tem prioridade."""
    token_env = (os.environ.get("SLACK_BOT_TOKEN") or "").strip()
    if token_env:
        return token_env
    config_path = Path(__file__).parent / ".." / "config.ini"
    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")
    if "slack" not in parser or "bot_token" not in parser["slack"]:
        raise KeyError("bot_token ausente em [slack] do config.ini")
    return parser["slack"]["bot_token"].strip()


def _get_client():
    global _client
    if _client is None:
        _client = WebClient(_carregar_token_slack())
    return _client


def notify_slack(mensagem: str, rotina: str) -> None:
    """Envia alerta de erro para o canal Slack (barra vermelha)."""
    attachment = {
        "color": "danger",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":x: Falha na execucao da rotina!",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Rotina {rotina} falhou*\n{mensagem}",
                },
            },
        ],
    }
    _get_client().chat_postMessage(
        channel=CANAL,
        attachments=[attachment],
        text=f"Erro em {rotina}",
    )


def notify_slack_success(
    mensagem: str, linhas_inseridas: int, linhas_atualizadas: int, rotina: str
) -> None:
    """Envia notificacao de sucesso para o canal Slack (barra verde, fields lado a lado)."""
    attachment = {
        "color": "good",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":white_check_mark: Rotina executada com sucesso!",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Rotina {rotina} executada com sucesso*\n{mensagem}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Registros Inseridos*\n{linhas_inseridas}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Registros Atualizados*\n{linhas_atualizadas}",
                    },
                ],
            },
        ],
    }
    _get_client().chat_postMessage(
        channel=CANAL,
        attachments=[attachment],
        text=f"{rotina} executada com sucesso",
    )