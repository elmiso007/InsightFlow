import os.path
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Escopos padrão. Ajuste conforme necessário.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def authenticate():
    """Autentica o usuário e retorna as credenciais."""
    creds = None

    # Verifica se já existe um token de acesso.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # Se não há credenciais válidas, faz o login do usuário.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Construir caminho relativo para credentials.json
            credentials_path = Path(__file__).parent / 'credentials.json'
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Salva as credenciais no arquivo token.json para o próximo uso.
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


authenticate()