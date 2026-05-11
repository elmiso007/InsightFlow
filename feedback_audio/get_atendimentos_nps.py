import pandas as pd
import sqlalchemy
from sqlalchemy import text
import re
import sys
import json
import psycopg2
import logging
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime, timedelta
from conecta_banco import *

# Configurar logger
logger = logging.getLogger('nps_monitor.atendimentos')

def get_atendimentos_nps(analistas_criticos, data_inicio=None, data_fim=None):
    """
    Busca atendimentos dos analistas que estão com NPS abaixo da meta
    
    Args:
        analistas_criticos: DataFrame com analistas críticos
        data_inicio: Data de início para filtrar (opcional)
        data_fim: Data de fim para filtrar (opcional)
    
    Returns:
        tuple: (conteudo_txt, lista_protocolos_unicos)
    """
    
    def dados_sensiveis(interacoes):
        """Função para anonimizar dados sensíveis nas conversas"""
        
        # Remover tags HTML
        interacoes = BeautifulSoup(interacoes, "html.parser").get_text()

        # Remover asteriscos ao redor de palavras
        interacoes = re.sub(r'\*(\w+)\*', r'\1', interacoes)

        # Anonimizar e-mails
        texto_anonimizado = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zAlo]{2,}', '[email]', interacoes)
        
        # Anonimizar CPFs
        texto_anonimizado = re.sub(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', '[CPF]', texto_anonimizado)
        
        # Anonimizar CNPJs
        texto_anonimizado = re.sub(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b', '[CNPJ]', texto_anonimizado)

        # Anonimizar telefones
        texto_anonimizado = re.sub(r'\b(\(?\d{2}\)?\s?)?9?\d{4}[-.]?\d{4}\b', '[telefone]', texto_anonimizado)

        # Ocultar sequências de IP
        texto_anonimizado = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP]', texto_anonimizado)

        # Oculta a apresentação do BOT para evitar confusões da LLM 
        texto_anonimizado = re.sub(r'Olá! Sou o WOZ', '[assistente]', texto_anonimizado)

        # Ocultar sequências de Subdomínios
        texto_anonimizado = re.sub(r'\b[a-zA-Z]\d+-[a-zA-Z0-9]+\b', '[subdomínio]', texto_anonimizado)

        # Ocultar códigos de barras (sequências de 12 a 14 dígitos)
        texto_anonimizado = re.sub(r'\b\d{12,14}\b', '[codigo_de_barras]', texto_anonimizado)

        # Ocultar links com http:// ou https://
        texto_anonimizado = re.sub(r'http[s]?://\S+', '[link]', texto_anonimizado)

        # Ocultar nomes de domínios (após 'http://', 'https://', ou outros casos)
        texto_anonimizado = re.sub(r'(?<=//)[a-zA-Z0-9.-]+', '[dominio]', texto_anonimizado)

        # Ocultar nomes de domínios com 'www.' explicitamente
        texto_anonimizado = re.sub(r'\bwww\.[a-zA-Z0-9.-]+', '[dominio]', texto_anonimizado)

        # Remover tags HTML
        texto_anonimizado = re.sub(r'<[^>]+>', '', texto_anonimizado)

        # Remove quebras de linha
        texto_anonimizado = re.sub(r'[\r\n]+', ' ', texto_anonimizado).strip()

        # Ocultar domínios com padrões específicos
        texto_anonimizado = re.sub(r'\b[a-zA-Z0-9.-]+(?:\.com\.br|\.gov\.br|\.org\.br|\.edu\.br|\.com|\.br|\.net|\.org|\.info|\.tech|\.xyz|\.tv|\.me|\.app)\b', '[dominio]', texto_anonimizado)

        # Anonimizar nomes de empresas específicas
        texto_anonimizado = re.sub(r'Kinghost|KINGHOST|kinghost|KingHost', '[empresa]', texto_anonimizado)

        # Anonimizar nomes de empresas concorrentes
        texto_anonimizado = re.sub(r'Octadesk|octadesk|OCTADESK|OCTA|octa|Octa|hostinger|Hostinger|HOSTINGER|Godaddy|godaddy|GODADDY|HOSTGATOR|hostgator|Hostgator|WIX|wix|Wix|Hostnet|hostnet|HOSTNET|cloudflare|Cloudflare|CLOUDFLARE|nuvemshop|NUVEMSHOP|Nuvemshop', '[concorrente]', texto_anonimizado)
        
        # Ocultar dados após termos sensíveis como "login", "senha", "usuário"
        texto_anonimizado = re.sub(r'(O seu usuário é: \s*)\S+', r'\1[usuário]', texto_anonimizado)
        texto_anonimizado = re.sub(r'(login\s*[:\s]?\s*)\S+', r'\1[login]', texto_anonimizado)
        texto_anonimizado = re.sub(r'(usuário\s*[:\s]?\s*)\S+', r'\1[usuario]', texto_anonimizado)
        texto_anonimizado = re.sub(r'(senha\s*[:\s]?\s*)\S+', r'\1[senha]', texto_anonimizado)

        # Ocultar palavrões (adicione mais conforme necessário)
        lista_palavroes = [
            "vagabundo", "merda", "puta", "caralho", "porra", "desgraça"
        ]
        
        for palavrao in lista_palavroes:
            texto_anonimizado = re.sub(rf'\b{palavrao}\b', '[palavrão]', texto_anonimizado, flags=re.IGNORECASE)

        return texto_anonimizado

    # Preparar lista de analistas
    if hasattr(analistas_criticos, 'index'):
        # Se for DataFrame
        lista_analistas = list(analistas_criticos.index)
    else:
        # Se for lista
        lista_analistas = list(analistas_criticos)
    
    if not lista_analistas:
        logger.warning("Nenhum analista crítico encontrado.")
        return [], []
    
    # Conectar ao banco - será fechado no finally
    engine = None
    conn = None

    # Converter lista de analistas para string SQL
    analistas_sql = "', '".join(lista_analistas)
    
    # Definir período de busca
    if not data_inicio:
        # Buscar últimos 30 dias se não especificado
        data_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not data_fim:
        data_fim = datetime.now().strftime('%Y-%m-%d')

    logger.info(f"Buscando atendimentos dos analistas: {', '.join(lista_analistas)}")
    logger.info(f"Período: {data_inicio} a {data_fim}")
    
    try:
        # Estabelecer conexões
        engine = get_sqlalchemy_engine()
        conn = get_psycopg2_connection()

        query = f'''
        SELECT
            rd."Protocolo",
            rd."Analista",
            rd."Data Encerramento" as data_encerramento,
            rd."Canal",
            rd."Velocidade",
            rd."Solução" as solucao,
            rd."Relacionamento",
            rd."Comentários" as comentarios,
            nps."ID Sessão" as id_sessao,
            nps."Data e Hora da Pesquisa" as data_hora_pesquisa,
            nps."Login do Analista" as login_analista_nps,
            m.mensagens
        FROM kinghost_octadesk.vw_report_diario rd
        INNER JOIN kinghost_octadesk.vw_nps nps ON CAST(rd."Protocolo" AS BIGINT) = nps."Protocolo"
        LEFT JOIN kinghost_octadesk.mensagens m ON nps."ID Sessão" = m.id
        WHERE rd."Analista" IN ('{analistas_sql}')
        AND rd."Data Encerramento" BETWEEN '{data_inicio}' AND '{data_fim} 23:59:59'
        ORDER BY rd."Data Encerramento" DESC;
        '''

        logger.info("Executando consulta no banco...")
        df = pd.read_sql(query, conn)
        
        if df.empty:
            logger.warning("Nenhum atendimento encontrado para os analistas especificados.")
            return [], []

        logger.info(f"Encontrados {len(df)} registros com avaliações NPS dos analistas críticos.")

        # Processar mensagens
        df_mensagem = df[['Protocolo', 'Analista', 'id_sessao', 'Canal', 'Velocidade', 'solucao', 'Relacionamento', 'comentarios', 'mensagens', 'data_encerramento']]
        lista_protocolos_unicos = df_mensagem['Protocolo'].dropna().unique().tolist()

        conteudo_txt = []
        arquivo_txt = Path(__file__).parent / 'atendimentos_nps_baixo.txt'

        # Adicionar cabeçalho informativo padronizado
        conteudo_txt.append("=" * 120 + "\n")
        conteudo_txt.append("🎯 RELATÓRIO DE ANÁLISE NPS - ANALISTAS COM PERFORMANCE CRÍTICA\n")
        conteudo_txt.append("=" * 120 + "\n")
        conteudo_txt.append(f"📅 PERÍODO: {data_inicio} até {data_fim}\n")
        conteudo_txt.append(f"👥 ANALISTAS IDENTIFICADOS: {', '.join(lista_analistas)}\n")
        conteudo_txt.append(f"🔍 TOTAL DE REGISTROS COM NPS: {len(df)}\n")
        conteudo_txt.append(f"⚠️  META NPS: ≥ 70 (todos os analistas abaixo estão com pelo menos uma nota abaixo da meta)\n")
        conteudo_txt.append("=" * 120 + "\n\n")

        # Processar por analista para manter organização
        for analista in lista_analistas:
            # Filtrar dados apenas deste analista
            df_analista = df_mensagem[df_mensagem['Analista'] == analista].copy()
            
            if df_analista.empty:
                continue
                
            # Cabeçalho do analista
            conteudo_txt.append("\n" + "🔥" * 50 + "\n")
            conteudo_txt.append(f"👤 ANALISTA: {analista.upper()}\n")
            conteudo_txt.append(f"📊 TOTAL DE ATENDIMENTOS: {len(df_analista)}\n")
            conteudo_txt.append("🔥" * 50 + "\n\n")
            
            # Processar cada atendimento do analista
            for _, row in df_analista.iterrows():
                protocolo = row['Protocolo']
                id_sessao = row['id_sessao']
                canal = row['Canal']
                velocidade = row['Velocidade']
                solucao = row['solucao']
                relacionamento = row['Relacionamento']
                comentarios_nps = row['comentarios']
                mensagens = row['mensagens']
                data_encerramento = row['data_encerramento']

                try:
                    # =============================================================================
                    # CABEÇALHO PADRONIZADO DO ATENDIMENTO
                    # =============================================================================
                    conteudo_txt.append("\n" + "=" * 100 + "\n")
                    conteudo_txt.append(f"PROTOCOLO: {protocolo}\n")
                    conteudo_txt.append(f"ANALISTA: {analista}\n")
                    conteudo_txt.append(f"CANAL: {canal} | DATA ENCERRAMENTO: {data_encerramento}\n")
                    conteudo_txt.append(f"ID SESSÃO: {id_sessao}\n")
                    conteudo_txt.append("-" * 100 + "\n")
                    
                    # NOTAS NPS (DESTAQUE ESPECIAL)
                    conteudo_txt.append("📊 AVALIAÇÃO NPS:\n")
                    conteudo_txt.append(f"   • VELOCIDADE: {velocidade}/10\n")
                    conteudo_txt.append(f"   • SOLUÇÃO: {solucao}/10\n") 
                    conteudo_txt.append(f"   • RELACIONAMENTO: {relacionamento}/10\n")
                    
                    # COMENTÁRIO NPS (SE EXISTIR)
                    if comentarios_nps and str(comentarios_nps).strip():
                        conteudo_txt.append(f"💬 COMENTÁRIO DO CLIENTE: {comentarios_nps}\n")
                    
                    conteudo_txt.append("-" * 100 + "\n")
                    conteudo_txt.append("🗣️ CONVERSA COMPLETA:\n")
                    conteudo_txt.append("-" * 100 + "\n")

                    # Processar mensagens - pode vir como string JSON ou já como objeto Python
                    mensagens_json = None
                    
                    if mensagens is not None:
                        # Se já vier como lista/dict do pandas
                        if isinstance(mensagens, (list, dict)):
                            mensagens_json = mensagens if isinstance(mensagens, list) else [mensagens]
                        # Se vier como string JSON
                        elif isinstance(mensagens, str) and mensagens.strip():
                            try:
                                mensagens_json = json.loads(mensagens)
                            except json.JSONDecodeError as e:
                                logger.warning(f"Erro ao decodificar JSON para protocolo {protocolo}: {e}")
                    
                    # Verificar se há mensagens válidas para processar
                    if mensagens_json and isinstance(mensagens_json, list) and len(mensagens_json) > 0:
                        # Contador de mensagens para melhor organização
                        contador_msg = 1

                        for msg in mensagens_json:
                            # Valida se os campos necessários estão presentes
                            if all(k in msg for k in ['sentBy', 'time', 'body']):
                                try:
                                    # Determina o autor com base no tipo de remetente
                                    tipo_remetente = msg.get('sentBy', {}).get('type', '')
                                    
                                    # Padronização dos rótulos
                                    if tipo_remetente == 'contact':
                                        author_formatado = "C"
                                    else:
                                        author_formatado = "A"

                                    # Aplica anonimização ou limpeza de dados sensíveis
                                    dados_ocultos = dados_sensiveis(msg['body'])

                                    # Monta a linha de texto formatada de forma simples
                                    conteudo_txt.append(f"{author_formatado}: {dados_ocultos}\n")
                                    
                                    contador_msg += 1
                                    
                                except Exception as e:
                                    # Loga erros de formatação específicos
                                    logger.warning(f"Erro ao processar mensagem individual: {str(e)}")
                            else:
                                # Loga mensagens com estrutura inválida
                                logger.debug(f"Mensagem com estrutura inesperada ignorada")

                        # RODAPÉ DO ATENDIMENTO
                        conteudo_txt.append("-" * 100 + "\n")
                        conteudo_txt.append("=" * 100 + "\n\n")
                        
                    else:
                        # Se não há mensagens, ainda mostra informações do NPS
                        conteudo_txt.append("⚠️  NENHUMA CONVERSA ENCONTRADA PARA ESTE PROTOCOLO\n")
                        conteudo_txt.append("=" * 100 + "\n\n")
                
                except Exception as e:
                    # Loga erros gerais de processamento
                    logger.error(f"Erro ao processar protocolo {protocolo}: {str(e)}")
                    # Ainda assim, registra as informações de NPS
                    conteudo_txt.append("❌ ERRO AO PROCESSAR ATENDIMENTO\n")
                    conteudo_txt.append("=" * 100 + "\n\n")
            
            # Separador entre analistas
            conteudo_txt.append("\n" + "🔥" * 50 + "\n")
            conteudo_txt.append(f"✅ FIM DOS ATENDIMENTOS DE {analista.upper()}\n")
            conteudo_txt.append("🔥" * 50 + "\n\n")

        # Salva os dados no arquivo TXT
        with open(arquivo_txt, 'w', encoding='utf-8') as arquivo:
            arquivo.writelines(conteudo_txt)

        logger.info(f"Atendimentos exportados para {arquivo_txt}")
        
        return conteudo_txt, lista_protocolos_unicos
    
    except psycopg2.OperationalError as e:
        logger.error(f"Erro de conexão com banco de dados: {str(e)}")
        raise
    except psycopg2.DatabaseError as e:
        logger.error(f"Erro de banco de dados: {str(e)}")
        raise
    except pd.errors.DatabaseError as e:
        logger.error(f"Erro ao executar query no pandas: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao processar JSON de mensagens: {str(e)}")
        raise
    except IOError as e:
        logger.error(f"Erro ao salvar arquivo TXT: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado em get_atendimentos_nps: {str(e)}")
        logger.exception("Detalhes do erro:")
        raise
    finally:
        # Garantir que conexões sejam fechadas independentemente do resultado
        if conn is not None:
            try:
                conn.close()
                logger.debug("Conexão fechada (get_atendimentos_nps)")
            except Exception as e:
                logger.warning(f"Erro ao fechar conexão: {str(e)}")
        
        if engine is not None:
            try:
                engine.dispose()
                logger.debug("Engine disposed (get_atendimentos_nps)")
            except Exception as e:
                logger.warning(f"Erro ao fazer dispose da engine: {str(e)}")


def get_estatisticas_analistas(analistas_criticos, data_inicio=None, data_fim=None):
    """
    Busca estatísticas dos atendimentos dos analistas críticos
    
    Args:
        analistas_criticos: Lista ou DataFrame com analistas críticos
        data_inicio: Data de início para filtrar (opcional)
        data_fim: Data de fim para filtrar (opcional)
    
    Returns:
        DataFrame: Estatísticas dos analistas
    """
    
    # Preparar lista de analistas
    if hasattr(analistas_criticos, 'index'):
        lista_analistas = list(analistas_criticos.index)
    else:
        lista_analistas = list(analistas_criticos)
    
    if not lista_analistas:
        logger.warning("Nenhum analista crítico encontrado para estatísticas.")
        return pd.DataFrame()

    # Converter lista de analistas para string SQL
    analistas_sql = "', '".join(lista_analistas)
    
    # Definir período de busca
    if not data_inicio:
        data_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not data_fim:
        data_fim = datetime.now().strftime('%Y-%m-%d')

    # Conectar ao banco - será fechado no finally
    engine = None
    conn = None
    
    try:
        # Estabelecer conexões
        engine = get_sqlalchemy_engine()
        conn = get_psycopg2_connection()

        query = f'''
        SELECT
            rd."Analista",
            COUNT(*) AS total_avaliacoes_nps,
            COUNT(DISTINCT rd."Protocolo") AS protocolos_unicos,
            AVG(CAST(rd."Velocidade" AS FLOAT)) AS media_velocidade,
            AVG(CAST(rd."Solução" AS FLOAT)) AS media_solucao,
            AVG(CAST(rd."Relacionamento" AS FLOAT)) AS media_relacionamento,
            rd."Canal",
            COUNT(CASE WHEN m.mensagens IS NOT NULL THEN 1 END) AS registros_com_mensagens
        FROM kinghost_octadesk.vw_report_diario rd
        INNER JOIN kinghost_octadesk.vw_nps nps ON CAST(rd."Protocolo" AS BIGINT) = nps."Protocolo"
        LEFT JOIN kinghost_octadesk.mensagens m ON nps."ID Sessão" = m.id
        WHERE rd."Analista" IN ('{analistas_sql}')
        AND rd."Data Encerramento" BETWEEN '{data_inicio}' AND '{data_fim} 23:59:59'
        GROUP BY rd."Analista", rd."Canal"
        ORDER BY total_avaliacoes_nps DESC;
        '''

        logger.info("Buscando estatísticas dos analistas...")
        df_stats = pd.read_sql(query, conn)
        
        return df_stats
    
    except psycopg2.OperationalError as e:
        logger.error(f"Erro de conexão com banco de dados (estatísticas): {str(e)}")
        raise
    except psycopg2.DatabaseError as e:
        logger.error(f"Erro de banco de dados (estatísticas): {str(e)}")
        raise
    except pd.errors.DatabaseError as e:
        logger.error(f"Erro ao executar query de estatísticas: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado em get_estatisticas_analistas: {str(e)}")
        logger.exception("Detalhes do erro:")
        raise
    finally:
        # Garantir que conexões sejam fechadas independentemente do resultado
        if conn is not None:
            try:
                conn.close()
                logger.debug("Conexão fechada (get_estatisticas_analistas)")
            except Exception as e:
                logger.warning(f"Erro ao fechar conexão: {str(e)}")
        
        if engine is not None:
            try:
                engine.dispose()
                logger.debug("Engine disposed (get_estatisticas_analistas)")
            except Exception as e:
                logger.warning(f"Erro ao fazer dispose da engine: {str(e)}")

