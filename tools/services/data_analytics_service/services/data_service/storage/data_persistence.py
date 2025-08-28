"""
Data Persistence Service - Step 2 of Storage Pipeline
Executes actual data storage using sink adapters
"""

import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tools.services.data_analytics_service.adapters.sink_adapters import (
    DuckDBSinkAdapter, ParquetSinkAdapter, CSVSinkAdapter
)

logger = logging.getLogger(__name__)

@dataclass
class PersistenceResult:
    """Result of data persistence step"""
    success: bool
    storage_details: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class DataPersistenceService:
    """
    Data Persistence Service - Step 2 of Storage Pipeline
    
    Handles:
    - Actual data storage execution using sink adapters
    - Storage verification and validation
    - Multiple format storage coordination
    - Storage optimization and compression
    """
    
    def __init__(self):
        self.execution_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_bytes_stored': 0,
            'average_duration': 0.0
        }
        
        # Initialize sink adapters
        self.adapters = {
            'duckdb': DuckDBSinkAdapter(),
            'parquet': ParquetSinkAdapter(),
            'csv': CSVSinkAdapter()
        }
        
        logger.info("Data Persistence Service initialized")
    
    def persist_data(self, 
                    data: pd.DataFrame,
                    persistence_config: Dict[str, Any]) -> PersistenceResult:
        """
        Execute data persistence operations
        
        Args:
            data: DataFrame to persist
            persistence_config: Configuration for persistence
            
        Returns:
            PersistenceResult with storage details
        """
        start_time = datetime.now()
        
        try:
            storage_type = persistence_config.get('storage_type', 'duckdb')
            destination = persistence_config.get('destination')
            table_name = persistence_config.get('table_name', 'data')
            
            if not destination:
                return PersistenceResult(
                    success=False,
                    errors=["Destination is required for data persistence"]
                )
            
            # Validate storage type
            if storage_type not in self.adapters:
                return PersistenceResult(
                    success=False,
                    errors=[f"Unsupported storage type: {storage_type}"]
                )
            
            # Prepare storage options
            storage_options = self._prepare_storage_options(persistence_config)
            
            # Execute storage
            adapter = self.adapters[storage_type]
            storage_result = self._execute_storage(
                adapter, data, destination, table_name, storage_options, storage_type
            )
            
            if not storage_result['success']:
                return PersistenceResult(
                    success=False,
                    errors=[storage_result.get('error', 'Storage execution failed')]
                )
            
            # Verify storage if requested
            verification_result = {}
            if persistence_config.get('verify_storage', True):
                verification_result = self._verify_storage(
                    adapter, destination, table_name, len(data), len(data.columns), storage_type
                )
            
            # Calculate performance metrics
            duration = (datetime.now() - start_time).total_seconds()
            file_size = storage_result.get('file_size_bytes', 0)
            
            performance_metrics = {
                'duration_seconds': duration,
                'rows_stored': storage_result.get('rows_stored', len(data)),
                'columns_stored': storage_result.get('columns_stored', len(data.columns)),
                'storage_size_bytes': file_size,
                'storage_size_mb': storage_result.get('file_size_mb', 0),
                'throughput_rows_per_sec': len(data) / max(duration, 0.001),
                'throughput_mb_per_sec': (file_size / 1024 / 1024) / max(duration, 0.001)
            }
            
            # Prepare storage details
            storage_details = {
                'storage_type': storage_type,
                'destination': destination,
                'table_name': table_name,
                'storage_options': storage_options,
                'storage_result': storage_result,
                'verification': verification_result,
                'adapter_info': self._get_adapter_info(adapter)
            }
            
            # Update execution stats
            self._update_stats(True, duration, file_size)
            
            return PersistenceResult(
                success=True,
                storage_details=storage_details,
                performance_metrics=performance_metrics,
                warnings=storage_result.get('warnings', [])
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(False, duration, 0)
            
            logger.error(f"Data persistence failed: {e}")
            return PersistenceResult(
                success=False,
                errors=[f"Persistence error: {str(e)}"],
                performance_metrics={'duration_seconds': duration}
            )
    
    def _prepare_storage_options(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare storage options from configuration"""
        options = {}
        
        # Common options
        if 'compression' in config:
            options['compression'] = config['compression']
        
        if 'if_exists' in config:
            options['if_exists'] = config['if_exists']
        else:
            options['if_exists'] = 'replace'  # Default
        
        # Storage type specific options
        storage_type = config.get('storage_type', 'duckdb')
        
        if storage_type == 'parquet':
            if 'partition_columns' in config:
                options['partition_cols'] = config['partition_columns']
            if 'compression' not in options:
                options['compression'] = 'snappy'  # Default for Parquet
        
        elif storage_type == 'csv':
            options['index'] = config.get('include_index', False)
            options['encoding'] = config.get('encoding', 'utf-8')
            options['separator'] = config.get('separator', ',')
        
        elif storage_type == 'duckdb':
            options['table_name'] = config.get('table_name', 'data')
        
        # Add any custom parameters
        if 'custom_options' in config:
            options.update(config['custom_options'])
        
        return options
    
    def _execute_storage(self, 
                        adapter,
                        data: pd.DataFrame,
                        destination: str,
                        table_name: str,
                        storage_options: Dict[str, Any],
                        storage_type: str) -> Dict[str, Any]:
        """Execute storage using appropriate adapter"""
        try:
            # Connect adapter if needed
            if not getattr(adapter, 'storage_info', None):
                if not adapter.connect(destination):
                    return {
                        'success': False,
                        'error': f'Failed to connect {storage_type} adapter'
                    }
            
            # Store data using adapter
            result = adapter.store_dataframe(
                df=data,
                destination=destination,
                table_name=table_name,
                storage_options=storage_options
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Storage execution failed for {storage_type}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _verify_storage(self, 
                       adapter,
                       destination: str,
                       table_name: str,
                       expected_rows: int,
                       expected_columns: int,
                       storage_type: str) -> Dict[str, Any]:
        """Verify that data was stored correctly"""
        try:
            verification = {
                'verified': False,
                'storage_exists': False,
                'row_count_match': False,
                'column_count_match': False,
                'actual_rows': 0,
                'actual_columns': 0
            }
            
            if storage_type == 'duckdb':
                # Check if table exists
                tables = adapter.list_tables()
                if table_name in tables:
                    verification['storage_exists'] = True
                    
                    # Get table info
                    table_info = adapter.get_table_info(table_name)
                    if table_info:
                        verification['actual_rows'] = table_info.get('row_count', 0)
                        verification['actual_columns'] = table_info.get('column_count', 0)
            
            elif storage_type in ['parquet', 'csv']:
                # Check if file exists
                file_extension = '.parquet' if storage_type == 'parquet' else '.csv'
                file_path = Path(destination) / f"{table_name}{file_extension}"
                
                if file_path.exists():
                    verification['storage_exists'] = True
                    
                    # Try to read and verify
                    try:
                        if storage_type == 'parquet':
                            sample_df = adapter.read_parquet(str(file_path))
                        else:
                            sample_df = adapter.read_csv(str(file_path))
                        
                        if not sample_df.empty:
                            verification['actual_rows'] = len(sample_df)
                            verification['actual_columns'] = len(sample_df.columns)
                    except Exception as e:
                        logger.warning(f"Could not verify file contents: {e}")
            
            # Check matches
            verification['row_count_match'] = verification['actual_rows'] == expected_rows
            verification['column_count_match'] = verification['actual_columns'] == expected_columns
            
            verification['verified'] = (
                verification['storage_exists'] and
                verification['row_count_match'] and
                verification['column_count_match']
            )
            
            return verification
            
        except Exception as e:
            logger.warning(f"Storage verification failed: {e}")
            return {
                'verified': False,
                'error': str(e)
            }
    
    def _get_adapter_info(self, adapter) -> Dict[str, Any]:
        """Get information about the adapter used"""
        try:
            adapter_info = {
                'adapter_class': adapter.__class__.__name__,
                'adapter_type': getattr(adapter, 'storage_info', {}).get('storage_type', 'unknown')
            }
            
            # Get adapter-specific stats if available
            if hasattr(adapter, 'get_service_stats'):
                adapter_info['stats'] = adapter.get_service_stats()
            
            return adapter_info
            
        except Exception as e:
            return {'error': str(e)}
    
    def persist_multiple_formats(self, 
                                 data: pd.DataFrame,
                                 format_configs: List[Dict[str, Any]]) -> Dict[str, PersistenceResult]:
        """Persist data in multiple formats simultaneously"""
        results = {}
        
        for config in format_configs:
            storage_type = config.get('storage_type', 'unknown')
            try:
                result = self.persist_data(data, config)
                results[storage_type] = result
            except Exception as e:
                logger.error(f"Multi-format persistence failed for {storage_type}: {e}")
                results[storage_type] = PersistenceResult(
                    success=False,
                    errors=[str(e)]
                )
        
        return results
    
    def get_storage_info(self, 
                        storage_type: str,
                        destination: str,
                        table_name: str) -> Dict[str, Any]:
        """Get information about stored data"""
        try:
            if storage_type not in self.adapters:
                return {'error': f'Unsupported storage type: {storage_type}'}
            
            adapter = self.adapters[storage_type]
            
            if storage_type == 'duckdb':
                if not getattr(adapter, 'storage_info', None):
                    adapter.connect(destination)
                return adapter.get_table_info(table_name)
            
            elif storage_type in ['parquet', 'csv']:
                file_extension = '.parquet' if storage_type == 'parquet' else '.csv'
                file_path = Path(destination) / f"{table_name}{file_extension}"
                
                if file_path.exists():
                    stat = file_path.stat()
                    return {
                        'file_path': str(file_path),
                        'file_size_bytes': stat.st_size,
                        'file_size_mb': round(stat.st_size / 1024 / 1024, 2),
                        'modified_time': datetime.fromtimestamp(stat.st_mtime),
                        'storage_type': storage_type
                    }
                else:
                    return {'error': 'Storage file not found'}
            
            return {}
            
        except Exception as e:
            return {'error': str(e)}
    
    def delete_storage(self, 
                      storage_type: str,
                      destination: str,
                      table_name: str) -> bool:
        """Delete stored data"""
        try:
            if storage_type not in self.adapters:
                return False
            
            adapter = self.adapters[storage_type]
            
            if storage_type == 'duckdb':
                if not getattr(adapter, 'storage_info', None):
                    adapter.connect(destination)
                return adapter.delete_table(table_name)
            
            elif storage_type in ['parquet', 'csv']:
                file_extension = '.parquet' if storage_type == 'parquet' else '.csv'
                file_path = Path(destination) / f"{table_name}{file_extension}"
                
                if file_path.exists():
                    file_path.unlink()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Storage deletion failed: {e}")
            return False
    
    def _update_stats(self, success: bool, duration: float, bytes_stored: int):
        """Update execution statistics"""
        self.execution_stats['total_operations'] += 1
        
        if success:
            self.execution_stats['successful_operations'] += 1
            self.execution_stats['total_bytes_stored'] += bytes_stored
        else:
            self.execution_stats['failed_operations'] += 1
        
        # Update average duration
        total = self.execution_stats['total_operations']
        old_avg = self.execution_stats['average_duration']
        self.execution_stats['average_duration'] = (old_avg * (total - 1) + duration) / total
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_operations'] / 
                max(1, self.execution_stats['total_operations'])
            ),
            'total_mb_stored': round(self.execution_stats['total_bytes_stored'] / 1024 / 1024, 2)
        }
    
    def cleanup(self):
        """Cleanup adapter resources"""
        for adapter in self.adapters.values():
            try:
                adapter.disconnect()
            except Exception as e:
                logger.warning(f"Adapter cleanup warning: {e}")
        
        logger.info("Data Persistence Service cleanup completed")