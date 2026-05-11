import logging
from pathlib import Path




def configurar_logger(nome_log='app', arquivo_log=f'logs.log', nivel=logging.INFO):


    path = Path(__file__).parent
    
    caminho_log = path / arquivo_log  # Correção aqui

    """
    Configura o logger para salvar em arquivo e exibir no console.

    Parâmetros:
    - nome_log: Nome do logger (pode ser usado para loggers separados).
    - arquivo_log: Caminho do arquivo onde os logs serão salvos.
    - nivel: Nível de log (ex: logging.INFO, logging.DEBUG, etc).
    """
    logger = logging.getLogger(nome_log)
    logger.setLevel(nivel)

    # Evita handlers duplicados se a função for chamada mais de uma vez
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatação do log
    formato = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')

    # Handler para arquivo
    file_handler = logging.FileHandler(caminho_log)
    file_handler.setFormatter(formato)

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formato)

    # Adiciona os handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
