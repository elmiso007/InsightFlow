#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Report Diário Locaweb
=====================
Aplicação para gerar e enviar relatórios diários de atendimento via Slack.

Autor: Emerson Ramos
Data: 2024-2025
"""

# ==============================================
# IMPORTS
# ==============================================
from slack_sdk import WebClient
from sqlalchemy import create_engine
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import locale
import matplotlib.pyplot as plt
import time
import os
import ssl
import certifi
import holidays
import logging
from dotenv import load_dotenv

# ==============================================
# CONFIGURAÇÕES INICIAIS
# ==============================================

# Carregar variáveis de ambiente
load_dotenv()

# Configurar SSL com certificados válidos
os.environ['SSL_CERT_FILE'] = certifi.where()
ssl_context = ssl.create_default_context()

# ==============================================
# CONFIGURAÇÃO DE LOGGING
# ==============================================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'report_diario.log')

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==============================================
# CONSTANTES
# ==============================================
HORARIO_10H = datetime.strptime("10:00:00", "%H:%M:%S").time()
HORARIO_12H = datetime.strptime("12:00:00", "%H:%M:%S").time()
HORARIO_14H = datetime.strptime("14:00:00", "%H:%M:%S").time()
HORARIO_18H = datetime.strptime("18:00:00", "%H:%M:%S").time()
HORARIO_19H = datetime.strptime("19:00:00", "%H:%M:%S").time()

# Cores para a tabela
COR_VERDE = '#2EA407'
COR_VERMELHO = '#E46B6B'
COR_LARANJA = '#F3A07D'
COR_VERDE_CLARO = '#9AC09A'
COR_AZUL_CLARO = 'lightblue'

# Canais
CANAL_WHATSAPP = 'WhatsApp'
CANAL_CHAT = 'Chat'
CANAL_TELEFONE = 'Telefone'

# ==============================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ==============================================
logger.info("Iniciando configuração do banco de dados...")

try:
    # Obter credenciais do banco de dados das variáveis de ambiente
    DB_SERVER = os.getenv('DB_SERVER')
    DB_DATABASE = os.getenv('DB_DATABASE')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    # Validar se as credenciais estão configuradas
    if not all([DB_SERVER, DB_DATABASE, DB_USER, DB_PASSWORD]):
        logger.error("Credenciais do banco de dados não configuradas no arquivo .env")
        raise ValueError("Configure as variáveis DB_SERVER, DB_DATABASE, DB_USER e DB_PASSWORD no arquivo .env")
    
    # Criar string de conexão
    conn_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/{DB_DATABASE}"
    engine = create_engine(conn_string)
    connection = engine.raw_connection()
    
    logger.info("Conexão com banco de dados estabelecida com sucesso")
except Exception as e:
    logger.error(f"Erro ao conectar ao banco de dados: {e}")
    raise

# ==============================================
# CONFIGURAÇÕES DE DATA E FERIADOS
# ==============================================
data_hoje = datetime.now().date()
feriados_brasil = holidays.Brazil()

# Verificar se hoje é um dia útil
dia_util = data_hoje.weekday() < 5 and data_hoje not in feriados_brasil

if dia_util:
    logger.info(f"{data_hoje} é um dia útil.")
    setores = ['Suporte', 'Cobrança']
else:
    logger.info(f"{data_hoje} não é um dia útil (final de semana ou feriado).")
    setores = ['Suporte']


# ==============================================
# CONFIGURAÇÕES DE LOCALE E FORMATAÇÃO
# ==============================================
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    logger.info("Locale configurado para pt_BR.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
        logger.warning("Usando locale Portuguese_Brazil.1252 (Windows)")
    except locale.Error:
        logger.warning("Não foi possível configurar locale em português, usando padrão do sistema")

# Armazenar a hora atual
hora_atual = datetime.now().time().replace(microsecond=0)

# Obter a data de hoje
data_de_hoje = datetime.now().date()
data_formatada = data_de_hoje.strftime('%d/%m')
data_7_dias = data_de_hoje - timedelta(days=7)
data_7_dias_atras = data_7_dias.strftime('%d/%m')

# Obter o nome do dia da semana em português
nome_dia_semana = data_de_hoje.strftime('%A')

# Corrigir problema de encoding específico
if nome_dia_semana == 'terÃ§a-feira':
    nome_dia_semana = 'Terça-Feira'

logger.info(f"Data atual: {data_formatada} ({nome_dia_semana})")

# ==============================================
# FUNÇÕES AUXILIARES
# ==============================================

def contar_linhas(df, setor=None, ignora_bot=None, atendidas=None, abandono=None, ultima_semana=None, data=None):
    """
    Conta o número de linhas do DataFrame com base nos filtros aplicados.
    
    Args:
        df (pd.DataFrame): DataFrame com os dados
        setor (str, optional): Filtrar por setor específico
        ignora_bot (bool, optional): Ignorar atendimentos de bot
        atendidas (bool, optional): Apenas conversas atendidas
        abandono (bool, optional): Apenas abandonos
        ultima_semana (bool, optional): Apenas última semana
        data (bool, optional): Apenas data de hoje
    
    Returns:
        int: Quantidade de registros que atendem aos filtros
    """
    df_filtrado = df.copy()
    
    if setor:
        df_filtrado = df_filtrado[df_filtrado['Setor'] == setor]
    if ignora_bot:
        df_filtrado = df_filtrado[df_filtrado['robo'] != 1]
    if atendidas:
        df_filtrado = df_filtrado[(df_filtrado['abandono'] != 'Abandonado') & (df_filtrado['Setor'] == setor)]
    if abandono:
        df_filtrado = df_filtrado[(df_filtrado['abandono'] == 'Abandonado') & (df_filtrado['Setor'] == setor)]
    if ultima_semana:
        df_filtrado = df_filtrado[df_filtrado['Ultima Semana'] == 1]
    if data:
        df_filtrado = df_filtrado[df_filtrado['dia'] == data_de_hoje]
    
    return len(df_filtrado)

def calcular_tempo(df, coluna_tempo, setor=None, ignora_bot=None, data=None):
    """
    Calcula o tempo médio de atendimento ou espera.
    
    Args:
        df (pd.DataFrame): DataFrame com os dados
        coluna_tempo (str): Nome da coluna de tempo a ser calculada
        setor (str, optional): Filtrar por setor
        ignora_bot (bool, optional): Ignorar atendimentos de bot
        data (bool, optional): Filtrar pela data de hoje
    
    Returns:
        str: Tempo médio no formato HH:MM:SS
    """
    df_filtrado = df.copy()
    
    if setor:
        df_filtrado = df_filtrado[df_filtrado['Setor'] == setor]
    if ignora_bot:
        df_filtrado = df_filtrado[(df_filtrado['robo'] != 1) & (df_filtrado['Tempo de Atendimento'] > 0)]
    if data:
        df_filtrado = df_filtrado[df_filtrado['dia'] == data_de_hoje]
    
    total_tempo = df_filtrado[coluna_tempo].sum()
    total_registros = len(df_filtrado)
    
    if total_registros > 0:
        tempo_medio_segundos = total_tempo / total_registros
        horas = int(tempo_medio_segundos // 3600)
        minutos = int((tempo_medio_segundos % 3600) // 60)
        segundos = int(tempo_medio_segundos % 60)
        return f"{horas:02}:{minutos:02}:{segundos:02}"
    else:
        return "00:00:00"
    
def obter_hoje():
    """
    Retorna o início e fim do dia atual.
    
    Returns:
        tuple: (datetime início do dia, datetime fim do dia)
    """
    hoje_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    hoje_fim = hoje_inicio + timedelta(hours=23, minutes=59, seconds=59)
    return hoje_inicio, hoje_fim

def soma_points(df, canal=None, setor=None, ultima_semana=None, data=None):
    """
    Soma os pontos (atendimentos) com base na hora atual e filtros aplicados.
    
    Args:
        df (pd.DataFrame): DataFrame com os dados
        canal (str, optional): Filtrar por canal específico
        setor (str, optional): Filtrar por setor
        ultima_semana (bool, optional): Filtrar pela última semana
        data (bool, optional): Filtrar pela data de hoje
    
    Returns:
        tuple: (soma_10h, soma_14h, soma_18h) - valores progressivos durante o dia
    """
    df_filtrado = df.copy()
    hora_atual = datetime.now().time().replace(microsecond=0)
    
    # Converter a coluna 'Data Inicio' para datetime
    df_filtrado['Data Inicio'] = pd.to_datetime(df_filtrado['Data Inicio'])
    
    # Aplicar filtros
    if canal:
        df_filtrado = df_filtrado[df_filtrado['Canal'] == canal]
    if setor:
        df_filtrado = df_filtrado[df_filtrado['Setor'] == setor]
    if ultima_semana:
        df_filtrado = df_filtrado[df_filtrado['Ultima Semana'] == 1]
    if data:
        df_filtrado = df_filtrado[df_filtrado['dia'] == data_de_hoje]
    
    # Inicializar somas
    soma_first = int(df_filtrado['first_point'].sum())
    soma_second = '-'
    soma_third = '-'
    
    # Somas progressivas baseadas no horário
    if hora_atual >= HORARIO_14H:
        soma_second = int(df_filtrado['second_point'].sum())
    
    if hora_atual >= HORARIO_18H:
        soma_third = int(df_filtrado['third_point'].sum())
    
    return soma_first, soma_second, soma_third

def padrao(df, canal=None, setor=None, ultima_semana=None, data=None, diautil=None):
    """
    Calcula as médias do período padrão (usado para comparação).
    
    Args:
        df (pd.DataFrame): DataFrame com os dados
        canal (str, optional): Filtrar por canal
        setor (str, optional): Filtrar por setor
        ultima_semana (bool, optional): Filtrar pela última semana
        data (bool, optional): Filtrar pelo período padrão
        diautil (bool, optional): Considerar apenas dias úteis
    
    Returns:
        tuple: (media_10h, media_14h, media_18h) - médias do período padrão
    """
    df_filtrado = df.copy()
    hora_atual = datetime.now().time().replace(microsecond=0)
    
    # Converter a coluna 'Data Inicio' para datetime
    df_filtrado['Data Inicio'] = pd.to_datetime(df_filtrado['Data Inicio'])
    
    # Aplicar filtros
    if canal:
        df_filtrado = df_filtrado[df_filtrado['Canal'] == canal]
    if setor:
        df_filtrado = df_filtrado[df_filtrado['Setor'] == setor]
    if ultima_semana:
        df_filtrado = df_filtrado[df_filtrado['Ultima Semana'] == 1]
    if data:
        df_filtrado = df_filtrado[(df_filtrado['Data Inicio'] >= padrao_inicio) & (df_filtrado['Data Inicio'] <= padrao_fim)]
    if diautil:
        df_filtrado = df_filtrado[df_filtrado['diautil'] == 1]
    
    # CÁLCULO DINÂMICO: Contar o número de dias úteis no período
    total_dias_uteis = df_filtrado[df_filtrado['diautil'] == 1]['dia'].nunique()
    
    # Fallback caso não haja dias úteis identificados
    if total_dias_uteis == 0:
        logger.warning("Nenhum dia útil encontrado no período padrão, usando valor padrão de 103 dias")
        total_dias_uteis = 103
    else:
        logger.info(f"Total de dias úteis no período padrão: {total_dias_uteis}")
    
    # Calcular médias
    total_first_padrao = df_filtrado['first_point'].sum()
    soma_first_padrao = round(total_first_padrao / total_dias_uteis)
    soma_second_padrao = '-'
    soma_third_padrao = '-'
    
    logger.debug(f'Padrão 10hs: {soma_first_padrao}')
    
    # Calcular médias progressivas baseadas no horário
    if hora_atual >= HORARIO_14H:
        total_second_padrao = df_filtrado['second_point'].sum()
        soma_second_padrao = round(total_second_padrao / total_dias_uteis)
        logger.debug(f'Padrão 14hs: {soma_second_padrao}')
    
    if hora_atual >= HORARIO_18H:
        total_third_padrao = df_filtrado['third_point'].sum()
        soma_third_padrao = round(total_third_padrao / total_dias_uteis)
        logger.debug(f'Padrão 18hs: {soma_third_padrao}')
    
    return soma_first_padrao, soma_second_padrao, soma_third_padrao

def percentual_padrao(valor1, valor2):
    """
    Calcula o percentual de variação entre dois valores.
    
    Args:
        valor1: Valor atual
        valor2: Valor de referência
    
    Returns:
        float: Percentual de variação (0 se valor2 for zero ou inválido)
    """
    # Normalizar valores '-' para zero
    if valor1 == '-':
        valor1 = 0
    if valor2 == '-':
        valor2 = 0
    
    # Evitar divisão por zero
    if valor2 is None or valor2 == 0:
        return 0
    
    return (valor1 - valor2) / valor2

def ajustar_celula(celula, valor):
    """
    Define a cor da célula e do texto baseado no valor percentual.
    Verde = negativo (abaixo do padrão = BOM)
    Vermelho = positivo (acima do padrão = RUIM)
    
    Args:
        celula: Célula da tabela matplotlib
        valor (float): Valor percentual
    """
    if valor < 0:
        celula.set_facecolor(COR_VERDE)
        celula.set_text_props(text=f"{round(valor, 2)}%", color='white')
    elif valor > 0:
        celula.set_facecolor(COR_VERMELHO)
        celula.set_text_props(text=f"{round(valor, 2)}%", color='white')
    else:
        celula.set_facecolor('white')
        celula.set_text_props(text="-", color='black')


# ==============================================
# PERÍODO PADRÃO PARA COMPARAÇÃO
# ==============================================
PADRAO_INICIO_STR = os.getenv('PADRAO_DATA_INICIO', '2025-08-01')
PADRAO_FIM_STR = os.getenv('PADRAO_DATA_FIM', '2025-10-31')

try:
    padrao_inicio = pd.to_datetime(f'{PADRAO_INICIO_STR} 00:00:00')
    padrao_fim = pd.to_datetime(f'{PADRAO_FIM_STR} 23:59:59')
    logger.info(f"Período padrão configurado: {PADRAO_INICIO_STR} até {PADRAO_FIM_STR}")
except Exception as e:
    logger.error(f"Erro ao configurar período padrão: {e}")
    raise

hoje_inicio, hoje_fim = obter_hoje()

# ==============================================
# CONSULTA AO BANCO DE DADOS
# ==============================================
logger.info("Consultando dados do banco...")

try:
    query = '''SELECT * FROM lw_octadesk.vw_report_diario_filtrada;'''
    df = pd.read_sql_query(query, connection)
    logger.info(f"Dados carregados com sucesso: {len(df)} registros")
except Exception as e:
    logger.error(f"Erro ao consultar banco de dados: {e}")
    raise


# ==============================================
# CONFIGURAÇÃO DE SAUDAÇÃO
# ==============================================
def obter_saudacao():
    """Retorna saudação baseada no horário atual."""
    hora = datetime.now().time()
    if hora <= HORARIO_12H:
        return "Bom dia!"
    elif hora <= HORARIO_19H:
        return "Boa tarde!"
    else:
        return "Boa noite!"

saudacao = obter_saudacao()

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


mensagem = {
    "blocks": [
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Report Diário Locaweb:*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f" {saudacao} Estamos disponibilizando abaixo os dados do relatório *Report Diário* da Locaweb."
            }
        }
    ]    
}

mensagem2 = ""

# Botões da mensagem final - URL do Power BI e e-mail de suporte vêm do .env
POWERBI_REPORT_URL = os.getenv('POWERBI_REPORT_URL', '').strip()
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', '').strip()

acoes_elementos = []
if POWERBI_REPORT_URL:
    acoes_elementos.append({
        "type": "button",
        "text": {"type": "plain_text", "text": ":bar_chart:  Relatório Completo", "emoji": True},
        "url": POWERBI_REPORT_URL
    })
acoes_elementos.append({
    "type": "button",
    "text": {"type": "plain_text", "text": ":sos:  Ajuda", "emoji": True}
})
acoes_elementos.append({
    "type": "button",
    "text": {"type": "plain_text", "text": ":loudspeaker:  Feedback", "emoji": True}
})

if SUPPORT_EMAIL:
    texto_suporte = (
        f"Se ficar com dúvidas sobre as informações, chame um analista no Slack "
        f"ou envie um email para: {SUPPORT_EMAIL}"
    )
else:
    texto_suporte = "Se ficar com dúvidas sobre as informações, chame um analista no Slack."

mensagem3 = {
    "blocks": [
        {"type": "divider"},
        {"type": "actions", "elements": acoes_elementos},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": texto_suporte}
        }
    ]
}




# ==============================================
# CONFIGURAÇÃO DO SLACK
# ==============================================
SLACK_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.getenv('SLACK_CHANNEL_ID')
SLACK_CHANNEL_TESTE = os.getenv('SLACK_CHANNEL_ID_TESTE')

if not SLACK_TOKEN:
    logger.error("Token do Slack não configurado no arquivo .env")
    raise ValueError("Configure a variável SLACK_BOT_TOKEN no arquivo .env")

if not SLACK_CHANNEL or not SLACK_CHANNEL_TESTE:
    logger.error("IDs de canal do Slack não configurados no arquivo .env")
    raise ValueError("Configure as variáveis SLACK_CHANNEL_ID e SLACK_CHANNEL_ID_TESTE no arquivo .env")

# ==============================================
# 🎯 AMBIENTE: definido pela variável APP_ENV no .env
# ==============================================
# APP_ENV=test         → canal de teste (default seguro)
# APP_ENV=production   → canal oficial
# APP_ENV=both         → envia para teste e produção simultaneamente
# ==============================================
APP_ENV = os.getenv('APP_ENV', 'test').strip().lower()

if APP_ENV == 'production':
    destinatarios = [SLACK_CHANNEL]
    logger.info(f"✅ MODO PRODUÇÃO ATIVO - Canal oficial ({SLACK_CHANNEL})")
elif APP_ENV == 'both':
    destinatarios = [SLACK_CHANNEL_TESTE, SLACK_CHANNEL]
    logger.warning(f"🔀 MODO DUAL ATIVO - Enviando para {len(destinatarios)} canais: {destinatarios}")
else:
    destinatarios = [SLACK_CHANNEL_TESTE]
    logger.warning(f"⚠️  MODO TESTE ATIVO - Canal de teste ({SLACK_CHANNEL_TESTE})")

# Criação do cliente Slack
try:
    client = WebClient(SLACK_TOKEN)
    logger.info("Cliente Slack inicializado com sucesso")
except Exception as e:
    logger.error(f"Erro ao inicializar cliente Slack: {e}")
    raise



# ==============================================
# ENVIO DA MENSAGEM INICIAL
# ==============================================
logger.info("Iniciando envio de mensagens via Slack...")

for destinatario in destinatarios:
    try:
        # Verificar se o destinatário começa com 'U' (usuário direto)
        if destinatario.startswith('U'):
            response_dm = client.conversations_open(users=destinatario)
            channel_id = response_dm["channel"]["id"]
            response_message = client.chat_postMessage(
                channel=channel_id, 
                blocks=mensagem["blocks"], 
                text=f"Report Diário {data_formatada}"
            )
            logger.info(f"Mensagem inicial enviada para usuário {destinatario}")
        
        # Verificar se o destinatário começa com 'C' (canal)
        elif destinatario.startswith('C'):
            response_message = client.chat_postMessage(
                channel=destinatario, 
                blocks=mensagem["blocks"], 
                text=f"Report Diário {data_formatada}"
            )
            logger.info(f"Mensagem inicial enviada para canal {destinatario}")
        
        else:
            logger.warning(f"Destinatário não reconhecido: {destinatario}")
    
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem inicial para {destinatario}: {e}")



# ==============================================
# PROCESSAMENTO POR SETOR
# ==============================================
logger.info(f"Processando relatórios para setores: {setores}")

for setor in setores:
    logger.info(f"Processando setor: {setor}")
    
    # Soma padrão calculada dinamicamente baseada nas datas padrao_inicio e padrao_fim
    soma_first_padrao, soma_second_padrao, soma_third_padrao = padrao(df, setor=setor, data=True, diautil=True)

    # Soma semana anterior
    soma_first_semana_anterior_wp, soma_second_semana_anterior_wp, soma_third_semana_anterior_wp = soma_points(
        df, canal=CANAL_WHATSAPP, setor=setor, ultima_semana=True
    )
    soma_first_semana_anterior_chat, soma_second_semana_anterior_chat, soma_third_semana_anterior_chat = soma_points(
        df, canal=CANAL_CHAT, setor=setor, ultima_semana=True
    )
    soma_first_semana_anterior_fone, soma_second_semana_anterior_fone, soma_third_semana_anterior_fone = soma_points(
        df, canal=CANAL_TELEFONE, setor=setor, ultima_semana=True
    )
    soma_first_semana_anterior, soma_second_semana_anterior, soma_third_semana_anterior = soma_points(
        df, canal=None, setor=setor, ultima_semana=True
    )
    
    # Soma dia atual
    soma_first_wp, soma_second_wp, soma_third_wp = soma_points(
        df, canal=CANAL_WHATSAPP, setor=setor, ultima_semana=0, data=True
    )
    soma_first_chat, soma_second_chat, soma_third_chat = soma_points(
        df, canal=CANAL_CHAT, setor=setor, ultima_semana=0, data=True
    )
    soma_first_fone, soma_second_fone, soma_third_fone = soma_points(
        df, canal=CANAL_TELEFONE, setor=setor, ultima_semana=0, data=True
    )
    soma_first, soma_second, soma_third = soma_points(
        df, canal=None, setor=setor, ultima_semana=0, data=True
    )

    # Define as colunas de tempo
    coluna_tempo_atendimento = 'Tempo de Atendimento'
    coluna_tempo_espera = 'Tempo de Espera'

    percentual_padrao1 = percentual_padrao(soma_first,soma_first_padrao) * 100
    percentual_padrao2 = percentual_padrao(soma_second,soma_second_padrao) * 100
    percentual_padrao3 = percentual_padrao(soma_third,soma_third_padrao) * 100

    percentual_semana_anterior1 = percentual_padrao(soma_first,soma_first_semana_anterior) * 100
    percentual_semana_anterior2 = percentual_padrao(soma_second,soma_second_semana_anterior) * 100
    percentual_semana_anterior3 = percentual_padrao(soma_third,soma_third_semana_anterior) * 100


    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    #ARMAZENA DADOS DO DIA

    # Calcula o tempo médio de atendimento (sem ignorar robôs)
    tma = calcular_tempo(df, coluna_tempo_atendimento, setor=setor, ignora_bot=True, data=data_de_hoje)
    
    # Calcula o tempo médio de espera
    tme = calcular_tempo(df, coluna_tempo_espera, setor=setor, data=data_de_hoje)
    
    # Quantidade de recebidos (exclui bots para alinhar com Atendidos/Abandonos)
    recebidos = contar_linhas(df, setor=setor, ignora_bot=True, data=True)
    
    # Quantidade de Atendidos
    atendidos = contar_linhas(df, setor=setor, ignora_bot=True, atendidas=True, data=True)
    
    # Quantidade de abandonos
    abandonos = contar_linhas(df, setor=setor, ignora_bot=True, abandono=True, data=True)
    
    # Percentual de abandonos em relação aos recebidos
    if recebidos != 0:
        calculo_percentual_de_abandonos = (abandonos / recebidos) * 100
    else:
        calculo_percentual_de_abandonos = 0
    
    percentual_de_abandonos = round(calculo_percentual_de_abandonos, 2)
    
    logger.info(f"{setor} - TMA: {tma}, TME: {tme}, Recebidos: {recebidos}, "
                f"Atendidos: {atendidos}, Abandonos: {abandonos} ({percentual_de_abandonos}%)") 
   
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Mensagem estilizada com o tempo médio de atendimento usando blocos
    mensagem2 = {
        "blocks": [
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Indicadores de {setor} | {data_formatada} :*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"> :stopwatch: *TMA:* {tma}   *|*   :pocoyo-esperando-sentado: *TME:* {tme}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"> :arrow_down: *Recebidos:* {recebidos}  *|*  :white_check_mark: *Atendidos:* {atendidos}   *|*  :x: *Abandonos:* {abandonos}   *|*  :chart_with_upwards_trend: *% de Aband.* {percentual_de_abandonos}"
                }
            }
        ]
    }

    # A correção de encoding já foi feita no início do script
    data_completa = f" {nome_dia_semana} | {data_formatada}"
    data_completa_semana_anterior = f"{nome_dia_semana}|{data_7_dias_atras}"

    
    tabela = {
        "": ["Padrão Média dia Útil Ago/Out 2025",
            f"WhatsApp D-7 {data_completa_semana_anterior}",
            f"Chat D-7 {data_completa_semana_anterior}",
            f"Telefone D-7 {data_completa_semana_anterior}",
            f"Consolidado D-7 {data_completa_semana_anterior}",
            f"WhatsApp {data_completa}",
            f"Chat {data_completa}",
            f"Telefone {data_completa}",
            f"Consolidado {data_completa}",
            "% Comparado ao Padrão",
            "% Comparado a Semana Anterior"],
        "00:00 as 10:00": 
            [soma_first_padrao,
            soma_first_semana_anterior_wp, 
            soma_first_semana_anterior_chat,
            soma_first_semana_anterior_fone,
            soma_first_semana_anterior, 
            soma_first_wp, 
            soma_first_chat,
            soma_first_fone, 
            soma_first,
            0,
            0],
        "00:00 as 14:00": 
            [soma_second_padrao,
            soma_second_semana_anterior_wp, 
            soma_second_semana_anterior_chat,
            soma_second_semana_anterior_fone,
            soma_second_semana_anterior,
            soma_second_wp, 
            soma_second_chat, 
            soma_second_fone,
            soma_second,
            0,
            0],
        "00:00 as 18:00": 
            [soma_third_padrao,
            soma_third_semana_anterior_wp,
            soma_third_semana_anterior_chat,
            soma_third_semana_anterior_fone,
            soma_third_semana_anterior, 
            soma_third_wp, 
            soma_third_chat, 
            soma_third_fone,
            soma_third,
            0,
            0]
    }
    

    df_plot = pd.DataFrame(tabela)

    # Configurar a figura para um tamanho maior, se necessário
    plt.figure(figsize=(10, 5))  # Aumente os valores conforme necessário

    # Ocultando os eixos
    plt.axis('tight')
    plt.axis('off')
    hora_atual = datetime.now().time().replace(microsecond=0,second=0)

    # Definir as larguras das colunas; ajustar as primeiras três colunas para serem mais estreitas
    col_widths = [0.3, 0.1, 0.1, 0.1]

    # Criando a tabela
    table = plt.table(cellText=df_plot.values, colLabels=df_plot.columns, cellLoc='center', loc='center', colWidths=col_widths)


    # Ajustando a aparência da tabela
    table.auto_set_font_size(False)
    table.set_fontsize(10)  # Reduzindo o tamanho da fonte
    table.scale(1.7, 1.7)  # Ajustando a escala da tabela



    table[0, 0].set_text_props(text=f"{setor}")
    table[0, 0].set_facecolor('lightblue')
    table[0, 1].set_facecolor('lightblue')
    table[0, 2].set_facecolor('lightblue')
    table[0, 3].set_facecolor('lightblue')

    #Dados de padrão
    table[1, 0].set_facecolor('White')
    table[1, 1].set_facecolor('White')
    table[1, 2].set_facecolor('White')
    table[1, 3].set_facecolor('White')

    #Dados de Whatsapp D-7
    table[2, 0].set_facecolor('#F3A07D')
    table[2, 1].set_facecolor('#F3A07D')
    table[2, 2].set_facecolor('#F3A07D')
    table[2, 3].set_facecolor('#F3A07D')

    #Dados de Chat de D-7
    table[3, 0].set_facecolor('#F3A07D')
    table[3, 1].set_facecolor('#F3A07D')
    table[3, 2].set_facecolor('#F3A07D')
    table[3, 3].set_facecolor('#F3A07D')

    #Dados de Tel de D-7
    table[4, 0].set_facecolor('#F3A07D')
    table[4, 1].set_facecolor('#F3A07D')
    table[4, 2].set_facecolor('#F3A07D')
    table[4, 3].set_facecolor('#F3A07D')

    #Dados Consolidado D-7
    table[5, 0].set_facecolor('#F3A07D')
    table[5, 1].set_facecolor('#F3A07D')
    table[5, 2].set_facecolor('#F3A07D')
    table[5, 3].set_facecolor('#F3A07D')

    #Dados de Whatsapp de hoje
    table[6, 0].set_facecolor('#9AC09A')
    table[6, 1].set_facecolor('#9AC09A')
    table[6, 2].set_facecolor('#9AC09A')
    table[6, 3].set_facecolor('#9AC09A')

    #Dados de Chat de hoje
    table[7, 0].set_facecolor('#9AC09A')
    table[7, 1].set_facecolor('#9AC09A')
    table[7, 2].set_facecolor('#9AC09A')
    table[7, 3].set_facecolor('#9AC09A')

    #Dados de Tel de hoje
    table[8, 0].set_facecolor('#9AC09A')
    table[8, 1].set_facecolor('#9AC09A')
    table[8, 2].set_facecolor('#9AC09A')
    table[8, 3].set_facecolor('#9AC09A')

    #Dados Consolidado de hoje
    table[9, 0].set_facecolor('#9AC09A')
    table[9, 1].set_facecolor('#9AC09A')
    table[9, 2].set_facecolor('#9AC09A')
    table[9, 3].set_facecolor('#9AC09A')

    #Dados Comparado ao padrão
    table[10, 0].set_facecolor('white')
    ajustar_celula(table[10, 1], percentual_padrao1)
    ajustar_celula(table[10, 2], percentual_padrao2)
    ajustar_celula(table[10, 3], percentual_padrao3)

    #Dados Comparado a semana anterior
    table[11, 0].set_facecolor('white')
    ajustar_celula(table[11, 1], percentual_semana_anterior1)
    ajustar_celula(table[11, 2], percentual_semana_anterior2)
    ajustar_celula(table[11, 3], percentual_semana_anterior3)


    # Adicionando um título
    plt.title(f"Report Diário {setor} Locaweb {data_formatada} | {hora_atual}", fontsize=14)

    # Salvando a tabela como imagem PNG
    imagem_path = "report_diario_Locaweb.png"
    
    try:
        plt.savefig(imagem_path, format='png', bbox_inches='tight', dpi=300)
        plt.subplots_adjust(left=0.1, right=0.9, top=0.95, bottom=0.1)
        plt.close()  # Fechar o plot para liberar memória
        logger.info(f"Imagem do relatório salva: {imagem_path}")
    except Exception as e:
        logger.error(f"Erro ao salvar imagem do relatório: {e}")
        raise
    
    # Obter saudação de despedida
    hora_atual_fim = datetime.now().time()
    
    if hora_atual_fim <= HORARIO_12H:
        saudacao_fim = "Tenha um bom dia!"
    elif hora_atual_fim <= HORARIO_18H:
        saudacao_fim = "Tenha uma ótima tarde!"
    else:
        saudacao_fim = "Tenha uma ótima noite! Bom descanso!"



    # Envio da mensagem estilizada e da imagem para o canal específico
    logger.info(f"Enviando relatório do setor {setor} via Slack...")
    
    for destinatario in destinatarios:
        try:
            # Verificar se o destinatário começa com 'U' (usuário direto)
            if destinatario.startswith('U'):
                response_dm = client.conversations_open(users=destinatario)
                channel_id = response_dm["channel"]["id"]
                
                # Enviar a mensagem
                response_message = client.chat_postMessage(
                    channel=channel_id, 
                    blocks=mensagem2["blocks"], 
                    text=f"Report Diário {data_formatada}"
                )
                logger.info(f"Mensagem do setor {setor} enviada para usuário {destinatario}")
                
                # Enviar a imagem
                with open(imagem_path, "rb") as image_file:
                    response_file = client.files_upload_v2(
                        channel=channel_id,
                        file=image_file,
                        title=f"Report Diário {setor} {data_formatada} | {hora_atual}"
                    )
                logger.info(f"Imagem do setor {setor} enviada para usuário {destinatario}")
            
            # Verificar se o destinatário começa com 'C' (canal)
            elif destinatario.startswith('C'):
                # Enviar a mensagem
                response_message = client.chat_postMessage(
                    channel=destinatario, 
                    blocks=mensagem2["blocks"], 
                    text=f"Report Diário {data_formatada}"
                )
                logger.info(f"Mensagem do setor {setor} enviada para canal {destinatario}")
                
                # Enviar a imagem
                with open(imagem_path, "rb") as image_file:
                    response_file = client.files_upload_v2(
                        channel=destinatario,
                        file=image_file,
                        title=f"Report Diário {setor} {data_formatada} | {hora_atual}"
                    )
                logger.info(f"Imagem do setor {setor} enviada para canal {destinatario}")
            
            else:
                logger.warning(f"Destinatário não reconhecido: {destinatario}")
            
            # Aguardar 5 segundos entre envios
            time.sleep(5)
        
        except Exception as e:
            logger.error(f"Erro ao enviar relatório do setor {setor} para {destinatario}: {e}")

# ==============================================
# ENVIO DA MENSAGEM FINAL
# ==============================================
logger.info("Enviando mensagem final com botões...")

for destinatario in destinatarios:
    try:
        if destinatario.startswith('U') or destinatario.startswith('C'):
            response_message2 = client.chat_postMessage(
                channel=destinatario, 
                blocks=mensagem3["blocks"], 
                text=f"{saudacao_fim}"
            )
            logger.info(f"Mensagem final enviada para {destinatario}")
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem final para {destinatario}: {e}")

logger.info("Processo de envio de relatórios concluído com sucesso!")
