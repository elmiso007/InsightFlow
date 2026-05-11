import mailbox
import os
from email.header import decode_header
from sqlalchemy import create_engine, text
import pandas as pd
import datetime
from datetime import datetime, timedelta, timezone
import configparser

# Caminho para o arquivo config.ini
config_file_path = 'C:\\Users\\lucas.abner\\Desktop\\Rotinas Python\\config.ini'

# Criar um objeto ConfigParser
config = configparser.ConfigParser()

# Ler o arquivo config.ini
config.read(config_file_path)

# Obter o diretório do perfil do Thunderbird
thunderbird_profile_dir = config['Thunderbird']['profile_dir']

# Local onde será salvo o arquivo
output_dir = '.\\'

# Nome da caixa de entrada
folder_name = 'King'

# Assunto a ser pesquisado
subject_keyword = 'Integração Locaweb - Atendimentos KingHost (Classificações)'

# Abre a pasta do Thunderbird
mbox = mailbox.mbox(os.path.join(thunderbird_profile_dir, folder_name))

# Data atual em UTC
today = datetime.now(timezone.utc)

# Ajustar para UTC-3
today_minus_3h = today - timedelta(hours=3)

# Formatar a data e hora no formato desejado (exemplo: DD/MM/AAAA HH:MM:SS)
data_hora_formatada = today_minus_3h.strftime("%d/%m/%Y %H:%M:%S")
 

# Localiza o último email recebido com o assunto contendo 'Intra'
last_email = None
last_email_date = None

for message in mbox:
    try:
        date_str = message['Date']
        # Remove o sufixo do fuso horário
        date_str = date_str.split(' (', 1)[0]
        date = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z').replace(tzinfo=timezone.utc)

        # Decodifica o subject do email
        subject_bytes, encoding = decode_header(message['Subject'])[0]
        subject = subject_bytes.decode(encoding or 'utf-8')

        # Verifica se o assunto decodificado contém a palavra-chave
        if subject_keyword.lower() in subject.lower():
            if last_email_date is None or date > last_email_date:
                last_email_date = date
                last_email = message
    except Exception as e:
        print(f"Erro ao processar email: {e}")

# Verifica se o último email com o assunto contendo 'Intra' tem anexo
if last_email and last_email.is_multipart():
    for part in last_email.get_payload():
        if part.get_filename():
            filename = part.get_filename()
            try:
                filename_bytes, encoding = decode_header(filename)[0]
                if isinstance(filename_bytes, bytes):
                    filename = filename_bytes.decode(encoding or 'utf-8')
                                      
            except Exception as e:
                print(f"Erro ao decodificar o nome do arquivo: {e}")
                continue

            # Salva o anexo no diretório especificado
            with open(os.path.join(output_dir, filename), 'wb') as f:
                f.write(part.get_payload(decode=True))

                mensagem = f" Arquivo {filename} baixado com sucesso!"

                print(mensagem)
                
                # Abrir o arquivo de texto em modo de escrita
                with open('logs.txt', 'a') as arquivo:
                    arquivo.write(data_hora_formatada + mensagem + '\n')

            #print(f"Subject do email: {subject}")
           
else:
    print(f"Nenhum email com assunto contendo '{subject_keyword}' encontrado.")


