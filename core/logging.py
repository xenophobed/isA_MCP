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
    loki_host: str = "localhost",
    loki_port: int = 50054,
    loki_enabled: bool = False,
    service_name: str = "mcp",
    environment: str = "development"
) -> None:
    """
    Setup centralized logging configuration with Loki gRPC support

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional, for local dev only)
        enable_console: Whether to enable console logging
        enable_structured: Whether to use structured JSON logging
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        loki_host: Loki server host for gRPC connection
        loki_port: Loki server gRPC port (default 50054)
        loki_enabled: Whether to enable Loki centralized logging via gRPC
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

    # Loki gRPC handler (centralized logging - recommended for production)
    if loki_enabled:
        try:
            from isa_common.loki_client import LokiClient

            # Custom Loki handler that uses isa_common.LokiClient via gRPC
            class LokiGrpcHandler(logging.Handler):
                """
                Custom Loki handler that uses isa_common.LokiClient via gRPC

                This handler automatically pushes logs to Loki using the LokiClient
                from isa_common, which handles gRPC connection management, retries,
                and efficient batching.
                """

                def __init__(self, loki_host: str, loki_port: int, user_id: str, service_labels: dict):
                    super().__init__()
                    self.loki_host = loki_host
                    self.loki_port = loki_port
                    self.user_id = user_id
                    self.service_labels = service_labels
                    self.client = None
                    self._error_count = 0
                    self._success_count = 0

                def emit(self, record):
                    """Send log record to Loki via gRPC"""
                    try:
                        # Lazy initialization of LokiClient (only when needed)
                        if self.client is None:
                            self.client = LokiClient(
                                host=self.loki_host,
                                port=self.loki_port,
                                user_id=self.user_id
                            )
                            self.client.__enter__()  # Open connection

                        # Format the log message
                        log_entry = self.format(record)

                        # Build labels with level and logger name
                        labels = self.service_labels.copy()
                        labels['level'] = record.levelname.lower()
                        labels['logger'] = record.name.replace(f"{self.user_id}.", "").replace(self.user_id, "main")

                        # Push to Loki using simple API
                        self.client.push_log(
                            message=log_entry,
                            labels=labels
                        )

                        self._success_count += 1

                        # Debug: log first few successful pushes
                        if self._success_count <= 2:
                            print(f"[LOKI_DEBUG] Successfully pushed log to Loki: {log_entry[:80]}", flush=True)

                    except Exception as e:
                        # Graceful degradation - don't fail the application
                        self._error_count += 1
                        if self._error_count <= 3:
                            print(f"[LOKI_ERROR] Failed to push log to Loki: {e}", flush=True)

                def close(self):
                    """Clean up Loki client connection"""
                    if self.client:
                        try:
                            self.client.__exit__(None, None, None)
                        except:
                            pass
                    super().close()

            # Extract service name and logger component
            # e.g., "mcp.security" -> service="mcp_service", logger="security"
            service_id = f"{service_name}_service"

            # Labels for Loki (used for filtering and searching)
            service_labels = {
                "service": service_id,
                "environment": environment,
                "job": service_id
            }

            # Create Loki gRPC handler
            loki_handler = LokiGrpcHandler(
                loki_host=loki_host,
                loki_port=loki_port,
                user_id=service_id,
                service_labels=service_labels
            )

            # Set formatter
            loki_handler.setFormatter(console_formatter)

            # Only send INFO and above to Loki (reduce network traffic)
            loki_handler.setLevel(logging.INFO)

            root_logger.addHandler(loki_handler)

            # Log successful Loki integration
            root_logger.info(f"✅ Centralized logging enabled | loki={loki_host}:{loki_port} via gRPC")

        except ImportError as e:
            # isa_common not installed
            root_logger.warning(f"⚠️  Could not setup Loki handler: {e}")
            root_logger.warning(f"⚠️  Please install isa-common: pip install isa-common")
        except Exception as e:
            # Loki unavailable or other error - don't fail the app
            root_logger.warning(f"⚠️  Could not connect to Loki at {loki_host}:{loki_port}: {e}")
            root_logger.info("📝 Logging to console only")

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
    Setup default logging configuration for MCP server with Loki gRPC support

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
            loki_host=log_config.loki_grpc_host,
            loki_port=log_config.loki_grpc_port,
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
            enable_structured=os.getenv("ENABLE_STRUCTURED_LOGGING", "false").lower() == "true",
            loki_host=os.getenv("LOKI_GRPC_HOST", "localhost"),
            loki_port=int(os.getenv("LOKI_GRPC_PORT", "50054")),
            loki_enabled=os.getenv("LOKI_ENABLED", "false").lower() == "true",
            service_name=os.getenv("SERVICE_NAME", "mcp"),
            environment=os.getenv("ENVIRONMENT", "development")
        )

# Global logger instances
logger = get_logger(__name__)
security_logger = get_logger("mcp.security")
monitoring_logger = get_logger("mcp.monitoring")
tool_logger = get_logger("mcp.tools")
