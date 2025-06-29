#!/usr/bin/env python3
"""
Configuration management for data analytics service
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """Manages configuration for data analytics service"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path.home() / ".data_analytics"
        self.config_dir.mkdir(exist_ok=True)
        
        # Default configuration
        self.default_config = {
            "database": {
                "connection_timeout": 30,
                "query_timeout": 300,
                "max_sample_size": 10000,
                "default_sample_size": 1000
            },
            "file_processing": {
                "max_file_size_mb": 100,
                "encoding_detection": True,
                "delimiter_detection": True
            },
            "metadata_extraction": {
                "include_data_analysis": True,
                "max_tables_to_analyze": 50,
                "max_columns_per_table": 20
            },
            "output": {
                "default_format": "json",
                "pretty_print": True,
                "include_timestamps": True
            }
        }
    
    def load_config(self, config_name: str = "default") -> Dict[str, Any]:
        """
        Load configuration from file
        
        Args:
            config_name: Name of configuration file (without extension)
        
        Returns:
            Configuration dictionary
        """
        config_file = self.config_dir / f"{config_name}.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # Merge with default config
                merged_config = self._merge_configs(self.default_config, user_config)
                return merged_config
            except Exception as e:
                print(f"Error loading config {config_name}: {e}")
                return self.default_config.copy()
        else:
            # Create default config file
            self.save_config(self.default_config, config_name)
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any], config_name: str = "default") -> bool:
        """
        Save configuration to file
        
        Args:
            config: Configuration dictionary to save
            config_name: Name of configuration file
        
        Returns:
            Success status
        """
        try:
            config_file = self.config_dir / f"{config_name}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config {config_name}: {e}")
            return False
    
    def get_database_config(self, config_name: str = "default") -> Dict[str, Any]:
        """Get database-specific configuration"""
        config = self.load_config(config_name)
        return config.get("database", {})
    
    def get_file_processing_config(self, config_name: str = "default") -> Dict[str, Any]:
        """Get file processing configuration"""
        config = self.load_config(config_name)
        return config.get("file_processing", {})
    
    def get_metadata_config(self, config_name: str = "default") -> Dict[str, Any]:
        """Get metadata extraction configuration"""
        config = self.load_config(config_name)
        return config.get("metadata_extraction", {})
    
    def get_output_config(self, config_name: str = "default") -> Dict[str, Any]:
        """Get output configuration"""
        config = self.load_config(config_name)
        return config.get("output", {})
    
    def list_configs(self) -> list:
        """List available configuration files"""
        try:
            config_files = list(self.config_dir.glob("*.json"))
            return [f.stem for f in config_files]
        except Exception:
            return []
    
    def delete_config(self, config_name: str) -> bool:
        """
        Delete configuration file
        
        Args:
            config_name: Name of configuration to delete
        
        Returns:
            Success status
        """
        try:
            if config_name == "default":
                return False  # Don't allow deleting default config
            
            config_file = self.config_dir / f"{config_name}.json"
            if config_file.exists():
                config_file.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting config {config_name}: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, list]:
        """
        Validate configuration
        
        Args:
            config: Configuration to validate
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate database config
        if "database" in config:
            db_config = config["database"]
            if "connection_timeout" in db_config and not isinstance(db_config["connection_timeout"], int):
                errors.append("database.connection_timeout must be an integer")
            if "max_sample_size" in db_config and not isinstance(db_config["max_sample_size"], int):
                errors.append("database.max_sample_size must be an integer")
        
        # Validate file processing config
        if "file_processing" in config:
            file_config = config["file_processing"]
            if "max_file_size_mb" in file_config and not isinstance(file_config["max_file_size_mb"], (int, float)):
                errors.append("file_processing.max_file_size_mb must be a number")
        
        # Validate metadata config
        if "metadata_extraction" in config:
            meta_config = config["metadata_extraction"]
            if "max_tables_to_analyze" in meta_config and not isinstance(meta_config["max_tables_to_analyze"], int):
                errors.append("metadata_extraction.max_tables_to_analyze must be an integer")
        
        return len(errors) == 0, errors
    
    def create_database_connection_config(self, 
                                        db_type: str,
                                        host: str,
                                        database: str,
                                        username: str,
                                        password: str,
                                        port: Optional[int] = None,
                                        **kwargs) -> Dict[str, Any]:
        """
        Create database connection configuration
        
        Args:
            db_type: Database type (postgresql, mysql, sqlserver)
            host: Database host
            database: Database name
            username: Username
            password: Password
            port: Port (optional, uses default for db_type)
            **kwargs: Additional configuration options
        
        Returns:
            Database connection configuration
        """
        # Default ports
        default_ports = {
            "postgresql": 5432,
            "mysql": 3306,
            "sqlserver": 1433
        }
        
        config = {
            "type": db_type.lower(),
            "host": host,
            "database": database,
            "username": username,
            "password": password,
            "port": port or default_ports.get(db_type.lower(), 5432)
        }
        
        # Add additional options
        config.update(kwargs)
        
        return config
    
    def create_file_config(self, 
                          file_path: str,
                          file_type: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """
        Create file processing configuration
        
        Args:
            file_path: Path to file
            file_type: File type (optional, auto-detected)
            **kwargs: Additional configuration options
        
        Returns:
            File processing configuration
        """
        config = {
            "file_path": file_path
        }
        
        if file_type:
            config["file_type"] = file_type.lower()
        
        # Add additional options
        config.update(kwargs)
        
        return config
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge user configuration with default configuration
        
        Args:
            default: Default configuration
            user: User configuration
        
        Returns:
            Merged configuration
        """
        merged = default.copy()
        
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def get_environment_config(self) -> Dict[str, Any]:
        """
        Get configuration from environment variables
        
        Returns:
            Configuration from environment variables
        """
        env_config = {}
        
        # Database configuration from environment
        if os.getenv("DB_TYPE"):
            env_config["database"] = {
                "type": os.getenv("DB_TYPE"),
                "host": os.getenv("DB_HOST"),
                "port": int(os.getenv("DB_PORT")) if os.getenv("DB_PORT") else None,
                "database": os.getenv("DB_NAME"),
                "username": os.getenv("DB_USER"),
                "password": os.getenv("DB_PASSWORD")
            }
        
        # File processing configuration from environment
        max_file_size = os.getenv("MAX_FILE_SIZE_MB")
        if max_file_size:
            env_config["file_processing"] = {
                "max_file_size_mb": float(max_file_size)
            }
        
        return env_config