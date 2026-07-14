"""
Sessao browser reutilizavel para download de gravacoes do Yeastar Admin Portal.

Fluxo por gravacao:
  1. Navega para /cdr_recording/recording (portal JS/WebSocket fica ativo)
  2. Dispara fetch POST /api/v1.0/recording/download com id_list=[id]
  3. O portal JS recebe notificacao WebSocket quando o arquivo esta pronto
  4. Playwright captura o download via page.expect_download()
  5. Salva o .wav (ou extrai de .zip se vier compactado)
"""

import time
import logging
import zipfile
from pathlib import Path

from config import config

logger = logging.getLogger('carga_audios.yeastar')


def _log(msg: str):
    print(f'[Browser] {msg}', flush=True)
    logger.info(msg)


class YeastarBrowserSession:

    def __init__(self):
        self._playwright = None
        self._browser    = None
        self._context    = None
        self._page       = None
        self._na_pagina_gravacoes = False

    def __enter__(self):
        self._abrir()
        return self

    def __exit__(self, *_):
        self._fechar()

    # ------------------------------------------------------------------

    def _abrir(self):
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            channel='msedge',
            headless=False,
            slow_mo=200,
            args=['--start-maximized'],
        )
        self._context = self._browser.new_context(
            ignore_https_errors=True,
            viewport=None,
        )
        self._page = self._context.new_page()
        self._fazer_login()

    def _fechar(self):
        try:
            self._browser.close()
        except Exception:
            pass
        try:
            self._playwright.stop()
        except Exception:
            pass

    def _pagina_ok(self) -> bool:
        try:
            _ = self._page.url
            return True
        except Exception:
            return False

    def _garantir_sessao(self):
        if not self._pagina_ok():
            _log('Pagina fechada — reabrindo sessao...')
            self._na_pagina_gravacoes = False
            self._fechar()
            self._abrir()

    def _fazer_login(self):
        portal_url = config.YEASTAR_URL.rstrip('/')
        page = self._page

        _log(f'Abrindo portal: {portal_url}')
        page.goto(portal_url, timeout=30000, wait_until='networkidle')

        page.wait_for_selector('#login_username', timeout=15000)
        page.fill('#login_username', config.YEASTAR_USER)
        page.fill('#login_password', config.YEASTAR_PASS)
        page.click('#login-btn')
        _log('Clicou em "Iniciar Sessao".')

        try:
            page.wait_for_selector('text=Acessar Portal Admin', timeout=20000)
            page.click('text=Acessar Portal Admin')
            _log('Clicou em "Acessar Portal Admin".')
            page.wait_for_load_state('networkidle', timeout=20000)
        except Exception as exc:
            _log(f'Botao Admin nao encontrado: {exc}')

        _log('Login concluido.')

    def _garantir_pagina_gravacoes(self):
        """Navega para /cdr_recording/recording se ainda nao estiver la."""
        if self._na_pagina_gravacoes and '/cdr_recording/recording' in self._page.url:
            return

        page = self._page
        portal_url = config.YEASTAR_URL.rstrip('/')

        try:
            page.click('text=Relatórios e Gravações', timeout=6000)
            time.sleep(0.8)
        except Exception:
            pass

        try:
            page.click('#m_recording', timeout=6000)
            page.wait_for_load_state('domcontentloaded', timeout=15000)
            time.sleep(1.5)
        except Exception:
            page.goto(f'{portal_url}/cdr_recording/recording',
                      timeout=20000, wait_until='domcontentloaded')
            time.sleep(1.5)

        self._na_pagina_gravacoes = True
        _log('Na pagina de gravacoes (portal JS/WS ativo).')

    def baixar_gravacao(self, recording_id: int, destino_path: Path) -> bool:
        """
        Baixa um audio usando o id interno Yeastar.

        Dispara fetch POST /api/v1.0/recording/download de dentro do portal
        (WebSocket ja conectado) e captura o arquivo via page.expect_download().

        Retorna True se bem-sucedido, False caso contrario.
        """
        self._garantir_sessao()
        self._garantir_pagina_gravacoes()

        page = self._page
        destino_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with page.expect_download(timeout=180000) as dl_info:
                result = page.evaluate(f"""async () => {{
                    const resp = await fetch('/api/v1.0/recording/download', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{id_list: [{recording_id}]}}),
                        credentials: 'include'
                    }});
                    const ct = resp.headers.get('content-type') || '';
                    if (ct.includes('json')) {{
                        return await resp.json();
                    }}
                    return {{type: 'binary'}};
                }}""")
                _log(f'id={recording_id} fetch={result}')

            dl = dl_info.value
            if dl.failure():
                _log(f'Download falhou: {dl.failure()}')
                return False

            tmp = destino_path.with_suffix('.download_tmp')
            dl.save_as(str(tmp))
            _log(f'Recebido: {dl.suggested_filename} ({tmp.stat().st_size} bytes)')

            if zipfile.is_zipfile(str(tmp)):
                with zipfile.ZipFile(str(tmp)) as zf:
                    audios = [n for n in zf.namelist()
                              if n.lower().endswith(('.wav', '.mp3', '.ogg', '.m4a'))]
                    if not audios:
                        _log('ZIP sem arquivo de audio.')
                        tmp.unlink(missing_ok=True)
                        return False
                    data = zf.read(audios[0])
                tmp.unlink(missing_ok=True)
                destino_path.write_bytes(data)
            else:
                tmp.rename(destino_path)

            _log(f'Salvo: {destino_path.name}')
            return True

        except Exception as exc:
            _log(f'Erro id={recording_id}: {exc}')
            return False
