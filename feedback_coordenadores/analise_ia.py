import pandas as pd
import google.generativeai as genai
from conecta_banco import *
import time
from datetime import datetime
import json
import logging
import re
from functools import lru_cache
from sqlalchemy import text
from pathlib import Path

sql_path = Path(__file__).parent
resposta_path = Path(__file__).parent / "resposta_nps_gemini.html"
analistas_criticos_dir = Path(__file__).parent / "analistas_criticos"

# Criar diretório de analistas críticos se não existir
analistas_criticos_dir.mkdir(exist_ok=True)

# Configurar logger para análise de IA
logger = logging.getLogger('nps_monitor.analise_ia')

"""
SISTEMA DE TABELAS COLORIDAS AUTOMÁTICAS
=========================================

As tabelas markdown geradas pela IA são automaticamente convertidas para HTML
com cores específicas por coluna, baseadas no tipo de tabela detectado:

1. TABELAS DE CASOS CRÍTICOS (4 colunas):
   - Cabeçalhos: Protocolo | Problema | Impacto no NPS | Ação Imediata/Sugerida
   - Cores: Azul claro | Laranja claro | Rosa claro | Verde claro
   - Classe CSS: tabela-casos-criticos

2. TABELAS DE RECOMENDAÇÕES (3 colunas):
   - Cabeçalhos: Prioridade | Dimensão NPS | Ação Específica
   - Cores: Laranja claro | Azul claro | Verde claro
   - Classe CSS: tabela-recomendacoes

3. TABELAS DE COMENTÁRIOS NPS (4 colunas):
   - Cabeçalhos: Protocolo | Notas Críticas | Comentário do Cliente | Correlação
   - Cores: Azul claro | Laranja claro | Roxo claro | Verde claro
   - Classe CSS: tabela-comentarios-nps

4. TABELAS DE ANÁLISE (5 colunas - padrão):
   - Cores por coluna: Azul | Laranja | Rosa | Roxo | Verde
   - Classe CSS: tabela-analise

A detecção automática acontece na função converter_tabela_markdown_para_html_cached()
baseada nos cabeçalhos das colunas.
"""

def criar_indice_analistas(dir_analistas):
    """
    Cria um arquivo índice HTML listando todos os analistas analisados
    
    Args:
        dir_analistas (Path): Diretório onde estão os arquivos dos analistas
    """
    try:
        # Listar todos os arquivos HTML no diretório
        arquivos_html = sorted([f for f in dir_analistas.glob("*.html") if f.name != "index.html"])
        
        if not arquivos_html:
            logger.debug("Nenhum arquivo de analista encontrado para criar índice")
            return
        
        # Criar conteúdo do índice
        html_indice = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Índice - Analistas Críticos</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 900px;
            margin: 40px auto;
            background-color: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        
        h1 {
            color: #2c3e50;
            border-bottom: 4px solid #667eea;
            padding-bottom: 15px;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-align: center;
        }
        
        .info-box {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            border-left: 4px solid #667eea;
        }
        
        .info-box p {
            margin: 5px 0;
            color: #555;
        }
        
        .analista-list {
            list-style: none;
            padding: 0;
        }
        
        .analista-item {
            background-color: #fff;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
            overflow: hidden;
        }
        
        .analista-item:hover {
            border-color: #667eea;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            transform: translateY(-2px);
        }
        
        .analista-link {
            display: flex;
            align-items: center;
            padding: 20px;
            text-decoration: none;
            color: #333;
        }
        
        .analista-icon {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            font-weight: bold;
            margin-right: 20px;
            flex-shrink: 0;
        }
        
        .analista-info {
            flex: 1;
        }
        
        .analista-nome {
            font-size: 1.3em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        .analista-arquivo {
            font-size: 0.9em;
            color: #777;
        }
        
        .arrow {
            font-size: 24px;
            color: #667eea;
            transition: transform 0.3s ease;
        }
        
        .analista-item:hover .arrow {
            transform: translateX(5px);
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            color: #777;
            font-size: 0.9em;
        }
        
        .contador {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            display: inline-block;
            font-weight: 600;
            margin-bottom: 20px;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            
            h1 {
                font-size: 2em;
            }
            
            .analista-link {
                padding: 15px;
            }
            
            .analista-icon {
                width: 40px;
                height: 40px;
                font-size: 20px;
                margin-right: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Analistas Críticos - NPS</h1>
        
        <div class="info-box">
            <p><strong>📅 Período de Análise:</strong> Conforme cada relatório individual</p>
            <p><strong>🎯 Critério:</strong> Analistas com NPS abaixo da meta (&lt; 70)</p>
        </div>
        
        <div class="contador">
            Total de Analistas: """ + str(len(arquivos_html)) + """
        </div>
        
        <ul class="analista-list">
"""
        
        # Adicionar cada analista à lista
        for arquivo in arquivos_html:
            nome_analista = arquivo.stem  # Nome do arquivo sem extensão
            # Primeira letra maiúscula para o ícone
            inicial = nome_analista[0].upper() if nome_analista else "A"
            
            html_indice += f"""            <li class="analista-item">
                <a href="{arquivo.name}" class="analista-link">
                    <div class="analista-icon">{inicial}</div>
                    <div class="analista-info">
                        <div class="analista-nome">{nome_analista}</div>
                        <div class="analista-arquivo">{arquivo.name}</div>
                    </div>
                    <div class="arrow">→</div>
                </a>
            </li>
"""
        
        html_indice += """        </ul>
        
        <div class="footer">
            <p>Gerado automaticamente pelo Sistema de Monitoramento NPS</p>
            <p>Para mais informações, consulte a documentação do projeto</p>
        </div>
    </div>
</body>
</html>"""
        
        # Salvar arquivo índice
        indice_path = dir_analistas / "index.html"
        with open(indice_path, 'w', encoding='utf-8') as f:
            f.write(html_indice)
        
        logger.info(f"✅ Índice de analistas criado: {indice_path.name} ({len(arquivos_html)} analistas)")
        
    except Exception as e:
        logger.error(f"Erro ao criar índice de analistas: {str(e)}")

@lru_cache(maxsize=128)
def converter_tabela_markdown_para_html_cached(linhas_tabela_tuple):
    """
    Versão cacheada da conversão de tabela markdown para HTML
    Usa tupla como entrada pois listas não são hasheáveis
    
    Args:
        linhas_tabela_tuple (tuple): Tupla de linhas da tabela em formato markdown
        
    Returns:
        str: Tabela HTML formatada
    """
    linhas_tabela = list(linhas_tabela_tuple)
    if len(linhas_tabela) < 2:
        return '\n'.join(linhas_tabela)
    
    # Processar cabeçalho (primeira linha)
    cabecalho = linhas_tabela[0]
    colunas_header = [col.strip() for col in cabecalho.split('|') if col.strip()]
    
    # Detectar tipo de tabela baseado nos cabeçalhos
    cabecalho_lower = ' '.join([col.lower().replace('**', '').replace('*', '') for col in colunas_header])
    
    # Determinar classe CSS baseada no conteúdo dos cabeçalhos
    classe_tabela = "tabela-analise"  # padrão
    
    if len(colunas_header) == 4:
        if 'protocolo' in cabecalho_lower and 'problema' in cabecalho_lower and 'impacto' in cabecalho_lower:
            classe_tabela = "tabela-casos-criticos"
        elif 'protocolo' in cabecalho_lower and 'notas' in cabecalho_lower and 'comentário' in cabecalho_lower:
            classe_tabela = "tabela-comentarios-nps"
        # Tabela de recomendações pode ter 4 colunas também (Prioridade, Dimensão, Ação, Impacto)
        elif ('prioridade' in cabecalho_lower or 'dimensão' in cabecalho_lower) and 'recomendação' in cabecalho_lower:
            classe_tabela = "tabela-recomendacoes"
    elif len(colunas_header) == 3:
        # Recomendações podem ter diferentes combinações de colunas
        if ('prioridade' in cabecalho_lower or 'dimensão' in cabecalho_lower) or \
           ('recomendação' in cabecalho_lower and 'ação' in cabecalho_lower):
            classe_tabela = "tabela-recomendacoes"
    
    html_tabela = f'<table class="{classe_tabela}">\n'
    
    html_tabela += '  <thead>\n    <tr>\n'
    for i, col in enumerate(colunas_header):
        # Remover asteriscos do cabeçalho
        col_limpo = col.replace('**', '').replace('*', '')
        html_tabela += f'      <th>{col_limpo}</th>\n'
    html_tabela += '    </tr>\n  </thead>\n'
    
    # Pular linha separadora (|---|---|)
    # Processar linhas de dados (a partir da terceira linha)
    html_tabela += '  <tbody>\n'
    for linha in linhas_tabela[2:]:
        if '|' in linha:
            colunas = [col.strip() for col in linha.split('|') if col.strip()]
            if colunas:
                html_tabela += '    <tr>\n'
                for i, col in enumerate(colunas):
                    html_tabela += f'      <td>{col}</td>\n'
                html_tabela += '    </tr>\n'
    
    html_tabela += '  </tbody>\n</table>\n'
    
    return html_tabela

def converter_tabela_markdown_para_html(linhas_tabela):
    """
    Wrapper não cacheado que converte lista em tupla para usar a versão cacheada
    
    Args:
        linhas_tabela (list): Lista de linhas da tabela em formato markdown
        
    Returns:
        str: Tabela HTML formatada
    """
    return converter_tabela_markdown_para_html_cached(tuple(linhas_tabela))

@lru_cache(maxsize=256)
def converter_markdown_para_html(texto_markdown):
    """
    Converte texto markdown para HTML formatado
    
    Args:
        texto_markdown (str): Texto em formato markdown
        
    Returns:
        str: Texto convertido em HTML
    """
    # Detectar e converter tabelas primeiro
    lines = texto_markdown.split('\n')
    resultado_lines = []
    i = 0
    
    while i < len(lines):
        linha = lines[i]
        
        # Detectar início de tabela (linha com múltiplos |)
        if linha.count('|') >= 3 and i + 1 < len(lines):
            # Verificar se a próxima linha é um separador (formato padrão)
            proxima = lines[i + 1]
            if '|---' in proxima or '|:--' in proxima or '| :--' in proxima or '|---' in proxima.replace(' ', ''):
                # Coletar todas as linhas da tabela
                linhas_tabela = [linha]
                j = i + 1
                while j < len(lines) and '|' in lines[j]:
                    linhas_tabela.append(lines[j])
                    j += 1
                
                # Converter tabela
                tabela_html = converter_tabela_markdown_para_html(linhas_tabela)
                resultado_lines.append(tabela_html)
                i = j
                continue
            
            # Detecção alternativa: se não tem separador mas tem várias linhas consecutivas com |
            # (algumas IAs geram tabelas sem a linha separadora)
            elif i + 2 < len(lines) and lines[i + 2].count('|') >= 3:
                # Coletar todas as linhas consecutivas com pipe
                linhas_tabela = []
                j = i
                while j < len(lines) and lines[j].strip() and '|' in lines[j]:
                    linhas_tabela.append(lines[j])
                    j += 1
                
                # Se coletou pelo menos 3 linhas, considerar como tabela
                if len(linhas_tabela) >= 3:
                    # Adicionar linha separadora se não existir
                    if not ('|---' in linhas_tabela[1] or '|:--' in linhas_tabela[1]):
                        # Contar colunas da primeira linha
                        num_colunas = linhas_tabela[0].count('|') - 1
                        separador = '| ' + ' | '.join(['---'] * num_colunas) + ' |'
                        linhas_tabela.insert(1, separador)
                    
                    # Converter tabela
                    tabela_html = converter_tabela_markdown_para_html(linhas_tabela)
                    resultado_lines.append(tabela_html)
                    i = j
                    continue
        
        resultado_lines.append(linha)
        i += 1
    
    # Reunir texto com tabelas já convertidas
    html = '\n'.join(resultado_lines)
    
    # Headers (## para h2, ### para h3, etc)
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # Negrito com asteriscos (*texto*)
    html = re.sub(r'\*(.*?)\*', r'<strong>\1</strong>', html)
    
    # Links markdown [texto](url)
    html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html)
    
    # Listas numeradas
    lines = html.split('\n')
    in_ordered_list = False
    result_lines = []
    
    for line in lines:
        # Detectar lista numerada (começa com número seguido de ponto)
        if re.match(r'^\d+\.\s+', line):
            if not in_ordered_list:
                result_lines.append('<ol>')
                in_ordered_list = True
            # Extrair conteúdo do item
            content = re.sub(r'^\d+\.\s+', '', line)
            result_lines.append(f'<li>{content}</li>')
        else:
            if in_ordered_list:
                result_lines.append('</ol>')
                in_ordered_list = False
            result_lines.append(line)
    
    # Fechar lista se terminou com ela
    if in_ordered_list:
        result_lines.append('</ol>')
    
    html = '\n'.join(result_lines)
    
    # Listas não numeradas (bullet points com •, -, *)
    lines = html.split('\n')
    in_unordered_list = False
    result_lines = []
    
    for line in lines:
        # Detectar lista não numerada
        if re.match(r'^[•\-\*]\s+', line):
            if not in_unordered_list:
                result_lines.append('<ul>')
                in_unordered_list = True
            # Extrair conteúdo do item
            content = re.sub(r'^[•\-\*]\s+', '', line)
            result_lines.append(f'<li>{content}</li>')
        else:
            if in_unordered_list:
                result_lines.append('</ul>')
                in_unordered_list = False
            result_lines.append(line)
    
    # Fechar lista se terminou com ela
    if in_unordered_list:
        result_lines.append('</ul>')
    
    html = '\n'.join(result_lines)
    
    # Linhas horizontais (---)
    html = re.sub(r'^---+$', '<hr>', html, flags=re.MULTILINE)
    
    # Parágrafos (linhas não vazias que não são tags HTML)
    lines = html.split('\n')
    result_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('<') and not stripped.endswith('>'):
            # Se não é uma tag HTML, envolver em parágrafo
            if not any(tag in stripped for tag in ['<h1>', '<h2>', '<h3>', '<li>', '<ol>', '<ul>', '<hr>', '</ol>', '</ul>']):
                result_lines.append(f'<p>{line}</p>')
            else:
                result_lines.append(line)
        else:
            result_lines.append(line)
    
    html = '\n'.join(result_lines)
    
    return html

def extrair_secoes_analise(texto_completo):
    """
    Extrai as seções específicas da análise de IA do markdown gerado
    
    Args:
        texto_completo (str): Texto completo da análise gerada pela IA
        
    Returns:
        dict: Dicionário com as seções extraídas
    """
    secoes = {
        'resumo_geral': '',
        'problemas_nps': '',
        'padroes_comportamentais': '',
        'comentarios_vs_conversas': '',
        'recomendacoes_melhoria': '',
        'casos_criticos': ''
    }
    
    try:
        # Definir delimitadores das seções
        delimitadores = [
            (r'\*Resumo Geral\*', r'\*Problemas Identificados por Dimensão NPS\*'),
            (r'\*Problemas Identificados por Dimensão NPS\*', r'\*Padrões Comportamentais dos Analistas\*'),
            (r'\*Padrões Comportamentais dos Analistas\*', r'\*Comentários NPS vs Conversas\*'),
            (r'\*Comentários NPS vs Conversas\*', r'\*Recomendações de Melhoria\*'),
            (r'\*Recomendações de Melhoria\*', r'\*Casos Críticos\*'),
            (r'\*Casos Críticos\*', r'$')  # Até o final do texto
        ]
        
        chaves_secoes = list(secoes.keys())
        
        for i, (inicio, fim) in enumerate(delimitadores):
            # Usar regex para encontrar o conteúdo entre os delimitadores
            if fim == r'$':
                # Para a última seção, capturar até o final
                padrao = rf'{inicio}\s*(.*?)(?:\Z|\n\s*$)'
            else:
                padrao = rf'{inicio}\s*(.*?)\s*{fim}'
            
            match = re.search(padrao, texto_completo, re.DOTALL | re.IGNORECASE)
            
            if match:
                conteudo = match.group(1).strip()
                # Remover linhas vazias no início e fim
                conteudo = re.sub(r'^\s*\n|\n\s*$', '', conteudo)
                secoes[chaves_secoes[i]] = conteudo
                
                logger.debug(f"✅ Seção '{chaves_secoes[i]}' extraída: {len(conteudo)} caracteres")
            else:
                logger.warning(f"❌ Seção '{chaves_secoes[i]}' não encontrada")
        
        # Verificar se pelo menos uma seção foi extraída
        secoes_com_conteudo = sum(1 for v in secoes.values() if v.strip())
        logger.info(f"📊 Extração concluída: {secoes_com_conteudo}/6 seções encontradas")
        
        return secoes
        
    except Exception as e:
        logger.error(f"Erro ao extrair seções: {str(e)}")
        return secoes

def analise_ia_nps(dataset, data_inicial, data_fim, analistas_criticos, lista_protocolos, setor='Não identificado'):
    """
    Analisa conversas de analistas com NPS baixo usando Gemini AI
    
    Args:
        dataset: Texto com conversas dos analistas
        data_inicial: Data inicial do período
        data_fim: Data final do período
        analistas_criticos: Lista de analistas com NPS baixo
        lista_protocolos: Lista de protocolos analisados
        setor: Setor do analista (padrão: 'Não identificado')
    
    Returns:
        str: Resposta da análise de IA
    """
    from textwrap import dedent

    from config import config
    
    tabela = 'rawdata_analise_nps_analistas'
    schema = config.DB_SCHEMA
    
    # Carregar chave da API do Gemini do arquivo .env
    api_key = config.GEMINI_API_KEY
    
    if not api_key:
        logger.error("❌ GEMINI_API_KEY não configurada no arquivo .env")
        raise ValueError("GEMINI_API_KEY não encontrada. Configure o arquivo .env")
    
    # Inicializar variáveis de conexão - serão fechadas no finally
    engine = None
    conn = None
    
    # Configurar a API do Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(config.GEMINI_MODEL)

    # Limita o tamanho do dataset (para segurança e custo)
    max_size = config.ANALISE_MAX_DATASET_SIZE
    if len(dataset) > max_size:
        dataset = dataset[:max_size] + '\n... (dataset truncado para análise)'
        logger.debug(f"Dataset truncado para {max_size} caracteres")

    # Prompt especializado para análise de NPS
    prompt_estrutura = dedent("""
        Analisar cuidadosamente o dataset fornecido abaixo:

        <dataset>
        {dataset}
        </dataset>
        
        **CONTEXTO IMPORTANTE:**
        Este dataset contém conversas de atendimento de analistas que receberam avaliações NPS BAIXAS (abaixo de 70) dos clientes. 
        Cada registro mostra:
        - NOTAS NPS: Velocidade, Solução, Relacionamento (escala 0-10)
        - Comentários NPS dos clientes
        - Conversas completas entre Cliente e Analista
        
        O formato das conversas é:
        - [data hora] Cliente: mensagem do cliente
        - [data hora] Analista: resposta do analista

        **OBJETIVO:** Identificar padrões e causas das avaliações NPS baixas para melhorar o atendimento.

        #Instruções de formatação
        A resposta deve seguir exatamente as seguintes formatações:
        
        1. Formate os títulos em *negrito*, utilizando **apenas um asterisco** (ex: *Título*).
        2. Destaque *números* e *percentuais* usando asterisco (ex: *34.5%*).
        3. Use listas numeradas para organizar informações.
        4. Sempre se refira ao dataset como "conversas analisadas".
        5. **IMPORTANTE - Formatação de Tabelas:**
           - Para tabelas de **Casos Críticos**: Use markdown com 4 colunas (Protocolo | Problema | Impacto no NPS | Ação Imediata Sugerida)
           - Para tabelas de **Recomendações**: Use markdown com 3 colunas (Prioridade | Dimensão NPS | Ação Específica)
           - Para tabelas de **Comentários NPS vs Conversas**: Use markdown com 4 colunas (Protocolo | Notas Críticas | Comentário do Cliente | Correlação)
           - As tabelas serão automaticamente convertidas para HTML com cores específicas por coluna
           - Use formatação markdown padrão para tabelas (| Coluna1 | Coluna2 |)
        
        #Solicitações de Análise:
        
        1. **Título:** *Análise de Conversas com NPS Baixo*
        
        2. **Resumo Geral:**
           - Informe quantos protocolos/conversas foram analisados
           - Identifique os analistas mencionados
           - Destaque as notas NPS mais críticas encontradas
        
        3. **Problemas Identificados por Dimensão NPS:**
           
           *Velocidade de Atendimento:*
           - Identifique padrões de demora nas respostas
           - Analise tempo entre mensagens do cliente e analista
           - Destaque casos onde clientes reclamaram de demora
           
           *Qualidade da Solução:*
           - Identifique casos onde problemas não foram resolvidos
           - Analise respostas técnicas inadequadas ou incompletas
           - Destaque situações onde clientes ficaram insatisfeitos com a solução
           
           *Relacionamento/Atendimento:*
           - Identifique problemas de comunicação
           - Analise tom e cordialidade nas respostas
           - Destaque casos de atendimento impessoal ou inadequado

        4. **Padrões Comportamentais dos Analistas:**
           {padrao_analistas}
           - Analise {estilo_analise}
           - Destaque {tipo_comportamentos} que podem estar causando NPS baixo

        5. **Comentários NPS vs Conversas:**
           - Correlacione os comentários NPS com o que aconteceu nas conversas
           - Identifique discrepâncias entre o que foi dito e como foi avaliado
           - Analise se as expectativas dos clientes foram atendidas

        6. **Recomendações de Melhoria:**
           - Sugira ações específicas para melhorar Velocidade
           - Sugira ações específicas para melhorar Solução
           - Sugira ações específicas para melhorar Relacionamento
           - Priorize as recomendações por impacto no NPS

        7. **Casos Críticos:**
           - Destaque os *3 casos mais críticos* encontrados
           - Para cada caso, explique: Protocolo, Problema, Impacto no NPS
           - Sugira ação imediata para cada caso crítico

        **IMPORTANTE:** Seja específico e actionável nas recomendações. O objetivo é que os gestores possam tomar ações concretas para melhorar o NPS dos analistas.
    """)

    # Personalizar prompt baseado se é um ou múltiplos analistas
    if len(analistas_criticos) == 1:
        padrao_analistas = f"- Foque na análise específica do analista: {analistas_criticos[0]}"
        estilo_analise = "o estilo de atendimento específico"
        tipo_comportamentos = "comportamentos específicos"
    else:
        padrao_analistas = "- Identifique padrões específicos por analista"
        estilo_analise = "diferenças na forma de atender entre analistas"
        tipo_comportamentos = "comportamentos"
    
    prompt_mensagem = prompt_estrutura.format(
        dataset=dataset,
        padrao_analistas=padrao_analistas,
        estilo_analise=estilo_analise,
        tipo_comportamentos=tipo_comportamentos
    )

    # Variável para armazenar o prompt atual (pode ser modificado no retry)
    prompt_atual = prompt_mensagem
    max_tentativas = config.ANALISE_MAX_TENTATIVAS
    
    try:
        # Estabelecer conexões ao banco
        engine = get_sqlalchemy_engine()
        conn = get_psycopg2_connection()
        
        for tentativa in range(max_tentativas):
            try:
                logger.info(f"Enviando para análise de IA... (Tentativa {tentativa + 1})")
                logger.debug(f"Prompt size: {len(prompt_atual)} caracteres")
                
                # Gerar resposta usando o Gemini
                response = model.generate_content(prompt_atual)
                
                if response.text:
                    resposta_conteudo = response.text
                    current_time = datetime.now()
                    
                    logger.info(f"✅ Resposta recebida da IA - {len(resposta_conteudo)} caracteres")
                    logger.info(f"📂 Setor do analista: {setor}")
                    
                    # Extrair seções da análise para validação
                    logger.info("🔍 Extraindo seções da análise...")
                    secoes_extraidas = extrair_secoes_analise(resposta_conteudo)
                    
                    # Converter cada seção de markdown para HTML
                    logger.info("🔄 Convertendo seções para HTML...")
                    secoes_html = {}
                    for nome_secao, conteudo_md in secoes_extraidas.items():
                        if conteudo_md.strip():
                            # Converter markdown para HTML
                            secoes_html[nome_secao] = converter_markdown_para_html(conteudo_md)
                            logger.debug(f"  ✓ {nome_secao}: {len(conteudo_md)} → {len(secoes_html[nome_secao])} chars")
                        else:
                            secoes_html[nome_secao] = ''
                    
                    # Contar quantas seções foram extraídas com sucesso
                    secoes_validas = sum(1 for v in secoes_extraidas.values() if v.strip())
                
                # Se menos de 4 seções foram extraídas, a análise não seguiu o formato
                if secoes_validas < 4 and tentativa < 2:  # Permite retry nas 2 primeiras tentativas
                    logger.warning(f"⚠️  Apenas {secoes_validas}/6 seções extraídas. Formato inadequado da IA.")
                    logger.info(f"🔄 Refazendo análise com prompt mais específico... (Tentativa {tentativa + 2})")
                    
                    # Aguardar um pouco mais antes de tentar novamente
                    time.sleep(config.ANALISE_DELAY_TENTATIVA)
                    
                    # Reformular o prompt sendo MUITO mais enfático sobre o formato
                    prompt_atual = f"""
IMPORTANTE: Sua resposta DEVE seguir EXATAMENTE o formato especificado com os títulos EXATOS abaixo.
Use EXATAMENTE estes títulos (copie e cole):

*Resumo Geral*
(seu conteúdo aqui)

*Problemas Identificados por Dimensão NPS*
(seu conteúdo aqui)

*Padrões Comportamentais dos Analistas*
(seu conteúdo aqui)

*Comentários NPS vs Conversas*
(seu conteúdo aqui)

*Recomendações de Melhoria*
(seu conteúdo aqui)

*Casos Críticos*
(seu conteúdo aqui)

AGORA ANALISE OS DADOS ABAIXO:

{prompt_mensagem}
"""
                    # Tentar novamente com o prompt reformulado
                    logger.debug("Enviando prompt reformulado para a IA...")
                    continue  # Volta para o início do loop de tentativas
                
                # Para compatibilidade com o banco de dados existente
                request_id = f"gemini-nps-{int(current_time.timestamp())}"
                model_name = config.GEMINI_MODEL
                
                # Estimativas de tokens (Gemini não fornece contagem exata como OpenAI)
                token_prompt = len(prompt_mensagem.split()) * 1.3  # Estimativa
                token_completion = len(resposta_conteudo.split()) * 1.3  # Estimativa
                
                time.sleep(2)  # Delay menor que OpenAI

                # Preparar conteúdo markdown
                conteudo_markdown = f"# Análise de NPS - {data_inicial} a {data_fim}\n\n"
                conteudo_markdown += f"**Analistas Analisados:** {', '.join(analistas_criticos) if analistas_criticos else 'N/A'}\n\n"
                conteudo_markdown += f"**Total de Protocolos:** {len(lista_protocolos)}\n\n"
                conteudo_markdown += "---\n\n"
                conteudo_markdown += resposta_conteudo
                
                # Converter conteúdo para HTML
                conteudo_html = converter_markdown_para_html(conteudo_markdown)
                
                # Verificar se é análise individual para adicionar botão de voltar
                botao_voltar = ""
                if analistas_criticos and len(analistas_criticos) == 1:
                    botao_voltar = """
        <div class="back-button-container">
            <a href="index.html" class="back-button">← Voltar ao Índice</a>
        </div>
"""
                
                # Criar documento HTML completo com CSS
                html_completo = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análise de NPS - {data_inicial} a {data_fim}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        
        .back-button-container {{
            max-width: 1200px;
            margin: 0 auto 10px auto;
        }}
        
        .back-button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        .back-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(102, 126, 234, 0.3);
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 25px;
            font-size: 2.2em;
        }}
        
        h2 {{
            color: #34495e;
            margin-top: 35px;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        
        h3 {{
            color: #5a6c7d;
            margin-top: 25px;
            margin-bottom: 15px;
            font-size: 1.4em;
        }}
        
        p {{
            margin-bottom: 15px;
            text-align: justify;
        }}
        
        strong {{
            color: #e74c3c;
            font-weight: 600;
        }}
        
        ul, ol {{
            margin-left: 30px;
            margin-bottom: 20px;
        }}
        
        li {{
            margin-bottom: 10px;
            line-height: 1.8;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 30px 0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.9em;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        table thead tr {{
            background-color: #3498db;
            color: white;
            text-align: left;
        }}
        
        table th,
        table td {{
            padding: 12px 15px;
            border: 1px solid #ddd;
        }}
        
        table tbody tr {{
            border-bottom: 1px solid #dddddd;
        }}
        
        table tbody tr:nth-of-type(even) {{
            background-color: #f8f9fa;
        }}
        
        table tbody tr:hover {{
            background-color: #e3f2fd;
        }}
        
        /* Tabela de Análise - Cores por Coluna */
        .tabela-analise {{
            font-size: 0.95em;
        }}
        
        .tabela-analise th.col-0,
        .tabela-analise td.col-0 {{
            background-color: #e3f2fd;
            font-weight: 600;
            text-align: center;
            width: 5%;
        }}
        
        .tabela-analise th.col-1,
        .tabela-analise td.col-1 {{
            background-color: #fff3e0;
            font-weight: 600;
            width: 12%;
        }}
        
        .tabela-analise th.col-2,
        .tabela-analise td.col-2 {{
            background-color: #fce4ec;
            width: 28%;
        }}
        
        .tabela-analise th.col-3,
        .tabela-analise td.col-3 {{
            background-color: #f3e5f5;
            width: 28%;
        }}
        
        .tabela-analise th.col-4,
        .tabela-analise td.col-4 {{
            background-color: #e8f5e9;
            width: 27%;
        }}
        
        .tabela-analise thead th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        .tabela-analise tbody tr:hover td {{
            filter: brightness(0.95);
            transition: all 0.2s ease;
        }}
        
        .tabela-analise td {{
            vertical-align: top;
            line-height: 1.6;
        }}
        
        .tabela-analise strong {{
            color: #d32f2f;
            font-weight: 700;
        }}
        
        /* Tabela de Recomendações - Cores por Coluna */
        .tabela-recomendacoes {{
            font-size: 0.9em;
        }}
        
        .tabela-recomendacoes th:nth-child(1),
        .tabela-recomendacoes td:nth-child(1) {{
            background-color: #fff3e0;
            font-weight: 600;
            text-align: center;
            width: 15%;
        }}
        
        .tabela-recomendacoes th:nth-child(2),
        .tabela-recomendacoes td:nth-child(2) {{
            background-color: #e1f5fe;
            font-weight: 600;
            text-align: center;
            width: 15%;
        }}
        
        .tabela-recomendacoes th:nth-child(3),
        .tabela-recomendacoes td:nth-child(3) {{
            background-color: #e8f5e9;
            width: 55%;
        }}
        
        /* 4ª coluna (se existir - ex: Impacto Estimado) */
        .tabela-recomendacoes th:nth-child(4),
        .tabela-recomendacoes td:nth-child(4) {{
            background-color: #f3e5f5;
            width: 20%;
        }}
        
        .tabela-recomendacoes thead th {{
            background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
            color: white;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        .tabela-recomendacoes tbody tr:hover td {{
            filter: brightness(0.95);
            transition: all 0.2s ease;
        }}
        
        .tabela-recomendacoes td {{
            vertical-align: top;
            line-height: 1.6;
        }}
        
        .tabela-recomendacoes strong {{
            color: #27ae60;
            font-weight: 700;
        }}
        
        /* Tabela de Casos Críticos - Cores por Coluna */
        .tabela-casos-criticos {{
            font-size: 0.9em;
        }}
        
        .tabela-casos-criticos th:nth-child(1),
        .tabela-casos-criticos td:nth-child(1) {{
            background-color: #e1f5fe;
            font-weight: 600;
            text-align: center;
            width: 12%;
        }}
        
        .tabela-casos-criticos th:nth-child(2),
        .tabela-casos-criticos td:nth-child(2) {{
            background-color: #fff3e0;
            width: 30%;
        }}
        
        .tabela-casos-criticos th:nth-child(3),
        .tabela-casos-criticos td:nth-child(3) {{
            background-color: #ffebee;
            width: 25%;
        }}
        
        .tabela-casos-criticos th:nth-child(4),
        .tabela-casos-criticos td:nth-child(4) {{
            background-color: #e8f5e9;
            width: 33%;
        }}
        
        .tabela-casos-criticos thead th {{
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: white;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        .tabela-casos-criticos tbody tr:hover td {{
            filter: brightness(0.95);
            transition: all 0.2s ease;
        }}
        
        .tabela-casos-criticos td {{
            vertical-align: top;
            line-height: 1.6;
        }}
        
        .tabela-casos-criticos strong {{
            color: #c62828;
            font-weight: 700;
        }}
        
        /* Tabela de Comentários NPS - Cores por Coluna */
        .tabela-comentarios-nps {{
            font-size: 0.9em;
        }}
        
        .tabela-comentarios-nps th:nth-child(1),
        .tabela-comentarios-nps td:nth-child(1) {{
            background-color: #e1f5fe;
            font-weight: 600;
            text-align: center;
            width: 10%;
        }}
        
        .tabela-comentarios-nps th:nth-child(2),
        .tabela-comentarios-nps td:nth-child(2) {{
            background-color: #fff3e0;
            text-align: center;
            width: 15%;
        }}
        
        .tabela-comentarios-nps th:nth-child(3),
        .tabela-comentarios-nps td:nth-child(3) {{
            background-color: #f3e5f5;
            width: 35%;
        }}
        
        .tabela-comentarios-nps th:nth-child(4),
        .tabela-comentarios-nps td:nth-child(4) {{
            background-color: #e8f5e9;
            width: 40%;
        }}
        
        .tabela-comentarios-nps thead th {{
            background: linear-gradient(135deg, #9c27b0 0%, #7b1fa2 100%);
            color: white;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        .tabela-comentarios-nps tbody tr:hover td {{
            filter: brightness(0.95);
            transition: all 0.2s ease;
        }}
        
        .tabela-comentarios-nps td {{
            vertical-align: top;
            line-height: 1.6;
        }}
        
        .tabela-comentarios-nps strong {{
            color: #7b1fa2;
            font-weight: 700;
        }}
        
        .meta-info {{
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }}
        
        .meta-info p {{
            margin-bottom: 5px;
        }}
        
        @media print {{
            body {{
                background-color: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
                padding: 20px;
            }}
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 20px;
            }}
            
            h1 {{
                font-size: 1.8em;
            }}
            
            h2 {{
                font-size: 1.4em;
            }}
        }}
    </style>
</head>
<body>
    {botao_voltar}
    <div class="container">
        {conteudo_html}
    </div>
</body>
</html>"""
                
                # Salvar resposta em arquivo HTML principal
                with open(resposta_path, 'w', encoding='utf-8') as arquivo:
                    arquivo.write(html_completo)
                
                # Salvar arquivo individual do analista na pasta analistas_criticos
                if analistas_criticos and len(analistas_criticos) > 0:
                    # Se for uma lista com apenas um analista
                    if isinstance(analistas_criticos, list) and len(analistas_criticos) == 1:
                        nome_analista = analistas_criticos[0]
                        # Sanitizar nome do arquivo (remover caracteres inválidos)
                        nome_arquivo_seguro = re.sub(r'[<>:"/\\|?*]', '_', nome_analista)
                        arquivo_analista_path = analistas_criticos_dir / f"{nome_arquivo_seguro}.html"
                        
                        with open(arquivo_analista_path, 'w', encoding='utf-8') as arquivo:
                            arquivo.write(html_completo)
                        logger.info(f"✅ Análise individual salva: {arquivo_analista_path.name}")
                        
                        # Atualizar índice de analistas
                        criar_indice_analistas(analistas_criticos_dir)
                    # Se for string (um analista)
                    elif isinstance(analistas_criticos, str):
                        nome_arquivo_seguro = re.sub(r'[<>:"/\\|?*]', '_', analistas_criticos)
                        arquivo_analista_path = analistas_criticos_dir / f"{nome_arquivo_seguro}.html"
                        
                        with open(arquivo_analista_path, 'w', encoding='utf-8') as arquivo:
                            arquivo.write(html_completo)
                        logger.info(f"✅ Análise individual salva: {arquivo_analista_path.name}")
                        
                        # Atualizar índice de analistas
                        criar_indice_analistas(analistas_criticos_dir)

                # Criar resposta JSON compatível com o formato OpenAI para o banco
                resposta_json = {
                    'id': request_id,
                    'model': model_name,
                    'usage': {
                        'prompt_tokens': int(token_prompt),
                        'completion_tokens': int(token_completion),
                        'total_tokens': int(token_prompt + token_completion)
                    },
                    'choices': [{
                        'message': {
                            'content': resposta_conteudo
                        }
                    }]
                }

                # Salvar no banco de dados
                df = pd.DataFrame({
                    'request': [current_time],
                    'dados_de': [data_inicial],
                    'dados_ate': [data_fim],
                    'lista_protocolos': [lista_protocolos],
                    'analistas_criticos': [analistas_criticos if isinstance(analistas_criticos, str) else ', '.join(analistas_criticos)],
                    'analise': ['monitoramento_nps_analistas'],
                    'setor': [setor],  # Usar o setor recebido como parâmetro
                    'input_text': [prompt_mensagem],
                    'request_id': [request_id],
                    'resposta_json': [json.dumps(resposta_json)],
                    'resposta_text': [resposta_conteudo],  # Markdown original
                    'token_prompt': [int(token_prompt)],
                    'token_completion': [int(token_completion)],
                    'model': [model_name]
                })
                
                # Log final do status da extração
                if secoes_validas < 4:
                    logger.warning(f"⚠️  ATENÇÃO: Salvando análise com apenas {secoes_validas}/6 seções extraídas após {tentativa + 1} tentativas")
                else:
                    logger.info(f"✅ Análise com {secoes_validas}/6 seções extraídas com sucesso")
                
                try:
                    # Inserção usando SQL direto para evitar problemas de compatibilidade
                    with conn.cursor() as cursor:
                        # Primeiro, obter o próximo ID manualmente
                        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM kinghost_octadesk.rawdata_analise_nps_analistas")
                        next_id = cursor.fetchone()[0]
                        
                        # Converter analistas_criticos corretamente (sem colchetes e aspas)
                        analistas_str = analistas_criticos if isinstance(analistas_criticos, str) else ', '.join(analistas_criticos)
                        protocolos_str = lista_protocolos if isinstance(lista_protocolos, str) else str(lista_protocolos)
                        
                        # Tentar inserir com as novas colunas (se existirem)
                        try:
                            insert_sql_completo = """
                            INSERT INTO kinghost_octadesk.rawdata_analise_nps_analistas 
                            (id, request, dados_de, dados_ate, analistas_criticos, lista_protocolos, 
                             analise, setor, input_text, request_id, resposta_json, resposta_text,
                             token_prompt, token_completion, model,
                             resumo_geral, problemas_nps, padroes_comportamentais,
                             comentarios_vs_conversas, recomendacoes_melhoria, casos_criticos)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(insert_sql_completo, (
                                next_id, current_time, data_inicial, data_fim, 
                                analistas_str, protocolos_str,
                                'NPS', setor, prompt_mensagem, request_id,
                                json.dumps(resposta_json),  # resposta_json
                                resposta_conteudo,  # resposta_text (markdown original)
                                int(token_prompt), int(token_completion), model_name,
                                secoes_html['resumo_geral'],  # HTML
                                secoes_html['problemas_nps'],  # HTML
                                secoes_html['padroes_comportamentais'],  # HTML
                                secoes_html['comentarios_vs_conversas'],  # HTML
                                secoes_html['recomendacoes_melhoria'],  # HTML
                                secoes_html['casos_criticos']  # HTML
                            ))
                            logger.info("✅ Análise salva com seções estruturadas em HTML!")
                            
                        except psycopg2.errors.UndefinedColumn as e:
                            # Se as colunas de seções não existem, usar inserção tradicional
                            logger.warning("⚠️  Colunas de seções não encontradas, usando inserção tradicional")
                            insert_sql = """
                            INSERT INTO kinghost_octadesk.rawdata_analise_nps_analistas 
                            (id, request, dados_de, dados_ate, analistas_criticos, lista_protocolos, 
                             analise, setor, input_text, request_id, resposta_json, resposta_text, 
                             token_prompt, token_completion, model)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(insert_sql, (
                                next_id, current_time, data_inicial, data_fim, 
                                analistas_str, protocolos_str,
                                'NPS', setor, prompt_mensagem, request_id,
                                json.dumps(resposta_json),
                                resposta_conteudo,  # markdown
                                int(token_prompt), int(token_completion), model_name
                            ))
                            logger.info("✅ Análise salva no formato tradicional (sem seções)")
                        
                        conn.commit()
                    logger.info("✅ Análise de IA salva no banco de dados")
                    
                    # Log das seções extraídas e convertidas para debug
                    logger.debug("📊 Seções salvas em HTML:")
                    for nome_secao, conteudo in secoes_html.items():
                        if conteudo.strip():
                            logger.debug(f"  - {nome_secao}: {len(conteudo)} caracteres (HTML)")
                    
                except Exception as db_error:
                    logger.error(f"Erro ao salvar no banco: {str(db_error)}")
                    logger.info("✅ Análise mantida apenas no arquivo HTML")
                    # Fazer rollback da transação abortada
                    try:
                        conn.rollback()
                        logger.debug("Rollback executado após erro no banco")
                    except Exception as rollback_error:
                        logger.warning(f"Erro ao fazer rollback: {str(rollback_error)}")

                logger.info("✅ Análise de IA salva no arquivo HTML")

                # Verificar se existe script SQL específico para NPS
                sql_nps_file = sql_path / 'insereDadosAnaliseNPS.sql'
                if sql_nps_file.exists():
                    try:
                        # Lê o script SQL específico para NPS
                        with open(sql_nps_file, 'r', encoding='utf-8') as file:
                            sql_script = file.read()
                        
                        # Executando o script SQL para processar dados usando psycopg2
                        with conn.cursor() as cursor:
                            cursor.execute(sql_script)
                            conn.commit()
                        logger.info("✅ Script SQL de processamento NPS executado com sucesso")
                    except Exception as sql_error:
                        # Extrair apenas a mensagem principal do erro, sem o SQL completo
                        error_msg = str(sql_error).split('\n')[0] if '\n' in str(sql_error) else str(sql_error)
                        logger.error(f"Erro ao executar script SQL de processamento: {error_msg}")
                        logger.debug(f"Script SQL que falhou: insereDadosAnaliseNPS.sql")
                        # Fazer rollback se houver erro
                        try:
                            conn.rollback()
                            logger.debug("Rollback executado após erro no script SQL")
                        except Exception as rollback_error:
                            logger.warning(f"Erro ao fazer rollback: {str(rollback_error)}")

                try:
                    conn.close()
                    engine.dispose()
                    logger.debug("Conexões fechadas com sucesso")
                except Exception as close_error:
                    logger.error(f"Erro ao fechar conexões: {str(close_error)}")
                
                    return resposta_conteudo
                    
                else:
                    logger.warning(f"Tentativa {tentativa + 1}: Resposta vazia do Gemini")
                    time.sleep(5)
            
            except genai.types.generation_types.StopCandidateException as e:
                logger.warning(f"Tentativa {tentativa + 1}: Conteúdo bloqueado por filtros de segurança")
                time.sleep(config.ANALISE_DELAY_TENTATIVA)
            except Exception as e:
                logger.error(f"Tentativa {tentativa + 1}: Erro na API do Gemini: {str(e)}")
                if "quota" in str(e).lower() or "rate" in str(e).lower() or "429" in str(e):
                    logger.warning("Quota excedida. Aguardando 2 minutos para tentar novamente...")
                    time.sleep(120)  # Aguardar 2 minutos quando houver erro de quota
                elif "safety" in str(e).lower():
                    logger.warning("Conteúdo bloqueado por filtros de segurança. Tentando novamente...")
                    time.sleep(config.ANALISE_DELAY_TENTATIVA)
                else:
                    logger.error("Erro desconhecido na API")
                    time.sleep(config.ANALISE_DELAY_TENTATIVA)
                
                if tentativa == max_tentativas - 1:  # Última tentativa
                    logger.error(f"❌ Todas as {max_tentativas} tentativas falharam")
                    return f"Erro: Não foi possível obter resposta do Gemini após {max_tentativas} tentativas."
        
        return "Erro: Análise não concluída."
    
    except psycopg2.OperationalError as e:
        logger.error(f"Erro de conexão com banco de dados (analise_ia): {str(e)}")
        return f"Erro: Falha de conexão com banco de dados - {str(e)}"
    except psycopg2.DatabaseError as e:
        logger.error(f"Erro de banco de dados (analise_ia): {str(e)}")
        return f"Erro: Erro de banco de dados - {str(e)}"
    except ValueError as e:
        # Captura erro de API Key não configurada
        logger.error(f"Erro de configuração: {str(e)}")
        return f"Erro: {str(e)}"
    except Exception as e:
        logger.error(f"Erro inesperado em analise_ia_nps: {str(e)}")
        logger.exception("Detalhes do erro:")
        return f"Erro: {str(e)}"
    finally:
        # Garantir que conexões sejam fechadas independentemente do resultado
        if conn is not None:
            try:
                conn.close()
                logger.debug("Conexão fechada (analise_ia_nps)")
            except Exception as e:
                logger.warning(f"Erro ao fechar conexão: {str(e)}")
        
        if engine is not None:
            try:
                engine.dispose()
                logger.debug("Engine disposed (analise_ia_nps)")
            except Exception as e:
                logger.warning(f"Erro ao fazer dispose da engine: {str(e)}")


def analise_comparativa_nps(analistas_criticos_dados, periodo_dias=30):
    """
    Análise comparativa entre analistas com NPS baixo e médio geral
    
    Args:
        analistas_criticos_dados: DataFrame com dados dos analistas críticos
        periodo_dias: Período para comparação (padrão 30 dias)
    
    Returns:
        str: Relatório comparativo
    """
    
    # Inicializar variáveis de conexão - serão fechadas no finally
    engine = None
    conn = None
    
    try:
        # Estabelecer conexões ao banco
        engine = get_sqlalchemy_engine()
        conn = get_psycopg2_connection()
        
        # Buscar dados gerais de NPS para comparação
        query_comparativa = f"""
        SELECT 
            "Analista",
            AVG(CAST("Velocidade" AS FLOAT)) as media_velocidade,
            AVG(CAST("Solução" AS FLOAT)) as media_solucao,
            AVG(CAST("Relacionamento" AS FLOAT)) as media_relacionamento,
            COUNT(*) as total_avaliacoes
        FROM kinghost_octadesk.vw_report_diario
        WHERE "Data Encerramento" >= (CURRENT_DATE - INTERVAL '{periodo_dias} days')
        AND "Velocidade" IS NOT NULL
        GROUP BY "Analista"
        HAVING COUNT(*) >= 3
        ORDER BY 
            (AVG(CAST("Velocidade" AS FLOAT)) + AVG(CAST("Solução" AS FLOAT)) + AVG(CAST("Relacionamento" AS FLOAT))) / 3 DESC
        """
        
        df_geral = pd.read_sql(query_comparativa, conn)
        
        if not df_geral.empty:
            # Calcular médias gerais
            media_geral_velocidade = df_geral['media_velocidade'].mean()
            media_geral_solucao = df_geral['media_solucao'].mean()
            media_geral_relacionamento = df_geral['media_relacionamento'].mean()
            
            # Preparar relatório comparativo
            relatorio = f"""
            
*Análise Comparativa - NPS Críticos vs Média Geral*

*Período de Comparação:* Últimos {periodo_dias} dias

*Média Geral da Empresa:*
• Velocidade: {media_geral_velocidade:.1f}
• Solução: {media_geral_solucao:.1f}  
• Relacionamento: {media_geral_relacionamento:.1f}

*Analistas Críticos vs Média:*
"""
            
            for analista in analistas_criticos_dados.index:
                if analista in df_geral['Analista'].values:
                    dados_analista = df_geral[df_geral['Analista'] == analista].iloc[0]
                    
                    diff_vel = dados_analista['media_velocidade'] - media_geral_velocidade
                    diff_sol = dados_analista['media_solucao'] - media_geral_solucao
                    diff_rel = dados_analista['media_relacionamento'] - media_geral_relacionamento
                    
                    relatorio += f"""
• *{analista}*:
  - Velocidade: {dados_analista['media_velocidade']:.1f} ({diff_vel:+.1f} vs média)
  - Solução: {dados_analista['media_solucao']:.1f} ({diff_sol:+.1f} vs média)
  - Relacionamento: {dados_analista['media_relacionamento']:.1f} ({diff_rel:+.1f} vs média)
"""
            
            return relatorio
    
    except psycopg2.OperationalError as e:
        logger.error(f"Erro de conexão com banco de dados (analise_comparativa): {str(e)}")
        return ""
    except psycopg2.DatabaseError as e:
        logger.error(f"Erro de banco de dados (analise_comparativa): {str(e)}")
        return ""
    except pd.errors.DatabaseError as e:
        logger.error(f"Erro ao executar query comparativa: {str(e)}")
        return ""
    except Exception as e:
        logger.error(f"Erro inesperado na análise comparativa: {str(e)}")
        logger.exception("Detalhes do erro:")
        return ""
    finally:
        # Garantir que conexões sejam fechadas independentemente do resultado
        if conn is not None:
            try:
                conn.close()
                logger.debug("Conexão fechada (analise_comparativa_nps)")
            except Exception as e:
                logger.warning(f"Erro ao fechar conexão: {str(e)}")
        
        if engine is not None:
            try:
                engine.dispose()
                logger.debug("Engine disposed (analise_comparativa_nps)")
            except Exception as e:
                logger.warning(f"Erro ao fazer dispose da engine: {str(e)}")
