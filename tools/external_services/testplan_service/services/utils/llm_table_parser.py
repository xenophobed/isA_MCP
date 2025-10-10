#!/usr/bin/env python3
"""
LLM Table Parser for 3GPP Documents
Uses AI to identify test case tables by analyzing headers
"""

import json
import sys
import os
from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio
from pathlib import Path

# Add paths
sys.path.append('/Users/xenodennis/Documents/Fun/isA_MCP/tools/services')
base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(base_path))

from services.parser.document_parser import UniversalDocumentParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMTableParser:
    """Simple LLM-based table parser for identifying test case tables"""
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        """Lazy load ISA client"""
        if self._client is None:
            try:
                sys.path.append('/Users/xenodennis/Documents/Fun/isA_Model')
                from isa_model.client import ISAModelClient
                self._client = ISAModelClient()
            except ImportError as e:
                logger.error(f"Failed to import ISAModelClient: {e}")
                raise
        return self._client
    
    def extract_table_headers(self, doc_path: str) -> List[Dict[str, Any]]:
        """Extract headers and sample content from all tables"""
        try:
            doc_path_obj = Path(doc_path)
            parser = UniversalDocumentParser()
            doc = parser.parse(doc_path_obj)
            
            logger.info(f"📄 Processing: {doc_path_obj.name}")
            logger.info(f"   Found {len(doc.tables)} tables")
            
            tables_info = []
            for i, table in enumerate(doc.tables):
                headers = table.headers if table.headers else []
                if not headers and table.rows:
                    # Try first row as headers
                    headers = [str(cell).strip() for cell in table.rows[0] if cell]
                
                # Extract sample content from first few rows
                sample_content = []
                for row_idx, row in enumerate(table.rows[:5]):  # First 5 rows
                    if row:
                        first_cell = str(row[0]).strip() if len(row) > 0 else ""
                        sample_content.append(first_cell)
                
                tables_info.append({
                    'index': i,
                    'headers': headers,
                    'rows': len(table.rows),
                    'sample_content': sample_content
                })
            
            return tables_info
            
        except Exception as e:
            logger.error(f"Failed to extract headers: {e}")
            return []
    
    async def identify_test_tables(self, tables_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM to identify test case tables"""
        try:
            # Build table summary with sample content
            table_summary = ""
            for table in tables_info:
                idx = table['index']
                headers = table['headers']
                rows = table['rows']
                sample_content = table.get('sample_content', [])
                table_summary += f"Table {idx}: Headers={headers}, Rows={rows}, Sample_first_cells={sample_content}\n"
            
            # Enhanced prompt to use sample content for better identification
            prompt = f"""Identify test case tables from these tables:

{table_summary}

Test case tables can be identified by:
1. Standard headers like: "Clause", "TC Title", "Test", "Title", "Release", "Applicability"
2. OR by examining Sample_first_cells for test ID patterns like: "6.2.2", "9.1.2.3", "TC_001", etc.
3. Tables with many rows (50+) containing test case data

Look at the Sample_first_cells to identify tables that contain test IDs even if headers are non-standard.

Test case tables typically:
- Have test IDs in first column like: "6.2.2", "6.2.2_1", "9.1.2.3", "TC_001" 
- Have many rows (50+ typically)
- May have section headers instead of standard test headers

NOT test tables:
- Condition tables (C01, C02...)
- PICS tables (pc_ items)  
- Information tables with few rows
- Tables with only notes or definitions

Return JSON:
{{
    "test_tables": [0, 1, 2],
    "estimated_total": 1000
}}
"""

            response = await self.client.invoke(
                input_data=prompt,
                task="chat",
                service_type="text", 
                model="gpt-4.1-mini",
                temperature=0.1,
                stream=False,
                response_format={"type": "json_object"}
            )
            
            if not response.get('success'):
                raise Exception(f"LLM failed: {response.get('error')}")
            
            # Handle response according to llm.md documentation (line 315)
            result = response.get('result', '')
            if hasattr(result, 'content'):
                # JSON mode: result.content contains the JSON string
                result_text = result.content
            else:
                result_text = str(result)
            
            data = json.loads(result_text)
            
            test_tables = data.get('test_tables', [])
            estimated = data.get('estimated_total', 0)
            
            logger.info(f"🤖 LLM identified {len(test_tables)} test tables")
            logger.info(f"   Test tables: {test_tables}")
            logger.info(f"   Estimated tests: {estimated}")
            
            return {
                'success': True,
                'test_tables': test_tables,
                'estimated_total': estimated,
                'all_tables_count': len(tables_info)
            }
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'test_tables': []
            }
    
    async def analyze_document(self, doc_path: str) -> Dict[str, Any]:
        """Complete document analysis"""
        try:
            # Extract headers
            tables_info = self.extract_table_headers(doc_path)
            if not tables_info:
                return {'success': False, 'error': 'No tables found'}
            
            # Use LLM to identify test tables
            result = await self.identify_test_tables(tables_info)
            
            if result['success']:
                return {
                    'success': True,
                    'document': doc_path,
                    'total_tables': len(tables_info),
                    'test_tables': result['test_tables'],
                    'estimated_tests': result['estimated_total'],
                    'tables_info': tables_info
                }
            else:
                return result
                
        except Exception as e:
            return {'success': False, 'error': str(e)}


async def test_parser():
    """Test the parser"""
    parser = LLMTableParser()
    doc_path = "data_source/3GPP/TS 36.523-2/36523-2-i80/36523-2-i80.docx"
    
    print(f"Testing parser on: {doc_path}")
    
    result = await parser.analyze_document(doc_path)
    
    if result['success']:
        print(f"✅ Success!")
        print(f"Total tables: {result['total_tables']}")
        print(f"Test tables: {result['test_tables']}")
        print(f"Estimated tests: {result['estimated_tests']}")
    else:
        print(f"❌ Failed: {result['error']}")
    
    return result


if __name__ == "__main__":
    asyncio.run(test_parser())