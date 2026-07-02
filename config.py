"""
Módulo de Configuração - Sistema de Análise NPS
================================================

Carrega configurações de variáveis de ambiente e fornece
valores padrão caso não estejam definidas.

Uso:
    from config import config
    api_key = config.GEMINI_API_KEY
"""

import os
import configparser
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Caminho do arquivo config.ini na raiz do workspace
WORKSPACE_CONFIG_PATH = Path(__file__).resolve().parent.parent / 'config.ini'


def _read_ini_config(path: Path):
    """Lê as chaves do config.ini do workspace, se existir."""
    parser = configparser.ConfigParser()
    if not path.exists():
        return {}

    try:
        parser.read(path, encoding='utf-8')
        return {
            section: dict(parser.items(section))
            for section in parser.sections()
        }
    except Exception:
        return {}


INI_CONFIG = _read_ini_config(WORKSPACE_CONFIG_PATH)


def _get_config_value(section: str, key: str, default=None):
    """Retorna valor do config.ini quando existir, senão usa o .env/valor padrão."""
    ini_section = INI_CONFIG.get(section, {})
    if key in ini_section and ini_section[key] not in (None, ''):
        return ini_section[key]

    env_key = {
        'database': {
            'server': 'DB_HOST',
            'port': 'DB_PORT',
            'database': 'DB_NAME',
            'uid': 'DB_USER',
            'pwd': 'DB_PASSWORD',
        },
        'gemini': {
            'api_key': 'GEMINI_API_KEY',
            'model': 'GEMINI_MODEL',
        },
    }.get(section, {}).get(key)

    if env_key:
        return os.getenv(env_key, default)
    return default


class Config:
    """Classe de configuração centralizada"""
    
    # ======================================================================
    # BANCO DE DADOS
    # ======================================================================
    DB_HOST = _get_config_value('database', 'server', os.getenv('DB_HOST', 'localhost'))
    DB_PORT = int(_get_config_value('database', 'port', os.getenv('DB_PORT', '5432')))
    DB_NAME = _get_config_value('database', 'database', os.getenv('DB_NAME', 'report_requesttracker'))
    DB_USER = _get_config_value('database', 'uid', os.getenv('DB_USER', 'postgres'))
    DB_PASSWORD = _get_config_value('database', 'pwd', os.getenv('DB_PASSWORD', ''))
    DB_SCHEMA = os.getenv('DB_SCHEMA', 'kinghost_octadesk')
    
    # ======================================================================
    # API GEMINI
    # ======================================================================
    GEMINI_API_KEY = _get_config_value('gemini', 'api_key', os.getenv('GEMINI_API_KEY'))
    GEMINI_MODEL = _get_config_value('gemini', 'model', os.getenv('GEMINI_MODEL', 'gemini-flash-latest'))
    
    # ======================================================================
    # CONFIGURAÇÕES DE NPS
    # ======================================================================
    NPS_META = float(os.getenv('NPS_META', '70.0'))
    NPS_MIN_AVALIACOES = int(os.getenv('NPS_MIN_AVALIACOES', '3'))
    NPS_PERIODO_TIPO = os.getenv('NPS_PERIODO_TIPO', 'mes_anterior')
    
    # ======================================================================
    # CONFIGURAÇÕES DE ANÁLISE IA
    # ======================================================================
    ANALISE_MAX_DATASET_SIZE = int(os.getenv('ANALISE_MAX_DATASET_SIZE', '12000'))
    ANALISE_MAX_TENTATIVAS = int(os.getenv('ANALISE_MAX_TENTATIVAS', '5'))
    ANALISE_DELAY_TENTATIVA = int(os.getenv('ANALISE_DELAY_TENTATIVA', '5'))
    ANALISE_RETENTION_DAYS = int(os.getenv('ANALISE_RETENTION_DAYS', '90'))
    ANALISE_MAX_ATENDIMENTOS_POR_ANALISTA = int(os.getenv('ANALISE_MAX_ATENDIMENTOS_POR_ANALISTA', '30'))
    
    # Processamento Paralelo
    # Para plano FREE: use 1 (sequencial) ou 2 (semi-paralelo)
    # Para plano PAGO: use 4-8 (paralelo completo)
    PARALELO_MAX_WORKERS = int(os.getenv('PARALELO_MAX_WORKERS', '1'))
    
    # ======================================================================
    # LOGGING
    # ======================================================================
    LOG_FILE_LEVEL = os.getenv('LOG_FILE_LEVEL', 'DEBUG')
    LOG_CONSOLE_LEVEL = os.getenv('LOG_CONSOLE_LEVEL', 'INFO')
    LOG_MAX_SIZE_MB = int(os.getenv('LOG_MAX_SIZE_MB', '10'))
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # ======================================================================
    # CAMINHOS DE ARQUIVOS
    # ======================================================================
    OUTPUT_PATH = os.getenv('OUTPUT_PATH', '')
    ARQUIVO_ATENDIMENTOS_PREFIX = os.getenv('ARQUIVO_ATENDIMENTOS_PREFIX', 'atendimentos_nps_baixo')
    ARQUIVO_RESPOSTA_PREFIX = os.getenv('ARQUIVO_RESPOSTA_PREFIX', 'resposta_nps_gemini')
    
    # ======================================================================
    # AMBIENTE
    # ======================================================================
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    
    @classmethod
    def validate(cls):
        """Valida se as configurações essenciais estão presentes"""
        errors = []
        
        if not cls.GEMINI_API_KEY:
            errors.append("❌ GEMINI_API_KEY não configurada no .env")
        
        if not cls.DB_PASSWORD:
            errors.append("⚠️  DB_PASSWORD não configurada no .env")
        
        if errors:
            print("\n🔴 ERROS DE CONFIGURAÇÃO:")
            for error in errors:
                print(f"  {error}")
            print("\n💡 Verifique o arquivo .env e configure as variáveis necessárias.\n")
            return False
        
        return True
    
    @classmethod
    def print_config(cls, hide_sensitive=True):
        """Exibe as configurações atuais (opcionalmente ocultando dados sensíveis)"""
        print("\n" + "="*70)
        print("⚙️  CONFIGURAÇÕES DO SISTEMA")
        print("="*70)
        
        print("\n📊 Banco de Dados:")
        print(f"  Host: {cls.DB_HOST}:{cls.DB_PORT}")
        print(f"  Database: {cls.DB_NAME}")
        print(f"  User: {cls.DB_USER}")
        print(f"  Password: {'*' * 10 if hide_sensitive and cls.DB_PASSWORD else cls.DB_PASSWORD}")
        print(f"  Schema: {cls.DB_SCHEMA}")
        
        print("\n🤖 API Gemini:")
        print(f"  Model: {cls.GEMINI_MODEL}")
        api_key_display = f"{cls.GEMINI_API_KEY[:10]}...{cls.GEMINI_API_KEY[-4:]}" if cls.GEMINI_API_KEY and hide_sensitive else cls.GEMINI_API_KEY
        print(f"  API Key: {api_key_display}")
        
        print("\n📈 Configurações NPS:")
        print(f"  Meta: {cls.NPS_META}")
        print(f"  Mín. Avaliações: {cls.NPS_MIN_AVALIACOES}")
        print(f"  Período: {cls.NPS_PERIODO_TIPO}")
        
        print("\n🔍 Análise IA:")
        print(f"  Max Dataset Size: {cls.ANALISE_MAX_DATASET_SIZE} chars")
        print(f"  Max Atendimentos por Analista: {cls.ANALISE_MAX_ATENDIMENTOS_POR_ANALISTA}")
        print(f"  Max Tentativas: {cls.ANALISE_MAX_TENTATIVAS}")
        print(f"  Delay: {cls.ANALISE_DELAY_TENTATIVA}s")
        
        print("\n📝 Logging:")
        print(f"  File Level: {cls.LOG_FILE_LEVEL}")
        print(f"  Console Level: {cls.LOG_CONSOLE_LEVEL}")
        print(f"  Max Size: {cls.LOG_MAX_SIZE_MB}MB")
        print(f"  Backups: {cls.LOG_BACKUP_COUNT}")
        
        print("\n🌍 Ambiente:")
        print(f"  Environment: {cls.ENVIRONMENT}")
        
        print("\n" + "="*70 + "\n")


# Instância global de configuração
config = Config()


# Validação automática ao importar (pode ser desabilitada se necessário)
if __name__ == "__main__":
    # Quando executado diretamente, mostra as configurações
    if config.validate():
        print("✅ Todas as configurações essenciais estão presentes!")
        config.print_config(hide_sensitive=True)
    else:
        print("\n⚠️  Configure o arquivo .env antes de executar a aplicação.")

