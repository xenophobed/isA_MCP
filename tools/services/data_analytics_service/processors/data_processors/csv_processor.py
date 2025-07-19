#!/usr/bin/env python3
"""
CSV Processor
Handles CSV file preprocessing and analysis for metadata extraction
"""

import pandas as pd
import sqlite3
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
        self.sqlite_db_path = None
        
        # Get path to resources/dbs/sqlite directory
        current_dir = Path(__file__).resolve()
        project_root = current_dir
        while project_root.name != "isA_MCP":
            project_root = project_root.parent
            if project_root == project_root.parent:  # Reached filesystem root
                break
        
        self.sqlite_base_dir = project_root / "resources" / "dbs" / "sqlite"
        self.sqlite_base_dir.mkdir(parents=True, exist_ok=True)
        
    def load_csv(self, **kwargs) -> bool:
        """Load CSV file with error handling"""
        try:
            default_params = {
                'encoding': 'utf-8',
                'na_values': ['', 'NULL', 'null', 'None', 'N/A', 'n/a'],
                'keep_default_na': True,
                'low_memory': False
            }
            default_params.update(kwargs)
            
            self.df = pd.read_csv(self.file_path, **default_params)
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
            "total_rows": len(self.df),
            "total_columns": len(self.df.columns),
            "column_names": list(self.df.columns),
            "memory_usage_mb": round(self.df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
            "has_duplicates": bool(self.df.duplicated().any()),
            "duplicate_count": int(self.df.duplicated().sum())
        }
    
    def analyze_columns(self) -> List[Dict[str, Any]]:
        """Analyze each column in detail"""
        if self.df is None:
            return []
        
        columns_analysis = []
        
        for idx, column_name in enumerate(self.df.columns):
            column_data = self.df[column_name]
            
            analysis = {
                "column_name": column_name,
                "ordinal_position": idx + 1,
                "data_type": str(column_data.dtype),
                "total_values": len(column_data),
                "null_count": int(column_data.isnull().sum()),
                "null_percentage": round((column_data.isnull().sum() / len(column_data)) * 100, 2),
                "unique_count": int(column_data.nunique()),
                "unique_percentage": round((column_data.nunique() / len(column_data)) * 100, 2),
                "business_type": self._infer_business_type(column_name, column_data),
                "sample_values": self._get_sample_values(column_data)
            }
            
            # Add type-specific analysis
            if pd.api.types.is_numeric_dtype(column_data):
                analysis.update(self._analyze_numeric_column(column_data))
            elif pd.api.types.is_string_dtype(column_data) or pd.api.types.is_object_dtype(column_data):
                analysis.update(self._analyze_text_column(column_data))
            
            columns_analysis.append(analysis)
        
        return columns_analysis
    
    def _infer_business_type(self, column_name: str, column_data: pd.Series) -> str:
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
        elif pd.api.types.is_bool_dtype(column_data):
            return 'boolean'
        elif pd.api.types.is_numeric_dtype(column_data):
            return 'numeric'
        else:
            return 'text'
    
    def _analyze_numeric_column(self, column_data: pd.Series) -> Dict[str, Any]:
        """Analyze numeric column"""
        try:
            return {
                "min_value": float(column_data.min()) if not column_data.empty else None,
                "max_value": float(column_data.max()) if not column_data.empty else None,
                "mean_value": float(column_data.mean()) if not column_data.empty else None,
                "median_value": float(column_data.median()) if not column_data.empty else None
            }
        except Exception:
            return {}
    
    def _analyze_text_column(self, column_data: pd.Series) -> Dict[str, Any]:
        """Analyze text column"""
        try:
            text_data = column_data.dropna().astype(str)
            if text_data.empty:
                return {}
            
            return {
                "avg_length": float(text_data.str.len().mean()),
                "min_length": int(text_data.str.len().min()),
                "max_length": int(text_data.str.len().max()),
                "most_common": dict(column_data.value_counts().head(3))
            }
        except Exception:
            return {}
    
    def _get_sample_values(self, column_data: pd.Series, limit: int = 3) -> List[Any]:
        """Get sample values from column"""
        try:
            non_null_data = column_data.dropna()
            if non_null_data.empty:
                return []
            
            unique_values = non_null_data.unique()
            sample_size = min(limit, len(unique_values))
            return unique_values[:sample_size].tolist()
        except Exception:
            return []
    
    def analyze_data_quality(self) -> Dict[str, Any]:
        """Analyze overall data quality"""
        if self.df is None:
            return {"error": "CSV not loaded"}
        
        total_cells = len(self.df) * len(self.df.columns)
        null_cells = self.df.isnull().sum().sum()
        
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
        return sample_df.to_dict('records')
    
    def save_to_sqlite(self, table_name: Optional[str] = None, if_exists: str = 'replace') -> Dict[str, Any]:
        """
        Save CSV data to SQLite database in resources/dbs/sqlite
        
        Args:
            table_name: Name for the table (defaults to CSV filename without extension)
            if_exists: What to do if table exists ('fail', 'replace', 'append')
            
        Returns:
            Dictionary with database information
        """
        if self.df is None:
            if not self.load_csv():
                return {"error": "Failed to load CSV data"}
        
        try:
            # Generate database filename
            csv_name = self.file_path.stem  # filename without extension
            if self.user_id:
                db_filename = f"user_{self.user_id}_{csv_name}.db"
            else:
                db_filename = f"{csv_name}.db"
            
            self.sqlite_db_path = self.sqlite_base_dir / db_filename
            
            # Default table name to CSV filename
            if table_name is None:
                table_name = csv_name.lower().replace('-', '_').replace(' ', '_')
            
            # Connect and save data
            with sqlite3.connect(self.sqlite_db_path) as conn:
                # Save DataFrame to SQLite
                self.df.to_sql(table_name, conn, if_exists=if_exists, index=False)
                
                # Get table info for verification
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns_info = cursor.fetchall()
                
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
            
            logger.info(f"Successfully saved CSV to SQLite: {self.sqlite_db_path}")
            
            return {
                "success": True,
                "database_path": str(self.sqlite_db_path),
                "table_name": table_name,
                "row_count": row_count,
                "columns": [{"name": col[1], "type": col[2]} for col in columns_info],
                "database_size_mb": round(self.sqlite_db_path.stat().st_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to save CSV to SQLite: {e}")
            return {"error": str(e)}
    
    def get_sqlite_connection(self) -> Optional[sqlite3.Connection]:
        """Get connection to the SQLite database"""
        if self.sqlite_db_path and self.sqlite_db_path.exists():
            return sqlite3.connect(self.sqlite_db_path)
        return None
    
    def get_database_metadata(self) -> Dict[str, Any]:
        """Get metadata about the SQLite database for SQL executor"""
        if not self.sqlite_db_path or not self.sqlite_db_path.exists():
            return {"error": "No SQLite database available"}
        
        try:
            with sqlite3.connect(self.sqlite_db_path) as conn:
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                table_names = [row[0] for row in cursor.fetchall()]
                
                tables_metadata = []
                for table_name in table_names:
                    # Get table info
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns_info = cursor.fetchall()
                    
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    
                    table_metadata = {
                        "table_name": table_name,
                        "record_count": row_count,
                        "columns": [
                            {
                                "column_name": col[1],
                                "data_type": col[2],
                                "ordinal_position": col[0],
                                "is_nullable": col[3] == 0,  # NOT NULL = 0
                                "column_default": col[4],
                                "is_primary_key": col[5] == 1
                            }
                            for col in columns_info
                        ]
                    }
                    tables_metadata.append(table_metadata)
                
                return {
                    "database_path": str(self.sqlite_db_path),
                    "database_type": "sqlite",
                    "tables": tables_metadata,
                    "total_tables": len(tables_metadata)
                }
                
        except Exception as e:
            logger.error(f"Failed to get database metadata: {e}")
            return {"error": str(e)}
    
    def get_full_analysis_with_sqlite(self, save_to_sqlite: bool = True) -> Dict[str, Any]:
        """Get complete analysis including SQLite database creation"""
        analysis = self.get_full_analysis()
        
        if save_to_sqlite and analysis.get("file_info") and "error" not in analysis:
            sqlite_result = self.save_to_sqlite()
            analysis["sqlite_database"] = sqlite_result
            
            if sqlite_result.get("success"):
                analysis["database_metadata"] = self.get_database_metadata()
        
        return analysis