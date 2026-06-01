# =============================================================================
# Motor Prescritivo PRB — Modelos de dados (dataclasses)
# =============================================================================
# Estruturas tipadas compartilhadas entre extractor, analyzer, rules_engine,
# customer_monitor e notifier. Manter aqui evita acoplamento por dict solto.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# -----------------------------------------------------------------------------
# Domínio: ServiceNow (lwsa.service_now_incidentes / lwsa.service_now_problemas)
# -----------------------------------------------------------------------------
@dataclass
class Incidente:
    """Representação canônica de uma INC do ServiceNow.

    Mapeamento direto da tabela `lwsa.service_now_incidentes`.
    Datas e prioridade são parseadas no extractor (vêm como text no banco).
    """
    inc_id: str                          # numero
    descricao_curta: str                 # descricao_curta
    descricao: str                       # descricao
    servidor: str                        # servidor (CI)
    produto: str                         # produto
    login_cliente: str                   # login_cliente (NÃO confundir com aberto_por)
    prioridade_atual: str                # prioridade (parseada para "P1".."P5")
    abertura: datetime                   # data_abertura
    atualizacao: datetime                # data_resolvido ou data_encerrado ou abertura
    qtd_atualizacoes: int                # derivado de atualizacoes (text)
    tem_solucao_contorno: bool           # heurística de descricao/fechamento
    tempo_solucao_contorno_min: int = 0  # MVP: não derivado, futuro: extrair via NLP
    # Campos enriquecedores (novos com a DDL real):
    organizacao: str = ""                # organizacao
    categoria: str = ""                  # categoria
    subcategoria: str = ""               # subcategoria
    grupo_designado: str = ""            # grupo_designado
    status: str = ""                     # status
    fechamento: str = ""                 # texto do fechamento (quando houver)

    @property
    def texto_busca(self) -> str:
        """Concatenação lower-case usada por heurísticas de termo."""
        return f"{self.descricao_curta} {self.descricao}".lower()


@dataclass
class PRBExistente:
    """PRB já aberta — alvo de potencial repriorização.

    Mapeamento direto da tabela `lwsa.service_now_problemas`, filtrada
    por status ativo (config.STATUS_PRB_ATIVOS).
    """
    prb_id: str                          # numero
    descricao_curta: str                 # descricao_curta
    descricao: str                       # descricao
    produto: str                         # produto
    servidor: str                        # servidor (match com cluster por (produto+servidor))
    prioridade_atual: str                # prioridade (parseada para "P1".."P5")
    status: str                          # status (sempre ativo após filtro)
    # Campos enriquecedores:
    solucao_alternativa: str = ""        # solucao_alternativa (workaround do PRB)
    origem: str = ""                     # origem (ex.: "Monitoração", "Reclame Aqui")
    categoria: str = ""                  # categoria
    subcategoria: str = ""               # subcategoria
    grupo_designado: str = ""            # grupo_designado
    qtd_atualizacoes: int = 0            # derivado de atualizacoes
    aberto_em: Optional[datetime] = None  # data_abertura
    data_resolucao: Optional[datetime] = None  # data_encerrado (marca entrega do Change Team)


# -----------------------------------------------------------------------------
# Domínio: Chamados de suporte (dynamics.chamados / kinghost.chamados)
# -----------------------------------------------------------------------------
@dataclass
class InteracaoChamado:
    """Chamado de suporte. A `organizacao` indica de qual tabela veio:
    'Locaweb' → dynamics.chamados | 'Kinghost' → kinghost.chamados.
    """
    chamado_id: str
    produto: str
    cliente_login: str
    organizacao: str                     # "Locaweb" | "Kinghost"
    data: datetime
    assunto: str
    origem: str = "cliente"              # canal/categorização (legado: cliente/analista)
    descricao: str = ""
    quantidade_interacoes_cliente: int = 0  # Kinghost: nativo. Dynamics: derivado.


# -----------------------------------------------------------------------------
# Domínio: Análise e Saída
# -----------------------------------------------------------------------------
@dataclass
class Cluster:
    """Grupo de INCs semanticamente similares, com métricas agregadas."""
    cluster_id: str
    nome: str                            # termo dominante (ex.: "kernel panic vps")
    incidentes: List[Incidente]
    servidor_principal: str              # CI mais frequente no grupo
    produto: str                         # produto majoritário
    qtd_incs: int
    score_criticidade: float             # 0.0 .. 1.0
    score_ineficiencia: float            # 0.0 .. 1.0
    tem_solucao_contorno: bool           # maioria dos incidentes
    tempo_contorno_min_medio: int
    chamados_relacionados: int = 0       # cruzamento de impacto real (dynamics/kinghost)
    cis_recorrentes_15d: List[str] = field(default_factory=list)
    termos_dominantes: List[str] = field(default_factory=list)

    @property
    def qtd_p3_idênticas(self) -> int:
        """Quantas INCs do cluster estão atualmente em P3 (gatilho proativo)."""
        return sum(1 for i in self.incidentes if i.prioridade_atual == "P3")


@dataclass
class PrescricaoPRB:
    """Saída do rules_engine: o que fazer com um cluster."""
    cluster_id: str
    acao: str                            # "ABRIR_PRB", "REPRIORIZAR_PRB", "MONITORAR", "NENHUMA"
    prioridade_sugerida: str             # P1..P5
    justificativa: List[str]             # bullets auditáveis
    urgencia: str                        # "CRITICA" | "ALTA" | "MEDIA" | "BAIXA" | "PLANEJADO"
    prb_existente: Optional[PRBExistente] = None
    prioridade_atual_prb: Optional[str] = None
    sugestao_repriorizacao: Optional[str] = None  # ex.: "Mudar prioridade de P3 para P2"


@dataclass
class SaudeCliente:
    """Avaliação de saúde de um cliente baseada no histórico dos últimos N meses.

    O atributo `alerta_recorrencia_alta` é o veredicto operacional — disparado
    quando o cliente acumula >= LIMIAR_INCS_SAUDE_CLIENTE INCs no período.
    Os demais campos são o histórico que embasa o veredicto.
    """
    cliente_login: str
    qtd_incs_periodo: int
    qtd_chamados_periodo: int
    severidade_media: float = 0.0   # 0.0 (rotineiro) a 1.0 (crítico), via PESO_PRIORIDADE_SEVERIDADE
    incs: List[Incidente] = field(default_factory=list)
    chamados: List[InteracaoChamado] = field(default_factory=list)
    alerta_recorrencia_alta: bool = False
    linha_do_tempo: List[Dict[str, Any]] = field(default_factory=list)  # ordenada por data


@dataclass
class ValidacaoEntrega:
    """Veredicto da validação retrospectiva de um PRB entregue pelo Change Team.

    Prisma complementar ao prescritivo: enquanto Rules Engine antecipa PRBs,
    o ValidadorEntrega olha PRBs já resolvidos e verifica se INCs do mesmo
    (produto, servidor) continuam aparecendo após a data de resolução.
    Fecha o loop de qualidade do fix.

    Campos da V2 (Radar CT): volumetria pré-resolução + delta de chamados
    pré/pós permitem responder "o PRB reduziu os contatos sobre o tema?".
    """
    prb_id: str
    descricao_curta: str
    produto: str
    servidor: str
    status_prb: str                       # ex.: "Aguardando Validação da Resolução"
    data_resolucao: datetime              # data_encerrado do PRB
    dias_pos_resolucao: int               # delta em dias entre agora e data_resolucao
    qtd_incs_pos_resolucao: int
    veredicto: str                        # "REINCIDENCIA" | "ENTREGA_VALIDADA" | "INCONCLUSIVO"
    incs_reincidentes: List[Incidente] = field(default_factory=list)

    # --- Contexto do PRB (V2 Radar CT) -----------------------------------------
    grupo_designado: str = ""             # squad/grupo dono do PRB no SNow
    data_abertura_prb: Optional[datetime] = None  # quando o PRB foi aberto (idade total)

    # --- Volumetria pré-resolução (V2) ----------------------------------------
    # Quantas INCs no mesmo (produto, servidor) o PRB cobriu nos 60 dias
    # anteriores à data_encerrado. Mede tamanho do problema que o CT resolveu.
    qtd_incs_pre_resolucao: int = 0
    clientes_unicos_pre: int = 0          # clientes distintos impactados pré-fix
    categorias_pre: int = 0               # diversidade de categorização

    # --- Delta de chamados pré vs pós (V2) ------------------------------------
    # Mesma janela em dias antes e depois da data_encerrado (config.JANELA_CHAMADOS_DELTA_DIAS).
    # Match via heurística por palavra-chave (ILIKE) — não há mapeamento direto
    # entre produto do PRB e produto/fila de chamados.
    palavra_chave_chamados: str = ""      # ex.: "Email" extraído de "Locaweb - Email"
    chamados_pre: int = 0
    chamados_pos: int = 0
    delta_chamados_pct: float = 0.0       # (pos - pre) / max(pre, 1); -1.0 a +inf


@dataclass
class ExecucaoMotor:
    """Estado completo de uma execução do motor (15 min). Alimenta dashboard e Slack."""
    timestamp: datetime
    clusters: List[Cluster] = field(default_factory=list)
    prescricoes: List[PrescricaoPRB] = field(default_factory=list)
    saude_clientes: List[SaudeCliente] = field(default_factory=list)
    validacoes_entrega: List[ValidacaoEntrega] = field(default_factory=list)
    total_incs_lidas: int = 0
    total_chamados: int = 0
    duracao_ciclo_ms: Optional[int] = None  # populado ao final de executar_ciclo
    erros: List[str] = field(default_factory=list)

    @property
    def alertas_criticos(self) -> List[PrescricaoPRB]:
        """Prescrições que devem disparar Slack imediato."""
        return [p for p in self.prescricoes if p.urgencia == "CRITICA"]

    @property
    def reincidencias_detectadas(self) -> List[ValidacaoEntrega]:
        """Validações que devem disparar Slack pro Change Team."""
        return [v for v in self.validacoes_entrega if v.veredicto == "REINCIDENCIA"]
