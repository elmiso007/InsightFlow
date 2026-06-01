# =============================================================================
# Motor Prescritivo PRB — Customer Monitor (Saúde do Cliente)
# =============================================================================
# Requisito original (Emerson/Bruno): para cada cliente com >= 3 INCs nos
# últimos 6 meses, montar a linha do tempo consolidada (ServiceNow + Dynamics) e
# emitir alerta de recorrência alta. Poupa o trabalho manual do analista de
# garimpar histórico chamado-a-chamado no plantão.
# =============================================================================
from __future__ import annotations

import logging
from collections import Counter
from datetime import timedelta
from typing import Dict, List, Sequence

import config
import time_utils
from extractor import FonteIncidentes, FonteChamados
from models import SaudeCliente, Incidente, InteracaoChamado

log = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Identificação de clientes com volume relevante
# -----------------------------------------------------------------------------
def _clientes_com_volume(
    incidentes: Sequence[Incidente], limiar: int = config.LIMIAR_INCS_SAUDE_CLIENTE
) -> List[str]:
    """Retorna logins com >= `limiar` INCs nas INCs já carregadas (janela atual)."""
    contagem: Counter[str] = Counter(
        i.login_cliente for i in incidentes if i.login_cliente
    )
    return [login for login, n in contagem.items() if n >= limiar]


# -----------------------------------------------------------------------------
# Detecção de atividade recente (anti alert fatigue)
# -----------------------------------------------------------------------------
def _tem_inc_recente(incs: Sequence[Incidente], dias: int) -> bool:
    """True se o cliente tem ao menos uma INC nos últimos N dias.

    Critério complementar ao volume — evita disparar alerta crônico para cliente
    com histórico antigo mas sem atividade recente (cliente que 'acalmou' não
    deve inundar Slack pelos próximos meses só porque ainda está na janela de
    6 meses).
    """
    if not incs:
        return False
    corte = time_utils.agora_utc() - timedelta(days=dias)
    return any(i.abertura >= corte for i in incs)


# -----------------------------------------------------------------------------
# Cálculo de severidade média do cliente
# -----------------------------------------------------------------------------
def _calcular_severidade_media(incs: Sequence[Incidente]) -> float:
    """Média ponderada das prioridades das INCs do cliente.

    Range 0.0 (cliente com tudo P5 — rotineiro) a 1.0 (tudo P1 — crítico).
    Mapeamento em config.PESO_PRIORIDADE_SEVERIDADE.

    Default 0.0 se lista vazia. Prioridade desconhecida (fora do mapa) é
    contada como peso 0.0 — equivalente a P5 — comportamento conservador.
    """
    if not incs:
        return 0.0
    pesos = [
        config.PESO_PRIORIDADE_SEVERIDADE.get(i.prioridade_atual, 0.0)
        for i in incs
    ]
    return round(sum(pesos) / len(pesos), 3)


# -----------------------------------------------------------------------------
# Construção da linha do tempo consolidada
# -----------------------------------------------------------------------------
def _montar_linha_do_tempo(
    incs: Sequence[Incidente], chamados: Sequence[InteracaoChamado]
) -> List[Dict]:
    """Mescla INCs e chamados em ordem cronológica decrescente."""
    eventos: List[Dict] = []
    for inc in incs:
        eventos.append({
            "fonte": "ServiceNow",
            "tipo": "INC",
            "id": inc.inc_id,
            "data": inc.abertura.isoformat(),
            "produto": inc.produto,
            "ci": inc.servidor,
            "prioridade": inc.prioridade_atual,
            "resumo": inc.descricao_curta,
            "tem_contorno": inc.tem_solucao_contorno,
        })
    for chamado in chamados:
        eventos.append({
            "fonte": chamado.organizacao or "Chamado",  # "Locaweb" ou "Kinghost"
            "tipo": "Chamado",
            "id": chamado.chamado_id,
            "data": chamado.data.isoformat(),
            "produto": chamado.produto,
            "origem": chamado.origem,
            "resumo": chamado.assunto,
        })
    eventos.sort(key=lambda e: e["data"], reverse=True)
    return eventos


# -----------------------------------------------------------------------------
# API pública
# -----------------------------------------------------------------------------
def gerar_saude_clientes(
    incidentes_janela: Sequence[Incidente],
    fonte_incidentes: FonteIncidentes,
    fonte_chamados: FonteChamados,
) -> List[SaudeCliente]:
    """Para cada cliente com volume >= limiar na janela atual de 24h, busca o
    histórico completo de 6 meses (ServiceNow + chamados Locaweb/Kinghost) e
    devolve uma avaliação de Saúde do Cliente.

    Otimização MVP: só consulta histórico longo para clientes que JÁ apareceram
    na janela de 24h. Em produção, considerar listar TOP-N clientes do mês via
    visão agregada no ServiceNow para detectar quem está reincidindo silenciosamente.
    """
    candidatos = _clientes_com_volume(
        incidentes_janela, limiar=config.LIMIAR_INCS_SAUDE_CLIENTE
    )
    log.info(
        "Clientes candidatos a avaliacao de saude (>=%d INCs na janela): %d -> %s",
        config.LIMIAR_INCS_SAUDE_CLIENTE, len(candidatos), candidatos,
    )

    saude_clientes: List[SaudeCliente] = []
    for login in candidatos:
        try:
            incs_historicas = fonte_incidentes.listar_incidentes_cliente(
                login, meses=config.JANELA_SAUDE_CLIENTE_MESES
            )
        except NotImplementedError:
            # Em produção: garantir cliente HTTP plugado. No mock, isso não
            # acontece. Aqui caímos para apenas as INCs já carregadas.
            log.warning(
                "Histórico longo ServiceNow indisponível para %s — usando janela atual.",
                login,
            )
            incs_historicas = [i for i in incidentes_janela if i.login_cliente == login]

        try:
            chamados = fonte_chamados.listar_chamados_cliente(
                login, meses=config.JANELA_SAUDE_CLIENTE_MESES
            )
        except NotImplementedError:
            log.warning("Histórico de chamados indisponível para %s.", login)
            chamados = []

        qtd_incs = len(incs_historicas)
        qtd_chamados = len(chamados)
        # Veredicto exige volume (recorrência) E atividade recente (anti alert
        # fatigue). Cliente com histórico antigo mas inativo agora não inunda Slack.
        recorrencia_alta = (
            qtd_incs >= config.LIMIAR_INCS_SAUDE_CLIENTE
            and _tem_inc_recente(incs_historicas, config.JANELA_RECENCIA_ALERTA_DIAS)
        )
        severidade = _calcular_severidade_media(incs_historicas)

        saude_clientes.append(SaudeCliente(
            cliente_login=login,
            qtd_incs_periodo=qtd_incs,
            qtd_chamados_periodo=qtd_chamados,
            severidade_media=severidade,
            incs=list(incs_historicas),
            chamados=list(chamados),
            alerta_recorrencia_alta=recorrencia_alta,
            linha_do_tempo=_montar_linha_do_tempo(incs_historicas, chamados),
        ))

    # Ordena por volume total decrescente (cliente "mais barulhento" primeiro)
    saude_clientes.sort(
        key=lambda c: c.qtd_incs_periodo + c.qtd_chamados_periodo,
        reverse=True,
    )
    log.info("Saude de clientes avaliada: %d.", len(saude_clientes))
    return saude_clientes