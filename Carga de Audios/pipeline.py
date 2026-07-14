"""
Pipeline de Carga de Áudios — Yeastar → Transcrição → PG17
===========================================================

Fluxo por execução:
  1. Determina o período (padrão: dia anterior completo).
  2. Consulta public.contatos_telefone (PG9) filtrando por enterqueue no período
     → obtém o conjunto de call_ids válidos + notas NPS (perg1/perg2/perg3).
  3. Autentica no Yeastar e busca todas as gravações do período.
  4. Cruza os resultados: mantém apenas gravações cujo call_id está em contatos_telefone.
  5. Para cada gravação cruzada:
     a. Ignora se já existe no banco (idempotência).
     b. Baixa o áudio para diretório temporário.
     c. Transcreve com faster-whisper.
     d. Salva resultado no PG17 (gravacoes_telefone) incluindo as notas NPS.
     e. Apaga o arquivo temporário.
  6. Registra resumo da execução no log.

Uso:
    python pipeline.py                              # processa o dia anterior (padrão)
    python pipeline.py --inicio 2026-07-01 --fim 2026-07-08   # período fixo (reprocessamento)
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import config
from yeastar_client import YeastarClient
from transcricao import transcrever
from conecta_banco import get_connection, get_connection_source, buscar_contatos_dia, gravacao_ja_existe, inserir_gravacao


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

    logger = logging.getLogger('carga_audios')
    logger.setLevel(logging.DEBUG)

    fh = RotatingFileHandler(
        logs_dir / 'pipeline.log',
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
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
# Utilitários
# ---------------------------------------------------------------------------

def _periodo_execucao(inicio: str = None, fim: str = None):
    """
    Calcula data_inicio e data_fim.
    Prioridade: --inicio/--fim > padrão (dia anterior completo).

    O padrão é sempre o dia anterior: 00:00:00 → 23:59:59,
    refletindo a regra de "olhar para o dia anterior à execução".
    """
    if inicio and fim:
        return (
            datetime.strptime(inicio, '%Y-%m-%d'),
            datetime.strptime(fim,    '%Y-%m-%d').replace(hour=23, minute=59, second=59),
        )
    ontem = date.today() - timedelta(days=1)
    data_inicio = datetime.combine(ontem, datetime.min.time())
    data_fim    = datetime.combine(ontem, datetime.max.time().replace(microsecond=0))
    return data_inicio, data_fim


def _nome_arquivo_temp(gravacao: dict) -> str:
    """Gera um nome de arquivo seguro para o áudio temporário."""
    call_id = gravacao.get('id', gravacao.get('call_id', 'desconhecido'))
    # Substitui caracteres inválidos em nomes de arquivo
    safe_id = str(call_id).replace('/', '_').replace('\\', '_').replace(':', '_')
    return f"{safe_id}.wav"


def _extrair_metadados(gravacao: dict) -> dict:
    """
    Normaliza os campos retornados pelo Yeastar para o formato do banco.

    O Yeastar pode retornar nomes de campos em formatos distintos dependendo
    da versão do firmware — este mapeamento centraliza a normalização.
    """
    # Tenta múltiplos nomes de chave para call_id (o Yeastar varia entre versões)
    call_id = (
        gravacao.get('id') or
        gravacao.get('call_id') or
        gravacao.get('recording_id') or
        gravacao.get('uniqueid', '')
    )

    # Converte start_time do formato Yeastar (DD/MM/YYYY HH:MM:SS) para datetime
    start_raw = gravacao.get('start_time', '')
    try:
        iniciada_em = datetime.strptime(start_raw, '%d/%m/%Y %H:%M:%S')
    except ValueError:
        # Fallback para ISO caso o firmware use outro formato
        try:
            iniciada_em = datetime.fromisoformat(start_raw)
        except ValueError:
            iniciada_em = datetime.now()
            logger.warning(f'Não foi possível parsear start_time="{start_raw}" — usando agora.')

    duracao = int(gravacao.get('duration', 0))
    encerrada_em = iniciada_em + timedelta(seconds=duracao)

    # Ramal do agente (callee em chamadas inbound, caller em outbound)
    ramal = gravacao.get('callee', gravacao.get('extension', ''))
    agente = gravacao.get('callee_name', gravacao.get('agent_name', ''))

    return {
        'call_id':          str(call_id),
        'iniciada_em':      iniciada_em,
        'encerrada_em':     encerrada_em,
        'duracao_segundos': duracao,
        'ramal_agente':     str(ramal),
        'agente':           str(agente),
        'arquivo_original': gravacao.get('recording_file', ''),
    }


# ---------------------------------------------------------------------------
# Processamento de uma gravação
# ---------------------------------------------------------------------------

def processar_gravacao(yeastar: YeastarClient, conn, gravacao: dict, nps: dict) -> str:
    """
    Processa uma única gravação: download → transcrição → banco.

    Args:
        nps: dict com nps_velocidade, nps_solucao, nps_relacionamento vindos de contatos_telefone.

    Retorna:
        'ok'         — processada com sucesso
        'pulada'     — já existia no banco
        'erro'       — falha em alguma etapa
    """
    metadados = _extrair_metadados(gravacao)
    call_id = metadados['call_id']

    # Idempotência: não reprocessa se já está no banco
    if gravacao_ja_existe(conn, call_id):
        logger.debug(f'⏭  {call_id} já existe — pulando.')
        return 'pulada'

    # Garante que o diretório temporário existe
    config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    caminho_audio = config.TEMP_DIR / _nome_arquivo_temp(gravacao)

    try:
        # Download do áudio
        recording_file = gravacao.get('recording_file', '')
        if not recording_file:
            logger.warning(f'{call_id}: sem recording_file — pulando.')
            return 'erro'

        ok = yeastar.baixar_gravacao(recording_file, caminho_audio)
        if not ok:
            return 'erro'

        # Transcrição
        resultado = transcrever(caminho_audio)
        if 'erro' in resultado:
            logger.error(f'{call_id}: transcrição falhou — {resultado["erro"]}')
            return 'erro'

        # Monta o registro completo para inserção
        registro = {
            **metadados,
            'transcricao_texto':  resultado['texto'],
            'transcricao_raw':    json.dumps(resultado, ensure_ascii=False),
            'transcricao_idioma': resultado.get('idioma', ''),
            'transcricao_modelo': resultado.get('modelo', ''),
            'nps_velocidade':     nps.get('nps_velocidade'),
            'nps_solucao':        nps.get('nps_solucao'),
            'nps_relacionamento': nps.get('nps_relacionamento'),
        }

        inserir_gravacao(conn, registro)
        logger.info(f'✓ {call_id} | {metadados["duracao_segundos"]}s | {len(resultado["texto"])} chars')
        return 'ok'

    finally:
        # Remove o arquivo temporário independentemente do resultado
        if caminho_audio.exists():
            caminho_audio.unlink()


# ---------------------------------------------------------------------------
# Orquestrador principal
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Pipeline de carga de áudios Yeastar → PG17')
    parser.add_argument('--inicio', type=str, help='Data de início YYYY-MM-DD (padrão: ontem)')
    parser.add_argument('--fim',    type=str, help='Data de fim   YYYY-MM-DD (padrão: ontem)')
    args = parser.parse_args()

    logger.info('=' * 60)
    logger.info('PIPELINE CARGA DE ÁUDIOS — INICIANDO')
    logger.info('=' * 60)

    # Valida configurações antes de qualquer operação externa
    try:
        config.validate()
    except EnvironmentError as e:
        logger.error(str(e))
        sys.exit(1)

    data_inicio, data_fim = _periodo_execucao(args.inicio, args.fim)
    logger.info(f'Período: {data_inicio:%Y-%m-%d %H:%M} → {data_fim:%Y-%m-%d %H:%M}')

    # ---------------------------------------------------------------
    # Passo 1 — Consulta ao banco fonte (PG9) para obter os call_ids
    # do dia e as notas NPS (perg1/2/3) de contatos_telefone
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
        logger.info('Nenhum contato encontrado em contatos_telefone para o período. Encerrando.')
        return

    call_ids_esperados = set(contatos.keys())
    logger.info(f'{len(call_ids_esperados)} call_id(s) a processar via Yeastar.')

    # ---------------------------------------------------------------
    # Passo 2 — Autenticação e busca no Yeastar
    # ---------------------------------------------------------------
    yeastar = YeastarClient()
    try:
        yeastar.login()
    except Exception as e:
        logger.error(f'Falha ao autenticar no Yeastar: {e}')
        sys.exit(1)

    gravacoes_brutas = yeastar.buscar_gravacoes(data_inicio, data_fim)
    if not gravacoes_brutas:
        logger.info('Nenhuma gravação encontrada no Yeastar para o período. Encerrando.')
        return

    # ---------------------------------------------------------------
    # Passo 3 — Cruza: mantém apenas gravações presentes em contatos_telefone
    # ---------------------------------------------------------------
    gravacoes = [
        g for g in gravacoes_brutas
        if str(g.get('id', g.get('call_id', ''))) in call_ids_esperados
    ]
    logger.info(
        f'{len(gravacoes)} gravação(ões) após cruzamento '
        f'(descartadas: {len(gravacoes_brutas) - len(gravacoes)}).'
    )

    if not gravacoes:
        logger.info('Nenhuma gravação correspondente após cruzamento. Encerrando.')
        return

    # ---------------------------------------------------------------
    # Passo 4 — Conexão ao destino (PG17) e processamento
    # ---------------------------------------------------------------
    try:
        conn = get_connection()
    except Exception as e:
        logger.error(f'Falha ao conectar ao PG17: {e}')
        sys.exit(1)

    contadores = {'ok': 0, 'pulada': 0, 'erro': 0}
    total = len(gravacoes)

    try:
        for idx, gravacao in enumerate(gravacoes, 1):
            call_id = str(gravacao.get('id', gravacao.get('call_id', '?')))
            logger.info(f'[{idx}/{total}] Processando {call_id}...')
            nps = contatos.get(call_id, {})
            resultado = processar_gravacao(yeastar, conn, gravacao, nps)
            contadores[resultado] += 1

    finally:
        conn.close()

    # Resumo da execução
    logger.info('=' * 60)
    logger.info(
        f'CONCLUÍDO — '
        f'OK: {contadores["ok"]} | '
        f'Puladas: {contadores["pulada"]} | '
        f'Erros: {contadores["erro"]} | '
        f'Total: {total}'
    )
    logger.info('=' * 60)


if __name__ == '__main__':
    main()