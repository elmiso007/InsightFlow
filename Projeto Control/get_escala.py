from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import sys
import os
import importlib.util
import json


def get_escala():
    # Configurações da planilha e faixa de dados.
    SAMPLE_SPREADSHEET_ID = "1MmL9p4Hyn2DIYJKzY7vsbVM9h1Hw4wB0s-SMJMUFLhU"
    SAMPLE_RANGE_NAME = "Pausas Proc N1!A1:N"


    path_to_auth = os.path.join(os.path.dirname(__file__), '..','API Google', 'auth.py')
    spec = importlib.util.spec_from_file_location('auth', path_to_auth)
    auth = importlib.util.module_from_spec(spec)
    sys.modules['auth'] = auth
    spec.loader.exec_module(auth)

    """Lê e manipula dados da planilha."""
    try:
        # Obtém as credenciais
        creds = auth.authenticate()

        # Constrói o serviço Sheets API
        service = build("sheets", "v4", credentials=creds)

        # Chama a API do Sheets
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME).execute()
        valores = result.get('values', [])  # Recupera os valores, ou uma lista vazia se não houver dados.

        if not valores:
            print("Nenhum dado encontrado na planilha.")
            

        # Índices das colunas de interesse (baseado no cabeçalho)
        cabecalho = valores[0]
        campos_de_interesse = {
            "Login": cabecalho.index("Login"),
            "Matricula": cabecalho.index("Matricula"),
            "Status": cabecalho.index("Status"),
            "Equipe": cabecalho.index("Equipe"),
            "Skill": cabecalho.index("Skill"),
            "Função": cabecalho.index("Função"),
            "Coordenador": cabecalho.index("Coordenador"),
            "Horario": cabecalho.index("Horario"),
            "Pausa1": cabecalho.index("Pausa1"),
            "Almoço": cabecalho.index("Almoço"),
            "Pausa3": cabecalho.index("Pausa3"),
            "Saida": cabecalho.index("Saida"),
            "Obs": cabecalho.index("Obs"),
            "ID Slack": cabecalho.index("ID Slack")
        }

        # Extrai os dados de todas as linhas
        escala = []

        arquivo = r"C:\Users\lucas.abner\Desktop\Rotinas Python\Projeto Control\escala.json"

        for linha in valores[1:]:
            dados = {
                "Login": linha[campos_de_interesse["Login"]] if len(linha) > campos_de_interesse["Login"] else "",
                "Matricula": linha[campos_de_interesse["Matricula"]] if len(linha) > campos_de_interesse["Matricula"] else "",
                "Status": linha[campos_de_interesse["Status"]] if len(linha) > campos_de_interesse["Status"] else "",
                "Equipe": linha[campos_de_interesse["Equipe"]] if len(linha) > campos_de_interesse["Equipe"] else "",
                "Skill": linha[campos_de_interesse["Skill"]] if len(linha) > campos_de_interesse["Skill"] else "",
                "Função": linha[campos_de_interesse["Função"]] if len(linha) > campos_de_interesse["Função"] else "",
                "Coordenador": linha[campos_de_interesse["Coordenador"]] if len(linha) > campos_de_interesse["Coordenador"] else "",
                "Horario": linha[campos_de_interesse["Horario"]] if len(linha) > campos_de_interesse["Horario"] else "",
                "Pausa1": linha[campos_de_interesse["Pausa1"]] if len(linha) > campos_de_interesse["Pausa1"] else "",
                "Almoço": linha[campos_de_interesse["Almoço"]] if len(linha) > campos_de_interesse["Almoço"] else "",
                "Pausa3": linha[campos_de_interesse["Pausa3"]] if len(linha) > campos_de_interesse["Pausa3"] else "",
                "Saida": linha[campos_de_interesse["Saida"]] if len(linha) > campos_de_interesse["Saida"] else "",
                "Obs": linha[campos_de_interesse["Obs"]] if len(linha) > campos_de_interesse["Obs"] else "",
                "ID Slack": linha[campos_de_interesse["ID Slack"]] if len(linha) > campos_de_interesse["ID Slack"] else "",
            }
            escala.append(dados)

        # Exibe os resultados
        #print("Escala extraída:")
        #for item in escala:
        #    print(item)

        #with open(arquivo, 'w') as file:
        #    json.dump(escala, file)
        
        #print(f"A lista foi salva em {arquivo}.")

       
    except HttpError as err:
        print(f"Erro de HTTP: {err}")

    return escala
