"""
Abre o Edge logado no Portal Admin e navega ate Arquivos de Gravacao.
Aguarda voce clicar em Download em qualquer gravacao.
Captura TUDO que acontece na rede e salva em captura_download.json.

Uso:
    python capturar_download.py

Passos:
    1. O Edge abre e faz login automaticamente
    2. Clica em "Acessar Portal Admin"
    3. Navega para Arquivos de Gravacao
    4. VOCE: seleciona qualquer gravacao e clica em "Baixar Gravacoes"
    5. Aguarda 3 minutos, depois fecha e salva
"""

import sys, io, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright
from config import config

SAIDA = 'captura_download.json'
log = []


def capturar(tipo, url, extra):
    if any(p in url for p in ['/api/', '/record', '/cdr', '/download', '/ws']):
        entry = {'tipo': tipo, 'url': url, **extra}
        log.append(entry)
        print(f'[{tipo}] {url}', flush=True)
        for k, v in extra.items():
            if v and k not in ('headers',):
                v_str = str(v)[:400]
                print(f'  {k}: {v_str}', flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=False, slow_mo=200,
                                args=['--start-maximized'])
    ctx = browser.new_context(ignore_https_errors=True, viewport=None)
    page = ctx.new_page()

    page.on('request', lambda r: capturar('REQ', r.url, {
        'method': r.method, 'body': r.post_data or ''}))
    page.on('response', lambda r: capturar('RES', r.url, {
        'status': r.status,
        'ct': r.headers.get('content-type', ''),
        'cl': r.headers.get('content-length', '?'),
        'body': (lambda: (
            r.text()[:600] if 'json' in r.headers.get('content-type','')
            else f'<BINARIO size={r.headers.get("content-length","?")}>'
        ) if not ('audio' in r.headers.get('content-type','') or
                  'octet' in r.headers.get('content-type','') or
                  'zip' in r.headers.get('content-type','')) else ...)()
    }))

    # Login
    portal = config.YEASTAR_URL.rstrip('/')
    print(f'\nAbrindo {portal}...', flush=True)
    page.goto(portal, timeout=30000, wait_until='networkidle')
    page.wait_for_selector('#login_username', timeout=15000)
    page.fill('#login_username', config.YEASTAR_USER)
    page.fill('#login_password', config.YEASTAR_PASS)
    page.click('#login-btn')

    try:
        page.wait_for_selector('text=Acessar Portal Admin', timeout=20000)
        page.click('text=Acessar Portal Admin')
        page.wait_for_load_state('networkidle', timeout=20000)
        print('Portal Admin aberto.', flush=True)
    except Exception as e:
        print(f'Portal Admin nao encontrado: {e}', flush=True)

    # Navega para Arquivos de Gravacao
    try:
        page.click('text=Relat', timeout=8000)
        time.sleep(1)
    except Exception:
        pass
    try:
        page.click('#m_recording', timeout=8000)
        page.wait_for_load_state('domcontentloaded', timeout=15000)
        print('Pagina de gravacoes carregada.', flush=True)
    except Exception:
        page.goto(f'{portal}/cdr_recording/recording', timeout=20000, wait_until='domcontentloaded')

    print('\n' + '='*60, flush=True)
    print('SELECIONE UMA GRAVACAO E CLIQUE EM "BAIXAR GRAVACOES"', flush=True)
    print('Aguardando 3 minutos (180s)...', flush=True)
    print('='*60, flush=True)

    # Aguarda download automaticamente
    try:
        with page.expect_download(timeout=180000) as dl_info:
            time.sleep(180)  # espera o usuario clicar
        dl = dl_info.value
        print(f'\nDOWNLOAD CAPTURADO: {dl.suggested_filename}', flush=True)
        dl.save_as(f'captura_{dl.suggested_filename}')
        print(f'Salvo como: captura_{dl.suggested_filename}', flush=True)
    except Exception as e:
        print(f'Download nao capturado: {e}', flush=True)

    with open(SAIDA, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f'\n{len(log)} evento(s) capturado(s) em {SAIDA}', flush=True)
    browser.close()
