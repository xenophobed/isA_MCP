#!/usr/bin/env python3
"""
Unified Asset Processor

Central processor that orchestrates processing of all digital asset types
with intelligent routing, parallel processing, and comprehensive analysis.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import time

# Import all specialized processors
from .pdf_processor import PDFProcessor
from .image_processor import ImageProcessor
from .audio_processor import AudioProcessor
from .video_processor import VideoProcessor
from .office_processor import OfficeProcessor
from .table_processor import TableProcessor
from .markdown_processor import MarkdownProcessor
from .text_processor import TextProcessor
from .asset_detector import AssetDetector

logger = logging.getLogger(__name__)

class ProcessingMode(Enum):
    """Processing modes for different workloads"""
    FAST = "fast"              # Quick processing, basic features
    COMPREHENSIVE = "comprehensive"  # Full analysis with all features
    SELECTIVE = "selective"    # User-specified features only
    BATCH = "batch"           # Optimized for batch processing

@dataclass
class ProcessingRequest:
    """Processing request configuration"""
    file_path: str
    processing_mode: ProcessingMode
    requested_features: List[str]
    output_format: str
    metadata: Dict[str, Any]

@dataclass
class UnifiedResult:
    """Unified processing result"""
    file_path: str
    asset_type: str
    success: bool
    results: Dict[str, Any]
    metadata: Dict[str, Any]
    processing_time: float
    features_processed: List[str]
    error: Optional[str] = None

class UnifiedAssetProcessor:
    """
    Unified processor that handles all digital asset types with intelligent
    routing, parallel processing, and comprehensive analysis capabilities.
    
    Features:
    - Automatic asset type detection
    - Intelligent processing pipeline routing
    - Parallel and batch processing
    - Feature-based processing control
    - Cross-asset analysis and correlation
    - Multi-format output generation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize all specialized processors
        self.asset_detector = AssetDetector()
        self.pdf_processor = PDFProcessor(self.config.get('pdf', {}))
        self.image_processor = ImageProcessor(self.config.get('image', {}))
        self.audio_processor = AudioProcessor(self.config.get('audio', {}))
        self.video_processor = VideoProcessor(self.config.get('video', {}))
        self.office_processor = OfficeProcessor(self.config.get('office', {}))
        self.table_processor = TableProcessor(self.config.get('table', {}))
        self.markdown_processor = MarkdownProcessor(self.config.get('markdown', {}))
        self.text_processor = TextProcessor(self.config.get('text', {}))
        
        # Processing settings
        self.max_parallel_jobs = self.config.get('max_parallel_jobs', 4)
        self.enable_cross_analysis = self.config.get('enable_cross_analysis', True)
        self.cache_results = self.config.get('cache_results', True)
        self.timeout_seconds = self.config.get('timeout_seconds', 300)
        
        # Feature mapping
        self.feature_map = {
            'text_extraction': ['pdf', 'image', 'office', 'video'],
            'object_detection': ['image', 'video'],
            'speech_recognition': ['audio', 'video'],
            'table_detection': ['pdf', 'image', 'office'],
            'structure_analysis': ['pdf', 'office'],
            'quality_assessment': ['image', 'audio', 'video'],
            'metadata_extraction': ['all'],
            'content_analysis': ['all']
        }
        
        logger.info("Unified Asset Processor initialized")
    
    async def process_asset(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process any digital asset with automatic type detection and routing.
        
        Args:
            file_path: Path to the asset file
            options: Processing options and configuration
            
        Returns:
            Comprehensive processing results
        """
        start_time = time.time()
        
        try:
            options = options or {}
            
            # Validate file existence
            if not Path(file_path).exists():
                return {
                    'file_path': file_path,
                    'success': False,
                    'error': 'File not found',
                    'processing_time': time.time() - start_time
                }
            
            # Step 1: Detect asset type
            asset_type = await self.asset_detector.detect_asset_type(file_path)
            if asset_type.value == 'unknown':
                return {
                    'file_path': file_path,
                    'success': False,
                    'error': 'Unsupported asset type',
                    'processing_time': time.time() - start_time
                }
            
            # Step 2: Create processing request
            processing_request = await self._create_processing_request(file_path, asset_type, options)
            
            # Step 3: Route to appropriate processor(s)
            results = await self._route_processing(processing_request)
            
            # Step 4: Post-process and enhance results
            enhanced_results = await self._enhance_results(results, processing_request)
            
            # Step 5: Generate unified output
            unified_result = await self._generate_unified_output(enhanced_results, processing_request)
            
            return {
                'file_path': file_path,
                'asset_type': asset_type.value,
                'success': True,
                'results': unified_result,
                'processing_time': time.time() - start_time,
                'features_processed': processing_request.requested_features
            }
            
        except Exception as e:
            logger.error(f"Asset processing failed: {e}")
            return {
                'file_path': file_path,
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    async def process_batch(self, file_paths: List[str], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process multiple assets in parallel.
        
        Args:
            file_paths: List of file paths to process
            options: Processing options
            
        Returns:
            Batch processing results
        """
        start_time = time.time()
        
        try:
            options = options or {}
            options['processing_mode'] = ProcessingMode.BATCH
            
            # Create semaphore for parallel processing
            semaphore = asyncio.Semaphore(self.max_parallel_jobs)
            
            async def process_single(file_path: str) -> Dict[str, Any]:
                async with semaphore:
                    return await self.process_asset(file_path, options)
            
            # Process all files in parallel
            tasks = [process_single(fp) for fp in file_paths]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze batch results
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
            
            # Cross-asset analysis if enabled
            cross_analysis = {}
            if self.enable_cross_analysis and len(successful_results) > 1:
                cross_analysis = await self._perform_cross_analysis(successful_results)
            
            return {
                'total_files': len(file_paths),
                'successful_count': len(successful_results),
                'failed_count': len(failed_results),
                'successful_results': successful_results,
                'failed_results': failed_results,
                'cross_analysis': cross_analysis,
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return {
                'total_files': len(file_paths) if file_paths else 0,
                'successful_count': 0,
                'failed_count': len(file_paths) if file_paths else 0,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    async def analyze_content_correlation(self, file_paths: List[str], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze content correlation across multiple assets.
        
        Args:
            file_paths: List of file paths to analyze
            options: Analysis options
            
        Returns:
            Content correlation analysis results
        """
        try:
            # Process all assets first
            batch_result = await self.process_batch(file_paths, options)
            
            if not batch_result.get('successful_results'):
                return {'error': 'No successful results to analyze', 'success': False}
            
            # Perform correlation analysis
            correlations = await self._analyze_content_correlations(batch_result['successful_results'])
            
            return {
                'correlations': correlations,
                'asset_count': len(batch_result['successful_results']),
                'correlation_score': correlations.get('overall_score', 0.0),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Content correlation analysis failed: {e}")
            return {'error': str(e), 'success': False}
    
    async def _create_processing_request(self, file_path: str, asset_type, options: Dict[str, Any]) -> ProcessingRequest:
        """Create a processing request based on asset type and options."""
        try:
            # Determine processing mode
            mode_str = options.get('processing_mode', 'comprehensive')
            processing_mode = ProcessingMode(mode_str) if isinstance(mode_str, str) else mode_str
            
            # Determine requested features
            if 'features' in options:
                requested_features = options['features']
            else:
                # Auto-determine features based on processing mode and asset type
                requested_features = await self._determine_features(asset_type, processing_mode)
            
            # Get metadata
            metadata = await self.asset_detector.get_asset_metadata(file_path)
            metadata.update(options.get('metadata', {}))
            
            return ProcessingRequest(
                file_path=file_path,
                processing_mode=processing_mode,
                requested_features=requested_features,
                output_format=options.get('output_format', 'comprehensive'),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Processing request creation failed: {e}")
            return ProcessingRequest(
                file_path=file_path,
                processing_mode=ProcessingMode.FAST,
                requested_features=['basic_analysis'],
                output_format='basic',
                metadata={}
            )
    
    async def _determine_features(self, asset_type, processing_mode: ProcessingMode) -> List[str]:
        """Determine which features to process based on asset type and mode."""
        try:
            if processing_mode == ProcessingMode.FAST:
                feature_sets = {
                    'pdf': ['text_extraction'],
                    'image': ['text_extraction'],
                    'audio': ['speech_recognition'],
                    'video': ['speech_recognition'],
                    'office': ['text_extraction'],
                    'default': ['text_extraction']
                }
            elif processing_mode == ProcessingMode.COMPREHENSIVE:
                feature_sets = {
                    'pdf': ['text_extraction', 'table_detection', 'structure_analysis', 'metadata_extraction'],
                    'image': ['text_extraction', 'object_detection', 'quality_assessment', 'metadata_extraction'],
                    'audio': ['speech_recognition', 'quality_assessment', 'metadata_extraction'],
                    'video': ['speech_recognition', 'object_detection', 'quality_assessment', 'metadata_extraction'],
                    'office': ['text_extraction', 'structure_analysis', 'table_detection', 'metadata_extraction'],
                    'default': ['text_extraction', 'metadata_extraction']
                }
            else:
                # Batch mode - optimized features
                feature_sets = {
                    'pdf': ['text_extraction', 'metadata_extraction'],
                    'image': ['text_extraction', 'metadata_extraction'],
                    'audio': ['speech_recognition', 'metadata_extraction'],
                    'video': ['speech_recognition', 'metadata_extraction'],
                    'office': ['text_extraction', 'metadata_extraction'],
                    'default': ['text_extraction', 'metadata_extraction']
                }
            
            asset_key = asset_type.value if hasattr(asset_type, 'value') else str(asset_type)
            return feature_sets.get(asset_key, feature_sets['default'])
            
        except Exception as e:
            logger.error(f"Feature determination failed: {e}")
            return ['text_extraction']
    
    async def _route_processing(self, request: ProcessingRequest) -> Dict[str, Any]:
        """Route processing to appropriate specialized processors."""
        try:
            results = {}
            asset_path = Path(request.file_path)
            asset_type = asset_path.suffix.lower()
            
            # Create options for processors
            processor_options = {
                'features': request.requested_features,
                'mode': request.processing_mode.value,
                **request.metadata
            }
            
            # Route to appropriate processor(s)
            if asset_type in ['.pdf']:
                if 'text_extraction' in request.requested_features:
                    results['pdf_text'] = await self.pdf_processor.extract_native_pdf_text(request.file_path, processor_options)
                if 'table_detection' in request.requested_features:
                    results['pdf_tables'] = await self.table_processor.extract_tables_from_pdf(request.file_path, processor_options)
                if 'structure_analysis' in request.requested_features:
                    results['pdf_structure'] = await self.pdf_processor.analyze_pdf_structure(request.file_path, processor_options)
            
            elif asset_type in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                if 'text_extraction' in request.requested_features:
                    results['image_text'] = await self.image_processor.extract_text(request.file_path, processor_options)
                if 'object_detection' in request.requested_features:
                    results['image_objects'] = await self.image_processor.detect_objects(request.file_path, processor_options)
                if 'quality_assessment' in request.requested_features:
                    results['image_analysis'] = await self.image_processor.analyze_image(request.file_path, processor_options)
            
            elif asset_type in ['.mp3', '.wav', '.flac', '.m4a']:
                if 'speech_recognition' in request.requested_features:
                    results['audio_transcript'] = await self.audio_processor.transcribe_speech(request.file_path, processor_options)
                if 'quality_assessment' in request.requested_features:
                    results['audio_analysis'] = await self.audio_processor.analyze_audio(request.file_path, processor_options)
            
            elif asset_type in ['.mp4', '.avi', '.mov', '.mkv']:
                if 'speech_recognition' in request.requested_features:
                    results['video_analysis'] = await self.video_processor.analyze_video(request.file_path, processor_options)
                if 'object_detection' in request.requested_features:
                    results['video_objects'] = await self.video_processor.detect_objects(request.file_path, processor_options)
            
            elif asset_type in ['.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt']:
                if 'text_extraction' in request.requested_features:
                    results['office_text'] = await self.office_processor.extract_text(request.file_path, processor_options)
                if 'structure_analysis' in request.requested_features:
                    results['office_structure'] = await self.office_processor.analyze_structure(request.file_path, processor_options)
                if 'table_detection' in request.requested_features and asset_type in ['.xlsx', '.xls']:
                    results['office_analysis'] = await self.office_processor.analyze_document(request.file_path, processor_options)
            
            elif asset_type in ['.txt', '.text']:
                if 'text_extraction' in request.requested_features:
                    results['text_content'] = await self.text_processor.extract_text(request.file_path, processor_options)
                if 'content_analysis' in request.requested_features:
                    results['text_analysis'] = await self.text_processor.analyze_text(request.file_path, processor_options)
            
            elif asset_type in ['.md', '.markdown']:
                if 'text_extraction' in request.requested_features:
                    results['text_content'] = await self.text_processor.extract_text(request.file_path, processor_options)
                if 'content_analysis' in request.requested_features:
                    results['text_analysis'] = await self.text_processor.analyze_text(request.file_path, processor_options)
                if 'structure_analysis' in request.requested_features:
                    results['markdown_structure'] = await self.markdown_processor.analyze_markdown(request.file_path, processor_options)
            
            # Always extract metadata if requested
            if 'metadata_extraction' in request.requested_features:
                results['metadata'] = await self.asset_detector.get_asset_metadata(request.file_path)
            
            return results
            
        except Exception as e:
            logger.error(f"Processing routing failed: {e}")
            return {'error': str(e)}
    
    async def _enhance_results(self, results: Dict[str, Any], request: ProcessingRequest) -> Dict[str, Any]:
        """Enhance and post-process results."""
        try:
            enhanced = results.copy()
            
            # Extract and combine text from all sources
            all_text = []
            for key, value in results.items():
                if isinstance(value, dict):
                    if 'text' in value:
                        all_text.append(value['text'])
                    elif 'transcript' in value:
                        all_text.append(value['transcript'])
                    elif 'full_text' in value:
                        all_text.append(value['full_text'])
            
            if all_text:
                enhanced['combined_text'] = '\\n\\n'.join(filter(None, all_text))
                enhanced['total_text_length'] = sum(len(text) for text in all_text)
                enhanced['text_sources'] = list(results.keys())
            
            # Quality scoring
            enhanced['quality_score'] = await self._calculate_quality_score(results)
            
            # Processing summary
            enhanced['processing_summary'] = {
                'features_processed': request.requested_features,
                'processing_mode': request.processing_mode.value,
                'successful_extractions': len([k for k, v in results.items() if isinstance(v, dict) and v.get('success', True)]),
                'failed_extractions': len([k for k, v in results.items() if isinstance(v, dict) and not v.get('success', True)])
            }
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Result enhancement failed: {e}")
            return results
    
    async def _generate_unified_output(self, results: Dict[str, Any], request: ProcessingRequest) -> Dict[str, Any]:
        """Generate unified output in requested format."""
        try:
            if request.output_format == 'markdown':
                # Generate markdown output
                markdown_result = self.markdown_processor.generate_markdown(results)
                return {
                    'format': 'markdown',
                    'content': markdown_result.markdown,
                    'structure': markdown_result.structure,
                    'raw_results': results
                }
            else:
                # Default comprehensive format
                return {
                    'format': 'comprehensive',
                    'content': results,
                    'summary': {
                        'file_path': request.file_path,
                        'asset_type': Path(request.file_path).suffix.lower(),
                        'features_processed': request.requested_features,
                        'text_extracted': bool(results.get('combined_text')),
                        'text_length': len(results.get('combined_text', '')),
                        'quality_score': results.get('quality_score', 0.0)
                    }
                }
                
        except Exception as e:
            logger.error(f"Unified output generation failed: {e}")
            return {'error': str(e), 'raw_results': results}
    
    async def _calculate_quality_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall quality score for processing results."""
        try:
            scores = []
            
            # Extract quality metrics from different processors
            for key, value in results.items():
                if isinstance(value, dict):
                    if 'quality_score' in value:
                        scores.append(value['quality_score'])
                    elif 'confidence' in value:
                        scores.append(value['confidence'])
                    elif 'success' in value:
                        scores.append(1.0 if value['success'] else 0.0)
            
            return sum(scores) / len(scores) if scores else 0.0
            
        except Exception as e:
            logger.error(f"Quality score calculation failed: {e}")
            return 0.0
    
    async def _perform_cross_analysis(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform cross-asset analysis to find correlations and patterns."""
        try:
            cross_analysis = {
                'asset_types': {},
                'common_themes': [],
                'text_similarities': [],
                'temporal_analysis': {},
                'content_clusters': []
            }
            
            # Analyze asset type distribution
            for result in results:
                asset_type = result.get('asset_type', 'unknown')
                cross_analysis['asset_types'][asset_type] = cross_analysis['asset_types'].get(asset_type, 0) + 1
            
            # Extract all text content for analysis
            text_contents = []
            for result in results:
                if result.get('success') and 'results' in result:
                    content = result['results'].get('content', {})
                    if isinstance(content, dict) and 'combined_text' in content:
                        text_contents.append({
                            'file_path': result.get('file_path', ''),
                            'text': content['combined_text'],
                            'asset_type': result.get('asset_type', 'unknown')
                        })
            
            # Simple theme analysis (would use more sophisticated NLP)
            if text_contents:
                all_text = ' '.join(item['text'] for item in text_contents)
                words = all_text.lower().split()
                word_freq = {}
                for word in words:
                    if len(word) > 3:  # Filter short words
                        word_freq[word] = word_freq.get(word, 0) + 1
                
                # Get top themes
                common_themes = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
                cross_analysis['common_themes'] = [{'word': word, 'frequency': freq} for word, freq in common_themes]
            
            return cross_analysis
            
        except Exception as e:
            logger.error(f"Cross-analysis failed: {e}")
            return {}
    
    async def _analyze_content_correlations(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze content correlations between assets."""
        try:
            correlations = {
                'text_similarity_matrix': [],
                'common_entities': [],
                'temporal_correlations': [],
                'overall_score': 0.0
            }
            
            # Extract text contents for similarity analysis
            text_items = []
            for result in results:
                if result.get('success') and 'results' in result:
                    content = result['results'].get('content', {})
                    if isinstance(content, dict) and 'combined_text' in content:
                        text_items.append({
                            'file': Path(result.get('file_path', '')).name,
                            'text': content['combined_text']
                        })
            
            # Simple text similarity (would use more sophisticated methods)
            if len(text_items) > 1:
                similarity_matrix = []
                for i, item1 in enumerate(text_items):
                    row = []
                    for j, item2 in enumerate(text_items):
                        if i == j:
                            similarity = 1.0
                        else:
                            # Simple word overlap similarity
                            words1 = set(item1['text'].lower().split())
                            words2 = set(item2['text'].lower().split())
                            if words1 and words2:
                                similarity = len(words1.intersection(words2)) / len(words1.union(words2))
                            else:
                                similarity = 0.0
                        row.append(similarity)
                    similarity_matrix.append(row)
                
                correlations['text_similarity_matrix'] = {
                    'files': [item['file'] for item in text_items],
                    'matrix': similarity_matrix
                }
                
                # Calculate overall correlation score
                if similarity_matrix:
                    total_similarities = []
                    for i in range(len(similarity_matrix)):
                        for j in range(i + 1, len(similarity_matrix[i])):
                            total_similarities.append(similarity_matrix[i][j])
                    
                    correlations['overall_score'] = sum(total_similarities) / len(total_similarities) if total_similarities else 0.0
            
            return correlations
            
        except Exception as e:
            logger.error(f"Content correlation analysis failed: {e}")
            return {'overall_score': 0.0}
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get all supported formats by category."""
        return {
            'pdf': self.pdf_processor.get_supported_formats(),
            'image': self.image_processor.get_supported_formats(),
            'audio': self.audio_processor.get_supported_formats(),
            'video': self.video_processor.get_supported_formats(),
            'office': self.office_processor.get_supported_formats(),
            'table': self.table_processor.get_supported_formats()
        }
    
    def get_available_features(self) -> Dict[str, List[str]]:
        """Get all available processing features."""
        return self.feature_map.copy()
    
    async def get_processing_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive processing capabilities."""
        return {
            'supported_formats': self.get_supported_formats(),
            'available_features': self.get_available_features(),
            'processing_modes': [mode.value for mode in ProcessingMode],
            'max_parallel_jobs': self.max_parallel_jobs,
            'cross_analysis_enabled': self.enable_cross_analysis,
            'timeout_seconds': self.timeout_seconds
        }