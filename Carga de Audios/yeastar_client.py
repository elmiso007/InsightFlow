"""
Cliente REST para o Yeastar PBX (S-Series e Cloud).

Fluxo de autenticação:
  1. POST /api/v1.0/login  — envia usuário e senha (MD5 + Base64)
  2. Se o servidor pedir 2FA → POST /api/v1.0/tfaverify com trust_device=1
  3. Autenticação via token (firmware legado) ou via cookie websession (Cloud)

Endpoints utilizados:
  - POST /api/v1.0/login
  - POST /api/v1.0/tfaverify
  - GET  /api/v1.0/recording/search
  - POST /api/v1.0/recording/download
"""

import hashlib
import base64
import logging
from datetime import datetime
from typing import Optional

import requests

from config import config

logger = logging.getLogger('carga_audios.yeastar')

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _encode_password(senha: str) -> str:
    md5_hex = hashlib.md5(senha.encode()).hexdigest()
    return base64.b64encode(md5_hex.encode()).decode()


def _url(endpoint: str) -> str:
    return f"{config.YEASTAR_URL.rstrip('/')}/{endpoint.lstrip('/')}"


class YeastarClient:
    """
    Sessão autenticada com o Yeastar PBX.
    Suporta dois modos de autenticação:
      - Token no query string (firmware S-Series legado)
      - Cookie websession (Yeastar Cloud / firmware atual)
    """

    def __init__(self):
        self._token: Optional[str] = None
        self._cookie_auth: bool = False   # True quando auth é via cookie websession
        self._session = requests.Session()
        self._session.verify = False

    # ------------------------------------------------------------------
    # Autenticação
    # ------------------------------------------------------------------

    def login_browser(self):
        """
        Alternativa de autenticação via Playwright + Edge.
        Usa o navegador para fazer login, aceitar o GDPR e capturar o cookie websession.
        Necessário quando o endpoint recording/search trava com 504 (GDPR pendente).
        """
        from yeastar_auth_browser import login_via_browser
        websession, reqs = login_via_browser()
        self._session.cookies.set('websession', websession)
        self._cookie_auth = True
        self._token = None
        logger.info(f'Login via browser OK — {len(reqs)} req(s) de API capturada(s).')

    def login(self):
        """
        Realiza login e armazena a credencial (token ou cookie).
        Trata 2FA automaticamente se necessário.

        P-Series Cloud (v83+): envia login_link_type=all no query string para
        garantir que o servidor defina o cookie websession.
        gdpr_download_url no response indica GDPR pendente mas login é válido.
        """
        payload = {
            'username': config.YEASTAR_USER,
            'password': _encode_password(config.YEASTAR_PASS),
            'language': 'pt_BR',
        }
        # login_link_type=all instrui o servidor a definir cookie websession
        qs = {'login_link_type': 'all'}
        resp = self._session.post(_url('/api/v1.0/login'), json=payload, params=qs, timeout=30)
        resp.raise_for_status()
        dados = resp.json()

        status  = dados.get('status', '')
        errcode = dados.get('errcode')
        token   = dados.get('token', '')

        # --- Sucesso com token no body (firmware legado) ---
        if (status == 'Success' or errcode == 0) and token:
            self._token = token
            self._cookie_auth = False
            logger.info('Login Yeastar OK (token).')
            return

        # --- 2FA necessário (formato legado) ---
        if status == 'need_verify':
            logger.info('2FA solicitado pelo Yeastar — verificando...')
            self._verificar_tfa()
            return

        # --- 2FA necessário (formato atual) ---
        if dados.get('need_tfa') == 1:
            tfa_token = dados.get('tfa_token', '')
            logger.info('2FA solicitado pelo Yeastar — verificando...')
            self._verificar_tfa(tfa_token=tfa_token)
            # Após TFA bem-sucedido, tenta login novamente para obter a sessão
            self.login()
            return

        # --- Sucesso via cookie (Yeastar Cloud) ---
        # gdpr_download_url indica GDPR pendente mas login é válido — ignora para API
        if errcode == 0 and self._session.cookies.get('websession'):
            self._cookie_auth = True
            self._token = None
            logger.info(
                f'Login Yeastar OK (cookie websession: '
                f'{self._session.cookies.get("websession")[:8]}...).'
            )
            return

        raise RuntimeError(f'Login Yeastar falhou: {dados}')

    def _verificar_tfa(self, tfa_token: str = ''):
        """
        Responde ao desafio de 2FA com trust_device=1 (registra dispositivo).
        Usa YEASTAR_TFA_CODE do .env ou pede o código interativamente.
        """
        payload = {
            'username':     config.YEASTAR_USER,
            'trust_device': 1,
        }
        if tfa_token:
            payload['tfa_token'] = tfa_token

        tfa_code = getattr(config, 'YEASTAR_TFA_CODE', '') or ''
        if not tfa_code:
            print('\n[Yeastar 2FA] Um código foi enviado por e-mail/SMS. Digite-o abaixo:')
            tfa_code = input('Código 2FA: ').strip()

        payload['verification_code'] = tfa_code

        resp = self._session.post(_url('/api/v1.0/tfaverify'), json=payload, timeout=30)
        resp.raise_for_status()
        dados = resp.json()

        # Verificação bem-sucedida: pode ou não ter token direto
        if dados.get('errcode') == 0 or dados.get('status') == 'Success':
            if dados.get('token'):
                self._token = dados['token']
                self._cookie_auth = False
                logger.info('2FA Yeastar verificado. Dispositivo confiável registrado.')
            else:
                # Token virá no próximo login — dispositivo marcado como confiável
                logger.info('2FA Yeastar verificado. Dispositivo confiável registrado.')
        else:
            raise RuntimeError(f'2FA Yeastar falhou: {dados}')

    def _auth_params(self) -> dict:
        """Retorna o parâmetro de token para query string (vazio em modo cookie)."""
        if self._cookie_auth:
            return {}
        if not self._token:
            raise RuntimeError('Não autenticado. Chame login() primeiro.')
        return {'token': self._token}

    # ------------------------------------------------------------------
    # Busca de gravações
    # ------------------------------------------------------------------

    def buscar_gravacoes(self, data_inicio: datetime, data_fim: datetime) -> list[dict]:
        """
        Retorna lista de gravações no período informado com paginação automática.

        P-Series v83+ usa time_begin/time_end (não start_time/end_time).
        Resposta: recording_list (não data/recordings). Arquivo em campo 'file'.
        """
        fmt = '%d/%m/%Y %H:%M:%S'
        page_size = 100
        todas: list[dict] = []
        page = 1

        while True:
            params = {
                **self._auth_params(),
                'time_begin':  data_inicio.strftime(fmt),
                'time_end':    data_fim.strftime(fmt),
                'page':        page,
                'page_size':   page_size,
                'sort_by':     'time',
                'order_by':    'asc',
                'call_from':   '',
                'call_to':     '',
            }
            resp = self._session.get(
                _url('/api/v1.0/recording/search'),
                params=params,
                timeout=60,
            )
            resp.raise_for_status()
            dados = resp.json()

            if dados.get('errcode') != 0 and dados.get('status') != 'Success':
                logger.warning(f'Busca de gravacoes retornou erro: {dados}')
                break

            lote = dados.get('recording_list', dados.get('data', dados.get('recordings', [])))
            todas.extend(lote)

            total = dados.get('total_number', len(todas))
            logger.info(f'Pagina {page}: {len(lote)} gravacoes | total={total}')

            if len(todas) >= total or len(lote) < page_size:
                break
            page += 1

        logger.info(f'{len(todas)} gravacao(oes) encontrada(s) entre {data_inicio} e {data_fim}.')
        return todas

    # ------------------------------------------------------------------
    # Download de áudio
    # ------------------------------------------------------------------

    def baixar_gravacao(self, recording_file: str, destino_path, recording_id: int = None) -> bool:
        """
        Faz download de um arquivo de gravação para destino_path.

        P-Series v83+: POST id_list=[<id>] — download assíncrono.
          - Server retorna errcode=2 (PROCESSING) enquanto prepara o arquivo.
          - Faz polling via GET com os mesmos params até receber binário.
        Firmware legado: POST recording_file=<filename>
        """
        import time as _time

        def _salvar(resp) -> bool:
            ct = resp.headers.get('Content-Type', '')
            if 'application/json' in ct:
                dados = resp.json()
                logger.error(f'Erro ao baixar {recording_file}: {dados}')
                return False
            with open(destino_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True

        try:
            if recording_id is not None:
                payload = {**self._auth_params(), 'id_list': [recording_id]}
                # POST inicia o download (pode retornar PROCESSING)
                resp = self._session.post(
                    _url('/api/v1.0/recording/download'),
                    json=payload,
                    timeout=60,
                    stream=True,
                )
                resp.raise_for_status()
                ct = resp.headers.get('Content-Type', '')

                if 'application/json' not in ct:
                    return _salvar(resp)

                dados = resp.json()
                if dados.get('errcode') == 2 and dados.get('errmsg') == 'PROCESSING':
                    # Polling: aguarda o servidor preparar o arquivo
                    for tentativa in range(15):
                        _time.sleep(2)
                        resp_poll = self._session.get(
                            _url('/api/v1.0/recording/download'),
                            params={**self._auth_params(), 'id_list': recording_id},
                            timeout=60,
                            stream=True,
                        )
                        resp_poll.raise_for_status()
                        ct_poll = resp_poll.headers.get('Content-Type', '')
                        if 'application/json' not in ct_poll:
                            return _salvar(resp_poll)
                        d = resp_poll.json()
                        if d.get('errcode') not in (2, 0):
                            logger.error(f'Polling download falhou: {d}')
                            return False
                        if d.get('errmsg') != 'PROCESSING':
                            return _salvar(resp_poll)
                        logger.debug(f'Tentativa {tentativa+1}/15: ainda processando...')
                    logger.error(f'Download excedeu tempo de espera: {recording_file}')
                    return False

                # Resposta imediata com erro
                logger.error(f'Erro ao baixar {recording_file}: {dados}')
                return False

            else:
                # Firmware legado
                payload = {**self._auth_params(), 'recording_file': recording_file}
                resp = self._session.post(
                    _url('/api/v1.0/recording/download'),
                    json=payload,
                    timeout=120,
                    stream=True,
                )
                resp.raise_for_status()
                return _salvar(resp)

        except Exception as e:
            logger.error(f'Falha no download de {recording_file}: {e}')
            return False