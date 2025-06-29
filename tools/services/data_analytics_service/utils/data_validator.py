#!/usr/bin/env python3
"""
Data validation utilities for data analytics service
"""

import re
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

class DataValidator:
    """Data validation utilities"""
    
    def __init__(self):
        # Common validation patterns
        self.patterns = {
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'phone': re.compile(r'^[\+]?[1-9][\d]{0,15}$'),
            'url': re.compile(r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'),
            'ip_address': re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'),
            'date_iso': re.compile(r'^\d{4}-\d{2}-\d{2}$'),
            'datetime_iso': re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
            'numeric': re.compile(r'^-?\d+\.?\d*$')
        }
    
    def validate_database_config(self, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate database configuration
        
        Args:
            config: Database configuration dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        required_fields = ['type', 'host', 'database', 'username', 'password']
        
        # Check required fields
        for field in required_fields:
            if field not in config or not config[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate database type
        supported_types = ['postgresql', 'mysql', 'sqlserver']
        if 'type' in config and config['type'].lower() not in supported_types:
            errors.append(f"Unsupported database type: {config['type']}. Supported types: {supported_types}")
        
        # Validate port
        if 'port' in config:
            port = config['port']
            if not isinstance(port, int) or port < 1 or port > 65535:
                errors.append("Port must be an integer between 1 and 65535")
        
        # Validate host
        if 'host' in config and config['host']:
            host = config['host']
            if not self._is_valid_hostname(host):
                errors.append(f"Invalid hostname: {host}")
        
        return len(errors) == 0, errors
    
    def validate_file_config(self, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate file configuration
        
        Args:
            config: File configuration dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        if 'file_path' not in config or not config['file_path']:
            errors.append("Missing required field: file_path")
        else:
            file_path = Path(config['file_path'])
            
            # Check if file exists
            if not file_path.exists():
                errors.append(f"File does not exist: {config['file_path']}")
            
            # Check file extension
            supported_extensions = {'.csv', '.xlsx', '.xls'}
            if file_path.suffix.lower() not in supported_extensions:
                errors.append(f"Unsupported file type: {file_path.suffix}. Supported types: {supported_extensions}")
            
            # Check file size (if configured)
            if file_path.exists():
                max_size_mb = config.get('max_file_size_mb', 100)
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb > max_size_mb:
                    errors.append(f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb} MB)")
        
        return len(errors) == 0, errors
    
    def validate_metadata_structure(self, metadata: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate metadata structure
        
        Args:
            metadata: Metadata dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required top-level keys
        required_keys = ['source_info', 'tables', 'columns']
        for key in required_keys:
            if key not in metadata:
                errors.append(f"Missing required metadata key: {key}")
        
        # Validate source_info
        if 'source_info' in metadata:
            source_info = metadata['source_info']
            if not isinstance(source_info, dict):
                errors.append("source_info must be a dictionary")
            else:
                if 'type' not in source_info:
                    errors.append("source_info must contain 'type' field")
        
        # Validate tables
        if 'tables' in metadata:
            if not isinstance(metadata['tables'], list):
                errors.append("tables must be a list")
            else:
                for i, table in enumerate(metadata['tables']):
                    table_errors = self._validate_table_structure(table, i)
                    errors.extend(table_errors)
        
        # Validate columns
        if 'columns' in metadata:
            if not isinstance(metadata['columns'], list):
                errors.append("columns must be a list")
            else:
                for i, column in enumerate(metadata['columns']):
                    column_errors = self._validate_column_structure(column, i)
                    errors.extend(column_errors)
        
        return len(errors) == 0, errors
    
    def validate_data_types(self, values: List[Any], expected_type: str) -> tuple[bool, List[str]]:
        """
        Validate data types for a list of values
        
        Args:
            values: List of values to validate
            expected_type: Expected data type (string, integer, float, boolean, date, email, etc.)
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        for i, value in enumerate(values):
            if value is None:
                continue  # Skip null values
            
            is_valid = self._validate_single_value(value, expected_type)
            if not is_valid:
                errors.append(f"Value at index {i} ({value}) does not match expected type {expected_type}")
        
        return len(errors) == 0, errors
    
    def validate_data_quality(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate data quality metrics
        
        Args:
            data: List of data records
        
        Returns:
            Data quality report
        """
        if not data:
            return {
                'total_records': 0,
                'quality_score': 0,
                'issues': ['No data provided']
            }
        
        total_records = len(data)
        issues = []
        
        # Get all columns
        all_columns = set()
        for record in data:
            all_columns.update(record.keys())
        
        column_stats = {}
        
        for column in all_columns:
            # Count nulls and empties
            null_count = 0
            empty_count = 0
            valid_count = 0
            
            for record in data:
                value = record.get(column)
                if value is None:
                    null_count += 1
                elif value == '' or (isinstance(value, str) and value.strip() == ''):
                    empty_count += 1
                else:
                    valid_count += 1
            
            null_percentage = (null_count / total_records) * 100
            empty_percentage = (empty_count / total_records) * 100
            completeness = (valid_count / total_records) * 100
            
            column_stats[column] = {
                'null_count': null_count,
                'empty_count': empty_count,
                'valid_count': valid_count,
                'null_percentage': null_percentage,
                'empty_percentage': empty_percentage,
                'completeness': completeness
            }
            
            # Flag quality issues
            if null_percentage > 50:
                issues.append(f"Column '{column}' has high null percentage: {null_percentage:.1f}%")
            if empty_percentage > 30:
                issues.append(f"Column '{column}' has high empty percentage: {empty_percentage:.1f}%")
        
        # Calculate overall quality score
        avg_completeness = sum(stats['completeness'] for stats in column_stats.values()) / len(column_stats)
        quality_score = avg_completeness / 100
        
        return {
            'total_records': total_records,
            'total_columns': len(all_columns),
            'quality_score': round(quality_score, 3),
            'average_completeness': round(avg_completeness, 2),
            'column_statistics': column_stats,
            'issues': issues
        }
    
    def _validate_table_structure(self, table: Dict[str, Any], index: int) -> List[str]:
        """Validate individual table structure"""
        errors = []
        required_fields = ['table_name', 'schema_name', 'table_type']
        
        if not isinstance(table, dict):
            errors.append(f"Table at index {index} must be a dictionary")
            return errors
        
        for field in required_fields:
            if field not in table:
                errors.append(f"Table at index {index} missing required field: {field}")
        
        # Validate record_count if present
        if 'record_count' in table and not isinstance(table['record_count'], int):
            errors.append(f"Table at index {index}: record_count must be an integer")
        
        return errors
    
    def _validate_column_structure(self, column: Dict[str, Any], index: int) -> List[str]:
        """Validate individual column structure"""
        errors = []
        required_fields = ['table_name', 'column_name', 'data_type']
        
        if not isinstance(column, dict):
            errors.append(f"Column at index {index} must be a dictionary")
            return errors
        
        for field in required_fields:
            if field not in column:
                errors.append(f"Column at index {index} missing required field: {field}")
        
        # Validate ordinal_position if present
        if 'ordinal_position' in column and not isinstance(column['ordinal_position'], int):
            errors.append(f"Column at index {index}: ordinal_position must be an integer")
        
        return errors
    
    def _validate_single_value(self, value: Any, expected_type: str) -> bool:
        """Validate a single value against expected type"""
        expected_type = expected_type.lower()
        
        if expected_type == 'string':
            return isinstance(value, str)
        elif expected_type == 'integer':
            return isinstance(value, int)
        elif expected_type == 'float':
            return isinstance(value, (int, float))
        elif expected_type == 'boolean':
            return isinstance(value, bool)
        elif expected_type == 'email':
            return isinstance(value, str) and bool(self.patterns['email'].match(value))
        elif expected_type == 'phone':
            return isinstance(value, str) and bool(self.patterns['phone'].match(str(value).replace('-', '').replace('(', '').replace(')', '').replace(' ', '')))
        elif expected_type == 'url':
            return isinstance(value, str) and bool(self.patterns['url'].match(value))
        elif expected_type == 'ip_address':
            return isinstance(value, str) and bool(self.patterns['ip_address'].match(value))
        elif expected_type == 'date':
            return isinstance(value, str) and bool(self.patterns['date_iso'].match(value))
        elif expected_type == 'datetime':
            return isinstance(value, str) and bool(self.patterns['datetime_iso'].match(value))
        elif expected_type == 'numeric':
            return isinstance(value, str) and bool(self.patterns['numeric'].match(value))
        else:
            return True  # Unknown type, assume valid
    
    def _is_valid_hostname(self, hostname: str) -> bool:
        """Validate hostname format"""
        if not hostname or len(hostname) > 255:
            return False
        
        # Check for IP address
        if self.patterns['ip_address'].match(hostname):
            return True
        
        # Check for hostname
        if hostname[-1] == ".":
            hostname = hostname[:-1]
        
        allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        return all(allowed.match(x) for x in hostname.split("."))
    
    def check_data_consistency(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check data consistency across metadata
        
        Args:
            metadata: Metadata dictionary
        
        Returns:
            Consistency report
        """
        report = {
            'consistent': True,
            'issues': [],
            'warnings': []
        }
        
        tables = metadata.get('tables', [])
        columns = metadata.get('columns', [])
        
        # Create lookup dictionaries
        table_names = {table['table_name'] for table in tables}
        column_table_map = {}
        
        for column in columns:
            table_name = column['table_name']
            if table_name not in column_table_map:
                column_table_map[table_name] = []
            column_table_map[table_name].append(column)
        
        # Check if all columns reference existing tables
        for table_name in column_table_map:
            if table_name not in table_names:
                report['issues'].append(f"Columns reference non-existent table: {table_name}")
                report['consistent'] = False
        
        # Check if all tables have columns
        for table_name in table_names:
            if table_name not in column_table_map:
                report['warnings'].append(f"Table '{table_name}' has no columns defined")
        
        # Check for duplicate table names
        table_name_counts = {}
        for table in tables:
            name = table['table_name']
            table_name_counts[name] = table_name_counts.get(name, 0) + 1
        
        for name, count in table_name_counts.items():
            if count > 1:
                report['issues'].append(f"Duplicate table name: {name} (appears {count} times)")
                report['consistent'] = False
        
        return report