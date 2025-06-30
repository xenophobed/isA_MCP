#!/usr/bin/env python3
"""
Advanced document processing tool
"""

import logging
from typing import Dict, Any, Optional, List

from ..services.document_processor import DocumentProcessor, TemplatePattern

logger = logging.getLogger(__name__)

# Global processor instance
_processor = None

def _get_processor() -> DocumentProcessor:
    """Get or create document processor instance."""
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor

async def process_document_advanced(file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Advanced document processing with template matching and stacked model integration.
    
    Args:
        file_path: Path to document file
        options: Processing options including:
            - use_stacked_model: Enable stacked model analysis
            - custom_templates: List of custom template patterns
            - output_format: 'json' or 'structured'
            
    Returns:
        Advanced processing results
    """
    try:
        processor = _get_processor()
        
        # Add custom templates if provided
        if options and 'custom_templates' in options:
            for template_data in options['custom_templates']:
                template = TemplatePattern(**template_data)
                processor.add_template(template)
        
        # Process document
        result = await processor.process_document(file_path, options or {})
        
        # Convert to dictionary format
        return {
            "status": result.status,
            "file_path": result.document_path,
            "pages_processed": result.pages_processed,
            "tables_extracted": result.tables_extracted,
            "images_generated": result.images_generated,
            "processing_time": result.processing_time,
            "structured_data": result.structured_data,
            "template_matches": result.template_matches,
            "errors": result.errors
        }
        
    except Exception as e:
        logger.error(f"Advanced document processing failed: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "file_path": file_path
        }

async def batch_analyze_documents(file_paths: List[str], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze multiple documents in batch.
    
    Args:
        file_paths: List of document file paths
        options: Processing options
        
    Returns:
        Batch processing results
    """
    try:
        processor = _get_processor()
        results = await processor.batch_process_documents(file_paths, options or {})
        
        # Convert results to dictionary format
        processed_results = []
        for result in results:
            processed_results.append({
                "file_path": result.document_path,
                "status": result.status,
                "pages_processed": result.pages_processed,
                "tables_extracted": result.tables_extracted,
                "processing_time": result.processing_time,
                "template_matches": len(result.template_matches),
                "errors": result.errors
            })
        
        # Calculate summary statistics
        successful = [r for r in processed_results if r['status'] == 'completed']
        failed = [r for r in processed_results if r['status'] == 'failed']
        
        return {
            "status": "completed",
            "total_documents": len(file_paths),
            "successful": len(successful),
            "failed": len(failed),
            "total_pages_processed": sum(r['pages_processed'] for r in successful),
            "total_tables_extracted": sum(r['tables_extracted'] for r in successful),
            "total_processing_time": sum(r['processing_time'] for r in processed_results),
            "results": processed_results
        }
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "total_documents": len(file_paths)
        }

def create_custom_template(template_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a custom template pattern for document matching.
    
    Args:
        template_config: Template configuration with fields:
            - pattern_id: Unique identifier
            - name: Template name
            - description: Template description
            - fields: List of field definitions
            - matching_rules: Rules for template matching
            - confidence_threshold: Minimum confidence (default 0.7)
            
    Returns:
        Template creation result
    """
    try:
        template = TemplatePattern(**template_config)
        processor = _get_processor()
        processor.add_template(template)
        
        return {
            "status": "success",
            "template_id": template.pattern_id,
            "template_name": template.name,
            "fields_count": len(template.fields)
        }
        
    except Exception as e:
        logger.error(f"Template creation failed: {e}")
        return {
            "error": str(e),
            "status": "failed"
        }