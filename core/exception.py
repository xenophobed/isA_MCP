#!/usr/bin/env python
"""
Custom Exception Classes for MCP Server
Provides structured error handling with proper error codes and data
"""
from typing import Dict, Any, Optional
from enum import Enum

class ErrorCode(Enum):
    """Standard error codes for MCP operations"""
    UNKNOWN = "UNKNOWN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"

class McpError(Exception):
    """Base MCP Error class with structured error information"""
    def __init__(
        self, 
        message: str, 
        error_code: ErrorCode = ErrorCode.UNKNOWN,
        data: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.data = data or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization"""
        return {
            "error": {
                "code": self.error_code.value,
                "message": self.message,
                "data": self.data
            }
        }

class AuthorizationError(McpError):
    """Authorization related errors"""
    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorCode.AUTHORIZATION_REQUIRED, 
            data
        )

class AuthorizationDeniedError(McpError):
    """Authorization denied errors"""
    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorCode.AUTHORIZATION_DENIED, 
            data
        )

class RateLimitError(McpError):
    """Rate limiting errors"""
    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorCode.RATE_LIMIT_EXCEEDED, 
            data
        )

class SecurityViolationError(McpError):
    """Security violation errors"""
    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorCode.SECURITY_VIOLATION, 
            data
        )

class ValidationError(McpError):
    """Input validation errors"""
    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorCode.VALIDATION_ERROR, 
            data
        )

class DatabaseError(McpError):
    """Database operation errors"""
    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorCode.DATABASE_ERROR, 
            data
        )

class ResourceNotFoundError(McpError):
    """Resource not found errors"""
    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorCode.RESOURCE_NOT_FOUND, 
            data
        )

class ConfigurationError(McpError):
    """Configuration related errors"""
    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorCode.CONFIGURATION_ERROR, 
            data
        )

class ExternalServiceError(McpError):
    """External service errors"""
    def __init__(self, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorCode.EXTERNAL_SERVICE_ERROR, 
            data
        )
