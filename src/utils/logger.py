import logging
from pathlib import Path

# Resolve project root (the QuantEngine directory)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger that outputs to both console and a log file.
    """
    # Ensure the logs directory exists
    log_dir = PROJECT_ROOT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console Handler (INFO level)
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.INFO)
    c_handler.setFormatter(formatter)
    logger.addHandler(c_handler)
    
    # File Handler (DEBUG level)
    log_file = log_dir / "pipeline.log"
    f_handler = logging.FileHandler(log_file, encoding='utf-8')
    f_handler.setLevel(logging.DEBUG)
    f_handler.setFormatter(formatter)
    logger.addHandler(f_handler)
    
    return logger
