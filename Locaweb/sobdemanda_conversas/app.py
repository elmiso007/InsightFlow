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
import os

sql_path = Path(__file__).parent 



    
def dados_sensiveis(interacoes):
    
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

    # Remove CC
    #texto_anonimizado = re.sub(r'******', '[CC]', texto_anonimizado)

    # Ocultar domínios com padrões específicos
    texto_anonimizado = re.sub(r'\b[a-zA-Z0-9.-]+(?:\.com\.br|\.gov\.br|\.org\.br|\.edu\.br|\.com|\.br|\.net|\.org|\.info|\.tech|\.xyz|\.tv|\.me|\.app)\b', '[dominio]', texto_anonimizado)

    # Anonimizar nomes de empresas específicas
    texto_anonimizado = re.sub(r'Locaweb|locaweb|LOCAWEB|Localweb|localweb', '[empresa]', texto_anonimizado)

    # Anonimizar nomes de empresas específicas
    texto_anonimizado = re.sub(r'Kinghost|KINGHOST|kinghost|hostinger|Hostinger|HOSTINGER|Godaddy|godaddy|GODADDY|HOSTGATOR|hostgator|Hostgator|WIX|wix|Wix|Hostnet|hostnet|HOSTNET|cloudflare|Cloudflare|CLOUDFLARE|nuvemshop|NUVEMSHOP|Nuvemshop', '[concorrente]', texto_anonimizado)
    
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
	a.id,
	a.protocolo, 
	a.agent_name,
	a.canal, 
	a.data_inicio_interacao, 
	a.data_fim_interacao,
	a.grupo_nome as fila,
	df.equipe,
	df.produto,
	df.setor,
	m.mensagens
FROM lw_octadesk.chat a
LEFT JOIN public.depara_chat df ON a.grupo_nome = df.fila
LEFT JOIN lw_octadesk.mensagens m  ON a.id = m.id
WHERE a.data_inicio_interacao between '2025-08-01 00:00:00' and '2025-08-31 23:59:59'
AND df.setor in ('Suporte')
and df.equipe in ('Suporte Email')
'''

# Carrega dados
df = pd.read_sql_query(query, conn)

# Converte a coluna de data para datetime e remove a parte da hora
df['data_inicio_interacao'] = pd.to_datetime(df['data_inicio_interacao']).dt.date


df_mensagem = df[['protocolo','data_inicio_interacao','fila', 'mensagens','setor','equipe','canal','produto']]

# Agrupa por dia
grupos_por_dia = df_mensagem.groupby('data_inicio_interacao')

def tratar_base64(mensagem):
    if isinstance(mensagem.get("message", ""), str) and mensagem["message"].startswith("data:image/"):
        mensagem["message"] = "[Imagem codificada removida]"  # Substitui o conteúdo base64
    return mensagem

# Itera sobre cada grupo (um por dia)
for data_dia, df_dia in grupos_por_dia:
    conteudo_txt = []

    for _, row in df_dia.iterrows():
        protocolo = row['protocolo']
        fila = row['fila']
        canal = row['canal']
        setor = row['setor']
        equipe = row['equipe']
        produto = row['produto']
        item = row['mensagens']
        data = row['data_inicio_interacao']

        try:
            if item and isinstance(item, str) and item.strip().startswith('['):

                mensagens = json.loads(item)
                
            else:
                print("Mensagem vazia ou formato inválido.")
                continue  # <- Pula para a próxima linha do DataFrame
            
            conteudo_txt.append("\n{\n")
            conteudo_txt.append(f"Protocolo: {protocolo} >> Data: {data} >> Fila: {fila} >> Canal: {canal} >> Setor: {setor} >> Equipe: {equipe} >> Produto: {produto}\n")

            for msg in mensagens:
                if all(k in msg for k in ['sentBy', 'time', 'body']):
                    try:
                        tipo_remetente = msg.get('sentBy', {}).get('type', '')
                        author_formatado = "[Cliente]" if tipo_remetente == 'contact' else "[Analista]"

                        dt = datetime.strptime(msg['time'], '%Y-%m-%dT%H:%M:%S.%fZ')
                        data_formatada = dt.strftime('%d/%m/%Y %H:%M:%S')

                        dados_ocultos = dados_sensiveis(msg['body'])

                        conteudo_txt.append(f"{author_formatado} - {dados_ocultos}\n")

                    except Exception as e:
                        print(f"Erro ao processar mensagem: {msg} - Erro: {e}")
                else:
                    print(f"Mensagem com estrutura inesperada: {msg}")

            conteudo_txt.append("},")
            
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {e} - Conteúdo: {item}")

    # Cria nome do arquivo com data invertida
    nome_arquivo = f"lw_agosto/atendimentos_{data_dia.strftime('%Y%m%d')}.txt"
    caminho_arquivo = os.path.join(sql_path, nome_arquivo)

    # Salva o arquivo .txt do dia
    with open(caminho_arquivo, 'w', encoding='utf-8') as arquivo:
        arquivo.writelines(conteudo_txt)

    print(f"Arquivo salvo: {caminho_arquivo}")
