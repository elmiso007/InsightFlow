# =============================================================================
# Testes — validador_entrega (prisma retrospectivo)
# =============================================================================
# Cobertura: matriz dos 3 veredictos + edge cases (PRB sem CI, ordenação,
# precedência REINCIDENCIA sobre janela mínima).
# =============================================================================
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List

import config
from models import Incidente, PRBExistente
from validador_entrega import (
    VEREDICTO_REINCIDENCIA,
    VEREDICTO_VALIDADA,
    VEREDICTO_INCONCLUSIVO,
    _classificar,
    gerar_validacoes_entrega,
)

from builders import make_incidente, make_prb


# -----------------------------------------------------------------------------
# Fake fonte — só implementa o que o validador usa
# -----------------------------------------------------------------------------
class _FakeFonte:
    """Fonte de incidentes mínima: devolve PRBs e INCs sob comando.

    Implementa a parte da interface FonteIncidentes que o validador toca.
    Outros métodos lançam NotImplementedError — falham alto se algo mudar.
    """

    def __init__(
        self,
        prbs: List[PRBExistente],
        incs_por_chave: dict[tuple[str, str], List[Incidente]] | None = None,
        vol_pre_por_chave: dict[tuple[str, str], dict[str, int]] | None = None,
    ) -> None:
        self.prbs = prbs
        self.incs_por_chave = incs_por_chave or {}
        self.vol_pre_por_chave = vol_pre_por_chave or {}

    def listar_prbs_para_validacao(self, dias: int) -> List[PRBExistente]:
        return list(self.prbs)

    def listar_incidentes_por_produto_servidor(
        self, produto: str, servidor: str, desde: datetime
    ) -> List[Incidente]:
        return list(self.incs_por_chave.get((produto, servidor), []))

    def contar_incidentes_no_ci_periodo(
        self, produto: str, servidor: str, desde: datetime, ate: datetime
    ) -> dict:
        return self.vol_pre_por_chave.get(
            (produto, servidor),
            {"qtd": 0, "clientes_unicos": 0, "categorias": 0},
        )

    def listar_incidentes_recentes(self, horas):
        raise NotImplementedError

    def listar_prbs_abertos(self):
        raise NotImplementedError

    def listar_incidentes_cliente(self, login_cliente, meses):
        raise NotImplementedError


# -----------------------------------------------------------------------------
# Classificador puro
# -----------------------------------------------------------------------------
class TestClassificar:
    def test_reincidencia_pelo_limiar(self):
        # >= LIMIAR_INCS_REINCIDENCIA INCs => REINCIDENCIA, independente da janela
        assert _classificar(
            config.LIMIAR_INCS_REINCIDENCIA, 1
        ) == VEREDICTO_REINCIDENCIA

    def test_validada_quando_zero_incs_e_janela_suficiente(self):
        assert _classificar(0, config.MIN_DIAS_PARA_VALIDAR) == VEREDICTO_VALIDADA

    def test_inconclusivo_quando_janela_curta_sem_incs(self):
        # 0 INCs mas janela < MIN_DIAS_PARA_VALIDAR => INCONCLUSIVO
        assert _classificar(0, config.MIN_DIAS_PARA_VALIDAR - 1) == VEREDICTO_INCONCLUSIVO

    def test_inconclusivo_quando_poucas_incs(self):
        # 1 ou 2 INCs (abaixo do limiar de 3) e tempo qualquer => INCONCLUSIVO
        assert _classificar(
            config.LIMIAR_INCS_REINCIDENCIA - 1, 30
        ) == VEREDICTO_INCONCLUSIVO

    def test_reincidencia_tem_precedencia_sobre_janela_curta(self):
        # Reincidência detectada no 2º dia ainda é reincidência (não vira inconclusivo)
        assert _classificar(
            config.LIMIAR_INCS_REINCIDENCIA, 2
        ) == VEREDICTO_REINCIDENCIA


# -----------------------------------------------------------------------------
# Avaliação completa (gerar_validacoes_entrega)
# -----------------------------------------------------------------------------
def _agora() -> datetime:
    return datetime.now(timezone.utc)


class TestGerarValidacoes:
    def test_veredicto_validada_para_prb_resolvido_sem_incs_novas(self):
        prb = make_prb(
            prb_id="PRB0001",
            produto="VPS",
            servidor="vps-01",
            status="Aguardando Validação da Resolução",
            data_resolucao=_agora() - timedelta(days=config.MIN_DIAS_PARA_VALIDAR + 1),
        )
        fonte = _FakeFonte(prbs=[prb])  # sem INCs novas no produto/servidor
        validacoes = gerar_validacoes_entrega(fonte)

        assert len(validacoes) == 1
        assert validacoes[0].veredicto == VEREDICTO_VALIDADA
        assert validacoes[0].qtd_incs_pos_resolucao == 0

    def test_veredicto_reincidencia_quando_incs_voltam(self):
        prb = make_prb(
            prb_id="PRB0002",
            produto="DNS",
            servidor="dns-01",
            status="Encerrado Automaticamente",
            data_resolucao=_agora() - timedelta(days=5),
        )
        incs_novas = [
            make_incidente(
                inc_id=f"INC{i:07d}", produto="DNS", servidor="dns-01"
            )
            for i in range(config.LIMIAR_INCS_REINCIDENCIA + 1)
        ]
        fonte = _FakeFonte(prbs=[prb], incs_por_chave={("DNS", "dns-01"): incs_novas})

        validacoes = gerar_validacoes_entrega(fonte)

        assert len(validacoes) == 1
        v = validacoes[0]
        assert v.veredicto == VEREDICTO_REINCIDENCIA
        assert v.qtd_incs_pos_resolucao == len(incs_novas)
        assert len(v.incs_reincidentes) == len(incs_novas)

    def test_veredicto_inconclusivo_quando_janela_curta(self):
        # 0 INCs novas mas só 2 dias desde resolução — não dá pra validar ainda
        prb = make_prb(
            prb_id="PRB0003",
            produto="Hosting",
            servidor="hm-01",
            status="Aguardando Validação da Resolução",
            data_resolucao=_agora() - timedelta(days=2),
        )
        fonte = _FakeFonte(prbs=[prb])
        validacoes = gerar_validacoes_entrega(fonte)

        assert validacoes[0].veredicto == VEREDICTO_INCONCLUSIVO

    def test_prb_sem_produto_ou_servidor_vira_inconclusivo(self):
        # Sem CI não dá pra matchar INCs — vira INCONCLUSIVO defensivo
        prb = make_prb(
            prb_id="PRB0004",
            produto="",
            servidor="",
            data_resolucao=_agora() - timedelta(days=20),
        )
        fonte = _FakeFonte(prbs=[prb])
        validacoes = gerar_validacoes_entrega(fonte)

        assert validacoes[0].veredicto == VEREDICTO_INCONCLUSIVO
        assert validacoes[0].qtd_incs_pos_resolucao == 0

    def test_ordenacao_reincidencia_primeiro(self):
        # Mistura: 1 validada, 1 reincidência, 1 inconclusivo — reincidência deve
        # aparecer no topo (ordem útil pro plantão).
        prb_validada = make_prb(
            prb_id="PRB_OK", produto="VPS", servidor="vps-ok",
            data_resolucao=_agora() - timedelta(days=10),
        )
        prb_reinc = make_prb(
            prb_id="PRB_REINC", produto="DNS", servidor="dns-bad",
            data_resolucao=_agora() - timedelta(days=5),
        )
        prb_incon = make_prb(
            prb_id="PRB_INCON", produto="MAIL", servidor="mail-x",
            data_resolucao=_agora() - timedelta(days=2),
        )
        incs = [
            make_incidente(inc_id=f"INC{i}", produto="DNS", servidor="dns-bad")
            for i in range(config.LIMIAR_INCS_REINCIDENCIA + 1)
        ]
        fonte = _FakeFonte(
            prbs=[prb_validada, prb_reinc, prb_incon],
            incs_por_chave={("DNS", "dns-bad"): incs},
        )

        validacoes = gerar_validacoes_entrega(fonte)

        assert [v.prb_id for v in validacoes][0] == "PRB_REINC"
        assert validacoes[0].veredicto == VEREDICTO_REINCIDENCIA

    def test_erro_em_um_prb_nao_derruba_outros(self):
        # PRB problemático: produto/servidor que cause exceção na fonte (simula bug)
        class _FontePicada(_FakeFonte):
            def listar_incidentes_por_produto_servidor(self, produto, servidor, desde):
                if produto == "QUEBRA":
                    raise RuntimeError("simulação de bug")
                return super().listar_incidentes_por_produto_servidor(produto, servidor, desde)

        prb_ok = make_prb(
            prb_id="PRB_OK", produto="VPS", servidor="vps-ok",
            data_resolucao=_agora() - timedelta(days=10),
        )
        prb_quebra = make_prb(
            prb_id="PRB_QUEBRA", produto="QUEBRA", servidor="x",
            data_resolucao=_agora() - timedelta(days=10),
        )
        fonte = _FontePicada(prbs=[prb_quebra, prb_ok])
        validacoes = gerar_validacoes_entrega(fonte)

        # Apenas o PRB_OK deve sobreviver — o outro foi catched no _avaliar_prb
        prb_ids = [v.prb_id for v in validacoes]
        assert "PRB_OK" in prb_ids
        assert "PRB_QUEBRA" not in prb_ids

# -----------------------------------------------------------------------------
# Fake fonte de chamados — só implementa o que o validador V2 usa
# -----------------------------------------------------------------------------
class _FakeFonteChamados:
    """Devolve contagens fixas por produto sob comando.

    Estrutura: contagens_por_produto = {produto: {"pre": N, "pos": M}}
    O validador pede pre/pos via desde<ate; aqui sabemos se é a primeira
    chamada (pre) ou a segunda (pos) por proximidade da data_ref.
    """

    def __init__(
        self,
        contagens_por_produto: dict[str, dict[str, int]] | None = None,
    ) -> None:
        self.contagens_por_produto = contagens_por_produto or {}
        # Histórico de chamadas: lista de (produto, desde, ate)
        self.chamadas: List[tuple] = []

    def contar_chamados_por_produto(self, produto, desde, ate):
        self.chamadas.append((produto, desde, ate))
        cfg = self.contagens_por_produto.get(produto)
        if not cfg:
            return 0
        # A 1ª chamada para um produto é "pre" (desde < ate <= data_ref),
        # a 2ª é "pos". Para simplificar, alternamos com base no histórico.
        nth = sum(1 for c in self.chamadas if c[0] == produto)
        return cfg.get("pre" if nth == 1 else "pos", 0)

    def listar_chamados_periodo(self, horas, produtos=None):
        return []

    def listar_chamados_cliente(self, login_cliente, meses):
        return []


# -----------------------------------------------------------------------------
# Volumetria pré-resolução + Delta de chamados (V2)
# -----------------------------------------------------------------------------
class TestVolumetriaPre:
    def test_volumetria_pre_propagada_para_validacao(self):
        prb = make_prb(
            prb_id="PRB_X", produto="VPS", servidor="vps-01",
            data_resolucao=_agora() - timedelta(days=10),
        )
        fonte = _FakeFonte(
            prbs=[prb],
            vol_pre_por_chave={
                ("VPS", "vps-01"): {"qtd": 25, "clientes_unicos": 12, "categorias": 4},
            },
        )
        validacoes = gerar_validacoes_entrega(fonte)
        v = validacoes[0]
        assert v.qtd_incs_pre_resolucao == 25
        assert v.clientes_unicos_pre == 12
        assert v.categorias_pre == 4

    def test_volumetria_pre_zero_quando_fonte_nao_tem(self):
        prb = make_prb(
            prb_id="PRB_X", produto="VPS", servidor="vps-01",
            data_resolucao=_agora() - timedelta(days=10),
        )
        fonte = _FakeFonte(prbs=[prb])
        validacoes = gerar_validacoes_entrega(fonte)
        v = validacoes[0]
        assert v.qtd_incs_pre_resolucao == 0
        assert v.clientes_unicos_pre == 0
        assert v.categorias_pre == 0


class TestDeltaChamados:
    def test_delta_negativo_quando_chamados_caem(self):
        # Pre=20, Pos=5 → delta = (5-20)/20 = -0.75 (queda de 75%)
        prb = make_prb(
            prb_id="PRB_X", produto="VPS", servidor="vps-01",
            data_resolucao=_agora() - timedelta(days=10),
        )
        fonte_inc = _FakeFonte(prbs=[prb])
        fonte_ch = _FakeFonteChamados(
            contagens_por_produto={"VPS": {"pre": 20, "pos": 5}},
        )
        validacoes = gerar_validacoes_entrega(fonte_inc, fonte_ch)
        v = validacoes[0]
        assert v.chamados_pre == 20
        assert v.chamados_pos == 5
        assert v.delta_chamados_pct == -0.75

    def test_delta_zero_quando_pre_zero(self):
        # Sem base, delta = 0.0 (não pode dividir por zero)
        prb = make_prb(
            prb_id="PRB_X", produto="VPS", servidor="vps-01",
            data_resolucao=_agora() - timedelta(days=10),
        )
        fonte_inc = _FakeFonte(prbs=[prb])
        fonte_ch = _FakeFonteChamados(
            contagens_por_produto={"VPS": {"pre": 0, "pos": 0}},
        )
        validacoes = gerar_validacoes_entrega(fonte_inc, fonte_ch)
        v = validacoes[0]
        assert v.chamados_pre == 0
        assert v.chamados_pos == 0
        assert v.delta_chamados_pct == 0.0

    def test_sem_fonte_chamados_delta_continua_zero(self):
        # Quando gerar_validacoes_entrega é chamado sem fonte_chamados,
        # delta fica 0 mas demais campos funcionam normalmente.
        prb = make_prb(
            prb_id="PRB_X", produto="VPS", servidor="vps-01",
            data_resolucao=_agora() - timedelta(days=10),
        )
        fonte_inc = _FakeFonte(prbs=[prb])
        validacoes = gerar_validacoes_entrega(fonte_inc)  # sem fonte_chamados
        v = validacoes[0]
        assert v.chamados_pre == 0
        assert v.chamados_pos == 0
        assert v.delta_chamados_pct == 0.0

    def test_delta_positivo_quando_chamados_sobem(self):
        # Pre=4, Pos=10 → delta = (10-4)/4 = 1.5 (subida de 150%)
        prb = make_prb(
            prb_id="PRB_X", produto="VPS", servidor="vps-01",
            data_resolucao=_agora() - timedelta(days=10),
        )
        fonte_inc = _FakeFonte(prbs=[prb])
        fonte_ch = _FakeFonteChamados(
            contagens_por_produto={"VPS": {"pre": 4, "pos": 10}},
        )
        validacoes = gerar_validacoes_entrega(fonte_inc, fonte_ch)
        v = validacoes[0]
        assert v.delta_chamados_pct == 1.5
