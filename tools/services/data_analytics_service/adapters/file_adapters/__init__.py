#!/usr/bin/env python3
"""
File adapters for different file formats
"""

from .base_adapter import FileAdapter
from .excel_adapter import ExcelAdapter
from .csv_adapter import CSVAdapter
from .document_adapter import DocumentAdapter

__all__ = [
    "FileAdapter",
    "ExcelAdapter", 
    "CSVAdapter",
    "DocumentAdapter"
]