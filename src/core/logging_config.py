import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Dict, Any
import json
from pathlib import Path

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Create structured log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

class CustomLogger:
    """Custom logger with structured logging and file rotation"""
    
    def __init__(self, name: str = "web_scraper"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            return
            
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers"""
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Console Handler (INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # File Handler - General logs (INFO and above)
        general_handler = logging.handlers.RotatingFileHandler(
            log_dir / "web_scraper.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        general_handler.setLevel(logging.INFO)
        general_formatter = StructuredFormatter()
        general_handler.setFormatter(general_formatter)
        
        # File Handler - Error logs (ERROR and above)
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "errors.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = StructuredFormatter()
        error_handler.setFormatter(error_formatter)
        
        # File Handler - Debug logs (DEBUG and above)
        debug_handler = logging.handlers.RotatingFileHandler(
            log_dir / "debug.log",
            maxBytes=20 * 1024 * 1024,  # 20MB
            backupCount=2
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_formatter = StructuredFormatter()
        debug_handler.setFormatter(debug_formatter)
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(general_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(debug_handler)
    
    def log_with_context(self, level: int, message: str, **kwargs):
        """Log with additional context"""
        extra_fields = kwargs.copy()
        record = self.logger.makeRecord(
            self.logger.name, level, "", 0, message, (), None
        )
        record.extra_fields = extra_fields
        self.logger.handle(record)
    
    def info(self, message: str, **kwargs):
        """Log info message with context"""
        self.log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        self.log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context"""
        self.log_with_context(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        self.log_with_context(logging.DEBUG, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context"""
        self.log_with_context(logging.CRITICAL, message, **kwargs)

def setup_logging(name: str = "web_scraper") -> CustomLogger:
    """Setup and return a configured logger"""
    return CustomLogger(name)

def get_logger(name: str = "web_scraper") -> CustomLogger:
    """Get a logger instance"""
    return CustomLogger(name)

# Global logger instance
logger = setup_logging()

# Logging middleware for FastAPI
class LoggingMiddleware:
    """Middleware to log all requests and responses"""
    
    def __init__(self, app):
        self.app = app
        self.logger = get_logger("http")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Log request
            start_time = datetime.utcnow()
            self.logger.info(
                f"Request started: {scope['method']} {scope['path']}",
                method=scope["method"],
                path=scope["path"],
                client_ip=scope.get("client", [None, None])[0],
                user_agent=dict(scope.get("headers", [])).get(b"user-agent", b"").decode(),
                timestamp=start_time.isoformat()
            )
            
            # Process request
            await self.app(scope, receive, send)
            
            # Log response
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            self.logger.info(
                f"Request completed: {scope['method']} {scope['path']}",
                method=scope["method"],
                path=scope["path"],
                duration=duration,
                timestamp=end_time.isoformat()
            )

# Performance logging decorator
def log_performance(func):
    """Decorator to log function performance"""
    def wrapper(*args, **kwargs):
        start_time = datetime.utcnow()
        try:
            result = func(*args, **kwargs)
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(
                f"Function {func.__name__} completed successfully",
                function=func.__name__,
                duration=duration,
                status="success"
            )
            return result
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(
                f"Function {func.__name__} failed",
                function=func.__name__,
                duration=duration,
                error=str(e),
                status="error"
            )
            raise
    
    return wrapper

# Async performance logging decorator
def log_async_performance(func):
    """Decorator to log async function performance"""
    async def wrapper(*args, **kwargs):
        start_time = datetime.utcnow()
        try:
            result = await func(*args, **kwargs)
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(
                f"Async function {func.__name__} completed successfully",
                function=func.__name__,
                duration=duration,
                status="success"
            )
            return result
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(
                f"Async function {func.__name__} failed",
                function=func.__name__,
                duration=duration,
                error=str(e),
                status="error"
            )
            raise
    
    return wrapper 