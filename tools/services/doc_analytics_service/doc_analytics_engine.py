#!/usr/bin/env python3
"""
Document Analytics Engine

Central orchestration engine for document analysis capabilities.
Provides unified interface to all document processing tools and manages their execution.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union

# Import all tool functions
from .services.data_analytics_service.tools import (
    # Basic analysis
    analyze_document,
    analyze_document_quality,
    
    # Table extraction
    extract_tables_from_document,
    
    # Image processing
    extract_images_from_document,
    get_document_images_summary,
    convert_document_to_images,
    
    # Advanced processing
    process_document_advanced,
    batch_analyze_documents,
    create_custom_template,
    
    # Utils
    get_supported_formats,
    get_available_tools
)

logger = logging.getLogger(__name__)

class DocumentAnalyticsEngine:
    """
    Central engine for document analytics operations.
    
    Provides unified interface to all document processing capabilities
    with proper error handling, logging, and result aggregation.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.stats = {
            'documents_processed': 0,
            'total_processing_time': 0.0,
            'successful_operations': 0,
            'failed_operations': 0
        }
        
    def get_capabilities(self) -> Dict[str, Any]:
        """Get engine capabilities and available tools."""
        return {
            'engine_version': '1.0.0',
            'available_tools': get_available_tools(),
            'supported_formats': get_supported_formats(),
            'statistics': self.stats.copy()
        }
    
    # === Basic Analysis Tools ===
    
    def analyze(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Basic document analysis."""
        try:
            result = analyze_document(file_path, options)
            self._update_stats(result)
            return result
        except Exception as e:
            return self._handle_error("analyze", str(e), file_path)
    
    def analyze_quality(self, file_path: str) -> Dict[str, Any]:
        """Analyze document quality."""
        try:
            result = analyze_document_quality(file_path)
            self._update_stats(result)
            return result
        except Exception as e:
            return self._handle_error("analyze_quality", str(e), file_path)
    
    # === Extraction Tools ===
    
    def extract_tables(self, file_path: str) -> Dict[str, Any]:
        """Extract tables from document."""
        try:
            result = extract_tables_from_document(file_path)
            self._update_stats(result)
            return result
        except Exception as e:
            return self._handle_error("extract_tables", str(e), file_path)
    
    def extract_images(self, file_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Extract embedded images from document."""
        try:
            result = extract_images_from_document(file_path, output_dir)
            self._update_stats(result)
            return result
        except Exception as e:
            return self._handle_error("extract_images", str(e), file_path)
    
    def get_images_summary(self, file_path: str) -> Dict[str, Any]:
        """Get summary of document images."""
        try:
            result = get_document_images_summary(file_path)
            self._update_stats(result)
            return result
        except Exception as e:
            return self._handle_error("get_images_summary", str(e), file_path)
    
    def convert_to_images(self, file_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Convert document pages to images."""
        try:
            result = convert_document_to_images(file_path, output_dir)
            self._update_stats(result)
            return result
        except Exception as e:
            return self._handle_error("convert_to_images", str(e), file_path)
    
    # === Advanced Processing Tools ===
    
    async def process_advanced(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Advanced document processing with template matching."""
        try:
            result = await process_document_advanced(file_path, options)
            self._update_stats(result)
            return result
        except Exception as e:
            return self._handle_error("process_advanced", str(e), file_path)
    
    async def batch_process(self, file_paths: List[str], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process multiple documents in batch."""
        try:
            result = await batch_analyze_documents(file_paths, options)
            self._update_stats(result)
            return result
        except Exception as e:
            return self._handle_error("batch_process", str(e), file_paths)
    
    def create_template(self, template_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create custom template pattern."""
        try:
            result = create_custom_template(template_config)
            self._update_stats(result)
            return result
        except Exception as e:
            return self._handle_error("create_template", str(e), template_config.get('pattern_id', 'unknown'))
    
    # === Workflow Methods ===
    
    def complete_analysis(self, file_path: str, include_advanced: bool = True) -> Dict[str, Any]:
        """
        Perform complete analysis of a document including all available tools.
        
        Args:
            file_path: Path to document file
            include_advanced: Whether to include advanced processing
            
        Returns:
            Complete analysis results
        """
        results = {
            'file_path': file_path,
            'analysis_type': 'complete',
            'components': {}
        }
        
        try:
            # Basic analysis
            results['components']['basic_analysis'] = self.analyze(file_path)
            
            # Quality analysis
            results['components']['quality_analysis'] = self.analyze_quality(file_path)
            
            # Table extraction
            results['components']['table_extraction'] = self.extract_tables(file_path)
            
            # Image extraction
            results['components']['image_extraction'] = self.extract_images(file_path)
            
            # Image summary
            results['components']['image_summary'] = self.get_images_summary(file_path)
            
            # Advanced processing (if requested)
            if include_advanced:
                try:
                    advanced_result = asyncio.run(self.process_advanced(file_path))
                    results['components']['advanced_processing'] = advanced_result
                except Exception as e:
                    results['components']['advanced_processing'] = {
                        'error': str(e),
                        'status': 'failed'
                    }
            
            # Calculate overall status
            successful_components = sum(
                1 for comp in results['components'].values() 
                if comp.get('status') == 'success'
            )
            total_components = len(results['components'])
            
            results['overall_status'] = 'success' if successful_components == total_components else 'partial'
            results['success_rate'] = successful_components / total_components
            
            return results
            
        except Exception as e:
            logger.error(f"Complete analysis failed: {e}")
            return {
                'file_path': file_path,
                'analysis_type': 'complete',
                'overall_status': 'failed',
                'error': str(e),
                'components': results.get('components', {})
            }
    
    async def smart_workflow(self, file_path: str, target: str = 'auto') -> Dict[str, Any]:
        """
        Smart workflow that adapts processing based on document characteristics.
        
        Args:
            file_path: Path to document file
            target: Target workflow type ('auto', 'tables', 'images', 'text', 'forms')
            
        Returns:
            Workflow results
        """
        workflow_results = {
            'file_path': file_path,
            'workflow_type': target,
            'steps_executed': [],
            'final_result': None
        }
        
        try:
            # Step 1: Basic analysis to understand document
            basic_result = self.analyze(file_path)
            workflow_results['steps_executed'].append('basic_analysis')
            
            if basic_result.get('status') != 'success':
                workflow_results['final_result'] = basic_result
                return workflow_results
            
            # Determine optimal workflow based on target and document characteristics
            structure = basic_result.get('document_structure', {})
            
            if target == 'auto':
                # Auto-detect best workflow
                if structure.get('total_tables', 0) > 0:
                    target = 'tables'
                elif structure.get('total_extracted_images', 0) > 0:
                    target = 'images'
                else:
                    target = 'text'
            
            # Execute workflow based on target
            if target == 'tables':
                table_result = self.extract_tables(file_path)
                workflow_results['steps_executed'].append('table_extraction')
                workflow_results['final_result'] = table_result
                
            elif target == 'images':
                image_result = self.extract_images(file_path)
                workflow_results['steps_executed'].append('image_extraction')
                workflow_results['final_result'] = image_result
                
            elif target == 'forms':
                # Use advanced processing for form detection
                advanced_result = await self.process_advanced(file_path, {
                    'use_stacked_model': True
                })
                workflow_results['steps_executed'].append('advanced_processing')
                workflow_results['final_result'] = advanced_result
                
            else:  # text workflow
                quality_result = self.analyze_quality(file_path)
                workflow_results['steps_executed'].append('quality_analysis')
                workflow_results['final_result'] = quality_result
            
            return workflow_results
            
        except Exception as e:
            logger.error(f"Smart workflow failed: {e}")
            workflow_results['final_result'] = {
                'error': str(e),
                'status': 'failed'
            }
            return workflow_results
    
    # === Utility Methods ===
    
    def _update_stats(self, result: Dict[str, Any]):
        """Update engine statistics."""
        if result.get('status') == 'success':
            self.stats['successful_operations'] += 1
        else:
            self.stats['failed_operations'] += 1
        
        if 'processing_time' in result:
            self.stats['total_processing_time'] += result['processing_time']
        
        self.stats['documents_processed'] += 1
    
    def _handle_error(self, operation: str, error: str, context: Any) -> Dict[str, Any]:
        """Handle and log errors consistently."""
        logger.error(f"Operation '{operation}' failed: {error}")
        self.stats['failed_operations'] += 1
        
        return {
            'status': 'failed',
            'operation': operation,
            'error': error,
            'context': str(context)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine performance statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset engine statistics."""
        self.stats = {
            'documents_processed': 0,
            'total_processing_time': 0.0,
            'successful_operations': 0,
            'failed_operations': 0
        }

# Global engine instance
_engine = None

def get_engine(config: Optional[Dict[str, Any]] = None) -> DocumentAnalyticsEngine:
    """Get or create global engine instance."""
    global _engine
    if _engine is None:
        _engine = DocumentAnalyticsEngine(config)
    return _engine

# === Public API Functions ===

def analyze_document_complete(file_path: str, include_advanced: bool = True) -> Dict[str, Any]:
    """Complete document analysis using all available tools."""
    engine = get_engine()
    return engine.complete_analysis(file_path, include_advanced)

async def smart_document_workflow(file_path: str, target: str = 'auto') -> Dict[str, Any]:
    """Smart adaptive workflow for document processing."""
    engine = get_engine()
    return await engine.smart_workflow(file_path, target)

def get_engine_capabilities() -> Dict[str, Any]:
    """Get comprehensive engine capabilities."""
    engine = get_engine()
    return engine.get_capabilities()

def get_engine_stats() -> Dict[str, Any]:
    """Get engine performance statistics."""
    engine = get_engine()
    return engine.get_stats()