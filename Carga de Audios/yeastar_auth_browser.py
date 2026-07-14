"""
Autenticação no Yeastar via browser (Playwright + Edge).

Fluxo:
1. Abre Edge, faz login automático
2. Navega à seção de gravações do portal (onde o GDPR para download pode aparecer)
3. Testa recording/search via fetch do próprio browser (usa cookies do browser)
4. Se OK: extrai dados diretamente do browser e retorna
5. Se ainda 504: aguarda interação manual do usuário e captura endpoint de GDPR
"""

import logging
import time
from typing import Optional

from config import config

logger = logging.getLogger('carga_audios.yeastar')


def _log(msg: str):
    print(f'[Browser] {msg}', flush=True)
    logger.info(msg)


def login_via_browser() -> tuple[str, list[dict]]:
    """
    Abre o Edge, faz login no portal Yeastar e captura a sessão autenticada.

    Retorna:
        (websession_cookie, requests_capturadas)
    """
    from playwright.sync_api import sync_playwright

    portal_url = config.YEASTAR_URL.rstrip('/')
    requests_capturadas: list[dict] = []
    websession: Optional[str] = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel='msedge',
            headless=False,
            slow_mo=300,
            args=['--start-maximized'],
        )
        context = browser.new_context(
            ignore_https_errors=True,
            viewport=None,
        )
        page = context.new_page()

        # ── Captura requests E responses de API ─────────────────────────────
        def on_request(request):
            url = request.url
            if '/api/' in url or '/gdpr' in url:
                entry = {
                    'method':    request.method,
                    'url':       url,
                    'post_data': request.post_data or '',
                }
                requests_capturadas.append(entry)
                _log(f'REQ {request.method} {url}  body={entry["post_data"][:120]}')

        def on_response(response):
            url = response.url
            if '/api/' in url or '/gdpr' in url:
                try:
                    body = response.text()[:400]
                except Exception:
                    body = '<binary>'
                _log(f'RES {response.status} {url}  body={body}')

        page.on('request',  on_request)
        page.on('response', on_response)

        # ── Navegação e login ────────────────────────────────────────────────
        _log(f'Abrindo portal: {portal_url}')
        page.goto(portal_url, timeout=30000, wait_until='networkidle')

        try:
            page.wait_for_selector('#login_username', timeout=15000)
            _log('Formulario de login detectado — preenchendo credenciais...')
            page.fill('#login_username', config.YEASTAR_USER)
            page.fill('#login_password', config.YEASTAR_PASS)
            page.click('#login-btn')
            _log('Clicou em "Iniciar Sessao".')
        except Exception as exc:
            _log(f'Login automatico falhou: {exc}')

        # Aguarda e clica em "Acessar Portal Admin"
        try:
            page.wait_for_selector('text=Acessar Portal Admin', timeout=20000)
            page.click('text=Acessar Portal Admin')
            _log('Clicou em "Acessar Portal Admin".')
            page.wait_for_load_state('networkidle', timeout=15000)
        except Exception as exc:
            _log(f'Botao "Acessar Portal Admin" nao encontrado: {exc}')

        # ── Aguarda portal carregar ──────────────────────────────────────────
        for tick in range(60):
            time.sleep(0.5)
            current_url = page.url
            if '/login' not in current_url and portal_url in current_url and tick > 4:
                _log(f'Portal carregado: {current_url}')
                break
        else:
            _log(f'Portal nao carregou em 30s — URL: {page.url}')

        time.sleep(2)

        # ── Navega à seção de gravações ──────────────────────────────────────
        # O portal usa hash routing — tenta rotas conhecidas
        recording_routes = [
            '/#/personal/recording',
            '/#/recording',
            '/#/cdr/recording',
        ]
        for rota in recording_routes:
            try:
                dest = portal_url + rota
                _log(f'Navegando para gravacoes: {dest}')
                page.goto(dest, timeout=15000, wait_until='domcontentloaded')
                time.sleep(3)
                current = page.url
                _log(f'URL apos navegacao: {current}')
                break
            except Exception as exc:
                _log(f'Falha ao navegar {rota}: {exc}')

        # ── Procura botões de GDPR na página de gravações ────────────────────
        time.sleep(2)
        _log('Botoes visiveis na pagina atual:')
        try:
            for btn in page.locator('button').all():
                try:
                    txt = btn.inner_text(timeout=500).strip()
                    if txt:
                        _log(f'  BOTAO: "{txt}"')
                    if any(kw in txt.lower() for kw in [
                        'agree', 'accept', 'aceitar', 'concordo',
                        'download', 'baixar', 'ok', 'confirm', 'i agree',
                    ]):
                        _log(f'  >> Clicando em: "{txt}"')
                        btn.click()
                        time.sleep(2)
                except Exception:
                    pass
        except Exception as exc:
            _log(f'Erro ao listar botoes: {exc}')

        # ── Testa recording/search via fetch do browser ──────────────────────
        _log('Testando recording/search via fetch do browser...')
        try:
            js_result = page.evaluate("""
                async () => {
                    const hoje = new Date();
                    const ontem = new Date(hoje);
                    ontem.setDate(ontem.getDate() - 1);
                    const pad = n => String(n).padStart(2,'0');
                    const fmt = d => `${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()} 00:00:00`;
                    const fmtFim = d => `${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()} 23:59:59`;
                    const url = `/api/v1.0/recording/search?start_time=${encodeURIComponent(fmt(ontem))}&end_time=${encodeURIComponent(fmtFim(ontem))}`;
                    try {
                        const r = await fetch(url, {credentials: 'include'});
                        const text = await r.text();
                        return {status: r.status, body: text.substring(0, 500)};
                    } catch(e) {
                        return {status: -1, body: String(e)};
                    }
                }
            """)
            _log(f'recording/search via browser: status={js_result.get("status")} body={js_result.get("body", "")[:300]}')
        except Exception as exc:
            _log(f'Erro no fetch via browser: {exc}')

        # ── Aguarda mais 20s para interação manual (caso GDPR precise de click) ──
        _log('Aguardando 20s para qualquer interacao manual...')
        _log('Se aparecer alguma tela de aceite, CLIQUE MANUALMENTE.')
        time.sleep(20)

        # ── Extrai cookie websession ─────────────────────────────────────────
        for cookie in context.cookies():
            if cookie['name'] == 'websession':
                websession = cookie['value']
                _log(f'Cookie websession: {websession[:12]}...')
                break

        _log(f'Total requests capturadas: {len(requests_capturadas)}')
        browser.close()

    if not websession:
        raise RuntimeError(
            'Cookie websession nao capturado. Verifique se o login foi concluido.'
        )

    return websession, requests_capturadas
