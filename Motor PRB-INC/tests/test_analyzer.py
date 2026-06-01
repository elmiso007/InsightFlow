# =============================================================================
# Testes — scores do analyzer
# =============================================================================
# Foco: garantir que _score_criticidade e _score_ineficiencia produzem valores
# determinísticos e no range esperado [0.0, 1.0]. Hotspot — score errado
# impacta priorização downstream.
# =============================================================================
from datetime import datetime, timezone, timedelta

import pytest

from analyzer import _score_criticidade, _score_ineficiencia, _termos_dominantes
from builders import make_incidente


# -----------------------------------------------------------------------------
# _score_criticidade
# -----------------------------------------------------------------------------
class TestScoreCriticidade:
    def test_range_sempre_entre_0_e_1(self):
        incs = [make_incidente()]
        score = _score_criticidade(incs, total_incs=1, cis_recorrentes=[])
        assert 0.0 <= score <= 1.0

    def test_total_incs_zero_retorna_zero(self):
        # Edge case: dataset vazio.
        score = _score_criticidade([], total_incs=0, cis_recorrentes=[])
        assert score == 0.0

    def test_tudo_critico_da_score_alto(self):
        # Volume 100%, indisponibilidade, sem contorno, CI recorrente → score próximo de 1.
        incs = [
            make_incidente(
                tem_contorno=False,
                descricao_curta="Servidor fora do ar",
                descricao="Não pinga, indisponível",
                servidor="srv-001",
            )
            for _ in range(10)
        ]
        score = _score_criticidade(incs, total_incs=10, cis_recorrentes=["srv-001"])
        assert score > 0.9  # quase máximo

    def test_baixa_criticidade(self):
        # 1 INC com contorno, sem termos críticos, sem CI recorrente.
        incs = [make_incidente(
            tem_contorno=True,
            descricao_curta="Lentidão pontual",
            descricao="Cliente reportou lentidão.",
        )]
        score = _score_criticidade(incs, total_incs=100, cis_recorrentes=[])
        assert score < 0.2  # baixo

    def test_recorrencia_apenas_contribui_010(self):
        # Apenas componente recorrência alto, outros baixos.
        incs = [make_incidente(tem_contorno=True, servidor="srv-recorrente")]
        score = _score_criticidade(incs, total_incs=100, cis_recorrentes=["srv-recorrente"])
        # PESO_RECORRENCIA_CI = 0.10, volume mínimo (1/100), outros zero.
        assert 0.10 < score < 0.15


# -----------------------------------------------------------------------------
# _score_ineficiencia
# -----------------------------------------------------------------------------
class TestScoreIneficiencia:
    def test_lista_vazia_retorna_zero(self):
        assert _score_ineficiencia([]) == 0.0

    def test_range_sempre_entre_0_e_1(self):
        incs = [make_incidente(qtd_updates=5)]
        score = _score_ineficiencia(incs)
        assert 0.0 <= score <= 1.0

    def test_muitas_atualizacoes_eleva_componente_volume(self):
        # Volume satura quando média >= LIMIAR_UPDATES_INEFICIENTE (8).
        incs = [make_incidente(qtd_updates=15) for _ in range(5)]
        score = _score_ineficiencia(incs)
        assert score > 0.5  # pelo menos componente volume alto

    def test_poucas_atualizacoes_score_baixo(self):
        # Poucas atualizações E espaçadas no tempo (24h) → baixo em ambos
        # componentes (volume baixo + velocidade baixa).
        now = datetime.now(timezone.utc)
        incs = [
            make_incidente(
                qtd_updates=1,
                abertura=now - timedelta(hours=24),
                atualizacao=now - timedelta(hours=1),
            )
            for _ in range(5)
        ]
        score = _score_ineficiencia(incs)
        assert score < 0.3

    def test_velocidade_alta_com_volume_alto(self):
        # INCs com muitos updates e janela curta (1h) → updates/hora alto.
        now = datetime.now(timezone.utc)
        incs = [
            make_incidente(
                qtd_updates=10,
                abertura=now - timedelta(hours=1),
                atualizacao=now,
            )
            for _ in range(5)
        ]
        score = _score_ineficiencia(incs)
        # Volume (10/8=1.25→satura em 1.0) + Velocidade (10/h / 2 = 5→satura em 1.0)
        assert score >= 0.99


# -----------------------------------------------------------------------------
# _termos_dominantes
# -----------------------------------------------------------------------------
class TestTermosDominantes:
    def test_retorna_top_n(self):
        incs = [
            make_incidente(descricao_curta="kernel panic", descricao="vps fora")
            for _ in range(3)
        ]
        termos = _termos_dominantes(incs, top_n=3)
        assert len(termos) <= 3

    def test_descarta_palavras_curtas(self):
        incs = [make_incidente(descricao_curta="a b c", descricao="kernel x y")]
        termos = _termos_dominantes(incs)
        # Tokens com len < 3 não entram.
        assert "kernel" in termos
        assert "a" not in termos
        assert "b" not in termos

    def test_descarta_digitos_puros(self):
        incs = [make_incidente(descricao_curta="2026", descricao="kernel panic")]
        termos = _termos_dominantes(incs)
        assert "2026" not in termos
        assert "kernel" in termos