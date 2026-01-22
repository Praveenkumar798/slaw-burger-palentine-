"""
Logging utility
"""

from datetime import datetime
from .config import LOG_FILE


class Logger:
    @staticmethod
    def log(message, level="INFO"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        print(log_entry)
        
        with open(LOG_FILE, 'a') as f:
            f.write(log_entry + "\n")
    
    @staticmethod
    def info(message):
        Logger.log(message, "INFO")
    
    @staticmethod
    def warning(message):
        Logger.log(message, "WARNING")
    
    @staticmethod
    def error(message):
        Logger.log(message, "ERROR")
    
    @staticmethod
    def section(title):
        separator = "=" * 70
        Logger.log(separator)
        Logger.log(title)
        Logger.log(separator)