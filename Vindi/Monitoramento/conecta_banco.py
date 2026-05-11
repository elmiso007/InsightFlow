import psycopg2
from sqlalchemy import create_engine
import pyodbc
import pandas as pd
from config import Config

def get_sqlalchemy_engine():
    """
    Cria e retorna uma engine SQLAlchemy para o banco de dados PostgreSQL.

    Returns:
        sqlalchemy.engine.Engine: Objeto de engine do SQLAlchemy.
    """
    # Conexão com PostgreSQL usando SQLAlchemy
    # Ensure Config is validated or handle potential errors at startup
    engine_conn_string = f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_SERVER}/{Config.DB_NAME}"
    engine = create_engine(engine_conn_string)
    return engine

def get_pyodbc_connection():
    """
    Cria e retorna uma conexão pyodbc.

    Returns:
        pyodbc.Connection: Objeto de conexão pyodbc.
    """
    # Conexão com PostgreSQL usando pyodbc
    driver = '{PostgreSQL Unicode(x64)}'
    conn_string = f'DRIVER={driver};SERVER={Config.DB_SERVER};DATABASE={Config.DB_NAME};UID={Config.DB_USER};PWD={Config.DB_PASSWORD}'
    conn = pyodbc.connect(conn_string)
    return conn

def get_psycopg2_connection():
    """
    Cria e retorna uma conexão psycopg2.

    Returns:
        psycopg2.extensions.connection: Objeto de conexão psycopg2.
    """
    # Conexão com PostgreSQL usando psycopg2
    psy_conn = psycopg2.connect(
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        host=Config.DB_SERVER
    )
    return psy_conn



