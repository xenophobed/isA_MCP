#!/usr/bin/env python3
"""
Metadata Extractor Service
A concrete service that extracts metadata from various data sources (CSV, DB, etc.)
Input: Data source (file path, connection string, etc.)
Output: Standardized metadata dictionary
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging

# Import specialized processors
try:
    from .csv_processor import CSVProcessor
except ImportError:
    from csv_processor import CSVProcessor

logger = logging.getLogger(__name__)

class MetadataExtractor:
    """
    Concrete metadata extraction service
    Supports multiple data source types and outputs standardized metadata
    """
    
    def __init__(self):
        self.supported_sources = {
            'csv': self._extract_csv_metadata,
            'excel': self._extract_excel_metadata,
            'json': self._extract_json_metadata,
            'database': self._extract_database_metadata
        }
        
    def extract_metadata(self, 
                        source_path: str, 
                        source_type: Optional[str] = None,
                        **kwargs) -> Dict[str, Any]:
        """
        Extract metadata from any supported data source
        
        Args:
            source_path: Path to data source (file path, connection string, etc.)
            source_type: Type of source ('csv', 'excel', 'json', 'database'). Auto-detected if None.
            **kwargs: Additional parameters for specific source types
            
        Returns:
            Standardized metadata dictionary
        """
        try:
            # Auto-detect source type if not provided
            if source_type is None:
                source_type = self._detect_source_type(source_path)
            
            # Validate source type
            if source_type not in self.supported_sources:
                return {
                    "error": f"Unsupported source type: {source_type}",
                    "supported_types": list(self.supported_sources.keys())
                }
            
            # Extract metadata using appropriate processor
            extraction_start = datetime.now()
            
            logger.info(f"Starting metadata extraction for {source_type}: {source_path}")
            
            # Call the appropriate extraction method
            metadata = self.supported_sources[source_type](source_path, **kwargs)
            
            extraction_end = datetime.now()
            extraction_duration = (extraction_end - extraction_start).total_seconds()
            
            # Add extraction metadata
            metadata.update({
                "extraction_info": {
                    "service": "MetadataExtractor",
                    "version": "1.0.0",
                    "source_type": source_type,
                    "source_path": source_path,
                    "extraction_time": extraction_end.isoformat(),
                    "extraction_duration_seconds": round(extraction_duration, 3),
                    "success": True
                }
            })
            
            logger.info(f"Metadata extraction completed in {extraction_duration:.3f} seconds")
            return metadata
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return {
                "error": str(e),
                "extraction_info": {
                    "service": "MetadataExtractor",
                    "version": "1.0.0",
                    "source_type": source_type,
                    "source_path": source_path,
                    "extraction_time": datetime.now().isoformat(),
                    "success": False
                }
            }
    
    def _detect_source_type(self, source_path: str) -> str:
        """
        Auto-detect source type from path/extension
        
        Args:
            source_path: Path to data source
            
        Returns:
            Detected source type
        """
        if isinstance(source_path, str):
            path = Path(source_path)
            
            if path.exists() and path.is_file():
                extension = path.suffix.lower()
                
                if extension == '.csv':
                    return 'csv'
                elif extension in ['.xlsx', '.xls']:
                    return 'excel'
                elif extension == '.json':
                    return 'json'
            
            # Check if it looks like a database connection string
            if any(db_indicator in source_path.lower() for db_indicator in ['postgresql://', 'mysql://', 'sqlite://', 'oracle://']):
                return 'database'
        
        # Default to CSV if uncertain
        return 'csv'
    
    def _extract_csv_metadata(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Extract metadata from CSV file
        
        Args:
            file_path: Path to CSV file
            **kwargs: Additional CSV processing parameters
            
        Returns:
            CSV metadata dictionary
        """
        processor = CSVProcessor(file_path)
        csv_analysis = processor.get_full_analysis()
        
        if "error" in csv_analysis:
            return csv_analysis
        
        # Transform to standardized format
        return self._standardize_metadata(csv_analysis, "csv")
    
    def _extract_excel_metadata(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Extract metadata from Excel file
        
        Args:
            file_path: Path to Excel file
            **kwargs: Additional Excel processing parameters
            
        Returns:
            Excel metadata dictionary
        """
        try:
            import pandas as pd
            
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            
            metadata = {
                "file_info": {
                    "file_name": Path(file_path).name,
                    "file_path": file_path,
                    "file_type": "excel",
                    "sheet_names": excel_file.sheet_names,
                    "total_sheets": len(excel_file.sheet_names)
                },
                "sheets": []
            }
            
            # Analyze each sheet
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    sheet_analysis = {
                        "sheet_name": sheet_name,
                        "total_rows": len(df),
                        "total_columns": len(df.columns),
                        "column_names": list(df.columns),
                        "column_types": {col: str(df[col].dtype) for col in df.columns}
                    }
                    
                    metadata["sheets"].append(sheet_analysis)
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze sheet {sheet_name}: {e}")
            
            return self._standardize_metadata(metadata, "excel")
            
        except Exception as e:
            return {"error": f"Failed to process Excel file: {e}"}
    
    def _extract_json_metadata(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Extract metadata from JSON file
        
        Args:
            file_path: Path to JSON file
            **kwargs: Additional JSON processing parameters
            
        Returns:
            JSON metadata dictionary
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            file_stats = Path(file_path).stat()
            
            metadata = {
                "file_info": {
                    "file_name": Path(file_path).name,
                    "file_path": file_path,
                    "file_type": "json",
                    "file_size_bytes": file_stats.st_size,
                    "file_size_mb": round(file_stats.st_size / (1024 * 1024), 2)
                },
                "structure": self._analyze_json_structure(data),
                "schema": self._infer_json_schema(data)
            }
            
            return self._standardize_metadata(metadata, "json")
            
        except Exception as e:
            return {"error": f"Failed to process JSON file: {e}"}
    
    def _extract_database_metadata(self, connection_string: str, **kwargs) -> Dict[str, Any]:
        """
        Extract metadata from database
        
        Args:
            connection_string: Database connection string
            **kwargs: Additional database parameters
            
        Returns:
            Database metadata dictionary
        """
        # This would require database-specific implementations
        # For now, return a placeholder
        return {
            "error": "Database metadata extraction not yet implemented",
            "connection_string": connection_string,
            "note": "This feature requires database-specific adapters"
        }
    
    def _standardize_metadata(self, raw_metadata: Dict[str, Any], source_type: str) -> Dict[str, Any]:
        """
        Standardize metadata format across different source types
        
        Args:
            raw_metadata: Raw metadata from source-specific processor
            source_type: Type of data source
            
        Returns:
            Standardized metadata dictionary
        """
        standardized = {
            "source_info": {
                "type": source_type,
                "analysis_timestamp": datetime.now().isoformat()
            },
            "tables": [],
            "columns": [],
            "data_quality": {},
            "business_patterns": {},
            "sample_data": [],
            "raw_metadata": raw_metadata
        }
        
        if source_type == "csv":
            standardized.update(self._standardize_csv_metadata(raw_metadata))
        elif source_type == "excel":
            standardized.update(self._standardize_excel_metadata(raw_metadata))
        elif source_type == "json":
            standardized.update(self._standardize_json_metadata(raw_metadata))
        
        return standardized
    
    def _standardize_csv_metadata(self, csv_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize CSV metadata"""
        if "error" in csv_metadata:
            return {"error": csv_metadata["error"]}
        
        # Extract file info
        file_info = csv_metadata.get("file_info", {})
        structure = csv_metadata.get("structure", {})
        columns = csv_metadata.get("columns", [])
        
        # Create standardized table entry
        table_info = {
            "table_name": file_info.get("file_name", "unknown").replace('.csv', ''),
            "table_type": "file",
            "record_count": structure.get("total_rows", 0),
            "column_count": structure.get("total_columns", 0),
            "file_size_mb": file_info.get("file_size_mb", 0),
            "created_date": file_info.get("created_time"),
            "modified_date": file_info.get("modified_time")
        }
        
        # Create standardized column entries
        standardized_columns = []
        for col in columns:
            standardized_col = {
                "table_name": table_info["table_name"],
                "column_name": col.get("column_name"),
                "data_type": col.get("data_type"),
                "business_type": col.get("business_type"),
                "ordinal_position": col.get("ordinal_position"),
                "is_nullable": col.get("null_count", 0) > 0,
                "null_percentage": col.get("null_percentage", 0),
                "unique_count": col.get("unique_count", 0),
                "unique_percentage": col.get("unique_percentage", 0),
                "sample_values": col.get("sample_values", [])
            }
            
            # Add type-specific statistics
            if "min_value" in col:
                standardized_col.update({
                    "min_value": col.get("min_value"),
                    "max_value": col.get("max_value"),
                    "mean_value": col.get("mean_value"),
                    "median_value": col.get("median_value")
                })
            
            if "avg_length" in col:
                standardized_col.update({
                    "avg_length": col.get("avg_length"),
                    "min_length": col.get("min_length"),
                    "max_length": col.get("max_length"),
                    "most_common": col.get("most_common", {})
                })
            
            standardized_columns.append(standardized_col)
        
        return {
            "source_info": {
                "file_path": file_info.get("file_path"),
                "file_size_mb": file_info.get("file_size_mb"),
                "total_rows": structure.get("total_rows"),
                "total_columns": structure.get("total_columns"),
                "has_duplicates": structure.get("has_duplicates", False)
            },
            "tables": [table_info],
            "columns": standardized_columns,
            "data_quality": csv_metadata.get("data_quality", {}),
            "business_patterns": csv_metadata.get("patterns", {}),
            "sample_data": csv_metadata.get("sample_data", [])
        }
    
    def _standardize_excel_metadata(self, excel_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize Excel metadata"""
        if "error" in excel_metadata:
            return {"error": excel_metadata["error"]}
        
        file_info = excel_metadata.get("file_info", {})
        sheets = excel_metadata.get("sheets", [])
        
        # Create table entries for each sheet
        tables = []
        columns = []
        
        for sheet in sheets:
            table_info = {
                "table_name": sheet.get("sheet_name"),
                "table_type": "sheet",
                "record_count": sheet.get("total_rows", 0),
                "column_count": sheet.get("total_columns", 0)
            }
            tables.append(table_info)
            
            # Create column entries
            for idx, col_name in enumerate(sheet.get("column_names", [])):
                col_type = sheet.get("column_types", {}).get(col_name, "unknown")
                
                column_info = {
                    "table_name": sheet.get("sheet_name"),
                    "column_name": col_name,
                    "data_type": col_type,
                    "ordinal_position": idx + 1
                }
                columns.append(column_info)
        
        return {
            "source_info": {
                "file_path": file_info.get("file_path"),
                "total_sheets": file_info.get("total_sheets"),
                "sheet_names": file_info.get("sheet_names", [])
            },
            "tables": tables,
            "columns": columns
        }
    
    def _standardize_json_metadata(self, json_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize JSON metadata"""
        if "error" in json_metadata:
            return {"error": json_metadata["error"]}
        
        file_info = json_metadata.get("file_info", {})
        structure = json_metadata.get("structure", {})
        
        return {
            "source_info": {
                "file_path": file_info.get("file_path"),
                "file_size_mb": file_info.get("file_size_mb"),
                "json_type": structure.get("type"),
                "total_keys": structure.get("total_keys", 0)
            },
            "schema": json_metadata.get("schema", {})
        }
    
    def _analyze_json_structure(self, data: Any) -> Dict[str, Any]:
        """Analyze JSON structure"""
        if isinstance(data, dict):
            return {
                "type": "object",
                "total_keys": len(data),
                "keys": list(data.keys())[:20],  # Limit to first 20 keys
                "nested_levels": self._calculate_json_depth(data)
            }
        elif isinstance(data, list):
            return {
                "type": "array",
                "length": len(data),
                "item_types": list(set(type(item).__name__ for item in data[:100]))  # Sample first 100 items
            }
        else:
            return {
                "type": type(data).__name__,
                "value": str(data)[:100]  # Truncate long values
            }
    
    def _calculate_json_depth(self, obj: Any, depth: int = 0) -> int:
        """Calculate maximum depth of JSON structure"""
        if isinstance(obj, dict):
            if not obj:
                return depth
            return max(self._calculate_json_depth(value, depth + 1) for value in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return depth
            return max(self._calculate_json_depth(item, depth + 1) for item in obj)
        else:
            return depth
    
    def _infer_json_schema(self, data: Any) -> Dict[str, Any]:
        """Infer JSON schema"""
        if isinstance(data, dict):
            schema = {
                "type": "object",
                "properties": {}
            }
            for key, value in data.items():
                schema["properties"][key] = self._infer_json_schema(value)
            return schema
        elif isinstance(data, list):
            if data:
                # Infer schema from first item
                return {
                    "type": "array",
                    "items": self._infer_json_schema(data[0])
                }
            return {"type": "array"}
        elif isinstance(data, str):
            return {"type": "string"}
        elif isinstance(data, int):
            return {"type": "integer"}
        elif isinstance(data, float):
            return {"type": "number"}
        elif isinstance(data, bool):
            return {"type": "boolean"}
        elif data is None:
            return {"type": "null"}
        else:
            return {"type": "unknown"}
    
    def get_supported_sources(self) -> List[str]:
        """Get list of supported data source types"""
        return list(self.supported_sources.keys())
    
    def save_metadata(self, metadata: Dict[str, Any], output_path: str) -> bool:
        """
        Save metadata to JSON file
        
        Args:
            metadata: Metadata dictionary to save
            output_path: Path to save the metadata
            
        Returns:
            Success status
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Metadata saved to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            return False

# Convenience function for simple usage
def extract_metadata(source_path: str, source_type: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to extract metadata
    
    Args:
        source_path: Path to data source
        source_type: Type of source (auto-detected if None)
        **kwargs: Additional parameters
        
    Returns:
        Metadata dictionary
    """
    extractor = MetadataExtractor()
    return extractor.extract_metadata(source_path, source_type, **kwargs)