"""
Script principal para monitoramento de atendimentos.

Este script realiza a verificação periódica do volume de atendimentos, comparando
com a média histórica e acionando análises de IA e notificações quando necessário.
"""

import pandas as pd
import json
import slack_sdk as sd
import sys
from get_atendimentos import get_atendimentos 
import time
from datetime import datetime, timedelta
import locale
import logging
from config import Config

# Configure basic logging
logging.basicConfig(level=Config.LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
from sqlalchemy import  text
from conecta_banco import *
import numpy as np
import holidays
from notifica import notifica, notifica_boas_noticias
from openai import analise_ia
import uuid
import re
from pathlib import Path

sql_path = Path(__file__).parent

#|-------------------------------------------------------------------------------------------------------------------|

# Validate configuration
try:
    Config.validate()
except ValueError as e:
    logger.error(str(e))
    sys.exit(1)

#VARIAVEIS DE DATA E HORA PARA QUERY E PARA CALCULO DO PERÍODO
task = 'monitoramento_is'

# Obter a data e hora atuais
data_hoje = datetime.now().date()
hora_atual = datetime.now()
hora_atual_formatada = hora_atual.strftime("%H:%M:%S")
# Converter para objeto time
hora_formatada_time = datetime.strptime(hora_atual_formatada, "%H:%M:%S").time()

# def verificar_horario_operacional(hora_atual):
    # """Encerra o script se o horário estiver fora do intervalo 06:00–22:00."""
    # hora_inicio_execucao = datetime.strptime("08:00:00", "%H:%M:%S").time()
    # hora_fim_execucao = datetime.strptime("18:00:00", "%H:%M:%S").time()

    # if not (hora_inicio_execucao <= hora_atual <= hora_fim_execucao):
        # print(f"Horário atual {hora_atual} está fora do intervalo permitido (08:00 às 18:00). Encerrando.")

        # sys.exit()

#verificar_horario_operacional(hora_formatada_time)

# Calcular a hora e os minutos há 10 minutos
hora_10_minutos_atras = hora_atual - timedelta(minutes=10)
hora_10_minutos_atras_formatada = hora_10_minutos_atras.strftime("%H:%M:%S")

# Calcular a hora e os minutos há 10 minutos
hora_30_minutos_atras = hora_atual - timedelta(minutes=30)
hora_30_minutos_atras_formatada = hora_30_minutos_atras.strftime("%H:%M:%S")
# Converter para objeto time
hora_30_minutos_atras_formatada_time = datetime.strptime(hora_30_minutos_atras_formatada, "%H:%M:%S").time()

data_primaria = datetime.now().date() - timedelta(days=30)
current_time = datetime.now()

# Lista de feriados no Brasil (ou outro país)
feriados_brasil = holidays.Brazil()

# Verificar se hoje é um dia útil
if data_hoje.weekday() < 5 and data_hoje not in feriados_brasil:
    logger.info(f"{data_hoje} é um dia útil.")
    data_primaria = datetime.now().date() - timedelta(days=11)
    dia_util = True
else:
    logger.info(f"{data_hoje} não é um dia útil.")
    data_primaria = datetime.now().date() - timedelta(days=30)
    dia_util = False

#|-------------------------------------------------------------------------------------------------------------------|

#FUNÇÕES 

def count_rows(df, data=None, hora_inicio=None, hora_fim=None):
    """
    Conta o número de linhas em um DataFrame com filtros opcionais de data e hora.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados.
        data (datetime.date, optional): Data para filtrar. Defaults to None.
        hora_inicio (datetime.time, optional): Hora inicial para filtrar. Defaults to None.
        hora_fim (datetime.time, optional): Hora final para filtrar. Defaults to None.

    Returns:
        int: Número de linhas que atendem aos critérios.
    """
    # Filtrar por data, se fornecida
    if data:
        df = df[df['data_inicio_interacao'].dt.date == data]

    # Filtrar por hora de início, se fornecida
    if hora_inicio is not None:
        df = df[df['hora'] >= hora_inicio]  # Comparação direta com time

    # Filtrar por hora de fim, se fornecida
    if hora_fim is not None:
        df = df[df['hora'] <= hora_fim]  # Comparação direta com time

    # Contar o número de registros
    count = df.shape[0]
    return count

def gerar_chave_unica():
    """
    Gera uma chave única UUID.

    Returns:
        str: String contendo o UUID gerado.
    """
    return str(uuid.uuid4())

#|-------------------------------------------------------------------------------------------------------------------|

#QUERY E CONEXÃO COM O BANCO E CONDIÇÃO PARA VERIFICAÇÃO APENAS EM DIA ÚTIL

if dia_util:

    query = f"""
    SELECT 
        c.protocolo,
        c.id as chave,
        c.data_inicio_interacao,
        DATE_TRUNC('day', c.data_inicio_interacao)::DATE AS dia,
        TO_CHAR(c.data_inicio_interacao, 'HH24:MI:SS')::TIME AS hora,
        c.contact_name as cliente, 
        c.agent_name as analista, 
        a.grupo as fila, 
        a.produto,
        a.equipe,
        a.setor, d.dia_util, d.feriado, d.dia_semana,d.mes
    FROM vindi.chat c
    LEFT JOIN vindi.depara_grupo a ON c.grupo_nome = a.grupo 
    LEFT JOIN public.dias d ON DATE_TRUNC('day', c.data_inicio_interacao)::DATE  = d.dia 
    WHERE data_inicio_interacao BETWEEN '{data_primaria} {hora_30_minutos_atras_formatada}' AND '{data_hoje} {hora_atual_formatada}'       
      AND a.setor = 'Suporte' AND d.dia_util IS {dia_util};
    """

    engine = get_sqlalchemy_engine()
    conn = get_pyodbc_connection()
    connection = engine.connect()

    df = pd.read_sql_query(query, conn)

# Verifica se o DataFrame está vazio antes de continuar
if df.empty:
    logger.warning("Nenhum dado retornado da consulta. Interrompendo a execução da pipeline.")
    conn.close()
    connection.close()
    engine.dispose()
    sys.exit()

else:    

    tabela = 'rawdata_monitoramento'
    schema = 'vindi'

    # Filtrar os últimos 7 dias únicos existentes
    dias_unicos = df['dia'].drop_duplicates().sort_values(ascending=False)
    # Ignorar o dia atual e selecionar os 7 dias únicos anteriores
    dias_7_anteriores = dias_unicos[dias_unicos < data_hoje].head(7)

    # Filtrar o DataFrame para incluir apenas os dias selecionados
    df_filtrado = df[df['dia'].isin(dias_7_anteriores)]

    #|-------------------------------------------------------------------------------------------------------------------|

    #MANIPULAÇÃO DOS DADOS

    df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S').dt.time
    intervalos = []

    # Extrair valores únicos de data (ignorando as horas)
    dias = df_filtrado['dia'].unique()

    #função para localizar a quantidade de atendimentos dos últimos 7 dias para o período analisado
    for dia in dias:
        atendimentos = count_rows(df, dia, hora_30_minutos_atras_formatada_time, hora_formatada_time)
        intervalos.append(atendimentos)

    logger.debug(f'ultimos dias {intervalos}')
    chave = gerar_chave_unica()
    logger.debug(f"Chave gerada: {chave}")

    setor = df['setor'].unique

    #ARMAZENA A MEDIA DOS ATENDIMENTOS DOS ULTIMOS 7 DIAS PARA O MESMO HORÁRIO DA CONSULTA
    media_ultima_semana_float = np.mean(intervalos)
    media_ultima_semana = round(media_ultima_semana_float, 2)
    logger.info(f"A media da ultima semana é {media_ultima_semana}")

    #ARMAZENA O TOTAL DE ATENDIMENTOS DE SUPORTE DOS ULTIMOS 30 MINUTOS.
    atendimentos_atuais = count_rows(df, data_hoje, hora_30_minutos_atras_formatada_time, hora_formatada_time)
    logger.info(f"A quantidade de atendimentos de hoje é: {atendimentos_atuais}")

    percentual = ((atendimentos_atuais - media_ultima_semana) / media_ultima_semana) * 100
    percentual = round(percentual, 2)
    logger.info(f"O percentual em relação a mesma janela de horário é de : {percentual}")

    if percentual > 15 and atendimentos_atuais > 3:
        logger.info("Analisando interações de clientes!")
        data_inicio = f"{data_hoje}  {hora_30_minutos_atras_formatada_time}"
        data_fim = f"{data_hoje} {hora_formatada_time}"
        logger.info(f" Período :{data_inicio} a {data_fim}")   

        conversas = get_atendimentos(data_inicio, data_fim)
        content = analise_ia(conversas, data_inicio, data_fim, task, 'Suporte', chave, task)

        # Aplicando a substituição com regex
        content = re.sub(r'\*\*', '*', content)

        notificou = True 
        notifica(content, percentual, media_ultima_semana)
        
    else:
        notificou = False

    df = pd.DataFrame({
        'data': [current_time],
        'data_inicio': [data_primaria],
        'hora_inicio': [hora_10_minutos_atras_formatada],
        'data_fim': [data_hoje],
        'hora_fim': [hora_atual_formatada],
        'dia_util': [dia_util],
        'media_comparativa': [media_ultima_semana],
        'atendimentos': [atendimentos_atuais],
        'percentual': [percentual],
        'notificou': [notificou],
        'chave_analise': [chave],
        'created_at': [current_time],
        'updated_at': [current_time]
    })

    logger.info('Gravando verificação no banco...')
    df.to_sql(tabela, con=engine, if_exists='replace', index=False, schema=schema)

    # Lê o script SQL do arquivo
    with open(rf'{sql_path}\insereDados.sql','r', encoding='utf-8') as file:
        sql_script = text(file.read())

    # Executando o script SQL
    connection.execute(sql_script)
    connection.commit()

    conn.close()
    connection.close()
    engine.dispose()
