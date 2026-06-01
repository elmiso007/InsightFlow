# =============================================================================
# Motor Prescritivo PRB — Entry point do ValidadorEntrega (prisma retrospectivo)
# =============================================================================
# Separado do main.py por design: rodada longa (~6h) que olha PRBs já
# entregues, enquanto o motor preventivo roda a cada 15 min em main.py.
#
# Uso:
#   python validar_entregas.py            → loop contínuo (default 6h)
#   python validar_entregas.py --once     → uma rodada e sai (debug/cron)
#   python validar_entregas.py --interval 24  → intervalo em horas
#
# Grava na mesma motor_execucao do banco (compartilha schema). O JSON do
# dashboard fica em arquivo separado pra não sobrescrever o do preventivo.
# =============================================================================
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime

import config
import time_utils
from extractor import criar_fonte_incidentes, criar_fonte_chamados
from models import ExecucaoMotor
from notifier import disparar_alertas_criticos, gravar_payload_dashboard
from notifier_db import persistir_execucao
from validador_entrega import gerar_validacoes_entrega


DEFAULT_INTERVALO_HORAS = 6  # validações não mudam em minutos — janela longa
JSON_OUTPUT_PATH = "./output/validacoes_entrega.json"


def configurar_logging() -> None:
    """Mesmo formato do main.py, mas arquivo separado para isolar logs."""
    os.makedirs(config.LOG_DIR, exist_ok=True)
    arquivo = os.path.join(
        config.LOG_DIR, f"validador-entrega-{datetime.now().strftime('%Y-%m-%d')}.log"
    )

    nivel = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)-22s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    raiz = logging.getLogger()
    raiz.setLevel(nivel)
    raiz.handlers.clear()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, Exception):
        pass

    handler_console = logging.StreamHandler(sys.stdout)
    handler_console.setFormatter(formatter)
    raiz.addHandler(handler_console)

    handler_arquivo = logging.FileHandler(arquivo, encoding="utf-8")
    handler_arquivo.setFormatter(formatter)
    raiz.addHandler(handler_arquivo)

    logging.getLogger("urllib3").setLevel(logging.WARNING)


def executar_validacao() -> ExecucaoMotor:
    """Roda um ciclo do prisma retrospectivo. Não toca cluster/prescrição/saúde
    — apenas valida entregas. Retorna a ExecucaoMotor para persistência.
    """
    log = logging.getLogger("validador")
    inicio = time.monotonic()

    fonte_inc = criar_fonte_incidentes()
    fonte_chamados = criar_fonte_chamados()
    execucao = ExecucaoMotor(timestamp=time_utils.agora_utc())

    try:
        execucao.validacoes_entrega = gerar_validacoes_entrega(fonte_inc, fonte_chamados)
    except Exception as exc:
        log.exception("Falha no ValidadorEntrega: %s", exc)
        execucao.erros.append(f"validador_entrega: {exc}")

    # Persistência: JSON sempre (rede de segurança), Postgres se habilitado.
    try:
        gravar_payload_dashboard(execucao, caminho=JSON_OUTPUT_PATH)
    except Exception as exc:
        log.exception("Falha ao gravar JSON: %s", exc)
        execucao.erros.append(f"json_dashboard: {exc}")

    execucao.duracao_ciclo_ms = int((time.monotonic() - inicio) * 1000)
    persistir_execucao(execucao)

    # Slack — apenas reincidências detectadas.
    disparar_alertas_criticos(execucao)

    return execucao


def rodar_loop(intervalo_horas: int) -> None:
    """Loop infinito com pausa configurável (em horas). Ctrl+C interrompe."""
    log = logging.getLogger("validador")
    log.info("ValidadorEntrega em loop — intervalo: %d horas.", intervalo_horas)
    while True:
        try:
            executar_validacao()
        except KeyboardInterrupt:
            log.info("Interrompido pelo usuário (Ctrl+C). Encerrando.")
            return
        except Exception as exc:
            log.exception("Erro inesperado no loop: %s", exc)
        time.sleep(intervalo_horas * 3600)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Motor Prescritivo PRB — Validador de Entrega (retrospectivo)."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa apenas uma rodada e encerra (útil para cron/debug).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVALO_HORAS,
        help=f"Intervalo entre ciclos em HORAS (default: {DEFAULT_INTERVALO_HORAS}).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configurar_logging()
    log = logging.getLogger("main")

    log.info("ValidadorEntrega iniciado (prisma retrospectivo).")
    log.info(
        "Modo mocks: %s | Janela: %d dias | Intervalo: %dh | Logs em %s",
        config.USAR_MOCKS,
        config.JANELA_VALIDACAO_ENTREGA_DIAS,
        args.interval,
        config.LOG_DIR,
    )

    if args.once:
        log.info("Modo single-run (--once) ativado.")
        execucao = executar_validacao()
        reincidencias = len(execucao.reincidencias_detectadas)
        log.info(
            "Validação única concluída: %d validações totais, %d reincidências.",
            len(execucao.validacoes_entrega), reincidencias,
        )
        return 0 if not execucao.erros else 1

    rodar_loop(intervalo_horas=args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())