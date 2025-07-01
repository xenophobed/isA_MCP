#!/usr/bin/env python3
"""
File adapters for different file formats
"""

from .base_adapter import FileAdapter
from .excel_adapter import ExcelAdapter
from .csv_adapter import CSVAdapter

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