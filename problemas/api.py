import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from datetime import datetime, timedelta,timezone
import json
import os
import sys
import logging
from function_logger import configurar_logger
import configparser
from sqlalchemy import create_engine, text
from pathlib import Path
from io import StringIO
from urllib.parse import urlencode

# Adiciona o caminho dois diretórios acima ao Python Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from notifica import notify_slack, notify_slack_success

# Caminho para o arquivo config
sql_path = Path(__file__).parent
config_path = f'{sql_path}/../'

# Configurar logger
logger = configurar_logger()

# Função auxiliar para executar SQL
def executar_sql(engine, sql_file_path, descricao="operação SQL"):
    """
    Executa um arquivo SQL e retorna o número de linhas afetadas
    """
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            query = text(file.read())
        
        with engine.connect() as conn:
            result = conn.execute(query)
            conn.commit()
            linhas_afetadas = result.rowcount
            logger.info(f"{descricao}: {linhas_afetadas} linhas afetadas")
            return linhas_afetadas
            
    except Exception as e:
        logger.error(f"Erro ao executar {descricao}: {e}")
        raise

try:
    # Obter o caminho absoluto para o arquivo config.ini
    config_file_path = os.path.join(config_path, 'config.ini')

    # Ler as configurações do arquivo config.ini
    config = configparser.ConfigParser()
    config.read(config_file_path)

    # Pegando configurações da API
    username = config['service_now']['username']
    senha = config['service_now']['pwd']
    instance = config['service_now']['instance']
    timeout = int(config['service_now']['timeout'])

    # Set up PostgreSQL connection
    server = config['database']['server']
    database = config['database']['database']
    uid = config['database']['uid']
    pwd = config['database']['pwd']

    # Conexão pelo sqlAlchemy
    conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
    engine = create_engine(conn_string)
    logger.info("Banco conectado com sucesso")

except Exception as e:
    print("Ocorreu um erro:", e)
    logger.error(f"Ocorreu um erro de conexão: {e}") 

# Construção do endpoint da API
base_url = f'https://{instance}.service-now.com/api/now/table/problem'

# Query filters para buscar incidentes
query_filters = [
    #"opened_by.u_type=nominal",
    #"state!=10", 
    "priority=1^ORpriority=2^ORpriority=3^ORpriority=4^ORpriority=5",
    "sys_updated_onRELATIVEGT@hour@ago@24",
    "company.name=Octadesk^ORcompany.name=Locaweb^ORcompany.name=KingHost"
]

# Campos a serem retornados
fields = [
    'number', 'company', 'task_for', 'cmdb_ci','assignment_group', 'assigned_to', 'priority', 
    'u_produto', 'u_categoria', 'u_subcategoria', 'state', 'u_origem', 'opened_at', 'opened_by',
    'closed_at', 'closed_by', 'u_codigo_de_encerramento', 'u_chamado_externo', 'u_prb_revisado',
    'short_description', 'description', 'u_solucao_alternativo', 'close_notes', 
    'sys_mod_count','opened_by.department'
]

# Parâmetros da URL
params = {
    'sysparm_query': '^'.join(query_filters),
    'sysparm_display_value': 'true',
    'sysparm_fields': ','.join(fields)
}

# URL final construída
url = f"{base_url}?{urlencode(params, safe='^@=!')}"

# Cabeçalhos
headers = {
    'Content-Type': 'application/json'
}

# Requisição GET
try:
    response = requests.get(url, auth=HTTPBasicAuth(username, senha), headers=headers, timeout=timeout)
    
    # Validar resposta da API
    if response.status_code != 200:
        logger.error(f"Erro na API Service Now: {response.status_code} - {response.text}")
        raise Exception(f"API retornou erro: {response.status_code}")
        
except requests.exceptions.Timeout:
    logger.error(f"Timeout na requisição para API Service Now após {timeout} segundos")
    raise Exception("Timeout na requisição para API Service Now")
except requests.exceptions.ConnectionError:
    logger.error("Erro de conexão com a API Service Now")
    raise Exception("Erro de conexão com a API Service Now")
except requests.exceptions.RequestException as e:
    logger.error(f"Erro na requisição para API Service Now: {e}")
    raise Exception(f"Erro na requisição para API Service Now: {e}")

# Verificando e imprimindo resultado
try:
    carga = []
    data = response.json()

    def valor_display(campo):
        if isinstance(campo, dict):
            return campo.get('display_value') or campo.get('value')
        return campo

    def extrair_id_departamento(campo_departamento):
        if isinstance(campo_departamento, dict):
            link = campo_departamento.get('link')
            if link:
                return link.split('/')[-1]
            return campo_departamento.get('value')
        return campo_departamento

    # Coleta de cada um dos parametros
    for problem in data['result']:
        numero = problem.get('number')
        organizacao = valor_display(problem.get('company'))
        task_for = valor_display(problem.get('task_for'))
        servidor = valor_display(problem.get('cmdb_ci'))
        grupo_designado = valor_display(problem.get('assignment_group'))
        designado_para = valor_display(problem.get('assigned_to'))
        prioridade = problem.get('priority')
        produto = valor_display(problem.get('u_produto'))
        categoria = problem.get('u_categoria')
        subcategoria = problem.get('u_subcategoria')
        status = problem.get('state')
        origem = problem.get('u_origem')
        data_abertura = problem.get('opened_at')
        aberto_por = valor_display(problem.get('opened_by'))
        data_encerrado = problem.get('closed_at')
        fechado_por = valor_display(problem.get('closed_by'))
        codigo_encerramento = problem.get('u_codigo_de_encerramento')
        chamado_externo = problem.get('u_chamado_externo')
        prb_revisado = problem.get('u_prb_revisado')
        descricao_curta = problem.get('short_description')
        descricao = problem.get('description')
        solucao_alternativa = problem.get('u_solucao_alternativo')
        fechamento = problem.get('close_notes')
        atualizacoes = problem.get('sys_mod_count')
        id_departamento = extrair_id_departamento(problem.get('opened_by.department'))

        registro = {
            "numero": numero,
            "organizacao": organizacao,
            "task_for": task_for,
            "servidor": servidor,
            "grupo_designado": grupo_designado,
            "designado_para": designado_para,
            "prioridade": prioridade,
            "produto": produto,
            "categoria": categoria,
            "subcategoria": subcategoria,
            "status": status,
            "origem": origem,
            "data_abertura": data_abertura,
            "aberto_por": aberto_por,
            "data_encerrado": data_encerrado,
            "fechado_por": fechado_por,
            "codigo_encerramento": codigo_encerramento,
            "chamado_externo": chamado_externo,
            "prb_revisado": prb_revisado,
            "descricao_curta": descricao_curta,
            "descricao": descricao,
            "solucao_alternativa": solucao_alternativa,
            "fechamento": fechamento,
            "atualizacoes": atualizacoes,
            "id_departamento": id_departamento,
        }

        carga.append(registro)
    
    # Criando o df dos dados da API
    df_content = pd.DataFrame(carga)

    sql_path = Path(__file__).parent 

    df_content.to_csv(sql_path / 'dados_incs.csv', index=False)

    # Definindo inserção dos dados no banco
    tabela = 'rawdata_service_now_problems'
    schema = 'lwsa'
    rotina = "LWSA (Carrega Problems P1-P5)"

    linhas = 0
    linhas_inseridas = 0
    linhas_atualizadas = 0
    total_linhas = 0
    total_linhas_inseridas = 0
    total_linhas_atualizadas = 0

    if df_content.empty:
        print("Nenhuma pesquisa retornada. DataFrame vazio. Interrompendo execução.")
        logger.warning(f"Nenhuma pesquisa retornada na rotina {rotina}.")
        notify_slack_success(f"Nenhuma linha inserida na tabela {schema}.{tabela} :lwsa:", 0, 0, rotina)
        sys.exit(0)  # Encerra a execução quando não há dados

    else:
        # Alimenta a tabela raw
        df_content.to_sql(tabela, con=engine, if_exists='replace', index=False, schema=schema)
        print(f"Dados carregados na tabela: {tabela}...")

        #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        # Trunca a tabela lwsa.stg_service_now_problems
        table_name = 'lwsa.stg_service_now_problems'
        with engine.connect() as conn:
            truncate_query = text(f"TRUNCATE TABLE {table_name}")
            conn.execute(truncate_query)
            conn.commit()
            print(f"Tabela {table_name} truncada com sucesso")

        # Alimenta a tabela lwsa.stg_service_now_problems
        linhas = executar_sql(engine, f'{sql_path}/StgInsereDados.sql',
                                       f"Inserção na tabela {table_name}")
        total_linhas += linhas
        print(f"{total_linhas} linhas inseridas na tabela {table_name}.")

        #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        # Alimenta a tabela lwsa.service_now_problems
        table_name = 'lwsa.service_now_problems'
        linhas_inseridas = executar_sql(engine, f'{sql_path}/InsereDados.sql',
                                       f"Inserção na tabela {table_name}")
        total_linhas_inseridas += linhas_inseridas
        print(f"{total_linhas_inseridas} linhas inseridas na tabela {table_name}.")

        #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        # Atualiza a tabela lwsa.service_now_problems
        linhas_atualizadas = executar_sql(engine, f'{sql_path}/AtualizaDados.sql',
                                         f"Atualização da tabela {table_name}")
        total_linhas_atualizadas += linhas_atualizadas
        print(f"{total_linhas_atualizadas} linhas atualizadas na tabela {table_name}.")

except Exception as e:
    print("Ocorreu um erro:", e)
    logger.error(f"Ocorreu um erro: {e}")
    notify_slack(f"Erro na execução da {rotina}: {e}", rotina)

# Notificação consolidada após o processo
notify_slack_success(f"{total_linhas_inseridas} linhas inseridas e {total_linhas_atualizadas} linhas atualizadas na tabela {table_name} :lwsa:",total_linhas_inseridas,total_linhas_atualizadas, rotina)

data_hora = datetime.now()
print(f"Fim : {data_hora}")

# Fechar conexão
engine.dispose()
logger.info("Conexão com banco encerrada")
