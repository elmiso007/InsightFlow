import pandas as pd
import sqlalchemy
from sqlalchemy import text
import re
from conecta_banco import *
import spacy
from datetime import datetime, timedelta
import json
from bs4 import BeautifulSoup


def get_atendimentos(data_inicio,data_fim):

    # Carrega o modelo de linguagem em português do spaCy
    nlp = spacy.load("pt_core_news_sm")

    def filtrar_interacoes(texto):
        # Ignorar interações que contém apenas um dígito
        if re.match(r'^\d$', texto.strip()):
            return True  # Retorna True para indicar que deve ser ignorado
        
        # Ignorar interações que começam com as frases específicas
        frases_a_ignorar = [
            "Autenticação recebida.",
            "Você está falando agora com",
            "Este atendimento está programado para finalizar",
            "Por favor me envie um *Ok*"
        ]
        
        for frase in frases_a_ignorar:
            if texto.strip().startswith(frase):
                return True  # Retorna True para indicar que deve ser ignorado

        return False  # Caso contrário, a interação será mantida

    def dados_sensiveis(interacoes):
        # Verifica se a interação deve ser ignorada
        if filtrar_interacoes(interacoes):
            return " "  # Retorna uma string vazia se for para ignorar
        
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

        # Ocultar códigos de barras (sequências de 12 a 14 dígitos)
        texto_anonimizado = re.sub(r'\b\d{12,14}\b', '[codigo_de_barras]', texto_anonimizado)

        # Ocultar links com http:// ou https://
        texto_anonimizado = re.sub(r'http[s]?://\S+', '[link]', texto_anonimizado)

        # Ocultar nomes de domínios (após 'http://', 'https://', ou outros casos)
        texto_anonimizado = re.sub(r'(?<=//)[a-zA-Z0-9.-]+', '[dominio]', texto_anonimizado)

        # Ocultar nomes de domínios com 'www.' explicitamente
        texto_anonimizado = re.sub(r'\bwww\.[a-zA-Z0-9.-]+', '[dominio]', texto_anonimizado)

        # Ocultar domínios com padrões específicos
        texto_anonimizado = re.sub(r'\b[a-zA-Z0-9.-]+(?:\.com\.br|\.gov\.br|\.org\.br|\.edu\.br|\.com|\.br|\.net|\.org|\.info|\.tech|\.xyz|\.tv|\.me|\.app)\b', '[dominio]', texto_anonimizado)

        # Anonimizar nomes de empresas específicas
        texto_anonimizado = re.sub(r'Locaweb|LOCAWEB|locaweb|localweb|Localweb', '[empresa]', texto_anonimizado)

        # Anonimizar nomes de empresas específicas
        texto_anonimizado = re.sub(r'Kinghost|KINGHOST|kinghost|hostinger|Hostinger|HOSTINGER|Godaddy|godaddy|GODADDY|HOSTGATOR|hostgator|Hostgator|WIX|wix|Wix|Hostnet|hostnet|HOSTNET|cloudflare|Cloudflare|CLOUDFLARE|nuvemshop|NUVEMSHOP|Nuvemshop', '[concorrente]', texto_anonimizado)
        
        # Processar com spaCy para anonimizar nomes de pessoas
        doc = nlp(texto_anonimizado)
        for ent in doc.ents:
            if ent.label_ == "PER":  # Verifica se a entidade é uma pessoa
                texto_anonimizado = texto_anonimizado.replace(ent.text, '[nome]')

        # Ocultar dados após termos sensíveis como "login", "senha", "usuário"
        texto_anonimizado = re.sub(r'(O seu usuário é o :\s*)\S+', r'\1[usuário]', texto_anonimizado)
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
        b.chave,
        b.data_inicio_interacao,
        b.data_fim_interacao,
        b.cliente,
        b.analista,
        b.fila,
        b.mensagens,
        dc.produto,
        dc.equipe,
        dc.setor,
        CASE 
            WHEN b.canal = '2' THEN 'Chat'
            WHEN b.canal = '9' THEN 'WhatsApp'
            ELSE NULL
        END AS canal  
    FROM aplicacao.conversas_xgen b 
    LEFT JOIN public.depara_chat dc ON b.fila = dc.fila
        WHERE b.data_inicio_interacao BETWEEN '{data_inicio}' AND '{data_fim}' AND b.analista NOT LIKE ('%chat%') AND dc.setor in ('Suporte');
    '''

    df = pd.read_sql_query(query,conn)


    df_mensagem = df[['protocolo','fila', 'mensagens','setor','produto','equipe','canal']]


    def tratar_base64(mensagem):
        if isinstance(mensagem.get("message", ""), str) and mensagem["message"].startswith("data:image/"):
            mensagem["message"] = "[Imagem codificada removida]"  # Substitui o conteúdo base64
        return mensagem


    # Nome do arquivo JSON
    arquivo_json = 'carga_para_analise.json'

    # Lista para armazenar os dados tratados
    dados_json = []

    for _, row in df_mensagem.iterrows():  # Itera sobre as linhas do DataFrame
        protocolo = row['protocolo']
        fila = row['fila']
        canal = row['canal']
        produto = row['produto']
        setor = row['setor']
        equipe = row['equipe']
        item = row['mensagens']

        try:
            # Valida se 'item' é uma string JSON válida e não vazia
            if isinstance(item, str) and item.strip():
                mensagens = json.loads(item)  # Converte JSON para lista de dicionários

                # Remove imagens codificadas e mensagens vazias
                mensagens = [tratar_base64(msg) for msg in mensagens if msg.get('message')]

                for msg in mensagens:
                    # Ignora autores específicos
                    if msg.get('author') in ['Giba', 'SISTEMA']:
                        continue

                    # Valida se os campos necessários estão presentes
                    if all(k in msg for k in ['source', 'Data', 'message']):
                        try:
                            # Formata as informações
                            author_formatado = "[cliente]" if msg['source'] == 0 else "[analista]"
                            data_formatada = datetime.strptime(msg['Data'], '%d/%m/%Y %H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
                            dados_ocultos = dados_sensiveis(msg['message'])

                            # Ignora mensagens que contenham '[==DELETAR==]'
                            #if "deletar" in msg.get('message', ''):
                            #    continue

                            # Adiciona os dados tratados à lista
                            dados_json.append({
                                "protocolo": protocolo,
                                "fila": fila,
                                "setor": setor,
                                "produto": produto,
                                "equipe": equipe,
                                "canal": canal,
                                "autor": author_formatado,
                                "data": data_formatada,
                                "mensagem": dados_ocultos
                            })
                        except Exception as e:
                            # Loga erros de formatação específicos
                            print(f"Erro ao processar mensagem: {msg} - Erro: {e}")
                    else:
                        # Loga mensagens com estrutura inválida
                        print(f"Mensagem com estrutura inesperada: {msg}")
            else:
                # Loga itens vazios ou não JSON
                print("Mensagem vazia ou formato inválido.")
        except json.JSONDecodeError as e:
            # Loga erros de conversão de JSON
            print(f"Erro ao decodificar JSON: {e} - Conteúdo: {item}")

    # Salva os dados tratados no arquivo JSON
    with open(arquivo_json, 'w', encoding='utf-8') as arquivo_json:
        json.dump(dados_json, arquivo_json, ensure_ascii=False, indent=4)

    print(f"Dados tratados salvos em {arquivo_json}")

    # Converte os dados para JSON como string
    conteudo_json = json.dumps(dados_json, ensure_ascii=False, indent=4)

    # Opcional: log para verificação
    print("JSON gerado com sucesso")
    
    conn.close()
    engine.dispose()

    # Retorna o conteúdo do JSON como objeto Python
    return json.loads(conteudo_json)

    #return arquivo_json