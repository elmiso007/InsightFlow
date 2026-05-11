"""Notificações Slack para rotinas Tray (stubs se slack_sdk não configurado)."""


def notify_slack(mensagem: str, rotina: str) -> None:
    print(f"[Slack erro — {rotina}] {mensagem}")


def notify_slack_success(
    mensagem: str, linhas_inseridas: int, linhas_atualizadas: int, rotina: str
) -> None:
    print(
        f"[Slack sucesso — {rotina}] {mensagem} "
        f"(inseridas={linhas_inseridas}, atualizadas={linhas_atualizadas})"
    )
