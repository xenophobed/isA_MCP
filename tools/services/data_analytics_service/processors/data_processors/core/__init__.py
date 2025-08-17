"""
Core data processing modules
Handles basic data operations, quality checks, and metadata extraction
"""

from .csv_processor import CSVProcessor
from .data_quality_processor import DataQualityProcessor
from .metadata_extractor import MetadataExtractor

__all__ = [
    'CSVProcessor',
    'DataQualityProcessor', 
    'MetadataExtractor'
]