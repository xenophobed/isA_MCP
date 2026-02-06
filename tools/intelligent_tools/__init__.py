"""
Intelligent Tools Package
AI-powered vision, audio, image generation, and video tools

This package organizes AI/ML tools into clear categories:
- vision_tools: Image analysis, OCR, object detection
- audio_tools: Audio transcription and analysis
- image_tools: AI image generation
- video_tools: Video processing (placeholder for future)

Service directories:
- vision/: Vision analysis services (ImageAnalyzer, UIDetector, OCRExtractor)
- audio/: Audio processing services (AudioAnalyzer)
- img/: Image generation services (AtomicImageIntelligence)
- language/: Language services (TextGenerator, TextSummarizer, EmbeddingGenerator)
"""

from .vision_tools import register_vision_tools, VisionTools
from .audio_tools import register_audio_tools, AudioTools
from .image_tools import register_image_tools, ImageTools
from .video_tools import register_video_tools, VideoTools

__all__ = [
    'register_vision_tools', 'VisionTools',
    'register_audio_tools', 'AudioTools',
    'register_image_tools', 'ImageTools',
    'register_video_tools', 'VideoTools',
]
