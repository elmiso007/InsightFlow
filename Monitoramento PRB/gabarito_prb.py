import os
import json
import configparser
import logging
import psycopg2
from openai import OpenAI
from datetime import datetime

# 1. Carregar as configurações do arquivo config.ini
config_path = r"C:\Users\emerson.ramos\Desktop\projetos\config.ini"
config = configparser.ConfigParser()
config.read(config_path, encoding='utf-8')

# 2. Instanciar as credenciais mapeadas do arquivo config.ini
DB_HOST = config.get('database', 'server')
DB_PORT = config.get('database', 'port', fallback='5432')
DB_NAME = config.get('database', 'database')
DB_USER = config.get('database', 'uid')
DB_PASS = config.get('database', 'pwd')

OPENAI_KEY = config.get('openai', 'api_key')

# 3. Inicializar o cliente OpenAI
client = OpenAI(api_key=OPENAI_KEY)

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")


def configurar_logger():
    # Cria um logger de arquivo para registrar a carga historica.
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("gabarito_prb")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    log_path = os.path.join(LOG_DIR, f"gabarito_prb_{datetime.now():%Y%m%d}.log")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger

# Lista exata de PRBs definida para monitoramento
PRBS_ALVO = [
    'PRB0040838', 'PRB0050697', 'PRB0055284', 'PRB0055680', 'PRB0056922', 'PRB0057465', 
    'PRB0058097', 'PRB0058099', 'PRB0058309', 'PRB0059289', 'PRB0061147', 'PRB0062476', 
    'PRB0062616', 'PRB0063538', 'PRB0064231', 'PRB0065149', 'PRB0065286', 'PRB0066814', 
    'PRB0066895', 'PRB0066900', 'PRB0068236', 'PRB0068319', 'PRB0068344', 'PRB0068547', 
    'PRB0068880', 'PRB0068888', 'PRB0068958', 'PRB0068961', 'PRB0069348', 'PRB0069465', 
    'PRB0069543', 'PRB0069607', 'PRB0069725', 'PRB0069746', 'PRB0069777', 'PRB0069940', 
    'PRB0069964', 'PRB0070155', 'PRB0070280', 'PRB0070421', 'PRB0070457', 'PRB0070718', 
    'PRB0070735', 'PRB0070861', 'PRB0070862', 'PRB0070869', 'PRB0071148', 'PRB0071149', 
    'PRB0071228', 'PRB0071253', 'PRB0071604', 'PRB0071643', 'PRB0071665', 'PRB0071758', 
    'PRB0071783', 'PRB0071791', 'PRB0071961', 'PRB0071972', 'PRB0071979', 'PRB0071995', 
    'PRB0071997', 'PRB0072049', 'PRB0072062', 'PRB0072088', 'PRB0072104', 'PRB0072152', 
    'PRB0072162', 'PRB0072164', 'PRB0072175', 'PRB0072228', 'PRB0072260', 'PRB0072274', 
    'PRB0072311', 'PRB0072340', 'PRB0072363', 'PRB0072365', 'PRB0072384', 'PRB0072400', 
    'PRB0072524', 'PRB0072583', 'PRB0072648', 'PRB0072691', 'PRB0072705', 'PRB0072729', 
    'PRB0072738', 'PRB0072878', 'PRB0072925', 'PRB0073006', 'PRB0073007', 'PRB0073011', 
    'PRB0073051', 'PRB0073198', 'PRB0073350'
]

# 4. Conexão com o Banco de Dados PostgreSQL utilizando os parâmetros do config.ini
conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS
)
cur = conn.cursor()

def carregar_e_processar_historico():
    logger = configurar_logger()
    # Query que busca os dados brutos da tabela original do Service-Now
    query = """
        SELECT numero, data_encerrado, descricao_curta, descricao 
        FROM lwsa.service_now_problems
        WHERE numero = ANY(%s) AND data_encerrado IS NOT NULL;
    """
    
    cur.execute(query, (PRBS_ALVO,))
    prbs_encontrados = cur.fetchall()
    
    logger.info("Foram encontrados %s PRBs para processamento.", len(prbs_encontrados))
    
    for row in prbs_encontrados:
        prb_id = row[0]
        data_conclusao = row[1]
        descricao_curta = row[2] or ""
        descricao_longa = row[3] or ""
        
        logger.info("Processando IA para %s...", prb_id)
        
        # Prompt estruturado para extração do Gabarito Semântico
        prompt = f"""
        Analise o seguinte registro de problema (PRB) do Service-Now e extraia uma estrutura padronizada do sintoma principal enfrentado pelo cliente final.
        
        Título/Descrição Curta: {descricao_curta}
        Descrição Completa: {descricao_longa}
        
        Responda estritamente em formato JSON válido, sem markdown corporativo, seguindo exatamente este formato:
        {{
            "categoria": "Categoria macro do sistema (ex: Autenticação, E-mail, Banco de Dados, Painel)",
            "tag": "uma_unica_tag_resumida_em_snake_case",
            "descricao_resumida": "Resumo de uma linha sobre qual é o erro/sintoma gerado para o usuário",
            "termos_relacionados": ["lista", "de", "termos", "ou", "variantes", "do", "erro"]
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={ "type": "json_object" },
            messages=[{"role": "user", "content": prompt}]
        )
        
        gabarito = json.loads(response.choices[0].message.content)
        
        # Criação do texto combinando resumo + tags para vetorização
        texto_para_vetor = f"{gabarito['descricao_resumida']} {', '.join(gabarito['termos_relacionados'])}"
        
        # Geração do Embedding
        embedding_response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texto_para_vetor
        )
        embedding = embedding_response.data[0].embedding
        
        # Converte as listas e vetores em string JSON para salvar no Postgres 9.2
        embedding_json = json.dumps(embedding)
        termos_json = json.dumps(gabarito['termos_relacionados'])
        
        # --- SOLUÇÃO DE COMPATIBILIDADE PARA POSTGRES < 9.5 (Verificação Manual) ---
        cur.execute("SELECT 1 FROM lwsa.gabarito_prb WHERE prb_id = %s;", (prb_id,))
        existe = cur.fetchone()
        
        if existe:
            # Se o registro já existir, atualiza
            cur.execute("""
                UPDATE lwsa.gabarito_prb 
                SET data_conclusao = %s, categoria = %s, tag = %s, 
                    descricao_resumida = %s, termos_relacionados = %s, embedding_sintoma = %s
                WHERE prb_id = %s;
            """, (data_conclusao, gabarito['categoria'], gabarito['tag'], gabarito['descricao_resumida'], termos_json, embedding_json, prb_id))
        else:
            # Se não existir, insere um novo
            cur.execute("""
                INSERT INTO lwsa.gabarito_prb (prb_id, data_conclusao, categoria, tag, descricao_resumida, termos_relacionados, embedding_sintoma)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (prb_id, data_conclusao, gabarito['categoria'], gabarito['tag'], gabarito['descricao_resumida'], termos_json, embedding_json))
        
        conn.commit()
        logger.info("PRB %s estruturado e indexado com sucesso.", prb_id)

try:
    carregar_e_processar_historico()
except Exception as e:
    logging.exception("Erro na execucao da carga: %s", e)
finally:
    cur.close()
    conn.close()
    print("Processo de Carga Histórica Finalizado!")