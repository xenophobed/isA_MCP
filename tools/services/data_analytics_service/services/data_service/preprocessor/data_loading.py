#!/usr/bin/env python3
"""
Data Loading Service - Step 1 of Preprocessing Pipeline
Handles data loading and format detection using adapters and processors
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import polars as pl

# Import adapters for different data sources
from ....adapters.file_adapters.csv_adapter import CSVAdapter
from ....adapters.file_adapters.excel_adapter import ExcelAdapter

# Import processors for format detection
from ....processors.data_processors.preprocessors.loading.file_format_detector import FileFormatDetector

logger = logging.getLogger(__name__)

class DataLoadingService:
    """
    Step 1: Data Loading & Format Detection Service
    
    Uses:
    - FileFormatDetector processor for format detection
    - CSVAdapter, ExcelAdapter for data loading
    
    Responsibilities:
    - Detect file format and properties
    - Load data using appropriate adapters
    - Validate basic structure
    - Provide standardized data access
    """
    
    def __init__(self):
        self.format_detector = FileFormatDetector()
        self.service_name = "DataLoadingService"
        
        # Supported adapters mapping
        self.adapters = {
            'csv': CSVAdapter,
            'tsv': CSVAdapter,
            'text': CSVAdapter,
            'excel': ExcelAdapter,
            'duckdb': self._get_duckdb_adapter
        }
        
        logger.info("Data Loading Service initialized")
    
    def load_data_source(self, source_path: str) -> Dict[str, Any]:
        """
        Load data source with format detection
        
        Args:
            source_path: Path to the data source
            
        Returns:
            Dict containing loading results
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Loading data source: {source_path}")
            
            # Step 1.1: Detect file format using processor
            format_info = self.format_detector.detect_format(source_path)
            if not format_info.get('success'):
                return {
                    'success': False,
                    'error': f"Format detection failed: {format_info.get('error')}",
                    'step': 'format_detection'
                }
            
            detected_format = format_info.get('detected_format')
            logger.info(f"Detected format: {detected_format}")
            
            # Step 1.2: Get appropriate adapter
            adapter = self._get_adapter(detected_format)
            if not adapter:
                return {
                    'success': False,
                    'error': f"No adapter available for format: {detected_format}",
                    'step': 'adapter_selection'
                }
            
            # Step 1.3: Extract metadata using adapter
            metadata_result = adapter.extract_metadata(source_path)
            if not metadata_result.get('valid'):
                return {
                    'success': False,
                    'error': f"Metadata extraction failed: {metadata_result.get('error')}",
                    'step': 'metadata_extraction'
                }
            
            # Step 1.4: Load actual DataFrame
            dataframe_result = self._load_dataframe(source_path, format_info)
            if not dataframe_result.get('success'):
                return {
                    'success': False,
                    'error': f"DataFrame loading failed: {dataframe_result.get('error')}",
                    'step': 'dataframe_loading'
                }
            
            # Calculate loading time
            loading_duration = (datetime.now() - start_time).total_seconds()
            
            # Prepare success result
            df = dataframe_result['dataframe']
            result = {
                'success': True,
                'source_path': source_path,
                'format_info': format_info,
                'metadata_result': metadata_result,
                'dataframe': df,
                'shape': (df.height, df.width),
                'columns': list(df.columns),
                'dtypes': {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)},
                'loading_duration': loading_duration,
                'adapter_used': adapter.__class__.__name__,
                'memory_usage_mb': df.estimated_size('mb')
            }
            
            logger.info(f"Data loaded successfully: {df.height} rows, {df.width} columns")
            return result
            
        except Exception as e:
            loading_duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Data loading failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'loading_duration': loading_duration,
                'step': 'general_error'
            }
    
    def _get_adapter(self, detected_format: str):
        """Get appropriate adapter for detected format"""
        adapter_class_or_method = self.adapters.get(detected_format)
        if adapter_class_or_method:
            # Handle special case for DuckDB (method instead of class)
            if detected_format == 'duckdb':
                return adapter_class_or_method()  # Call the method
            else:
                return adapter_class_or_method()  # Instantiate the class
        return None
    
    def _load_dataframe(self, source_path: str, format_info: Dict[str, Any]) -> Dict[str, Any]:
        """Load data into pandas DataFrame with proper settings"""
        try:
            detected_format = format_info.get('detected_format', 'csv')
            encoding = format_info.get('encoding', 'utf-8')
            delimiter = format_info.get('delimiter', ',')
            
            if detected_format in ['csv', 'tsv', 'text']:
                df = pl.read_csv(
                    source_path,
                    encoding=encoding,
                    separator=delimiter,
                    null_values=['', 'NULL', 'null', 'N/A', 'n/a', 'NA', '#N/A'],
                    infer_schema_length=10000  # Better schema inference
                )
            elif detected_format == 'excel':
                df = pl.read_excel(source_path, read_options={"null_values": ['', 'NULL', 'null', 'N/A', 'n/a', 'NA', '#N/A']})
            elif detected_format == 'duckdb':
                # Handle DuckDB using the enterprise DuckDB service
                try:
                    from resources.dbs.duckdb.core import get_duckdb_service, AccessLevel, ConnectionConfig
                    
                    # Create connection config
                    config = ConnectionConfig(
                        database_path=source_path,
                        read_only=True,  # Read-only for preprocessing
                        threads=2,
                        memory_limit="512MB"
                    )
                    
                    # Get enterprise DuckDB service
                    duckdb_service = get_duckdb_service(connection_config=config)
                    
                    # Get tables using the service
                    tables_result = duckdb_service.execute_query("SHOW TABLES", access_level=AccessLevel.READ_ONLY)
                    
                    if tables_result:
                        # Find the largest table for preprocessing sample
                        table_sizes = []
                        for table_row in tables_result:
                            table_name = table_row[0]
                            count_result = duckdb_service.execute_query(
                                f"SELECT COUNT(*) FROM {table_name}",
                                access_level=AccessLevel.READ_ONLY
                            )
                            count = count_result[0][0] if count_result else 0
                            table_sizes.append((table_name, count))
                        
                        if table_sizes:
                            # Get main table (largest)
                            main_table = max(table_sizes, key=lambda x: x[1])
                            table_name = main_table[0]
                            
                            # Load sample for preprocessing (limit to 5k for performance)
                            sample_size = min(5000, main_table[1])
                            df = duckdb_service.execute_query_df(
                                f"SELECT * FROM {table_name} LIMIT {sample_size}",
                                framework='polars',
                                access_level=AccessLevel.READ_ONLY
                            )
                            
                            logger.info(f"Loaded {len(df)} rows from DuckDB table '{table_name}' via enterprise service (sample of {main_table[1]} total)")
                        else:
                            return {'success': False, 'error': 'No data tables found in DuckDB'}
                    else:
                        return {'success': False, 'error': 'No tables found in DuckDB'}
                        
                except ImportError as e:
                    return {'success': False, 'error': f'DuckDB enterprise service not available: {e}'}
                except Exception as e:
                    return {'success': False, 'error': f'DuckDB enterprise service error: {str(e)}'}
            else:
                # Fallback to CSV
                df = pl.read_csv(source_path, encoding='utf-8')

            # Basic validation
            if df.height == 0:
                return {
                    'success': False,
                    'error': 'Loaded DataFrame is empty'
                }
            
            return {
                'success': True,
                'dataframe': df
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"DataFrame loading error: {str(e)}"
            }
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return list(self.format_detector.get_supported_formats().keys())
    
    def is_format_supported(self, file_path: str) -> bool:
        """Check if file format is supported"""
        return self.format_detector.is_supported_format(file_path)
    
    def _get_duckdb_adapter(self):
        """Return a DuckDB adapter using existing infrastructure"""
        # Use our existing DuckDB sink adapter for data loading
        from ....adapters.sink_adapters.duckdb_adapter import DuckDBSinkAdapter
        
        class DuckDBLoadingAdapter:
            """Simple DuckDB loading adapter wrapper"""
            def __init__(self):
                self.duckdb_adapter = DuckDBSinkAdapter()
            
            def extract_metadata(self, source_path: str) -> Dict[str, Any]:
                """Extract metadata from DuckDB"""
                try:
                    if not self.duckdb_adapter.connect(source_path):
                        return {'valid': False, 'error': 'Failed to connect to DuckDB'}
                    
                    tables = self.duckdb_adapter.list_tables()
                    total_rows = 0
                    total_columns = 0
                    
                    # Get info for each table
                    tables_info = []
                    for table_name in tables:
                        table_info = self.duckdb_adapter.get_table_info(table_name)
                        tables_info.append(table_info)
                        total_rows += table_info.get('row_count', 0)
                        total_columns += table_info.get('column_count', 0)
                    
                    return {
                        'valid': True,
                        'tables': tables_info,
                        'total_tables': len(tables),
                        'total_rows': total_rows,
                        'total_columns': total_columns
                    }
                    
                except Exception as e:
                    return {'valid': False, 'error': str(e)}
        
        return DuckDBLoadingAdapter()