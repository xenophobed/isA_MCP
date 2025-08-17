#!/usr/bin/env python3
"""
Enhanced Unified Processor

Combines traditional processing with AI enhancement for superior results.
This is the main entry point that integrates all processing capabilities.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import time

from .unified_asset_processor import UnifiedAssetProcessor, ProcessingMode
from .ai_enhanced_processor import AIEnhancedProcessor

logger = logging.getLogger(__name__)

class EnhancedUnifiedProcessor:
    """
    Enhanced unified processor that combines traditional methods with AI intelligence
    for comprehensive digital asset processing and understanding.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize core processors
        self.unified_processor = UnifiedAssetProcessor(self.config.get('unified', {}))
        self.ai_enhancer = AIEnhancedProcessor(self.config.get('ai_enhancement', {}))
        
        # Processing settings
        self.enable_ai_enhancement = self.config.get('enable_ai_enhancement', True)
        self.ai_enhancement_threshold = self.config.get('ai_enhancement_threshold', 0.7)
        self.max_processing_time = self.config.get('max_processing_time', 600)  # 10 minutes
        
        logger.info("Enhanced Unified Processor initialized")
    
    async def process_asset_enhanced(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process any digital asset with full traditional + AI enhancement.
        
        Args:
            file_path: Path to the asset file
            options: Processing options including AI enhancement settings
            
        Returns:
            Enhanced processing results combining traditional and AI analysis
        """
        start_time = time.time()
        
        try:
            options = options or {}
            
            # Step 1: Traditional processing using unified processor
            logger.info(f"Starting traditional processing for: {Path(file_path).name}")
            traditional_result = await self.unified_processor.process_asset(file_path, options)
            
            if not traditional_result.get('success'):
                return {
                    'file_path': file_path,
                    'success': False,
                    'error': f"Traditional processing failed: {traditional_result.get('error')}",
                    'processing_time': time.time() - start_time
                }
            
            # Step 2: AI Enhancement (if enabled and appropriate)
            enhanced_result = traditional_result.copy()
            
            if self.enable_ai_enhancement and options.get('enable_ai', True):
                logger.info(f"Starting AI enhancement for: {Path(file_path).name}")
                
                asset_type = traditional_result.get('asset_type', 'unknown')
                
                # Route to appropriate AI enhancement based on asset type
                if asset_type in ['image', 'pdf']:
                    enhanced_result = await self._enhance_image_based_content(file_path, traditional_result)
                elif asset_type in ['audio', 'video']:
                    enhanced_result = await self._enhance_audio_based_content(file_path, traditional_result)
                elif asset_type in ['office', 'text']:
                    enhanced_result = await self._enhance_text_based_content(file_path, traditional_result)
                else:
                    # Generic enhancement for any content with text
                    enhanced_result = await self._enhance_generic_content(file_path, traditional_result)
                
                # Apply holistic document understanding
                enhanced_result = await self.ai_enhancer.enhance_document_understanding(file_path, enhanced_result)
                
                # Generate insights and recommendations
                enhanced_result = await self.ai_enhancer.generate_insights_and_recommendations(enhanced_result, file_path)
            
            # Step 3: Finalize results
            final_result = {
                'file_path': file_path,
                'asset_type': traditional_result.get('asset_type'),
                'success': True,
                'traditional_processing': traditional_result,
                'enhanced_processing': enhanced_result,
                'ai_enhancement_enabled': self.enable_ai_enhancement and options.get('enable_ai', True),
                'processing_time': time.time() - start_time,
                'processing_summary': {
                    'traditional_success': traditional_result.get('success', False),
                    'ai_enhancement_applied': 'ai_enhancement_time' in enhanced_result,
                    'total_features_processed': len(traditional_result.get('features_processed', [])),
                    'ai_confidence': enhanced_result.get('quality_score', 0.0)
                }
            }
            
            return final_result
            
        except Exception as e:
            logger.error(f"Enhanced processing failed for {file_path}: {e}")
            return {
                'file_path': file_path,
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    async def _enhance_image_based_content(self, file_path: str, traditional_result: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance image-based content (images, PDFs with images)."""
        try:
            # Extract results from traditional processing
            results = traditional_result.get('results', {})
            
            # Enhance with AI image analysis
            enhanced_result = await self.ai_enhancer.enhance_image_analysis(file_path, results)
            
            # If we have text content, enhance it too
            text_content = self._extract_text_from_results(results)
            if text_content:
                text_enhanced = await self.ai_enhancer.enhance_text_analysis(
                    text_content, enhanced_result, f"Extracted from {Path(file_path).suffix} file"
                )
                enhanced_result.update(text_enhanced)
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Image-based content enhancement failed: {e}")
            return traditional_result
    
    async def _enhance_audio_based_content(self, file_path: str, traditional_result: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance audio-based content (audio files, video audio)."""
        try:
            # Extract results from traditional processing
            results = traditional_result.get('results', {})
            
            # Enhance with AI audio analysis
            enhanced_result = await self.ai_enhancer.enhance_audio_analysis(file_path, results)
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Audio-based content enhancement failed: {e}")
            return traditional_result
    
    async def _enhance_text_based_content(self, file_path: str, traditional_result: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance text-based content (office documents, text files)."""
        try:
            # Extract text content from traditional processing
            results = traditional_result.get('results', {})
            text_content = self._extract_text_from_results(results)
            
            if text_content:
                # Enhance with AI text analysis
                enhanced_result = await self.ai_enhancer.enhance_text_analysis(
                    text_content, results, f"Office document: {Path(file_path).name}"
                )
                return enhanced_result
            
            return traditional_result
            
        except Exception as e:
            logger.error(f"Text-based content enhancement failed: {e}")
            return traditional_result
    
    async def _enhance_generic_content(self, file_path: str, traditional_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generic enhancement for any content type."""
        try:
            results = traditional_result.get('results', {})
            text_content = self._extract_text_from_results(results)
            
            if text_content and len(text_content) > 50:
                # Apply generic text enhancement
                enhanced_result = await self.ai_enhancer.enhance_text_analysis(
                    text_content, results, f"Generic content from {Path(file_path).suffix} file"
                )
                return enhanced_result
            
            return traditional_result
            
        except Exception as e:
            logger.error(f"Generic content enhancement failed: {e}")
            return traditional_result
    
    def _extract_text_from_results(self, results: Dict[str, Any]) -> str:
        """Extract all available text from processing results."""
        text_parts = []
        
        # Common text fields
        text_fields = ['text', 'combined_text', 'transcript', 'full_text']
        
        for field in text_fields:
            if field in results and results[field]:
                text_parts.append(str(results[field]))
        
        # Check nested results
        for key, value in results.items():
            if isinstance(value, dict):
                nested_text = self._extract_text_from_results(value)
                if nested_text:
                    text_parts.append(nested_text)
        
        return '\\n\\n'.join(filter(None, text_parts))
    
    async def process_batch_enhanced(self, file_paths: List[str], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process multiple assets with enhanced analysis and cross-correlation.
        
        Args:
            file_paths: List of file paths to process
            options: Processing options
            
        Returns:
            Enhanced batch processing results with correlations
        """
        start_time = time.time()
        
        try:
            options = options or {}
            
            # Process each file with enhancement
            enhanced_results = []
            
            # Use semaphore for controlled parallel processing
            max_parallel = options.get('max_parallel', self.unified_processor.max_parallel_jobs)
            semaphore = asyncio.Semaphore(max_parallel)
            
            async def process_single_enhanced(file_path: str) -> Dict[str, Any]:
                async with semaphore:
                    return await self.process_asset_enhanced(file_path, options)
            
            # Process all files
            tasks = [process_single_enhanced(fp) for fp in file_paths]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Separate successful and failed results
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        'file_path': file_paths[i] if i < len(file_paths) else 'unknown',
                        'error': str(result)
                    })
                elif result.get('success'):
                    successful_results.append(result)
                else:
                    failed_results.append(result)
            
            # Perform enhanced cross-analysis if we have multiple successful results
            cross_analysis = {}
            if len(successful_results) > 1 and options.get('enable_cross_analysis', True):
                cross_analysis = await self._perform_enhanced_cross_analysis(successful_results)
            
            return {
                'total_files': len(file_paths),
                'successful_count': len(successful_results),
                'failed_count': len(failed_results),
                'successful_results': successful_results,
                'failed_results': failed_results,
                'enhanced_cross_analysis': cross_analysis,
                'processing_time': time.time() - start_time,
                'ai_enhancement_enabled': self.enable_ai_enhancement
            }
            
        except Exception as e:
            logger.error(f"Enhanced batch processing failed: {e}")
            return {
                'total_files': len(file_paths) if file_paths else 0,
                'successful_count': 0,
                'failed_count': len(file_paths) if file_paths else 0,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    async def _perform_enhanced_cross_analysis(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform AI-enhanced cross-analysis of multiple assets."""
        try:
            # Extract all content for analysis
            content_summary = []
            
            for result in results:
                file_path = result.get('file_path', '')
                asset_type = result.get('asset_type', 'unknown')
                
                # Extract AI insights if available
                enhanced = result.get('enhanced_processing', {})
                ai_insights = enhanced.get('ai_insights_and_recommendations', {})
                ai_analysis = enhanced.get('ai_content_analysis', {})
                
                content_summary.append({
                    'file': Path(file_path).name,
                    'type': asset_type,
                    'insights': ai_insights.get('insights', ''),
                    'analysis': ai_analysis.get('analysis', ''),
                    'quality': enhanced.get('quality_score', 0.0)
                })
            
            # Generate cross-analysis using AI
            if self.enable_ai_enhancement and content_summary:
                cross_analysis_prompt = f"""Analyze the relationships and patterns across these {len(content_summary)} digital assets:

"""
                
                for i, item in enumerate(content_summary, 1):
                    cross_analysis_prompt += f"""
{i}. {item['file']} ({item['type']})
   Quality Score: {item['quality']:.2f}
   Insights: {item['insights'][:200]}...
   Analysis: {item['analysis'][:200]}...
"""
                
                cross_analysis_prompt += """

Provide comprehensive cross-analysis including:
1. Common themes and patterns across all assets
2. Content relationships and dependencies
3. Quality assessment comparison
4. Recommended organization or categorization
5. Potential use cases for the collection
6. Missing elements or gaps in the content set
7. Actionable insights for content strategy

Format as structured analysis with clear sections."""
                
                try:
                    cross_analysis_result = await self.ai_enhancer.text_generator.generate(
                        prompt=cross_analysis_prompt,
                        temperature=0.3
                    )
                    
                    return {
                        'ai_cross_analysis': cross_analysis_result,
                        'asset_count': len(content_summary),
                        'average_quality': sum(item['quality'] for item in content_summary) / len(content_summary),
                        'asset_types': list(set(item['type'] for item in content_summary)),
                        'analysis_confidence': 0.85
                    }
                    
                except Exception as e:
                    logger.error(f"AI cross-analysis failed: {e}")
                    return {'error': f'AI cross-analysis failed: {e}'}
            
            return {'message': 'AI enhancement disabled or insufficient content for cross-analysis'}
            
        except Exception as e:
            logger.error(f"Enhanced cross-analysis failed: {e}")
            return {'error': str(e)}
    
    async def get_comprehensive_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive capabilities of the enhanced processor."""
        traditional_caps = await self.unified_processor.get_processing_capabilities()
        
        return {
            'traditional_capabilities': traditional_caps,
            'ai_enhancement_capabilities': self.ai_enhancer.get_enhancement_capabilities(),
            'enhanced_features': [
                'intelligent_content_understanding',
                'cross_asset_correlation_analysis',
                'ai_powered_insights_generation',
                'quality_assessment_and_recommendations',
                'automated_categorization_and_tagging',
                'comprehensive_document_analysis'
            ],
            'processing_modes': ['traditional_only', 'ai_enhanced', 'comprehensive'],
            'ai_enhancement_enabled': self.enable_ai_enhancement
        }