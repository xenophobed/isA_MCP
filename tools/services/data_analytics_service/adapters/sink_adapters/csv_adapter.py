#!/usr/bin/env python3
"""
CSV Sink Adapter
Stores data TO CSV files for universal compatibility
"""

import polars as pl
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import csv

from .base_sink_adapter import BaseSinkAdapter

logger = logging.getLogger(__name__)

class CSVSinkAdapter(BaseSinkAdapter):
    """
    CSV sink adapter for storing data in CSV format
    
    CSV is excellent for:
    - Universal compatibility
    - Human readability
    - Simple data exchange
    - Legacy system integration
    """
    
    def __init__(self):
        super().__init__()
    
    def connect(self, destination: str, **kwargs) -> bool:
        """
        Prepare for CSV file writing
        
        Args:
            destination: Directory path for CSV files
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
                'storage_type': 'csv',
                'encoding_support': ['utf-8', 'latin-1', 'cp1252']
            }
            
            logger.info(f"CSV adapter ready for: {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup CSV adapter: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Cleanup resources"""
        # No persistent connections for file-based storage
        return True
    
    def store_dataframe(self, df: pl.DataFrame, 
                       destination: str,
                       table_name: Optional[str] = None,
                       storage_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Store DataFrame as CSV file
        
        Args:
            df: DataFrame to store
            destination: Output directory
            table_name: File name (without extension)
            storage_options: CSV-specific options
            
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
                        'error': 'Failed to setup CSV adapter'
                    }
            
            # Prepare storage options
            options = storage_options or {}
            file_name = self._sanitize_table_name(table_name or 'data') + '.csv'
            output_path = Path(destination) / file_name
            
            # CSV-specific options
            encoding = options.get('encoding', 'utf-8')
            sep = options.get('separator', ',')
            index = options.get('index', False)
            header = options.get('header', True)
            na_rep = options.get('na_rep', '')
            float_format = options.get('float_format', None)
            date_format = options.get('date_format', None)
            quoting = options.get('quoting', csv.QUOTE_MINIMAL)
            
            # Handle potential encoding issues
            if encoding not in ['utf-8', 'latin-1', 'cp1252']:
                logger.warning(f"Encoding {encoding} may cause issues, defaulting to utf-8")
                encoding = 'utf-8'
            
            # Store DataFrame
            df.to_csv(
                output_path,
                sep=sep,
                encoding=encoding,
                index=index,
                header=header,
                na_rep=na_rep,
                float_format=float_format,
                date_format=date_format,
                quoting=quoting
            )
            
            # Get file size
            file_size = output_path.stat().st_size
            
            storage_duration = (pd.Timestamp.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'destination': destination,
                'file_path': str(output_path),
                'file_name': file_name,
                'storage_adapter': 'CSVSinkAdapter',
                'storage_duration': storage_duration,
                'rows_stored': len(df),
                'columns_stored': len(df.columns),
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / 1024 / 1024, 2),
                'encoding': encoding,
                'separator': sep,
                'has_header': header,
                'has_index': index,
                'storage_options_used': options,
                'warnings': validation.get('warnings', [])
            }
            
            self._log_storage_operation('CSV storage', True, {
                'file': file_name,
                'rows': len(df),
                'size': f"{result['file_size_mb']}MB",
                'duration': f"{storage_duration:.2f}s"
            })
            
            return result
            
        except Exception as e:
            storage_duration = (pd.Timestamp.now() - start_time).total_seconds()
            error_msg = str(e)
            
            self._log_storage_operation('CSV storage', False, {
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
    
    def read_csv(self, file_path: str, **kwargs) -> pl.DataFrame:
        """
        Read CSV file back to DataFrame
        
        Args:
            file_path: Path to CSV file
            **kwargs: Additional read options
            
        Returns:
            DataFrame with loaded data
        """
        try:
            # Auto-detect encoding if not specified
            encoding = kwargs.get('encoding', None)
            if encoding is None:
                encoding = self._detect_encoding(file_path)
                kwargs['encoding'] = encoding
            
            # Try to read with specified options
            return pd.read_csv(file_path, **kwargs)
                
        except Exception as e:
            logger.error(f"Failed to read CSV file: {e}")
            return pl.DataFrame()
    
    def _detect_encoding(self, file_path: str) -> str:
        """Auto-detect file encoding"""
        try:
            import chardet
            
            with open(file_path, 'rb') as f:
                sample = f.read(10000)  # Read first 10KB
                result = chardet.detect(sample)
                confidence = result.get('confidence', 0)
                
                if confidence > 0.7:
                    return result['encoding']
                else:
                    return 'utf-8'  # Default fallback
                    
        except ImportError:
            # chardet not available, try common encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read(1000)  # Try to read first 1KB
                    return encoding
                except UnicodeDecodeError:
                    continue
            
            return 'utf-8'  # Final fallback
        except Exception:
            return 'utf-8'
    
    def list_csv_files(self, directory: str) -> List[Dict[str, Any]]:
        """List all CSV files in directory with metadata"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return []
            
            files_info = []
            for csv_file in dir_path.glob('*.csv'):
                try:
                    stat = csv_file.stat()
                    
                    # Try to get basic info without fully loading
                    encoding = self._detect_encoding(str(csv_file))
                    
                    # Read first few lines to get column info
                    with open(csv_file, 'r', encoding=encoding) as f:
                        sample_lines = [f.readline() for _ in range(3)]
                        if sample_lines and sample_lines[0]:
                            # Detect separator
                            sniffer = csv.Sniffer()
                            separator = sniffer.sniff(sample_lines[0]).delimiter
                            
                            # Count columns
                            header = sample_lines[0].strip().split(separator)
                            num_columns = len(header)
                        else:
                            separator = ','
                            num_columns = 0
                            header = []
                    
                    # Estimate row count (rough)
                    with open(csv_file, 'r', encoding=encoding) as f:
                        row_count = sum(1 for _ in f) - 1  # Subtract header
                    
                    files_info.append({
                        'file_path': str(csv_file),
                        'file_name': csv_file.name,
                        'size_bytes': stat.st_size,
                        'size_mb': round(stat.st_size / 1024 / 1024, 2),
                        'modified_time': pd.Timestamp.fromtimestamp(stat.st_mtime),
                        'estimated_rows': max(0, row_count),
                        'num_columns': num_columns,
                        'columns': header,
                        'encoding': encoding,
                        'separator': separator
                    })
                        
                except Exception as e:
                    logger.warning(f"Could not get metadata for {csv_file}: {e}")
                    continue
            
            return files_info
            
        except Exception as e:
            logger.error(f"Failed to list CSV files: {e}")
            return []
    
    def validate_csv_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate CSV file format and detect issues
        
        Args:
            file_path: Path to CSV file to validate
            
        Returns:
            Validation results
        """
        try:
            issues = []
            warnings = []
            
            file_path = Path(file_path)
            if not file_path.exists():
                return {
                    'valid': False,
                    'errors': ['File does not exist'],
                    'warnings': [],
                    'file_path': str(file_path)
                }
            
            # Check file size
            size_mb = file_path.stat().st_size / 1024 / 1024
            if size_mb > 500:  # Large file warning
                warnings.append(f"Large file size: {size_mb:.1f}MB")
            
            # Detect encoding
            encoding = self._detect_encoding(str(file_path))
            
            # Read sample to check format
            try:
                sample_df = pd.read_csv(file_path, nrows=100, encoding=encoding)
                
                # Check for common issues
                if sample_df.empty:
                    issues.append("File appears to be empty")
                
                # Check for unnamed columns
                unnamed_cols = [col for col in sample_df.columns if 'Unnamed:' in str(col)]
                if unnamed_cols:
                    warnings.append(f"Found {len(unnamed_cols)} unnamed columns")
                
                # Check for mixed data types in columns
                for col in sample_df.columns:
                    if sample_df[col].dtype == 'object':
                        # Try to detect if it should be numeric
                        numeric_count = pd.to_numeric(sample_df[col], errors='coerce').notna().sum()
                        if 0 < numeric_count < len(sample_df[col]) * 0.9:
                            warnings.append(f"Column '{col}' has mixed data types")
                
                return {
                    'valid': len(issues) == 0,
                    'errors': issues,
                    'warnings': warnings,
                    'file_path': str(file_path),
                    'detected_encoding': encoding,
                    'sample_rows': len(sample_df),
                    'sample_columns': len(sample_df.columns),
                    'column_names': list(sample_df.columns),
                    'data_types': sample_df.dtypes.to_dict()
                }
                
            except Exception as e:
                issues.append(f"Failed to parse CSV: {str(e)}")
                return {
                    'valid': False,
                    'errors': issues,
                    'warnings': warnings,
                    'file_path': str(file_path),
                    'detected_encoding': encoding
                }
                
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation failed: {str(e)}"],
                'warnings': [],
                'file_path': str(file_path)
            }
    
    def convert_to_csv(self, input_path: str, output_path: str, 
                      input_format: str = 'auto', **options) -> Dict[str, Any]:
        """
        Convert other formats to CSV
        
        Args:
            input_path: Source file path
            output_path: Output CSV path
            input_format: Source format (auto, excel, json, parquet)
            **options: Format-specific options
            
        Returns:
            Conversion results
        """
        try:
            start_time = pd.Timestamp.now()
            
            # Auto-detect format
            if input_format == 'auto':
                suffix = Path(input_path).suffix.lower()
                format_map = {
                    '.xlsx': 'excel', '.xls': 'excel',
                    '.json': 'json', '.jsonl': 'json',
                    '.parquet': 'parquet', '.pq': 'parquet'
                }
                input_format = format_map.get(suffix, 'unknown')
            
            # Read source file
            if input_format == 'excel':
                df = pd.read_excel(input_path, **options)
            elif input_format == 'json':
                df = pd.read_json(input_path, **options)
            elif input_format == 'parquet':
                df = pd.read_parquet(input_path, **options)
            else:
                return {
                    'success': False,
                    'error': f"Unsupported input format: {input_format}"
                }
            
            # Write as CSV
            result = self.store_dataframe(
                df, 
                str(Path(output_path).parent),
                Path(output_path).stem
            )
            
            conversion_duration = (pd.Timestamp.now() - start_time).total_seconds()
            
            if result['success']:
                result.update({
                    'conversion_type': f"{input_format}_to_csv",
                    'conversion_duration': conversion_duration,
                    'source_format': input_format,
                    'source_path': input_path
                })
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'conversion_type': f"{input_format}_to_csv",
                'source_path': input_path,
                'output_path': output_path
            }