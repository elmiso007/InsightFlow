import psycopg2
from sqlalchemy import create_engine
import pyodbc
import pandas as pd

# Configurações de conexão
server = '10.30.138.28'
database = 'report_requesttracker'
uid = 'automatizacoes'
pwd = '[REDACTED_DB_PASSWORD]'

def get_sqlalchemy_engine():
    # Conexão com PostgreSQL usando SQLAlchemy
    engine_conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
    engine = create_engine(engine_conn_string)
    return engine

def get_pyodbc_connection():
    # Conexão com PostgreSQL usando pyodbc
    driver = '{PostgreSQL Unicode(x64)}'
    conn_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}'
    conn = pyodbc.connect(conn_string)
    return conn

def get_psycopg2_connection():
    # Conexão com PostgreSQL usando psycopg2
    psy_conn = psycopg2.connect(
        dbname=database,
        user=uid,
        password=pwd,
        host=server
    )
    return psy_conn



