# =============================================================================
# Testes — parsers defensivos do extractor
# =============================================================================
# Foco: garantir que parsers (datas, prioridade, atualizações, contorno) lidam
# com dados malformados sem propagar exceção. Hotspot crítico — dados do banco
# vêm como text e podem ter qualquer formato.
# =============================================================================
from datetime import datetime, timezone

import pytest

from extractor import (
    _parse_datetime,
    _parse_prioridade,
    _contar_atualizacoes,
    _detectar_contorno,
)


# -----------------------------------------------------------------------------
# _parse_datetime
# -----------------------------------------------------------------------------
class TestParseDatetime:
    def test_data_valida_ISO_retorna_utc_tz_aware(self):
        resultado = _parse_datetime("2026-05-27 14:30:00")
        assert resultado is not None
        assert resultado.tzinfo is not None
        assert resultado.tzinfo == timezone.utc

    def test_data_nula_retorna_none(self):
        assert _parse_datetime(None) is None

    def test_data_vazia_retorna_none(self):
        assert _parse_datetime("") is None

    def test_data_malformada_retorna_none(self):
        assert _parse_datetime("abc") is None
        assert _parse_datetime("25/05/2026") is None  # formato BR não aceito

    def test_data_com_whitespace_ignorado(self):
        resultado = _parse_datetime("  2026-05-27 14:30:00  ")
        assert resultado is not None

    def test_conversao_brt_para_utc(self):
        # 14:30 BRT = 17:30 UTC (BRT é UTC-3)
        resultado = _parse_datetime("2026-05-27 14:30:00")
        assert resultado.hour == 17
        assert resultado.minute == 30


# -----------------------------------------------------------------------------
# _parse_prioridade
# -----------------------------------------------------------------------------
class TestParsePrioridade:
    @pytest.mark.parametrize("entrada,esperado", [
        ("1", "P1"),
        ("2", "P2"),
        ("3", "P3"),
        ("4", "P4"),
        ("5", "P5"),
    ])
    def test_numero_isolado(self, entrada, esperado):
        assert _parse_prioridade(entrada) == esperado

    @pytest.mark.parametrize("entrada", ["P1", "P2", "P3", "P4", "P5"])
    def test_ja_normalizada(self, entrada):
        assert _parse_prioridade(entrada) == entrada

    def test_nula_volta_p4(self):
        assert _parse_prioridade(None) == "P4"

    def test_vazia_volta_p4(self):
        assert _parse_prioridade("") == "P4"

    def test_invalida_volta_p4(self):
        assert _parse_prioridade("xyz") == "P4"
        assert _parse_prioridade("99") == "P99"  # numero invalido virou P99 (limitação consciente)


# -----------------------------------------------------------------------------
# _contar_atualizacoes
# -----------------------------------------------------------------------------
class TestContarAtualizacoes:
    def test_nulo_retorna_zero(self):
        assert _contar_atualizacoes(None) == 0

    def test_vazio_retorna_zero(self):
        assert _contar_atualizacoes("") == 0

    def test_conta_timestamps(self):
        texto = """
        2026-05-27 14:30:00 - João - Investiguei
        2026-05-27 15:00:00 - Maria - Resolvido
        """
        assert _contar_atualizacoes(texto) == 2

    def test_fallback_blocos_separados(self):
        texto = "Primeira anotação\n\nSegunda anotação\n\nTerceira anotação"
        assert _contar_atualizacoes(texto) == 3

    def test_um_unico_timestamp(self):
        assert _contar_atualizacoes("2026-05-27 14:30:00 - resolvido") == 1


# -----------------------------------------------------------------------------
# _detectar_contorno
# -----------------------------------------------------------------------------
class TestDetectarContorno:
    def test_termo_contorno_simples(self):
        assert _detectar_contorno("Há contorno aplicado") is True

    def test_workaround(self):
        assert _detectar_contorno("Workaround temporário") is True

    def test_sem_termo(self):
        assert _detectar_contorno("Servidor caiu, investigando") is False

    def test_multiplos_argumentos(self):
        # Função aceita *textos
        assert _detectar_contorno("normal", "tem contorno aqui") is True
        assert _detectar_contorno("normal", "também normal") is False

    def test_nulos_ignorados(self):
        assert _detectar_contorno(None, "tem workaround") is True
        assert _detectar_contorno(None, None) is False