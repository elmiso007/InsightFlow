"""
Configuração centralizada da pipeline de carga de áudios.
Lê variáveis do .env e expõe um objeto config com todos os parâmetros.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / '.env')


class Config:
    # ------------------------------------------------------------------
    # Yeastar PBX
    # ------------------------------------------------------------------
    YEASTAR_URL      = os.getenv('YEASTAR_URL', 'https://locaweb.ras.yeastar.com')
    YEASTAR_USER     = os.getenv('YEASTAR_USER', '')
    YEASTAR_PASS     = os.getenv('YEASTAR_PASS', '')
    YEASTAR_TFA_CODE = os.getenv('YEASTAR_TFA_CODE', '')  # código 2FA (usado só na 1ª execução por ambiente)

    # ------------------------------------------------------------------
    # Banco PG17 (destino das transcrições)
    # ------------------------------------------------------------------
    DB17_HOST   = os.getenv('DB17_HOST', '')
    DB17_PORT   = int(os.getenv('DB17_PORT', '5432'))
    DB17_NAME   = os.getenv('DB17_NAME', '')
    DB17_USER   = os.getenv('DB17_USER', '')
    DB17_PASS   = os.getenv('DB17_PASS', '')
    DB17_SCHEMA = os.getenv('DB17_SCHEMA', 'lw_octadesk')

    # ------------------------------------------------------------------
    # Transcrição (faster-whisper)
    # ------------------------------------------------------------------
    WHISPER_MODEL    = os.getenv('WHISPER_MODEL', 'medium')
    WHISPER_DEVICE   = os.getenv('WHISPER_DEVICE', 'cpu')
    WHISPER_LANGUAGE = os.getenv('WHISPER_LANGUAGE', 'pt')

    # ------------------------------------------------------------------
    # Comportamento da pipeline
    # ------------------------------------------------------------------
    # Diretório temporário para os áudios (relativo à raiz do projeto)
    TEMP_DIR  = Path(__file__).parent / os.getenv('TEMP_DIR', 'temp_audio')

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    @classmethod
    def validate(cls):
        """Verifica se as credenciais obrigatórias estão preenchidas."""
        erros = []
        if not cls.YEASTAR_USER:
            erros.append('YEASTAR_USER não configurado')
        if not cls.YEASTAR_PASS:
            erros.append('YEASTAR_PASS não configurado')
        if not cls.DB17_HOST:
            erros.append('DB17_HOST não configurado')
        if not cls.DB17_NAME:
            erros.append('DB17_NAME não configurado')
        if erros:
            raise EnvironmentError('Configuração incompleta:\n' + '\n'.join(f'  - {e}' for e in erros))


config = Config()