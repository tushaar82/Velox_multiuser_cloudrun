"""
Logging configuration for the trading platform.
"""
import logging
import sys
from typing import Optional

from shared.config import get_settings


def setup_logging(service_name: str, level: Optional[str] = None) -> None:
    """
    Configure logging for a service.
    
    Args:
        service_name: Name of the service (e.g., 'api_gateway')
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    settings = get_settings()
    
    # Determine log level
    if level is None:
        level = "DEBUG" if settings.debug else "INFO"
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Service-specific logger
    service_logger = logging.getLogger(service_name)
    service_logger.setLevel(level)
    
    logging.info(f"Logging configured for {service_name} at {level} level")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
