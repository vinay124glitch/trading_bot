import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_file="trading_bot.log", log_level=logging.INFO):
    """
    Configures application-wide logging.
    Logs are written to both a console handler (stdout) and a rolling file handler.
    """
    # Create logger
    logger = logging.getLogger("trading_bot")
    logger.setLevel(log_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if logger.handlers:
        return logger

    # Define formats
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s"
    )
    console_formatter = logging.Formatter(
        "[%(levelname)s] %(message)s"
    )

    # Console Handler (clean output for user)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler (detailed output for auditing/debugging)
    try:
        # Ensure log directory or file can be created/written to
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)  # Capture all debug logs in the file
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Also elevate overall logger level to DEBUG so file handler gets debug messages
        logger.setLevel(logging.DEBUG)
    except Exception as e:
        print(f"Warning: Could not configure log file handler ({e}). Logging to console only.")

    return logger

# Get or create the logger instance
logger = logging.getLogger("trading_bot")
