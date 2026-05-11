from slack_sdk import WebClient
from sqlalchemy import create_engine
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import locale
import matplotlib.pyplot as plt
import time
import configparser
import os
import ssl
from urllib.request import urlopen
import certifi
import holidays
os.environ['SSL_CERT_FILE'] = certifi.where()

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Obter o caminho absoluto para o arquivo config.ini
config_folder = r'C:\Users\lucas.abner\Desktop\Rotinas Python'
config_file_path = os.path.join(config_folder, 'config.ini')

# Ler as configurações do arquivo config.ini
config = configparser.ConfigParser()
config.read(config_file_path)

# Set up PostgreSQL connection
server = config['database']['server']
database = config['database']['database']
uid = config['database']['uid']
pwd = config['database']['pwd']
conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
engine = create_engine(conn_string)
connection = engine.connect()


data_hoje = datetime.now().date()
# Lista de feriados no Brasil (ou outro país)
feriados_brasil = holidays.Brazil()

# Verificar se hoje é um dia útil
if data_hoje.weekday() < 5 and data_hoje not in feriados_brasil:
    print(f"{data_hoje} é um dia útil.")
    setores = ['Suporte','Financeiro']
    dia_util = True
else:
    print(f"{data_hoje} não é um dia útil.")
    setores = ['Suporte']
    dia_util = False

# Definir o locale para português
locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
# Armazenar a hora atual
hora_atual = datetime.now().time().replace(microsecond=0)
# Obter a data de hoje
data_de_hoje = datetime.now().date()
data_formatada = data_de_hoje.strftime('%d/%m')  # Formato DD/MM/YYYY
data_7_dias = data_de_hoje - timedelta(days=7)
data_7_dias_atras = data_7_dias.strftime('%d/%m')
# Obter o nome do dia da semana em português
nome_dia_semana = data_de_hoje.strftime('%A')

# Função para contar o número de linhas do DataFrame
def contar_linhas(df,setor=None,ignora_bot=None, atendidas=None, abandono=None,ultima_semana=None, data=None):

    if setor:
        df = df[(df['Setor'] == setor)]
    if ignora_bot:
        df = df[df['robo'] != 1]
    if atendidas:
        df = df[(df['abandono'] != 'Abandonado') & (df['Setor'] == setor) ]
    if abandono:
        df = df[(df['abandono'] == 'Abandonado') & (df['Setor'] == setor) ]
    if ultima_semana:
        df = df[(df['Ultima Semana'] == 1)]
    if data:
        df = df[(df['data'] == data_de_hoje)]

    """Retorna a quantidade de registros no DataFrame."""
    return len(df)

# Função para calcular o tempo médio de atendimento
def calcular_tempo(df, coluna_tempo, setor=None, ignora_bot=None, data=None):
    # Filtrar por setor, se fornecido
    if setor:
        df = df[df['Setor'] == setor]

    # Filtrar valores da coluna 'robo' se o parâmetro 'ignora_bot' for True
    if ignora_bot:
        df = df[(df['robo'] != 1) & (df[coluna_tempo] > 0)]

    # Filtrar por data, se fornecido
    if data:
        df = df[df['data'] == data]

    # Filtrar apenas os valores da coluna de tempo que forem <= 5400 segundos
    #df = df[df[coluna_tempo] <= 5400]

    # Soma dos valores da coluna de tempo
    total_tempo = df[coluna_tempo].sum()

    # Contagem de registros após os filtros
    total_registros = len(df)

    if total_registros > 0:
        # Cálculo do tempo médio em segundos
        tempo_medio_segundos = total_tempo / total_registros

        # Converter para o formato HH:MM:SS
        horas = int(tempo_medio_segundos // 3600)
        minutos = int((tempo_medio_segundos % 3600) // 60)
        segundos = int(tempo_medio_segundos % 60)

        return f"{horas:02}:{minutos:02}:{segundos:02}"
    else:
        return "00:00:00"

    
def obter_hoje():
    # Definir o início e o final do dia
    hoje_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    hoje_fim = hoje_inicio + timedelta(hours=23, minutes=59, seconds=59)
    
    return hoje_inicio, hoje_fim

# Função para somar os pontos com base na hora corrente e canal
def soma_points(df, canal=None,setor= None, ultima_semana=None, data=None):
    # Obter a hora atual
    hora_atual = datetime.now().time().replace(microsecond=0)
    
    # Converter a coluna 'Data Inicio' para datetime (se ainda não estiver)
    df['Data Inicio'] = pd.to_datetime(df['Data Inicio'])
    
    # Filtrar pelo canal, se fornecido
    if canal:
        df = df[df['Canal'] == canal]
    if setor:
        df = df[df['Setor'] == setor]
    if ultima_semana:
        df = df[(df['Ultima Semana'] == 1)]
    if data:
        df = df[(df['data'] == data_de_hoje)]


    # Inicializar a soma
    soma_first = int(df['first_point'].sum())  # sempre soma o primeiro ponto como inteiro
    soma_second = '-'  # valor padrão para segundo ponto
    soma_third = '-'  # valor padrão para terceiro ponto

    # Verificar os intervalos de tempo e realizar a soma
    if hora_atual >= datetime.strptime("14:00:00", "%H:%M:%S").time():
        soma_second = int(df['second_point'].sum())  # apenas soma se a condição for verdadeira

    # Verificar os intervalos de tempo e realizar a soma
    if hora_atual >= datetime.strptime("18:00:00", "%H:%M:%S").time():
        soma_third = int(df['third_point'].sum())  # apenas soma se a condição for verdadeira

    return soma_first, soma_second, soma_third

def padrao(df, canal=None,setor= None, ultima_semana=None, data=None,diautil=None):
    # Obter a hora atual
    hora_atual = datetime.now().time().replace(microsecond=0)
    
    # Converter a coluna 'Data Inicio' para datetime (se ainda não estiver)
    df['Data Inicio'] = pd.to_datetime(df['Data Inicio'])

    # Filtrar pelo canal, se fornecido
    if canal:
        df = df[df['Canal'] == canal]
    if setor:
        df = df[df['Setor'] == setor]
    if ultima_semana:
        df = df[(df['Ultima Semana'] == 1)]
    if data:
        df = df[(df['Data Inicio'] >= padrao_inicio) & (df['Data Inicio'] <= padrao_fim)]
    if diautil:
        df= df[df['diautil'] == 1] 

     # Supondo que 'data' é uma coluna no DataFrame
    total = df[df['diautil'] == 1]  # Filtra apenas as linhas onde 'diautil' é igual a 1
    total = total['data'].nunique()  # Conta o número de valores únicos na coluna 'data'
    print(total)

    # Inicializar a soma
    total_first_padrao = df['first_point'].sum()  # sempre soma o primeiro ponto
    soma_first_padrao = round(total_first_padrao/total)
    soma_second_padrao = '-'  # valor padrão para segundo ponto
    soma_third_padrao = '-'  # valor padrão para terceiro ponto

    # Verificar os intervalos de tempo e realizar a soma
    if hora_atual >= datetime.strptime("14:00:00", "%H:%M:%S").time():
        total_second_padrao = df['second_point'].sum()  # apenas soma se a condição for verdadeira
        soma_second_padrao = round(total_second_padrao/total)
    # Verificar os intervalos de tempo e realizar a soma
    if hora_atual >= datetime.strptime("18:00:00", "%H:%M:%S").time():
        total_third_padrao = df['third_point'].sum()  # apenas soma se a condição for verdadeira
        soma_third_padrao = round(total_third_padrao/total)

    return soma_first_padrao, soma_second_padrao, soma_third_padrao

def percentual_padrao(valor1, valor2):
    # Substituir '-' por None
    if valor1 == '-':
        valor1 = None
    if valor2 == '-':
        valor2 = None
    
    # Verificar se valor2 é None
    if valor2 is None or valor2 == 0:
        # Trate o caso onde valor2 é zero ou None; por exemplo, retornando 0 ou um valor padrão
        return 0
    else:
        calculo = (valor1 - valor2) / valor2
        return calculo

# Função para definir a cor da célula e do texto
def ajustar_celula(celula, valor):
    if valor < 0:
        celula.set_facecolor('#2EA407')  # Verde para negativo
        celula.set_text_props(text=f"{round(valor, 2)}%", color='white')  # Texto branco
    elif valor > 0:
        celula.set_facecolor('#E46B6B')  # Vermelho para positivo
        celula.set_text_props(text=f"{round(valor, 2)}%", color='white')  # Texto branco
    elif valor == 0:
        celula.set_facecolor('white')  # Vermelho para positivo
        celula.set_text_props(text="-", color='black')  # Texto branco




padrao_inicio = pd.to_datetime('2024-07-01 00:00:00')  # ou a data que você estiver utilizando
padrao_fim = pd.to_datetime('2024-11-30 23:59:59')

hoje_inicio, hoje_fim = obter_hoje()

# Consulta SQL
query = f'''SELECT * FROM octadesk.vw_report_diario WHERE "Data Inicio" BETWEEN '2024-07-01 00:00:00' AND '{hoje_fim}'; '''

# Executa a consulta e armazena os resultados no DataFrame
df = pd.read_sql_query(query, connection)


if hora_atual <= datetime.strptime("12:00:00", "%H:%M:%S").time():
        saudacao = "Bom dia!"
elif hora_atual <= datetime.strptime("19:00:00", "%H:%M:%S").time():
    saudacao = "Boa tarde!"
else:
    saudacao = "Boa noite!"

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
                "text": "*Report Diário Octadesk:*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f" {saudacao} Estamos disponibilizando abaixo os dados do relatório *Report Diário* da Octadesk."
            }
        }
    ]    
}

mensagem2 = ""

mensagem3 = {
        "blocks": [
            {
                "type": "divider"
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":bar_chart:  Relatório Completo",
                            "emoji": True
                        },
                        "url": "https://app.powerbi.com/reportEmbed?reportId=ecf010c1-0d61-4244-ad98-fd92b2a4c822&autoAuth=true&ctid=700a4e08-ed6d-4401-835a-4e4fe805c8ca"
                    },

                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":sos:  Ajuda",
                            "emoji": True
                        }
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":loudspeaker:  Feedback",
                            "emoji": True
                        }
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Se ficar com dúvidas sobre as informações, basta chamar algum de nossos analistas aqui no Slack ou enviar um email para: trafego@locaweb.com.br."
                }
            },
        ]
    }




# Lista de destinatários (IDs de canal ou de usuários)
#destinatarios = ['C07NSPQ69TL'] #CANAL teste
destinatarios = ['C08CURK02H0'] #CANAL OFICIAL


# Criação do cliente Slack com seu token
client = WebClient('[REDACTED_SLACK_TOKEN]')



for destinatario in destinatarios:
        # Verificar se o destinatário começa com 'U'
        if destinatario.startswith('U'):
            # Abrir um direct com o usuário do Slack
            response_dm = client.conversations_open(users=destinatario)
            channel_id = response_dm["channel"]["id"]

            # Enviar a mensagem no direct
            response_message = client.chat_postMessage(channel=channel_id, blocks=mensagem["blocks"], text= f"Report Diário {data_formatada}")
            print(f"Mensagem enviada para o direct do usuário {destinatario}.")
        # Verificar se o destinatário começa com 'C'
        elif destinatario.startswith('C'):
            # Usar o código que já possui para destinatários que começam com 'C'
            response_message = client.chat_postMessage(channel=destinatario, blocks=mensagem["blocks"], text=f"Report Diário {data_formatada}")
            print(f"Mensagem enviada para {destinatario}.")



for setor in setores:

    
    #Soma padrão
    soma_first_padrao, soma_second_padrao, soma_third_padrao = padrao(df,setor=setor,data=True,diautil=True)

    # Soma semana anterior
    soma_first_semana_anterior_wp, soma_second_semana_anterior_wp, soma_third_semana_anterior_wp = soma_points(df, canal='WhatsApp', setor=setor, ultima_semana=True)
    soma_first_semana_anterior_chat,soma_second_semana_anterior_chat,soma_third_semana_anterior_chat = soma_points(df, canal='Chat',setor=setor,ultima_semana=True)
    soma_first_semana_anterior, soma_second_semana_anterior, soma_third_semana_anterior = soma_points(df,canal=None,setor=setor, ultima_semana=True)

    #Soma dia atual
    soma_first_wp,soma_second_wp,soma_third_wp = soma_points(df, canal='WhatsApp',setor=setor,ultima_semana=0,data=True)    
    soma_first_chat,soma_second_chat,soma_third_chat = soma_points(df, canal='Chat',setor=setor,ultima_semana=0,data=True)
    soma_first, soma_second, soma_third = soma_points(df,canal=None,setor=setor, ultima_semana=0,data=True)

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
    tma = calcular_tempo(df, coluna_tempo_atendimento,setor=setor, ignora_bot=True,data=data_de_hoje)

    # Calcula o tempo médio de espera, ignorando robôs
    tme = calcular_tempo(df, coluna_tempo_espera,setor=setor,data=data_de_hoje)

    #quantidade de recebidos
    recebidos = contar_linhas(df,setor=setor,data=True)

    #Quantidade de Atendidos
    atendidos = contar_linhas(df,setor=setor,ignora_bot=True,atendidas=True,data=True)

    #Quantidade de abandonos
    abandonos = contar_linhas(df,setor=setor,ignora_bot=True,abandono=True,data=True)

    #Percentual de abandonos em relçao aos recebidos
    if recebidos != 0:
        calculo_percentual_de_abandonos = (abandonos / recebidos) * 100
    else:
        calculo_percentual_de_abandonos = 0  # ou outro valor que faça sentido no seu contexto


    #Arredondamento do resultado,  mantendo duas casas decimais
    percentual_de_abandonos = round(calculo_percentual_de_abandonos, 2) 
   
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

    if nome_dia_semana == ('terÃ§a-feira'):
        nome_dia_semana = str('Terça-Feira')
    
    data_completa = f" {nome_dia_semana} | {data_formatada}"
    data_completa_semana_anterior = f"{nome_dia_semana}|{data_7_dias_atras}"

    
    tabela = {
        "": ["Padrão Média dia Útil - Jul. a Nov. 2024",
            f"WhatsApp D-7 {data_completa_semana_anterior}",
            f"Chat D-7 {data_completa_semana_anterior}",
            f"Consolidado D-7 {data_completa_semana_anterior}",
            f"WhatsApp {data_completa}",
            f"Chat {data_completa}",
            f"Consolidado {data_completa}",
            "% Comparado ao Padrão",
            "% Comparado a Semana Anterior"],
        "00:00 as 10:00": 
            [soma_first_padrao,
            soma_first_semana_anterior_wp, 
            soma_first_semana_anterior_chat,
            soma_first_semana_anterior, 
            soma_first_wp, 
            soma_first_chat, 
            soma_first,
            0,
            0],
        "00:00 as 14:00": 
            [soma_second_padrao,
            soma_second_semana_anterior_wp, 
            soma_second_semana_anterior_chat,
            soma_second_semana_anterior,
            soma_second_wp, 
            soma_second_chat, 
            soma_second,
            0,
            0],
        "00:00 as 18:00": 
            [soma_third_padrao,
            soma_third_semana_anterior_wp,
            soma_third_semana_anterior_chat,
            soma_third_semana_anterior, 
            soma_third_wp, 
            soma_third_chat, 
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

    #Dados Consolidado D-7
    table[4, 0].set_facecolor('#F3A07D')
    table[4, 1].set_facecolor('#F3A07D')
    table[4, 2].set_facecolor('#F3A07D')
    table[4, 3].set_facecolor('#F3A07D')

    #Dados de Whatsapp de hoje
    table[5, 0].set_facecolor('#9AC09A')
    table[5, 1].set_facecolor('#9AC09A')
    table[5, 2].set_facecolor('#9AC09A')
    table[5, 3].set_facecolor('#9AC09A')

    #Dados de Chat de hoje
    table[6, 0].set_facecolor('#9AC09A')
    table[6, 1].set_facecolor('#9AC09A')
    table[6, 2].set_facecolor('#9AC09A')
    table[6, 3].set_facecolor('#9AC09A')

    #Dados Consolidado de hoje
    table[7, 0].set_facecolor('#9AC09A')
    table[7, 1].set_facecolor('#9AC09A')
    table[7, 2].set_facecolor('#9AC09A')
    table[7, 3].set_facecolor('#9AC09A')

    #Dados Comparado ao padrão
    table[8, 0].set_facecolor('white')
    ajustar_celula(table[8, 1], percentual_padrao1)
    ajustar_celula(table[8, 2], percentual_padrao2)
    ajustar_celula(table[8, 3], percentual_padrao3)

    #Dados Comparado a semana anterior
    table[9, 0].set_facecolor('white')
    ajustar_celula(table[9, 1], percentual_semana_anterior1)
    ajustar_celula(table[9, 2], percentual_semana_anterior2)
    ajustar_celula(table[9, 3], percentual_semana_anterior3)


    # Adicionando um título
    plt.title(f"Report Diário {setor} Octadesk {data_formatada} | {hora_atual}", fontsize=14)

    # Salvando a tabela como imagem PNG
    imagem_path = "report_diario_Octadesk.png"
    plt.savefig(imagem_path, format='png', bbox_inches='tight', dpi=300)

    plt.subplots_adjust(left=0.1, right=0.9, top=0.95, bottom=0.1)


    # Exibindo a tabela
    #plt.show()


    hora_atual = datetime.now().time()

    if hora_atual <= datetime.strptime("12:00:00", "%H:%M:%S").time():
        saudacao = "Tenha um bom dia!"
    elif hora_atual <= datetime.strptime("18:00:00", "%H:%M:%S").time():
        saudacao = "Tenha uma ótima tarde!"
    else:
        saudacao = "Tenha uma ótima noite! Bom descanso!"



    # Envio da mensagem estilizada e da imagem para o canal específico
    for destinatario in destinatarios:
        # Verificar se o destinatário começa com 'U'
        if destinatario.startswith('U'):
            # Abrir um direct com o usuário do Slack
            response_dm = client.conversations_open(users=destinatario)
            channel_id = response_dm["channel"]["id"]

            # Enviar a mensagem no direct
            response_message = client.chat_postMessage(channel=channel_id, blocks=mensagem2["blocks"], text= f"Report Diário {data_formatada}")
            print(f"Mensagem enviada para o direct do usuário {destinatario}.")
            
            # Enviar a imagem usando files_upload_v2
            with open(imagem_path, "rb") as image_file:
                response_file = client.files_upload_v2(
                    channel=channel_id,  # Usar channel do direct
                    file=image_file,
                    title=f"Report Diário {data_formatada} | {hora_atual}"
                )
            print(f"Imagem enviada para o direct do usuário {destinatario}.")
        
        # Verificar se o destinatário começa com 'C'
        elif destinatario.startswith('C'):
            # Usar o código que já possui para destinatários que começam com 'C'
            response_message = client.chat_postMessage(channel=destinatario, blocks=mensagem2["blocks"], text=f"Report Diário {data_formatada}")
            print(f"Mensagem enviada para {destinatario}.")
            
            # Enviar a imagem usando files_upload_v2
            with open(imagem_path, "rb") as image_file:
                response_file = client.files_upload_v2(
                    channel=destinatario,  # Usar channel
                    file=image_file,
                    title=f"Report Diário {setor} {data_formatada} | {hora_atual}"
                )
            print(f"Imagem enviada para {destinatario}.")

        else:
            print('Usuário não reconhecido')

        # Aguardar 2 segundos (ou o tempo que você preferir)
        time.sleep(5)

for destinatario in destinatarios:
    # Enviar a terceira mensagem, apenas para destinatários reconhecidos
    if destinatario.startswith('U') or destinatario.startswith('C'):
        response_message2 = client.chat_postMessage(channel=destinatario, blocks=mensagem3["blocks"],text=f"{saudacao}")
        print(f"Mensagem enviada para {destinatario}.")
