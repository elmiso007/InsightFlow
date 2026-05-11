"""
Contact Rate Processor - Sistema de processamento e atualização de taxa de contato.

Este módulo processa dados de contato a partir de arquivos CSV, realiza transformações
e atualiza um banco de dados PostgreSQL com as métricas de taxa de contato.
"""

import pandas as pd
import psycopg2
from io import StringIO
from pathlib import Path
import logging
import sys
from typing import Tuple, Optional

# === CONFIGURAÇÕES ===
BASE_DIR = Path(__file__).resolve().parent

# Configuração de caminhos
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'contact_logfile.log'
CSV_FILE = BASE_DIR / 'Contact Rate_ Suporte N1.csv'

# === SETUP DE LOGGING ===
def setup_logging() -> logging.Logger:
    """Configura o sistema de logging com handlers para arquivo e console."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Evita handlers duplicados
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# === CONFIGURAÇÃO DE BANCO DE DADOS ===
DB_CONFIG = {
    'host': 'cpro23221.publiccloud.com.br',
    'port': '5432',
    'dbname': 'report_requesttracker',
    'user': 'a_report',
    'password': 'Eequ8ohc'
}

def create_database_connection() -> Tuple[Optional[psycopg2.extensions.connection], Optional[psycopg2.extensions.cursor]]:
    """
    Estabelece conexão com o banco de dados PostgreSQL.
    
    Returns:
        Tuple com conexão e cursor, ou (None, None) em caso de erro.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        logger.info("Conexão com o banco de dados estabelecida com sucesso.")
        return conn, cur
    except psycopg2.Error as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        return None, None

# === LEITURA E PROCESSAMENTO DO CSV ===
def read_csv_file(file_path: Path) -> pd.DataFrame:
    """
    Lê e processa o arquivo CSV com tratamento de encoding e formatação.
    
    Args:
        file_path: Caminho para o arquivo CSV
        
    Returns:
        DataFrame bruto com os dados do CSV
        
    Raises:
        SystemExit: Se o arquivo não puder ser processado
    """
    try:
        with open(file_path, mode='r', encoding='utf-8', newline='') as f:
            linhas = f.read().replace('\r\n', '\n').replace('\r', '\n').splitlines()

        linhas = [linha.strip().strip('"') for linha in linhas if linha.strip()]
        
        header = ['AnoMes', 'Clientes', 'Contatos', 'Contact Rate (%)']
        data = []

        for linha in linhas[1:]:
            partes = linha.replace('""', '').strip().strip('"').split(',')

            # Reconstrói campos com vírgula decimal
            if len(partes) == 5:
                partes[3] = f"{partes[3]},{partes[4]}"
                partes = partes[:4]

            if len(partes) == 4:
                data.append([p.strip() for p in partes])

        df = pd.DataFrame(data, columns=header)
        logger.info(f"Arquivo CSV processado com sucesso. {len(df)} linhas lidas.")
        return df
        
    except FileNotFoundError:
        logger.error(f"Arquivo CSV não encontrado: {file_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro ao processar o arquivo CSV: {e}")
        sys.exit(1)

def transform_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica transformações e validações ao DataFrame.
    
    Args:
        df: DataFrame bruto do CSV
        
    Returns:
        DataFrame transformado e validado
        
    Raises:
        SystemExit: Se houver erro na transformação
    """
    try:
        # Limpeza de colunas
        df.columns = [col.strip().replace('\ufeff', '') for col in df.columns]

        mapeamento_colunas = {
            "AnoMes": "data",
            "Clientes": "contratos",
            "Contatos": "contatos",
            "Contact Rate (%)": "contactrate",
        }
        df.rename(columns=mapeamento_colunas, inplace=True)

        # Transformações de tipo
        df['data'] = pd.to_datetime(df['data'], format="%Y/%m").dt.strftime("%Y/%m")
        
        # Converte números removendo separadores de milhares
        df['contratos'] = (
            df['contratos']
            .astype(str)
            .str.replace('.', '', regex=False)
            .astype(int)
        )
        
        df['contatos'] = (
            df['contatos']
            .astype(str)
            .str.replace('.', '', regex=False)
            .astype(int)
        )

        # Converte percentual para decimal
        df['contactrate'] = (
            df['contactrate']
            .astype(str)
            .str.strip()
            .str.replace('"', '', regex=False)
            .str.replace('%', '', regex=False)
            .str.replace(',', '.', regex=False)
            .astype(float) / 100
        ).round(4)

        logger.info("Transformações aplicadas com sucesso.")
        return df

    except Exception as e:
        logger.error(f"Erro durante a transformação dos dados: {e}")
        sys.exit(1)
def load_to_staging(conn: psycopg2.extensions.connection, 
                   cur: psycopg2.extensions.cursor, 
                   df: pd.DataFrame) -> bool:
    """
    Trunca a tabela staging e carrega os dados via COPY (mais rápido que INSERT).
    
    Args:
        conn: Conexão com o banco de dados
        cur: Cursor da conexão
        df: DataFrame com dados transformados
        
    Returns:
        True se sucesso, False caso contrário
    """
    try:
        cur.execute("TRUNCATE TABLE public.stg_contact_rate_kinghost;")
        conn.commit()
        logger.info("Tabela staging truncada com sucesso!")

        buffer = StringIO()
        df.to_csv(buffer, sep='\t', index=False, header=False)
        buffer.seek(0)

        copy_sql = f"""
            COPY public.stg_contact_rate_kinghost ({', '.join(f'"{col}"' for col in df.columns)})
            FROM STDIN WITH (FORMAT CSV, DELIMITER E'\t', NULL '', HEADER FALSE)
        """

        cur.copy_expert(sql=copy_sql, file=buffer)
        conn.commit()
        logger.info(f"{len(df)} linhas inseridas na tabela staging com sucesso.")
        return True

    except psycopg2.Error as e:
        logger.error(f"Erro na carga via COPY: {e}")
        conn.rollback()
        return False

def execute_sql_script(conn: psycopg2.extensions.connection, 
                      cur: psycopg2.extensions.cursor, 
                      file_path: Path, 
                      description: str) -> bool:
    """
    Executa um script SQL a partir de um arquivo.
    
    Args:
        conn: Conexão com o banco de dados
        cur: Cursor da conexão
        file_path: Caminho do arquivo SQL
        description: Descrição da operação para logging
        
    Returns:
        True se sucesso, False caso contrário
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            sql = file.read()
        
        cur.execute(sql)
        linhas_afetadas = cur.rowcount
        conn.commit()
        logger.info(f"{linhas_afetadas} linhas afetadas na {description}.")
        return True
        
    except psycopg2.Error as e:
        logger.error(f"Erro ao executar {description}: {e}")
        conn.rollback()
        return False
    except FileNotFoundError:
        logger.error(f"Arquivo SQL não encontrado: {file_path}")
        return False

# === FLUXO PRINCIPAL DE EXECUÇÃO ===
def main():
    """Executa o pipeline completo de processamento de contact rate."""
    conn, cur = create_database_connection()
    
    if not conn:
        sys.exit(1)
    
    try:
        logger.info("=" * 60)
        logger.info("Iniciando pipeline de processamento de Contact Rate")
        logger.info("=" * 60)
        
        # Leitura do CSV
        df = read_csv_file(CSV_FILE)
        
        # Transformação dos dados
        df_transformado = transform_dataframe(df)
        print(df_transformado)
        
        # Carregamento na tabela staging
        if not load_to_staging(conn, cur, df_transformado):
            raise Exception("Falha na carga para tabela staging")
        
        # Execução de INSERT
        insert_file = BASE_DIR / 'INSERT.sql'
        if not execute_sql_script(conn, cur, insert_file, 'inserção final'):
            raise Exception("Falha na execução do INSERT")
        
        # Execução de UPDATE
        update_file = BASE_DIR / 'UPDATE.sql'
        if not execute_sql_script(conn, cur, update_file, 'atualização final'):
            raise Exception("Falha na execução do UPDATE")
        
        logger.info("=" * 60)
        logger.info("Pipeline executado com sucesso!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Erro crítico no pipeline: {e}")
        sys.exit(1)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        logger.info("Conexão com banco de dados encerrada.")

if __name__ == '__main__':
    main()
