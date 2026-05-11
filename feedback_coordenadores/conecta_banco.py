import psycopg2
from sqlalchemy import create_engine
import pyodbc
import pandas as pd
from contextlib import contextmanager
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import config

# Configurar logger
logger = logging.getLogger('nps_monitor.database')

# Configurações de conexão carregadas do .env
server = config.DB_HOST
port = config.DB_PORT
database = config.DB_NAME
uid = config.DB_USER
pwd = config.DB_PASSWORD


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    reraise=True
)
def get_sqlalchemy_engine():
    """
    Cria e retorna uma engine SQLAlchemy para PostgreSQL
    Com retry automático (3 tentativas) e backoff exponencial
    
    Returns:
        Engine: Engine SQLAlchemy configurada
    
    Raises:
        sqlalchemy.exc.OperationalError: Erro de conexão com banco
        sqlalchemy.exc.DatabaseError: Erro geral de banco de dados
    """
    try:
        # Conexão com PostgreSQL usando SQLAlchemy
        engine_conn_string = f"postgresql://{uid}:{pwd}@{server}:{port}/{database}"
        engine = create_engine(engine_conn_string)
        logger.debug(f"Engine SQLAlchemy criada para {database}@{server}")
        return engine
    except Exception as e:
        logger.error(f"Erro ao criar engine SQLAlchemy: {str(e)}")
        raise


def get_pyodbc_connection():
    """
    Cria e retorna uma conexão pyodbc para PostgreSQL
    
    Returns:
        Connection: Conexão pyodbc configurada
    
    Raises:
        pyodbc.OperationalError: Erro de conexão
        pyodbc.DatabaseError: Erro de banco de dados
    """
    try:
        # Conexão com PostgreSQL usando pyodbc
        driver = '{PostgreSQL Unicode(x64)}'
        conn_string = f'DRIVER={driver};SERVER={server};PORT={port};DATABASE={database};UID={uid};PWD={pwd}'
        conn = pyodbc.connect(conn_string)
        logger.debug(f"Conexão pyodbc estabelecida com {database}@{server}")
        return conn
    except pyodbc.OperationalError as e:
        logger.error(f"Erro de conexão pyodbc: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro ao criar conexão pyodbc: {str(e)}")
        raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(psycopg2.OperationalError),
    reraise=True
)
def get_psycopg2_connection():
    """
    Cria e retorna uma conexão psycopg2 para PostgreSQL
    Com retry automático (3 tentativas) e backoff exponencial para erros de conexão
    
    Returns:
        Connection: Conexão psycopg2 configurada
    
    Raises:
        psycopg2.OperationalError: Erro de conexão
        psycopg2.DatabaseError: Erro de banco de dados
    """
    try:
        # Conexão com PostgreSQL usando psycopg2
        psy_conn = psycopg2.connect(
            dbname=database,
            user=uid,
            password=pwd,
            host=server,
            port=port
        )
        logger.debug(f"Conexão psycopg2 estabelecida com {database}@{server}")
        return psy_conn
    except psycopg2.OperationalError as e:
        logger.error(f"Erro de conexão psycopg2: {str(e)}")
        raise
    except psycopg2.DatabaseError as e:
        logger.error(f"Erro de banco de dados psycopg2: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao criar conexão psycopg2: {str(e)}")
        raise


@contextmanager
def database_connection():
    """
    Context manager para gerenciar conexões de banco de dados
    Garante que engine e conexão sejam fechadas adequadamente
    
    Usage:
        with database_connection() as (engine, conn):
            # usar engine e conn
            # fechamento automático ao sair do bloco
    
    Yields:
        tuple: (engine, conn) - SQLAlchemy engine e psycopg2 connection
    """
    engine = None
    conn = None
    try:
        engine = get_sqlalchemy_engine()
        conn = get_psycopg2_connection()
        logger.debug("Conexões de banco estabelecidas (context manager)")
        yield engine, conn
    except psycopg2.OperationalError as e:
        logger.error(f"Erro operacional no banco de dados: {str(e)}")
        raise
    except psycopg2.DatabaseError as e:
        logger.error(f"Erro de banco de dados: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado com conexões de banco: {str(e)}")
        raise
    finally:
        # Garantir fechamento das conexões
        if conn is not None:
            try:
                conn.close()
                logger.debug("Conexão psycopg2 fechada")
            except Exception as e:
                logger.warning(f"Erro ao fechar conexão psycopg2: {str(e)}")
        
        if engine is not None:
            try:
                engine.dispose()
                logger.debug("Engine SQLAlchemy disposed")
            except Exception as e:
                logger.warning(f"Erro ao fazer dispose da engine: {str(e)}")




