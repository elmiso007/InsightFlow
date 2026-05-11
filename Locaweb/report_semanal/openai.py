import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import json
from sqlalchemy import text


def analise_openai(df_atual,df_past,dias_restantes,prompt,valor_extra=None, valor_extra2 = None,valor_extra3= None):  

    # Sua chave da API da OpenAI
    api_key = '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'

    # URL da API
    url = 'https://api.openai.com/v1/chat/completions'


    # Leitura do conteúdo do prompt.md
    with open(prompt, "r", encoding="utf-8") as file:
        prompt = file.read()

    # Substituição das variáveis dentro do conteúdo
    # Monta o dicionário básico sempre presente
    params = {
        "df_atual": df_atual,
        "df_past": df_past,
        "dias_restantes": dias_restantes
    }

    # Só adiciona extras se não forem None
    if valor_extra is not None:
        params["valor_extra"] = valor_extra
    if valor_extra2 is not None:
        params["valor_extra2"] = valor_extra2
    if valor_extra3 is not None:
        params["valor_extra3"] = valor_extra3

    # Usa o dicionário no format
    prompt_mensagem = prompt.format(**params)

    # Dados do pedido
    data = {

        "model": "gpt-4o",  # ou outro modelo disponível
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

    max_retries = 3
    retry_delay = 30  # segundos
    resposta_conteudo = None
    
    for attempt in range(max_retries):
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
            #with open('resposta_openai.md', 'w', encoding='utf-8') as arquivo:
            #    arquivo.write(resposta_conteudo)

            # Salvar a resposta no banco de dados usando pandas
            df = pd.DataFrame({
                'request': current_time,
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
            
            #df.to_sql(tabela, con=engine, if_exists='replace', index=False, schema= schema)

            print("Resposta salva em 'resposta_openai.txt' e no banco de dados.")
            break  # Sai do loop se a requisição foi bem sucedida
        
            # Lê o script SQL do arquivo
            #with open('C:/Users/lucas.abner/Downloads/www/IA/InsereDados.sql',  'r', encoding='utf-8') as file:
            #    sql_script = text(file.read())

            # Executando o script SQL
            #conn.execute(sql_script)
            #conn.commit()
            #engine.dispose()

        elif response.status_code == 429:
            print(f"Quota excedida. Tentativa {attempt + 1}/{max_retries}. Aguardando {retry_delay}s...")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Backoff exponencial
            else:
                print("Número máximo de tentativas atingido. Retornando mensagem padrão.")
                resposta_conteudo = "Análise indisponível no momento devido a limitações da API. Por favor, tente novamente mais tarde."

        else:
            print("Erro:", response.status_code, response.text)
            resposta_conteudo = f"Erro na análise: {response.status_code}"
            break

    return resposta_conteudo
