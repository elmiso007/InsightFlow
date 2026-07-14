import pandas as pd
import json
import slack_sdk as sd
import sys
from datetime import datetime, timedelta
import locale
from sqlalchemy import text
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import holidays
import uuid
import re
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import psycopg2
from config import config
from conecta_banco import *
from analise_ia import analise_ia_nps, analise_comparativa_nps, limpar_rawdata_antigos, analise_ja_existe, executar_sql_pos_analise
from get_atendimentos_nps import get_atendimentos_analista_individual, get_estatisticas_analistas

sql_path = Path(__file__).parent

#|-------------------------------------------------------------------------------------------------------------------|

# CONFIGURAÇÃO DE LOGGING

def setup_logging():
    """Configura o sistema de logging estruturado"""
    
    # Criar diretório de logs se não existir
    logs_dir = sql_path / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Configurar formatação
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configurar logger principal
    logger = logging.getLogger('nps_monitor')
    logger.setLevel(logging.DEBUG)
    
    # Handler para arquivo com rotação (usando config)
    log_file = logs_dir / "nps_verificacao.log"
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=config.LOG_MAX_SIZE_MB*1024*1024,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, config.LOG_FILE_LEVEL))
    file_handler.setFormatter(formatter)
    
    # Handler para console (usando config)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.LOG_CONSOLE_LEVEL))
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # Adicionar handlers ao logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Inicializar logging
logger = setup_logging()

#|-------------------------------------------------------------------------------------------------------------------|

# VARIÁVEIS DE DATA E HORA PARA QUERY E PARA CÁLCULO DO PERÍODO

task = 'monitoramento_nps_analistas'

# Obter a data e hora atuais
data_hoje = datetime.now().date()
hora_atual = datetime.now()
hora_atual_formatada = hora_atual.strftime("%H:%M:%S")
current_time = datetime.now()

# Calcular primeiro e último dia do mês anterior
primeiro_dia_mes_atual = data_hoje.replace(day=1)
ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
primeiro_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)

# Formatação para uso na query SQL
data_inicio_analise = primeiro_dia_mes_anterior.strftime('%Y-%m-%d')
data_fim_analise = ultimo_dia_mes_anterior.strftime('%Y-%m-%d')

logger.info(f"Executando verificação de NPS em {data_hoje} às {hora_atual_formatada}")
logger.info(f"Período de análise: {data_inicio_analise} até {data_fim_analise} (mês anterior)")

# Determinar tipo do dia (apenas para logging)
feriados_brasil = holidays.Brazil()
if data_hoje.weekday() < 5 and data_hoje not in feriados_brasil:
    tipo_dia = "dia útil"
    dia_util = True
else:
    tipo_dia = "fim de semana/feriado"
    dia_util = False

logger.debug(f"Tipo do dia: {tipo_dia}")

#|-------------------------------------------------------------------------------------------------------------------|

# FUNÇÕES

def notifica_boas_noticias(mensagem):
    """Função para notificar boas notícias sobre NPS"""
    logger.info("=== NOTIFICAÇÃO DE BOAS NOTÍCIAS ===")
    logger.info(f"Mensagem: {mensagem[:200]}...")  # Limita tamanho para log
    logger.info("=====================================")

def notifica(mensagem, analistas_criticos, total_analistas):
    """Função para notificar problemas de NPS"""
    logger.warning("=== NOTIFICAÇÃO DE ALERTA ===")
    logger.warning(f"Analistas críticos: {analistas_criticos}/{total_analistas}")
    logger.warning(f"Mensagem de alerta: {mensagem[:200]}...")  # Limita tamanho para log
    logger.warning("=============================")

def gerar_chave_unica():
    return str(uuid.uuid4())

def processar_analista_individual(analista_nome, comentarios_criticos, data_inicio, data_fim, setores_analistas, idx, total):
    """Thread-safe: busca dados de UM analista e executa análise de IA."""
    logger.info(f"[{idx}/{total}] Iniciando {analista_nome}...")

    comentarios_analista = comentarios_criticos[
        comentarios_criticos['Analista'] == analista_nome
    ].copy()

    if comentarios_analista.empty:
        logger.warning(f"[{idx}/{total}] {analista_nome}: nenhum comentário NPS")
        return analista_nome, None, []

    if analise_ja_existe(analista_nome, data_inicio, data_fim):
        logger.info(f"[{idx}/{total}] ⏭ {analista_nome}: análise já existe para {data_inicio}~{data_fim}, pulando")
        return analista_nome, "PULADO", []

    atendimentos_txt, protocolos_analista = get_atendimentos_analista_individual(
        analista_nome, data_inicio, data_fim
    )

    texto_analista = f"=== ANÁLISE ESPECÍFICA: {analista_nome.upper()} ===\n"
    texto_analista += f"Período: {data_inicio} até {data_fim}\n"
    texto_analista += f"Total de comentários NPS: {len(comentarios_analista)}\n\n"

    for _, row in comentarios_analista.iterrows():
        texto_analista += f"Protocolo: {row['Protocolo']}\n"
        texto_analista += f"Notas NPS: Velocidade={row['Velocidade']}, Solução={row['Solução']}, Relacionamento={row['Relacionamento']}\n"
        texto_analista += f"Comentário: {row['Comentários']}\n"
        texto_analista += "-" * 80 + "\n"

    if atendimentos_txt:
        texto_analista += "\n=== CONVERSAS COMPLETAS ===\n"
        texto_analista += "".join(atendimentos_txt[:5000])

    setor = setores_analistas.get(analista_nome, 'Não identificado')
    if not protocolos_analista:
        protocolos_analista = list(comentarios_analista['Protocolo'].dropna().unique())

    analise = analise_ia_nps(
        texto_analista, data_inicio, data_fim,
        [analista_nome], protocolos_analista, setor
    )

    if analise and not analise.startswith("Erro:"):
        logger.info(f"[{idx}/{total}] ✓ {analista_nome} concluído")
    else:
        logger.error(f"[{idx}/{total}] ✗ {analista_nome} falhou")

    return analista_nome, analise, protocolos_analista


def extrair_setores_analistas(df):
    """Extrai os setores dos analistas do DataFrame"""
    setores_por_analista = {}
    
    for analista in df['Analista'].unique():
        # Pegar o setor mais frequente do analista (em caso de múltiplos setores)
        dados_analista = df[df['Analista'] == analista]
        setor = dados_analista['Setor'].mode()
        
        if len(setor) > 0:
            setores_por_analista[analista] = setor[0]
        else:
            setores_por_analista[analista] = 'Não identificado'
    
    return setores_por_analista

def calcular_nps_nota(serie_notas):
    """Calcula NPS para uma série de notas seguindo a fórmula padrão"""
    if len(serie_notas) == 0:
        return None
    
    # Remover valores nulos
    notas_validas = serie_notas.dropna()
    if len(notas_validas) == 0:
        return None
    
    # Contar promotores, neutros e detratores
    promotores = len(notas_validas[notas_validas >= 9])
    detratores = len(notas_validas[notas_validas <= 6])
    neutros = len(notas_validas[(notas_validas > 6) & (notas_validas < 9)])
    total_respostas = len(notas_validas)
    
    # Calcular NPS
    diferenca = promotores - detratores
    
    if total_respostas == 0:
        return None
    
    if diferenca == 0 and neutros > 0:
        return 0.0
    
    resultado = (diferenca * 100) / total_respostas
    return round(resultado, 2)

def calcular_nps_analistas(df):
    """Calcula NPS para Velocidade, Solução, Relacionamento por Analista usando a fórmula padrão"""
    resultados = []
    
    for analista in df['Analista'].unique():
        dados_analista = df[df['Analista'] == analista]
        
        # Calcular NPS para cada pergunta
        nps_velocidade = calcular_nps_nota(dados_analista['Velocidade'])
        nps_solucao = calcular_nps_nota(dados_analista['Solução'])
        nps_relacionamento = calcular_nps_nota(dados_analista['Relacionamento'])
        
        # Contar total de avaliações
        total_avaliacoes = len(dados_analista)
        
        resultados.append({
            'Analista': analista,
            'NPS_Velocidade': nps_velocidade,
            'NPS_Solucao': nps_solucao,
            'NPS_Relacionamento': nps_relacionamento,
            'Total_Avaliacoes': total_avaliacoes
        })
    
    df_nps = pd.DataFrame(resultados).set_index('Analista')
    return df_nps

def identificar_analistas_criticos(df_nps, meta_nps=None, min_avaliacoes=None):
    """Identifica analistas com NPS abaixo da meta e número mínimo de avaliações"""
    # Usar configurações do .env se não fornecidas
    if meta_nps is None:
        meta_nps = config.NPS_META
    if min_avaliacoes is None:
        min_avaliacoes = config.NPS_MIN_AVALIACOES
    
    analistas_criticos = []
    
    for analista, dados in df_nps.iterrows():
        if dados['Total_Avaliacoes'] >= min_avaliacoes:
            # Verificar se algum NPS está abaixo da meta
            nps_valores = [dados['NPS_Velocidade'], dados['NPS_Solucao'], dados['NPS_Relacionamento']]
            nps_validos = [nps for nps in nps_valores if nps is not None]
            
            if nps_validos:  # Se tem pelo menos um NPS calculado
                # Verifica se algum NPS está abaixo da meta
                if any(nps < meta_nps for nps in nps_validos):
                    analistas_criticos.append(analista)
    
    df_criticos = df_nps.loc[analistas_criticos] if analistas_criticos else pd.DataFrame()
    return df_criticos

def analisar_comentarios_negativos(df, analistas_criticos):
    """Analisa comentários de analistas com NPS baixo"""
    df_comentarios = df[
        (df['Analista'].isin(analistas_criticos.index)) &
        (df['Comentários'].notna()) &
        (df['Comentários'].str.strip() != '')
    ]
    
    return df_comentarios[['Analista', 'Protocolo', 'Velocidade', 'Solução', 'Relacionamento', 'Comentários', 'Data Encerramento']]

#|-------------------------------------------------------------------------------------------------------------------|

# QUERY E CONEXÃO COM O BANCO

logger.info("Conectando ao banco de dados...")

query = f"""
SELECT 
    "Protocolo",
    "Analista",
    "Fila",
    "Setor",
    "Produto",
    "Cliente",
    "Data Encerramento",
    "Tempo de Espera",
    "Tempo de Atendimento",
    "Status",
    "Login Cliente",
    "Canal",
    "Velocidade",
    "Solução",
    "Relacionamento",
    "Comentários",
    "Ultima Semana",    
    "data"
FROM kinghost_octadesk.vw_report_diario
WHERE "Data Encerramento" >= '{data_inicio_analise}' 
    AND "Data Encerramento" <= '{data_fim_analise} 23:59:59'
    AND ("Velocidade" IS NOT NULL OR "Solução" IS NOT NULL OR "Relacionamento" IS NOT NULL)
ORDER BY "Data Encerramento" DESC;
"""

# Inicializar variáveis de conexão - serão fechadas no finally
engine = None
conn = None

try:
    # Estabelecer conexões
    engine = get_sqlalchemy_engine()
    conn = get_psycopg2_connection()
    
    logger.info("Executando query...")
    df = pd.read_sql(query, conn)
    logger.info(f"Registros encontrados: {len(df)}")
    
    # Verifica se o DataFrame está vazio antes de continuar
    if df.empty:
        logger.error("Nenhum dado de NPS retornado da consulta. Interrompendo a execução.")
        sys.exit(1)
        
    #|-------------------------------------------------------------------------------------------------------------------|
    
    # ANÁLISE DOS DADOS DE NPS
    
    logger.info("=== ANÁLISE DE NPS DOS ANALISTAS ===")
    
    # Converter datas
    df['Data Encerramento'] = pd.to_datetime(df['Data Encerramento'])
    
    # Calcular NPS por analista usando a fórmula padrão
    df_nps_analistas = calcular_nps_analistas(df)
    logger.info(f"Total de analistas avaliados: {len(df_nps_analistas)}")
    
    # Identificar analistas abaixo da meta (usando configurações do .env)
    analistas_criticos = identificar_analistas_criticos(df_nps_analistas)
    logger.info(f"Meta NPS configurada: {config.NPS_META} | Mín. avaliações: {config.NPS_MIN_AVALIACOES}")
    
    # Extrair setores dos analistas
    setores_analistas = extrair_setores_analistas(df)
    logger.debug(f"Setores identificados: {setores_analistas}")
    
    logger.info(f"Analistas com NPS abaixo da meta (< 70): {len(analistas_criticos)}")
    
    if not analistas_criticos.empty:
        logger.warning(f"=== ANALISTAS COM NPS ABAIXO DA META === Total: {len(analistas_criticos)} analistas")
        
        # Analisar comentários dos analistas críticos
        comentarios_criticos = analisar_comentarios_negativos(df, analistas_criticos)
        
        # Obter estatísticas dos analistas (query de agregação — permanece em bulk)
        stats_analistas = get_estatisticas_analistas(analistas_criticos, data_inicio_analise, data_fim_analise)

        if not stats_analistas.empty:
            logger.info(f"=== ESTATÍSTICAS DOS ANALISTAS CRÍTICOS === Total: {len(stats_analistas)} analistas processados")

        if not comentarios_criticos.empty:
            logger.info("=== COMENTÁRIOS DOS ANALISTAS COM NPS BAIXO ===")
            logger.info(f"Encontrados {len(comentarios_criticos)} comentários para análise")

            fila_analistas = list(analistas_criticos.index)
            total_analistas = len(fila_analistas)
            logger.info(f"=== INICIANDO ANÁLISE POR ANALISTA ({config.PARALELO_MAX_WORKERS} worker(s) paralelo(s)) ===")
            logger.info(f"Total de analistas na fila: {total_analistas}")

            content = ""
            resultados_analistas = {}
            protocolos_analistas = []
            analistas_processados = 0

            with ThreadPoolExecutor(max_workers=config.PARALELO_MAX_WORKERS) as executor:
                futures = {
                    executor.submit(
                        processar_analista_individual,
                        nome,
                        comentarios_criticos,
                        data_inicio_analise,
                        data_fim_analise,
                        setores_analistas,
                        idx + 1,
                        total_analistas
                    ): nome
                    for idx, nome in enumerate(fila_analistas)
                }

                for future in as_completed(futures):
                    nome = futures[future]
                    try:
                        nome_ret, analise, protocolos_ret = future.result()
                        analistas_processados += 1
                        protocolos_analistas.extend(protocolos_ret)
                        if analise == "PULADO":
                            pass  # análise existente, nenhuma ação necessária
                        elif analise and not analise.startswith("Erro:"):
                            resultados_analistas[nome_ret] = analise
                        else:
                            logger.error(f"✗ Falha na análise de {nome_ret}")
                    except Exception as e:
                        analistas_processados += 1
                        logger.error(f"Erro no processamento de {nome}: {str(e)}")

            # Montar content na ordem original dos analistas
            for nome in fila_analistas:
                if nome in resultados_analistas:
                    analise = resultados_analistas[nome]
                    comentarios_analista = comentarios_criticos[comentarios_criticos['Analista'] == nome]
                    content += f"\n{'='*80}\n"
                    content += f"ANÁLISE INDIVIDUAL - {nome.upper()}\n"
                    content += f"Data: {data_inicio_analise} a {data_fim_analise}\n"
                    content += f"Comentários analisados: {len(comentarios_analista)}\n"
                    content += f"{'='*80}\n"
                    content += analise + "\n\n"

            logger.info(f"=== PROCESSAMENTO CONCLUÍDO ===")
            logger.info(f"Total de analistas processados: {analistas_processados}/{total_analistas}")
            
            # Análise comparativa geral (usando os dias do mês anterior)
            logger.info("Executando análise comparativa geral...")
            dias_mes_anterior = (ultimo_dia_mes_anterior - primeiro_dia_mes_anterior).days + 1
            analise_comp = analise_comparativa_nps(analistas_criticos, periodo_dias=dias_mes_anterior)
            if analise_comp:
                content += f"\n{'='*80}\n"
                content += "ANÁLISE COMPARATIVA GERAL\n"
                content += f"{'='*80}\n"
                content += analise_comp
            
            # Aplicando a substituição com regex
            content = re.sub(r'\*\*', '*', content)
            
            # Criar relatório personalizado para NPS
            relatorio_nps = f"""
🔴 *ALERTA: NPS ABAIXO DA META DETECTADO*

📊 *Resumo da Análise:*
• Período analisado: {data_inicio_analise} até {data_fim_analise} (mês anterior)
• Total de avaliações analisadas: {len(df)}
• Analistas com NPS abaixo da meta (< 70): {len(analistas_criticos)}
• Atendimentos analisados: {len(protocolos_analistas)} protocolos
• Todos os setores incluídos na análise

📋 *Analistas com NPS < 70:*
"""
            
            for analista, dados in analistas_criticos.iterrows():
                # Buscar estatísticas do analista
                stats_analista = stats_analistas[stats_analistas['Analista'] == analista]
                if not stats_analista.empty:
                    total_avaliacoes = stats_analista.iloc[0]['total_avaliacoes_nps']
                    protocolos_unicos = stats_analista.iloc[0]['protocolos_unicos']
                    relatorio_nps += f"\n• *{analista}*: Velocidade:{dados['NPS_Velocidade']}, Solução:{dados['NPS_Solucao']}, Relacionamento:{dados['NPS_Relacionamento']}"
                    relatorio_nps += f"\n  └ {dados['Total_Avaliacoes']} avaliações NPS | {protocolos_unicos} protocolos únicos | {total_avaliacoes} registros"
                else:
                    relatorio_nps += f"\n• *{analista}*: Velocidade:{dados['NPS_Velocidade']}, Solução:{dados['NPS_Solucao']}, Relacionamento:{dados['NPS_Relacionamento']} - {dados['Total_Avaliacoes']} avaliações"
            
            relatorio_nps += f"\n\n🤖 *Análise dos Comentários:*\n{content}"
            
            logger.info("Enviando notificação...")
            notifica(relatorio_nps, len(analistas_criticos), len(df_nps_analistas))
            notificou = True
            
        else:
            logger.warning("Nenhum comentário encontrado para os analistas críticos.")
            notificou = False
    else:
        logger.info("OK Todos os analistas atingiram a meta de NPS!")
        
        # Mostrar os primeiros analistas
        logger.info("=== TOP 5 ANALISTAS ===")
        contador = 0
        for analista, dados in df_nps_analistas.iterrows():
            if contador < 5:
                logger.info(f"Top Analista: {analista} - "
                           f"Vel:{dados['NPS_Velocidade']} Sol:{dados['NPS_Solucao']} "
                           f"Rel:{dados['NPS_Relacionamento']} - {dados['Total_Avaliacoes']} avaliações")
                contador += 1
        
        relatorio_positivo = f"""
✅ *RELATÓRIO POSITIVO DE NPS*

📊 *Status:* Todos os analistas atingiram a meta de NPS (>= 70)!
📅 *Período analisado:* {data_inicio_analise} até {data_fim_analise} (mês anterior)
📈 *Total de avaliações:* {len(df)}

🏆 *Primeiros 5 Analistas:*
"""
        
        contador = 0
        for analista, dados in df_nps_analistas.iterrows():
            if contador < 5:
                relatorio_positivo += f"\n• *{analista}*: Velocidade:{dados['NPS_Velocidade']}, Solução:{dados['NPS_Solucao']}, Relacionamento:{dados['NPS_Relacionamento']} - {dados['Total_Avaliacoes']} avaliações"
                contador += 1
        
        notifica_boas_noticias(relatorio_positivo)
        notificou = True
    
    #|-------------------------------------------------------------------------------------------------------------------|
    
    # SALVAR DADOS DA VERIFICAÇÃO
    
    executar_sql_pos_analise(conn)
    limpar_rawdata_antigos(conn)
    logger.info("✓ Verificação de NPS concluída com sucesso!")
    
except psycopg2.OperationalError as e:
    logger.error(f"Erro de conexão com banco de dados: {str(e)}")
    logger.error("Verifique as credenciais do banco no arquivo .env")
    sys.exit(1)
except psycopg2.DatabaseError as e:
    logger.error(f"Erro de banco de dados: {str(e)}")
    logger.exception("Detalhes do erro de banco:")
    sys.exit(1)
except pd.errors.DatabaseError as e:
    logger.error(f"Erro ao executar query: {str(e)}")
    logger.exception("Detalhes do erro de query:")
    sys.exit(1)
except ValueError as e:
    logger.error(f"Erro de valor/configuração: {str(e)}")
    logger.error("Verifique as configurações no arquivo .env")
    sys.exit(1)
except KeyError as e:
    logger.error(f"Erro de chave ausente nos dados: {str(e)}")
    logger.exception("Detalhes do erro:")
    sys.exit(1)
except SystemExit:
    # Permitir que sys.exit() funcione normalmente
    raise
except Exception as e:
    logger.error(f"Erro inesperado durante a execução: {str(e)}")
    logger.exception("Detalhes do erro:")
    sys.exit(1)
    
finally:
    # Garantir que conexões sejam fechadas independentemente do resultado
    if conn is not None:
        try:
            conn.close()
            logger.debug("Conexão psycopg2 fechada")
        except Exception as close_error:
            logger.warning(f"Erro ao fechar conexão: {str(close_error)}")
    
    if engine is not None:
        try:
            engine.dispose()
            logger.debug("Engine disposed")
        except Exception as close_error:
            logger.warning(f"Erro ao fazer dispose da engine: {str(close_error)}")
    
    logger.info("Conexões fechadas. Execução finalizada.")
