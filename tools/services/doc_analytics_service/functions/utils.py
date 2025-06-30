#!/usr/bin/env python3
"""
Utility functions for document analytics
"""

from typing import Dict, Any

def get_supported_formats() -> Dict[str, Any]:
    """
    Get list of supported document formats.
    
    Returns:
        Supported formats information
    """
    return {
        "supported_formats": {
            ".pdf": "Portable Document Format",
            ".doc": "Microsoft Word Document (legacy)",
            ".docx": "Microsoft Word Document",
            ".ppt": "Microsoft PowerPoint Presentation (legacy)",
            ".pptx": "Microsoft PowerPoint Presentation",
            ".txt": "Plain Text Document"
        },
        "capabilities": {
            "text_extraction": True,
            "table_extraction": True,
            "image_conversion": True,
            "embedded_image_extraction": True,
            "ocr_processing": True,
            "template_matching": True,
            "stacked_model_integration": True,
            "batch_processing": True
        },
        "output_formats": ["json", "structured", "images"]
    }

def get_available_tools() -> list:
    """Get list of available document analysis tools."""
    return [
        {
            "name": "analyze_document",
            "description": "Basic document analysis and structure extraction",
            "module": "basic_analyzer",
            "async": False
        },
        {
            "name": "analyze_document_quality",
            "description": "Analyze document quality and completeness", 
            "module": "basic_analyzer",
            "async": False
        },
        {
            "name": "extract_tables_from_document",
            "description": "Extract all tables from document",
            "module": "table_extractor",
            "async": False
        },
        {
            "name": "extract_images_from_document",
            "description": "Extract all embedded images from document",
            "module": "image_extractor",
            "async": False
        },
        {
            "name": "get_document_images_summary",
            "description": "Get summary of all images in document",
            "module": "image_extractor", 
            "async": False
        },
        {
            "name": "convert_document_to_images",
            "description": "Convert document pages to images",
            "module": "image_extractor",
            "async": False
        },
        {
            "name": "process_document_advanced",
            "description": "Advanced processing with template matching and stacked model",
            "module": "advanced_processor",
            "async": True
        },
        {
            "name": "batch_analyze_documents",
            "description": "Process multiple documents in batch",
            "module": "advanced_processor",
            "async": True
        },
        {
            "name": "create_custom_template",
            "description": "Create custom template for document matching",
            "module": "advanced_processor",
            "async": False
        },
        {
            "name": "get_supported_formats",
            "description": "Get supported document formats and capabilities",
            "module": "utils",
            "async": False
        }
    ]