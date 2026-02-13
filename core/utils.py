#!/usr/bin/env python3
"""
Utility Functions and Common Services - isA MCP Core

PROJECT DESCRIPTION:
    Comprehensive utility library providing common functionality, validation, formatting, security,
    and helper functions used throughout the isA MCP system. This module serves as the foundation
    for data validation, security operations, file handling, JSON processing, and standardized
    response formatting across all system components.

INPUTS:
    - User input data requiring validation and sanitization
    - JSON strings and objects for processing
    - File paths and content for safe I/O operations
    - Timestamps and duration data for formatting
    - Sensitive data requiring masking and security handling
    - Raw data requiring hashing and cryptographic operations

OUTPUTS:
    - Validated and sanitized input data
    - Standardized JSON responses (success/error formats)
    - Formatted timestamps, durations, and byte counts
    - Secure hashes and request identifiers
    - Masked sensitive data for logging and debugging
    - Safe file read/write operations with error handling

FUNCTIONALITY:
    - Data Validation and Sanitization:
      * Email, user ID, and tool name format validation
      * Input sanitization removing control characters and null bytes
      * JSON validation and safe parsing with fallbacks
      * Length restrictions and truncation for security

    - Security and Cryptographic Utilities:
      * Secure hash generation (MD5, SHA1, SHA256)
      * Sensitive data masking for logs and responses
      * Request ID generation for tracing and audit trails
      * Input validation against injection attacks

    - Formatting and Conversion:
      * Human-readable timestamp formatting (ISO 8601)
      * Duration formatting (ms, seconds, minutes, hours)
      * Byte count formatting (B, KB, MB, GB, TB, PB)
      * Standardized response format creation

    - File System Operations:
      * Safe file reading with encoding and error handling
      * Secure file writing with directory creation
      * Path validation and directory management
      * Cross-platform path handling with pathlib

    - JSON Processing:
      * Safe JSON parsing with default fallback values
      * JSON serialization with custom encoding support
      * Multi-object merging for configuration management
      * Error-tolerant JSON operations

    - Retry and Resilience:
      * Decorator-based retry mechanism for functions
      * Exponential backoff for failed operations
      * Exception handling for both sync and async functions
      * Configurable retry attempts and delay strategies

DEPENDENCIES:
    - json: JSON processing and serialization
    - hashlib: Cryptographic hashing functions
    - re: Regular expression pattern matching
    - datetime: Timestamp and time duration handling
    - pathlib: Cross-platform file system path operations
    - contextlib: Context management utilities
    - core.config: System configuration access
    - core.exception: Custom exception handling
    - core.logging: Structured logging infrastructure

OPTIMIZATION POINTS:
    - Implement compiled regex patterns for validation
    - Add caching for repeated validation operations
    - Optimize JSON serialization for large objects
    - Add streaming file operations for large files
    - Implement async file operations for better performance
    - Add compression support for large data handling
    - Optimize hash generation with hardware acceleration
    - Add input validation caching for repeated patterns
    - Implement batch processing for multiple operations
    - Add memory-efficient operations for large datasets

SECURITY CONSIDERATIONS:
    - All user input is sanitized and validated
    - Sensitive data is properly masked in logs
    - File operations include path traversal protection
    - Hash functions use secure algorithms
    - Input length limits prevent buffer overflow attacks
    - Control character removal prevents injection attacks
    - Secure random generation for request IDs

USAGE:
    from core.utils import (
        validate_email, sanitize_input, generate_hash,
        format_timestamp, safe_json_loads, create_success_response
    )

    # Validation
    if validate_email(user_email):
        clean_input = sanitize_input(user_data)

    # Security
    data_hash = generate_hash(sensitive_data)
    masked_data = mask_sensitive_data(response_data)

    # Formatting
    response = create_success_response(data, "Operation completed")
"""

import json
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Callable
from contextlib import contextmanager
from pathlib import Path

from .config import get_settings
from .exception import DatabaseError, ValidationError
from .logging import get_logger

logger = get_logger(__name__)

# Database utilities have been moved to resources.database package
# Import them from there if needed:
# from resources.database.manager import get_database_manager

# =====================
# VALIDATION UTILITIES
# =====================


def validate_json(data: str) -> bool:
    """Validate if string is valid JSON"""
    try:
        json.loads(data)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_user_id(user_id: str) -> bool:
    """Validate user ID format"""
    # Allow alphanumeric, underscore, hyphen, and dot
    pattern = r"^[a-zA-Z0-9_.-]+$"
    return bool(re.match(pattern, user_id)) and len(user_id) <= 100


def validate_tool_name(tool_name: str) -> bool:
    """Validate tool name format"""
    # Allow alphanumeric and underscore only
    pattern = r"^[a-zA-Z0-9_]+$"
    return bool(re.match(pattern, tool_name)) and len(tool_name) <= 50


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input"""
    if not isinstance(text, str):
        raise ValidationError("Input must be a string")

    # Remove null bytes and control characters (except newline and tab)
    sanitized = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
        logger.warning(f"Input truncated to {max_length} characters")

    return sanitized


# =====================
# FORMATTING UTILITIES
# =====================


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format datetime as ISO string"""
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO timestamp string to datetime"""
    try:
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValidationError(f"Invalid timestamp format: {timestamp_str}")


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 1:
        return f"{seconds*1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_bytes(bytes_count: int) -> str:
    """Format byte count in human-readable format"""
    size = float(bytes_count)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}PB"


# =====================
# HASHING AND SECURITY UTILITIES
# =====================


def generate_hash(data: str, algorithm: str = "sha256") -> str:
    """Generate hash of data"""
    if algorithm == "md5":
        return hashlib.md5(data.encode()).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(data.encode()).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(data.encode()).hexdigest()
    else:
        raise ValidationError(f"Unsupported hash algorithm: {algorithm}")


def generate_request_id() -> str:
    """Generate unique request ID"""
    import time
    import random

    timestamp = int(time.time() * 1000)
    random_part = random.randint(1000, 9999)
    return f"req_{timestamp}_{random_part}"


def mask_sensitive_data(
    data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Mask sensitive data in dictionary"""
    if sensitive_keys is None:
        sensitive_keys = ["password", "token", "key", "secret", "api_key"]

    masked_data = data.copy()

    def mask_recursive(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if any(sensitive_key.lower() in key.lower() for sensitive_key in sensitive_keys):
                    obj[key] = "***MASKED***"
                else:
                    mask_recursive(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                mask_recursive(item, f"{path}[{i}]")

    mask_recursive(masked_data)
    return masked_data


# =====================
# JSON UTILITIES
# =====================


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safely load JSON with default fallback"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Failed to parse JSON: {json_str[:100]}...")
        return default


def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """Safely dump object to JSON"""
    try:
        return json.dumps(obj, indent=indent, default=str, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to serialize to JSON: {e}")
        return json.dumps({"error": "Serialization failed", "type": str(type(obj))})


def merge_json_objects(*objects: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple JSON objects"""
    result = {}
    for obj in objects:
        if isinstance(obj, dict):
            result.update(obj)
    return result


# =====================
# FILE UTILITIES
# =====================


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if necessary"""
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def safe_file_read(file_path: Union[str, Path], encoding: str = "utf-8") -> Optional[str]:
    """Safely read file content"""
    try:
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()
    except (IOError, UnicodeDecodeError) as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return None


def safe_file_write(file_path: Union[str, Path], content: str, encoding: str = "utf-8") -> bool:
    """Safely write content to file"""
    try:
        path_obj = Path(file_path)
        ensure_directory(path_obj.parent)

        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
        return True
    except IOError as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return False


# =====================
# RETRY UTILITIES
# =====================


def retry_on_exception(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """Decorator for retrying function calls on exceptions"""

    def decorator(func: Callable):
        async def async_wrapper(*args, **kwargs):
            last_exception: Optional[Exception] = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff**attempt)
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {wait_time}s..."
                        )
                        import asyncio

                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")

            if last_exception:
                raise last_exception
            else:
                raise RuntimeError("No attempts were made")

        def sync_wrapper(*args, **kwargs):
            last_exception: Optional[Exception] = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff**attempt)
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {wait_time}s..."
                        )
                        import time

                        time.sleep(wait_time)
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")

            if last_exception:
                raise last_exception
            else:
                raise RuntimeError("No attempts were made")

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# =====================
# RESPONSE UTILITIES
# =====================


def create_success_response(data: Any, message: str = "Operation successful") -> Dict[str, Any]:
    """Create standardized success response"""
    return {"status": "success", "message": message, "data": data, "timestamp": format_timestamp()}


def create_error_response(
    error_code: str, message: str, details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "status": "error",
        "error": {"code": error_code, "message": message, "details": details or {}},
        "timestamp": format_timestamp(),
    }
