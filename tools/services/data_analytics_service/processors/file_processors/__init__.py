"""
File processors for data analytics service
"""

from .pdf_processor import PDFProcessor
from .markdown_processor import MarkdownProcessor
from .regex_extractor import RegexExtractor, Entity, RelationType, Relation

# ImageProcessor requires cv2 (OpenCV) - make it optional
try:
    from .image_processor import ImageProcessor
    IMAGE_PROCESSOR_AVAILABLE = True
except ImportError:
    ImageProcessor = None
    IMAGE_PROCESSOR_AVAILABLE = False

# AudioProcessor may have optional dependencies
try:
    from .audio_processor import AudioProcessor
    AUDIO_PROCESSOR_AVAILABLE = True
except ImportError:
    AudioProcessor = None
    AUDIO_PROCESSOR_AVAILABLE = False

# VideoProcessor requires cv2 (OpenCV) - make it optional
try:
    from .video_processor import VideoProcessor
    VIDEO_PROCESSOR_AVAILABLE = True
except ImportError:
    VideoProcessor = None
    VIDEO_PROCESSOR_AVAILABLE = False

# TableProcessor requires cv2 (OpenCV) - make it optional
try:
    from .table_processor import TableProcessor
    TABLE_PROCESSOR_AVAILABLE = True
except ImportError:
    TableProcessor = None
    TABLE_PROCESSOR_AVAILABLE = False

from .office_processor import OfficeProcessor
from .text_processor import TextProcessor
from .asset_detector import AssetDetector
from .unified_asset_processor import UnifiedAssetProcessor, ProcessingMode
from .ai_enhanced_processor import AIEnhancedProcessor
from .enhanced_unified_processor import EnhancedUnifiedProcessor

__all__ = [
    'PDFProcessor', 
    'MarkdownProcessor', 
    'RegexExtractor', 
    'Entity', 
    'RelationType', 
    'Relation',
    'OfficeProcessor',
    'TextProcessor',
    'AssetDetector',
    'UnifiedAssetProcessor',
    'ProcessingMode',
    'AIEnhancedProcessor',
    'EnhancedUnifiedProcessor'
]

# Add optional processors to __all__ only if available
if IMAGE_PROCESSOR_AVAILABLE:
    __all__.append('ImageProcessor')
if AUDIO_PROCESSOR_AVAILABLE:
    __all__.append('AudioProcessor')
if VIDEO_PROCESSOR_AVAILABLE:
    __all__.append('VideoProcessor')
if TABLE_PROCESSOR_AVAILABLE:
    __all__.append('TableProcessor')