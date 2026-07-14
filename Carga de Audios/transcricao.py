"""
Módulo de transcrição de áudio usando faster-whisper.

Carrega o modelo uma única vez (caro em memória) e oferece a função
transcrever() para uso pela pipeline.

Saída de transcrever():
    {
        'texto': str,               # transcrição completa em texto plano
        'idioma': str,              # idioma detectado (ex: 'pt')
        'idioma_probabilidade': float,
        'segmentos': [              # lista de segmentos com timestamps
            {'inicio': float, 'fim': float, 'texto': str},
            ...
        ],
        'modelo': str               # nome do modelo usado
    }
"""

import logging
from pathlib import Path
from config import config

logger = logging.getLogger('carga_audios.transcricao')

# Carregamento lazy do modelo — ocorre na primeira chamada a transcrever()
# para não bloquear o startup da pipeline se a transcrição não for necessária.
_modelo = None


def _carregar_modelo():
    """Instancia o modelo faster-whisper (download automático na primeira vez)."""
    global _modelo
    if _modelo is not None:
        return _modelo

    from faster_whisper import WhisperModel

    compute = 'int8' if config.WHISPER_DEVICE == 'cpu' else 'float16'
    fallbacks = [config.WHISPER_MODEL, 'small', 'base', 'tiny']
    seen = []
    for nome in fallbacks:
        if nome in seen:
            continue
        seen.append(nome)
        try:
            logger.info(f'Carregando modelo Whisper "{nome}" ({config.WHISPER_DEVICE}/{compute})...')
            _modelo = WhisperModel(nome, device=config.WHISPER_DEVICE, compute_type=compute)
            logger.info(f'Modelo Whisper "{nome}" carregado.')
            return _modelo
        except (RuntimeError, MemoryError) as e:
            logger.warning(f'Falha ao carregar "{nome}": {e} — tentando modelo menor...')

    raise RuntimeError('Nao foi possivel carregar nenhum modelo Whisper (memoria insuficiente).')


def transcrever(caminho_audio: Path) -> dict:
    """
    Transcreve um arquivo de áudio e retorna o resultado estruturado.

    Args:
        caminho_audio: Caminho completo para o arquivo de áudio (WAV, MP3, etc.)

    Returns:
        Dicionário com texto, idioma, segmentos e modelo.
        Em caso de erro, retorna dict com 'texto' vazio e 'erro' com a mensagem.
    """
    modelo = _carregar_modelo()

    try:
        logger.debug(f'Transcrevendo: {caminho_audio.name}')

        # language=None ativa detecção automática; fixar em 'pt' é mais rápido
        # e evita confusão entre português e espanhol em ligações curtas.
        segmentos_iter, info = modelo.transcribe(
            str(caminho_audio),
            language=config.WHISPER_LANGUAGE or None,
            beam_size=5,
            vad_filter=True,          # Remove silêncio antes de transcrever
            vad_parameters={'min_silence_duration_ms': 500},
        )

        segmentos = []
        partes_texto = []

        for seg in segmentos_iter:
            segmentos.append({
                'inicio': round(seg.start, 2),
                'fim':    round(seg.end, 2),
                'texto':  seg.text.strip(),
            })
            partes_texto.append(seg.text.strip())

        texto_completo = ' '.join(partes_texto)

        logger.debug(
            f'{caminho_audio.name}: {len(segmentos)} segmento(s), '
            f'idioma={info.language} ({info.language_probability:.0%})'
        )

        return {
            'texto':                texto_completo,
            'idioma':               info.language,
            'idioma_probabilidade': round(info.language_probability, 4),
            'segmentos':            segmentos,
            'modelo':               config.WHISPER_MODEL,
        }

    except Exception as e:
        logger.error(f'Erro ao transcrever {caminho_audio.name}: {e}')
        return {
            'texto':    '',
            'idioma':   '',
            'segmentos': [],
            'modelo':   config.WHISPER_MODEL,
            'erro':     str(e),
        }