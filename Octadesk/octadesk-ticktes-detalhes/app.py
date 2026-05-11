import pandas as pd
from sqlalchemy import create_engine,text
from datetime import datetime,timedelta, timezone
import json
import configparser
import requests
import psycopg2
from function_logger import configurar_logger
from pathlib import Path
import os
import sys

sql_path = Path(__file__).parent 

# Adiciona o caminho três diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack, notify_slack_success  

# Configurar logger
logger = configurar_logger()

tabela = 'rawdata_tickets_detalhes'
schema = 'octadesk'  
rotina = "Octadesk (Carrega Tickets Detalhados)"

try:
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
    engine_conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
    engine = create_engine(engine_conn_string)
    connection = engine.connect()

    # Set up PostgreSQL connection
    psy_conn = psycopg2.connect(
        dbname=database,
        user=uid,
        password=pwd,
        host=server
    )
    cur = psy_conn.cursor()
    logger.info("Banco conectado com sucesso")

except Exception as e:
    print("Ocorreu um erro:", e)
    logger.error(f"Ocorreu um erro de conexão: {e}")    



data_hora = datetime.now()
data = datetime.now().date()
hora = datetime.now().time()
hora_anterior = data_hora - timedelta(hours=3)
hora_anterior = hora_anterior.time()

print(f"Inicio : {data_hora}")

DDL_URL = "https://help.apibeta.octadesk.services"
#TOKEN = "75657565-0f17-4044-ab0b-3268d2052a6b.ae43d054-7ec4-4cf1-8b01-7ae37436af67"
TOKEN = "75657565-0f17-4044-ab0b-3268d2052a6b.13dd5460-8d60-4df0-b79a-7d842db006dc"

def ajusta_formato_data(atendimento):
    if atendimento:
        # Remove o 'Z' e adiciona deslocamento de fuso horário explícito
        if atendimento.endswith("Z"):
            atendimento = atendimento[:-1] + "+0000"
        
        # Ajuste para lidar com frações de segundo
        atendimento_convertido = datetime.strptime(atendimento, '%Y-%m-%dT%H:%M:%S.%f%z')
        
        # Ajustar o fuso horário (opcional)
        ajusta_fuso = atendimento_convertido - timedelta(hours=3)
        
        # Formatar a data no formato desejado
        atendimento = ajusta_fuso.strftime('%Y-%m-%d %H:%M:%S')
        return atendimento
    return None


def get_ticket_number(DDL_URL,TOKEN,ID):

    endpoint = f"{DDL_URL}/tickets/{ID}"

    headers = {
        "accept": "application/json",
        "X-API-KEY": TOKEN
    }

    response = requests.get(endpoint, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Falha na autenticação. Código de status: {response.status_code}")
        return None
    

query = f"SELECT DISTINCT numero FROM octadesk.ticketsbacklog a WHERE data_atualizacao >= '{data} {hora_anterior}'"

#query = "SELECT DISTINCT numero FROM octadesk.ticketsbacklog a WHERE datacriacao >= '2025-07-21 00:00:00'"

df = pd.read_sql_query(query,connection)

carga = []

todos_tickets = []

for _, row in df.iterrows():
    
    atendimento_id = row['numero']
    ticket = get_ticket_number(DDL_URL, TOKEN, atendimento_id)

    # Verifica se o dicionário tem dados
    if ticket:
        todos_tickets.append(ticket)

        id = ticket.get('id')
        number = ticket.get('number')
        summary = ticket.get('summary')
        description = ticket.get('description')
        status_id = ticket.get('status').get('id')
        status_name = ticket.get('status').get('name')
        channel_id = ticket.get('channel').get('id')
        channel_name = ticket.get('channel').get('name')
        requester_id = ticket.get('requester').get('id')
        requester_name = ticket.get('requester').get('name')
        requester_email = ticket.get('requester').get('email')
        resolution_Date = ticket.get('resolutionDate')
        resolution_Date = ajusta_formato_data(resolution_Date)

        #CUSTOM FIELDS DESTRO DA CHAVE REQUESTER:
        requester_custom_fields = ticket.get('requester').get('customField', []) # ARMAZENA A LISTA COMPLETA
        requester_cf = {item['key']: item['value'] for item in requester_custom_fields} #CRIA UMA LISTA E ADICIONA EM UMA VARIAVEL   
        requester_custom_fields = json.dumps(requester_custom_fields)

        #PERCORRE OS ITENS DESTA LISTA REQUESTER
        requester_cf_id_contact_status = requester_cf.get('idContactStatus',None)
        requester_cf_cnpj = requester_cf.get('cnpj',None)
        requester_cf_chat_id_conversa = requester_cf.get('chat_id-conversa',None)
        requester_cf_chat_subdominio_octadesk = requester_cf.get('subdominio_octadesk',None)
        requester_cf_chat_ultima_data_contato= requester_cf.get('chat_ultima_data_contato',None)
        requester_cf_chat_ultima_data_contato = ajusta_formato_data(requester_cf_chat_ultima_data_contato)
        requester_cf_chat_id_ultima_conversa = requester_cf.get('chat_id_ultima_conversa',None)
        requester_cf_chat_nome_grupo_atendimento = requester_cf.get('chat_nome_grupo_atendimento',None)
        requester_cf_chat_tem_ticket = requester_cf.get('chat_tem-ticket',None)
        requester_cf_chat_id_conversa = requester_cf.get('chatIdConversa',None)
        requester_cf_cluster = requester_cf.get('cluster',None)
        requester_cf_codigo_do_plano = requester_cf.get('codigo_do_plano',None)
        requester_cf_mrr = requester_cf.get('mrr',None)
        requester_cf_data_de_contratacao = requester_cf.get('data_de_contratacao',None)
        requester_cf_perfil_do_usuario = requester_cf.get('perfil_do_usuario',None)

        #--------------------------------------------------------------------------------------------------------------------------------

        group_id = ticket.get('group', {}).get('id',None)
        group_name = ticket.get('group', {}).get('name',None)

        form = ticket.get('form',{})
        form_id = form.get('id', None)
        form_name = form.get('name',None)

        priority = ticket.get('priority', {})
        priority_id = priority.get('id', None)
        priority_name = priority.get('name',None)

        organization = ticket.get('organization',{})
        organization_id = organization.get('id',None)
        organization_name = organization.get('name',None)
        custom_fields_organization = organization.get('customField', [])
        custom_fields_organization= json.dumps(custom_fields_organization)

        assigned = ticket.get('assigned',{})
        assigned_id = assigned.get('id',None)
        assigned_name = assigned.get('name',None)
        assigned_email = assigned.get('email',None)

        participating_assigned = ticket.get('participatingAssigned',[])
        participating_assigned_last = {item['id']: item['name'] for item in participating_assigned}
        # Obter a última tupla (id, name)
        if participating_assigned_last:
            last_id, last_name = list(participating_assigned_last.items())[-1]
        else:
            last_id, last_name = None, None 
        participating_assigned_last = json.dumps(participating_assigned_last)

        cc = ticket.get('cc',[])
        cc = json.dumps(cc)
        cco = ticket.get('cco',[])
        cco = json.dumps(cco)
        tags = ticket.get('tags',[])
        created_at = ticket.get('createdAt')
        created_at = ajusta_formato_data(created_at)
        interactions_count = ticket.get('interactionsCount')
        updated_at = ticket.get('updatedAt',{})
        updated_at = ajusta_formato_data(updated_at)
        
        updated_by = ticket.get('updatedBy',{})
        updated_by_id = updated_by.get('id',None)
        updated_by_name = updated_by.get('name',None)
        updated_by_email = updated_by.get('email',None)


        #--------------------------------------------------------------------------------------------------------------------------------
        #PERCORRE OS ITENS DESTA LISTA 'customField'

        custom_field = ticket.get('customField',[]) # ARMAZENA A LISTA COMPLETA
        cf = {item['key']: item['value'] for item in custom_field} #CRIA UMA LISTA E ADICIONA EM UMA VARIAVEL

        custom_field = json.dumps(custom_field)

        cf_quem_interagiu_por_ultimo = cf.get('quem_interagiu_por_ultimo', None)
        cf_squad = cf.get('squad', None)
        cf_ambiente = cf.get('ambiente', None)
        cf_cluster = cf.get('cluster', None)
        cf_status_do_card_no_jira = cf.get('status_do_card_no_jira', None)
        cf_tipo_do_ticket_produto = cf.get('tipo_do_ticket_produto', None)
        cf_escalado_n3 = cf.get('escalado_n3', None)
        cf_reputacao_afetada = cf.get('reputacao_afetada', None)
        cf_nivel_de_atrito = cf.get('nivel_de_atrito', None)
        cf_risco_de_churn_oficial = cf.get('risco_de_churn_oficial', None)
        cf_analista_responsavel_pela_abertura = cf.get('analista_responsavel_pela_abertura', None)
        cf_whatsapp_do_cliente = cf.get('whatsapp_do_cliente', None)
        cf_an_lise_qualidade = cf.get('an_lise_qualidade', None)
        cf_analise_qualidade = cf.get('analise_qualidade', None)

        #--------------------------------------------------------------------------------------------------------------------------------
        #INTERAÇÃO SOB A LISTA APPS

        apps = ticket.get('apps',[]) #ARAMAZENA A LISTA COMPLETA COM DEFAULT 'VAZIO' []
        apps = json.dumps(apps)
    
        last_interaction = ticket.get('lastInteraction', {})
        last_interaction = json.dumps(last_interaction)
        last_human_interaction = ticket.get('lastHumanInteraction', {})
        last_human_interaction = json.dumps(last_human_interaction)
        attachments = ticket.get('attachments',[])
        attachments = json.dumps(attachments)

        registro = {
            "id": id,
            "number": number,
            "summary": summary,
            "description": description,

            "status_id": status_id,
            "status_name": status_name,

            "channel_id": channel_id,
            "channel_name": channel_name,

            "requester_id": requester_id,
            "requester_name": requester_name,
            "requester_email": requester_email,
            "requester_custom_fields":requester_custom_fields,
            "requester_cf_id_contact_status": requester_cf_id_contact_status,
            "requester_cf_cnpj": requester_cf_cnpj,
            "requester_cf_chat_id_conversa": requester_cf_chat_id_conversa,
            "requester_cf_chat_subdominio_octadesk": requester_cf_chat_subdominio_octadesk,
            "requester_cf_chat_ultima_data_contato": requester_cf_chat_ultima_data_contato,
            "requester_cf_chat_id_ultima_conversa": requester_cf_chat_id_ultima_conversa,
            "requester_cf_chat_nome_grupo_atendimento": requester_cf_chat_nome_grupo_atendimento,
            "requester_cf_chat_tem_ticket": requester_cf_chat_tem_ticket,
            "requester_cf_cluster": requester_cf_cluster,
            "requester_cf_codigo_do_plano": requester_cf_codigo_do_plano,
            "requester_cf_mrr": requester_cf_mrr,
            "requester_cf_data_de_contratacao": requester_cf_data_de_contratacao,
            "requester_cf_perfil_do_usuario": requester_cf_perfil_do_usuario,

            "group_id": group_id,
            "group_name": group_name,

            "form_id": form_id,
            "form_name": form_name,

            "priority_id": priority_id,
            "priority_name": priority_name,

            "organization_id": organization_id,
            "organization_name": organization_name,
            "custom_fields_organization":custom_fields_organization,

            "assigned_id": assigned_id,
            "assigned_name": assigned_name,
            "assigned_email": assigned_email,
            "participating_assigned": participating_assigned_last,
            "last_id": last_id,
            "last_name":last_name,

            "cc":cc,
            "cco":cco,
            "tags":tags,

            "interactions_count":interactions_count,

            "created_at":created_at,
            "updated_at":updated_at,
            "updated_by_id":updated_by_id,
            "updated_by_name":updated_by_name,
            "updated_by_email":updated_by_email,

            "custom_field":custom_field,
            "cf_quem_interagiu_por_ultimo":cf_quem_interagiu_por_ultimo,
            "cf_squad":cf_squad,
            "cf_ambiente":cf_ambiente,
            "cf_cluster":cf_cluster,
            "cf_status_do_card_no_jira":cf_status_do_card_no_jira,
            "cf_tipo_do_ticket_produto":cf_tipo_do_ticket_produto,
            "cf_escalado_n3":cf_escalado_n3,
            "cf_reputacao_afetada":cf_reputacao_afetada,
            "cf_nivel_de_atrito":cf_nivel_de_atrito,
            "cf_risco_de_churn_oficial":cf_risco_de_churn_oficial,
            "cf_analista_responsavel_pela_abertura":cf_analista_responsavel_pela_abertura,
            "cf_whatsapp_do_cliente":cf_whatsapp_do_cliente,
            "cf_an_lise_qualidade":cf_an_lise_qualidade,
            "cf_analise_qualidade":cf_analise_qualidade,

            "apps":apps,

            "last_interaction":last_interaction,
            "last_human_interaction":last_human_interaction,
            "attachments":attachments,
            "resolution_Date":resolution_Date

        }

        carga.append(registro)


# Salva tudo no final
if todos_tickets:
    caminho_arquivo = os.path.join(sql_path, 'tickets.json')
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        json.dump(todos_tickets, f, ensure_ascii=False, indent=4)

df_content = pd.DataFrame(carga)

df_content.to_sql(tabela,con=engine,if_exists='replace',index=False,schema=schema)

total_linhas_atualizadas = 0

try:
    with open(f'{sql_path}/insereDados.sql', 'r',encoding='utf-8') as file: 
        query_insercao = text(file.read())

    tabela = 'octadesk.tickets_detalhados'
    linhas_inseridas = 0
    result = connection.execute(query_insercao)
    total_linhas_inseridas = result.rowcount
    linhas_inseridas += total_linhas_inseridas
    connection.commit()
    logger.info(f' {linhas_inseridas} linhas inseridas na tabela {tabela}')
    notify_slack_success(f"{total_linhas_inseridas} linhas inseridas e {total_linhas_atualizadas} linhas atualizadas na tabela {tabela}.:octadesk:",total_linhas_inseridas,total_linhas_atualizadas, rotina)

except Exception as e:
    print("Ocorreu um erro:", e)
    logger.error(f'Ocorreu um erro: {e}')
    notify_slack(f"Erro na execução da {rotina}: {e}", rotina)

connection.close()
engine.dispose

data_hora = datetime.now()

print(f"FIM : {data_hora}")












    

