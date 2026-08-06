"""Logging configuration for the application."""

import logging
import sys
from pathlib import Path

# Create logs directory
log_dir = Path("logs")


def setup_logging(log_level: str = "INFO", debug: bool = False) -> logging.Logger:
    """Set up logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        debug: Whether to enable debug logging
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("ai_sql_agent")
    logger.setLevel(log_level)
    
    # Avoid adding duplicate handlers if setup_logging is called multiple times
    if logger.handlers:
        return logger

    # Create formatters
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (wrapped in try-except for read-only or container environments like Streamlit Cloud)
    try:
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "ai_sql_agent.log")
        file_handler.setLevel(logging.DEBUG if debug else log_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"File logging not available, using console logging only: {e}")
    
    return logger
