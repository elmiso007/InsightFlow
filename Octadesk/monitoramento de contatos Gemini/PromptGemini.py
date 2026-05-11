# PromptGemini.py

import pandas as pd
from google import genai
from google.genai.errors import APIError
from conecta_banco import *
import time
from datetime import datetime
import json
from sqlalchemy import text
from pathlib import Path
from textwrap import dedent


sql_path = Path(__file__).parent
resposta_path = Path(__file__).parent / "resposta_gemini.md" 

def analise_ia(dataset, data_inicial, data_fim, tarefa, setor, lista_protocolos):
    tabela = 'rawdata_analise_monitoramento_contatos'
    schema = 'octadesk'
    engine = get_sqlalchemy_engine()
    connection = engine.connect()

    # Sua chave da API do Gemini. 
    # Mantenha esta chave segura. Usar variáveis de ambiente é a melhor prática.
    api_key = '[REDACTED_GEMINI_KEY]' 

    try:
        # Inicializa o cliente com a chave fornecida
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Erro ao inicializar o cliente Gemini: {e}")
        return f"ERRO: Falha ao inicializar o cliente Gemini. Erro: {e}"

    # Modelo Gemini rápido e eficiente
    model = "gemini-2.5-flash" 

    # Limita o tamanho do dataset (para segurança e custo)
    if len(dataset) > 10000:
        dataset = dataset[:10000] + '\n... (dataset truncado para análise)'

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

    resposta_conteudo = ""
    token_prompt = 0
    token_completion = 0
    request_id = 'N/A'
    input_text = prompt_mensagem 

    for i in range(5):
        try:
            print(f"Tentativa {i+1} de 5...")
            response = client.models.generate_content(
                model=model,
                contents=prompt_mensagem,
                config=genai.types.GenerateContentConfig(
                    # Aumentado para 4096 tokens para garantir resposta completa
                    max_output_tokens=4096 
                )
            )

            # -----------------------------------------------------------------
            # Verificação de conteúdo e motivo de bloqueio (SAFETY ou MAX_TOKENS)
            # -----------------------------------------------------------------
            if not response.text:
                finish_reason = None
                if response.candidates and response.candidates[0].finish_reason:
                    finish_reason = response.candidates[0].finish_reason.name
                
                print(f"Tentativa {i+1} falhou: Resposta vazia. Motivo de finalização: {finish_reason}")
                
                # Se o motivo for MAX_TOKENS, tentaremos novamente com o mesmo limite, 
                # mas aumentamos o tempo de espera.
                if finish_reason == 'SAFETY' or finish_reason == 'MAX_TOKENS':
                    print(f"Motivo de falha: {finish_reason}. Aumentando o tempo de espera...")
                
                time.sleep(10 * (i + 1)) # Aumenta o tempo de espera após a falha
                continue # Pula para a próxima iteração
            # -----------------------------------------------------------------


            # Processamento da resposta (Só executa se response.text não for vazio)
            resposta_conteudo = response.text
            
            # Trata a ausência do atributo 'name' ou de 'candidates'
            request_id = 'N/A'
            if response.candidates and hasattr(response.candidates[0], 'name'):
                request_id = response.candidates[0].name
            elif response.candidates:
                request_id = f"candidate_index_{response.candidates[0].index}"

            current_time = datetime.now()
            
            # USO DE TOKENS (usage_metadata)
            if response.usage_metadata:
                token_prompt = response.usage_metadata.prompt_token_count
                token_completion = response.usage_metadata.candidates_token_count
            
            # Cria um log JSON simplificado para persistência
            resposta_json_log = {
                'model': model,
                'request_id': request_id,
                'prompt_tokens': token_prompt,
                'completion_tokens': token_completion,
                'response_text_snippet': resposta_conteudo[:200] + '...'
            }
            resposta_json_str = json.dumps(resposta_json_log)

            time.sleep(10)

            with open(resposta_path, 'w', encoding='utf-8') as arquivo:
                arquivo.write(resposta_conteudo)

            df = pd.DataFrame({
                'request': [current_time],
                'dados_de': [data_inicial],
                'dados_ate': [data_fim],
                'lista_protocolos': [lista_protocolos],
                'analise': [tarefa],
                'setor': [setor],
                'input_text': [input_text],
                'request_id': [request_id],
                'resposta_json': [resposta_json_str], 
                'resposta_text': [resposta_conteudo],
                'token_prompt': [token_prompt],
                'token_completion': [token_completion],
                'model': [model]
            })

            df.to_sql(tabela, con=engine, if_exists='replace', index=False, schema=schema)

            print("Resposta salva no markdown e banco de dados.")

            with open(rf'{sql_path}\insereDadosAnaliseIA.sql', 'r', encoding='utf-8') as file:
                sql_script = text(file.read())

            connection.execute(sql_script)
            connection.commit()

            connection.close()
            engine.dispose()
            break # SAI DO LOOP APÓS O SUCESSO
            
        # TRATAMENTO DE ERROS DO GEMINI
        except APIError as e:
            if "RESOURCE_EXHAUSTED" in str(e): 
                print("Quota excedida ou limite de taxa atingido. Aguardando para tentar novamente...")
                time.sleep(10)
            else:
                print(f"Erro da API do Gemini: {e}")
                break
        except Exception as e:
            # Erro genérico
            print(f"Erro inesperado durante a chamada ou processamento: {e}")
            time.sleep(10)
            continue # Tenta novamente em caso de erro genérico

    # Garante o retorno de uma string em caso de falha total do loop
    if not resposta_conteudo:
        # Tenta fechar as conexões se elas ainda estiverem abertas
        try:
            connection.close()
            engine.dispose()
        except:
            pass
        return "ERRO: O serviço de IA falhou após 5 tentativas. O campo 'content' está vazio."
        
    return resposta_conteudo