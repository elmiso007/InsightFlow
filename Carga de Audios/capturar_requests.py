"""
Abre o Edge logado no Yeastar (Portal Admin) e captura todas as chamadas de API
enquanto voce navega manualmente. Resultado salvo em captura_requests.json.

Uso:
    python capturar_requests.py

Passos:
    1. O Edge abre, preenche login e clica em "Iniciar Sessao" automaticamente
    2. Clica em "Acessar Portal Admin" automaticamente
    3. Navegue ate a secao de Gravacoes e clique em Download
    4. Quando terminar, pressione ENTER no terminal
    5. O resultado com todas as chamadas fica em captura_requests.json
"""

import json
import sys
import io
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright
from config import config

SAIDA = 'captura_requests.json'
requests_log = []


def on_request(request):
    url = request.url
    if any(p in url for p in ['/api/', '/gdpr', '/record', '/cdr']):
        entry = {
            'tipo':      'REQUEST',
            'method':    request.method,
            'url':       url,
            'post_data': request.post_data or '',
        }
        requests_log.append(entry)
        print(f'  REQ  {request.method:6} {url}', flush=True)
        if entry['post_data']:
            print(f'         body: {entry["post_data"][:300]}', flush=True)


def on_response(response):
    url = response.url
    if any(p in url for p in ['/api/', '/gdpr', '/record', '/cdr']):
        try:
            ct = response.headers.get('content-type', '')
            if 'application/json' in ct:
                body = response.text()[:600]
            elif any(x in ct for x in ['audio', 'octet', 'zip', 'wav']):
                body = f'<BINARIO content-type={ct} size={response.headers.get("content-length","?")}>'
            else:
                body = response.text()[:200]
        except Exception:
            body = '<erro ao ler body>'

        entry = {
            'tipo':   'RESPONSE',
            'status': response.status,
            'url':    url,
            'ct':     response.headers.get('content-type', ''),
            'body':   body,
        }
        requests_log.append(entry)
        print(f'  RES  {response.status:3} {url}', flush=True)
        print(f'         ct={entry["ct"]}', flush=True)
        print(f'         body: {body[:400]}', flush=True)


portal_url = config.YEASTAR_URL.rstrip('/')

with sync_playwright() as p:
    browser = p.chromium.launch(
        channel='msedge',
        headless=False,
        slow_mo=300,
        args=['--start-maximized'],
    )
    context = browser.new_context(ignore_https_errors=True, viewport=None)
    page = context.new_page()

    page.on('request',  on_request)
    page.on('response', on_response)

    print(f'\nAbrindo portal: {portal_url}', flush=True)
    page.goto(portal_url, timeout=30000, wait_until='networkidle')

    # ── Passo 1: preenche login ──────────────────────────────────────────────
    try:
        page.wait_for_selector('#login_username', timeout=15000)
        page.fill('#login_username', config.YEASTAR_USER)
        page.fill('#login_password', config.YEASTAR_PASS)
        print('Credenciais preenchidas.', flush=True)
        page.click('#login-btn')
        print('Clicou em "Iniciar Sessao".', flush=True)
    except Exception as e:
        print(f'Login automatico falhou: {e}', flush=True)

    # ── Passo 2: aguarda e clica em "Acessar Portal Admin" ──────────────────
    print('Aguardando opcao "Acessar Portal Admin"...', flush=True)
    try:
        page.wait_for_selector('text=Acessar Portal Admin', timeout=20000)
        page.click('text=Acessar Portal Admin')
        print('Clicou em "Acessar Portal Admin".', flush=True)
        page.wait_for_load_state('networkidle', timeout=15000)
    except Exception as e:
        print(f'Opcao "Acessar Portal Admin" nao encontrada: {e}', flush=True)
        print('Continue manualmente se necessario.', flush=True)

    print('\n' + '='*60, flush=True)
    print('PORTAL ADMIN ABERTO.', flush=True)
    print('Navegue ate Gravacoes e clique em Download em algum audio.', flush=True)
    print('Todas as chamadas de API aparecem acima em tempo real.', flush=True)
    print('\nPressione ENTER aqui quando terminar.', flush=True)
    print('='*60, flush=True)
    input()

    with open(SAIDA, 'w', encoding='utf-8') as f:
        json.dump(requests_log, f, ensure_ascii=False, indent=2)

    print(f'\n{len(requests_log)} evento(s) capturado(s) salvos em {SAIDA}', flush=True)
    browser.close()
