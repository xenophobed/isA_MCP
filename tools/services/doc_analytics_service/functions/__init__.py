#!/usr/bin/env python3
"""
Document analytics tools module
"""

from .basic_analyzer import analyze_document, analyze_document_quality
from .table_extractor import extract_tables_from_document
from .image_extractor import (
    extract_images_from_document, 
    get_document_images_summary, 
    convert_document_to_images
)
from .advanced_processor import (
    process_document_advanced, 
    batch_analyze_documents, 
    create_custom_template
)
from .rag_tools import (
    create_document_rag_session,
    add_document_to_rag_session,
    query_document_rag,
    get_rag_session_info,
    delete_rag_session,
    list_rag_sessions,
    get_rag_service_stats,
    quick_document_question
)
from .utils import get_supported_formats, get_available_tools

__all__ = [
    # Basic analysis
    "analyze_document",
    "analyze_document_quality",
    
    # Table extraction
    "extract_tables_from_document",
    
    # Image processing
    "extract_images_from_document",
    "get_document_images_summary", 
    "convert_document_to_images",
    
    # Advanced processing
    "process_document_advanced",
    "batch_analyze_documents",
    "create_custom_template",
    
    # RAG tools
    "create_document_rag_session",
    "add_document_to_rag_session", 
    "query_document_rag",
    "get_rag_session_info",
    "delete_rag_session",
    "list_rag_sessions",
    "get_rag_service_stats",
    "quick_document_question",
    
    # Utils
    "get_supported_formats",
    "get_available_tools"
]