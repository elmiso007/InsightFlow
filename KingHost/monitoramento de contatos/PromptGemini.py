import pandas as pd
import google.generativeai as genai
from conecta_banco import *
import time
from datetime import datetime
import json
from sqlalchemy import text
from pathlib import Path



sql_path = Path(__file__).parent
resposta_path = Path(__file__).parent / "resposta_gemini.md"

def analise_ia(dataset, data_inicial, data_fim, tarefa, setor, lista_protocolos):
    from textwrap import dedent

    tabela = 'rawdata_analise_monitoramento_contatos'
    schema = 'kinghost_octadesk'
    engine = get_sqlalchemy_engine()
    connection = engine.connect()

    # Sua chave da API do Gemini
    api_key = '[REDACTED_GEMINI_KEY]'
    
    # Configurar a API do Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')

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
        5. Sempre se refira ao dataset como "base".
        
        #Solicitações:
        1. Um título denominado *Análise de motivos de contato*. Certifique-se de formatar este título exatamente conforme as instruções, não utilize o caractere '#' para o titulo, utilizando a mesma formatação de números já definida.
        2. Liste os 3 principais motivos de contato identificados nos protocolos existentes no dataset e utilize a mesma formatação de Títulos já definida. Para cada motivo:
           - Destaque os motivos utilizando a formatação de negrito já definida.
           - Informe seu percentual em relação ao total de protocolos distintos, seguindo a formatação de números especificada.
           - Justifique o motivo da classificação de cada motivo.
           - Traga o numero de 3 protocolos analisados que impactaram na definição do principal motivo para exemplo de conferencia.
        3. Informe o número total de protocolos distintos que foram analisados, formatando o valor conforme as instruções.
    """)

    prompt_mensagem = prompt_estrutura.format(dataset=dataset)

    for tentativa in range(5):
        try:
            # Gerar resposta usando o Gemini
            response = model.generate_content(prompt_mensagem)
            
            if response.text:
                resposta_conteudo = response.text
                current_time = datetime.now()
                
                # Para compatibilidade com o banco de dados existente
                request_id = f"gemini-{int(current_time.timestamp())}"
                model_name = "gemini-pro"
                
                # Estimativas de tokens (Gemini não fornece contagem exata como OpenAI)
                token_prompt = len(prompt_mensagem.split()) * 1.3  # Estimativa
                token_completion = len(resposta_conteudo.split()) * 1.3  # Estimativa
                
                time.sleep(2)  # Delay menor que OpenAI

                with open(
                    resposta_path,
                    'w',
                    encoding='utf-8'
                ) as arquivo:
                    arquivo.write(resposta_conteudo)

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

                df = pd.DataFrame({
                    'request': current_time,
                    'dados_de': data_inicial,
                    'dados_ate': data_fim,
                    'lista_protocolos': [lista_protocolos],
                    'analise': tarefa,
                    'setor': setor,
                    'input_text': [prompt_mensagem],
                    'request_id': [request_id],
                    'resposta_json': json.dumps(resposta_json),
                    'resposta_text': [resposta_conteudo],
                    'token_prompt': int(token_prompt),
                    'token_completion': int(token_completion),
                    'model': model_name
                })

                df.to_sql(tabela, con=engine, if_exists='replace', index=False, schema=schema)

                print("Resposta salva no markdown e banco de dados.")

                # Lê o script SQL do arquivo
                with open(f'{sql_path}\insereDadosAnaliseIA.sql',  'r', encoding='utf-8') as file:
                    sql_script = text(file.read())

                # Executando o script SQL
                connection.execute(sql_script)
                connection.commit()

                connection.close()
                engine.dispose()
                break
            else:
                print(f"Tentativa {tentativa + 1}: Resposta vazia do Gemini")
                time.sleep(5)
        
        except Exception as e:
            print(f"Tentativa {tentativa + 1}: Erro na API do Gemini: {str(e)}")
            if "quota" in str(e).lower() or "rate" in str(e).lower():
                print("Quota excedida. Aguardando para tentar novamente...")
                time.sleep(10)
            else:
                time.sleep(5)
            
            if tentativa == 4:  # Última tentativa
                print("Todas as tentativas falharam.")
                connection.close()
                engine.dispose()
                return "Erro: Não foi possível obter resposta do Gemini após 5 tentativas."

    return resposta_conteudo
