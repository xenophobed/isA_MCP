#!/usr/bin/env python3
"""
Document Analytics Tools - RAG Interface

Simplified interface for document RAG functionality.
"""

import logging
from typing import Dict, Any
from pathlib import Path

from .services.data_analytics_service.tools.rag_tools import quick_document_question

logger = logging.getLogger(__name__)

def quick_rag_question(file_path: str, question: str) -> Dict[str, Any]:
    """
    Quick RAG document question - ask questions about any document.
    
    Args:
        file_path: Path to document file (PDF, DOC, DOCX, PPT, PPTX, TXT)
        question: Question to ask about the document
        
    Returns:
        Answer with context and source information
    """
    # Validate file exists
    if not Path(file_path).exists():
        return {
            "error": "File not found",
            "status": "failed",
            "file_path": file_path
        }
    
    # Check supported format
    supported_extensions = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.txt'}
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext not in supported_extensions:
        return {
            "error": f"Unsupported file format: {file_ext}",
            "status": "failed",
            "file_path": file_path,
            "supported_formats": list(supported_extensions)
        }
    
    try:
        # Use the quick document question function
        result = quick_document_question(file_path, question)
        return result
        
    except Exception as e:
        logger.error(f"Quick RAG question failed: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "file_path": file_path,
            "question": question
        }

# Export for MCP
__all__ = ["quick_rag_question"]