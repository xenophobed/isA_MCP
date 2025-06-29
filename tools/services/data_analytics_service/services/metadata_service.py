#!/usr/bin/env python3
"""
Metadata Discovery Service
High-level service for discovering and analyzing metadata from various data sources
"""

import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from ..adapters.database_adapters import DatabaseAdapter, PostgreSQLAdapter, MySQLAdapter, SQLServerAdapter
from ..adapters.file_adapters import FileAdapter, ExcelAdapter, CSVAdapter
from ..utils.error_handler import DataAnalyticsError, DatabaseConnectionError, MetadataExtractionError
from ..utils.config_manager import ConfigManager
from ..utils.data_validator import DataValidator

class MetadataDiscoveryService:
    """High-level service for metadata discovery across different data sources"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.data_validator = DataValidator()
        self.supported_databases = {
            'postgresql': PostgreSQLAdapter,
            'mysql': MySQLAdapter,
            'sqlserver': SQLServerAdapter
        }
        self.supported_files = {
            'excel': ExcelAdapter,
            'csv': CSVAdapter
        }
        
    def discover_database_metadata(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Discover metadata from database
        
        Args:
            config: Database configuration containing:
                - type: Database type (postgresql, mysql, sqlserver)
                - host: Database host
                - port: Database port
                - database: Database name
                - username: Username
                - password: Password
                - schema_filter: Optional list of schemas to analyze
                - include_data_analysis: Whether to include data distribution analysis
                - sample_size: Sample size for data analysis
        
        Returns:
            Dictionary containing complete metadata information
        """
        try:
            # Validate configuration
            self._validate_database_config(config)
            
            # Get database type
            db_type = config['type'].lower()
            if db_type not in self.supported_databases:
                raise DataAnalyticsError(f"Unsupported database type: {db_type}")
            
            # Create adapter
            adapter_class = self.supported_databases[db_type]
            adapter = adapter_class()
            
            # Extract metadata
            metadata = adapter.extract_full_metadata(config)
            
            # Add discovery metadata
            metadata['discovery_info'] = {
                'service': 'MetadataDiscoveryService',
                'version': '1.0.0',
                'discovery_time': datetime.now().isoformat(),
                'source_type': 'database',
                'source_subtype': db_type
            }
            
            return metadata
            
        except Exception as e:
            raise MetadataExtractionError(f"Failed to discover database metadata: {str(e)}")
    
    def discover_file_metadata(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Discover metadata from file
        
        Args:
            config: File configuration containing:
                - file_path: Path to file
                - file_type: Type of file (excel, csv) - auto-detected if not provided
                - include_data_analysis: Whether to include data distribution analysis
        
        Returns:
            Dictionary containing complete metadata information
        """
        try:
            # Validate configuration
            self._validate_file_config(config)
            
            file_path = config['file_path']
            
            # Auto-detect file type if not provided
            file_type = config.get('file_type')
            if not file_type:
                file_type = self._detect_file_type(file_path)
            
            file_type = file_type.lower()
            if file_type not in self.supported_files:
                raise DataAnalyticsError(f"Unsupported file type: {file_type}")
            
            # Create adapter
            adapter_class = self.supported_files[file_type]
            adapter = adapter_class()
            
            # Extract metadata
            metadata = adapter.extract_full_metadata(config)
            
            # Add discovery metadata
            metadata['discovery_info'] = {
                'service': 'MetadataDiscoveryService',
                'version': '1.0.0',
                'discovery_time': datetime.now().isoformat(),
                'source_type': 'file',
                'source_subtype': file_type
            }
            
            return metadata
            
        except Exception as e:
            raise MetadataExtractionError(f"Failed to discover file metadata: {str(e)}")
    
    def discover_multiple_sources(self, sources: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Discover metadata from multiple sources
        
        Args:
            sources: List of source configurations
        
        Returns:
            Dictionary mapping source names to their metadata
        """
        results = {}
        errors = {}
        
        for i, source_config in enumerate(sources):
            source_name = source_config.get('name', f"source_{i}")
            
            try:
                if source_config.get('type') in self.supported_databases:
                    # Database source
                    metadata = self.discover_database_metadata(source_config)
                elif 'file_path' in source_config:
                    # File source
                    metadata = self.discover_file_metadata(source_config)
                else:
                    raise DataAnalyticsError(f"Unknown source type for {source_name}")
                
                results[source_name] = metadata
                
            except Exception as e:
                errors[source_name] = str(e)
        
        # Combine results
        combined_results = {
            'sources': results,
            'errors': errors,
            'summary': {
                'total_sources': len(sources),
                'successful': len(results),
                'failed': len(errors),
                'discovery_time': datetime.now().isoformat()
            }
        }
        
        return combined_results
    
    def compare_schemas(self, source1_metadata: Dict[str, Any], source2_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare schemas between two data sources
        
        Args:
            source1_metadata: Metadata from first source
            source2_metadata: Metadata from second source
        
        Returns:
            Dictionary containing comparison results
        """
        try:
            comparison = {
                'comparison_time': datetime.now().isoformat(),
                'source1_info': source1_metadata.get('source_info', {}),
                'source2_info': source2_metadata.get('source_info', {}),
                'table_comparison': self._compare_tables(
                    source1_metadata.get('tables', []),
                    source2_metadata.get('tables', [])
                ),
                'column_comparison': self._compare_columns(
                    source1_metadata.get('columns', []),
                    source2_metadata.get('columns', [])
                ),
                'relationship_comparison': self._compare_relationships(
                    source1_metadata.get('relationships', []),
                    source2_metadata.get('relationships', [])
                )
            }
            
            return comparison
            
        except Exception as e:
            raise DataAnalyticsError(f"Failed to compare schemas: {str(e)}")
    
    def export_metadata(self, metadata: Dict[str, Any], output_path: str, format: str = 'json') -> bool:
        """
        Export metadata to file
        
        Args:
            metadata: Metadata to export
            output_path: Output file path
            format: Export format (json, csv)
        
        Returns:
            Success status
        """
        try:
            if format.lower() == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
                return True
            
            elif format.lower() == 'csv':
                # Export tables and columns as CSV
                import pandas as pd
                
                # Create tables CSV
                tables_df = pd.DataFrame(metadata.get('tables', []))
                if not tables_df.empty:
                    tables_path = output_path.replace('.csv', '_tables.csv')
                    tables_df.to_csv(tables_path, index=False)
                
                # Create columns CSV
                columns_df = pd.DataFrame(metadata.get('columns', []))
                if not columns_df.empty:
                    columns_path = output_path.replace('.csv', '_columns.csv')
                    columns_df.to_csv(columns_path, index=False)
                
                return True
            
            else:
                raise DataAnalyticsError(f"Unsupported export format: {format}")
                
        except Exception as e:
            print(f"Failed to export metadata: {e}")
            return False
    
    def get_summary_statistics(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary statistics from metadata
        
        Args:
            metadata: Metadata dictionary
        
        Returns:
            Summary statistics
        """
        try:
            tables = metadata.get('tables', [])
            columns = metadata.get('columns', [])
            relationships = metadata.get('relationships', [])
            
            summary = {
                'totals': {
                    'tables': len(tables),
                    'columns': len(columns),
                    'relationships': len(relationships)
                },
                'table_statistics': self._analyze_table_statistics(tables),
                'column_statistics': self._analyze_column_statistics(columns),
                'relationship_statistics': self._analyze_relationship_statistics(relationships),
                'data_quality_overview': self._analyze_data_quality(metadata)
            }
            
            return summary
            
        except Exception as e:
            return {"error": str(e)}
    
    def _validate_database_config(self, config: Dict[str, Any]) -> None:
        """Validate database configuration"""
        required_fields = ['type', 'host', 'database', 'username', 'password']
        
        for field in required_fields:
            if field not in config:
                raise DataAnalyticsError(f"Missing required field: {field}")
        
        if config['type'].lower() not in self.supported_databases:
            raise DataAnalyticsError(f"Unsupported database type: {config['type']}")
    
    def _validate_file_config(self, config: Dict[str, Any]) -> None:
        """Validate file configuration"""
        if 'file_path' not in config:
            raise DataAnalyticsError("Missing required field: file_path")
        
        file_path = Path(config['file_path'])
        if not file_path.exists():
            raise DataAnalyticsError(f"File not found: {config['file_path']}")
    
    def _detect_file_type(self, file_path: str) -> str:
        """Auto-detect file type from extension"""
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        if extension in ['.xlsx', '.xls']:
            return 'excel'
        elif extension == '.csv':
            return 'csv'
        else:
            raise DataAnalyticsError(f"Cannot detect file type for extension: {extension}")
    
    def _compare_tables(self, tables1: List[Dict], tables2: List[Dict]) -> Dict[str, Any]:
        """Compare tables between two sources"""
        table_names1 = {t['table_name'] for t in tables1}
        table_names2 = {t['table_name'] for t in tables2}
        
        return {
            'common_tables': list(table_names1 & table_names2),
            'source1_only': list(table_names1 - table_names2),
            'source2_only': list(table_names2 - table_names1),
            'total_source1': len(table_names1),
            'total_source2': len(table_names2),
            'similarity_score': len(table_names1 & table_names2) / max(len(table_names1), len(table_names2)) if tables1 or tables2 else 0
        }
    
    def _compare_columns(self, columns1: List[Dict], columns2: List[Dict]) -> Dict[str, Any]:
        """Compare columns between two sources"""
        # Group columns by table
        tables1_cols = {}
        tables2_cols = {}
        
        for col in columns1:
            table = col['table_name']
            if table not in tables1_cols:
                tables1_cols[table] = []
            tables1_cols[table].append(col['column_name'])
        
        for col in columns2:
            table = col['table_name']
            if table not in tables2_cols:
                tables2_cols[table] = []
            tables2_cols[table].append(col['column_name'])
        
        # Compare common tables
        common_tables = set(tables1_cols.keys()) & set(tables2_cols.keys())
        table_comparisons = {}
        
        for table in common_tables:
            cols1 = set(tables1_cols[table])
            cols2 = set(tables2_cols[table])
            
            table_comparisons[table] = {
                'common_columns': list(cols1 & cols2),
                'source1_only': list(cols1 - cols2),
                'source2_only': list(cols2 - cols1),
                'similarity_score': len(cols1 & cols2) / max(len(cols1), len(cols2)) if cols1 or cols2 else 0
            }
        
        return {
            'table_comparisons': table_comparisons,
            'total_columns_source1': len(columns1),
            'total_columns_source2': len(columns2)
        }
    
    def _compare_relationships(self, relationships1: List[Dict], relationships2: List[Dict]) -> Dict[str, Any]:
        """Compare relationships between two sources"""
        # Create relationship signatures
        rel_sigs1 = {f"{r['from_table']}.{r['from_column']} -> {r['to_table']}.{r['to_column']}" for r in relationships1}
        rel_sigs2 = {f"{r['from_table']}.{r['from_column']} -> {r['to_table']}.{r['to_column']}" for r in relationships2}
        
        return {
            'common_relationships': list(rel_sigs1 & rel_sigs2),
            'source1_only': list(rel_sigs1 - rel_sigs2),
            'source2_only': list(rel_sigs2 - rel_sigs1),
            'total_source1': len(rel_sigs1),
            'total_source2': len(rel_sigs2),
            'similarity_score': len(rel_sigs1 & rel_sigs2) / max(len(rel_sigs1), len(rel_sigs2)) if relationships1 or relationships2 else 0
        }
    
    def _analyze_table_statistics(self, tables: List[Dict]) -> Dict[str, Any]:
        """Analyze table statistics"""
        if not tables:
            return {}
        
        record_counts = [t.get('record_count', 0) for t in tables]
        
        return {
            'total_records': sum(record_counts),
            'avg_records_per_table': sum(record_counts) / len(tables),
            'largest_table': max(tables, key=lambda t: t.get('record_count', 0))['table_name'] if record_counts else None,
            'smallest_table': min(tables, key=lambda t: t.get('record_count', 0))['table_name'] if record_counts else None
        }
    
    def _analyze_column_statistics(self, columns: List[Dict]) -> Dict[str, Any]:
        """Analyze column statistics"""
        if not columns:
            return {}
        
        data_types = [c.get('data_type', 'unknown') for c in columns]
        nullable_count = sum(1 for c in columns if c.get('is_nullable', False))
        
        from collections import Counter
        type_distribution = Counter(data_types)
        
        return {
            'total_columns': len(columns),
            'nullable_columns': nullable_count,
            'not_nullable_columns': len(columns) - nullable_count,
            'data_type_distribution': dict(type_distribution.most_common())
        }
    
    def _analyze_relationship_statistics(self, relationships: List[Dict]) -> Dict[str, Any]:
        """Analyze relationship statistics"""
        if not relationships:
            return {}
        
        constraint_types = [r.get('constraint_type', 'unknown') for r in relationships]
        
        from collections import Counter
        type_distribution = Counter(constraint_types)
        
        return {
            'total_relationships': len(relationships),
            'constraint_type_distribution': dict(type_distribution.most_common())
        }
    
    def _analyze_data_quality(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall data quality"""
        tables = metadata.get('tables', [])
        columns = metadata.get('columns', [])
        
        quality_scores = [t.get('data_quality_score', 0) for t in tables if t.get('data_quality_score') is not None]
        
        return {
            'avg_data_quality_score': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            'tables_with_quality_score': len(quality_scores),
            'columns_with_comments': sum(1 for c in columns if c.get('column_comment')),
            'tables_with_comments': sum(1 for t in tables if t.get('table_comment'))
        }