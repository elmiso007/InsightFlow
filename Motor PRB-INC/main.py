# =============================================================================
# Motor Prescritivo PRB — Entry point
# =============================================================================
# Uso:
#   python main.py                  → loop contínuo a cada 15 min (produção)
#   python main.py --once           → executa uma única rodada e sai (debug)
#   python main.py --interval 5     → intervalo customizado em minutos
# =============================================================================
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime

import config
from extractor import criar_fonte_incidentes, criar_fonte_chamados
from scheduler import executar_ciclo, rodar_loop


def configurar_logging() -> None:
    """Logging para console + arquivo rotacionado por dia."""
    os.makedirs(config.LOG_DIR, exist_ok=True)
    # Nome de arquivo usa data LOCAL (BRT) propositalmente — operador olhando
    # a pasta de logs prefere ver datas no fuso local. Demais usos do motor
    # padronizam UTC via time_utils.agora_utc().
    arquivo = os.path.join(
        config.LOG_DIR, f"motor-prb-{datetime.now().strftime('%Y-%m-%d')}.log"
    )

    nivel = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)-22s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    raiz = logging.getLogger()
    raiz.setLevel(nivel)
    # Evita handlers duplicados quando o módulo é re-importado
    raiz.handlers.clear()

    # Console em UTF-8 (cp1252 padrão do Windows quebra com emojis/setas).
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

    # Silencia ruído de libs externas
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("schedule").setLevel(logging.WARNING)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Motor Prescritivo PRB — antecipa PRBs a partir de INCs."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa apenas uma rodada e encerra (útil para debug/CI).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=config.INTERVALO_JOB_MINUTOS,
        help=f"Intervalo entre ciclos em minutos (default: {config.INTERVALO_JOB_MINUTOS}).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configurar_logging()
    log = logging.getLogger("main")

    log.info("Motor Prescritivo PRB iniciado.")
    log.info("Modo mocks: %s | Intervalo: %d min | Logs em %s",
             config.USAR_MOCKS, args.interval, config.LOG_DIR)

    if args.once:
        log.info("Modo single-run (--once) ativado.")
        fonte_inc = criar_fonte_incidentes()
        fonte_chamados = criar_fonte_chamados()
        execucao = executar_ciclo(fonte_inc, fonte_chamados)
        log.info(
            "Execução única concluída: %d clusters, %d prescrições, %d saúde de clientes.",
            len(execucao.clusters), len(execucao.prescricoes), len(execucao.saude_clientes),
        )
        return 0 if not execucao.erros else 1

    rodar_loop(intervalo_min=args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())