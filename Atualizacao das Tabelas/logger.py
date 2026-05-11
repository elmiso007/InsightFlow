import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


class LoggerConfig:
    """Classe para configurar e gerenciar logs de forma centralizada"""
    
    # Configurações padrão
    LOG_DIR = Path("logs")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT = "%d/%m/%Y %H:%M:%S"
    DEFAULT_LEVEL = logging.INFO
    
    @staticmethod
    def setup_logger(
        name: str,
        log_file: str = None,
        level: int = logging.INFO,
        console: bool = True,
        file_handler: bool = True,
        max_bytes: int = 5 * 1024 * 1024,  # 5MB
        backup_count: int = 5
    ) -> logging.Logger:
        """
        Configura um logger com handlers para arquivo e console.
        
        Args:
            name: Nome do logger (geralmente __name__)
            log_file: Nome do arquivo de log (opcional)
            level: Nível de logging (logging.DEBUG, INFO, etc)
            console: Se deve adicionar handler de console
            file_handler: Se deve adicionar handler de arquivo
            max_bytes: Tamanho máximo do arquivo de log antes de rotacionar
            backup_count: Número de backups a manter
            
        Returns:
            logging.Logger: Logger configurado
        """
        
        # Criar diretório de logs se não existir
        LoggerConfig.LOG_DIR.mkdir(exist_ok=True)
        
        # Criar ou obter logger
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Evitar adicionar handlers duplicados
        if logger.handlers:
            return logger
        
        # Formatter
        formatter = logging.Formatter(LoggerConfig.LOG_FORMAT, LoggerConfig.DATE_FORMAT)
        
        # Handler de Console
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # Handler de Arquivo
        if file_handler and log_file:
            log_path = LoggerConfig.LOG_DIR / log_file
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    @staticmethod
    def get_logger(name: str, log_file: str = None, level: int = logging.INFO) -> logging.Logger:
        """
        Obtém um logger já configurado ou cria um novo.
        
        Args:
            name: Nome do logger
            log_file: Nome do arquivo de log
            level: Nível de logging
            
        Returns:
            logging.Logger: Logger configurado
        """
        if log_file is None:
            log_file = f"{name.replace('.', '_')}.log"
        
        return LoggerConfig.setup_logger(name, log_file, level)


# Exemplo de uso e função de conveniência
def get_logger(name: str, log_file: str = None, level: int = logging.INFO) -> logging.Logger:
    """
    Função de conveniência para obter um logger configurado.
    
    Uso:
        from logger import get_logger
        
        logger = get_logger(__name__)
        logger.info("Informação importante")
        logger.error("Erro encontrado")
    """
    return LoggerConfig.get_logger(name, log_file, level)
