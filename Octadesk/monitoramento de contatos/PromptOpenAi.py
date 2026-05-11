import pandas as pd
import requests
from conecta_banco import *
import time
from datetime import datetime
import json
from sqlalchemy import text
from pathlib import Path



sql_path = Path(__file__).parent
resposta_path = Path(__file__).parent / "resposta_openai.md"

def analise_ia(dataset, data_inicial, data_fim, tarefa, setor, lista_protocolos):
    from textwrap import dedent

    tabela = 'rawdata_analise_monitoramento_contatos'
    schema = 'octadesk'
    engine = get_sqlalchemy_engine()
    connection = engine.connect()

    # Sua chave da API da OpenAI
    api_key = '[REDACTED_OPENAI_KEY]'

    # URL da API
    url = 'https://api.openai.com/v1/chat/completions'


    # Limita o tamanho do dataset (para segurança e custo)
    if len(dataset) > 10000: #Quantidade de caracteres
        dataset = dataset[:10000] + '\n... (dataset truncado para análise)' #Caso seja limitado informa no final

    # Prompt refatorado e estruturado
    prompt_estrutura = dedent("""
        Analisar cuidadosamente o dataset fornecido abaixo:

        <dataset>
        {dataset}
        </dataset>
        
        Com base no dataset fornecido, que contém dados de atendimento ao cliente da minha empresa de hospedagem de sites, e-mails e outros serviços, analise os dados e responda às seguintes solicitações.
        Cada atendimento contém um número de protocolo único e o prefixo indica se a mensagem foi enviada por [c = cliente] ou [a = analista]. A chave 'mensagem' contém o conteúdo textual.

        *Exemplo de estrutura de entrada:*
        {{
            "Protocolo": 12345,
            "autor": "[cliente]",
            "mensagem": "Não consigo acessar meu e-mail"
        }}

        #Instruções de formatação
        A resposta deve seguir exatamente as seguintes formatações:
        
        1. Considere apenas mensagens com autor '[cliente]' para identificar o motivo do contato.
        2. Agrupe mensagens semelhantes semanticamente (ex: "erro ao entrar", "problema com login").
        3. Formate os títulos em *negrito*, utilizando **apenas um asterisco** (ex: *Título*).
        4. Destaque *números* e *percentuais* usando asterisco (ex: *34.5%*).
        5. Sempre se refira ao dataset como “base”.
        
        #Solicitações:
        1. Um título denominado *Análise de motivos de contato*. Certifique-se de formatar este título exatamente conforme as instruções, não utilize o caractere '#' para o titulo, utilizando a mesma formatação de números já definida.
        2. Liste os 3 principais motivos de contato identificados nos protocolos existentes no dataset e utilize a mesma formatação de Títulos já definida. Para cada motivo:
           - Destaque os motivos utilizando a formatação de negrito já definida.
           - Informe seu percentual em relação ao total de protocolos distintos, seguindo a formatação de números especificada.
           - Justifique o motivo da classificação de cada motivo.
           - Traga o numero de 3 protocolos analisados para exemplo de conferencia.
        3. Informe o número total de protocolos distintos que foram analisados, formatando o valor conforme as instruções.
    """)

    prompt_mensagem = prompt_estrutura.format(dataset=dataset)

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt_mensagem}],
        "max_tokens": 500
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for _ in range(5):
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            resposta_json = response.json()
            request_id = resposta_json.get('id', 'N/A')
            resposta_conteudo = resposta_json['choices'][0]['message']['content']
            input_text = data["messages"][0]["content"]
            current_time = datetime.now()
            token_prompt = resposta_json['usage']['prompt_tokens']
            token_completion = resposta_json['usage']['completion_tokens']
            model = resposta_json['model']

            time.sleep(10)

            with open(
                resposta_path,
                'w',
                encoding='utf-8'
            ) as arquivo:
                arquivo.write(resposta_conteudo)

            df = pd.DataFrame({
                'request': current_time,
                'dados_de': data_inicial,
                'dados_ate': data_fim,
                'lista_protocolos': [lista_protocolos],
                'analise': tarefa,
                'setor': setor,
                'input_text': [input_text],
                'request_id': [request_id],
                'resposta_json': json.dumps(resposta_json),
                'resposta_text': [resposta_conteudo],
                'token_prompt': token_prompt,
                'token_completion': token_completion,
                'model': model
            })

            df.to_sql(tabela, con=engine, if_exists='replace', index=False, schema=schema)

            print("Resposta salva no markdown e banco de dados.")

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
            time.sleep(10)
        else:
            print("Erro:", response.status_code, response.text)
            break

    return resposta_conteudo
