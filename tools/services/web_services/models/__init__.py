#!/usr/bin/env python
"""
Web Services Models
Standard data structures for web crawling and processing
"""
from .crawl_models import (
    CrawlMode, CrawlStrategy, CrawlConfig, CrawlResult, CrawlJobResult,
    ExtractionSchema, FilterConfig, ResourcePoolConfig
)
from .extraction_models import (
    ContentType, ExtractedContent, ExtractionResult, ExtractionMetadata
)
from .filtering_models import (
    FilterType, FilterCriteria, FilterResult, FilterMetadata, FilterPipeline, PredefinedFilters
)

__all__ = [
    # Crawl models
    'CrawlMode', 'CrawlStrategy', 'CrawlConfig', 'CrawlResult', 'CrawlJobResult',
    'ExtractionSchema', 'FilterConfig', 'ResourcePoolConfig',
    
    # Extraction models
    'ContentType', 'ExtractedContent', 'ExtractionResult', 'ExtractionMetadata',
    
    # Filtering models
    'FilterType', 'FilterCriteria', 'FilterResult', 'FilterMetadata', 'FilterPipeline', 'PredefinedFilters'
]