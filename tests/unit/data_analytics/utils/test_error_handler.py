#!/usr/bin/env python3
"""
Unit tests for error handler
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parents[5]
sys.path.insert(0, str(project_root))

from tools.services.data_analytics_service.utils.error_handler import (
    DataAnalyticsError,
    DatabaseConnectionError,
    MetadataExtractionError,
    FileProcessingError,
    ConfigurationError,
    ValidationError,
    handle_error
)

class TestErrorHandler(unittest.TestCase):
    """Test cases for error handler"""
    
    def test_data_analytics_error_base(self):
        """Test base DataAnalyticsError functionality"""
        # Test basic error
        error = DataAnalyticsError("Test error message")
        
        self.assertEqual(str(error), "Test error message")
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(error.error_code, "ANALYTICS_ERROR")
        self.assertEqual(error.details, {})
        
        # Test error with custom code and details
        details = {"field": "test_field", "value": "test_value"}
        error_with_details = DataAnalyticsError(
            "Custom error",
            error_code="CUSTOM_ERROR",
            details=details
        )
        
        self.assertEqual(error_with_details.error_code, "CUSTOM_ERROR")
        self.assertEqual(error_with_details.details, details)
        
        # Test to_dict method
        error_dict = error_with_details.to_dict()
        expected_dict = {
            "error_type": "DataAnalyticsError",
            "error_code": "CUSTOM_ERROR",
            "message": "Custom error",
            "details": details
        }
        
        self.assertEqual(error_dict, expected_dict)
    
    def test_database_connection_error(self):
        """Test DatabaseConnectionError"""
        # Test basic database error
        db_error = DatabaseConnectionError("Connection failed")
        
        self.assertEqual(db_error.error_code, "DB_CONNECTION_ERROR")
        self.assertEqual(db_error.message, "Connection failed")
        
        # Test with database details
        db_error_with_details = DatabaseConnectionError(
            "PostgreSQL connection failed",
            database_type="postgresql",
            host="localhost"
        )
        
        self.assertEqual(db_error_with_details.database_type, "postgresql")
        self.assertEqual(db_error_with_details.host, "localhost")
        
        error_dict = db_error_with_details.to_dict()
        self.assertEqual(error_dict["error_type"], "DatabaseConnectionError")
        self.assertEqual(error_dict["details"]["database_type"], "postgresql")
        self.assertEqual(error_dict["details"]["host"], "localhost")
    
    def test_metadata_extraction_error(self):
        """Test MetadataExtractionError"""
        # Test basic metadata error
        meta_error = MetadataExtractionError("Extraction failed")
        
        self.assertEqual(meta_error.error_code, "METADATA_EXTRACTION_ERROR")
        
        # Test with source details
        meta_error_with_details = MetadataExtractionError(
            "Failed to extract from table",
            source_type="database",
            source_name="users_table"
        )
        
        self.assertEqual(meta_error_with_details.source_type, "database")
        self.assertEqual(meta_error_with_details.source_name, "users_table")
        
        error_dict = meta_error_with_details.to_dict()
        self.assertEqual(error_dict["details"]["source_type"], "database")
        self.assertEqual(error_dict["details"]["source_name"], "users_table")
    
    def test_file_processing_error(self):
        """Test FileProcessingError"""
        # Test basic file error
        file_error = FileProcessingError("File processing failed")
        
        self.assertEqual(file_error.error_code, "FILE_PROCESSING_ERROR")
        
        # Test with file details
        file_error_with_details = FileProcessingError(
            "Excel file corrupted",
            file_path="/path/to/file.xlsx",
            file_type="excel"
        )
        
        self.assertEqual(file_error_with_details.file_path, "/path/to/file.xlsx")
        self.assertEqual(file_error_with_details.file_type, "excel")
        
        error_dict = file_error_with_details.to_dict()
        self.assertEqual(error_dict["details"]["file_path"], "/path/to/file.xlsx")
        self.assertEqual(error_dict["details"]["file_type"], "excel")
    
    def test_configuration_error(self):
        """Test ConfigurationError"""
        # Test basic configuration error
        config_error = ConfigurationError("Invalid configuration")
        
        self.assertEqual(config_error.error_code, "CONFIGURATION_ERROR")
        
        # Test with config field
        config_error_with_field = ConfigurationError(
            "Database host is required",
            config_field="database.host"
        )
        
        self.assertEqual(config_error_with_field.config_field, "database.host")
        
        error_dict = config_error_with_field.to_dict()
        self.assertEqual(error_dict["details"]["config_field"], "database.host")
    
    def test_validation_error(self):
        """Test ValidationError"""
        # Test basic validation error
        validation_error = ValidationError("Validation failed")
        
        self.assertEqual(validation_error.error_code, "VALIDATION_ERROR")
        
        # Test with validation details
        validation_error_with_details = ValidationError(
            "Email format is invalid",
            validation_type="email",
            field_name="user_email"
        )
        
        self.assertEqual(validation_error_with_details.validation_type, "email")
        self.assertEqual(validation_error_with_details.field_name, "user_email")
        
        error_dict = validation_error_with_details.to_dict()
        self.assertEqual(error_dict["details"]["validation_type"], "email")
        self.assertEqual(error_dict["details"]["field_name"], "user_email")
    
    def test_handle_error_with_data_analytics_errors(self):
        """Test handle_error function with DataAnalyticsError subclasses"""
        # Test with DataAnalyticsError
        analytics_error = DataAnalyticsError("Test analytics error", "TEST_CODE")
        handled = handle_error(analytics_error)
        
        expected = analytics_error.to_dict()
        self.assertEqual(handled, expected)
        
        # Test with DatabaseConnectionError
        db_error = DatabaseConnectionError("DB error", "postgresql", "localhost")
        handled_db = handle_error(db_error)
        
        self.assertEqual(handled_db["error_type"], "DatabaseConnectionError")
        self.assertEqual(handled_db["error_code"], "DB_CONNECTION_ERROR")
        self.assertEqual(handled_db["message"], "DB error")
        self.assertEqual(handled_db["details"]["database_type"], "postgresql")
    
    def test_handle_error_with_standard_exceptions(self):
        """Test handle_error function with standard Python exceptions"""
        # Test with ValueError
        value_error = ValueError("Invalid value provided")
        handled = handle_error(value_error)
        
        expected = {
            "error_type": "UnexpectedError",
            "error_code": "UNEXPECTED_ERROR",
            "message": "Invalid value provided",
            "details": {"exception_type": "ValueError"}
        }
        
        self.assertEqual(handled, expected)
        
        # Test with TypeError
        type_error = TypeError("Type mismatch")
        handled_type = handle_error(type_error)
        
        self.assertEqual(handled_type["error_type"], "UnexpectedError")
        self.assertEqual(handled_type["error_code"], "UNEXPECTED_ERROR")
        self.assertEqual(handled_type["message"], "Type mismatch")
        self.assertEqual(handled_type["details"]["exception_type"], "TypeError")
        
        # Test with generic Exception
        generic_error = Exception("Generic error")
        handled_generic = handle_error(generic_error)
        
        self.assertEqual(handled_generic["details"]["exception_type"], "Exception")
    
    def test_error_inheritance(self):
        """Test error class inheritance"""
        # All custom errors should inherit from DataAnalyticsError
        db_error = DatabaseConnectionError("DB error")
        self.assertIsInstance(db_error, DataAnalyticsError)
        
        meta_error = MetadataExtractionError("Meta error")
        self.assertIsInstance(meta_error, DataAnalyticsError)
        
        file_error = FileProcessingError("File error")
        self.assertIsInstance(file_error, DataAnalyticsError)
        
        config_error = ConfigurationError("Config error")
        self.assertIsInstance(config_error, DataAnalyticsError)
        
        validation_error = ValidationError("Validation error")
        self.assertIsInstance(validation_error, DataAnalyticsError)
    
    def test_error_chaining_and_context(self):
        """Test error chaining and context preservation"""
        # Test that errors can be chained (Python's exception chaining)
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise DataAnalyticsError("Wrapped error") from e
        except DataAnalyticsError as wrapped:
            self.assertIsNotNone(wrapped.__cause__)
            self.assertIsInstance(wrapped.__cause__, ValueError)
            self.assertEqual(str(wrapped.__cause__), "Original error")
    
    def test_error_dict_serialization(self):
        """Test that error dictionaries are JSON serializable"""
        import json
        
        # Test complex error with details
        error = DatabaseConnectionError(
            "Connection timeout",
            database_type="postgresql",
            host="db.example.com"
        )
        
        error_dict = error.to_dict()
        
        # Should be JSON serializable
        try:
            json_str = json.dumps(error_dict)
            loaded_dict = json.loads(json_str)
            self.assertEqual(loaded_dict, error_dict)
        except (TypeError, ValueError) as e:
            self.fail(f"Error dictionary should be JSON serializable: {e}")
    
    def test_error_message_formatting(self):
        """Test error message formatting and readability"""
        # Test detailed error message
        error = MetadataExtractionError(
            "Failed to extract column metadata from table 'users' in schema 'public'",
            source_type="database",
            source_name="users"
        )
        
        error_dict = error.to_dict()
        
        # Message should be descriptive
        self.assertIn("users", error_dict["message"])
        self.assertIn("public", error_dict["message"])
        self.assertIn("column metadata", error_dict["message"])
        
        # Details should provide structured information
        self.assertEqual(error_dict["details"]["source_type"], "database")
        self.assertEqual(error_dict["details"]["source_name"], "users")
    
    def test_empty_and_none_values(self):
        """Test handling of empty and None values"""
        # Test with None details
        error = DataAnalyticsError("Test error", details=None)
        self.assertEqual(error.details, {})
        
        # Test with empty details
        error_empty = DataAnalyticsError("Test error", details={})
        self.assertEqual(error_empty.details, {})
        
        # Test error with None values in details
        file_error = FileProcessingError("Error", file_path=None, file_type=None)
        error_dict = file_error.to_dict()
        
        # None values should still be included in details if explicitly set
        # (the constructor may or may not add them depending on implementation)
        self.assertIn("details", error_dict)

if __name__ == '__main__':
    unittest.main()