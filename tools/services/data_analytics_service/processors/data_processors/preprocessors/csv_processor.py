#!/usr/bin/env python3
"""
CSV Processor
Handles CSV file preprocessing and analysis for metadata extraction
"""

import polars as pl
# import sqlite3  # Deprecated - using DuckDB instead
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class CSVProcessor:
    """CSV file processor for metadata extraction"""
    
    def __init__(self, file_path: str, user_id: Optional[str] = None):
        self.file_path = Path(file_path)
        self.df = None
        self.user_id = user_id
        self.duckdb_path = None  # Using DuckDB instead of SQLite
        
    def load_csv(self, **kwargs) -> bool:
        """Load CSV file with error handling"""
        try:
            # Map pandas-style params to polars
            null_values = kwargs.pop('na_values', ['', 'NULL', 'null', 'None', 'N/A', 'n/a'])
            encoding = kwargs.pop('encoding', 'utf-8')
            # Ignore pandas-specific params
            kwargs.pop('keep_default_na', None)
            kwargs.pop('low_memory', None)

            self.df = pl.read_csv(
                self.file_path,
                null_values=null_values,
                encoding=encoding,
                **kwargs
            )
            logger.info(f"Successfully loaded CSV: {self.file_path.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load CSV {self.file_path}: {e}")
            return False
    
    def get_full_analysis(self) -> Dict[str, Any]:
        """Get complete CSV analysis"""
        if not self.load_csv():
            return {"error": "Failed to load CSV file"}
        
        return {
            "file_info": self.analyze_file_info(),
            "structure": self.analyze_structure(), 
            "columns": self.analyze_columns(),
            "data_quality": self.analyze_data_quality(),
            "patterns": self.detect_patterns(),
            "sample_data": self.get_sample_data(),
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def analyze_file_info(self) -> Dict[str, Any]:
        """Analyze basic file information"""
        if not self.file_path.exists():
            return {"error": "File does not exist"}
        
        file_stats = self.file_path.stat()
        return {
            "file_name": self.file_path.name,
            "file_path": str(self.file_path),
            "file_size_bytes": file_stats.st_size,
            "file_size_mb": round(file_stats.st_size / (1024 * 1024), 2),
            "created_time": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
            "modified_time": datetime.fromtimestamp(file_stats.st_mtime).isoformat()
        }
    
    def analyze_structure(self) -> Dict[str, Any]:
        """Analyze CSV structure"""
        if self.df is None:
            return {"error": "CSV not loaded"}

        return {
            "total_rows": self.df.height,
            "total_columns": self.df.width,
            "column_names": self.df.columns,
            "memory_usage_mb": round(self.df.estimated_size("mb"), 2),
            "has_duplicates": self.df.is_duplicated().any(),
            "duplicate_count": self.df.is_duplicated().sum()
        }
    
    def analyze_columns(self) -> List[Dict[str, Any]]:
        """Analyze each column in detail"""
        if self.df is None:
            return []

        columns_analysis = []

        for idx, column_name in enumerate(self.df.columns):
            column_data = self.df[column_name]

            null_count = column_data.null_count()
            unique_count = column_data.n_unique()
            total_values = self.df.height

            analysis = {
                "column_name": column_name,
                "ordinal_position": idx + 1,
                "data_type": str(column_data.dtype),
                "total_values": total_values,
                "null_count": null_count,
                "null_percentage": round((null_count / total_values) * 100, 2) if total_values > 0 else 0,
                "unique_count": unique_count,
                "unique_percentage": round((unique_count / total_values) * 100, 2) if total_values > 0 else 0,
                "business_type": self._infer_business_type(column_name, column_data),
                "sample_values": self._get_sample_values(column_data)
            }

            # Add type-specific analysis
            if column_data.dtype in [pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64, pl.Float32, pl.Float64]:
                analysis.update(self._analyze_numeric_column(column_data))
            elif column_data.dtype in [pl.Utf8, pl.String]:
                analysis.update(self._analyze_text_column(column_data))

            columns_analysis.append(analysis)

        return columns_analysis
    
    def _infer_business_type(self, column_name: str, column_data: pl.Series) -> str:
        """Infer business type from column name and data"""
        name_lower = column_name.lower()

        if any(pattern in name_lower for pattern in ['id', '_id', 'identifier']):
            return 'identifier'
        elif any(pattern in name_lower for pattern in ['name', 'title', 'label']):
            return 'name'
        elif 'email' in name_lower:
            return 'email'
        elif any(pattern in name_lower for pattern in ['phone', 'tel', 'mobile']):
            return 'phone'
        elif any(pattern in name_lower for pattern in ['address', 'city', 'country', 'state']):
            return 'address'
        elif any(pattern in name_lower for pattern in ['date', 'time', 'created', 'updated']):
            return 'temporal'
        elif any(pattern in name_lower for pattern in ['price', 'amount', 'cost', 'value']):
            return 'monetary'
        elif any(pattern in name_lower for pattern in ['quantity', 'count', 'stock']):
            return 'quantity'
        elif column_data.dtype == pl.Boolean:
            return 'boolean'
        elif column_data.dtype in [pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64, pl.Float32, pl.Float64]:
            return 'numeric'
        else:
            return 'text'
    
    def _analyze_numeric_column(self, column_data: pl.Series) -> Dict[str, Any]:
        """Analyze numeric column"""
        try:
            return {
                "min_value": float(column_data.min()) if column_data.len() > 0 else None,
                "max_value": float(column_data.max()) if column_data.len() > 0 else None,
                "mean_value": float(column_data.mean()) if column_data.len() > 0 else None,
                "median_value": float(column_data.median()) if column_data.len() > 0 else None
            }
        except Exception:
            return {}
    
    def _analyze_text_column(self, column_data: pl.Series) -> Dict[str, Any]:
        """Analyze text column"""
        try:
            text_data = column_data.drop_nulls().cast(pl.Utf8)
            if text_data.len() == 0:
                return {}

            str_lengths = text_data.str.len_chars()
            value_counts = column_data.value_counts().head(3)

            return {
                "avg_length": float(str_lengths.mean()),
                "min_length": int(str_lengths.min()),
                "max_length": int(str_lengths.max()),
                "most_common": {str(row[0]): int(row[1]) for row in value_counts.iter_rows()}
            }
        except Exception:
            return {}
    
    def _get_sample_values(self, column_data: pl.Series, limit: int = 3) -> List[Any]:
        """Get sample values from column"""
        try:
            non_null_data = column_data.drop_nulls()
            if non_null_data.len() == 0:
                return []

            unique_values = non_null_data.unique()
            sample_size = min(limit, unique_values.len())
            return unique_values[:sample_size].to_list()
        except Exception:
            return []
    
    def analyze_data_quality(self) -> Dict[str, Any]:
        """Analyze overall data quality"""
        if self.df is None:
            return {"error": "CSV not loaded"}

        total_cells = self.df.height * self.df.width
        # null_count() returns a DataFrame with counts per column, we need to sum them
        null_cells = self.df.null_count().sum_horizontal()[0]  # Get scalar value

        overall_quality = 1.0 - (null_cells / total_cells) if total_cells > 0 else 0.0

        return {
            "overall_quality_score": round(overall_quality, 3),
            "completeness_percentage": round((1 - null_cells / total_cells) * 100, 2) if total_cells > 0 else 0,
            "total_cells": total_cells,
            "null_cells": int(null_cells)
        }
    
    def detect_patterns(self) -> Dict[str, Any]:
        """Detect patterns and business domain indicators"""
        if self.df is None:
            return {"error": "CSV not loaded"}
        
        # Domain keywords
        domain_indicators = {
            "ecommerce": ["product", "order", "cart", "price", "inventory", "customer"],
            "finance": ["amount", "balance", "transaction", "payment", "account"],
            "hr": ["employee", "salary", "department", "staff"],
            "crm": ["customer", "contact", "lead", "sales"]
        }
        
        # Check column names for domain indicators
        all_text = ' '.join(self.df.columns).lower()
        
        domain_scores = {}
        for domain, keywords in domain_indicators.items():
            score = sum(1 for keyword in keywords if keyword in all_text)
            domain_scores[domain] = score
        
        primary_domain = max(domain_scores.items(), key=lambda x: x[1]) if domain_scores else ("unknown", 0)
        
        return {
            "domain_scores": domain_scores,
            "primary_domain": primary_domain[0],
            "confidence": min(primary_domain[1] / len(self.df.columns), 1.0) if len(self.df.columns) > 0 else 0
        }
    
    def get_sample_data(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample data from CSV"""
        if self.df is None:
            return []

        sample_df = self.df.head(limit)
        return sample_df.to_dicts()
    
    def save_to_sqlite(self, table_name: Optional[str] = None, if_exists: str = 'replace') -> Dict[str, Any]:
        """
        DEPRECATED: Save CSV data to database (now using DuckDB instead of SQLite)
        
        Args:
            table_name: Name for the table (defaults to CSV filename without extension)
            if_exists: What to do if table exists ('fail', 'replace', 'append')
            
        Returns:
            Dictionary with database information
        """
        logger.warning("save_to_sqlite is deprecated. DuckDB can read CSV files directly without conversion.")
        
        # Return info about the CSV file itself since DuckDB can query it directly
        if self.df is None:
            if not self.load_csv():
                return {"error": "Failed to load CSV data"}
        
        csv_name = self.file_path.stem
        if table_name is None:
            table_name = csv_name.lower().replace('-', '_').replace(' ', '_')
        
        return {
            "success": True,
            "csv_path": str(self.file_path),
            "table_name": table_name,
            "row_count": self.df.height,
            "columns": [{"name": col, "type": str(self.df[col].dtype)} for col in self.df.columns],
            "note": "Use DuckDB to query this CSV directly: SELECT * FROM 'path/to/file.csv'"
        }
    
    def get_sqlite_connection(self):
        """DEPRECATED: Use DuckDB instead"""
        logger.warning("get_sqlite_connection is deprecated. Use DuckDB for better performance.")
        return None
    
    def get_database_metadata(self) -> Dict[str, Any]:
        """Get metadata about the CSV for database operations"""
        if self.df is None:
            if not self.load_csv():
                return {"error": "Failed to load CSV data"}
        
        csv_name = self.file_path.stem
        table_name = csv_name.lower().replace('-', '_').replace(' ', '_')
        
        return {
            "csv_path": str(self.file_path),
            "database_type": "duckdb",
            "tables": [{
                "table_name": table_name,
                "record_count": self.df.height,
                "columns": [
                    {
                        "column_name": col,
                        "data_type": str(self.df[col].dtype),
                        "ordinal_position": idx,
                        "is_nullable": bool(self.df[col].null_count() > 0),
                        "column_default": None,
                        "is_primary_key": False
                    }
                    for idx, col in enumerate(self.df.columns, 1)
                ]
            }],
            "total_tables": 1,
            "query_example": f"SELECT * FROM '{self.file_path}' LIMIT 10"
        }
    
    def get_full_analysis_with_sqlite(self, save_to_sqlite: bool = True) -> Dict[str, Any]:
        """Get complete analysis (SQLite deprecated, using DuckDB metadata)"""
        analysis = self.get_full_analysis()
        
        if analysis.get("file_info") and "error" not in analysis:
            analysis["database_metadata"] = self.get_database_metadata()
            analysis["duckdb_note"] = "Use DuckDB to query CSV directly without conversion"
        
        return analysis