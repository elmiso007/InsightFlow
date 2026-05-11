import pandas as pd
import json
import slack_sdk as sd
import sys
from get_atendimentos import get_atendimentos 
import time
from datetime import datetime, timedelta
import locale
from sqlalchemy import  text
from conecta_banco import *
import numpy as np
import holidays
from notifica import notifica, notifica_boas_noticias
from PromptGemini import analise_ia
import uuid
import re
from pathlib import Path

sql_path = Path(__file__).parent

#|-------------------------------------------------------------------------------------------------------------------|

#VARIAVEIS DE DATA E HORA PARA QUERY E PARA CALCULO DO PERÍODO

task = 'monitoramento_contatos_kinghost'

# Obter a data e hora atuais
data_hoje = datetime.now().date()
hora_atual = datetime.now()
hora_atual_formatada = hora_atual.strftime("%H:%M:%S")
# Converter para objeto time
hora_formatada_time = datetime.strptime(hora_atual_formatada, "%H:%M:%S").time()

def verificar_horario_operacional(hora_atual):
    """Encerra o script se o horário estiver fora do intervalo 06:00–22:00."""
    hora_inicio_execucao = datetime.strptime("06:00:00", "%H:%M:%S").time()
    hora_fim_execucao = datetime.strptime("22:00:00", "%H:%M:%S").time()

    if not (hora_inicio_execucao <= hora_atual <= hora_fim_execucao):
        print(f"Horário atual {hora_atual} está fora do intervalo permitido (06:00 às 22:00). Encerrando.")
        sys.exit()

verificar_horario_operacional(hora_formatada_time)

# Calcular a hora e os minutos há 10 minutos
hora_10_minutos_atras = hora_atual - timedelta(minutes=10)
hora_10_minutos_atras_formatada = hora_10_minutos_atras.strftime("%H:%M:%S")

# Calcular a hora e os minutos há 30 minutos
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
    print(f"{data_hoje} é um dia útil.")
    data_primaria = datetime.now().date() - timedelta(days=11)
    dia_util = True
else:
    print(f"{data_hoje} não é um dia útil.")
    dia_util = False

#|-------------------------------------------------------------------------------------------------------------------|

#FUNÇÕES 

def count_rows(df, data=None, hora_inicio=None, hora_fim=None):
    # Filtrar por data, se fornecida
    if data:
        df = df[df['data_inicio_interacao'].dt.date == data]

    # Filtrar por hora de início, se fornecida
    if hora_inicio is not None:
        df = df[df['hora'] >= hora_inicio] # Comparação direta com time

    # Filtrar por hora de fim, se fornecida
    if hora_fim is not None:
        df = df[df['hora'] <= hora_fim] # Comparação direta com time

    # Contar o número de registros
    return df.shape[0]

def gerar_chave_unica():
    return str(uuid.uuid4())

#|-------------------------------------------------------------------------------------------------------------------|

#QUERY E CONEXÃO COM O BANCO E CONDIÇÃO SE DIA ÚTIL

if dia_util:

    query = f"""
    SELECT 
        c.id,
        c.protocolo,
        c.agent_name as analista,
        c.data_inicio_interacao,
        DATE_TRUNC('day', c.data_inicio_interacao)::DATE AS dia,
        TO_CHAR(c.data_inicio_interacao, 'HH24:MI:SS')::TIME AS hora,
        c.contact_name AS cliente,
        df.setor,
        m.mensagens,
        d.dia_util, d.feriado, d.dia_semana,d.mes
    FROM kinghost_octadesk.chat c 
    LEFT JOIN kinghost_octadesk.mensagens m ON c.id = m.id 
    LEFT JOIN public.dias d ON DATE_TRUNC('day', c.data_inicio_interacao)::DATE  = d.dia
    LEFT JOIN kinghost.depara_fila df ON c.grupo_nome = df.fila
    WHERE data_inicio_interacao BETWEEN '{data_primaria} {hora_30_minutos_atras_formatada}' AND '{data_hoje} {hora_atual_formatada}'
    AND df.setor = 'Suporte' AND d.dia_util IS {dia_util};
    """

    engine = get_sqlalchemy_engine()
    conn = get_pyodbc_connection()
    connection = engine.connect()
    df = pd.read_sql_query(query, conn)

# Verifica se o DataFrame está vazio antes de continuar
if df.empty:
    print("Nenhum dado retornado da consulta. Interrompendo a execução da pipeline.")
    conn.close()
    connection.close()
    engine.dispose()
    sys.exit()

else:

    tabela = 'rawdata_monitoramento_contatos'
    schema = 'kinghost_octadesk'

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

    print(f'ultimos dias {intervalos}')
    chave = gerar_chave_unica()
    print(chave)

    setor = df['setor'].unique

    #ARMAZENA A MEDIA DOS ATENDIMENTOS DOS ULTIMOS 7 DIAS PARA O MESMO HORÁRIO DA CONSULTA
    media_ultima_semana_float = np.mean(intervalos)
    media_ultima_semana = round(media_ultima_semana_float, 2)
    print(f"A media da ultima semana é {media_ultima_semana}")

    #ARMAZENA O TOTAL DE ATENDIMENTOS DE SUPORTE DOS ULTIMOS 30 MINUTOS.
    atendimentos_atuais = count_rows(df, data_hoje, hora_30_minutos_atras_formatada_time, hora_formatada_time)
    print(f"A quantidade de atendimentos de hoje é: {atendimentos_atuais}")

    percentual = ((atendimentos_atuais - media_ultima_semana) / media_ultima_semana) * 100
    percentual = round(percentual, 2)
    print(f"O percentual em relação a mesma janela de horário é de : {percentual}")

    if percentual > -100 and atendimentos_atuais > 4:
        print("Analisando interações de clientes!")
        data_inicio = f"{data_hoje}  {hora_30_minutos_atras_formatada_time}"
        data_fim = f"{data_hoje} {hora_formatada_time}"
        print(f" Período :{data_inicio} a {data_fim}")   

        conversas, lista_protocolos = get_atendimentos(data_inicio, data_fim)
        content = analise_ia(conversas, data_inicio, data_fim, task, 'Suporte', lista_protocolos)

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
        'notificou': [notificou]
    })

    print('Gravando verificação no banco...')
    df.to_sql(tabela, con=engine, if_exists='replace', index=False, schema=schema)

    # Lê o script SQL do arquivo
    with open(rf'{sql_path}\insereDados.sql','r', encoding='utf-8') as file:
        sql_script = text(file.read())

    #Executando o script SQL
    connection.execute(sql_script)
    connection.commit()

    conn.close()
    connection.close()
    engine.dispose()
