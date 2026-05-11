import pandas as pd
import sqlalchemy
from sqlalchemy import text
import re
from conecta_banco import *
import spacy
from datetime import datetime, timedelta
import json
from bs4 import BeautifulSoup
from pathlib import Path
import logging

logger = logging.getLogger(__name__)



def get_atendimentos(data_inicio, data_fim):
    """
    Recupera e processa atendimentos do banco de dados para o período especificado.
    
    Realiza a consulta SQL, anonimiza dados sensíveis e formata as mensagens para análise.

    Args:
        data_inicio (str): Data/Hora inicial do período.
        data_fim (str): Data/Hora final do período.

    Returns:
        tuple: Uma tupla contendo:
            - conteudo_txt (list): Lista de strings com o conteúdo formatado e anonimizado.
            - lista_protocolos_unicos (list): Lista de protocolos únicos encontrados.
    """

    # Carrega o modelo de linguagem em português do spaCy
    #nlp = spacy.load("pt_core_news_sm")
    
    def dados_sensiveis(interacoes):
        """
        Remove ou substitui dados sensíveis do texto das interações.

        Aplica expressões regulares para identificar e mascarar CPFs, e-mails, telefones,
        nomes de empresas concorrentes, palavrões, etc.

        Args:
            interacoes (str): Texto original da interação.

        Returns:
            str: Texto anonimizado.
        """
        
        # Remover tags HTML
        interacoes = BeautifulSoup(interacoes, "html.parser").get_text()

        # Remover asteriscos ao redor de palavras
        interacoes = re.sub(r'\*(\w+)\*', r'\1', interacoes)

        # Anonimizar e-mails
        texto_anonimizado = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zAlo]{2,}', '[email]', interacoes)
        
        # Anonimizar CPFs (formatado, 11 dígitos, ou 9 dígitos + hífen + 2)
        texto_anonimizado = re.sub(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b|\b\d{9}-\d{2}\b', '[CPF]', texto_anonimizado)
        
        # Anonimizar CNPJs
        texto_anonimizado = re.sub(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b', '[CNPJ]', texto_anonimizado)

        # Anonimizar telefones
        texto_anonimizado = re.sub(r'\b(\(?\d{2}\)?\s?)?9?\d{4}[-.]?\d{4}\b', '[telefone]', texto_anonimizado)

        # Ocultar sequências de IP
        texto_anonimizado = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP]', texto_anonimizado)

        #Oculta a apresentação do BOT para etivar confusões da LLM 
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
        texto_anonimizado = re.sub(r'Vindi|vindi|VINDI|vindi.com.br|vindi.com|VINDI.COM.BR|VINDI.COM', '[empresa]', texto_anonimizado)

        # Anonimizar nomes de empresas específicas
        texto_anonimizado = re.sub(r'Pagcerto|pagcerto|PAGCERTO|PagCerto|PagSeguro|Pagseguro|pagseguro|PAGSEGURO|mercadoseguro|MercadoSeguro|Mercadoseguro|MERCADOSEGURO|MERCADOPAGO|mercadopago|MercadoPago|Pagar.me|PAGARME|Paypal|PAYPAL', '[concorrente]', texto_anonimizado)
        
        # Processar com spaCy para anonimizar nomes de pessoas
        #doc = nlp(texto_anonimizado)
        #for ent in doc.ents:
        #    if ent.label_ == "PER":  # Verifica se a entidade é uma pessoa
        #        texto_anonimizado = texto_anonimizado.replace(ent.text, '[nome]')

        # Ocultar dados após termos sensíveis como "login", "senha", "usuário"
        texto_anonimizado = re.sub(r'(O seu usuário é: \s*)\S+', r'\1[usuário]', texto_anonimizado)
        texto_anonimizado = re.sub(r'(login\s*[:\s]?\s*)\S+', r'\1[login]', texto_anonimizado)
        texto_anonimizado = re.sub(r'(usuário\s*[:\s]?\s*)\S+', r'\1[usuario]', texto_anonimizado)
        texto_anonimizado = re.sub(r'(senha\s*[:\s]?\s*)\S+', r'\1[senha]', texto_anonimizado)

        # Ocultar palavrões (adicione mais conforme necessário)
        lista_palavroes = [
            "vagabundo", "merda", "puta" # Substitua por palavras reais
                ]
        
        
        for palavrao in lista_palavroes:
            texto_anonimizado = re.sub(rf'\b{palavrao}\b', '[palavrão]', texto_anonimizado, flags=re.IGNORECASE)

        return texto_anonimizado

    engine = get_sqlalchemy_engine()
    conn = get_pyodbc_connection()

    query = f'''
    SELECT
        b.protocolo,
        b.data_inicio_interacao,
        b.data_fim_interacao,
        b.contact_name AS cliente,
        b.agent_name AS analista,
        dc.grupo as fila,
        m.mensagens,
        dc.produto,
        dc.equipe,
        dc.setor,
        b.canal
    FROM vindi.chat b 
    LEFT JOIN vindi.mensagens m ON b.id = m.id
    LEFT JOIN vindi.depara_grupo dc ON b.grupo_nome = dc.grupo
        WHERE b.data_inicio_interacao BETWEEN '{data_inicio}' AND '{data_fim}' AND dc.setor = 'Suporte';
    '''

    df = pd.read_sql_query(query,conn)


    df_mensagem = df[['protocolo','fila', 'mensagens','setor','equipe','canal']]
    lista_protocolos_unicos = df_mensagem['protocolo'].dropna().unique().tolist()

    # Nome do arquivo JSON
    arquivo_json = 'carga_para_analise.json'

    conteudo_txt = []

    arquivo_txt = Path(__file__).parent / 'dados.txt'

    for _, row in df_mensagem.iterrows():  # Itera sobre as linhas do DataFrame
        protocolo = row['protocolo']
        fila = row['fila']
        canal = row['canal']
        setor = row['setor']
        equipe = row['equipe']
        item = row['mensagens']

        try:
            # Valida se 'item' é uma string JSON válida e não vazia
            if isinstance(item, str) and item.strip():
                mensagens = json.loads(item)  # Converte JSON para lista de dicionários

                # Adiciona o cabeçalho ao texto
                conteudo_txt.append("\n{\n")
                conteudo_txt.append(f"Protocolo: {protocolo} >> Fila: {fila}\n")


                for msg in mensagens:
                        # Valida se os campos necessários estão presentes
                        if all(k in msg for k in ['sentBy', 'time', 'body']):
                            try:
                                # Determina o autor com base no tipo de remetente
                                tipo_remetente = msg.get('sentBy', {}).get('type', '')
                                author_formatado = "c" if tipo_remetente == 'contact' else "a"

                                # Converte e formata a data ISO 8601 para dd/mm/yyyy HH:MM:SS
                                dt = datetime.strptime(msg['time'], '%Y-%m-%dT%H:%M:%S.%fZ')
                                data_formatada = dt.strftime('%d/%m/%Y %H:%M:%S')

                                # Aplica anonimização ou limpeza de dados sensíveis
                                dados_ocultos = dados_sensiveis(msg['body'])

                                # Monta a linha de texto formatada
                                conteudo_txt.append(f"{author_formatado} - {dados_ocultos}\n")
                                
                            except Exception as e:
                                # Loga erros de formatação específicos
                                logger.error(f"Erro ao processar mensagem: {msg} - Erro: {e}")
                        else:
                            # Loga mensagens com estrutura inválida
                            logger.warning(f"Mensagem com estrutura inesperada: {msg}")

                conteudo_txt.append("\n},\n")
            else:
                # Loga itens vazios ou não JSON
                logger.warning("Mensagem vazia ou formato inválido.")
        except json.JSONDecodeError as e:
            # Loga erros de conversão de JSON
            logger.error(f"Erro ao decodificar JSON: {e} - Conteúdo: {item}")

    # Salva os dados no arquivo TXT
    with open(arquivo_txt, 'w', encoding='utf-8') as arquivo:
        arquivo.writelines(conteudo_txt)

    logger.info(f"Conteúdo exportado para {arquivo_txt}")

    return conteudo_txt, lista_protocolos_unicos

#get_atendimentos()