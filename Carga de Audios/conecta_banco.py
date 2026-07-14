"""
Conexão ao banco PG17 que armazena as transcrições de gravações telefônicas,
e ao banco PG9 fonte que contém a tabela public.contatos_telefone (via config.ini raiz).
"""

import configparser
import psycopg2
import logging
from datetime import datetime
from pathlib import Path
from config import config

# config.ini compartilhado entre todos os projetos — fica um nível acima desta pasta
_CONFIG_INI = Path(__file__).parent.parent / 'config.ini'

logger = logging.getLogger('carga_audios.banco')


def get_connection():
    """Abre e retorna uma conexão psycopg2 ao PG17 (destino das transcrições)."""
    return psycopg2.connect(
        host=config.DB17_HOST,
        port=config.DB17_PORT,
        dbname=config.DB17_NAME,
        user=config.DB17_USER,
        password=config.DB17_PASS,
    )


def get_connection_source():
    """Abre e retorna uma conexão psycopg2 ao PG9 fonte (contatos_telefone).
    Credenciais lidas do config.ini compartilhado na raiz dos projetos.
    """
    ini = configparser.ConfigParser()
    ini.read(_CONFIG_INI)
    db = ini['database']
    return psycopg2.connect(
        host=db['server'],
        port=db.get('port', '5432'),
        dbname=db['database'],
        user=db['uid'],
        password=db['pwd'],
    )


def buscar_contatos_dia(conn, data_inicio: datetime, data_fim: datetime) -> dict:
    """
    Consulta public.contatos_telefone filtrando pelo período em enterqueue.

    Retorna dict indexado por call_id com as notas NPS:
        {
            '<call_id>': {
                'nps_velocidade':    int | None,
                'nps_solucao':       int | None,
                'nps_relacionamento': int | None,
            },
            ...
        }
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT call_id, perg1, perg2, perg3
              FROM public.contatos_telefone
             WHERE enterqueue >= %s
               AND enterqueue <  %s
               AND call_id IS NOT NULL
            """,
            (data_inicio, data_fim),
        )
        rows = cur.fetchall()

    contatos = {}
    for call_id, perg1, perg2, perg3 in rows:
        contatos[str(call_id)] = {
            'nps_velocidade':     perg1,
            'nps_solucao':        perg2,
            'nps_relacionamento': perg3,
        }

    logger.info(f'{len(contatos)} contato(s) encontrado(s) em contatos_telefone para o período.')
    return contatos


def gravacao_ja_existe(conn, call_id: str) -> bool:
    """
    Verifica se uma gravação com esse call_id já foi processada.
    Usado para garantir idempotência — evita baixar e transcrever duas vezes.
    """
    schema = config.DB17_SCHEMA
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT 1 FROM {schema}.gravacoes_telefone WHERE call_id = %s LIMIT 1",
            (call_id,)
        )
        return cur.fetchone() is not None


def inserir_gravacao(conn, dados: dict):
    """
    Insere uma gravação transcrita na tabela gravacoes_telefone.

    Parâmetros esperados em dados:
        call_id, iniciada_em, encerrada_em, duracao_segundos,
        ramal_agente, agente, arquivo_original,
        transcricao_texto, transcricao_raw (JSON),
        transcricao_idioma, transcricao_modelo,
        nps_velocidade, nps_solucao, nps_relacionamento  (opcionais — None se não houver nota)
    """
    schema = config.DB17_SCHEMA
    sql = f"""
        INSERT INTO {schema}.gravacoes_telefone (
            call_id, iniciada_em, encerrada_em, duracao_segundos,
            ramal_agente, agente, arquivo_original,
            transcricao_texto, transcricao_raw,
            transcricao_idioma, transcricao_modelo,
            nps_velocidade, nps_solucao, nps_relacionamento
        ) VALUES (
            %(call_id)s, %(iniciada_em)s, %(encerrada_em)s, %(duracao_segundos)s,
            %(ramal_agente)s, %(agente)s, %(arquivo_original)s,
            %(transcricao_texto)s, %(transcricao_raw)s,
            %(transcricao_idioma)s, %(transcricao_modelo)s,
            %(nps_velocidade)s, %(nps_solucao)s, %(nps_relacionamento)s
        )
        ON CONFLICT (call_id) DO NOTHING;
    """
    with conn.cursor() as cur:
        cur.execute(sql, dados)
    conn.commit()
    logger.debug(f"Gravação {dados['call_id']} inserida no banco.")