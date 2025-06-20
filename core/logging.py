#!/usr/bin/env python
"""
Centralized Logging Configuration for MCP Server
Provides structured logging with proper formatting and handlers
"""
import logging
import logging.handlers
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = getattr(record, 'user_id')
        if hasattr(record, 'tool_name'):
            log_entry["tool_name"] = getattr(record, 'tool_name')
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = getattr(record, 'request_id')
        if hasattr(record, 'execution_time'):
            log_entry["execution_time"] = getattr(record, 'execution_time')
            
        return json.dumps(log_entry)

class MCPLogger:
    """Enhanced logger for MCP operations with context"""
    
    def __init__(self, name: str, logger: logging.Logger):
        self.name = name
        self.logger = logger
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs) -> 'MCPLogger':
        """Set context that will be included in all log messages"""
        self.context.update(kwargs)
        return self
    
    def clear_context(self) -> 'MCPLogger':
        """Clear the current context"""
        self.context.clear()
        return self
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with context"""
        # Merge context with kwargs
        extra = {**self.context, **kwargs}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def tool_execution(self, tool_name: str, user_id: str, success: bool, 
                      execution_time: float, **kwargs):
        """Log tool execution with standard fields"""
        self.info(
            f"Tool execution: {tool_name}",
            tool_name=tool_name,
            user_id=user_id,
            success=success,
            execution_time=execution_time,
            **kwargs
        )
    
    def security_event(self, event_type: str, user_id: str, details: Dict[str, Any]):
        """Log security events"""
        self.warning(
            f"Security event: {event_type}",
            event_type=event_type,
            user_id=user_id,
            security_details=details
        )
    
    def authorization_event(self, tool_name: str, user_id: str, status: str, 
                           request_id: Optional[str] = None):
        """Log authorization events"""
        self.info(
            f"Authorization {status}: {tool_name}",
            tool_name=tool_name,
            user_id=user_id,
            authorization_status=status,
            request_id=request_id
        )

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_structured: bool = False,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Setup centralized logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        enable_console: Whether to enable console logging
        enable_structured: Whether to use structured JSON logging
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatters
    if enable_structured:
        console_formatter = StructuredFormatter()
        file_formatter = StructuredFormatter()
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

def get_logger(name: str) -> MCPLogger:
    """
    Get an enhanced MCP logger instance
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        MCPLogger instance with enhanced functionality
    """
    logger = logging.getLogger(name)
    return MCPLogger(name, logger)

# Default setup for MCP server
def setup_mcp_logging():
    """Setup default logging configuration for MCP server"""
    setup_logging(
        log_level="INFO",
        log_file="mcp_server.log",
        enable_console=True,
        enable_structured=False
    )

# Global logger instances
logger = get_logger(__name__)
security_logger = get_logger("mcp.security")
monitoring_logger = get_logger("mcp.monitoring")
tool_logger = get_logger("mcp.tools")
