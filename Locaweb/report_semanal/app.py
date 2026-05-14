from datetime import datetime, timedelta
import pandas as pd
from function_logger import configurar_logger 
from sqlalchemy import create_engine, text
from slack_sdk import WebClient
import holidays
from tabulate import tabulate 
from gerarpdf import gerar_pdf
from openai import analise_openai
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
from email.header import Header
import configparser
import os
import time


sql_path = Path(__file__).parent

# Configurar logger
logger = configurar_logger()

# Carregar configurações sensíveis do config.ini (BD, Slack, Gmail).
config_file_path = sql_path.parent.parent / 'config.ini'
config = configparser.ConfigParser()

if not config_file_path.exists():
    logger.error(f"Arquivo config.ini não encontrado em {config_file_path}. Encerrando.")
    raise SystemExit(f"config.ini ausente em {config_file_path}")

config.read(config_file_path)

try:
    DB_SERVER = config['database']['server']
    DB_NAME = config['database']['database']
    DB_USER = config['database']['uid']
    DB_PASSWORD = config['database']['pwd']
except KeyError as e:
    logger.error(f"Configurações de banco ausentes no config.ini: {e}")
    raise SystemExit(f"Seção [database] incompleta em config.ini: {e}")

try:
    SLACK_BOT_TOKEN = config['slack']['bot_token']
except KeyError as e:
    logger.error(f"Token do Slack ausente no config.ini: {e}")
    raise SystemExit(f"Seção [slack] incompleta em config.ini: {e}")

try:
    _csv_to_list = lambda s: [x.strip() for x in s.split(',') if x.strip()]
    REPORT_DESTINATARIOS_EMAIL = _csv_to_list(config['report_semanal']['destinatarios_email'])
    REPORT_DESTINATARIOS_BCC = _csv_to_list(config['report_semanal'].get('destinatarios_bcc', ''))
    REPORT_SLACK_CHANNEL = config['report_semanal']['slack_channel']
    SCHEMA_OCTADESK = config['report_semanal'].get('schema_octadesk', 'lw_octadesk')
    SCHEMA_SERVICENOW = config['report_semanal'].get('schema_servicenow', 'lwsa')
except KeyError as e:
    logger.error(f"Configurações do report_semanal ausentes no config.ini: {e}")
    raise SystemExit(f"Seção [report_semanal] incompleta em config.ini: {e}")

try:
    EMAIL_ACCOUNT = config['gmail']['EMAIL_ACCOUNT']
    EMAIL_PASSWORD = config['gmail']['EMAIL_PASSWORD']
except KeyError:
    logger.warning("Configurações de email não encontradas no config.ini. PDFs não serão enviados por email.")
    EMAIL_ACCOUNT = None
    EMAIL_PASSWORD = None

hoje = datetime.now()

data_hoje = datetime.now().date()
# Lista de feriados no Brasil (ou outro país)
feriados_brasil = holidays.Brazil()

setores = ['Suporte', 
            'Cobrança'
            ]

fim_ano = datetime(hoje.year, 12, 31)
dias_restantes = (fim_ano - hoje).days

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

try:
    conn_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}"
    engine = create_engine(conn_string)
    conn = engine.connect()
    logger.info("Conexao com o Banco estabelecida!")

except Exception as e:
    print("Ocorreu um erro na conexão:", e)
    logger.error(f"Ocorreu um erro na conexão: {e}")
    #notify_slack(f"Erro na execução da {rotina}: {e}", rotina)
    exit(1)  # Sair se não conseguir conectar    

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

# Função para contar o número de linhas do DataFrame
def contar_linhas(df,setor=None,ignora_bot=None, atendidas=None, abandono=None,ultima_semana=None, data=None, semana_anterior= None):

    if setor:
        df = df[(df['setor'] == setor)]
    if ignora_bot:
        df = df[df['robo'] != 1]
    if atendidas:
        df = df[(df['abandono'] != 1) & (df['setor'] == setor) ]
    if abandono:
        df = df[(df['abandono'] == 1) & (df['setor'] == setor) ]
    if ultima_semana:
        df = df[(df['ultima_semana'] == 1)]
    if data:
        df = df[(df['data'] == data_hoje)]
    if semana_anterior:
        df = df[(df['semana_anterior'] == 1)]

    return len(df)
# Função para calcular o tempo médio de atendimento
def calcular_tempo(df, coluna_tempo, setor=None, ignora_bot=None, data=None, semana_anterior=None, ultima_semana=None):
    if setor:
        df = df[(df['setor'] == setor)]
    if ignora_bot:
        df = df[(df['robo'] != 1) & (df['Tempo de Atendimento'] > 0)]
    if data:
        df = df[(df['data'] == data_hoje)]
    if semana_anterior:
        df = df[(df['semana_anterior'] == 1)]
    if ultima_semana:
        df = df[(df['ultima_semana'] == 1)]

    total_tempo = df[coluna_tempo].sum()
    total_registros = len(df)
    
    if total_registros > 0:
        tempo_medio_segundos = total_tempo / total_registros
        horas = int(tempo_medio_segundos // 3600)
        minutos = int((tempo_medio_segundos % 3600) // 60)
        segundos = int(tempo_medio_segundos % 60)
        return f"{horas:02}:{minutos:02}:{segundos:02}"
    else:
        return "00:00:00"
  
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
    
def calcular_metricas_setor(df_setor, setor, coluna_tempo_atendimento, coluna_tempo_espera, periodo="semana_atual"):
    # Definição dos flags para períodos
    semana_anterior = periodo == "semana_anterior"
    ultima_semana = periodo == "ultima_semana"

    # Dicionário de parâmetros extras para o filtro
    params = {}
    if periodo != "media_anual":
        params.update({
            "semana_anterior": semana_anterior,
            "ultima_semana": ultima_semana
        })

    # Contagens
    recebidos = contar_linhas(df_setor, **params)
    atendidos = contar_linhas(df_setor, setor=setor, atendidas=True, **params)
    abandonos = contar_linhas(df_setor, setor=setor, abandono=True, **params)

    # Tempos médios
    tma = calcular_tempo(df_setor, coluna_tempo_atendimento, **params)
    tme = calcular_tempo(df_setor, coluna_tempo_espera, **params)

    # Percentual de abandono
    percentual_abandono = round((abandonos / recebidos) * 100, 2) if recebidos != 0 else 0

    return {
        "Setor": setor,
        "Recebidos": recebidos,
        "Atendidos": atendidos,
        "Abandonos": abandonos,
        "Percentual": percentual_abandono,
        "TMA": tma,
        "TME": tme
    }

def calcular_nps_periodo(df, periodo=None):
    
    # Filtra por período
    if periodo == "ultima_semana":
        df = df[df['ultima_semana'] == 1]
    elif periodo == "semana_anterior":
        df = df[df['semana_anterior'] == 1]
    # Para media anual não filtramos por período

    # Filtra respostas válidas
    df_nps = df[df['p1_nota'].notna() & df['p2_nota'].notna() & df['p3_nota'].notna()]
    
    total_de_pesquisas = len(df_nps)
    if total_de_pesquisas == 0:
        return pd.DataFrame(columns=["Pesquisa", "NPS", "Promotores", "Neutros", "Detratores"])
    
    # Apenas categorias
    df_categorias = df_nps[['categoria_p1', 'categoria_p2', 'categoria_p3']].rename(columns={
        'categoria_p1': 'P1',
        'categoria_p2': 'P2',
        'categoria_p3': 'P3'
    })

    # Calcula por cada pesquisa (P1, P2, P3)
    resultados = []
    for categoria in df_categorias.columns:
        col = df_categorias[categoria]
        promotores = (col == 'Promotora').sum()
        neutros = (col == 'Neutra').sum()
        detratores = (col == 'Detratora').sum()
        
        nps = ((promotores - detratores) / total_de_pesquisas) * 100
        nps_int = round(nps)

        resultados.append({
            "Pesquisa": categoria,
            "NPS": nps_int,
            "Promotores": promotores,
            "Neutros": neutros,
            "Detratores": detratores
        })
    
    return pd.DataFrame(resultados)

def analise_comentario_periodo(df, periodo=None):
    # Filtra por período
    if periodo == "ultima_semana":
        df = df[df['ultima_semana'] == 1]
    elif periodo == "semana_anterior":
        df = df[df['semana_anterior'] == 1]
    # Para média anual não filtramos

    # Filtra respostas válidas
    df_comentario = df[df['p4_nota'].notna()][['p4_nota']]

    if df_comentario.empty:
        return None  # Nenhum comentário encontrado

    # Concatena todos os comentários em um único texto, separados por quebra de linha
    comentarios_texto = "\n".join(df_comentario['p4_nota'].astype(str).tolist())

    # Limita tamanho para não estourar o limite de tokens da API
    if len(comentarios_texto) > 8000:
        comentarios_texto = comentarios_texto[:8000] + "\n[... Comentários truncados ...]"

    return comentarios_texto

def processar_incidentes_nominais(df_incidentes):
    """
    Processa os dados de incidentes do ServiceNow (apenas nominais da última semana)
    
    Args:
        df_incidentes: DataFrame com dados da query_3 (incidentes ServiceNow já filtrados)
    
    Returns:
        dict: Dados estruturados dos incidentes para análise IA
    """
    if df_incidentes.empty:
        return {
            "total_incidentes": 0,
            "produtos_afetados": {},
            "resumo_problemas": "",
            "resumo_solucoes": ""
        }
    
    # Estatísticas básicas
    total_incidentes = len(df_incidentes)
    
    # Produtos mais afetados
    produtos_afetados = df_incidentes['produto'].value_counts().head(5).to_dict()
    
    # Resumo dos problemas (descrição_curta)
    problemas = df_incidentes['descricao_curta'].dropna().tolist()
    resumo_problemas = "\n".join([f"- {problema}" for problema in problemas[:20]])  # Aumentado para 20 itens
    
    # Resumo das soluções (fechamento)
    solucoes = df_incidentes['fechamento'].dropna().tolist()
    resumo_solucoes = "\n".join([f"- {solucao}" for solucao in solucoes[:20]])  # Aumentado para 20 itens
    
    # Limita tamanho para não estourar tokens da API
    if len(resumo_problemas) > 3000:
        resumo_problemas = resumo_problemas[:3000] + "\n[... Problemas truncados ...]"
    
    if len(resumo_solucoes) > 3000:
        resumo_solucoes = resumo_solucoes[:3000] + "\n[... Soluções truncadas ...]"
    
    return {
        "total_incidentes": total_incidentes,
        "produtos_afetados": produtos_afetados,
        "resumo_problemas": resumo_problemas,
        "resumo_solucoes": resumo_solucoes
    }

def processar_incidentes_por_setor(df_incidentes, setor):
    """
    Processa os dados de incidentes do ServiceNow específicos por setor
    
    Args:
        df_incidentes: DataFrame com dados da query_3 (incidentes ServiceNow já filtrados)
        setor: String indicando o setor ('Suporte' ou 'Cobrança')
    
    Returns:
        dict: Dados estruturados dos incidentes para análise IA ou dados vazios se não for Suporte
    """
    # Se não for setor de Suporte, retorna dados vazios (sem incidentes técnicos)
    if setor != 'Suporte':
        return {
            "total_incidentes": 0,
            "produtos_afetados": {},
            "resumo_problemas": "Nenhum incidente técnico relevante para análise do setor de Cobrança.",
            "resumo_solucoes": "Análise focada em métricas de atendimento e satisfação do cliente."
        }
    
    # Para o setor de Suporte, processa normalmente os incidentes
    return processar_incidentes_nominais(df_incidentes)

def enviar_email_pdf(lista_pdfs, periodo, destinatarios_email, bcc=None):
    """
    Envia os PDFs gerados por email via Gmail em um único email
    
    Args:
        lista_pdfs: Lista de dicionários com informações dos PDFs [{'arquivo': caminho, 'setor': nome_setor}, ...]
        periodo: Período do relatório (string)
        destinatarios_email: Lista de endereços de email para envio
        bcc: Lista de endereços de email para cópia oculta (opcional)
    
    Returns:
        bool: True se enviado com sucesso, False caso contrário
    """
    if not EMAIL_ACCOUNT or not EMAIL_PASSWORD:
        logger.error("Configurações de email não disponíveis. Não é possível enviar o PDF.")
        print("⚠️ AVISO: Configurações de email não disponíveis. PDF não será enviado.")
        return False
    
    if not lista_pdfs or len(lista_pdfs) == 0:
        logger.error("Nenhum PDF fornecido para envio.")
        print("❌ ERRO: Nenhum PDF fornecido para envio.")
        return False
    
    # Obter o tempo atual para validar que os PDFs são recentes
    tempo_atual = datetime.now()
    # Considerar PDFs válidos se foram criados/modificados nos últimos 15 minutos
    # (tempo suficiente para garantir que são da execução atual)
    tempo_limite_minutos = 15
    
    # Verificar se todos os arquivos existem e são recentes
    for pdf_info in lista_pdfs:
        arquivo_pdf = pdf_info['arquivo']
        if not os.path.exists(arquivo_pdf):
            logger.error(f"Arquivo PDF não encontrado: {arquivo_pdf}")
            print(f"❌ ERRO: Arquivo PDF não encontrado: {arquivo_pdf}")
            return False
        
        # Verificar data de modificação do arquivo
        tempo_modificacao = datetime.fromtimestamp(os.path.getmtime(arquivo_pdf))
        diferenca_tempo = (tempo_atual - tempo_modificacao).total_seconds() / 60  # em minutos
        
        if diferenca_tempo > tempo_limite_minutos:
            logger.error(f"Arquivo PDF muito antigo para envio: {arquivo_pdf} (modificado há {diferenca_tempo:.1f} minutos)")
            print(f"❌ ERRO: Arquivo PDF muito antigo para envio: {os.path.basename(arquivo_pdf)}")
            print(f"   Arquivo foi modificado há {diferenca_tempo:.1f} minutos. Apenas PDFs gerados na execução atual serão enviados.")
            return False
        
        logger.info(f"PDF validado: {os.path.basename(arquivo_pdf)} (modificado há {diferenca_tempo:.1f} minutos)")
    
    try:
        # Criar mensagem
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ACCOUNT
        msg['To'] = ', '.join(destinatarios_email)
        if bcc:
            msg['Bcc'] = ', '.join(bcc) if isinstance(bcc, list) else bcc
        msg['Subject'] = f"Análise Semanal de Atendimento com Insights de IA - {periodo}"
        
        # Preparar lista de setores para o corpo do email
        setores_enviados = [pdf_info['setor'] for pdf_info in lista_pdfs]
        setores_str = ' e '.join(setores_enviados) if len(setores_enviados) > 1 else setores_enviados[0]
        
        # Corpo do email
        corpo_email = f"""
        Prezados,
        
        Seguem em anexo os Reports Semanais dos setores {setores_str} referentes ao período de {periodo}.
        
        Este é um email automático gerado pelo sistema de relatórios.

        Qualquer discrepância, favor entrar em contato com a equipe de Data Analytics.
        
        Atenciosamente,
        
        Equipe de Data Analytics
        """
        
        msg.attach(MIMEText(corpo_email, 'plain', 'utf-8'))
        
        # Anexar todos os PDFs
        for pdf_info in lista_pdfs:
            arquivo_pdf = pdf_info['arquivo']
            
            # Garantir que o arquivo está completamente escrito e estável
            # Verificar se o tamanho do arquivo está estável (não está mudando)
            tamanho_anterior = 0
            tentativas_estabilidade = 0
            max_tentativas_estabilidade = 10
            
            while tentativas_estabilidade < max_tentativas_estabilidade:
                if os.path.exists(arquivo_pdf):
                    tamanho_atual = os.path.getsize(arquivo_pdf)
                    if tamanho_atual == tamanho_anterior and tamanho_atual > 0:
                        # Arquivo estável, pode prosseguir
                        break
                    tamanho_anterior = tamanho_atual
                time.sleep(0.5)  # Aguardar 0.5 segundos antes de verificar novamente
                tentativas_estabilidade += 1
            
            # Verificar se o arquivo existe e tem tamanho válido
            if not os.path.exists(arquivo_pdf):
                logger.error(f"Arquivo PDF não encontrado após verificação: {arquivo_pdf}")
                print(f"❌ ERRO: Arquivo PDF não encontrado: {os.path.basename(arquivo_pdf)}")
                continue
            
            tamanho_final = os.path.getsize(arquivo_pdf)
            if tamanho_final == 0:
                logger.error(f"Arquivo PDF está vazio: {arquivo_pdf}")
                print(f"❌ ERRO: Arquivo PDF está vazio: {os.path.basename(arquivo_pdf)}")
                continue
            
            logger.info(f"Arquivo PDF validado e estável: {os.path.basename(arquivo_pdf)} ({tamanho_final} bytes)")
            
            # Ler e anexar o arquivo
            nome_arquivo = os.path.basename(arquivo_pdf)
            
            with open(arquivo_pdf, "rb") as anexo:
                conteudo = anexo.read()
                # Verificar se o conteúdo foi lido corretamente
                if len(conteudo) == 0:
                    logger.error(f"Falha ao ler conteúdo do arquivo PDF: {arquivo_pdf}")
                    print(f"❌ ERRO: Falha ao ler conteúdo do arquivo: {nome_arquivo}")
                    continue
                
                # Usar MIMEApplication que é mais adequado para PDFs
                # Isso garante melhor compatibilidade com clientes de email
                part = MIMEApplication(conteudo, _subtype='pdf')
                
                # Configurar o nome do arquivo corretamente
                # Usar o método correto para adicionar o filename
                part.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=('utf-8', '', nome_arquivo)
                )
                
                msg.attach(part)
                print(f"   ✓ Anexado: {nome_arquivo} ({len(conteudo)} bytes)")
                logger.info(f"PDF anexado: {nome_arquivo} ({len(conteudo)} bytes)")
        
        # Conectar ao servidor SMTP do Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        
        # Enviar email
        # Preparar lista de destinatários incluindo BCC
        todos_destinatarios = destinatarios_email.copy()
        if bcc:
            if isinstance(bcc, list):
                todos_destinatarios.extend(bcc)
            else:
                todos_destinatarios.append(bcc)
        
        texto = msg.as_string()
        server.sendmail(EMAIL_ACCOUNT, todos_destinatarios, texto)
        server.quit()
        
        mensagem_log = f"Email enviado com sucesso para {', '.join(destinatarios_email)}"
        mensagem_log += f" com {len(lista_pdfs)} PDF(s) anexado(s)"
        if bcc:
            bcc_list = bcc if isinstance(bcc, list) else [bcc]
            mensagem_log += f" (BCC: {', '.join(bcc_list)})"
        logger.info(mensagem_log)
        print(f"✅ {mensagem_log}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar email: {e}")
        print(f"❌ ERRO ao enviar email: {e}")
        import traceback
        traceback.print_exc()
        return False

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

query = f"SELECT * FROM {SCHEMA_OCTADESK}.vw_report_semanal;"

query_2 = f"SELECT * FROM {SCHEMA_OCTADESK}.vw_woz;"

query_3 = f"""SELECT i.numero, i.data_abertura,
                i.descricao_curta, i.fechamento, i.produto, i.tipo_usuario
                FROM {SCHEMA_SERVICENOW}.service_now_incidentes i
                WHERE i.organizacao = 'Locaweb'
                AND i.produto IS NOT NULL
                AND i.fechamento IS NOT NULL
                AND i.status = 'Encerrado'
                AND i.tipo_usuario = 'Nominal'
                AND i.produto ILIKE '%%Locaweb%%'
                AND i.prioridade IN ('2 - Alta', '1 - Critica')
                AND i.data_abertura::date >= ('now'::text::date - 4);"""

df = pd.read_sql_query(query,conn)
df_2 = pd.read_sql_query(query_2,conn)
df_3 = pd.read_sql_query(query_3,conn)

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# ANÁLISE WOZ - Volume de IDs resolvidos por tipo
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

def analisar_volume_woz(df, setor):
    """
    Analisa o volume de IDs resolvidos por cada tipo de WOZ
    e calcula as taxas de resolução baseadas na coluna tags.
    
    Returns:
        dict: Dicionário com volumes, taxas de resolução e comparações
    """
    
    # Mapeamento das colunas WOZ para suas tags correspondentes
    if setor == 'Suporte':
        mapeamento_woz_tags = {
            'woz_resolvido': 'SUPORTE_TRANSFER_WOZ',
            'woz_linux_resolvido': 'Suporte_Transfer_WOZ_HospedagemLinux',
            'woz_windows_resolvido': 'Suporte_Transfer_WOZ_HospedagemWindows',
            'woz_wordpress_resolvido': 'Suporte_Transfer_WOZ_Hospedagem Wordpress',
            'woz_criadordesites_resolvido': 'Suporte_Transfer_WOZ_CriadordeSites',
            'woz_ssl_resolvido': 'Suporte_Transfer_WOZ_CertificadoSSL',
            'woz_bancodedados_resolvido': 'Suporte_Transfer_WOZ_BancodeDados',
            'woz_restorebackup_resolvido': 'Suporte_Transfer_WOZ_Restore/Backup',
            'woz_registro_resolvido': 'Suporte_Transfer_WOZ_RegistrodeDomínio',
            'woz_cloudhosting_resolvido': 'Suporte_Transfer_WOZ_CloudHosting',
            'woz_cloudserverpro_resolvido': 'Suporte_Transfer_WOZ_CloudServerPro',
            'woz_vpslocaweb_resolvido': 'Suporte_Transfer_WOZ_VPSLocaweb',
            'woz_servidordedicado_resolvido': 'Suporte_Transfer_WOZ_ServidorDedicado',
            'woz_servidorgerenciado_resolvido': 'Suporte_Transfer_WOZ_ServidorGerenciado',
            'woz_hospedagemdedicada_resolvido': 'Suporte_Transfer_WOZ_HospedagemDedicada',
            'woz_locawebcloud_resolvido': 'Suporte_Transfer_WOZ_LocawebCloud',
            'woz_email_resolvido': 'Suporte_Transfer_WOZ_EmailLocaweb',
            'woz_exchange_resolvido': 'Suporte_Transfer_WOZ_Exchange',
            'woz_emailgo_resolvido': 'Suporte_Transfer_WOZ_EmailGO',
            'woz_gw_resolvido': 'Suporte_Transfer_WOZ_GoogleWorkspace',
            'woz_emarketing_resolvido': 'Suporte_Transfer_WOZ_EmailMarketing',
            'woz_smtp_resolvido': 'Suporte_Transfer_WOZ_SMTPLocaweb',
            'woz_pabx_resolvido': 'Suporte_Transfer_WOZ_PABXVirtual',
            'woz_revendalocaweb_resolvido': 'Suporte_Transfer_WOZ_RevendaLocaweb',
            'woz_revendaplesk_resolvido': 'Suporte_Transfer_WOZ_RevendaPlesk',
            'woz_revendacpanel_resolvido': 'Suporte_Transfer_WOZ_RevendacPanel'
        }
    else:
        mapeamento_woz_tags = {
            #'woz_resolvido': 'SUPORTE_TRANSFER_WOZ',
            'woz_cobranca_resolvido': 'SUPORTE_TRANSFER_WOZ_Cobrança'
        }
    
    # Inicializar resultado
    resultado = {
        'semana_atual': {},
        'semana_anterior': {},
        'comparacao': {},
        'taxa_resolucao_atual': {},
        'taxa_resolucao_anterior': {}
    }
    
    def calcular_metricas_periodo(df_periodo, nome_periodo):
        """Calcula métricas para um período específico"""
        metricas = {}
        taxas = {}
        
        for coluna, tag in mapeamento_woz_tags.items():
            # Volume resolvido (método original)
            volume_resolvido = df_periodo[coluna].sum()
            metricas[coluna] = volume_resolvido
            
            # Calcular taxa de resolução baseada na coluna tags
            if 'tags' in df_periodo.columns:
                # Casos que têm a tag específica
                casos_com_tag = df_periodo[df_periodo['tags'].str.contains(tag, case=False, na=False)]
                total_casos = len(casos_com_tag)
                
                if total_casos > 0:
                    # Casos resolvidos dentre os que têm a tag
                    casos_resolvidos = casos_com_tag[coluna].sum()
                    taxa_resolucao = (casos_resolvidos / total_casos) * 100
                else:
                    casos_resolvidos = 0
                    taxa_resolucao = 0
                
                taxas[coluna] = {
                    'total_casos': total_casos,
                    'casos_resolvidos': int(casos_resolvidos),
                    'taxa_percentual': taxa_resolucao
                }
            else:
                # Fallback se não houver coluna tags
                taxas[coluna] = {
                    'total_casos': 0,
                    'casos_resolvidos': int(volume_resolvido),
                    'taxa_percentual': 0
                }
        
        return metricas, taxas
    
    # Calcular métricas para semana atual
    df_semana_atual = df[df['ultima_semana'] == 1]
    resultado['semana_atual'], resultado['taxa_resolucao_atual'] = calcular_metricas_periodo(
        df_semana_atual, 'atual'
    )
    
    # Calcular métricas para semana anterior  
    df_semana_anterior = df[df['semana_anterior'] == 1]
    resultado['semana_anterior'], resultado['taxa_resolucao_anterior'] = calcular_metricas_periodo(
        df_semana_anterior, 'anterior'
    )
    
    # Calcular comparações (diferença absoluta e percentual)
    for coluna in mapeamento_woz_tags.keys():
        atual = resultado['semana_atual'][coluna]
        anterior = resultado['semana_anterior'][coluna]
        
        diferenca = atual - anterior
        
        if anterior > 0:
            variacao_percentual = ((atual - anterior) / anterior) * 100
        else:
            variacao_percentual = 0 if atual == 0 else float('inf')
        
        resultado['comparacao'][coluna] = {
            'diferenca_absoluta': diferenca,
            'variacao_percentual': variacao_percentual
        }
    
    return resultado

def gerar_analise_woz_ia(analise_woz):
    """
    Gera análise de IA para o WOZ com dados separados por período
    """
    # Mapeamento de nomes técnicos para nomes apresentáveis
    mapeamento_nomes_apresentaveis = {
        'woz_resolvido': 'WOZ Geral',
        'woz_linux_resolvido': 'Hospedagem Linux',
        'woz_windows': 'Hospedagem Windows',
        'woz_windows_resolvido': 'Hospedagem Windows',
        'woz_wordpress_resolvido': 'Hospedagem WordPress',
        'woz_criadordesites_resolvido': 'Criador de Sites',
        'woz_ssl_resolvido': 'Certificado SSL',
        'woz_bancodedados_resolvido': 'Banco de Dados',
        'woz_restorebackup_resolvido': 'Restore/Backup',
        'woz_registro': 'Registro de Domínio',
        'woz_registro_resolvido': 'Registro de Domínio',
        'woz_cloudhosting_resolvido': 'Cloud Hosting',
        'woz_cloudserverpro_resolvido': 'Cloud Server Pro',
        'woz_vpslocaweb_resolvido': 'VPS Locaweb',
        'woz_servidordedicado_resolvido': 'Servidor Dedicado',
        'woz_servidorgerenciado_resolvido': 'Servidor Gerenciado',
        'woz_hospedagemdedicada_resolvido': 'Hospedagem Dedicada',
        'woz_locawebcloud_resolvido': 'Locaweb Cloud',
        'woz_email_resolvido': 'Email Locaweb',
        'woz_exchange_resolvido': 'Exchange',
        'woz_emailgo_resolvido': 'Email GO',
        'woz_gw_resolvido': 'Google Workspace',
        'woz_emarketing_resolvido': 'Email Marketing',
        'woz_smtp_resolvido': 'SMTP Locaweb',
        'woz_pabx_resolvido': 'PABX Virtual',
        'woz_revendalocaweb_resolvido': 'Revenda Locaweb',
        'woz_revendaplesk_resolvido': 'Revenda Plesk',
        'woz_revendacpanel_resolvido': 'Revenda cPanel',
        'woz_cobranca_resolvido': 'Cobrança'
    }
    # Converter os dados para um formato mais legível para a IA
    df_atual_str = "Dados da Semana Atual:\n"
    df_atual_str += f"Total de casos WOZ: {sum(analise_woz['semana_atual'].values())}\n"
    df_atual_str += "Detalhamento por tipo:\n"
    for tipo, volume in analise_woz['semana_atual'].items():
        taxa_info = analise_woz['taxa_resolucao_atual'].get(tipo, {})
        total_casos = taxa_info.get('total_casos', 0)
        taxa_percentual = taxa_info.get('taxa_percentual', 0)
        nome_apresentavel = mapeamento_nomes_apresentaveis.get(tipo, tipo)
        df_atual_str += f"- {nome_apresentavel}: {volume} resolvidos de {total_casos} casos ({taxa_percentual:.1f}% taxa de resolução)\n"
    
    df_past_str = "Dados da Semana Anterior:\n"
    df_past_str += f"Total de casos WOZ: {sum(analise_woz['semana_anterior'].values())}\n"
    df_past_str += "Detalhamento por tipo:\n"
    for tipo, volume in analise_woz['semana_anterior'].items():
        taxa_info = analise_woz['taxa_resolucao_anterior'].get(tipo, {})
        total_casos = taxa_info.get('total_casos', 0)
        taxa_percentual = taxa_info.get('taxa_percentual', 0)
        nome_apresentavel = mapeamento_nomes_apresentaveis.get(tipo, tipo)
        df_past_str += f"- {nome_apresentavel}: {volume} resolvidos de {total_casos} casos ({taxa_percentual:.1f}% taxa de resolução)\n"
    
    # Caminho para o prompt
    prompt_path = sql_path / "prompts" / "analise_woz_semanal.md"
    
    try:
        # Chamar a função analise_openai com os dados formatados
        analise_ia = analise_openai(
            df_atual=df_atual_str,
            df_past=df_past_str,
            dias_restantes=0,  # Não é usado no prompt WOZ
            prompt=str(prompt_path)
        )
        return analise_ia
    except Exception as e:
        logger.error(f"Erro ao gerar análise WOZ com IA: {e}")
        # Retornar análise de fallback em caso de erro
        total_atual = sum(analise_woz['semana_atual'].values())
        total_anterior = sum(analise_woz['semana_anterior'].values())
        diferenca = total_atual - total_anterior
        variacao = ((diferenca / total_anterior) * 100) if total_anterior > 0 else 0
        
        return f"**Resumo WOZ:** Na semana atual foram processados {total_atual} casos, comparado a {total_anterior} na semana anterior. Variação de {diferenca:+d} casos ({variacao:+.1f}%)."


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

# Criação do cliente Slack com seu token
client = WebClient(SLACK_BOT_TOKEN)

# Destinatarios carregados de [report_semanal] no config.ini
destinatarios = [REPORT_SLACK_CHANNEL]
destinatarios_email = REPORT_DESTINATARIOS_EMAIL
destinatarios_bcc = REPORT_DESTINATARIOS_BCC


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

print("=== INICIANDO PROCESSAMENTO GERAL ===")
print(f"Setores configurados: {setores}")

# Lista para armazenar os PDFs gerados
pdfs_gerados = []

for setor in setores:
    print(f"\n=== INICIANDO PROCESSAMENTO DO SETOR: {setor} ===")

    df_setor = df[(df['setor'] == setor)].copy()
    print(f"Registros encontrados para {setor}: {len(df_setor)}")

    if len(df_setor) == 0:
        print(f"⚠️ AVISO: Nenhum registro encontrado para o setor '{setor}'. Pulando...")
        continue

    # formato datetime
    df_setor['data_inicio_interacao'] = pd.to_datetime(df_setor['data_inicio_interacao'])

    # Obter a menor e a maior data
    registros_semana_atual = df_setor[df_setor['ultima_semana'] == 1]
    print(f"Registros da última semana para {setor}: {len(registros_semana_atual)}")

    if len(registros_semana_atual) == 0:
        print(f"⚠️ AVISO: Nenhum registro da última semana para '{setor}'. Pulando...")
        continue

    menor_data = registros_semana_atual['data_inicio_interacao'].min().date()
    maior_data = registros_semana_atual['data_inicio_interacao'].max().date()

    menor_data = menor_data.strftime('%d/%m/%Y')
    maior_data = maior_data.strftime('%d/%m/%Y')
    print(f"Período processado para {setor}: {menor_data} a {maior_data}")


    # Define as colunas de tempo
    coluna_tempo_atendimento = 'tempo_atendimento_segundos'
    coluna_tempo_espera = 'tempo_espera'

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------

    metricas = {
        "semana_anterior": calcular_metricas_setor(df_setor, setor, coluna_tempo_atendimento, coluna_tempo_espera, periodo="semana_anterior"),
        "semana_atual": calcular_metricas_setor(df_setor, setor, coluna_tempo_atendimento, coluna_tempo_espera, periodo="ultima_semana"),
        "media_anual": calcular_metricas_setor(df_setor, setor, coluna_tempo_atendimento, coluna_tempo_espera, periodo="media_anual")
    }


    # Se quiser converter cada um para DataFrame:
    df_semana_ant = pd.DataFrame([metricas["semana_anterior"]])
    df_semana_atual = pd.DataFrame([metricas["semana_atual"]])
    df_media_anual = pd.DataFrame([metricas["media_anual"]])

    df_media_anual = df_media_anual[['Setor','Percentual','TMA','TME']]
    df_media_anual.columns = ['Setor','Média % Abandonos','TMA','TME']

    df_semana_atual.columns = ["Setor", "Recebidos", "Atendidos","Abandonos","% Abandonos","TMA","TME"]
    mensagem_final = "\n" + tabulate(df_semana_atual, headers="keys", tablefmt="fancy_grid", showindex=False) + "\n"

    print(mensagem_final)

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------

    df_canais = df_setor['canal'].unique().tolist()

    carga_semana_anterior_canais = []
    carga_semana_atual_canais = []
    carga_media_anual_canais = []
    carga_nps_semana_anterior_canais = []
    carga_nps_semana_atual_canais = []
    carga_nps_media_anual_canais = []

    for canal in df_canais:
        df_canal = df_setor[df_setor['canal'] == canal]

        metricas_canais = {
            "semana_anterior": calcular_metricas_setor(df_canal, setor, coluna_tempo_atendimento, coluna_tempo_espera, periodo="semana_anterior"),
            "semana_atual": calcular_metricas_setor(df_canal, setor, coluna_tempo_atendimento, coluna_tempo_espera, periodo="ultima_semana"),
            "media_anual": calcular_metricas_setor(df_canal, setor, coluna_tempo_atendimento, coluna_tempo_espera, periodo="media_anual")
        }

        for periodo_nome in metricas_canais:
            df_periodo = pd.DataFrame([metricas_canais[periodo_nome]])
            df_periodo['Canal'] = canal
            # Reorganiza as colunas para que Canal fique na primeira posição
            cols = df_periodo.columns.tolist()
            cols = ['Canal'] + [c for c in cols if c != 'Canal']
            df_periodo = df_periodo[cols]

            # Renomeia colunas (ajuste nomes caso seja diferente)
            df_periodo.columns = ["Canal","Setor","Recebidos", "Atendidos", "Abandonos", "% Abandonos", "TMA", "TME"]
            df_periodo = df_periodo[["Canal", "Recebidos", "Atendidos", "Abandonos", "% Abandonos", "TMA", "TME"]]

            # Calcula NPS já com a info do canal
            nps_data = calcular_nps_periodo(df_canal, periodo=periodo_nome)
            if isinstance(nps_data, dict):
                nps_data["Canal"] = canal
            elif isinstance(nps_data, pd.DataFrame):
                nps_data["Canal"] = canal

            # Adiciona ao respectivo acumulador
            if periodo_nome == "semana_anterior":
                carga_semana_anterior_canais.append(df_periodo)
                carga_nps_semana_anterior_canais.append(nps_data)
            elif periodo_nome == "semana_atual":
                carga_semana_atual_canais.append(df_periodo)
                carga_nps_semana_atual_canais.append(nps_data)
            elif periodo_nome == "media_anual":
                carga_media_anual_canais.append(df_periodo)
                carga_nps_media_anual_canais.append(nps_data)

    # Concatena os DataFrames para cada período
    df_resultado_semana_anterior = pd.concat(carga_semana_anterior_canais, ignore_index=True)
    df_resultado_semana_atual = pd.concat(carga_semana_atual_canais, ignore_index=True)
    df_resultado_media_anual = pd.concat(carga_media_anual_canais, ignore_index=True)

    # Concatena os DataFrames para cada período
    df_resultado_nps_canais_semana_anterior = pd.concat(carga_nps_semana_anterior_canais, ignore_index=True)
    df_resultado_nps_canais_semana_atual = pd.concat(carga_nps_semana_atual_canais, ignore_index=True)
    df_resultado_nps_canais_media_anual = pd.concat(carga_nps_media_anual_canais, ignore_index=True)


    mensagem_final = "\n" + tabulate(df_resultado_semana_atual, headers="keys", tablefmt="fancy_grid", showindex=False) + "\n"

    mensagem_final2 = "\n" + tabulate(df_resultado_nps_canais_semana_atual, headers="keys", tablefmt="fancy_grid", showindex=False) + "\n"

    print(mensagem_final)

    print(mensagem_final2)


    #LISTA DE EQUIPES
    lista_equipes = df_setor['equipe'].unique().tolist()

    if setor == 'Suporte':

        carga_semana_anterior_equipes = []
        carga_semana_atual_equipes = []
        carga_media_anual_equipes = []

        #CALCULOS SEMANAIS
        for equipe in lista_equipes:

            df_equipe = df_setor[df_setor['equipe'] == equipe]

            metricas_equipes = {
                "semana_anterior": calcular_metricas_setor(df_equipe, setor, coluna_tempo_atendimento, coluna_tempo_espera, periodo="semana_anterior"),
                "semana_atual": calcular_metricas_setor(df_equipe, setor, coluna_tempo_atendimento, coluna_tempo_espera, periodo="ultima_semana"),
                "media_anual": calcular_metricas_setor(df_equipe, setor, coluna_tempo_atendimento, coluna_tempo_espera, periodo="media_anual")
                }

            for periodo_nome in metricas_equipes:
                df_periodo = pd.DataFrame([metricas_equipes[periodo_nome]])
                df_periodo['Equipe'] = equipe
                # Reorganiza as colunas para que a Equipe fique na primeira posição
                cols = df_periodo.columns.tolist()
                cols = ['Equipe'] + [c for c in cols if c != 'Equipe']
                df_periodo = df_periodo[cols]

                # Renomeia colunas (ajuste nomes caso seja diferente)
                df_periodo.columns = ["Equipe","Setor","Recebidos", "Atendidos", "Abandonos", "% Abandonos", "TMA", "TME"]
                df_periodo = df_periodo[["Equipe", "Recebidos", "Atendidos", "Abandonos", "% Abandonos", "TMA", "TME"]]

                # Adiciona ao respectivo acumulador
                if periodo_nome == "semana_anterior":
                    carga_semana_anterior_equipes.append(df_periodo)
                elif periodo_nome == "semana_atual":
                    carga_semana_atual_equipes.append(df_periodo)
                elif periodo_nome == "media_anual":
                    carga_media_anual_equipes.append(df_periodo)

        # Concatena os DataFrames para cada período
        df_resultado_semana_anterior_equipes = pd.concat(carga_semana_anterior_equipes, ignore_index=True)
        df_resultado_semana_atual_equipes = pd.concat(carga_semana_atual_equipes, ignore_index=True)
        df_resultado_media_anual_equipes = pd.concat(carga_media_anual_equipes, ignore_index=True)

        mensagem_final = "\n" + tabulate(df_resultado_semana_atual_equipes, headers="keys", tablefmt="fancy_grid", showindex=False) + "\n"

        print(mensagem_final)

    else:
        print(f"O setor: {setor} não tem grupos")

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------

    #CALCULO DE NPS
    nps_semana_anterior = calcular_nps_periodo(df_setor, periodo="semana_anterior")
    nps_semana_atual = calcular_nps_periodo(df_setor, periodo="ultima_semana")
    nps_media_anual = calcular_nps_periodo(df_setor)  # sem periodo = ano todo

    mensagem_final = "\n" + tabulate(nps_semana_atual, headers="keys", tablefmt="fancy_grid", showindex=False) + "\n"

    print(mensagem_final)

    # Extrai os comentários da última semana e da semana anterior
    comentarios_semana_atual = analise_comentario_periodo(df_setor, periodo="ultima_semana")
    comentarios_semana_anterior = analise_comentario_periodo(df_setor, periodo="semana_anterior")

    # Processa os dados de incidentes ServiceNow específicos por setor
    incidentes_nominais = processar_incidentes_por_setor(df_3, setor)

    # Para o PDF, usar dados brutos da query_3 (apenas para setor Suporte)
    incidentes_brutos = df_3 if setor == 'Suporte' else None


    # Defina os caminhos
    periodo = f"{menor_data} a {maior_data}"
    periodo_nome = f"{menor_data.replace('/', '-')} a {maior_data.replace('/', '-')}"
    reports_dir = sql_path / "Reports"
    reports_dir.mkdir(parents=True, exist_ok=True)  # Cria o diretório se não existir
    nome_pdf = str(reports_dir / f"Report Semanal {setor} - {periodo_nome}.pdf")


    # Seleciona o prompt específico baseado no setor
    if setor == 'Suporte':
        prompt_contatos = str(sql_path / "prompts" / "analise_contatos_semanal.md")
    else:
        prompt_contatos = str(sql_path / "prompts" / "analise_contatos_cobranca.md")

    analise_semanal = analise_openai(
        df_atual=df_semana_atual,
        df_past=df_semana_ant,
        dias_restantes=dias_restantes,
        valor_extra=incidentes_nominais,
        prompt=prompt_contatos
        )

    analise_total = analise_openai(
        df_atual=df_semana_atual,
        df_past=df_media_anual,
        dias_restantes=dias_restantes,
        prompt=str(sql_path / "prompts" / "analise_contatos_anual.md")
        )

    # Seleciona o prompt de NPS específico baseado no setor
    if setor == 'Suporte':
        prompt_nps = str(sql_path / "prompts" / "analise_nps_semanal.md")
    else:
        prompt_nps = str(sql_path / "prompts" / "analise_nps_cobranca.md")

    analise_nps = analise_openai(
        df_atual=nps_semana_atual,
        df_past=nps_semana_anterior,
        dias_restantes=dias_restantes,
        valor_extra = metricas,
        valor_extra2 = incidentes_nominais,
        prompt=prompt_nps
        )

    # Seleciona o prompt de comentários específico baseado no setor
    if setor == 'Suporte':
        prompt_comentarios = str(sql_path / "prompts" / "analise_comentarios.md")
    else:
        prompt_comentarios = str(sql_path / "prompts" / "analise_comentarios_cobranca.md")

    # Gera análise da IA sobre os comentários
    analise_comentarios = analise_openai(
        df_atual=comentarios_semana_atual,
        df_past=comentarios_semana_anterior,
        dias_restantes=dias_restantes,
        valor_extra=incidentes_nominais,
        prompt=prompt_comentarios
        )

    try:
        # Executar análise WOZ específica para o setor atual
        analise_woz = analisar_volume_woz(df_2, setor)

        # Gerar análise WOZ com IA
        analise_woz_ia = gerar_analise_woz_ia(analise_woz)

    except Exception as e:
        print(f"❌ ERRO na análise WOZ do setor '{setor}': {str(e)}")
        print(f"Tipo do erro: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        # Usar dados vazios para não interromper o PDF
        analise_woz = {
            'semana_atual': {},
            'semana_anterior': {},
            'comparacao': {},
            'taxa_resolucao_atual': {},
            'taxa_resolucao_anterior': {}
        }
        analise_woz_ia = "Análise WOZ não disponível devido a erro no processamento."

    # Gere o PDF
    gerar_pdf(
        nome_arquivo=nome_pdf,
        metricas_total = df_media_anual,
        metricas=df_semana_atual,
        metricas_sm=df_semana_ant,
        metricas_canais=df_resultado_semana_atual,
        metricas_canais_sm=df_resultado_semana_anterior,
        df_media_anual_canais=df_resultado_media_anual,
        metricas_equipes=df_resultado_semana_atual_equipes if setor == 'Suporte' else None,
        metricas_equipes_sm=df_resultado_semana_anterior_equipes if setor == 'Suporte' else None,
        metricas_media_anual=df_resultado_media_anual_equipes if setor == 'Suporte' else None,
        metricas_nps=nps_semana_atual,
        metricas_nps_sm=nps_semana_anterior,
        metricas_nps_anual=nps_media_anual,
        setor=setor,
        periodo=periodo,
        content_md_first_anl=analise_semanal,
        content_md_second_anl = analise_total,
        content_md_third_anl= analise_nps,
        content_md_fourth_anl=analise_comentarios,
        analise_woz=analise_woz,
        analise_woz_ia=analise_woz_ia,
        incidentes_dados=incidentes_brutos
        )

    print(f"✅ PDF gerado com sucesso para o setor: {setor}")
    print(f"Arquivo: {nome_pdf}")

    # Aguardar um momento para garantir que o arquivo está completamente escrito no disco
    time.sleep(1)

    # Verificar se o arquivo existe e tem tamanho válido
    if os.path.exists(nome_pdf):
        tamanho = os.path.getsize(nome_pdf)
        if tamanho > 0:
            print(f"   Arquivo validado: {tamanho} bytes")
        else:
            logger.warning(f"Arquivo PDF gerado está vazio: {nome_pdf}")
            print(f"⚠️ AVISO: Arquivo PDF está vazio, mas continuando...")
    else:
        logger.error(f"Arquivo PDF não encontrado após geração: {nome_pdf}")
        print(f"❌ ERRO: Arquivo PDF não encontrado após geração!")

    # Armazenar informações do PDF gerado para envio posterior
    pdfs_gerados.append({
        'arquivo': nome_pdf,
        'setor': setor,
        'periodo': periodo
    })

    print(f"=== FINALIZANDO PROCESSAMENTO DO SETOR: {setor} ===\n")

# Enviar todos os PDFs em um único email após processar todos os setores
if pdfs_gerados and destinatarios_email:
    print(f"\n📧 Preparando envio de {len(pdfs_gerados)} PDF(s) recém-gerado(s) por email...")
    for idx, pdf_info in enumerate(pdfs_gerados, 1):
        nome_arquivo = os.path.basename(pdf_info['arquivo'])
        print(f"   [{idx}] {nome_arquivo} (Setor: {pdf_info['setor']})")
        # Verificar se o arquivo existe antes de enviar
        if os.path.exists(pdf_info['arquivo']):
            tamanho = os.path.getsize(pdf_info['arquivo'])
            print(f"       Arquivo existe: {tamanho} bytes")
        else:
            print(f"       ⚠️ AVISO: Arquivo não encontrado!")
    print(f"   Destinatários: {len(destinatarios_email)}")
    if destinatarios_bcc:
        print(f"   BCC: {len(destinatarios_bcc)} destinatário(s)")
    # Aguardar um momento adicional antes de enviar para garantir que tudo está pronto
    print("   Aguardando estabilização dos arquivos...")
    time.sleep(5)
    # Usar o período do primeiro PDF (todos devem ter o mesmo período)
    periodo_email = pdfs_gerados[0]['periodo']
    enviar_email_pdf(pdfs_gerados, periodo_email, destinatarios_email, bcc=destinatarios_bcc if destinatarios_bcc else None)
elif not destinatarios_email:
    print("ℹ️ Nenhum destinatário de email configurado. PDFs não serão enviados por email.")
elif not pdfs_gerados:
    print("ℹ️ Nenhum PDF foi gerado. Nada para enviar por email.")

# Fechar conexão com banco de dados
try:
    conn.close()
    engine.dispose()
    print("Conexão com banco de dados encerrada.")
except Exception as e:
    print(f"Erro ao fechar conexão com banco: {e}")

