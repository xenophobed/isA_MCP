#!/usr/bin/env python3
"""
File adapters for different file formats
"""

from typing import Dict, List, Any

from .base_adapter import FileAdapter
# Temporarily comment out specific adapters due to import issues
# from .excel_adapter import ExcelAdapter
# from .csv_adapter import CSVAdapter

# Create working adapter classes
class ExcelAdapter(FileAdapter):
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.xlsx', '.xls']
        
    def load_data(self, file_path: str) -> Dict[str, Any]:
        try:
            import pandas as pd
            df = pd.read_excel(file_path)
            return {
                "success": True,
                "data": df,
                "shape": df.shape,
                "columns": df.columns.tolist()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

class CSVAdapter(FileAdapter):
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.csv']
        
    def load_data(self, file_path: str) -> Dict[str, Any]:
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            return {
                "success": True,
                "data": df,
                "shape": df.shape,
                "columns": df.columns.tolist()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

# Make document adapter optional (requires PyMuPDF)
try:
    from .document_adapter import DocumentAdapter
    DOCUMENT_ADAPTER_AVAILABLE = True
except ImportError:
    DocumentAdapter = None
    DOCUMENT_ADAPTER_AVAILABLE = False

__all__ = [
    "FileAdapter",
    "ExcelAdapter", 
    "CSVAdapter"
]

if DOCUMENT_ADAPTER_AVAILABLE:
    __all__.append("DocumentAdapter")