#!/usr/bin/env python3
"""
Basic document analysis tool
"""

import logging
from typing import Dict, Any, Optional

from ..adapters.file_adapters.document_adapter import DocumentAdapter

logger = logging.getLogger(__name__)

def analyze_document(file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze a document and extract basic structure and content.
    
    Args:
        file_path: Path to document file
        options: Processing options
        
    Returns:
        Document analysis results
    """
    try:
        adapter = DocumentAdapter()
        success = adapter.connect({'file_path': file_path})
        
        if not success:
            return {"error": "Failed to load document", "status": "failed"}
        
        # Get basic analysis
        structure = adapter._analyze_structure()
        tables = adapter.get_tables()
        page_classification = adapter.classify_pages()
        
        result = {
            "status": "success",
            "file_path": file_path,
            "document_structure": structure,
            "tables_found": len(tables),
            "table_details": [
                {
                    "name": table.table_name,
                    "columns": len(getattr(table, 'extraction_metadata', {}).get('columns', [])),
                    "rows": table.record_count,
                    "page": getattr(table, 'extraction_metadata', {}).get('page_number')
                }
                for table in tables
            ],
            "page_classification": page_classification,
            "page_images": adapter.get_page_images(),
            "processing_metadata": {
                "total_pages": structure.get('total_pages', 0),
                "total_tables": structure.get('total_tables', 0),
                "supported_format": True
            }
        }
        
        adapter.disconnect()
        return result
        
    except Exception as e:
        logger.error(f"Document analysis failed: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "file_path": file_path
        }

def analyze_document_quality(file_path: str) -> Dict[str, Any]:
    """
    Analyze document quality and data completeness.
    
    Args:
        file_path: Path to document file
        
    Returns:
        Quality analysis results
    """
    try:
        adapter = DocumentAdapter()
        success = adapter.connect({'file_path': file_path})
        
        if not success:
            return {"error": "Failed to load document", "status": "failed"}
        
        validation_result = adapter.validate_file_structure()
        structure = adapter._analyze_structure()
        
        # Additional quality metrics
        quality_score = 0.0
        quality_factors = []
        
        # Check page distribution
        page_types = structure.get('page_types', {})
        if page_types.get('mixed', 0) > 0:
            quality_score += 0.3
            quality_factors.append("Mixed content pages found")
        
        # Check table presence
        if structure.get('total_tables', 0) > 0:
            quality_score += 0.4
            quality_factors.append("Structured tables detected")
        
        # Check text content
        total_content = sum(len(page.content) for page in adapter.pages)
        if total_content > 1000:
            quality_score += 0.3
            quality_factors.append("Substantial text content")
        
        adapter.disconnect()
        
        return {
            "status": "success",
            "file_path": file_path,
            "quality_score": min(quality_score, 1.0),
            "quality_factors": quality_factors,
            "validation_result": validation_result,
            "structure_analysis": structure,
            "recommendations": _generate_quality_recommendations(quality_score, structure)
        }
        
    except Exception as e:
        logger.error(f"Quality analysis failed: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "file_path": file_path
        }

def _generate_quality_recommendations(quality_score: float, structure: Dict[str, Any]) -> list:
    """Generate recommendations based on quality analysis."""
    recommendations = []
    
    if quality_score < 0.5:
        recommendations.append("Document may benefit from preprocessing or format conversion")
    
    if structure.get('total_tables', 0) == 0:
        recommendations.append("No structured tables detected - consider manual table marking")
    
    if structure.get('page_types', {}).get('image', 0) > structure.get('total_pages', 1) * 0.5:
        recommendations.append("High image content - stacked model analysis recommended")
    
    return recommendations