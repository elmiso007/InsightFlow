"""
Módulo de sincronização de dados de Gestão de Pessoas (G.H).

Realiza ETL (Extract, Transform, Load) de dados do Excel para o PostgreSQL,
exporta para Google Sheets e sincroniza com tabela de contratos (c_gh).

Estrutura:
- Leitura de dados do Excel G.H
- Transformação e normalização
- Inserção em tabela de staging (stg_dados_gh)
- Exportação para Google Sheets
- Sincronização com tabela c_gh

Autor: Sistema de RH
Data: 2026-02-04
"""

import pandas as pd
import psycopg2
from psycopg2 import sql
from datetime import datetime, date
import logging
import os
import sys
import importlib.util
from googleapiclient.discovery import build
from pathlib import Path
from io import StringIO

# === CONFIGURAÇÕES ===
SQL_PATH = Path(__file__).parent

# Caminhos de arquivos
EXCEL_PATH = SQL_PATH / 'G.H.xlsx'
SQL_INSERT_PATH = SQL_PATH / 'INSERT.sql'
SQL_UPDATE_PATH = SQL_PATH / 'UPDATE.sql'
LOG_PATH = SQL_PATH / 'logs' / 'gh_logfile.log'

# Configurações do Google Sheets
SPREADSHEET_ID = '1MmL9p4Hyn2DIYJKzY7vsbVM9h1Hw4wB0s-SMJMUFLhU'
SHEET_NAME = 'Dados_RH_Semanal!A1'
NOME_ABA_DADOS = 'Dados_RH_Semanal'
NOME_ABA_C_GH = 'C_GH'

# Configurações do banco de dados
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'cpro23221.publiccloud.com.br'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'report_requesttracker'),
    'user': os.getenv('DB_USER', 'a_report'),
    'password': os.getenv('DB_PASSWORD', 'Eequ8ohc')
}

# === LOGGING ===
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

# === MAPEAMENTO DE COLUNAS ===
COLUNA_MAPEAMENTO = {
    "EMPRESA DO FUNCIONARIO": "empresa_func",
    "RAZÃO SOCIAL": "razao_social",
    "CNPJ": "cnpj",
    "MATRICULA FUNCIONÁRIO": "matricula",
    "NOME FUNCIONÁRIO": "nome",
    "DATA DE ADMISSÃO": "admissao",
    "CARGO": "cargo",
    "MACRO CARGO": "macro_cargo",
    "NIVEL DE CARREIRA": "nivel_carreira",
    "GH FUNCIONÁRIO": "gh_funcionario",
    "DESCRIÇÃO GH FUNCIONÁRIO": "desc_gh_funcionario",
    "NOME GESTOR": "nome_gestor",
    "CENTRO DE CUSTO": "cc",
    "DESCRIÇÃO CENTRO DE CUSTO": "desc_cc",
    "DATA DE NASCIMENTO": "data_nascimento",
    "E-MAIL CORPORATIVO": "email_corporativo",
    "SITUAÇÃO ATUAL": "situacao",
    "SEXO": "sexo",
    "DIRETORIA GH": "diretoria_gh"
}

COLUNAS_FINAIS_C_GH = [
    "mes", "emp_mat", "nome_sobrenome", "nome", "cargo", "situacao", "gestor",
    "centro_de_custo", "desc_cc", "admissao", "empresa", "matricula", "equipe",
    "lider_bdo", "funcao", "carga_horaria", "rotacao", "data_nascimento", "upgrade"
]

# === CONEXÃO COM O BANCO ===
class DatabaseConnection:
    """Gerenciador de conexão com PostgreSQL."""
    
    def __init__(self, config):
        """Inicializa configuração do banco de dados."""
        self.config = config
        self.conn = None
        self.cur = None
    
    def conectar(self):
        """Abre conexão com o banco."""
        try:
            self.conn = psycopg2.connect(**self.config)
            self.cur = self.conn.cursor()
            logger.info("✓ Conectado ao banco de dados com sucesso.")
            return self
        except Exception as e:
            logger.error(f"✗ Erro ao conectar ao banco: {e}")
            sys.exit(1)
    
    def desconectar(self):
        """Fecha conexão com o banco."""
        try:
            if self.cur:
                self.cur.close()
            if self.conn:
                self.conn.close()
            logger.debug("Conexão com o banco fechada.")
        except Exception as e:
            logger.warning(f"Aviso ao desconectar: {e}")
    
    def __enter__(self):
        return self.conectar()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.desconectar()

# === FUNÇÕES DE TRANSFORMAÇÃO ===
def ler_excel(caminho):
    """
    Lê dados do arquivo Excel.
    
    Args:
        caminho: Path do arquivo Excel
        
    Returns:
        DataFrame com os dados lidos
    """
    try:
        df = pd.read_excel(caminho)
        logger.info(f"✓ Arquivo Excel lido: {len(df)} registros")
        return df
    except FileNotFoundError:
        logger.error(f"✗ Arquivo não encontrado: {caminho}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Erro ao ler Excel: {e}")
        sys.exit(1)

def transformar_dados(df):
    """
    Transforma e normaliza dados do DataFrame.
    
    Args:
        df: DataFrame com dados brutos
        
    Returns:
        DataFrame transformado
    """
    try:
        # Limpa nomes de colunas
        df.columns = [col.strip() for col in df.columns]
        
        # Remove colunas desnecessárias
        colunas_remover = ["MATRICULA GESTOR", "MACRO CARGO GESTOR"]
        df.drop(columns=colunas_remover, inplace=True, errors='ignore')
        
        # Renomeia colunas
        df.rename(columns=COLUNA_MAPEAMENTO, inplace=True)
        
        # Adiciona colunas de controle
        df['mes'] = pd.to_datetime(date.today().replace(day=1))
        df['data_gh'] = pd.to_datetime(datetime.now())
        
        logger.info(f"✓ Transformações aplicadas: {len(df)} registros processados")
        return df
    except Exception as e:
        logger.error(f"✗ Erro ao transformar dados: {e}")
        sys.exit(1)

# === FUNÇÕES DE CARREGAMENTO ===
def carregar_dados_staging(df, tabela_staging='stg_dados_gh'):
    """
    Carrega dados em tabela de staging via COPY do PostgreSQL.
    
    Args:
        df: DataFrame a ser inserido
        tabela_staging: Nome da tabela de destino
    """
    try:
        with DatabaseConnection(DB_CONFIG) as db:
            # Limpa tabela
            db.cur.execute(f"TRUNCATE TABLE public.{tabela_staging}")
            
            # Carrega dados via COPY (mais eficiente que INSERT)
            buffer = StringIO()
            df.to_csv(buffer, sep='\t', index=False, header=False)
            buffer.seek(0)
            
            db.cur.copy_from(
                buffer, 
                tabela_staging, 
                null='', 
                sep='\t', 
                columns=list(df.columns)
            )
            db.conn.commit()
            logger.info(f"✓ {len(df)} registros inseridos em {tabela_staging}")
    except Exception as e:
        logger.error(f"✗ Erro ao carregar dados em staging: {e}")
        sys.exit(1)

def executar_sql_arquivo(caminho_sql):
    """
    Executa SQL de um arquivo.
    
    Args:
        caminho_sql: Path do arquivo SQL
        
    Returns:
        Número de linhas afetadas
    """
    try:
        with open(caminho_sql, 'r', encoding='utf-8') as file:
            query = file.read()
        
        with DatabaseConnection(DB_CONFIG) as db:
            db.cur.execute(sql.SQL(query))
            linhas_afetadas = db.cur.rowcount
            db.conn.commit()
            logger.info(f"✓ SQL executado: {linhas_afetadas} linhas afetadas ({caminho_sql.name})")
            return linhas_afetadas
    except Exception as e:
        logger.error(f"✗ Erro ao executar SQL: {e}")
        sys.exit(1)

# === FUNÇÕES DO GOOGLE SHEETS ===
def autenticar_google_sheets():
    """
    Autentica com Google Sheets API usando módulo de autenticação.
    
    Returns:
        Serviço autenticado do Google Sheets
    """
    try:
        path_to_auth = SQL_PATH.parent / 'API Google' / 'auth.py'
        spec = importlib.util.spec_from_file_location('auth', path_to_auth)
        auth = importlib.util.module_from_spec(spec)
        sys.modules['auth'] = auth
        spec.loader.exec_module(auth)
        
        creds = auth.authenticate()
        service = build("sheets", "v4", credentials=creds)
        logger.info("✓ Autenticado no Google Sheets")
        return service
    except Exception as e:
        logger.error(f"✗ Erro ao autenticar Google Sheets: {e}")
        sys.exit(1)

def exportar_google_sheets(service, dados_query):
    """
    Exporta dados para Google Sheets.
    
    Args:
        service: Serviço Google Sheets
        dados_query: Tupla (dados, colunas) retornada do banco
    """
    try:
        dados, colunas = dados_query
        
        def formatar_linha(linha, colunas):
            """Formata valores de linha para exportação."""
            nova_linha = []
            for idx, cel in enumerate(linha):
                if colunas[idx] == 'matricula':
                    nova_linha.append(str(cel))
                elif isinstance(cel, (datetime, date)):
                    nova_linha.append(cel.strftime('%d/%m/%Y'))
                else:
                    nova_linha.append(str(cel) if cel is not None else "")
            return nova_linha
        
        valores = [colunas] + [formatar_linha(linha, colunas) for linha in dados]
        
        sheet = service.spreadsheets()
        sheet.values().clear(spreadsheetId=SPREADSHEET_ID, range=NOME_ABA_DADOS).execute()
        
        body = {
            "valueInputOption": "RAW",
            "data": [{"range": SHEET_NAME, "values": valores}]
        }
        
        sheet.values().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
        logger.info(f"✓ {len(dados)} registros exportados para Google Sheets")
    except Exception as e:
        logger.error(f"✗ Erro ao exportar para Google Sheets: {e}")
        sys.exit(1)

def obter_dados_google_sheets(service, aba):
    """
    Obtém dados de uma aba do Google Sheets.
    
    Args:
        service: Serviço Google Sheets
        aba: Nome da aba
        
    Returns:
        Valores obtidos da aba
    """
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, 
            range=aba
        ).execute()
        valores = result.get('values', [])
        logger.debug(f"✓ Dados obtidos de {aba}: {len(valores)} linhas")
        return valores
    except Exception as e:
        logger.error(f"✗ Erro ao obter dados de {aba}: {e}")
        return []

# === FUNÇÕES DE SINCRONIZAÇÃO ===
def processar_dados_c_gh(valores_c_gh):
    """
    Processa e prepara dados para inserção em c_gh.
    
    Args:
        valores_c_gh: Dados brutos do Google Sheets
        
    Returns:
        DataFrame processado ou None se vazio
    """
    try:
        if not valores_c_gh or len(valores_c_gh) < 2:
            logger.warning("⚠ Aba 'C_GH' está vazia ou contém apenas cabeçalhos")
            return None
        
        header = valores_c_gh[0]
        linhas = valores_c_gh[1:]
        df_c_gh = pd.DataFrame(linhas, columns=header)
        
        # Adiciona colunas de controle
        df_c_gh['mes'] = pd.to_datetime(date.today().replace(day=1))
        df_c_gh['upgrade'] = pd.to_datetime(datetime.now())
        
        # Converte datas para formato padrão
        df_c_gh['admissao'] = pd.to_datetime(
            df_c_gh['admissao'], 
            format='%d/%m/%Y', 
            errors='coerce'
        )
        df_c_gh['data_nascimento'] = pd.to_datetime(
            df_c_gh['data_nascimento'], 
            format='%d/%m/%Y', 
            errors='coerce'
        )
        
        # Converte carga horária
        df_c_gh['carga_horaria'] = pd.to_datetime(
            df_c_gh['carga_horaria'], 
            format='%H:%M', 
            errors='coerce'
        ).dt.time
        
        # Converte matrícula para inteiro
        df_c_gh['matricula'] = pd.to_numeric(
            df_c_gh['matricula'], 
            errors='coerce'
        ).fillna(0).astype(int)
        
        # Garante que todas as colunas finais existem
        for col in COLUNAS_FINAIS_C_GH:
            if col not in df_c_gh.columns:
                df_c_gh[col] = None
        
        df_c_gh = df_c_gh[COLUNAS_FINAIS_C_GH]
        logger.info(f"✓ {len(df_c_gh)} registros processados para c_gh")
        return df_c_gh
    except Exception as e:
        logger.error(f"✗ Erro ao processar dados c_gh: {e}")
        return None

# === FUNÇÃO PRINCIPAL ===
def main():
    """Executa o fluxo completo de sincronização de dados."""
    logger.info("=" * 60)
    logger.info("Iniciando sincronização de dados G.H")
    logger.info("=" * 60)
    
    try:
        # Etapa 1: Leitura e transformação
        logger.info("\n[1/5] Lendo e transformando dados do Excel...")
        df = ler_excel(EXCEL_PATH)
        df_transformado = transformar_dados(df)
        
        # Etapa 2: Carregamento na staging
        logger.info("\n[2/5] Carregando dados em tabela staging...")
        carregar_dados_staging(df_transformado, 'stg_dados_gh')
        
        # Etapa 3: Inserção na tabela principal
        logger.info("\n[3/5] Inserindo dados na tabela dados_gh...")
        executar_sql_arquivo(SQL_INSERT_PATH)
        
        # Etapa 4: Exportação para Google Sheets
        logger.info("\n[4/5] Exportando para Google Sheets...")
        service = autenticar_google_sheets()
        
        with DatabaseConnection(DB_CONFIG) as db:
            query_export = '''
                SELECT
                    matricula, nome, login, cc, desc_cc, cargo, nome_gestor,
                    gh_funcionario, desc_gh_funcionario, admissao, situacao,
                    data_nascimento, razao_social, diretoria_gh
                FROM dados_gh gh
                WHERE data_gh = (
                    SELECT MAX(data_gh)
                    FROM dados_gh gh2
                    WHERE gh2.mes >= '2025-01-01 00:00:00'
                )
                AND (empresa_func = '2' or empresa_func = '43')
            '''
            db.cur.execute(query_export)
            dados = db.cur.fetchall()
            colunas = [desc[0] for desc in db.cur.description]
        
        exportar_google_sheets(service, (dados, colunas))
        
        # Etapa 5: Sincronização com c_gh
        logger.info("\n[5/5] Sincronizando tabela c_gh...")
        valores_c_gh = obter_dados_google_sheets(service, NOME_ABA_C_GH)
        df_c_gh = processar_dados_c_gh(valores_c_gh)
        
        if df_c_gh is not None:
            carregar_dados_staging(df_c_gh, 'stg_c_gh')
            executar_sql_arquivo(SQL_UPDATE_PATH)
            logger.info("✓ Sincronização com c_gh concluída")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ Sincronização concluída com sucesso!")
        logger.info("=" * 60)
    
    except KeyboardInterrupt:
        logger.warning("\n⚠ Sincronização interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n✗ Erro não tratado: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()