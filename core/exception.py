#!/usr/bin/env python3
"""
Structured Exception Handling System - isA MCP Core

PROJECT DESCRIPTION:
    Comprehensive exception handling framework providing structured error management for the isA MCP system.
    Implements standardized error codes, hierarchical exception classes, and JSON-serializable error responses
    to ensure consistent error handling across all system components including authentication, authorization,
    validation, database operations, and external service integrations.

INPUTS:
    - Error conditions from system operations (auth failures, validation errors, etc.)
    - User-provided data that fails validation checks
    - Database operation failures and connection issues
    - External service communication failures
    - Security policy violations and authorization denials
    - Configuration errors and missing parameters

OUTPUTS:
    - Structured exception objects with standardized error codes
    - JSON-serializable error responses for API endpoints
    - Detailed error context and debugging information
    - Hierarchical error classification for proper handling
    - Audit-friendly error messages for security compliance
    - Actionable error information for client applications

FUNCTIONALITY:
    - Standardized Error Classification:
      * VALIDATION_ERROR: Input validation and data format errors
      * AUTHORIZATION_REQUIRED: Authentication required for access
      * AUTHORIZATION_DENIED: Insufficient permissions for operation
      * RATE_LIMIT_EXCEEDED: Request rate limiting violations
      * SECURITY_VIOLATION: Security policy breaches and threats
      * RESOURCE_NOT_FOUND: Missing resources or endpoints
      * DATABASE_ERROR: Database operation and connection failures
      * EXTERNAL_SERVICE_ERROR: Third-party service communication issues
      * CONFIGURATION_ERROR: System configuration and setup problems
    
    - Hierarchical Exception Classes:
      * McpError: Base exception class with structured error data
      * AuthorizationError: Authentication and login requirement errors
      * AuthorizationDeniedError: Permission and access denial errors
      * ValidationError: Input validation and data format errors
      * DatabaseError: Database operation and connectivity issues
      * SecurityViolationError: Security policy violations
      * ResourceNotFoundError: Missing resource and endpoint errors
      * ConfigurationError: System configuration problems
      * ExternalServiceError: External API and service failures
    
    - Error Context and Debugging:
      * Structured error data with contextual information
      * Error chaining to preserve original exception causes
      * JSON serialization for API response formatting
      * Standardized error codes for programmatic handling
      * Detailed error messages for debugging and logging

DEPENDENCIES:
    - typing: Type hints for error data structures
    - enum: Enumerated error code definitions
    - json: Error serialization for API responses (implicit)

OPTIMIZATION POINTS:
    - Add error correlation IDs for distributed system tracing
    - Implement error aggregation for batch operation failures
    - Add error severity levels for prioritized handling
    - Optimize JSON serialization for large error contexts
    - Add error translation for internationalization support
    - Implement error rate limiting to prevent log flooding
    - Add error pattern detection for automated alerts
    - Optimize error stack trace capture and formatting
    - Add error metrics collection for system monitoring
    - Implement error recovery suggestions and recommendations

USAGE PATTERNS:
    The exception system is used throughout the isA MCP codebase:
    
    1. **Authentication and Authorization** (core/auth.py, core/security.py):
       - AuthorizationError for missing authentication
       - AuthorizationDeniedError for insufficient permissions
       - SecurityViolationError for security policy breaches
    
    2. **Input Validation** (core/utils.py, tools/*, services/*):
       - ValidationError for malformed data and invalid inputs
       - Used in email validation, user ID checking, JSON parsing
    
    3. **Database Operations** (core/database/*):
       - DatabaseError for connection and query failures
       - ResourceNotFoundError for missing database records
    
    4. **Admin Operations** (tools/general_tools/admin_tools.py):
       - McpError for unauthorized administrative access
       - Used in authorization request management
    
    5. **External Services** (tools/services/*/):
       - ExternalServiceError for API communication failures
       - ConfigurationError for missing service credentials

USAGE:
    from core.exception import (
        McpError, ValidationError, AuthorizationError,
        DatabaseError, SecurityViolationError
    )
    
    # Input validation
    if not validate_email(email):
        raise ValidationError("Invalid email format", {"email": email})
    
    # Authorization checking
    if not user_has_permission(user_id, "admin"):
        raise AuthorizationError("Admin access required")
    
    # Database operations
    try:
        result = db.query(sql)
    except Exception as e:
        raise DatabaseError("Query failed", {"sql": sql}) from e
    
    # JSON API responses
    try:
        process_request(data)
    except McpError as e:
        return JSONResponse(e.to_dict(), status_code=400)
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
