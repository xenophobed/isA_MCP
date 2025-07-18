#!/usr/bin/env python3
"""
Base file adapter abstract class
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path
from ...processors.data_processors.metadata_extractor import MetadataExtractor, TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

class FileAdapter(MetadataExtractor):
    """Abstract base class for file adapters"""
    
    def __init__(self):
        self.file_path = None
        self.file_info = None
        self.data = None
    
    @abstractmethod
    def _load_file(self, file_path: str) -> Any:
        """Load file content - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def _analyze_structure(self) -> Dict[str, Any]:
        """Analyze file structure - must be implemented by subclasses"""
        pass
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """Load and analyze file"""
        try:
            self.file_path = config['file_path']
            
            # Validate file exists
            if not Path(self.file_path).exists():
                raise FileNotFoundError(f"File not found: {self.file_path}")
            
            # Load file
            self.data = self._load_file(self.file_path)
            
            # Get file info
            file_stat = Path(self.file_path).stat()
            self.file_info = {
                "file_path": self.file_path,
                "file_name": Path(self.file_path).name,
                "file_size": file_stat.st_size,
                "created_time": file_stat.st_ctime,
                "modified_time": file_stat.st_mtime,
                "file_type": self.__class__.__name__.replace('Adapter', '').lower()
            }
            
            return True
        except Exception as e:
            print(f"File loading failed: {e}")
            return False
    
    def disconnect(self) -> None:
        """Clean up file resources"""
        self.file_path = None
        self.file_info = None
        self.data = None
    
    def get_file_info(self) -> Dict[str, Any]:
        """Get file information"""
        return self.file_info or {}
    
    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from file"""
        try:
            if not self.data:
                return []
            
            # For files, table_name usually refers to sheet/section name
            return self._get_sample_data_internal(table_name, limit)
        except Exception as e:
            return [{"error": str(e)}]
    
    @abstractmethod
    def _get_sample_data_internal(self, section_name: str, limit: int) -> List[Dict[str, Any]]:
        """Internal method to get sample data"""
        pass
    
    def get_relationships(self) -> List[RelationshipInfo]:
        """Files typically don't have explicit relationships"""
        return []
    
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Files typically don't have indexes"""
        return []
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze data distribution in file"""
        try:
            return self._analyze_column_distribution(table_name, column_name, sample_size)
        except Exception as e:
            return {"error": str(e), "analysis_failed": True}
    
    @abstractmethod
    def _analyze_column_distribution(self, section_name: str, column_name: str, sample_size: int) -> Dict[str, Any]:
        """Internal method to analyze column distribution"""
        pass
    
    def validate_file_structure(self) -> Dict[str, Any]:
        """Validate file structure and data quality"""
        try:
            if not self.data:
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
    
    def _assess_data_quality(self) -> Dict[str, Any]:
        """Assess data quality metrics"""
        try:
            quality_metrics = {
                "total_sections": 0,
                "total_columns": 0,
                "total_rows": 0,
                "empty_sections": 0,
                "columns_with_nulls": 0,
                "data_type_consistency": {}
            }
            
            # This will be implemented by subclasses
            return self._compute_quality_metrics(quality_metrics)
        except Exception as e:
            return {"error": str(e)}
    
    @abstractmethod
    def _compute_quality_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compute specific quality metrics for file type"""
        pass
    
    def get_file_statistics(self) -> Dict[str, Any]:
        """Get comprehensive file statistics"""
        try:
            if not self.data:
                return {"error": "No data loaded"}
            
            stats = {
                "file_info": self.file_info,
                "structure_info": self._analyze_structure(),
                "data_summary": self._get_data_summary()
            }
            
            return stats
        except Exception as e:
            return {"error": str(e)}
    
    @abstractmethod
    def _get_data_summary(self) -> Dict[str, Any]:
        """Get summary of data content"""
        pass
    
    def export_metadata_to_dict(self) -> Dict[str, Any]:
        """Export all metadata as dictionary"""
        try:
            metadata = {
                "source_info": {
                    "type": "file",
                    "subtype": self.__class__.__name__.replace('Adapter', '').lower(),
                    "file_path": self.file_path,
                    "extraction_time": self._get_current_timestamp()
                },
                "file_info": self.file_info,
                "tables": [],
                "columns": [],
                "relationships": [],
                "indexes": [],
                "data_analysis": {},
                "structure_analysis": self._analyze_structure()
            }
            
            # Get table-like structures
            tables = self.get_tables()
            metadata["tables"] = [self._table_to_dict(t) for t in tables]
            
            # Get column information
            columns = self.get_columns()
            metadata["columns"] = [self._column_to_dict(c) for c in columns]
            
            return metadata
        except Exception as e:
            return {"error": str(e)}
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _infer_data_type(self, value: Any) -> str:
        """Infer data type from value"""
        if value is None or value == '':
            return 'null'
        elif isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, str):
            # Try to infer more specific types
            value_lower = str(value).lower().strip()
            
            # Check for boolean-like strings
            if value_lower in ['true', 'false', 'yes', 'no', '1', '0']:
                return 'boolean_string'
            
            # Check for date-like strings
            if self._looks_like_date(value):
                return 'date_string'
            
            # Check for numeric strings
            if self._looks_like_number(value):
                return 'numeric_string'
            
            return 'text'
        else:
            return 'object'
    
    def _looks_like_date(self, value: str) -> bool:
        """Check if string looks like a date"""
        import re
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, str(value).strip()):
                return True
        return False
    
    def _looks_like_number(self, value: str) -> bool:
        """Check if string looks like a number"""
        try:
            float(str(value).replace(',', ''))
            return True
        except ValueError:
            return False
    
    def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding"""
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                return result['encoding'] or 'utf-8'
        except ImportError:
            # Fallback if chardet is not available
            return 'utf-8'
        except Exception:
            return 'utf-8'