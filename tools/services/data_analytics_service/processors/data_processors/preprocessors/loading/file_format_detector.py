#!/usr/bin/env python3
"""
File Format Detection Processor
Detects file format, encoding, and basic structure
"""

import csv
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FileFormatDetector:
    """Detects file format and basic properties"""
    
    def __init__(self):
        self.supported_formats = {
            '.csv': 'csv',
            '.tsv': 'tsv', 
            '.txt': 'text',
            '.xlsx': 'excel',
            '.xls': 'excel',
            '.json': 'json',
            '.jsonl': 'jsonl',
            '.parquet': 'parquet',
            '.duckdb': 'duckdb',
            '.db': 'duckdb'
        }
    
    def detect_format(self, file_path: str) -> Dict[str, Any]:
        """
        Detect file format and properties
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict with format detection results
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {
                    'success': False,
                    'error': 'File does not exist'
                }
            
            # Basic file info
            file_info = {
                'success': True,
                'file_name': path.name,
                'file_size': path.stat().st_size,
                'file_extension': path.suffix.lower(),
                'detected_format': 'unknown',
                'encoding': None,
                'delimiter': None,
                'has_header': None
            }
            
            # Detect format by extension
            extension = path.suffix.lower()
            if extension in self.supported_formats:
                file_info['detected_format'] = self.supported_formats[extension]
            
            # For CSV-like files, detect encoding and delimiter
            if file_info['detected_format'] in ['csv', 'tsv', 'text']:
                encoding_result = self._detect_encoding(file_path)
                file_info['encoding'] = encoding_result
                
                delimiter_result = self._detect_delimiter(file_path, encoding_result)
                file_info['delimiter'] = delimiter_result
                
                header_result = self._detect_header(file_path, encoding_result, delimiter_result)
                file_info['has_header'] = header_result
            
            return file_info
            
        except Exception as e:
            logger.error(f"Format detection failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding"""
        try:
            # Try common encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read(1024)  # Read first 1KB
                    return encoding
                except UnicodeDecodeError:
                    continue
            
            return 'utf-8'  # Default fallback
            
        except Exception:
            return 'utf-8'
    
    def _detect_delimiter(self, file_path: str, encoding: str) -> Optional[str]:
        """Detect CSV delimiter"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                sample = f.read(1024)
                
            # Use CSV sniffer
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(sample, delimiters=',;\t|')
                return dialect.delimiter
            except csv.Error:
                # Fallback: count occurrences
                delimiters = {',': 0, ';': 0, '\t': 0, '|': 0}
                for delimiter in delimiters:
                    delimiters[delimiter] = sample.count(delimiter)
                
                # Return most common delimiter
                if max(delimiters.values()) > 0:
                    return max(delimiters, key=delimiters.get)
                
            return ','  # Default fallback
            
        except Exception:
            return ','
    
    def _detect_header(self, file_path: str, encoding: str, delimiter: str) -> bool:
        """Detect if file has header row"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                first_line = f.readline().strip()
                second_line = f.readline().strip()
            
            if not first_line or not second_line:
                return False
            
            first_fields = first_line.split(delimiter)
            second_fields = second_line.split(delimiter)
            
            if len(first_fields) != len(second_fields):
                return False
            
            # Check if first row looks like headers
            # Headers are usually strings, data often contains numbers
            first_numeric_count = sum(1 for field in first_fields if self._is_numeric(field.strip()))
            second_numeric_count = sum(1 for field in second_fields if self._is_numeric(field.strip()))
            
            # If first row has fewer numbers than second row, likely header
            return first_numeric_count < second_numeric_count
            
        except Exception:
            return True  # Default assume header
    
    def _is_numeric(self, value: str) -> bool:
        """Check if string represents a number"""
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def get_supported_formats(self) -> Dict[str, str]:
        """Get supported file formats"""
        return self.supported_formats.copy()
    
    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported"""
        extension = Path(file_path).suffix.lower()
        return extension in self.supported_formats