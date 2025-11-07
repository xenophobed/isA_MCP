#!/usr/bin/env python3
"""
CSV file adapter for metadata extraction
"""

import csv
from typing import Dict, List, Any, Optional
from collections import Counter
from .base_adapter import FileAdapter
from .base_adapter import TableInfo, ColumnInfo

try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False

class CSVAdapter(FileAdapter):
    """CSV file adapter for .csv files"""

    def __init__(self):
        super().__init__()
        if not POLARS_AVAILABLE:
            raise ImportError("polars is required for CSV adapter. Install with: pip install polars")
        
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

            # Load CSV with detected parameters (Polars API)
            df = pl.read_csv(
                file_path,
                separator=self.delimiter,  # Polars uses 'separator' not 'delimiter'
                encoding=self.encoding,
                null_values=['', 'NULL', 'null', 'N/A', 'n/a', 'NA', '#N/A'],
                infer_schema_length=1000  # Polars schema inference
            )

            self.dataframe = df

            # Store CSV metadata
            self.csv_info = {
                'delimiter': self.delimiter,
                'encoding': self.encoding,
                'has_header': self._detect_header(df),
                'total_rows': df.height,  # Polars uses .height
                'total_columns': df.width  # Polars uses .width
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
    
    def _detect_header(self, df: pl.DataFrame) -> bool:
        """Detect if CSV has header row"""
        if df.height == 0:
            return False

        # Check if first row looks like headers (all strings, no duplicates)
        first_row = df.row(0) if df.height > 0 else []

        # If all values in first row are strings and they're unique, likely header
        if df.height > 1:
            try:
                # Filter out null values
                first_row_values = [val for val in first_row if val is not None]
                first_row_strings = all(isinstance(val, str) for val in first_row_values)
                first_row_unique = len(set(first_row_values)) == len(first_row_values)

                # Check if second row has different data types
                second_row = df.row(1)
                second_row_values = [val for val in second_row if val is not None]
                second_row_has_numbers = any(isinstance(val, (int, float)) for val in second_row_values)

                return first_row_strings and first_row_unique and second_row_has_numbers
            except Exception:
                pass

        # Check column names - if they look like generated names (column_0, column_1), probably no header
        generated_names = all(col.startswith('column_') and col[7:].isdigit() for col in df.columns)
        return not generated_names
    
    def _analyze_structure(self) -> Dict[str, Any]:
        """Analyze CSV file structure"""
        if self.dataframe is None:
            return {}

        df = self.dataframe

        # Count empty rows (all values are null)
        empty_rows = sum(1 for i in range(df.height) if all(val is None for val in df.row(i)))

        # Count empty columns (all values are null)
        empty_columns = sum(1 for col in df.columns if df[col].null_count() == df.height)

        structure = {
            'csv_info': self.csv_info,
            'rows': df.height,
            'columns': df.width,
            'column_names': list(df.columns),
            'data_types': {str(col): str(df[col].dtype) for col in df.columns},
            'empty_rows': empty_rows,
            'empty_columns': empty_columns,
            'duplicate_rows': int(df.is_duplicated().sum()),
            'memory_usage': df.estimated_size('b')  # bytes
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
            record_count=self.dataframe.height,
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
                data_type=self._map_polars_to_sql_type(column_series.dtype),
                max_length=data_analysis.get('max_length'),
                is_nullable=column_series.null_count() > 0,
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
    
    def _analyze_column_data(self, series: pl.Series) -> Dict[str, Any]:
        """Analyze polars series data"""
        analysis = {}

        # Basic stats
        total_count = series.len()
        null_count = series.null_count()  # This is already a scalar for Series
        non_null_series = series.drop_nulls()

        analysis['null_percentage'] = (null_count / total_count) if total_count > 0 else 0
        analysis['unique_count'] = non_null_series.n_unique()
        analysis['unique_percentage'] = analysis['unique_count'] / non_null_series.len() if non_null_series.len() > 0 else 0

        # Sample values
        sample_size = min(10, non_null_series.len())
        if sample_size > 0:
            analysis['sample_values'] = non_null_series.sample(n=sample_size).to_list()
        else:
            analysis['sample_values'] = []

        # Value range for numeric columns
        if series.dtype in [pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64, pl.Float32, pl.Float64]:
            if non_null_series.len() > 0:
                analysis['value_range'] = {
                    'min': float(non_null_series.min()),
                    'max': float(non_null_series.max()),
                    'mean': float(non_null_series.mean()),
                    'std': float(non_null_series.std()) if non_null_series.len() > 1 else 0
                }

        # Max length for string columns
        if series.dtype == pl.Utf8:
            string_lengths = non_null_series.str.len_chars()
            if string_lengths.len() > 0:
                analysis['max_length'] = int(string_lengths.max())
                analysis['avg_length'] = float(string_lengths.mean())
            else:
                analysis['max_length'] = 0
                analysis['avg_length'] = 0

        return analysis
    
    def _map_polars_to_sql_type(self, dtype) -> str:
        """Map polars dtype to SQL-like type"""
        if dtype in [pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64]:
            return 'integer'
        elif dtype in [pl.Float32, pl.Float64]:
            return 'decimal'
        elif dtype == pl.Boolean:
            return 'boolean'
        elif dtype in [pl.Date, pl.Datetime, pl.Time]:
            return 'timestamp'
        elif dtype == pl.Utf8:
            return 'text'
        else:
            return 'text'
    
    def _infer_business_type(self, column_name: str, series: pl.Series) -> str:
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
        elif series.drop_nulls().len() > 0:
            sample_val = str(series.drop_nulls()[0])
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
        if self.dataframe is None or self.dataframe.height == 0:
            return 0.0

        df = self.dataframe
        total_cells = df.height * df.width
        # polars null_count() returns DataFrame, need to sum horizontally then get total
        null_count_df = df.null_count()
        # Sum across all columns to get total null count
        null_cells = sum(null_count_df.row(0))  # Get first row and sum all values
        completeness = 1 - (null_cells / total_cells) if total_cells > 0 else 0

        # Check for duplicates
        duplicate_ratio = int(df.is_duplicated().sum()) / df.height if df.height > 0 else 0
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
            elif series.drop_nulls().n_unique() == series.drop_nulls().len() and series.drop_nulls().len() > 0:
                key_columns.append(str(column))

        return key_columns[:3]  # Return max 3 key columns
    
    def _get_sample_data_internal(self, section_name: str, limit: int) -> List[Dict[str, Any]]:
        """Get sample data from CSV"""
        if self.dataframe is None:
            return []

        try:
            sample_df = self.dataframe.head(limit)
            return sample_df.to_dicts()  # Polars uses to_dicts()
        except Exception as e:
            return [{"error": f"Failed to get sample data: {str(e)}"}]
    
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
            'total_columns': df.width,
            'total_rows': df.height,
            'empty_sections': 1 if df.height == 0 else 0,
            'columns_with_nulls': sum(1 for col in df.columns if df[col].null_count() > 0),
            'duplicate_rows': int(df.is_duplicated().sum()),
            'encoding': self.encoding,
            'delimiter': self.delimiter
        })

        return metrics
    
    def _get_data_summary(self) -> Dict[str, Any]:
        """Get summary of CSV data"""
        if self.dataframe is None:
            return {}

        df = self.dataframe

        # Count data types
        dtype_counts = {}
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            dtype_counts[dtype_str] = dtype_counts.get(dtype_str, 0) + 1

        summary = {
            'rows': df.height,
            'columns': df.width,
            'data_types': dtype_counts,
            'memory_usage': df.estimated_size('b'),
            'csv_properties': {
                'delimiter': self.delimiter,
                'encoding': self.encoding,
                'has_header': self.csv_info.get('has_header', False)
            },
            'data_quality': {
                'null_percentage': sum(df.null_count().row(0)) / (df.height * df.width) if (df.height * df.width) > 0 else 0,
                'duplicate_percentage': int(df.is_duplicated().sum()) / df.height if df.height > 0 else 0
            }
        }

        return summary
    
    def get_value_counts(self, column_name: str, top_n: int = 10) -> Dict[str, int]:
        """Get value counts for a specific column"""
        if self.dataframe is None or column_name not in self.dataframe.columns:
            return {}

        value_counts = self.dataframe[column_name].value_counts().head(top_n)
        # Convert to dict: Polars value_counts returns DataFrame with columns 'column_name' and 'counts'
        result = {}
        for row in value_counts.iter_rows():
            result[str(row[0])] = int(row[1])
        return result
    
    def export_filtered_data(self, output_path: str, filter_conditions: Optional[Dict[str, Any]] = None) -> bool:
        """Export filtered CSV data"""
        try:
            if self.dataframe is None:
                return False

            df = self.dataframe.clone()

            # Apply filters if provided
            if filter_conditions:
                for column, condition in filter_conditions.items():
                    if column in df.columns:
                        if isinstance(condition, dict):
                            if 'min' in condition:
                                df = df.filter(pl.col(column) >= condition['min'])
                            if 'max' in condition:
                                df = df.filter(pl.col(column) <= condition['max'])
                        else:
                            df = df.filter(pl.col(column) == condition)

            df.write_csv(output_path)
            return True
        except Exception:
            return False

    def validate_file_structure(self) -> Dict[str, Any]:
        """Validate CSV file structure and data quality - override to handle DataFrame check"""
        try:
            if self.dataframe is None or self.dataframe.height == 0:
                return {"valid": False, "error": "No data loaded"}

            validation_result = {
                "valid": True,
                "file_info": self.file_info,
                "structure_analysis": self._analyze_structure(),
                "data_quality": self._assess_data_quality()
            }

            return validation_result
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from CSV file - override to handle DataFrame check"""
        try:
            if self.dataframe is None or self.dataframe.height == 0:
                return []

            # For CSV, table_name is usually the filename (ignored)
            return self._get_sample_data_internal(table_name, limit)
        except Exception as e:
            return [{"error": str(e)}]