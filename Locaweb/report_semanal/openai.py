import pandas as pd
import requests
import time
import configparser
from datetime import datetime, timedelta
from pathlib import Path
import json
from sqlalchemy import text


# Procura primeiro ao lado deste arquivo (uso standalone), depois 2 niveis
# acima (convencao do monorepo original).
_AQUI = Path(__file__).parent
_CONFIG_CANDIDATOS = [_AQUI / 'config.ini', _AQUI.parent.parent / 'config.ini']
_CONFIG_PATH = next((p for p in _CONFIG_CANDIDATOS if p.exists()), _CONFIG_CANDIDATOS[0])
_config = configparser.ConfigParser()
_config.read(_CONFIG_PATH)

try:
    _OPENAI_API_KEY = _config['openai']['api_key']
    _OPENAI_MODEL = _config['openai'].get('model', 'gpt-4o-mini')
except KeyError as e:
    tentados = ', '.join(str(p) for p in _CONFIG_CANDIDATOS)
    raise RuntimeError(
        f"Seção [openai] ausente ou incompleta. "
        f"Caminhos tentados: {tentados}. "
        f"Esperado: api_key (e opcionalmente model). Faltou: {e}"
    )


def analise_openai(df_atual,df_past,dias_restantes,prompt,valor_extra=None, valor_extra2 = None,valor_extra3= None):

    api_key = _OPENAI_API_KEY

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

        "model": _OPENAI_MODEL,
        "messages": [
            {"role": "user", "content": prompt_mensagem}
        ],
        "max_completion_tokens": 500,  # Número máximo de tokens a serem gerados na resposta
    }

    # Cabeçalhos da solicitação
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Inicializar variável para evitar UnboundLocalError
    resposta_conteudo = None
    
    # Tentativas de retry em caso de erro 429
    max_tentativas = 3
    tentativa = 0
    tempo_espera = 10
    
    while tentativa < max_tentativas:
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
            
        
            # Lê o script SQL do arquivo
            #with open('C:/Users/lucas.abner/Downloads/www/IA/InsereDados.sql',  'r', encoding='utf-8') as file:
            #    sql_script = text(file.read())

            # Executando o script SQL
            #conn.execute(sql_script)
            #conn.commit()
            #engine.dispose()
            
            # Sucesso, sair do loop
            break

        elif response.status_code == 429:
            tentativa += 1
            print(f"Quota excedida. Tentativa {tentativa}/{max_tentativas}. Aguardando {tempo_espera} segundos...")
            time.sleep(tempo_espera)
            # Aumentar tempo de espera exponencialmente
            tempo_espera = min(tempo_espera * 2, 120)  # Máximo de 2 minutos

        else:
            print(f"Erro {response.status_code}: {response.text}")
            # Para outros erros, não tentar novamente
            break
    
    # Verificar se conseguiu obter resposta
    if resposta_conteudo is None:
        erro_msg = f"Falha ao obter resposta da API após {max_tentativas} tentativas."
        print(f"❌ ERRO: {erro_msg}")
        raise Exception(erro_msg)
    
    return resposta_conteudo
