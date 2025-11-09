"""
Logging configuration for the trading platform.
Provides structured logging with JSON output for Cloud Logging.
"""
import logging
import sys
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime

from shared.config import get_settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'severity': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'account_id'):
            log_data['account_id'] = record.account_id
        if hasattr(record, 'strategy_id'):
            log_data['strategy_id'] = record.strategy_id
        if hasattr(record, 'order_id'):
            log_data['order_id'] = record.order_id
        if hasattr(record, 'trading_mode'):
            log_data['trading_mode'] = record.trading_mode
        if hasattr(record, 'event'):
            log_data['event'] = record.event
        
        return json.dumps(log_data)


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
    
    # Use JSON formatting in production (Cloud Run)
    use_json = os.getenv('ENVIRONMENT', 'development') == 'production'
    
    # Create formatter
    if use_json:
        formatter = JSONFormatter()
    else:
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


class LogContext:
    """Context manager for adding extra fields to log records"""
    
    def __init__(self, logger: logging.Logger, **kwargs):
        self.logger = logger
        self.extra = kwargs
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.extra.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)
