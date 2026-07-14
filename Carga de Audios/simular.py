"""
Simulação do Pipeline de Carga de Áudios
=========================================
Executa o fluxo completo (PG9 → Yeastar → transcrição) sem tocar no banco PG17.

Resultados gerados em simulacao/:
  audios/   — arquivos de áudio baixados (mantidos após a execução)
  resultado_AAAA-MM-DD.json — metadados + transcrição + notas NPS de cada gravação

Uso:
    python simular.py                              # processa o dia anterior (padrão)
    python simular.py --inicio 2026-07-01 --fim 2026-07-08
"""

import argparse
import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import config
from yeastar_client import YeastarClient
from yeastar_browser_session import YeastarBrowserSession
from transcricao import transcrever
from conecta_banco import get_connection_source, buscar_contatos_dia

SIMULACAO_DIR = Path(__file__).parent / 'simulacao'


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _setup_logging():
    logs_dir = Path(__file__).parent / 'logs'
    logs_dir.mkdir(exist_ok=True)

    fmt = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    logger = logging.getLogger('carga_audios.simular')
    logger.setLevel(logging.DEBUG)

    fh = RotatingFileHandler(
        logs_dir / 'simular.log',
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8',
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


logger = _setup_logging()


# ---------------------------------------------------------------------------
# Utilitários (mesma lógica do pipeline.py)
# ---------------------------------------------------------------------------

def _periodo_execucao(inicio: str = None, fim: str = None):
    if inicio and fim:
        return (
            datetime.strptime(inicio, '%Y-%m-%d'),
            datetime.strptime(fim, '%Y-%m-%d').replace(hour=23, minute=59, second=59),
        )
    ontem = date.today() - timedelta(days=1)
    data_inicio = datetime.combine(ontem, datetime.min.time())
    data_fim    = datetime.combine(ontem, datetime.max.time().replace(microsecond=0))
    return data_inicio, data_fim


def _uniqueid_do_arquivo(filename: str) -> str:
    """Extrai o uniqueid Asterisk do nome do arquivo de gravação.
    Formato: YYYYMMDDHHMMSS-UNIQUEID-caller-callee-type.wav
    """
    m = re.match(r'\d{14}-(\d+\.\d+)-', filename)
    return m.group(1) if m else ''


def _extrair_metadados(gravacao: dict) -> dict:
    arquivo = gravacao.get('file', gravacao.get('recording_file', ''))

    # Prioridade: uid Yeastar (= call_id do PG9) > id interno
    # O uid tem formato YYYYMMDDHHMMSS+hex e é o mesmo valor em contatos_telefone.call_id
    call_id = (
        gravacao.get('uid') or
        gravacao.get('call_id') or
        str(gravacao.get('id', ''))
    )

    # P-Series v83+: campo 'time'; legado: 'start_time'
    start_raw = gravacao.get('time', gravacao.get('start_time', ''))
    try:
        iniciada_em = datetime.strptime(start_raw, '%d/%m/%Y %H:%M:%S')
    except ValueError:
        try:
            iniciada_em = datetime.fromisoformat(start_raw)
        except ValueError:
            iniciada_em = datetime.now()
            logger.warning(f'Nao foi possivel parsear time="{start_raw}" — usando agora.')

    duracao = int(gravacao.get('duration', 0))
    encerrada_em = iniciada_em + timedelta(seconds=duracao)

    # P-Series v83+: call_from contém "Nome<ramal>", call_from_number é o ramal limpo
    call_from = gravacao.get('call_from', '')
    ramal = gravacao.get('call_from_number', '') or call_from
    agente = gravacao.get('call_from_name', '') or call_from

    return {
        'call_id':          str(call_id),
        'iniciada_em':      iniciada_em.isoformat(),
        'encerrada_em':     encerrada_em.isoformat(),
        'duracao_segundos': duracao,
        'ramal_agente':     str(ramal),
        'agente':           str(agente),
        'arquivo_original': arquivo,
    }


# ---------------------------------------------------------------------------
# Processamento de uma gravação (sem banco)
# ---------------------------------------------------------------------------

def simular_gravacao(
    browser_session: YeastarBrowserSession,
    gravacao: dict,
    nps: dict,
    audios_dir: Path,
    uid: str = '',
) -> dict | None:
    """
    Baixa e transcreve uma gravacao sem gravar no banco.
    Usa o browser (Portal Admin) para baixar — fluxo manual replicado.

    Retorna o registro completo como dict, ou None em caso de erro.
    O arquivo de audio e mantido em audios_dir.
    """
    metadados = _extrair_metadados(gravacao)
    call_id = uid or metadados['call_id']  # uid Yeastar == call_id PG9 == campo custom_uid do portal

    if not call_id:
        logger.warning(f'Gravacao sem call_id identificavel — pulando.')
        return None

    safe_id = call_id.replace('/', '_').replace('\\', '_').replace(':', '_').replace('.', '_')
    caminho_audio = audios_dir / f'{safe_id}.wav'

    if caminho_audio.exists():
        logger.info(f'{call_id} — audio ja existe, reutilizando.')
    else:
        recording_id = int(gravacao.get('id', 0))
        ok = browser_session.baixar_gravacao(recording_id, caminho_audio)
        if not ok:
            return None

    resultado = transcrever(caminho_audio)
    if 'erro' in resultado:
        logger.error(f'{call_id}: transcrição falhou — {resultado["erro"]}')
        return None

    logger.info(f'✓ {call_id} | {metadados["duracao_segundos"]}s | {len(resultado["texto"])} chars')

    return {
        **metadados,
        'nps_velocidade':     nps.get('nps_velocidade'),
        'nps_solucao':        nps.get('nps_solucao'),
        'nps_relacionamento': nps.get('nps_relacionamento'),
        'transcricao_texto':  resultado['texto'],
        'transcricao_idioma': resultado.get('idioma', ''),
        'transcricao_modelo': resultado.get('modelo', ''),
        'transcricao_raw':    resultado,
        'audio_local':        str(caminho_audio),
    }


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Simulação do pipeline de carga de áudios (sem banco)')
    parser.add_argument('--inicio',  type=str,  help='Data de início YYYY-MM-DD (padrão: ontem)')
    parser.add_argument('--fim',     type=str,  help='Data de fim   YYYY-MM-DD (padrão: ontem)')
    parser.add_argument('--max',     type=int,  default=0, help='Limita a N gravacoes (0 = sem limite)')
    parser.add_argument('--browser', action='store_true',
                        help='Usa Edge (Playwright) para login — necessário quando GDPR bloqueia a API')
    args = parser.parse_args()

    logger.info('=' * 60)
    logger.info('SIMULAÇÃO — CARGA DE ÁUDIOS (sem gravação no banco)')
    logger.info('=' * 60)

    # Valida apenas o que a simulação usa (Yeastar) — PG17 não é necessário
    erros = []
    if not config.YEASTAR_USER:
        erros.append('YEASTAR_USER não configurado')
    if not config.YEASTAR_PASS:
        erros.append('YEASTAR_PASS não configurado')
    if erros:
        logger.error('Configuração incompleta:\n' + '\n'.join(f'  - {e}' for e in erros))
        sys.exit(1)

    data_inicio, data_fim = _periodo_execucao(args.inicio, args.fim)
    logger.info(f'Período: {data_inicio:%Y-%m-%d %H:%M} → {data_fim:%Y-%m-%d %H:%M}')

    # Diretórios de saída
    audios_dir = SIMULACAO_DIR / 'audios'
    audios_dir.mkdir(parents=True, exist_ok=True)

    json_saida = SIMULACAO_DIR / f'resultado_{data_inicio:%Y-%m-%d}.json'

    # ---------------------------------------------------------------
    # Passo 1 — Banco fonte (PG9)
    # ---------------------------------------------------------------
    try:
        conn_source = get_connection_source()
    except Exception as e:
        logger.error(f'Falha ao conectar ao banco fonte (PG9): {e}')
        sys.exit(1)

    try:
        contatos = buscar_contatos_dia(conn_source, data_inicio, data_fim)
    except Exception as e:
        logger.error(f'Falha ao consultar contatos_telefone: {e}')
        sys.exit(1)
    finally:
        conn_source.close()

    if not contatos:
        logger.info('Nenhum contato encontrado para o período. Encerrando.')
        return

    call_ids_esperados = set(contatos.keys())
    logger.info(f'{len(call_ids_esperados)} call_id(s) a processar via Yeastar.')

    # ---------------------------------------------------------------
    # Passo 2 — Yeastar: busca lista de gravacoes via API
    # ---------------------------------------------------------------
    yeastar = YeastarClient()
    try:
        yeastar.login()
    except Exception as e:
        logger.error(f'Falha ao autenticar no Yeastar (API): {e}')
        sys.exit(1)

    gravacoes_brutas = yeastar.buscar_gravacoes(data_inicio, data_fim)
    if not gravacoes_brutas:
        logger.info('Nenhuma gravacao encontrada no Yeastar. Encerrando.')
        return

    # ---------------------------------------------------------------
    # Passo 3 — Cruzamento
    # ---------------------------------------------------------------
    def _ids_gravacao(g: dict) -> list[str]:
        return [
            g.get('uid', ''),    # uid Yeastar == call_id PG9 (chave principal)
            g.get('call_id', ''),
            str(g.get('id', '')),
        ]

    gravacoes = [
        g for g in gravacoes_brutas
        if any(cid in call_ids_esperados for cid in _ids_gravacao(g) if cid)
    ]
    logger.info(
        f'{len(gravacoes)} gravacao(oes) apos cruzamento '
        f'(descartadas: {len(gravacoes_brutas) - len(gravacoes)}).'
    )

    # Deduplica por arquivo — mesmo WAV pode aparecer múltiplas vezes na API Yeastar
    vistos: set[str] = set()
    gravacoes_unicas = []
    for g in gravacoes:
        chave = g.get('file') or str(g.get('id', ''))
        if chave not in vistos:
            vistos.add(chave)
            gravacoes_unicas.append(g)
    if len(gravacoes_unicas) < len(gravacoes):
        logger.info(
            f'Deduplicacao: {len(gravacoes)} → {len(gravacoes_unicas)} '
            f'({len(gravacoes) - len(gravacoes_unicas)} duplicata(s) removida(s)).'
        )
    gravacoes = gravacoes_unicas

    if args.max and args.max > 0:
        gravacoes = gravacoes[:args.max]
        logger.info(f'Limitando a {len(gravacoes)} gravacao(oes) (--max {args.max}).')

    if not gravacoes:
        # Mostra amostras para diagnóstico
        amostra_yeastar = []
        for g in gravacoes_brutas[:3]:
            arquivo = g.get('file', '')
            uid_extraido = _uniqueid_do_arquivo(arquivo)
            amostra_yeastar.append({
                'uid': g.get('uid'), 'id': g.get('id'),
                'file': arquivo, 'uniqueid_extraido': uid_extraido,
            })
        amostra_pg9 = list(list(call_ids_esperados)[:3])
        logger.info(f'Amostra Yeastar (primeiros 3): {amostra_yeastar}')
        logger.info(f'Amostra call_ids PG9 (primeiros 3): {amostra_pg9}')
        logger.info('Nenhuma gravacao correspondente apos cruzamento. Encerrando.')
        return

    # ---------------------------------------------------------------
    # Passo 4 — Download (via Portal Admin) + transcrição + JSON
    # ---------------------------------------------------------------
    registros = []
    contadores = {'ok': 0, 'erro': 0}
    total = len(gravacoes)

    logger.info('Abrindo Portal Admin para downloads...')
    with YeastarBrowserSession() as browser_session:
        for idx, gravacao in enumerate(gravacoes, 1):
            arquivo = gravacao.get('file', '')
            uid = gravacao.get('uid', '')          # uid Yeastar == call_id PG9
            logger.info(f'[{idx}/{total}] uid={uid}  arquivo={arquivo}')

            # NPS: indexado por uid Yeastar (= call_id do PG9)
            nps = contatos.get(uid, {})

            registro = simular_gravacao(browser_session, gravacao, nps, audios_dir, uid)
            if registro:
                registros.append(registro)
                contadores['ok'] += 1
            else:
                contadores['erro'] += 1

    # Salva JSON (sobrescreve se ja existir para o mesmo dia)
    with open(json_saida, 'w', encoding='utf-8') as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)

    logger.info('=' * 60)
    logger.info('SIMULACAO CONCLUIDA')
    logger.info(f'  OK: {contadores["ok"]} | Erros: {contadores["erro"]} | Total: {total}')
    logger.info(f'  JSON salvo em: {json_saida}')
    logger.info(f'  Audios em:     {audios_dir}')
    logger.info('=' * 60)


if __name__ == '__main__':
    main()
