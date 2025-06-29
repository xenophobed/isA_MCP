#!/usr/bin/env python3
"""
Unit tests for data validator
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parents[5]
sys.path.insert(0, str(project_root))

from tools.services.data_analytics_service.utils.data_validator import DataValidator

class TestDataValidator(unittest.TestCase):
    """Test cases for data validator"""
    
    def setUp(self):
        """Set up each test"""
        self.validator = DataValidator()
    
    def test_validate_database_config(self):
        """Test database configuration validation"""
        # Test valid PostgreSQL config
        valid_config = {
            "type": "postgresql",
            "host": "localhost",
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass",
            "port": 5432
        }
        
        is_valid, errors = self.validator.validate_database_config(valid_config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Test missing required fields
        invalid_config = {
            "type": "postgresql",
            "host": "localhost"
            # Missing database, username, password
        }
        
        is_valid, errors = self.validator.validate_database_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        
        # Verify specific missing fields are reported
        error_text = " ".join(errors)
        self.assertIn("database", error_text)
        self.assertIn("username", error_text)
        self.assertIn("password", error_text)
        
        # Test unsupported database type
        unsupported_config = {
            "type": "unsupported_db",
            "host": "localhost",
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass"
        }
        
        is_valid, errors = self.validator.validate_database_config(unsupported_config)
        self.assertFalse(is_valid)
        self.assertIn("Unsupported database type", " ".join(errors))
        
        # Test invalid port
        invalid_port_config = {
            "type": "postgresql",
            "host": "localhost",
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass",
            "port": 99999  # Invalid port
        }
        
        is_valid, errors = self.validator.validate_database_config(invalid_port_config)
        self.assertFalse(is_valid)
        self.assertIn("Port must be", " ".join(errors))
    
    def test_validate_file_config(self):
        """Test file configuration validation"""
        # Create a temporary file for testing
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp_file:
            test_file_path = tmp_file.name
            tmp_file.write(b"test,data\n1,2\n")
        
        try:
            # Test valid file config
            valid_config = {
                "file_path": test_file_path
            }
            
            is_valid, errors = self.validator.validate_file_config(valid_config)
            self.assertTrue(is_valid)
            self.assertEqual(len(errors), 0)
            
            # Test missing file path
            invalid_config = {}
            
            is_valid, errors = self.validator.validate_file_config(invalid_config)
            self.assertFalse(is_valid)
            self.assertIn("Missing required field: file_path", " ".join(errors))
            
            # Test non-existent file
            nonexistent_config = {
                "file_path": "/nonexistent/file.csv"
            }
            
            is_valid, errors = self.validator.validate_file_config(nonexistent_config)
            self.assertFalse(is_valid)
            self.assertIn("File does not exist", " ".join(errors))
            
            # Test unsupported file type
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as txt_file:
                unsupported_file_path = txt_file.name
            
            try:
                unsupported_config = {
                    "file_path": unsupported_file_path
                }
                
                is_valid, errors = self.validator.validate_file_config(unsupported_config)
                self.assertFalse(is_valid)
                self.assertIn("Unsupported file type", " ".join(errors))
            finally:
                Path(unsupported_file_path).unlink(missing_ok=True)
        
        finally:
            # Clean up
            Path(test_file_path).unlink(missing_ok=True)
    
    def test_validate_metadata_structure(self):
        """Test metadata structure validation"""
        # Test valid metadata
        valid_metadata = {
            "source_info": {
                "type": "database",
                "total_tables": 2,
                "total_columns": 5
            },
            "tables": [
                {
                    "table_name": "test_table",
                    "schema_name": "public",
                    "table_type": "BASE TABLE",
                    "record_count": 100
                }
            ],
            "columns": [
                {
                    "table_name": "test_table",
                    "column_name": "id",
                    "data_type": "integer",
                    "is_nullable": False,
                    "ordinal_position": 1
                }
            ],
            "relationships": [],
            "indexes": []
        }
        
        is_valid, errors = self.validator.validate_metadata_structure(valid_metadata)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Test missing required keys
        invalid_metadata = {
            "source_info": {"type": "database"},
            # Missing tables and columns
        }
        
        is_valid, errors = self.validator.validate_metadata_structure(invalid_metadata)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        
        error_text = " ".join(errors)
        self.assertIn("tables", error_text)
        self.assertIn("columns", error_text)
        
        # Test invalid source_info
        invalid_source_metadata = {
            "source_info": "invalid_type",  # Should be dict
            "tables": [],
            "columns": []
        }
        
        is_valid, errors = self.validator.validate_metadata_structure(invalid_source_metadata)
        self.assertFalse(is_valid)
        self.assertIn("source_info must be a dictionary", " ".join(errors))
        
        # Test invalid table structure
        invalid_table_metadata = {
            "source_info": {"type": "database"},
            "tables": [
                {
                    "table_name": "test",
                    # Missing required fields
                }
            ],
            "columns": []
        }
        
        is_valid, errors = self.validator.validate_metadata_structure(invalid_table_metadata)
        self.assertFalse(is_valid)
        error_text = " ".join(errors)
        self.assertIn("schema_name", error_text)
        self.assertIn("table_type", error_text)
    
    def test_validate_data_types(self):
        """Test data type validation"""
        # Test string validation
        string_values = ["hello", "world", "test"]
        is_valid, errors = self.validator.validate_data_types(string_values, "string")
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Test integer validation
        integer_values = [1, 2, 3, 42]
        is_valid, errors = self.validator.validate_data_types(integer_values, "integer")
        self.assertTrue(is_valid)
        
        # Test mixed types (should fail)
        mixed_values = [1, "string", 3.14]
        is_valid, errors = self.validator.validate_data_types(mixed_values, "integer")
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        
        # Test email validation
        valid_emails = ["test@example.com", "user@domain.org"]
        is_valid, errors = self.validator.validate_data_types(valid_emails, "email")
        self.assertTrue(is_valid)
        
        invalid_emails = ["invalid-email", "no-at-symbol.com", "user@"]
        is_valid, errors = self.validator.validate_data_types(invalid_emails, "email")
        self.assertFalse(is_valid)
        
        # Test numeric strings
        numeric_strings = ["123", "45.67", "-89.1"]
        is_valid, errors = self.validator.validate_data_types(numeric_strings, "numeric")
        self.assertTrue(is_valid)
        
        # Test with null values (should be skipped)
        values_with_nulls = [1, None, 3, None]
        is_valid, errors = self.validator.validate_data_types(values_with_nulls, "integer")
        self.assertTrue(is_valid)  # Nulls are skipped
    
    def test_validate_data_quality(self):
        """Test data quality validation"""
        # Test with good quality data
        good_data = [
            {"id": 1, "name": "John", "email": "john@example.com", "age": 30},
            {"id": 2, "name": "Jane", "email": "jane@example.com", "age": 25},
            {"id": 3, "name": "Bob", "email": "bob@example.com", "age": 35}
        ]
        
        quality_report = self.validator.validate_data_quality(good_data)
        
        self.assertIsInstance(quality_report, dict)
        self.assertIn("total_records", quality_report)
        self.assertIn("total_columns", quality_report)
        self.assertIn("quality_score", quality_report)
        self.assertIn("column_statistics", quality_report)
        self.assertIn("issues", quality_report)
        
        self.assertEqual(quality_report["total_records"], 3)
        self.assertEqual(quality_report["total_columns"], 4)
        self.assertGreater(quality_report["quality_score"], 0.8)  # Should be high quality
        
        # Test with poor quality data
        poor_data = [
            {"id": 1, "name": "John", "email": "", "age": None},
            {"id": None, "name": "", "email": "jane@example.com", "age": 25},
            {"id": 3, "name": None, "email": None, "age": None}
        ]
        
        poor_quality_report = self.validator.validate_data_quality(poor_data)
        
        self.assertLess(poor_quality_report["quality_score"], 0.7)  # Should be lower quality
        self.assertGreater(len(poor_quality_report["issues"]), 0)  # Should have issues
        
        # Test with empty data
        empty_quality_report = self.validator.validate_data_quality([])
        self.assertEqual(empty_quality_report["total_records"], 0)
        self.assertEqual(empty_quality_report["quality_score"], 0)
    
    def test_check_data_consistency(self):
        """Test data consistency checking"""
        # Test consistent metadata
        consistent_metadata = {
            "tables": [
                {"table_name": "users"},
                {"table_name": "orders"}
            ],
            "columns": [
                {"table_name": "users", "column_name": "id"},
                {"table_name": "users", "column_name": "name"},
                {"table_name": "orders", "column_name": "id"},
                {"table_name": "orders", "column_name": "user_id"}
            ]
        }
        
        consistency_report = self.validator.check_data_consistency(consistent_metadata)
        
        self.assertIsInstance(consistency_report, dict)
        self.assertIn("consistent", consistency_report)
        self.assertIn("issues", consistency_report)
        self.assertIn("warnings", consistency_report)
        
        self.assertTrue(consistency_report["consistent"])
        self.assertEqual(len(consistency_report["issues"]), 0)
        
        # Test inconsistent metadata (columns reference non-existent table)
        inconsistent_metadata = {
            "tables": [
                {"table_name": "users"}
            ],
            "columns": [
                {"table_name": "users", "column_name": "id"},
                {"table_name": "orders", "column_name": "id"}  # orders table doesn't exist
            ]
        }
        
        inconsistent_report = self.validator.check_data_consistency(inconsistent_metadata)
        
        self.assertFalse(inconsistent_report["consistent"])
        self.assertGreater(len(inconsistent_report["issues"]), 0)
        self.assertIn("orders", " ".join(inconsistent_report["issues"]))
        
        # Test duplicate table names
        duplicate_metadata = {
            "tables": [
                {"table_name": "users"},
                {"table_name": "users"}  # Duplicate
            ],
            "columns": []
        }
        
        duplicate_report = self.validator.check_data_consistency(duplicate_metadata)
        
        self.assertFalse(duplicate_report["consistent"])
        self.assertIn("Duplicate table name", " ".join(duplicate_report["issues"]))
    
    def test_email_pattern_validation(self):
        """Test email pattern validation"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@example.co.uk",
            "123@numbers.com"
        ]
        
        for email in valid_emails:
            self.assertTrue(self.validator.patterns['email'].match(email), f"Valid email {email} should match")
        
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@@domain.com",
            "user@domain",
            ""
        ]
        
        for email in invalid_emails:
            self.assertFalse(self.validator.patterns['email'].match(email), f"Invalid email {email} should not match")
    
    def test_phone_pattern_validation(self):
        """Test phone pattern validation"""
        valid_phones = [
            "1234567890",
            "+1234567890",
            "91234567890"
        ]
        
        for phone in valid_phones:
            self.assertTrue(self.validator.patterns['phone'].match(phone), f"Valid phone {phone} should match")
        
        invalid_phones = [
            "123",  # Too short
            "abc123",  # Contains letters
            "+",  # Just plus
            ""
        ]
        
        for phone in invalid_phones:
            self.assertFalse(self.validator.patterns['phone'].match(phone), f"Invalid phone {phone} should not match")
    
    def test_hostname_validation(self):
        """Test hostname validation"""
        valid_hostnames = [
            "localhost",
            "example.com",
            "subdomain.example.com",
            "192.168.1.1",
            "test-server.local"
        ]
        
        for hostname in valid_hostnames:
            self.assertTrue(self.validator._is_valid_hostname(hostname), f"Valid hostname {hostname} should be valid")
        
        invalid_hostnames = [
            "",
            "a" * 256,  # Too long
            "invalid..hostname",  # Double dots
            "-invalid.com",  # Starts with dash
            "invalid-.com"  # Ends with dash
        ]
        
        for hostname in invalid_hostnames:
            self.assertFalse(self.validator._is_valid_hostname(hostname), f"Invalid hostname {hostname} should be invalid")
    
    def test_date_pattern_validation(self):
        """Test date pattern validation"""
        valid_dates = [
            "2023-12-25",
            "2000-01-01",
            "1999-12-31"
        ]
        
        for date in valid_dates:
            self.assertTrue(self.validator.patterns['date_iso'].match(date), f"Valid date {date} should match")
        
        invalid_dates = [
            "2023/12/25",  # Wrong format
            "25-12-2023",  # Wrong order
            "2023-13-01",  # Invalid month (but pattern doesn't check semantics)
            "not-a-date"
        ]
        
        for date in invalid_dates:
            self.assertFalse(self.validator.patterns['date_iso'].match(date), f"Invalid date {date} should not match")

if __name__ == '__main__':
    unittest.main()