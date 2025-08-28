#!/usr/bin/env python3
"""
Parquet Sink Adapter
Stores data TO Parquet files for efficient columnar storage
"""

import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path

from .base_sink_adapter import BaseSinkAdapter

logger = logging.getLogger(__name__)

class ParquetSinkAdapter(BaseSinkAdapter):
    """
    Parquet sink adapter for storing data in Parquet format
    
    Parquet is excellent for:
    - Columnar storage efficiency
    - Fast compression
    - Schema preservation
    - Cross-platform compatibility
    """
    
    def __init__(self):
        super().__init__()
        self.pyarrow_available = False
        
        # Check for pyarrow availability
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
            self.pyarrow_available = True
            self.pa = pa
            self.pq = pq
        except ImportError:
            logger.warning("PyArrow not available. Install with: pip install pyarrow")
    
    def connect(self, destination: str, **kwargs) -> bool:
        """
        Prepare for Parquet file writing
        
        Args:
            destination: Directory path for Parquet files
            **kwargs: Additional configuration
            
        Returns:
            True if setup successful
        """
        try:
            # Create directory if needed
            output_dir = Path(destination)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Store connection info
            self.storage_info = {
                'output_directory': str(output_dir),
                'storage_type': 'parquet',
                'pyarrow_available': self.pyarrow_available
            }
            
            logger.info(f"Parquet adapter ready for: {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Parquet adapter: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Cleanup resources"""
        # No persistent connections for file-based storage
        return True
    
    def store_dataframe(self, df: pd.DataFrame, 
                       destination: str,
                       table_name: Optional[str] = None,
                       storage_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Store DataFrame as Parquet file
        
        Args:
            df: DataFrame to store
            destination: Output directory
            table_name: File name (without extension)
            storage_options: Parquet-specific options
            
        Returns:
            Storage result information
        """
        start_time = pd.Timestamp.now()
        
        try:
            # Validate DataFrame
            validation = self.validate_dataframe(df)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': f"DataFrame validation failed: {validation['errors']}",
                    'warnings': validation['warnings']
                }
            
            # Setup if not already done
            if not self.storage_info:
                if not self.connect(destination):
                    return {
                        'success': False,
                        'error': 'Failed to setup Parquet adapter'
                    }
            
            # Prepare storage options
            options = storage_options or {}
            file_name = self._sanitize_table_name(table_name or 'data') + '.parquet'
            output_path = Path(destination) / file_name
            
            # Parquet-specific options
            compression = options.get('compression', 'snappy')  # snappy, gzip, brotli, lz4
            index = options.get('index', False)
            partition_cols = options.get('partition_cols', None)
            
            # Store DataFrame
            if self.pyarrow_available and partition_cols:
                # Use pyarrow for partitioned datasets
                table = self.pa.Table.from_pandas(df)
                self.pq.write_to_dataset(
                    table,
                    root_path=str(output_path.parent),
                    partition_cols=partition_cols,
                    compression=compression
                )
                output_info = f"partitioned dataset in {output_path.parent}"
            else:
                # Use pandas for simple files
                df.to_parquet(
                    output_path,
                    compression=compression,
                    index=index,
                    engine='pyarrow' if self.pyarrow_available else 'auto'
                )
                output_info = str(output_path)
            
            # Get file size
            if partition_cols:
                # Calculate total size for partitioned dataset
                total_size = sum(f.stat().st_size for f in Path(output_path.parent).rglob('*.parquet'))
            else:
                total_size = output_path.stat().st_size
            
            storage_duration = (pd.Timestamp.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'destination': destination,
                'file_path': output_info,
                'file_name': file_name,
                'storage_adapter': 'ParquetSinkAdapter',
                'storage_duration': storage_duration,
                'rows_stored': len(df),
                'columns_stored': len(df.columns),
                'file_size_bytes': total_size,
                'file_size_mb': round(total_size / 1024 / 1024, 2),
                'compression': compression,
                'partitioned': bool(partition_cols),
                'partition_columns': partition_cols,
                'storage_options_used': options,
                'warnings': validation.get('warnings', [])
            }
            
            self._log_storage_operation('Parquet storage', True, {
                'file': file_name,
                'rows': len(df),
                'size': f"{result['file_size_mb']}MB",
                'duration': f"{storage_duration:.2f}s"
            })
            
            return result
            
        except Exception as e:
            storage_duration = (pd.Timestamp.now() - start_time).total_seconds()
            error_msg = str(e)
            
            self._log_storage_operation('Parquet storage', False, {
                'error': error_msg,
                'duration': f"{storage_duration:.2f}s"
            })
            
            return {
                'success': False,
                'error': error_msg,
                'storage_duration': storage_duration,
                'destination': destination,
                'file_name': table_name
            }
    
    def read_parquet(self, file_path: str, **kwargs) -> pd.DataFrame:
        """
        Read Parquet file back to DataFrame
        
        Args:
            file_path: Path to Parquet file or directory
            **kwargs: Additional read options
            
        Returns:
            DataFrame with loaded data
        """
        try:
            path = Path(file_path)
            
            if path.is_dir():
                # Read partitioned dataset
                if self.pyarrow_available:
                    dataset = self.pq.ParquetDataset(path)
                    table = dataset.read()
                    return table.to_pandas()
                else:
                    # Fallback: read all parquet files in directory
                    parquet_files = list(path.rglob('*.parquet'))
                    if not parquet_files:
                        return pd.DataFrame()
                    
                    dfs = []
                    for file in parquet_files:
                        dfs.append(pd.read_parquet(file))
                    
                    return pd.concat(dfs, ignore_index=True)
            else:
                # Read single file
                return pd.read_parquet(file_path, **kwargs)
                
        except Exception as e:
            logger.error(f"Failed to read Parquet file: {e}")
            return pd.DataFrame()
    
    def list_parquet_files(self, directory: str) -> List[Dict[str, Any]]:
        """List all Parquet files in directory with metadata"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return []
            
            files_info = []
            for parquet_file in dir_path.rglob('*.parquet'):
                try:
                    stat = parquet_file.stat()
                    
                    # Try to get basic info without fully loading
                    if self.pyarrow_available:
                        parquet_file_obj = self.pq.ParquetFile(parquet_file)
                        metadata = parquet_file_obj.metadata
                        schema = parquet_file_obj.schema_arrow
                        
                        files_info.append({
                            'file_path': str(parquet_file),
                            'file_name': parquet_file.name,
                            'size_bytes': stat.st_size,
                            'size_mb': round(stat.st_size / 1024 / 1024, 2),
                            'modified_time': pd.Timestamp.fromtimestamp(stat.st_mtime),
                            'num_rows': metadata.num_rows,
                            'num_columns': schema.names.__len__(),
                            'columns': schema.names,
                            'compression': metadata.row_group(0).column(0).compression
                        })
                    else:
                        files_info.append({
                            'file_path': str(parquet_file),
                            'file_name': parquet_file.name,
                            'size_bytes': stat.st_size,
                            'size_mb': round(stat.st_size / 1024 / 1024, 2),
                            'modified_time': pd.Timestamp.fromtimestamp(stat.st_mtime)
                        })
                        
                except Exception as e:
                    logger.warning(f"Could not get metadata for {parquet_file}: {e}")
                    continue
            
            return files_info
            
        except Exception as e:
            logger.error(f"Failed to list Parquet files: {e}")
            return []
    
    def optimize_parquet_dataset(self, input_path: str, output_path: str, 
                                partition_cols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Optimize Parquet dataset by repartitioning and compacting
        
        Args:
            input_path: Source Parquet files
            output_path: Optimized output location
            partition_cols: Columns to partition by
            
        Returns:
            Optimization results
        """
        try:
            if not self.pyarrow_available:
                return {
                    'success': False,
                    'error': 'PyArrow required for dataset optimization'
                }
            
            start_time = pd.Timestamp.now()
            
            # Read the dataset
            dataset = self.pq.ParquetDataset(input_path)
            table = dataset.read()
            
            # Write optimized dataset
            self.pq.write_to_dataset(
                table,
                root_path=output_path,
                partition_cols=partition_cols,
                compression='snappy',
                use_legacy_dataset=False
            )
            
            optimization_duration = (pd.Timestamp.now() - start_time).total_seconds()
            
            # Get size comparison
            input_size = sum(f.stat().st_size for f in Path(input_path).rglob('*.parquet'))
            output_size = sum(f.stat().st_size for f in Path(output_path).rglob('*.parquet'))
            
            return {
                'success': True,
                'input_path': input_path,
                'output_path': output_path,
                'optimization_duration': optimization_duration,
                'input_size_mb': round(input_size / 1024 / 1024, 2),
                'output_size_mb': round(output_size / 1024 / 1024, 2),
                'size_reduction_percent': round((1 - output_size / input_size) * 100, 2),
                'partition_columns': partition_cols,
                'num_rows': table.num_rows,
                'num_columns': table.num_columns
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize Parquet dataset: {e}")
            return {
                'success': False,
                'error': str(e),
                'input_path': input_path,
                'output_path': output_path
            }