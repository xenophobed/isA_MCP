#!/usr/bin/env python3
"""
Error handling utilities for data analytics service
"""

class DataAnalyticsError(Exception):
    """Base exception for data analytics operations"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or "ANALYTICS_ERROR"
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert error to dictionary"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }

class DatabaseConnectionError(DataAnalyticsError):
    """Error connecting to database"""
    
    def __init__(self, message: str, database_type: str = None, host: str = None):
        self.database_type = database_type
        self.host = host
        details = {}
        if database_type:
            details["database_type"] = database_type
        if host:
            details["host"] = host
        super().__init__(message, "DB_CONNECTION_ERROR", details)

class MetadataExtractionError(DataAnalyticsError):
    """Error during metadata extraction"""
    
    def __init__(self, message: str, source_type: str = None, source_name: str = None):
        self.source_type = source_type
        self.source_name = source_name
        details = {}
        if source_type:
            details["source_type"] = source_type
        if source_name:
            details["source_name"] = source_name
        super().__init__(message, "METADATA_EXTRACTION_ERROR", details)

class FileProcessingError(DataAnalyticsError):
    """Error processing files"""
    
    def __init__(self, message: str, file_path: str = None, file_type: str = None):
        self.file_path = file_path
        self.file_type = file_type
        details = {}
        if file_path:
            details["file_path"] = file_path
        if file_type:
            details["file_type"] = file_type
        super().__init__(message, "FILE_PROCESSING_ERROR", details)

class ConfigurationError(DataAnalyticsError):
    """Error in configuration"""
    
    def __init__(self, message: str, config_field: str = None):
        self.config_field = config_field
        details = {}
        if config_field:
            details["config_field"] = config_field
        super().__init__(message, "CONFIGURATION_ERROR", details)

class ValidationError(DataAnalyticsError):
    """Data validation error"""
    
    def __init__(self, message: str, validation_type: str = None, field_name: str = None):
        self.validation_type = validation_type
        self.field_name = field_name
        details = {}
        if validation_type:
            details["validation_type"] = validation_type
        if field_name:
            details["field_name"] = field_name
        super().__init__(message, "VALIDATION_ERROR", details)

def handle_error(error: Exception) -> dict:
    """
    Handle and format errors for consistent response
    
    Args:
        error: Exception to handle
    
    Returns:
        Formatted error dictionary
    """
    if isinstance(error, DataAnalyticsError):
        return error.to_dict()
    else:
        return {
            "error_type": "UnexpectedError",
            "error_code": "UNEXPECTED_ERROR",
            "message": str(error),
            "details": {"exception_type": type(error).__name__}
        }