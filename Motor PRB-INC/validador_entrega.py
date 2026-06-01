# =============================================================================
# Motor Prescritivo PRB — Validador de Entrega (prisma retrospectivo)
# =============================================================================
# Complementa os prismas preventivos (Rules Engine + Customer Monitor) com uma
# leitura retrospectiva: para cada PRB que o Change Team entregou nos últimos
# N dias, conta INCs novas no mesmo (produto, servidor) e emite veredicto.
#
# Veredictos:
#   - REINCIDENCIA      → ≥ LIMIAR_INCS_REINCIDENCIA INCs pós-resolução.
#                         Dispara Slack imediato pro Change Team.
#   - ENTREGA_VALIDADA  → 0 INCs pós-resolução E dias_pos_resolucao ≥
#                         MIN_DIAS_PARA_VALIDAR.
#                         Janela suficientemente longa sem regressão.
#   - INCONCLUSIVO      → caso intermediário (pouco tempo desde resolução,
#                         poucas INCs sob o limiar, etc.). Continua sob observação.
# =============================================================================
from __future__ import annotations

import logging
from typing import List

import config
import time_utils
from extractor import FonteIncidentes
from models import Incidente, PRBExistente, ValidacaoEntrega

log = logging.getLogger(__name__)


VEREDICTO_REINCIDENCIA = "REINCIDENCIA"
VEREDICTO_VALIDADA = "ENTREGA_VALIDADA"
VEREDICTO_INCONCLUSIVO = "INCONCLUSIVO"


def _classificar(qtd_incs: int, dias_pos: int) -> str:
    """Aplica a matriz simples de veredicto.

    A ordem importa: REINCIDENCIA tem precedência sobre tempo de janela —
    se aparecer reincidência ainda no 2º dia, é reincidência mesmo assim.
    """
    if qtd_incs >= config.LIMIAR_INCS_REINCIDENCIA:
        return VEREDICTO_REINCIDENCIA
    if qtd_incs == 0 and dias_pos >= config.MIN_DIAS_PARA_VALIDAR:
        return VEREDICTO_VALIDADA
    return VEREDICTO_INCONCLUSIVO


def _avaliar_prb(prb: PRBExistente, fonte_inc: FonteIncidentes) -> ValidacaoEntrega:
    """Calcula veredicto de um único PRB.

    PRBs sem data_resolucao (ex.: Aguardando Validação ainda sem encerramento
    formal) são tratados com data_resolucao = data_abertura como salvaguarda —
    veredicto fica INCONCLUSIVO até o status virar 'Encerrado Automaticamente'.
    """
    agora = time_utils.agora_utc()
    data_ref = prb.data_resolucao or prb.aberto_em or agora
    dias_pos = max(0, (agora - data_ref).days)

    # Sem produto ou servidor não dá pra fazer match — INCONCLUSIVO.
    if not prb.produto or not prb.servidor:
        log.debug(
            "PRB %s sem produto/servidor — pulando match de reincidência.", prb.prb_id
        )
        return ValidacaoEntrega(
            prb_id=prb.prb_id,
            descricao_curta=prb.descricao_curta,
            produto=prb.produto,
            servidor=prb.servidor,
            status_prb=prb.status,
            data_resolucao=data_ref,
            dias_pos_resolucao=dias_pos,
            qtd_incs_pos_resolucao=0,
            veredicto=VEREDICTO_INCONCLUSIVO,
            incs_reincidentes=[],
        )

    incs_pos: List[Incidente] = fonte_inc.listar_incidentes_por_produto_servidor(
        produto=prb.produto, servidor=prb.servidor, desde=data_ref
    )

    qtd = len(incs_pos)
    veredicto = _classificar(qtd, dias_pos)

    return ValidacaoEntrega(
        prb_id=prb.prb_id,
        descricao_curta=prb.descricao_curta,
        produto=prb.produto,
        servidor=prb.servidor,
        status_prb=prb.status,
        data_resolucao=data_ref,
        dias_pos_resolucao=dias_pos,
        qtd_incs_pos_resolucao=qtd,
        veredicto=veredicto,
        incs_reincidentes=incs_pos,
    )


def gerar_validacoes_entrega(
    fonte_incidentes: FonteIncidentes,
) -> List[ValidacaoEntrega]:
    """Roda o prisma retrospectivo: lista PRBs encerrados na janela e avalia cada um.

    Falha defensiva: se um PRB der erro durante a avaliação, registra e continua
    com os demais — não derruba o ciclo inteiro por causa de um caso ruim.
    """
    try:
        prbs = fonte_incidentes.listar_prbs_para_validacao(
            config.JANELA_VALIDACAO_ENTREGA_DIAS
        )
    except Exception as exc:
        log.error("Falha ao listar PRBs para validação: %s", exc)
        return []

    log.info("PRBs candidatos a validação de entrega: %d.", len(prbs))

    validacoes: List[ValidacaoEntrega] = []
    for prb in prbs:
        try:
            validacoes.append(_avaliar_prb(prb, fonte_incidentes))
        except Exception as exc:
            log.warning("Falha ao validar entrega de %s: %s", prb.prb_id, exc)

    # Ordena por urgência (reincidências primeiro, depois por dias_pos_resolucao desc)
    ordem_veredicto = {
        VEREDICTO_REINCIDENCIA: 0,
        VEREDICTO_INCONCLUSIVO: 1,
        VEREDICTO_VALIDADA: 2,
    }
    validacoes.sort(
        key=lambda v: (ordem_veredicto.get(v.veredicto, 9), -v.dias_pos_resolucao)
    )

    contagem = {v: 0 for v in (
        VEREDICTO_REINCIDENCIA, VEREDICTO_VALIDADA, VEREDICTO_INCONCLUSIVO
    )}
    for v in validacoes:
        contagem[v.veredicto] = contagem.get(v.veredicto, 0) + 1
    log.info(
        "Validações de entrega: %d (reincidência: %d, validada: %d, inconclusivo: %d).",
        len(validacoes),
        contagem[VEREDICTO_REINCIDENCIA],
        contagem[VEREDICTO_VALIDADA],
        contagem[VEREDICTO_INCONCLUSIVO],
    )
    return validacoes