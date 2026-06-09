# =============================================================================
# LocaPredict — motor prescritivo de PRB.
# =============================================================================
# Recebe um cluster de incidentes e seus scores e devolve uma PrescricaoPRB rica:
# ação curta para o banco, urgência, decisão de abrir PRB, grupo destino,
# bullets de evidência, descrição em linguagem natural e score composto para
# ordenação. Cinco regras em cascata (CRÍTICA → ALTA → MEDIA-investigar →
# MEDIA-fluxo → BAIXA), avaliadas na ordem — a primeira que casar para a busca.
# =============================================================================
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence


# Mapa de urgência (cascata de regras atual) para P-level oficial da Locaweb Varejo.
# P5 fica reservado: nenhuma das 5 regras atuais o produz; será atribuído em F3
# quando entrar a detecção de "Monitoração Automática" / incidentes isolados.
MAPA_URGENCIA_PRIORIDADE: Dict[str, str] = {
    "CRITICA": "P1",
    "ALTA":    "P2",
    "MEDIA":   "P3",
    "BAIXA":   "P4",
}

# OLA target em horas por P-level (diretrizes operacionais — ata Locaweb Varejo).
# Usado no alerta Slack e como referência para o time de Service Operation.
OLA_TARGETS_HORAS: Dict[str, int] = {
    "P1": 4,
    "P2": 4,
    "P3": 12,
    "P4": 24,
    "P5": 96,
}

# --- F3: limiares de calibração da matriz P1-P4 ---
# Ajuste centralizado aqui — toda a lógica de prescrever_acao_prb() lê esses
# valores. Calibração inicial (ata Locaweb Varejo) foi >=100 e revelou-se
# permissiva para a realidade operacional (5000+ INCs/mês em alguns produtos).
# Valores atuais refletem ajuste após análise empírica.
LIMIAR_P2_HISTORICO_COM_CONTORNO = 1000   # >= este número em N dias → P2 (ALTA)
LIMIAR_P3_HISTORICO_COM_CONTORNO_MIN = 100  # faixa P3 começa aqui
LIMIAR_P3_HISTORICO_COM_CONTORNO_MAX = LIMIAR_P2_HISTORICO_COM_CONTORNO  # exclusivo
LIMIAR_P2_SEM_CONTORNO_NO_CLUSTER = 5     # >= INCs sem contorno no cluster → P2
LIMIAR_P3_SEVERIDADE_PERCEPTIVEL = 0.5    # score_severidade >= → "falha perceptível"

# --- F3: heurísticas de detecção (substring case-insensitive em desc_clean + descricao_curta) ---
# Os termos refletem a matriz oficial da ata Locaweb Varejo. São heurísticos —
# podem produzir falsos positivos/negativos. Ajustar aqui (não em SQL/código).
_TERMOS_RECLAME_AQUI = ("reclame aqui", "reclameaqui", "reclame-aqui")
_TERMOS_SEM_CONTORNO = (
    "sem contorno",
    "sem solucao",
    "sem solução",
    "nenhum contorno",
    "no workaround",
)
_TERMOS_INDISPONIVEL = (
    "indisponivel",
    "indisponível",
    "fora do ar",
    "ambiente fora",
    "tudo fora",
    "todos fora",
)
_TERMOS_MONITORACAO_GRUPO = ("monit",)
_TERMOS_MONITORACAO_LOGIN = ("monit", "automat", "alert")


def _prioridade_e_ola(urgencia: str) -> tuple[str, int]:
    """Resolve P-level e OLA target em horas a partir da urgência da regra."""
    prioridade = MAPA_URGENCIA_PRIORIDADE.get(urgencia, "P4")
    return prioridade, OLA_TARGETS_HORAS.get(prioridade, OLA_TARGETS_HORAS["P4"])


def _texto_para_busca(inc: dict) -> str:
    """Concatena desc_clean + descricao_curta em lowercase para match por substring."""
    partes: List[str] = []
    for chave in ("desc_clean", "descricao_curta"):
        valor = inc.get(chave)
        if valor:
            partes.append(str(valor).lower())
    return " ".join(partes)


def _tem_reclame_aqui(cluster_data: Sequence[dict]) -> bool:
    """True se algum INC do cluster menciona Reclame Aqui (heurística por substring)."""
    return any(
        any(t in _texto_para_busca(inc) for t in _TERMOS_RECLAME_AQUI)
        for inc in cluster_data
    )


def _algum_sem_contorno(cluster_data: Sequence[dict]) -> bool:
    """True se algum INC do cluster menciona ausência de solução de contorno."""
    return any(
        any(t in _texto_para_busca(inc) for t in _TERMOS_SEM_CONTORNO)
        for inc in cluster_data
    )


def _contar_sem_contorno(cluster_data: Sequence[dict]) -> int:
    """Quantos INCs do cluster mencionam ausência de solução de contorno."""
    return sum(
        1
        for inc in cluster_data
        if any(t in _texto_para_busca(inc) for t in _TERMOS_SEM_CONTORNO)
    )


def _algum_indisponivel(cluster_data: Sequence[dict]) -> bool:
    """True se algum INC indica produto/ambiente indisponível."""
    return any(
        any(t in _texto_para_busca(inc) for t in _TERMOS_INDISPONIVEL)
        for inc in cluster_data
    )


def _todos_monitoracao_automatica(cluster_data: Sequence[dict]) -> bool:
    """
    True se TODOS os INCs do cluster vêm de monitoração automática.

    Critério: grupo_designado contém "monit" OU login_cliente contém
    "monit"/"automat"/"alert" (case-insensitive). Usado para classificar
    P4 quando a origem é técnica/automática e não usuário final.
    """
    if not cluster_data:
        return False
    for inc in cluster_data:
        grupo = str(inc.get("grupo_designado") or "").lower()
        login = str(inc.get("login_cliente") or "").lower()
        eh_monit = (
            any(t in grupo for t in _TERMOS_MONITORACAO_GRUPO)
            or any(t in login for t in _TERMOS_MONITORACAO_LOGIN)
        )
        if not eh_monit:
            return False
    return True


def _algum_ola_estourado(cluster_data: Sequence[dict], ola_target_horas: float) -> bool:
    """
    True se algum INC do cluster ultrapassou o OLA target (em horas).

    Compara contra `tempo_medio_resolucao` (já em horas conforme o pipeline em
    main.py:fetch_incidentes). Quando o target é <= 0, retorna False.
    """
    if ola_target_horas <= 0:
        return False
    return any(
        float(inc.get("tempo_medio_resolucao") or 0) > ola_target_horas
        for inc in cluster_data
    )


@dataclass
class PrescricaoPRB:
    """Resultado prescritivo de um cluster — viaja na tupla de insight até o Slack."""

    acao: str
    urgencia: str  # "CRITICA" | "ALTA" | "MEDIA" | "BAIXA"
    deve_abrir_prb: bool
    grupo_destino: str
    evidencias: List[str] = field(default_factory=list)
    descricao_rica: str = ""
    score_composto: float = 0.0
    prioridade: str = "P4"          # "P1".."P5" — atribuído diretamente pela matriz F3
    ola_target_horas: int = 24      # Tempo de resolução máximo em horas (diretriz oficial)
    upgrade_aplicado: Optional[str] = None  # Ex.: "P3->P2 por 7 INCs sem contorno"

    def __post_init__(self) -> None:
        """Garante ola_target_horas coerente com prioridade quando essa não veio explícita.

        Antes de F3, a prioridade era derivada da urgencia (CRITICA/ALTA/MEDIA/BAIXA).
        Após F3, a matriz P1-P4 atribui prioridade diretamente — quem constrói deve
        passar `prioridade=` e `ola_target_horas=` explicitamente. Para retrocompat
        com possíveis chamadas legadas (sem prioridade explícita), derivamos a partir
        da urgencia se ola_target_horas ainda está no default.
        """
        if self.prioridade in OLA_TARGETS_HORAS:
            self.ola_target_horas = OLA_TARGETS_HORAS[self.prioridade]
        else:
            self.prioridade, self.ola_target_horas = _prioridade_e_ola(self.urgencia)


def _faixa_severidade(score: float) -> str:
    if score >= 0.75:
        return "ALTA"
    if score >= 0.50:
        return "MEDIA"
    return "BAIXA"


def _faixa_ineficiencia(score: float) -> str:
    if score >= 0.60:
        return "CRITICA"
    if score >= 0.30:
        return "ATENCAO"
    return "SAUDAVEL"


def _grupo_destino_majoritario(cluster_data: Sequence[dict]) -> str:
    """Grupo do ServiceNow mais frequente no cluster (fallback: 'Nao informado')."""
    grupos = [
        str(inc.get("grupo_designado")).strip()
        for inc in cluster_data
        if inc.get("grupo_designado") and str(inc.get("grupo_designado")).strip()
    ]
    if not grupos:
        return "Nao informado"
    grupo_top, _ = Counter(grupos).most_common(1)[0]
    return grupo_top


def _contar_prioridade_critica_ou_alta(cluster_data: Sequence[dict]) -> int:
    """
    Conta INCs com prioridade crítica/alta. Heurística por substring: aceita
    rótulos como '1 - Critical', 'Crítico', 'High', 'Alta'. Robusta a variações
    de string vindas do ServiceNow.
    """
    total = 0
    for inc in cluster_data:
        prioridade = str(inc.get("prioridade") or "").strip().lower()
        if not prioridade:
            continue
        if (
            "crit" in prioridade
            or "high" in prioridade
            or "alt" in prioridade
            or prioridade.startswith("1")
            or prioridade.startswith("2")
        ):
            total += 1
    return total


def _categorias_distintas(cluster_data: Sequence[dict]) -> int:
    valores = {
        str(inc.get("categoria")).strip().lower()
        for inc in cluster_data
        if inc.get("categoria") and str(inc.get("categoria")).strip()
    }
    return len(valores)


def _clientes_distintos(cluster_data: Sequence[dict]) -> int:
    valores = {
        str(inc.get("login_cliente")).strip().lower()
        for inc in cluster_data
        if inc.get("login_cliente") and str(inc.get("login_cliente")).strip()
    }
    return len(valores)


def _coletar_evidencias(
    cluster_data: Sequence[dict],
    score_severidade: float,
    ineficiencia_score: float,
    servidores: Iterable[str],
) -> List[str]:
    """Monta bullets de evidência cruzando 7 fontes de sinal do cluster."""
    n = len(cluster_data)
    evidencias: List[str] = [
        f"Volume: {n} incidente(s) no cluster",
        f"Severidade {_faixa_severidade(score_severidade)} (score {score_severidade:.2f})",
        f"Ineficiência {_faixa_ineficiencia(ineficiencia_score)} (score {ineficiencia_score:.2f})",
    ]

    servidores_lista = [s for s in servidores if s]
    if servidores_lista:
        amostra = ", ".join(servidores_lista[:3])
        extra = "" if len(servidores_lista) <= 3 else f" (+{len(servidores_lista) - 3})"
        evidencias.append(f"Servidores afetados: {len(servidores_lista)} — {amostra}{extra}")

    prio_criticas = _contar_prioridade_critica_ou_alta(cluster_data)
    if prio_criticas:
        evidencias.append(f"Prioridade crítica/alta: {prio_criticas} INC(s)")

    cats = _categorias_distintas(cluster_data)
    if cats > 1:
        evidencias.append(f"Categorias distintas: {cats} (amplitude do problema)")

    clientes = _clientes_distintos(cluster_data)
    if clientes:
        evidencias.append(f"Clientes impactados: {clientes}")

    return evidencias


def _calcular_score_composto(
    score_severidade: float, ineficiencia_score: float, n_incidentes: int
) -> float:
    """Média 50/50 dos scores + bônus de volume (+0.05 se n>=5, +0.10 se n>=10)."""
    base = 0.5 * float(score_severidade) + 0.5 * float(ineficiencia_score)
    if n_incidentes >= 10:
        base += 0.10
    elif n_incidentes >= 5:
        base += 0.05
    return min(1.0, base)


def prescrever_acao_prb(
    cluster_data: Sequence[dict],
    score_severidade: float,
    ineficiencia_score: float,
    produto: str,
    servidores: Iterable[str] = (),
    total_historico_com_contorno: int = 0,
    total_historico_sem_contorno: int = 0,
    janela_historica_dias: int = 30,
) -> PrescricaoPRB:
    """
    Avalia a matriz P1–P4 (Locaweb Varejo) em cascata e devolve PrescricaoPRB rica.

    Regras (primeira que casa decide a prioridade; upgrade pode subir P3→P2):

      P1 (CRITICA): cluster com "Reclame Aqui" SEM solução de contorno
                    E OLA estourado (algum INC com tempo_medio_resolucao
                    > OLA target de P1).
      P2 (ALTA):    indisponibilidade detectada, OU >=5 INCs sem contorno
                    no cluster, OU >=100 INCs com contorno no histórico do
                    produto (últimos `janela_historica_dias`).
                    Marca `upgrade_aplicado` se sem essas condições a regra
                    base seria P3.
      P3 (MEDIA):   casos isolados com falha perceptível (severidade >= 0.5),
                    OU 1-4 INCs sem contorno no cluster, OU 20-99 INCs com
                    contorno no histórico.
      P4 (BAIXA):   monitoração automática (todos os INCs vindos de origem
                    técnica), OU casos isolados sem impacto principal
                    (severidade < 0.5 e sem demais sinais).

    Os scores `severidade`/`ineficiencia`/`composto` continuam sendo calculados
    e exibidos como contexto, mas não decidem mais a prioridade.
    """
    produto_label = produto or "Desconhecido"
    grupo_destino = _grupo_destino_majoritario(cluster_data)
    servidores_lista = [str(s).strip() for s in servidores if s and str(s).strip()]
    n = len(cluster_data)

    # Contexto (mantido como antes — viaja como diagnóstico no Slack)
    score_composto = _calcular_score_composto(score_severidade, ineficiencia_score, n)
    evidencias = _coletar_evidencias(
        cluster_data, score_severidade, ineficiencia_score, servidores_lista
    )

    # Sinais F3
    tem_reclame_aqui = _tem_reclame_aqui(cluster_data)
    tem_sem_contorno_qualquer = _algum_sem_contorno(cluster_data)
    n_sem_contorno_cluster = _contar_sem_contorno(cluster_data)
    tem_indisponivel = _algum_indisponivel(cluster_data)
    eh_monitoracao = _todos_monitoracao_automatica(cluster_data)
    ola_estourado_p1 = _algum_ola_estourado(cluster_data, OLA_TARGETS_HORAS["P1"])

    # Evidências adicionais quando os sinais F3 estão presentes
    if tem_reclame_aqui:
        evidencias.append("Reclame Aqui mencionado em pelo menos um INC")
    if n_sem_contorno_cluster > 0:
        evidencias.append(
            f"Sem solução de contorno: {n_sem_contorno_cluster} INC(s) no cluster"
        )
    if tem_indisponivel:
        evidencias.append("Indisponibilidade de produto/ambiente detectada")
    if eh_monitoracao:
        evidencias.append("Origem: monitoração automática")
    if total_historico_com_contorno or total_historico_sem_contorno:
        evidencias.append(
            f"Histórico {janela_historica_dias}d em {produto_label}: "
            f"{total_historico_com_contorno} com contorno · "
            f"{total_historico_sem_contorno} sem contorno"
        )

    # ----- P1: CRÍTICA -----
    if tem_reclame_aqui and tem_sem_contorno_qualquer and ola_estourado_p1:
        return PrescricaoPRB(
            acao=f"Abrir PRB P1 (Reclame Aqui sem contorno + OLA estourado) — {produto_label}",
            urgencia="CRITICA",
            deve_abrir_prb=True,
            grupo_destino=grupo_destino,
            evidencias=evidencias,
            descricao_rica=(
                f"Incidentes com referência a Reclame Aqui sem solução de contorno "
                f"e OLA já estourado em {produto_label}. Tratar como P1 — abrir PRB "
                f"imediatamente."
            ),
            score_composto=score_composto,
            prioridade="P1",
            ola_target_horas=OLA_TARGETS_HORAS["P1"],
        )

    # ----- P2: ALTA (com possível upgrade de P3) -----
    p2_indisponivel = tem_indisponivel
    p2_volume_sem_contorno = n_sem_contorno_cluster >= LIMIAR_P2_SEM_CONTORNO_NO_CLUSTER
    p2_volume_com_contorno = total_historico_com_contorno >= LIMIAR_P2_HISTORICO_COM_CONTORNO

    if p2_indisponivel or p2_volume_sem_contorno or p2_volume_com_contorno:
        # Sinaliza upgrade quando uma regra de volumetria elevou um caso que
        # de outra forma cairia em P3 (sem indisponibilidade, com sinais médios).
        seria_p3 = (
            (not p2_indisponivel)
            and (
                score_severidade >= LIMIAR_P3_SEVERIDADE_PERCEPTIVEL
                or 0 < n_sem_contorno_cluster < LIMIAR_P2_SEM_CONTORNO_NO_CLUSTER
                or (
                    LIMIAR_P3_HISTORICO_COM_CONTORNO_MIN
                    <= total_historico_com_contorno
                    < LIMIAR_P3_HISTORICO_COM_CONTORNO_MAX
                )
            )
        )
        motivo_upgrade: Optional[str] = None
        if seria_p3 and (p2_volume_sem_contorno or p2_volume_com_contorno):
            razoes: List[str] = []
            if p2_volume_sem_contorno:
                razoes.append(f"{n_sem_contorno_cluster} INCs sem contorno no cluster")
            if p2_volume_com_contorno:
                razoes.append(
                    f"{total_historico_com_contorno} INCs com contorno em {janela_historica_dias}d"
                )
            motivo_upgrade = "P3->P2 por " + " e ".join(razoes)

        razoes_p2: List[str] = []
        if p2_indisponivel:
            razoes_p2.append("indisponibilidade")
        if p2_volume_sem_contorno:
            razoes_p2.append(f">={n_sem_contorno_cluster} sem contorno")
        if p2_volume_com_contorno:
            razoes_p2.append(f">={total_historico_com_contorno} com contorno em {janela_historica_dias}d")

        return PrescricaoPRB(
            acao=f"Abrir PRB P2 ({', '.join(razoes_p2)}) — {produto_label}",
            urgencia="ALTA",
            deve_abrir_prb=True,
            grupo_destino=grupo_destino,
            evidencias=evidencias,
            descricao_rica=(
                f"PRB P2 disparado em {produto_label}: {', '.join(razoes_p2)}. "
                f"Aplicar tratamento conforme matriz oficial."
            ),
            score_composto=score_composto,
            prioridade="P2",
            ola_target_horas=OLA_TARGETS_HORAS["P2"],
            upgrade_aplicado=motivo_upgrade,
        )

    # ----- P3: MEDIA -----
    p3_severidade = score_severidade >= LIMIAR_P3_SEVERIDADE_PERCEPTIVEL
    p3_volume_sem_contorno = 0 < n_sem_contorno_cluster < LIMIAR_P2_SEM_CONTORNO_NO_CLUSTER
    p3_volume_com_contorno = (
        LIMIAR_P3_HISTORICO_COM_CONTORNO_MIN
        <= total_historico_com_contorno
        < LIMIAR_P3_HISTORICO_COM_CONTORNO_MAX
    )

    if p3_severidade or p3_volume_sem_contorno or p3_volume_com_contorno:
        razoes_p3: List[str] = []
        if p3_severidade:
            razoes_p3.append(f"severidade {score_severidade:.2f}")
        if p3_volume_sem_contorno:
            razoes_p3.append(f"{n_sem_contorno_cluster} sem contorno no cluster")
        if p3_volume_com_contorno:
            razoes_p3.append(
                f"{total_historico_com_contorno} com contorno em {janela_historica_dias}d"
            )
        return PrescricaoPRB(
            acao=f"Investigar candidato a PRB P3 em {produto_label}",
            urgencia="MEDIA",
            deve_abrir_prb=False,
            grupo_destino=grupo_destino,
            evidencias=evidencias,
            descricao_rica=(
                f"Falha perceptível em {produto_label} ({', '.join(razoes_p3)}). "
                f"Investigar antes de decidir abertura de PRB."
            ),
            score_composto=score_composto,
            prioridade="P3",
            ola_target_horas=OLA_TARGETS_HORAS["P3"],
        )

    # ----- P4: BAIXA -----
    # Monitoração automática classifica P4 com descrição dedicada;
    # demais casos isolados sem impacto também caem aqui.
    if eh_monitoracao:
        return PrescricaoPRB(
            acao=f"Monitorar {produto_label} (origem: monitoração automática)",
            urgencia="BAIXA",
            deve_abrir_prb=False,
            grupo_destino=grupo_destino,
            evidencias=evidencias,
            descricao_rica=(
                f"Cluster originado em monitoração automática em {produto_label} — "
                f"sem impacto direto em usuário final. Manter acompanhamento padrão."
            ),
            score_composto=score_composto,
            prioridade="P4",
            ola_target_horas=OLA_TARGETS_HORAS["P4"],
        )

    return PrescricaoPRB(
        acao=f"Monitorar {produto_label}",
        urgencia="BAIXA",
        deve_abrir_prb=False,
        grupo_destino=grupo_destino,
        evidencias=evidencias,
        descricao_rica=(
            f"Caso isolado em {produto_label} ({n} INC(s), severidade "
            f"{score_severidade:.2f}). Sem indicação de Reclame Aqui, sem "
            f"sinalização de contorno ausente e sem volumetria histórica relevante."
        ),
        score_composto=score_composto,
        prioridade="P4",
        ola_target_horas=OLA_TARGETS_HORAS["P4"],
    )
