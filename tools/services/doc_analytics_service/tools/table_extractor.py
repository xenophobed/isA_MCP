#!/usr/bin/env python3
"""
Table extraction tool
"""

import logging
from typing import Dict, Any

from ..adapters.file_adapters.document_adapter import DocumentAdapter

logger = logging.getLogger(__name__)

def extract_tables_from_document(file_path: str) -> Dict[str, Any]:
    """
    Extract all tables from a document.
    
    Args:
        file_path: Path to document file
        
    Returns:
        Extracted table data
    """
    try:
        adapter = DocumentAdapter()
        success = adapter.connect({'file_path': file_path})
        
        if not success:
            return {"error": "Failed to load document", "status": "failed"}
        
        tables = adapter.get_tables()
        
        table_data = []
        for table in tables:
            # Get sample data for the table
            sample_data = adapter.get_sample_data(table.table_name, limit=10)
            
            columns = getattr(table, 'extraction_metadata', {}).get('columns', [])
            table_info = {
                "table_name": table.table_name,
                "page_number": getattr(table, 'extraction_metadata', {}).get('page_number'),
                "columns": [
                    {
                        "name": col.column_name,
                        "type": col.data_type,
                        "nullable": col.is_nullable
                    }
                    for col in columns
                ],
                "row_count": table.record_count,
                "sample_data": sample_data
            }
            table_data.append(table_info)
        
        adapter.disconnect()
        
        return {
            "status": "success",
            "file_path": file_path,
            "tables_found": len(table_data),
            "tables": table_data
        }
        
    except Exception as e:
        logger.error(f"Table extraction failed: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "file_path": file_path
        }