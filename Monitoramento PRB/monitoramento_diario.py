import os
import json
import argparse
import configparser
import logging
import psycopg2
import numpy as np
from datetime import datetime, date, timedelta
from openai import OpenAI

# 1. Carregar as configurações do arquivo config.ini
config_path = r"C:\Users\emerson.ramos\Desktop\projetos\config.ini"
config = configparser.ConfigParser()
config.read(config_path, encoding='utf-8')

# Credenciais e parametros de conexao carregados do arquivo de configuracao.
DB_HOST = config.get('database', 'server')
DB_PORT = config.get('database', 'port', fallback='5432')
DB_NAME = config.get('database', 'database')
DB_USER = config.get('database', 'uid')
DB_PASS = config.get('database', 'pwd')
OPENAI_KEY = config.get('openai', 'api_key')

client = OpenAI(api_key=OPENAI_KEY)

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")


def configurar_logger():
    # Cria um logger de arquivo para registrar a execucao do monitoramento.
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("monitoramento_prb")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    log_path = os.path.join(LOG_DIR, f"monitoramento_diario_{datetime.now():%Y%m%d}.log")
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

# Preencha estes campos se quiser definir a data diretamente no codigo.
# Se ambos ficarem em branco, o monitoramento usa D-1.
DATA_INICIO_MANUAL = None  # Ex: "2026-06-10"
DATA_FIM_MANUAL = None     # Ex: "2026-06-15"


def parse_data_monitoramento(valor_data):
    # Converte a data informada pelo usuario ou usa ontem como padrao.
    if valor_data:
        return datetime.strptime(valor_data, "%Y-%m-%d").date()
    return date.today() - timedelta(days=1)


def parse_intervalo_monitoramento(data_inicio_str, data_fim_str):
    # Define o intervalo de validacao; se nada for informado, usa apenas D-1.
    if data_inicio_str and data_fim_str:
        data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
        data_fim = datetime.strptime(data_fim_str, "%Y-%m-%d").date()
    elif data_inicio_str:
        data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
        data_fim = data_inicio
    else:
        data_inicio = parse_data_monitoramento(None)
        data_fim = data_inicio

    if data_fim < data_inicio:
        raise ValueError("A data fim nao pode ser menor que a data inicio.")

    return data_inicio, data_fim


def parse_args():
    parser = argparse.ArgumentParser(description="Monitoramento diário de PRBs")
    parser.add_argument("--inicio", help="Data de início do período (YYYY-MM-DD)")
    parser.add_argument("--fim", help="Data de fim do período (YYYY-MM-DD)")
    parser.add_argument(
        "--historic",
        action="store_true",
        help="Ignora a regra de data de conclusão do gabarito para análise histórica."
    )
    return parser.parse_args()


def normalizar_origem_chat(canal):
    # Converte web para chat e mantém os demais canais como vierem.
    if not canal:
        return "chat"

    canal_normalizado = str(canal).strip().lower()
    if canal_normalizado == "web":
        return "chat"
    return canal_normalizado


def origem_ja_registrada(cur, origem_id):
    # Impede que o mesmo atendimento seja gravado mais de uma vez na tabela de reincidencia.
    cur.execute(
        "SELECT 1 FROM lwsa.ocorrencia_reincidencia WHERE origem_id = %s LIMIT 1;",
        (str(origem_id),),
    )
    return cur.fetchone() is not None

def carregar_gabaritos(cur):
    """Carrega todos os gabaritos ativos da tabela lwsa.gabarito_prb para a memória."""
    # Busca os PRBs conhecidos para comparar com os atendimentos capturados.
    cur.execute("SELECT prb_id, data_conclusao, descricao_resumida, embedding_sintoma FROM lwsa.gabarito_prb;")
    rows = cur.fetchall()
    gabaritos = []
    for r in rows:
        gabaritos.append({
            "prb_id": r[0],
            "data_conclusao": r[1],
            "descricao_resumida": r[2],
            "embedding": np.array(json.loads(r[3]))
        })
    return gabaritos

def coletar_atendimentos_periodo(cur, data_inicio, data_fim):
    """Busca interações de chats e chamados finalizados em um intervalo de datas."""
    atendimentos = []

    # Etapa 1: coleta chats encerrados dentro do periodo selecionado.
    query_chats = """
        SELECT 
            c.id::varchar AS "id",
            'chat' AS "tipo",
            c.canal AS "canal",
            COALESCE(ia.problema_principal, 'Atendimento Chat') AS "titulo",
            COALESCE(ia.resumo_final, '') AS "conteudo",
            c.data_fim_interacao AS "data_criacao"
        FROM lw_octadesk.chat c
        INNER JOIN lw_octadesk.classificacao_ia ia ON c.id::uuid = ia.chat_id
        WHERE c.data_fim_interacao >= %s
          AND c.data_fim_interacao < %s
          AND ia.resumo_final IS NOT NULL;
    """
    cur.execute(query_chats, (data_inicio, data_fim))
    for r in cur.fetchall():
        atendimentos.append({"id": r[0], "tipo": r[1], "canal": r[2], "titulo": r[3], "conteudo": r[4], "data_criacao": r[5]})

    # Etapa 2: coleta chamados encerrados dentro do mesmo periodo.
    query_chamados = """
        SELECT 
            ch.idchamado::varchar AS "id",
            'chamado' AS "tipo",
            COALESCE(ch.assunto, 'Atendimento Chamado') AS "titulo",
            COALESCE(ia_ch.resumo_final, '') AS "conteudo",
            ch.dataresolvido AS "data_criacao"
        FROM dynamics.chamados ch
        INNER JOIN dynamics.classificacao_ia_chamados ia_ch ON ch.idchamado = ia_ch.idchamado
        WHERE ch.dataresolvido >= %s
          AND ch.dataresolvido < %s
          AND ia_ch.resumo_final IS NOT NULL;
    """
    cur.execute(query_chamados, (data_inicio, data_fim))
    for r in cur.fetchall():
        atendimentos.append({"id": r[0], "tipo": r[1], "titulo": r[2], "conteudo": r[3], "data_criacao": r[4]})

    return atendimentos

def executar_processamento_diario(data_inicio_str=None, data_fim_str=None, historic_mode=False):
    # Define o periodo que sera analisado.
    logger = configurar_logger()
    data_inicio, data_fim = parse_intervalo_monitoramento(
        data_inicio_str or DATA_INICIO_MANUAL,
        data_fim_str or DATA_FIM_MANUAL,
    )
    data_fim_exclusiva = data_fim + timedelta(days=1)

    modo_texto = "HISTÓRICO" if historic_mode else "PROD"
    logger.info("--- Iniciando Processamento Diário Incremental (%s) ---", modo_texto)
    logger.info("Periodo configurado: %s ate %s", data_inicio.isoformat(), data_fim.isoformat())
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
    cur = conn.cursor()
    
    try:
        # Carrega os PRBs de referencia usados na comparacao.
        gabaritos = carregar_gabaritos(cur)
        if not gabaritos:
            logger.warning("Nenhum gabarito ativo encontrado na base.")
            return

        # Busca os atendimentos do periodo selecionado.
        if data_inicio == data_fim:
            logger.info("Varrendo as tabelas operacionais em busca de interacoes do dia %s...", data_inicio.isoformat())
        else:
            logger.info("Varrendo as tabelas operacionais em busca de interacoes de %s ate %s...", data_inicio.isoformat(), data_fim.isoformat())
        lista_atendimentos = coletar_atendimentos_periodo(cur, data_inicio, data_fim_exclusiva)
        total_itens = len(lista_atendimentos)
        logger.info("Total de atendimentos capturados para analise: %s", total_itens)

        if total_itens == 0:
            logger.warning("Nenhum atendimento finalizado no periodo selecionado.")
            return

        alertas_detectados = 0

        # Analisa cada atendimento e tenta identificar reincidencias.
        for idx, atendimento in enumerate(lista_atendimentos, 1):
            id_atendimento = atendimento['id']
            tipo_origem = atendimento['tipo']
            origem_tipo = normalizar_origem_chat(atendimento.get('canal')) if tipo_origem == 'chat' else tipo_origem
            texto_completo_cliente = f"{atendimento['titulo']} {atendimento['conteudo']}".strip()
            data_atendimento = atendimento['data_criacao']
            
            if not texto_completo_cliente:
                continue

            # Camada 1: Busca Semântica por Embeddings
            emb_resp = client.embeddings.create(model="text-embedding-3-small", input=texto_completo_cliente)
            emb_atendimento = np.array(emb_resp.data[0].embedding)
            
            for gabarito in gabaritos:
                # Regra de Ouro: Ignora se o atendimento ocorreu antes ou no mesmo dia do PRB resolvido,
                # exceto em modo historico, quando queremos comparar o histórico anterior à força tarefa.
                if not historic_mode and data_atendimento <= gabarito['data_conclusao']:
                    continue
                
                # Calcula a similaridade entre o atendimento e o gabarito salvo.
                similarity = np.dot(emb_atendimento, gabarito['embedding']) / (
                    np.linalg.norm(emb_atendimento) * np.linalg.norm(gabarito['embedding'])
                )
                
                if similarity >= 0.72:
                    # Camada 2: valida com LLM para reduzir falsos positivos.
                    prompt_valida = f"""
                    O cliente relatou o seguinte em um atendimento: "{texto_completo_cliente}"
                    Este sintoma é EXATAMENTE o mesmo erro técnico descrito neste padrão resolvido: "{gabarito['descricao_resumida']}"?
                    Responda estritamente em formato JSON válido:
                    {{"reincidente": true/false, "confianca": 0.00 a 1.00, "justificativa": "breve motivo técnico"}}
                    """
                    res = client.chat.completions.create(
                        model="gpt-4o-mini",
                        response_format={ "type": "json_object" },
                        messages=[{"role": "user", "content": prompt_valida}]
                    )
                    resultado_ia = json.loads(res.choices[0].message.content)
                    
                    if resultado_ia.get('reincidente') is True:
                        if origem_ja_registrada(cur, id_atendimento):
                            logger.warning("Atendimento %s ja existe em ocorrencia_reincidencia; gravacao ignorada.", id_atendimento)
                            continue

                        # Grava o alerta de reincidencia no banco.
                        cur.execute("""
                            INSERT INTO lwsa.ocorrencia_reincidencia 
                            (prb_id, origem_tipo, origem_id, data_ocorrencia, texto_analisado, score_similaridade, score_confianca_llm, justificativa_ia)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                        """, (
                            gabarito['prb_id'], origem_tipo, str(id_atendimento), data_atendimento, 
                            texto_completo_cliente[:1000], float(similarity), float(resultado_ia.get('confianca', 0)), resultado_ia.get('justificativa', '')
                        ))
                        conn.commit()
                        alertas_detectados += 1
                        logger.info("[%s/%s] Alerta gravado. Reincidencia de %s encontrada no evento %s.", idx, total_itens, gabarito['prb_id'], id_atendimento)
                        
        # Exibe o resultado final do processamento.
        logger.info("--- Rotina finalizada com sucesso. Alertas totais gravados: %s ---", alertas_detectados)
        
    except Exception as e:
        # Mostra qualquer erro inesperado durante a rotina.
        logger.exception("Erro critico durante a execucao: %s", e)
    finally:
        # Fecha cursor e conexao para liberar os recursos.
        cur.close()
        conn.close()

if __name__ == "__main__":
    args = parse_args()
    executar_processamento_diario(
        data_inicio_str=args.inicio,
        data_fim_str=args.fim,
        historic_mode=args.historic,
    )