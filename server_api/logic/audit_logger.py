import logging
import os
import sys
from datetime import datetime

class AuditLogger:
    def __init__(self, log_dir: str = "LOGS"):
        self.is_vercel = os.getenv("VERCEL") == "1"
        self.log_dir = log_dir
        
        # Só tentamos criar pastas se NÃO estivermos no Vercel
        if not self.is_vercel:
            if not os.path.exists(self.log_dir):
                try:
                    os.makedirs(self.log_dir)
                except:
                    pass
            
        # Logger Principal do Servidor
        self.main_logger = self._setup_logger("main", "server.log")
            
        # Logger de Acesso (Entradas/Saídas)
        self.access_logger = self._setup_logger("access", "access.log")
        
        # Logger de Registros (Auditorias de Higiene)
        self.registros_logger = self._setup_logger("registros", "registros.log")
        
        # Logger de Erros do Sistema
        self.error_logger = self._setup_logger("errors", "system_errors.log")

    def _setup_logger(self, name, log_file, level=logging.INFO):
        logger = logging.getLogger(name)
        if not logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            
            # Handler de Console (Funciona em qualquer lugar e essencial no Vercel)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            # Handler de Arquivo (Só se NÃO estivermos no Vercel)
            if not self.is_vercel:
                try:
                    log_path = os.path.join(self.log_dir, log_file)
                    file_handler = logging.FileHandler(log_path, encoding='utf-8')
                    file_handler.setFormatter(formatter)
                    logger.addHandler(file_handler)
                except Exception as e:
                    print(f"[LOGGER_WARN] Não foi possível criar arquivo de log: {e}")

            logger.setLevel(level)
        return logger

    def log_event(self, user: str, action: str, details: str = ""):
        message = f"User: {user} | Action: {action} | Details: {details}"
        self.access_logger.info(message)

    def log_system(self, message: str, level=logging.INFO):
        if level == logging.ERROR:
            self.error_logger.error(message)
        else:
            self.main_logger.info(message)

    def log_error(self, context: str, error: str):
        message = f"Context: {context} | Error: {error}"
        self.error_logger.error(message)

# Instância global
logger = AuditLogger()
