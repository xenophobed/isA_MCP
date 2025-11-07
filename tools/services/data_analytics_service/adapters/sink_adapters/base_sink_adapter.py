#!/usr/bin/env python3
"""
Base Sink Adapter
Abstract base class for all data sink adapters
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import polars as pl
import logging

logger = logging.getLogger(__name__)

class BaseSinkAdapter(ABC):
    """
    Abstract base class for sink adapters
    
    Sink adapters handle storing/exporting data TO various destinations:
    - Databases (DuckDB, SQLite, PostgreSQL, etc.)
    - Files (Parquet, CSV, JSON, etc.)
    - Cloud storage (S3, etc.)
    """
    
    def __init__(self):
        self.adapter_name = self.__class__.__name__
        self.connection = None
        self.storage_info = {}
        
    @abstractmethod
    def store_dataframe(self, df: pl.DataFrame,
                       destination: str,
                       table_name: Optional[str] = None,
                       storage_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Store DataFrame to destination
        
        Args:
            df: DataFrame to store
            destination: Destination path/connection string
            table_name: Optional table name for database destinations
            storage_options: Optional storage configuration
            
        Returns:
            Dict with storage result information
        """
        pass
    
    @abstractmethod
    def connect(self, destination: str, **kwargs) -> bool:
        """
        Establish connection to destination
        
        Args:
            destination: Destination connection string/path
            **kwargs: Additional connection parameters
            
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close connection to destination
        
        Returns:
            True if disconnection successful
        """
        pass
    
    def validate_dataframe(self, df: pl.DataFrame) -> Dict[str, Any]:
        """
        Validate DataFrame before storage
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Validation result
        """
        validation = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Check if DataFrame is empty (polars API)
            if df.is_empty():
                validation['valid'] = False
                validation['errors'].append('DataFrame is empty')
                return validation
            
            # Check for problematic column names
            problematic_cols = []
            for col in df.columns:
                col_str = str(col)
                if col_str.startswith(' ') or col_str.endswith(' '):
                    problematic_cols.append(f"'{col}' has leading/trailing spaces")
                if any(char in col_str for char in ['/', '\\', '?', '*', '[', ']']):
                    problematic_cols.append(f"'{col}' contains special characters")
            
            if problematic_cols:
                validation['warnings'].extend(problematic_cols)
            
            # Check data types (polars API)
            # Count string/object columns
            object_col_count = sum(1 for dtype in df.dtypes if dtype == pl.Utf8 or dtype == pl.Object)
            if object_col_count > len(df.columns) * 0.8:
                validation['warnings'].append('High percentage of string/object columns - consider type conversion')

            # Check memory usage (polars API)
            memory_bytes = df.estimated_size()
            memory_mb = memory_bytes / (1024 * 1024)
            if memory_mb > 1000:  # 1GB threshold
                validation['warnings'].append(f'Large DataFrame: {memory_mb:.1f} MB')
            
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f'Validation error: {str(e)}')
        
        return validation
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about the storage destination"""
        return {
            'adapter_name': self.adapter_name,
            'connected': self.connection is not None,
            'storage_info': self.storage_info.copy()
        }
    
    def _sanitize_table_name(self, table_name: str) -> str:
        """Sanitize table name for database storage"""
        if not table_name:
            return 'data_table'
        
        # Remove special characters and replace with underscores
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', str(table_name))
        
        # Ensure it starts with a letter or underscore
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        
        # Limit length
        if len(sanitized) > 63:  # Most databases have limits around 63 chars
            sanitized = sanitized[:63]
        
        return sanitized or 'data_table'
    
    def _log_storage_operation(self, operation: str, success: bool, 
                              details: Dict[str, Any] = None):
        """Log storage operation"""
        details = details or {}
        if success:
            logger.info(f"{self.adapter_name}: {operation} successful - {details}")
        else:
            logger.error(f"{self.adapter_name}: {operation} failed - {details}")