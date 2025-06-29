#!/usr/bin/env python3
"""
Unit tests for configuration manager
"""

import unittest
import tempfile
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parents[5]
sys.path.insert(0, str(project_root))

from tools.services.data_analytics_service.utils.config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    """Test cases for configuration manager"""
    
    def setUp(self):
        """Set up each test with temporary config directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(self.temp_dir)
    
    def tearDown(self):
        """Clean up temporary directory"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_default_config_creation(self):
        """Test default configuration creation"""
        config = self.config_manager.load_config("default")
        
        # Verify default config structure
        self.assertIsInstance(config, dict)
        self.assertIn("database", config)
        self.assertIn("file_processing", config)
        self.assertIn("metadata_extraction", config)
        self.assertIn("output", config)
        
        # Verify database config
        db_config = config["database"]
        self.assertIn("connection_timeout", db_config)
        self.assertIn("query_timeout", db_config)
        self.assertIn("max_sample_size", db_config)
        self.assertIn("default_sample_size", db_config)
        
        # Verify file processing config
        file_config = config["file_processing"]
        self.assertIn("max_file_size_mb", file_config)
        self.assertIn("encoding_detection", file_config)
        self.assertIn("delimiter_detection", file_config)
        
        # Verify metadata extraction config
        meta_config = config["metadata_extraction"]
        self.assertIn("include_data_analysis", meta_config)
        self.assertIn("max_tables_to_analyze", meta_config)
        self.assertIn("max_columns_per_table", meta_config)
        
        # Verify output config
        output_config = config["output"]
        self.assertIn("default_format", output_config)
        self.assertIn("pretty_print", output_config)
        self.assertIn("include_timestamps", output_config)
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration"""
        test_config = {
            "database": {
                "connection_timeout": 60,
                "max_sample_size": 5000
            },
            "file_processing": {
                "max_file_size_mb": 200
            }
        }
        
        # Save config
        success = self.config_manager.save_config(test_config, "test_config")
        self.assertTrue(success)
        
        # Load config
        loaded_config = self.config_manager.load_config("test_config")
        
        # Verify loaded config contains our settings
        self.assertEqual(loaded_config["database"]["connection_timeout"], 60)
        self.assertEqual(loaded_config["database"]["max_sample_size"], 5000)
        self.assertEqual(loaded_config["file_processing"]["max_file_size_mb"], 200)
        
        # Verify default values are still present
        self.assertIn("query_timeout", loaded_config["database"])
        self.assertIn("encoding_detection", loaded_config["file_processing"])
    
    def test_config_merging(self):
        """Test configuration merging functionality"""
        # Create partial config
        partial_config = {
            "database": {
                "connection_timeout": 45
            },
            "new_section": {
                "new_setting": "test_value"
            }
        }
        
        # Save and load
        self.config_manager.save_config(partial_config, "partial")
        merged_config = self.config_manager.load_config("partial")
        
        # Verify merging worked
        self.assertEqual(merged_config["database"]["connection_timeout"], 45)
        self.assertIn("query_timeout", merged_config["database"])  # Default preserved
        self.assertIn("new_section", merged_config)  # New section added
        self.assertEqual(merged_config["new_section"]["new_setting"], "test_value")
    
    def test_specific_config_getters(self):
        """Test specific configuration getters"""
        # Test database config getter
        db_config = self.config_manager.get_database_config()
        self.assertIsInstance(db_config, dict)
        self.assertIn("connection_timeout", db_config)
        
        # Test file processing config getter
        file_config = self.config_manager.get_file_processing_config()
        self.assertIsInstance(file_config, dict)
        self.assertIn("max_file_size_mb", file_config)
        
        # Test metadata config getter
        meta_config = self.config_manager.get_metadata_config()
        self.assertIsInstance(meta_config, dict)
        self.assertIn("include_data_analysis", meta_config)
        
        # Test output config getter
        output_config = self.config_manager.get_output_config()
        self.assertIsInstance(output_config, dict)
        self.assertIn("default_format", output_config)
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Test valid config
        valid_config = {
            "database": {
                "connection_timeout": 30,
                "max_sample_size": 1000
            },
            "file_processing": {
                "max_file_size_mb": 100
            }
        }
        
        is_valid, errors = self.config_manager.validate_config(valid_config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Test invalid config
        invalid_config = {
            "database": {
                "connection_timeout": "invalid_string",  # Should be int
                "max_sample_size": "invalid"  # Should be int
            },
            "file_processing": {
                "max_file_size_mb": "invalid"  # Should be number
            }
        }
        
        is_valid, errors = self.config_manager.validate_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        
        # Verify specific error messages
        error_text = " ".join(errors)
        self.assertIn("connection_timeout", error_text)
        self.assertIn("max_sample_size", error_text)
        self.assertIn("max_file_size_mb", error_text)
    
    def test_list_configs(self):
        """Test listing available configurations"""
        # Initially should have default config
        configs = self.config_manager.list_configs()
        self.assertIn("default", configs)
        
        # Create additional configs
        self.config_manager.save_config({"test": "value1"}, "config1")
        self.config_manager.save_config({"test": "value2"}, "config2")
        
        # Should now have all configs
        configs = self.config_manager.list_configs()
        self.assertIn("default", configs)
        self.assertIn("config1", configs)
        self.assertIn("config2", configs)
        self.assertGreaterEqual(len(configs), 3)
    
    def test_delete_config(self):
        """Test deleting configurations"""
        # Create test config
        self.config_manager.save_config({"test": "value"}, "test_delete")
        
        # Verify it exists
        configs = self.config_manager.list_configs()
        self.assertIn("test_delete", configs)
        
        # Delete it
        success = self.config_manager.delete_config("test_delete")
        self.assertTrue(success)
        
        # Verify it's gone
        configs = self.config_manager.list_configs()
        self.assertNotIn("test_delete", configs)
        
        # Test deleting non-existent config
        success = self.config_manager.delete_config("non_existent")
        self.assertFalse(success)
        
        # Test deleting default config (should be prevented)
        success = self.config_manager.delete_config("default")
        self.assertFalse(success)
    
    def test_create_database_connection_config(self):
        """Test creating database connection configuration"""
        # Test PostgreSQL config
        pg_config = self.config_manager.create_database_connection_config(
            db_type="postgresql",
            host="localhost",
            database="test_db",
            username="test_user",
            password="test_pass"
        )
        
        self.assertEqual(pg_config["type"], "postgresql")
        self.assertEqual(pg_config["host"], "localhost")
        self.assertEqual(pg_config["database"], "test_db")
        self.assertEqual(pg_config["username"], "test_user")
        self.assertEqual(pg_config["password"], "test_pass")
        self.assertEqual(pg_config["port"], 5432)  # Default PostgreSQL port
        
        # Test MySQL config with custom port
        mysql_config = self.config_manager.create_database_connection_config(
            db_type="mysql",
            host="db.example.com",
            database="my_db",
            username="user",
            password="pass",
            port=3307,
            charset="utf8mb4"
        )
        
        self.assertEqual(mysql_config["type"], "mysql")
        self.assertEqual(mysql_config["port"], 3307)
        self.assertEqual(mysql_config["charset"], "utf8mb4")
    
    def test_create_file_config(self):
        """Test creating file processing configuration"""
        # Test basic file config
        file_config = self.config_manager.create_file_config(
            file_path="/path/to/data.csv"
        )
        
        self.assertEqual(file_config["file_path"], "/path/to/data.csv")
        
        # Test file config with type and options
        excel_config = self.config_manager.create_file_config(
            file_path="/path/to/data.xlsx",
            file_type="excel",
            include_data_analysis=True,
            sheet_filter=["Sheet1", "Sheet2"]
        )
        
        self.assertEqual(excel_config["file_path"], "/path/to/data.xlsx")
        self.assertEqual(excel_config["file_type"], "excel")
        self.assertTrue(excel_config["include_data_analysis"])
        self.assertEqual(excel_config["sheet_filter"], ["Sheet1", "Sheet2"])
    
    def test_environment_config(self):
        """Test environment variable configuration"""
        # Set test environment variables
        test_env = {
            "DB_TYPE": "postgresql",
            "DB_HOST": "test.example.com",
            "DB_PORT": "5433",
            "DB_NAME": "test_env_db",
            "DB_USER": "env_user",
            "DB_PASSWORD": "env_pass",
            "MAX_FILE_SIZE_MB": "150"
        }
        
        # Set environment variables
        for key, value in test_env.items():
            os.environ[key] = value
        
        try:
            # Get environment config
            env_config = self.config_manager.get_environment_config()
            
            # Verify database config from environment
            self.assertIn("database", env_config)
            db_config = env_config["database"]
            self.assertEqual(db_config["type"], "postgresql")
            self.assertEqual(db_config["host"], "test.example.com")
            self.assertEqual(db_config["port"], 5433)
            self.assertEqual(db_config["database"], "test_env_db")
            self.assertEqual(db_config["username"], "env_user")
            self.assertEqual(db_config["password"], "env_pass")
            
            # Verify file processing config from environment
            self.assertIn("file_processing", env_config)
            file_config = env_config["file_processing"]
            self.assertEqual(file_config["max_file_size_mb"], 150.0)
            
        finally:
            # Clean up environment variables
            for key in test_env.keys():
                os.environ.pop(key, None)
    
    def test_config_file_creation(self):
        """Test configuration file creation and file system interaction"""
        # Verify config directory is created
        self.assertTrue(Path(self.temp_dir).exists())
        
        # Create config and verify file exists
        test_config = {"test": "value"}
        self.config_manager.save_config(test_config, "file_test")
        
        config_file = Path(self.temp_dir) / "file_test.json"
        self.assertTrue(config_file.exists())
        
        # Verify file contents
        with open(config_file, 'r') as f:
            loaded_data = json.load(f)
        
        # Should be merged with defaults
        self.assertIn("test", loaded_data)
        self.assertEqual(loaded_data["test"], "value")
        self.assertIn("database", loaded_data)  # Default sections should be present
    
    def test_config_error_handling(self):
        """Test configuration error handling"""
        # Test invalid JSON in config file
        invalid_json_file = Path(self.temp_dir) / "invalid.json"
        with open(invalid_json_file, 'w') as f:
            f.write("invalid json content {")
        
        # Should return default config on error
        config = self.config_manager.load_config("invalid")
        self.assertEqual(config, self.config_manager.default_config)
        
        # Test saving to invalid path (permission test might not work on all systems)
        # This test is optional and depends on file system permissions

if __name__ == '__main__':
    unittest.main()