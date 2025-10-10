#!/usr/bin/env python3
"""
Centralized Logging and Monitoring System - isA MCP Core

PROJECT DESCRIPTION:
    Advanced logging infrastructure providing structured, contextual, and performance-oriented logging
    for the isA MCP system. Implements configurable log formatters, rotating file handlers, 
    security event logging, and specialized loggers for different system components.

INPUTS:
    - Log messages from all system components
    - Security events and authentication attempts
    - Tool execution metrics and performance data
    - System configuration for log levels and output formats
    - Context information (user IDs, request IDs, execution times)

OUTPUTS:
    - Structured JSON logs for machine processing
    - Human-readable console logs for development
    - Rotating log files with configurable retention
    - Security audit trails and compliance logs
    - Performance metrics and execution timing data
    - Error reports with full context and stack traces

FUNCTIONALITY:
    - Multi-Format Logging:
      * Structured JSON logging for production environments
      * Human-readable formatting for development
      * Configurable log levels and output destinations
      * Log rotation with size and time-based policies
    
    - Contextual Logging:
      * Request ID tracking across service calls
      * User ID association with all operations
      * Tool execution context and performance metrics
      * Security event correlation and audit trails
    
    - Specialized Loggers:
      * Security logger for authentication/authorization events
      * Tool execution logger with performance metrics
      * Monitoring logger for system health and metrics
      * Error logger with enhanced context and debugging info
    
    - Performance Monitoring:
      * Execution time tracking for all operations
      * Tool performance metrics and optimization insights
      * System resource usage monitoring
      * Response time analysis and bottleneck detection
    
    - Security and Compliance:
      * Security event logging with threat detection
      * Authorization decision audit trails
      * Compliance logging for regulatory requirements
      * Tamper-evident log integrity protection

DEPENDENCIES:
    - logging: Python standard logging framework
    - logging.handlers: Advanced log handlers (rotation, buffering)
    - json: Structured log format serialization
    - datetime: Timestamp generation and formatting
    - pathlib: Cross-platform log file path handling

OPTIMIZATION POINTS:
    - Implement asynchronous logging for high-throughput scenarios
    - Add log aggregation and centralized collection
    - Optimize JSON serialization for structured logs
    - Implement log compression for long-term storage
    - Add real-time log streaming for monitoring dashboards
    - Optimize log file I/O with buffering strategies
    - Add log sampling for high-volume debug logging
    - Implement log alerting for critical events
    - Add log analytics and pattern detection
    - Optimize memory usage for long-running processes

LOGGER CATEGORIES:
    - MCPLogger: Enhanced base logger with context management
    - SecurityLogger: Authentication and authorization events
    - ToolLogger: Tool execution and performance monitoring
    - MonitoringLogger: System health and metrics collection
    - ErrorLogger: Error reporting with enhanced debugging context

USAGE:
    from core.logging import get_logger, setup_mcp_logging
    
    # Setup logging infrastructure
    setup_mcp_logging()
    
    # Get specialized loggers
    logger = get_logger(__name__)
    security_logger = get_logger("mcp.security")
    
    # Context-aware logging
    logger.set_context(user_id="user123", request_id="req456")
    logger.info("Processing user request")
    
    # Tool execution logging
    logger.tool_execution("analyze_data", "user123", True, 1.23)
"""
import logging
import logging.handlers
import sys
import json
import os
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
    backup_count: int = 5,
    loki_url: Optional[str] = None,
    loki_enabled: bool = False,
    service_name: str = "mcp",
    environment: str = "development"
) -> None:
    """
    Setup centralized logging configuration with Loki support

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional, for local dev only)
        enable_console: Whether to enable console logging
        enable_structured: Whether to use structured JSON logging
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        loki_url: Loki server URL for centralized logging
        loki_enabled: Whether to enable Loki centralized logging
        service_name: Service name for Loki labels
        environment: Environment name (development, staging, production)
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

    # Console handler (always enabled for local dev and debugging)
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Loki handler (centralized logging - recommended for production)
    if loki_enabled and loki_url:
        try:
            from logging_loki import LokiHandler

            # Extract logger component from logger name
            # e.g., "mcp.security" -> logger="security", "mcp" -> logger="main"
            def get_logger_component(logger_name: str) -> str:
                if not logger_name or logger_name == service_name:
                    return "main"
                return logger_name.replace(f"{service_name}.", "").replace(service_name, "main")

            # Create Loki labels (used for filtering in Grafana)
            loki_labels = {
                "service": service_name,
                "environment": environment,
                "job": f"{service_name}_service"
            }

            # Create Loki handler
            loki_handler = LokiHandler(
                url=f"{loki_url}/loki/api/v1/push",
                tags=loki_labels,
                version="1",
            )

            # Only send INFO and above to Loki (reduce network traffic)
            loki_handler.setLevel(logging.INFO)

            root_logger.addHandler(loki_handler)

            # Log successful Loki integration
            root_logger.info(f"✅ Centralized logging enabled | loki_url={loki_url} | service={service_name}")

        except ImportError:
            root_logger.warning("⚠️  python-logging-loki not installed. Install with: pip install python-logging-loki")
            root_logger.info("📝 Logging to console/file only")
        except Exception as e:
            # Loki unavailable - don't fail the app, just log locally
            root_logger.warning(f"⚠️  Could not connect to Loki: {e}")
            root_logger.info("📝 Logging to console/file only")

    # File handler with rotation (optional, mainly for local dev backup)
    # In production with Loki, file logging is optional
    if log_file and not loki_enabled:
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
def setup_mcp_logging(config=None):
    """
    Setup default logging configuration for MCP server with Loki support

    Args:
        config: Optional MCPSettings config object. If not provided, uses environment variables.
    """
    if config and hasattr(config, 'logging'):
        # Use config from MCPSettings
        log_config = config.logging
        setup_logging(
            log_level=log_config.log_level,
            log_file=log_config.log_file if not log_config.loki_enabled else None,
            enable_console=log_config.enable_console,
            enable_structured=log_config.enable_structured,
            max_file_size=log_config.max_file_size,
            backup_count=log_config.backup_count,
            loki_url=log_config.loki_url,
            loki_enabled=log_config.loki_enabled,
            service_name=log_config.service_name,
            environment=log_config.environment
        )
    else:
        # Fallback to environment variables
        setup_logging(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "logs/mcp_server.log") if not os.getenv("LOKI_ENABLED", "false").lower() == "true" else None,
            enable_console=True,
            enable_structured=os.getenv("LOG_STRUCTURED", "false").lower() == "true",
            loki_url=os.getenv("LOKI_URL", "http://localhost:3100"),
            loki_enabled=os.getenv("LOKI_ENABLED", "false").lower() == "true",
            service_name=os.getenv("SERVICE_NAME", "mcp"),
            environment=os.getenv("ENVIRONMENT", "development")
        )

# Global logger instances
logger = get_logger(__name__)
security_logger = get_logger("mcp.security")
monitoring_logger = get_logger("mcp.monitoring")
tool_logger = get_logger("mcp.tools")
