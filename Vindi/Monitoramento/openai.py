import pandas as pd
import requests
from conecta_banco import *
from config import Config
import re
import spacy
import time
from datetime import datetime, timedelta
import json
from sqlalchemy import text
from pathlib import Path

sql_path = Path(__file__).parent



def analise_ia(dataset,data_inicial, data_fim,tarefa,setor,chave,task):
    """
    Envia os dados de atendimento para a API da OpenAI para análise de motivos.

    Constrói um prompt com instruções específicas para que a IA analise o dataset,
    identifique os principais motivos de contato e retorne um relatório formatado em Markdown.
    A resposta é salva no banco de dados e em um arquivo local.

    Args:
        dataset (list): Lista de mensagens anonimizadas.
        data_inicial (str): Data inicial do período analisado.
        data_fim (str): Data final do período analisado.
        tarefa (str): Nome da tarefa/contexto.
        setor (str): Setor analisado (ex: 'Suporte').
        chave (str): Identificador único da análise.
        task (str): Parâmetro redundante de tarefa (pode ser unificado no futuro).

    Returns:
        str: Conteúdo da resposta da IA (relatório).
    """

    chave = chave

    tabela = 'rawdata_analise_monitoramento'

    schema = 'vindi'

    engine = get_sqlalchemy_engine()

    connection = engine.connect()   

    # Sua chave da API da OpenAI
    api_key = Config.OPENAI_API_KEY

    # URL da API
    url = 'https://api.openai.com/v1/chat/completions'


    prompt_mensagem = f'''Analisar cuidadosamente dataset fornecido:
    <dataset>
        {{f"{dataset}"}}
    </dataset>
    Com base no dataset fornecido, que contém dados de atendimento ao cliente da minha empresa de intermediadora de pagamentos e gestão de cobranças, analise os dados e responda às seguintes solicitações. Cada atendimento possui um número de protocolo único e na chave autor consta a informação [cliente], quando a mensagem foi enviada pelo cliente, ou [analista], quando enviada pelo analista.

    A opção 'mensagem' contém as mensagens trocadas pelo cliente e pelo analista.
    Cada atendimento esta entre chaves {'exemplo'}, sendo assim, cada atendimento terá seu respectivo numero de Protocolo.

    #Instruções de Formatação
    A resposta deve seguir exatamente as seguintes formatações:

    #Considere o parâmetro de {{Títulos}} obrigatório para formatação de títulos.  

    1. {{Títulos}}: Formate os títulos em negrito, utilizando *negrito*. Não utilize asteriscos duplos! Exemplo: '**' 
    2. Números e Percentuais: Destaque os valores numéricos e percentuais com a formatação * ao redor do número (exemplo: 123).
    
    #Solicitações
    1. Um título denominado *Análise de motivos de contato*. Certifique-se de formatar este título exatamente conforme as instruções, não utilize o caractere '#' para o titulo, utilizando a mesma formatação de números já definida. 
    2. Liste os 3 principais motivos de contato identificados nos protocolos existentes no dataset e utilize a mesma formatação de {{Títulos}} já definida. Para cada motivo:
        - Informe seu percentual em relação ao total de protocolos distintos, seguindo a formatação de números especificada.
        - Destaque os motivos utilizando a formatação de negrito já definida.
        -Justifique o motivo da classificação de cada motivo.
        - Traga o numero de 3 protocolos analisados para exemplo de conferencia.
    3. Informe o número total de protocolos distintos que foram analisados, formatando o valor conforme as instruções.
    '''


    # Dados do pedido
    data = {
        "model": "gpt-4o-mini",  # ou outro modelo disponível
        "messages": [
            {"role": "user", "content": prompt_mensagem}
        ],
        "max_tokens": 500,  # Número máximo de tokens a serem gerados na resposta
    }

    # Cabeçalhos da solicitação
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for _ in range(5):
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            # Obter e imprimir a resposta
            
            resposta_json = response.json()
            request_id = resposta_json.get('id', 'N/A')
            resposta_conteudo = resposta_json['choices'][0]['message']['content']
            input_text = data["messages"][0]["content"]
            current_time = datetime.now()
            token_prompt = resposta_json['usage']['prompt_tokens']
            token_completion = resposta_json['usage']['completion_tokens']
            model = resposta_json['model']

            time.sleep(10)

            # Exportar a resposta para um arquivo md
            with open(rf'{sql_path}\resposta_openai.md', 'w', encoding='utf-8') as arquivo:
                arquivo.write(resposta_conteudo)

            # Salvar a resposta no banco de dados usando pandas
            df = pd.DataFrame({
                'request': current_time,
                'chave': chave,
                'tarefa':task,
                'dados_de':data_inicial,
                'dados_ate': data_fim,
                'analise': tarefa,
                'setor':setor,
                'input_text':[input_text],
                'request_id':[request_id],
                'resposta_json':json.dumps(resposta_json),
                'resposta_text': [resposta_conteudo],
                'token_prompt': token_prompt,
                'token_completion': token_completion,
                'model': model,
                'created_at': current_time,
                'updated_at': current_time
                }        
            )
            

            df.to_sql(tabela, con=engine, if_exists='replace', index=False, schema= schema)

            print("Resposta salva em 'resposta_openai.txt' e no banco de dados.")
            
        
            # Lê o script SQL do arquivo
            with open(rf'{sql_path}\insereDadosAnaliseIA.sql',  'r', encoding='utf-8') as file:
                sql_script = text(file.read())

            # Executando o script SQL
            connection.execute(sql_script)
            connection.commit()

            connection.close()
            engine.dispose()

            break

        elif response.status_code == 429:
            print("Quota excedida. Aguardando para tentar novamente...")
            time.sleep(10)  # Aguarde 10 segundos antes de tentar novamente
        else:
            print("Erro:", response.status_code, response.text)
            break


    return resposta_conteudo