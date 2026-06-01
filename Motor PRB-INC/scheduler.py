# =============================================================================
# Motor Prescritivo PRB — Scheduler (job a cada 15 minutos)
# =============================================================================
# Orquestra o pipeline completo em loop temporizado. Tratamento de erro é
# defensivo: qualquer falha em uma execução é logada mas NÃO derruba o loop —
# o motor precisa sobreviver a flakiness das APIs ServiceNow/Dynamics.
#
# Em produção, considere substituir o `schedule` por:
#   - cron do sistema (mais simples de monitorar)
#   - APScheduler (se precisar de persistência / replay)
#   - Kubernetes CronJob (se for containerizar)
# O `schedule` é mantido aqui por ser zero-dependência além do PyPI.
# =============================================================================
from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime
from typing import Optional

import config
import time_utils
from models import ExecucaoMotor
import analyzer
import customer_monitor
import notifier
import notifier_db
import rules_engine
from extractor import (
    FonteIncidentes,
    FonteChamados,
    criar_fonte_incidentes,
    criar_fonte_chamados,
)

log = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Pipeline de uma execução
# -----------------------------------------------------------------------------
def executar_ciclo(
    fonte_inc: FonteIncidentes,
    fonte_chamados: FonteChamados,
) -> ExecucaoMotor:
    """Executa uma rodada completa do motor.

    Pipeline:
      1. Extrai INCs (24h) + chamados (24h) + PRBs abertos.
      2. Clusteriza + calcula scores + cruza com volume de chamados.
      3. Aplica regras P1..P5 + sugere repriorizações.
      4. Avalia Saúde dos clientes com volume.
      5. Persiste estado para o dashboard e dispara Slack para críticos.
    """
    inicio = time_utils.agora_utc()
    execucao = ExecucaoMotor(timestamp=inicio)

    # 1. Extração
    try:
        incidentes = fonte_inc.listar_incidentes_recentes(config.JANELA_INC_HORAS)
        execucao.total_incs_lidas = len(incidentes)
        log.info("INCs lidas (24h): %d.", len(incidentes))
    except Exception as exc:
        log.exception("Falha ao extrair INCs: %s", exc)
        execucao.erros.append(f"extrair_incs: {exc}")
        execucao.duracao_ciclo_ms = int(
            (time_utils.agora_utc() - inicio).total_seconds() * 1000
        )
        return execucao

    try:
        chamados = fonte_chamados.listar_chamados_periodo(config.JANELA_DYNAMICS_HORAS)
        execucao.total_chamados = len(chamados)
        log.info("Chamados (24h): %d.", len(chamados))
    except Exception as exc:
        log.warning("Falha ao extrair chamados — seguindo sem cruzamento: %s", exc)
        execucao.erros.append(f"extrair_chamados: {exc}")
        chamados = []

    try:
        prbs_abertos = fonte_inc.listar_prbs_abertos()
        log.info("PRBs abertos lidos: %d.", len(prbs_abertos))
    except Exception as exc:
        log.warning("Falha ao listar PRBs abertos — sem sugestão de repriorização: %s", exc)
        execucao.erros.append(f"listar_prbs: {exc}")
        prbs_abertos = []

    # 2. Análise
    try:
        execucao.clusters = analyzer.analisar(incidentes, chamados)
    except Exception as exc:
        log.exception("Falha na análise: %s", exc)
        execucao.erros.append(f"analisar: {exc}")

    # 3. Regras
    try:
        execucao.prescricoes = rules_engine.prescrever_lote(
            execucao.clusters, prbs_abertos
        )
        log.info(
            "Prescrições geradas: %d (críticas: %d).",
            len(execucao.prescricoes),
            len(execucao.alertas_criticos),
        )
    except Exception as exc:
        log.exception("Falha no rules_engine: %s", exc)
        execucao.erros.append(f"rules_engine: {exc}")

    # 4. Saúde do Cliente
    try:
        execucao.saude_clientes = customer_monitor.gerar_saude_clientes(
            incidentes, fonte_inc, fonte_chamados
        )
    except Exception as exc:
        log.exception("Falha no customer_monitor: %s", exc)
        execucao.erros.append(f"saude_cliente: {exc}")

    # 5. Saídas (não bloqueiam execução em caso de falha)
    # 5a. Dashboard JSON (fallback / consumo simples)
    try:
        notifier.gravar_payload_dashboard(execucao)
    except Exception as exc:
        log.exception("Falha ao gravar dashboard JSON: %s", exc)
        execucao.erros.append(f"dashboard_json: {exc}")

    # Métrica de duração até aqui (tempo de processamento) — populada ANTES da
    # persistência Postgres para ser gravada na coluna duracao_ciclo_ms.
    # Não inclui Slack (que pode demorar muito com rate limit defensivo).
    execucao.duracao_ciclo_ms = int(
        (time_utils.agora_utc() - inicio).total_seconds() * 1000
    )

    # 5b. Persistência Postgres (lwsa.motor_*) — fonte para análises temporais
    try:
        notifier_db.persistir_execucao(execucao)
    except Exception as exc:
        log.exception("Falha ao persistir no banco: %s", exc)
        execucao.erros.append(f"dashboard_db: {exc}")

    # 5c. Slack (alertas críticos)
    try:
        notifier.disparar_alertas_criticos(execucao)
    except Exception as exc:
        log.exception("Falha ao disparar Slack: %s", exc)
        execucao.erros.append(f"slack: {exc}")

    # Log final mostra ambos (persistido vs. total incluindo Slack).
    duracao_total_ms = int((time_utils.agora_utc() - inicio).total_seconds() * 1000)
    log.info(
        "Ciclo executado em %d ms (processamento: %d ms, Slack: %d ms).",
        duracao_total_ms,
        execucao.duracao_ciclo_ms,
        duracao_total_ms - execucao.duracao_ciclo_ms,
    )

    return execucao


# -----------------------------------------------------------------------------
# Loop com `schedule` (zero-dep, simples)
# -----------------------------------------------------------------------------
_STOP_REQUESTED = False


def _stop_handler(signum, frame) -> None:
    """SIGINT/SIGTERM → encerra o loop ao final do ciclo corrente."""
    global _STOP_REQUESTED
    log.info("Sinal %s recebido — encerrando após o ciclo atual.", signum)
    _STOP_REQUESTED = True


def rodar_loop(intervalo_min: int = config.INTERVALO_JOB_MINUTOS) -> None:
    """Loop principal. Roda imediatamente uma vez e depois a cada N minutos."""
    fonte_inc = criar_fonte_incidentes()
    fonte_chamados = criar_fonte_chamados()

    # SIGINT/SIGTERM: encerramento limpo
    signal.signal(signal.SIGINT, _stop_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop_handler)

    try:
        import schedule
    except ImportError:
        log.warning(
            "Lib `schedule` não instalada — caindo para loop manual com sleep. "
            "Recomendo `pip install schedule`."
        )
        return _rodar_loop_manual(fonte_inc, fonte_chamados, intervalo_min)

    def _job() -> None:
        log.info("=" * 70)
        log.info("Iniciando ciclo do Motor Prescritivo PRB às %s",
                 time_utils.agora_utc().isoformat(timespec="seconds"))
        try:
            execucao = executar_ciclo(fonte_inc, fonte_chamados)
            log.info(
                "Ciclo concluído: %d clusters, %d prescrições, %d saúde de clientes, %d erros.",
                len(execucao.clusters), len(execucao.prescricoes),
                len(execucao.saude_clientes), len(execucao.erros),
            )
        except Exception as exc:
            log.exception("Erro não tratado no ciclo: %s", exc)

    # Roda uma vez imediatamente para validar o setup
    _job()

    schedule.every(intervalo_min).minutes.do(_job)
    log.info("Agendado: job a cada %d minutos. Ctrl+C para encerrar.", intervalo_min)

    while not _STOP_REQUESTED:
        schedule.run_pending()
        time.sleep(1)

    log.info("Loop encerrado.")


def _rodar_loop_manual(
    fonte_inc: FonteIncidentes,
    fonte_chamados: FonteChamados,
    intervalo_min: int,
) -> None:
    """Fallback sem `schedule`: sleep simples entre ciclos."""
    intervalo_seg = intervalo_min * 60
    while not _STOP_REQUESTED:
        try:
            executar_ciclo(fonte_inc, fonte_chamados)
        except Exception as exc:
            log.exception("Erro não tratado no ciclo: %s", exc)
        for _ in range(intervalo_seg):
            if _STOP_REQUESTED:
                break
            time.sleep(1)