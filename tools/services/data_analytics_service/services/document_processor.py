#!/usr/bin/env python3
"""
Document processing service for advanced document analysis and structured data extraction.
Integrates with stacked model for table recognition and template matching.
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging

from ..adapters.file_adapters.document_adapter import DocumentAdapter, DocumentPageInfo
from ..core.metadata_extractor import TableInfo, ColumnInfo

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Result of document processing."""
    document_path: str
    pages_processed: int
    tables_extracted: int
    images_generated: int
    structured_data: Dict[str, Any]
    template_matches: List[Dict[str, Any]] = field(default_factory=list)
    processing_time: float = 0.0
    status: str = "completed"
    errors: List[str] = field(default_factory=list)

@dataclass
class TemplatePattern:
    """Template pattern for matching structured data."""
    pattern_id: str
    name: str
    description: str
    fields: List[Dict[str, Any]]
    matching_rules: Dict[str, Any]
    confidence_threshold: float = 0.7

@dataclass
class StackedModelRequest:
    """Request structure for stacked model analysis."""
    image_path: str
    analysis_type: str  # 'table_extraction', 'form_analysis', 'general_ocr'
    page_context: Dict[str, Any]
    model_params: Dict[str, Any] = field(default_factory=dict)

class DocumentProcessor:
    """Advanced document processing service."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.adapter = DocumentAdapter()
        self.templates: List[TemplatePattern] = []
        self.stacked_model_endpoint = self.config.get('stacked_model_endpoint')
        self.processing_cache = {}
        
        # Initialize template patterns
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default template patterns for common document types."""
        
        # Invoice template
        invoice_template = TemplatePattern(
            pattern_id="invoice_001",
            name="Standard Invoice",
            description="Standard invoice with header, line items, and totals",
            fields=[
                {"name": "invoice_number", "type": "string", "required": True},
                {"name": "date", "type": "date", "required": True},
                {"name": "vendor", "type": "string", "required": True},
                {"name": "line_items", "type": "table", "required": True},
                {"name": "total_amount", "type": "currency", "required": True}
            ],
            matching_rules={
                "keywords": ["invoice", "bill", "total", "amount"],
                "table_required": True,
                "min_numeric_fields": 2
            }
        )
        
        # Form template
        form_template = TemplatePattern(
            pattern_id="form_001", 
            name="Standard Form",
            description="Form with field-value pairs",
            fields=[
                {"name": "form_fields", "type": "key_value_pairs", "required": True}
            ],
            matching_rules={
                "keywords": ["name", "address", "phone", "email"],
                "field_value_pattern": True
            }
        )
        
        # Report template
        report_template = TemplatePattern(
            pattern_id="report_001",
            name="Data Report", 
            description="Report with tables and charts",
            fields=[
                {"name": "title", "type": "string", "required": True},
                {"name": "summary", "type": "text", "required": False},
                {"name": "data_tables", "type": "table_list", "required": True}
            ],
            matching_rules={
                "keywords": ["report", "analysis", "summary"],
                "multiple_tables": True
            }
        )
        
        self.templates = [invoice_template, form_template, report_template]
    
    async def process_document(self, file_path: str, options: Dict[str, Any] = None) -> ProcessingResult:
        """Process document with full analysis pipeline."""
        
        start_time = asyncio.get_event_loop().time()
        options = options or {}
        
        try:
            logger.info(f"Starting document processing: {file_path}")
            
            # Stage 1: Load and preprocess document
            success = self.adapter.connect({'file_path': file_path})
            if not success:
                raise Exception("Failed to load document")
            
            # Stage 2: Extract basic structure
            structure = self.adapter._analyze_structure()
            tables = self.adapter.get_tables()
            
            # Stage 3: Process pages with stacked model (if available)
            stacked_results = []
            if self.stacked_model_endpoint and options.get('use_stacked_model', True):
                stacked_results = await self._process_with_stacked_model()
            
            # Stage 4: Template matching
            template_matches = await self._match_templates(structure, tables, stacked_results)
            
            # Stage 5: Synthesize structured data
            structured_data = await self._synthesize_structured_data(
                structure, tables, stacked_results, template_matches
            )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            result = ProcessingResult(
                document_path=file_path,
                pages_processed=structure.get('total_pages', 0),
                tables_extracted=structure.get('total_tables', 0),
                images_generated=len(self.adapter.get_page_images()),
                structured_data=structured_data,
                template_matches=template_matches,
                processing_time=processing_time
            )
            
            logger.info(f"Document processing completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return ProcessingResult(
                document_path=file_path,
                pages_processed=0,
                tables_extracted=0,
                images_generated=0,
                structured_data={},
                status="failed",
                errors=[str(e)],
                processing_time=asyncio.get_event_loop().time() - start_time
            )
        finally:
            self.adapter.disconnect()
    
    async def _process_with_stacked_model(self) -> List[Dict[str, Any]]:
        """Process document pages with stacked model for enhanced analysis."""
        
        results = []
        page_images = self.adapter.get_page_images()
        
        for i, image_path in enumerate(page_images):
            page_info = self.adapter.get_page_content(i + 1)
            
            if not page_info or not image_path:
                continue
            
            # Determine analysis type based on page content
            analysis_type = self._determine_analysis_type(page_info)
            
            request = StackedModelRequest(
                image_path=image_path,
                analysis_type=analysis_type,
                page_context={
                    'page_number': page_info.page_number,
                    'page_type': page_info.page_type,
                    'text_content': page_info.content[:500],  # First 500 chars
                    'table_count': len(page_info.tables)
                }
            )
            
            # Send to stacked model
            try:
                model_result = await self._call_stacked_model(request)
                results.append({
                    'page_number': page_info.page_number,
                    'analysis_type': analysis_type,
                    'model_result': model_result,
                    'image_path': image_path
                })
            except Exception as e:
                logger.warning(f"Stacked model processing failed for page {i+1}: {e}")
                results.append({
                    'page_number': page_info.page_number,
                    'analysis_type': analysis_type,
                    'model_result': None,
                    'error': str(e)
                })
        
        return results
    
    def _determine_analysis_type(self, page_info: DocumentPageInfo) -> str:
        """Determine the appropriate analysis type for stacked model."""
        
        if page_info.page_type == 'table' or len(page_info.tables) >= 2:
            return 'table_extraction'
        elif 'form' in page_info.content.lower() or self._has_form_patterns(page_info.content):
            return 'form_analysis'
        else:
            return 'general_ocr'
    
    def _has_form_patterns(self, content: str) -> bool:
        """Check if content has form-like patterns."""
        form_indicators = ['name:', 'address:', 'phone:', 'email:', 'date:', '____']
        content_lower = content.lower()
        return sum(1 for indicator in form_indicators if indicator in content_lower) >= 2
    
    async def _call_stacked_model(self, request: StackedModelRequest) -> Dict[str, Any]:
        """Call the stacked model API for image analysis."""
        
        if not self.stacked_model_endpoint:
            raise Exception("Stacked model endpoint not configured")
        
        # Simulate API call for now - replace with actual HTTP request
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Mock response based on analysis type
        if request.analysis_type == 'table_extraction':
            return {
                'tables': [
                    {
                        'table_id': 'extracted_1',
                        'confidence': 0.9,
                        'data': [
                            ['Header1', 'Header2', 'Header3'],
                            ['Row1Col1', 'Row1Col2', 'Row1Col3'],
                            ['Row2Col1', 'Row2Col2', 'Row2Col3']
                        ],
                        'bbox': [100, 100, 500, 300]
                    }
                ],
                'confidence': 0.9,
                'processing_time': 0.5
            }
        elif request.analysis_type == 'form_analysis':
            return {
                'fields': [
                    {'name': 'customer_name', 'value': 'John Doe', 'confidence': 0.95},
                    {'name': 'address', 'value': '123 Main St', 'confidence': 0.88},
                    {'name': 'phone', 'value': '555-1234', 'confidence': 0.92}
                ],
                'confidence': 0.91,
                'processing_time': 0.3
            }
        else:
            return {
                'text': request.page_context.get('text_content', ''),
                'confidence': 0.85,
                'processing_time': 0.2
            }
    
    async def _match_templates(self, structure: Dict, tables: List[TableInfo], 
                             stacked_results: List[Dict]) -> List[Dict[str, Any]]:
        """Match document content against predefined templates."""
        
        matches = []
        
        # Collect all content for analysis
        all_content = []
        for page in self.adapter.pages:
            all_content.append(page.content.lower())
        
        combined_content = ' '.join(all_content)
        
        # Test each template
        for template in self.templates:
            confidence = await self._calculate_template_confidence(
                template, combined_content, structure, tables, stacked_results
            )
            
            if confidence >= template.confidence_threshold:
                matches.append({
                    'template_id': template.pattern_id,
                    'template_name': template.name,
                    'confidence': confidence,
                    'matched_fields': await self._extract_template_fields(
                        template, combined_content, structure, stacked_results
                    )
                })
        
        return sorted(matches, key=lambda x: x['confidence'], reverse=True)
    
    async def _calculate_template_confidence(self, template: TemplatePattern, 
                                           content: str, structure: Dict,
                                           tables: List[TableInfo], 
                                           stacked_results: List[Dict]) -> float:
        """Calculate confidence score for template matching."""
        
        score = 0.0
        rules = template.matching_rules
        
        # Keyword matching
        if 'keywords' in rules:
            keyword_matches = sum(1 for kw in rules['keywords'] if kw in content)
            score += (keyword_matches / len(rules['keywords'])) * 0.3
        
        # Table requirements
        if rules.get('table_required') and structure.get('total_tables', 0) > 0:
            score += 0.2
        
        if rules.get('multiple_tables') and structure.get('total_tables', 0) > 1:
            score += 0.2
        
        # Field-value pattern detection
        if rules.get('field_value_pattern'):
            # Look for key:value patterns
            field_patterns = len([line for line in content.split('\n') 
                                if ':' in line and len(line.split(':')) == 2])
            if field_patterns > 3:
                score += 0.3
        
        # Numeric field requirements
        if 'min_numeric_fields' in rules:
            import re
            numeric_matches = len(re.findall(r'\d+\.?\d*', content))
            if numeric_matches >= rules['min_numeric_fields']:
                score += 0.2
        
        return min(score, 1.0)
    
    async def _extract_template_fields(self, template: TemplatePattern, 
                                     content: str, structure: Dict,
                                     stacked_results: List[Dict]) -> Dict[str, Any]:
        """Extract specific fields based on template definition."""
        
        extracted_fields = {}
        
        for field_def in template.fields:
            field_name = field_def['name']
            field_type = field_def['type']
            
            if field_type == 'string':
                # Extract string fields (simplified)
                if field_name == 'invoice_number':
                    import re
                    matches = re.findall(r'invoice\s*#?\s*(\w+)', content, re.IGNORECASE)
                    if matches:
                        extracted_fields[field_name] = matches[0]
                elif field_name == 'vendor':
                    # Look for company name patterns
                    lines = content.split('\n')[:5]  # Check first 5 lines
                    for line in lines:
                        if len(line.strip()) > 3 and not line.strip().isdigit():
                            extracted_fields[field_name] = line.strip()
                            break
            
            elif field_type == 'table':
                # Extract table data
                if structure.get('total_tables', 0) > 0:
                    extracted_fields[field_name] = []
                    for result in stacked_results:
                        if result.get('model_result', {}).get('tables'):
                            extracted_fields[field_name].extend(
                                result['model_result']['tables']
                            )
            
            elif field_type == 'key_value_pairs':
                # Extract field-value pairs
                pairs = {}
                for line in content.split('\n'):
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            key = parts[0].strip().lower()
                            value = parts[1].strip()
                            pairs[key] = value
                extracted_fields[field_name] = pairs
        
        return extracted_fields
    
    async def _synthesize_structured_data(self, structure: Dict, tables: List[TableInfo],
                                        stacked_results: List[Dict], 
                                        template_matches: List[Dict]) -> Dict[str, Any]:
        """Synthesize all extracted data into structured format."""
        
        structured_data = {
            'document_metadata': {
                'total_pages': structure.get('total_pages', 0),
                'page_types': structure.get('page_types', {}),
                'total_tables': structure.get('total_tables', 0),
                'processing_date': asyncio.get_event_loop().time()
            },
            'extracted_tables': [],
            'template_analysis': {
                'best_match': template_matches[0] if template_matches else None,
                'all_matches': template_matches,
                'confidence_scores': [m['confidence'] for m in template_matches]
            },
            'page_analysis': [],
            'stacked_model_results': stacked_results
        }
        
        # Add table data
        for table in tables:
            table_data = {
                'table_name': table.table_name,
                'page_location': table.metadata.get('page_number'),
                'columns': [col.column_name for col in table.columns],
                'row_count': table.record_count,
                'extraction_confidence': 0.8  # Default confidence
            }
            
            # Enhance with stacked model results if available
            for result in stacked_results:
                if (result.get('model_result', {}).get('tables') and
                    result.get('page_number') == table.metadata.get('page_number')):
                    table_data['stacked_model_enhancement'] = result['model_result']['tables']
                    table_data['extraction_confidence'] = result['model_result'].get('confidence', 0.8)
            
            structured_data['extracted_tables'].append(table_data)
        
        # Add page-level analysis
        for page in self.adapter.pages:
            page_analysis = {
                'page_number': page.page_number,
                'content_type': page.page_type,
                'text_length': len(page.content),
                'table_count': len(page.tables),
                'has_image': page.image_path is not None
            }
            
            # Add stacked model results for this page
            for result in stacked_results:
                if result.get('page_number') == page.page_number:
                    page_analysis['stacked_model_analysis'] = result.get('model_result')
                    break
            
            structured_data['page_analysis'].append(page_analysis)
        
        return structured_data
    
    def add_template(self, template: TemplatePattern):
        """Add a custom template pattern."""
        self.templates.append(template)
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            'templates_loaded': len(self.templates),
            'stacked_model_configured': self.stacked_model_endpoint is not None,
            'cache_size': len(self.processing_cache)
        }
    
    async def batch_process_documents(self, file_paths: List[str], 
                                    options: Dict[str, Any] = None) -> List[ProcessingResult]:
        """Process multiple documents in batch."""
        
        results = []
        
        for file_path in file_paths:
            try:
                result = await self.process_document(file_path, options)
                results.append(result)
            except Exception as e:
                logger.error(f"Batch processing failed for {file_path}: {e}")
                results.append(ProcessingResult(
                    document_path=file_path,
                    pages_processed=0,
                    tables_extracted=0,
                    images_generated=0,
                    structured_data={},
                    status="failed",
                    errors=[str(e)]
                ))
        
        return results