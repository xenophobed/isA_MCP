#!/usr/bin/env python3
"""
CSV file adapter for metadata extraction
"""

import csv
from typing import Dict, List, Any, Optional
from collections import Counter
from .base_adapter import FileAdapter
from ...core.metadata_extractor import TableInfo, ColumnInfo

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

class CSVAdapter(FileAdapter):
    """CSV file adapter for .csv files"""
    
    def __init__(self):
        super().__init__()
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for CSV adapter. Install with: pip install pandas")
        
        self.dataframe = None
        self.csv_info = {}
        self.delimiter = None
        self.encoding = None
    
    def _load_file(self, file_path: str) -> Any:
        """Load CSV file"""
        try:
            # Detect encoding
            self.encoding = self._detect_encoding(file_path)
            
            # Detect delimiter
            self.delimiter = self._detect_delimiter(file_path)
            
            # Load CSV with detected parameters
            df = pd.read_csv(
                file_path, 
                delimiter=self.delimiter,
                encoding=self.encoding,
                na_values=['', 'NULL', 'null', 'N/A', 'n/a', 'NA', '#N/A'],
                keep_default_na=True
            )
            
            self.dataframe = df
            
            # Store CSV metadata
            self.csv_info = {
                'delimiter': self.delimiter,
                'encoding': self.encoding,
                'has_header': self._detect_header(df),
                'total_rows': len(df),
                'total_columns': len(df.columns)
            }
            
            return df
        
        except Exception as e:
            raise Exception(f"Failed to load CSV file: {e}")
    
    def _detect_delimiter(self, file_path: str) -> str:
        """Detect CSV delimiter"""
        try:
            with open(file_path, 'r', encoding=self.encoding or 'utf-8') as file:
                # Read first few lines to detect delimiter
                sample = file.read(1024)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                return delimiter
        except Exception:
            # Default to comma
            return ','
    
    def _detect_header(self, df: pd.DataFrame) -> bool:
        """Detect if CSV has header row"""
        if df.empty:
            return False
        
        # Check if first row looks like headers (all strings, no duplicates)
        first_row = df.iloc[0] if len(df) > 0 else pd.Series()
        
        # If all values in first row are strings and they're unique, likely header
        if len(df) > 1:
            try:
                first_row_strings = all(isinstance(val, str) for val in first_row if pd.notna(val))
                first_row_unique = len(first_row.dropna().unique()) == len(first_row.dropna())
                
                # Check if second row has different data types
                second_row = df.iloc[1]
                second_row_has_numbers = any(isinstance(val, (int, float)) for val in second_row if pd.notna(val))
                
                return first_row_strings and first_row_unique and second_row_has_numbers
            except Exception:
                pass
        
        # Check column names - if they look like generated names (0, 1, 2), probably no header
        generated_names = all(isinstance(col, int) or str(col).isdigit() for col in df.columns)
        return not generated_names
    
    def _analyze_structure(self) -> Dict[str, Any]:
        """Analyze CSV file structure"""
        if self.dataframe is None:
            return {}
        
        df = self.dataframe
        
        structure = {
            'csv_info': self.csv_info,
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': list(df.columns),
            'data_types': {str(col): str(df[col].dtype) for col in df.columns},
            'empty_rows': df.isnull().all(axis=1).sum(),
            'empty_columns': df.isnull().all(axis=0).sum(),
            'duplicate_rows': df.duplicated().sum(),
            'memory_usage': df.memory_usage(deep=True).sum()
        }
        
        return structure
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get CSV file as table metadata"""
        if self.dataframe is None:
            return []
        
        # CSV is treated as a single table
        file_name = self.file_info['file_name'] if self.file_info else 'csv_data'
        table_name = file_name.replace('.csv', '').replace('.CSV', '')
        
        table_info = TableInfo(
            table_name=table_name,
            schema_name="csv_file",
            table_type="CSV",
            record_count=len(self.dataframe),
            table_comment=f"CSV file: {file_name}",
            created_date="",
            last_modified="",
            business_category=self._categorize_csv_content(),
            update_frequency="unknown",
            data_quality_score=self._calculate_data_quality_score(),
            key_columns=self._identify_key_columns()
        )
        
        return [table_info]
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get column information from CSV"""
        if self.dataframe is None:
            return []
        
        columns = []
        df = self.dataframe
        file_name = self.file_info['file_name'] if self.file_info else 'csv_data'
        table_name = table_name or file_name.replace('.csv', '').replace('.CSV', '')
        
        for idx, column_name in enumerate(df.columns):
            column_series = df[column_name]
            
            # Analyze column data
            data_analysis = self._analyze_column_data(column_series)
            
            column_info = ColumnInfo(
                table_name=table_name,
                column_name=str(column_name),
                data_type=self._map_pandas_to_sql_type(column_series.dtype),
                max_length=data_analysis.get('max_length'),
                is_nullable=column_series.isnull().any(),
                default_value="",
                column_comment=f"Column from CSV file {file_name}",
                ordinal_position=idx + 1,
                business_type=self._infer_business_type(column_name, column_series),
                value_range=data_analysis.get('value_range'),
                null_percentage=data_analysis.get('null_percentage'),
                unique_percentage=data_analysis.get('unique_percentage'),
                sample_values=data_analysis.get('sample_values')
            )
            
            columns.append(column_info)
        
        return columns
    
    def _analyze_column_data(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze pandas series data"""
        analysis = {}
        
        # Basic stats
        total_count = len(series)
        null_count = series.isnull().sum()
        non_null_series = series.dropna()
        
        analysis['null_percentage'] = null_count / total_count if total_count > 0 else 0
        analysis['unique_count'] = non_null_series.nunique()
        analysis['unique_percentage'] = analysis['unique_count'] / len(non_null_series) if len(non_null_series) > 0 else 0
        
        # Sample values
        sample_size = min(10, len(non_null_series))
        if sample_size > 0:
            analysis['sample_values'] = non_null_series.sample(sample_size).tolist()
        else:
            analysis['sample_values'] = []
        
        # Value range for numeric columns
        if pd.api.types.is_numeric_dtype(series):
            if len(non_null_series) > 0:
                analysis['value_range'] = {
                    'min': float(non_null_series.min()),
                    'max': float(non_null_series.max()),
                    'mean': float(non_null_series.mean()),
                    'std': float(non_null_series.std()) if len(non_null_series) > 1 else 0
                }
        
        # Max length for string columns
        if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
            string_lengths = non_null_series.astype(str).str.len()
            if len(string_lengths) > 0:
                analysis['max_length'] = int(string_lengths.max())
                analysis['avg_length'] = float(string_lengths.mean())
            else:
                analysis['max_length'] = 0
                analysis['avg_length'] = 0
        
        return analysis
    
    def _map_pandas_to_sql_type(self, dtype) -> str:
        """Map pandas dtype to SQL-like type"""
        dtype_str = str(dtype)
        
        if 'int' in dtype_str:
            return 'integer'
        elif 'float' in dtype_str:
            return 'decimal'
        elif 'bool' in dtype_str:
            return 'boolean'
        elif 'datetime' in dtype_str:
            return 'timestamp'
        elif 'object' in dtype_str:
            return 'text'
        else:
            return 'text'
    
    def _infer_business_type(self, column_name: str, series: pd.Series) -> str:
        """Infer business type from column name and data"""
        column_lower = str(column_name).lower()
        
        # ID columns
        if any(keyword in column_lower for keyword in ['id', 'key', 'code', 'number']):
            return 'identifier'
        
        # Name columns
        elif any(keyword in column_lower for keyword in ['name', 'title', 'description']):
            return 'name'
        
        # Amount/Price columns
        elif any(keyword in column_lower for keyword in ['amount', 'price', 'cost', 'value', 'total', 'sum']):
            return 'amount'
        
        # Date columns
        elif any(keyword in column_lower for keyword in ['date', 'time', 'created', 'updated']):
            return 'datetime'
        
        # Status columns
        elif any(keyword in column_lower for keyword in ['status', 'state', 'type', 'category']):
            return 'category'
        
        # Email columns
        elif 'email' in column_lower:
            return 'email'
        
        # Phone columns
        elif any(keyword in column_lower for keyword in ['phone', 'tel', 'mobile']):
            return 'phone'
        
        # Check data patterns
        elif len(series.dropna()) > 0:
            sample_val = str(series.dropna().iloc[0])
            if '@' in sample_val and '.' in sample_val:
                return 'email'
            elif sample_val.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').isdigit():
                return 'phone'
        
        return 'general'
    
    def _categorize_csv_content(self) -> str:
        """Categorize CSV content based on column names"""
        if self.dataframe is None:
            return 'unknown'
        
        column_names = [str(col).lower() for col in self.dataframe.columns]
        all_columns = ' '.join(column_names)
        
        if any(keyword in all_columns for keyword in ['transaction', 'order', 'sale', 'payment']):
            return 'transaction'
        elif any(keyword in all_columns for keyword in ['customer', 'user', 'client', 'person']):
            return 'customer'
        elif any(keyword in all_columns for keyword in ['product', 'item', 'inventory', 'stock']):
            return 'product'
        elif any(keyword in all_columns for keyword in ['config', 'setting', 'parameter']):
            return 'configuration'
        elif any(keyword in all_columns for keyword in ['log', 'event', 'audit']):
            return 'log'
        else:
            return 'data'
    
    def _calculate_data_quality_score(self) -> float:
        """Calculate data quality score for CSV"""
        if self.dataframe is None or self.dataframe.empty:
            return 0.0
        
        df = self.dataframe
        total_cells = df.size
        null_cells = df.isnull().sum().sum()
        completeness = 1 - (null_cells / total_cells)
        
        # Check for duplicates
        duplicate_ratio = df.duplicated().sum() / len(df)
        uniqueness = 1 - duplicate_ratio
        
        # Simple quality score
        quality_score = (completeness * 0.7) + (uniqueness * 0.3)
        return round(quality_score, 2)
    
    def _identify_key_columns(self) -> List[str]:
        """Identify potential key columns"""
        if self.dataframe is None:
            return []
        
        key_columns = []
        df = self.dataframe
        
        for column in df.columns:
            column_lower = str(column).lower()
            series = df[column]
            
            # Check if column name suggests it's a key
            if any(keyword in column_lower for keyword in ['id', 'key', 'code']):
                key_columns.append(str(column))
            
            # Check if column has unique values (potential key)
            elif series.nunique() == len(series.dropna()) and len(series.dropna()) > 0:
                key_columns.append(str(column))
        
        return key_columns[:3]  # Return max 3 key columns
    
    def _get_sample_data_internal(self, section_name: str, limit: int) -> List[Dict[str, Any]]:
        """Get sample data from CSV"""
        if self.dataframe is None:
            return []
        
        sample_df = self.dataframe.head(limit)
        return sample_df.to_dict('records')
    
    def _analyze_column_distribution(self, section_name: str, column_name: str, sample_size: int) -> Dict[str, Any]:
        """Analyze column data distribution"""
        if self.dataframe is None:
            return {"error": "No data loaded"}
        
        if column_name not in self.dataframe.columns:
            return {"error": f"Column {column_name} not found"}
        
        series = self.dataframe[column_name]
        return self._analyze_column_data(series)
    
    def _compute_quality_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compute CSV-specific quality metrics"""
        if self.dataframe is None:
            return metrics
        
        df = self.dataframe
        
        metrics.update({
            'total_sections': 1,  # CSV is one section
            'total_columns': len(df.columns),
            'total_rows': len(df),
            'empty_sections': 1 if df.empty else 0,
            'columns_with_nulls': sum(1 for col in df.columns if df[col].isnull().any()),
            'duplicate_rows': df.duplicated().sum(),
            'encoding': self.encoding,
            'delimiter': self.delimiter
        })
        
        return metrics
    
    def _get_data_summary(self) -> Dict[str, Any]:
        """Get summary of CSV data"""
        if self.dataframe is None:
            return {}
        
        df = self.dataframe
        
        summary = {
            'rows': len(df),
            'columns': len(df.columns),
            'data_types': df.dtypes.value_counts().to_dict(),
            'memory_usage': df.memory_usage(deep=True).sum(),
            'csv_properties': {
                'delimiter': self.delimiter,
                'encoding': self.encoding,
                'has_header': self.csv_info.get('has_header', False)
            },
            'data_quality': {
                'null_percentage': df.isnull().sum().sum() / df.size if df.size > 0 else 0,
                'duplicate_percentage': df.duplicated().sum() / len(df) if len(df) > 0 else 0
            }
        }
        
        return summary
    
    def get_value_counts(self, column_name: str, top_n: int = 10) -> Dict[str, int]:
        """Get value counts for a specific column"""
        if self.dataframe is None or column_name not in self.dataframe.columns:
            return {}
        
        value_counts = self.dataframe[column_name].value_counts().head(top_n)
        return value_counts.to_dict()
    
    def export_filtered_data(self, output_path: str, filter_conditions: Optional[Dict[str, Any]] = None) -> bool:
        """Export filtered CSV data"""
        try:
            if self.dataframe is None:
                return False
            
            df = self.dataframe.copy()
            
            # Apply filters if provided
            if filter_conditions:
                for column, condition in filter_conditions.items():
                    if column in df.columns:
                        if isinstance(condition, dict):
                            if 'min' in condition:
                                df = df[df[column] >= condition['min']]
                            if 'max' in condition:
                                df = df[df[column] <= condition['max']]
                        else:
                            df = df[df[column] == condition]
            
            df.to_csv(output_path, index=False)
            return True
        except Exception:
            return False