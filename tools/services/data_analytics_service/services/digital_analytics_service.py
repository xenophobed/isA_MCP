#!/usr/bin/env python3
"""
Digital Analytics Engine

A comprehensive three-layer architecture for analyzing various digital assets:
- Layer 1: Digital Asset Preprocessing (file type detection, scan vs print identification)
- Layer 2: Specific Processing (OCR, table transformer, VLM for images)
- Layer 3: LLM Summarization and Extraction

Supports: PDF, PPT, images, audio, video, and other digital assets
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Import models
from .models.base_models import AssetType

# Layer imports
from .processors.asset_detector import AssetDetector
from .processors.format_analyzer import FormatAnalyzer
from .processors.ocr_processor import OCRProcessor
from .processors.pdf_processor import PDFProcessor
from .processors.table_processor import TableProcessor
from .processors.vlm_processor import VLMProcessor
from .processors.audio_processor import AudioProcessor
from .processors.video_processor import VideoProcessor
from .processors.llm_extractor import LLMExtractor
from .processors.content_summarizer import ContentSummarizer

logger = logging.getLogger(__name__)

@dataclass
class DigitalAsset:
    """Digital asset metadata"""
    file_path: str
    asset_type: AssetType
    format_details: Dict[str, Any]
    preprocessing_metadata: Dict[str, Any]
    processing_results: Dict[str, Any]
    extraction_results: Dict[str, Any]

class DigitalAnalyticsEngine:
    """
    Central engine for digital asset analysis.
    
    Three-layer architecture:
    1. Preprocessing: Asset detection and format analysis
    2. Processing: Specific processing based on asset type
    3. Extraction: LLM-based summarization and extraction
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.stats = {
            'assets_processed': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'processing_time_by_layer': {
                'preprocessing': 0.0,
                'processing': 0.0,
                'extraction': 0.0
            }
        }
        
        # Initialize layer components
        self.asset_detector = AssetDetector()
        self.format_analyzer = FormatAnalyzer()
        self.ocr_processor = OCRProcessor()
        self.pdf_processor = PDFProcessor()
        self.table_processor = TableProcessor()
        self.vlm_processor = VLMProcessor()
        self.audio_processor = AudioProcessor()
        self.video_processor = VideoProcessor()
        self.llm_extractor = LLMExtractor()
        self.content_summarizer = ContentSummarizer()
    
    async def analyze_digital_asset(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> DigitalAsset:
        """
        Complete three-layer analysis of a digital asset.
        
        Args:
            file_path: Path to the digital asset
            options: Processing options
            
        Returns:
            Complete digital asset analysis
        """
        try:
            # Layer 1: Preprocessing
            asset = await self._layer1_preprocessing(file_path, options)
            
            # Layer 2: Processing
            asset = await self._layer2_processing(asset, options)
            
            # Layer 3: Extraction
            asset = await self._layer3_extraction(asset, options)
            
            self._update_stats(asset)
            return asset
            
        except Exception as e:
            logger.error(f"Digital asset analysis failed: {e}")
            return DigitalAsset(
                file_path=file_path,
                asset_type=AssetType.UNKNOWN,
                format_details={'error': str(e)},
                preprocessing_metadata={},
                processing_results={},
                extraction_results={}
            )
    
    async def _layer1_preprocessing(self, file_path: str, options: Dict[str, Any]) -> DigitalAsset:
        """
        Layer 1: Digital Asset Preprocessing
        
        - Detect file type and format
        - Identify scan vs print for PDFs
        - Analyze layout regions for images
        - Determine processing strategy
        """
        import time
        start_time = time.time()
        
        try:
            # Detect asset type
            asset_type = await self.asset_detector.detect_asset_type(file_path)
            
            # Analyze format specifics
            format_details = await self.format_analyzer.analyze_format(file_path, asset_type)
            
            # Create digital asset object
            asset = DigitalAsset(
                file_path=file_path,
                asset_type=asset_type,
                format_details=format_details,
                preprocessing_metadata={
                    'preprocessing_time': time.time() - start_time,
                    'strategy': self._determine_processing_strategy(asset_type, format_details)
                },
                processing_results={},
                extraction_results={}
            )
            
            self.stats['processing_time_by_layer']['preprocessing'] += time.time() - start_time
            return asset
            
        except Exception as e:
            logger.error(f"Layer 1 preprocessing failed: {e}")
            raise
    
    async def _layer2_processing(self, asset: DigitalAsset, options: Dict[str, Any]) -> DigitalAsset:
        """
        Layer 2: Specific Processing
        
        - OCR for text extraction
        - Table transformer for tables
        - VLM for image analysis
        - Audio processing for voice
        - Video processing for video frames
        """
        import time
        start_time = time.time()
        
        try:
            processing_strategy = asset.preprocessing_metadata.get('strategy', {})
            
            if asset.asset_type == AssetType.PDF_SCANNED:
                # Scanned PDF: OCR everything
                ocr_results = await self.ocr_processor.process_scanned_pdf(asset.file_path)
                table_results = await self.table_processor.extract_from_ocr(ocr_results)
                asset.processing_results = {
                    'ocr_text': ocr_results,
                    'tables': table_results,
                    'method': 'full_ocr'
                }
                
            elif asset.asset_type == AssetType.PDF_NATIVE:
                # Native PDF: Extract text directly, OCR only images
                text_results = await self._extract_native_pdf_text(asset.file_path)
                image_results = await self.vlm_processor.process_pdf_images(asset.file_path)
                asset.processing_results = {
                    'text': text_results,
                    'images': image_results,
                    'method': 'hybrid'
                }
                
            elif asset.asset_type == AssetType.IMAGE:
                # Image: Layout detection + OCR + VLM
                layout_results = await self.ocr_processor.detect_layout_regions(asset.file_path)
                vlm_results = await self.vlm_processor.analyze_image_content(asset.file_path)
                asset.processing_results = {
                    'layout': layout_results,
                    'visual_analysis': vlm_results,
                    'method': 'vision_analysis'
                }
                
            elif asset.asset_type == AssetType.POWERPOINT:
                # PowerPoint: Extract text + process images
                text_results = await self._extract_ppt_text(asset.file_path)
                image_results = await self.vlm_processor.process_ppt_images(asset.file_path)
                asset.processing_results = {
                    'slides': text_results,
                    'images': image_results,
                    'method': 'structured_extraction'
                }
                
            elif asset.asset_type == AssetType.AUDIO:
                # Audio: Speaker identification + emotion + content
                audio_results = await self.audio_processor.analyze_audio(asset.file_path)
                asset.processing_results = {
                    'transcript': audio_results.get('transcript'),
                    'speakers': audio_results.get('speakers'),
                    'emotions': audio_results.get('emotions'),
                    'method': 'audio_analysis'
                }
                
            elif asset.asset_type == AssetType.VIDEO:
                # Video: Frame analysis + audio processing
                video_results = await self.video_processor.analyze_video(asset.file_path)
                asset.processing_results = {
                    'frames': video_results.get('frames'),
                    'audio': video_results.get('audio'),
                    'objects': video_results.get('objects'),
                    'method': 'multimodal_analysis'
                }
            
            processing_time = time.time() - start_time
            asset.processing_results['processing_time'] = processing_time
            self.stats['processing_time_by_layer']['processing'] += processing_time
            
            return asset
            
        except Exception as e:
            logger.error(f"Layer 2 processing failed: {e}")
            raise
    
    async def _layer3_extraction(self, asset: DigitalAsset, options: Dict[str, Any]) -> DigitalAsset:
        """
        Layer 3: LLM Summarization and Extraction
        
        - Content summarization
        - Key information extraction
        - Structured data generation
        - Thematic analysis
        """
        import time
        start_time = time.time()
        
        try:
            # Prepare content for LLM processing
            content_for_llm = self._prepare_content_for_llm(asset)
            
            # Generate summary
            summary_results = await self.content_summarizer.summarize_content(
                content_for_llm, 
                asset.asset_type
            )
            
            # Extract key information
            extraction_results = await self.llm_extractor.extract_structured_data(
                content_for_llm,
                asset.asset_type,
                options.get('extraction_schema')
            )
            
            # Thematic analysis
            thematic_results = await self.llm_extractor.analyze_themes(
                content_for_llm,
                asset.asset_type
            )
            
            asset.extraction_results = {
                'summary': summary_results,
                'structured_data': extraction_results,
                'themes': thematic_results,
                'confidence_scores': self._calculate_confidence_scores(asset),
                'extraction_time': time.time() - start_time
            }
            
            self.stats['processing_time_by_layer']['extraction'] += time.time() - start_time
            return asset
            
        except Exception as e:
            logger.error(f"Layer 3 extraction failed: {e}")
            raise
    
    def _determine_processing_strategy(self, asset_type: AssetType, format_details: Dict[str, Any]) -> Dict[str, Any]:
        """Determine optimal processing strategy based on asset type and format."""
        strategy = {
            'primary_method': 'unknown',
            'secondary_methods': [],
            'ai_services_required': []
        }
        
        if asset_type == AssetType.PDF_SCANNED:
            strategy.update({
                'primary_method': 'ocr',
                'secondary_methods': ['table_detection', 'layout_analysis'],
                'ai_services_required': ['ocr_service', 'table_transformer']
            })
        elif asset_type == AssetType.PDF_NATIVE:
            strategy.update({
                'primary_method': 'text_extraction',
                'secondary_methods': ['image_analysis'],
                'ai_services_required': ['vlm_service']
            })
        elif asset_type == AssetType.IMAGE:
            strategy.update({
                'primary_method': 'vision_analysis',
                'secondary_methods': ['ocr', 'layout_detection'],
                'ai_services_required': ['vlm_service', 'ocr_service']
            })
        elif asset_type == AssetType.AUDIO:
            strategy.update({
                'primary_method': 'speech_recognition',
                'secondary_methods': ['speaker_identification', 'emotion_analysis'],
                'ai_services_required': ['whisper_service', 'speaker_service']
            })
        elif asset_type == AssetType.VIDEO:
            strategy.update({
                'primary_method': 'multimodal_analysis',
                'secondary_methods': ['frame_analysis', 'audio_processing'],
                'ai_services_required': ['vlm_service', 'whisper_service', 'object_detection']
            })
        
        return strategy
    
    def _prepare_content_for_llm(self, asset: DigitalAsset) -> Dict[str, Any]:
        """Prepare processed content for LLM analysis."""
        content = {
            'asset_type': asset.asset_type.value,
            'file_path': asset.file_path,
            'processing_method': asset.processing_results.get('method', 'unknown')
        }
        
        # Add processed content based on asset type
        if asset.asset_type in [AssetType.PDF_SCANNED, AssetType.PDF_NATIVE]:
            content['text'] = asset.processing_results.get('text', '')
            content['tables'] = asset.processing_results.get('tables', [])
        elif asset.asset_type == AssetType.IMAGE:
            content['visual_analysis'] = asset.processing_results.get('visual_analysis', {})
            content['layout'] = asset.processing_results.get('layout', {})
        elif asset.asset_type == AssetType.AUDIO:
            content['transcript'] = asset.processing_results.get('transcript', '')
            content['speakers'] = asset.processing_results.get('speakers', [])
            content['emotions'] = asset.processing_results.get('emotions', [])
        elif asset.asset_type == AssetType.VIDEO:
            content['frames'] = asset.processing_results.get('frames', [])
            content['audio'] = asset.processing_results.get('audio', {})
            content['objects'] = asset.processing_results.get('objects', [])
        
        return content
    
    def _calculate_confidence_scores(self, asset: DigitalAsset) -> Dict[str, float]:
        """Calculate confidence scores for each processing layer."""
        # Mock implementation - would be based on actual processing results
        return {
            'preprocessing_confidence': 0.9,
            'processing_confidence': 0.8,
            'extraction_confidence': 0.85,
            'overall_confidence': 0.83
        }
    
    async def _extract_native_pdf_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text from native PDF using PyPDF."""
        # Mock implementation
        return {
            'pages': [],
            'total_text': '',
            'method': 'pypdf'
        }
    
    async def _extract_ppt_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text from PowerPoint slides."""
        # Mock implementation
        return {
            'slides': [],
            'total_text': '',
            'method': 'python-pptx'
        }
    
    def _update_stats(self, asset: DigitalAsset):
        """Update engine statistics."""
        self.stats['assets_processed'] += 1
        
        if asset.extraction_results:
            self.stats['successful_operations'] += 1
        else:
            self.stats['failed_operations'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine performance statistics."""
        return self.stats.copy()
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get engine capabilities."""
        return {
            'engine_version': '2.0.0',
            'supported_asset_types': [asset_type.value for asset_type in AssetType],
            'processing_layers': ['preprocessing', 'processing', 'extraction'],
            'ai_services': ['ocr', 'table_transformer', 'vlm', 'whisper', 'speaker_identification'],
            'statistics': self.stats
        }

# Global engine instance
_engine = None

def get_digital_analytics_engine(config: Optional[Dict[str, Any]] = None) -> DigitalAnalyticsEngine:
    """Get or create global digital analytics engine instance."""
    global _engine
    if _engine is None:
        _engine = DigitalAnalyticsEngine(config)
    return _engine

# Public API functions
async def analyze_digital_asset_complete(file_path: str, options: Optional[Dict[str, Any]] = None) -> DigitalAsset:
    """Complete three-layer analysis of a digital asset."""
    engine = get_digital_analytics_engine()
    return await engine.analyze_digital_asset(file_path, options or {})

def get_engine_capabilities() -> Dict[str, Any]:
    """Get comprehensive engine capabilities."""
    engine = get_digital_analytics_engine()
    return engine.get_capabilities()

def get_engine_stats() -> Dict[str, Any]:
    """Get engine performance statistics."""
    engine = get_digital_analytics_engine()
    return engine.get_stats()