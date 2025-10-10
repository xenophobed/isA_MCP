#!/usr/bin/env python3
"""
Digital Service Package

Enhanced Digital Analytics Service with latest RAG Factory architecture
"""

from .enhanced_digital_service import DigitalAnalyticsService
from .config.analytics_config import AnalyticsConfig, VectorDBPolicy, ProcessingMode
from .utils.convenience_functions import (
    get_digital_analytics_service,
    create_digital_analytics_service,
    store_knowledge,
    search_knowledge,
    generate_rag_response,
    query_with_mode,
    hybrid_query,
    recommend_mode,
    get_rag_capabilities,
    get_service_stats,
    configure_policy
)

__all__ = [
    # Main service class
    'DigitalAnalyticsService',
    
    # Configuration classes
    'AnalyticsConfig',
    'VectorDBPolicy', 
    'ProcessingMode',
    
    # Service management functions
    'get_digital_analytics_service',
    'create_digital_analytics_service',
    
    # Knowledge management functions
    'store_knowledge',
    'search_knowledge',
    'generate_rag_response',
    
    # Multi-mode RAG functions
    'query_with_mode',
    'hybrid_query',
    'recommend_mode',
    'get_rag_capabilities',
    
    # Service management functions
    'get_service_stats',
    'configure_policy'
]

# Version information
__version__ = "2.0.0"
__author__ = "Digital Analytics Team"
__description__ = "Enhanced Digital Analytics Service with RAG Factory Architecture"