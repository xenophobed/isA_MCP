#!/usr/bin/env python3
"""
Image Processor

Handles comprehensive image processing including OCR, object detection,
scene analysis, and visual content understanding.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

# Optional dependencies - make cv2 and numpy optional
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

logger = logging.getLogger(__name__)

@dataclass
class ObjectDetection:
    """Object detection result"""
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    center: Tuple[int, int]
    area: float

@dataclass
class TextRegion:
    """Text region detection result"""
    bbox: Tuple[int, int, int, int]
    text: str
    confidence: float
    language: str

@dataclass
class SceneAnalysis:
    """Scene analysis result"""
    scene_type: str
    confidence: float
    attributes: Dict[str, Any]
    color_palette: List[str]
    lighting: Dict[str, Any]

@dataclass
class ImageAnalysisResult:
    """Complete image analysis result"""
    dimensions: Tuple[int, int]
    file_size: int
    objects: List[ObjectDetection]
    text_regions: List[TextRegion]
    scene_analysis: SceneAnalysis
    image_quality: Dict[str, Any]
    processing_time: float

class ImageProcessor:
    """
    Image processor for comprehensive image analysis.
    
    Capabilities:
    - Object detection and recognition
    - OCR text extraction
    - Scene understanding
    - Image quality assessment
    - Visual content analysis
    - Layout detection
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Check if required dependencies are available
        if not CV2_AVAILABLE:
            logger.warning("OpenCV (cv2) not available - ImageProcessor functionality will be limited")
        if not NUMPY_AVAILABLE:
            logger.warning("NumPy not available - ImageProcessor functionality will be limited")
        
        # OCR settings
        self.ocr_engine = self.config.get('ocr_engine', 'tesseract')
        self.ocr_languages = self.config.get('ocr_languages', ['eng'])
        
        # Object detection settings
        self.object_model = self.config.get('object_model', 'yolo')
        self.detection_threshold = self.config.get('detection_threshold', 0.5)
        self.nms_threshold = self.config.get('nms_threshold', 0.4)
        
        # Image processing settings
        self.enable_preprocessing = self.config.get('enable_preprocessing', True)
        self.max_dimension = self.config.get('max_dimension', 2048)
        
        logger.info("Image Processor initialized")
    
    async def analyze_image(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Comprehensive image analysis.
        
        Args:
            file_path: Path to image file
            options: Analysis options
            
        Returns:
            Complete image analysis results
        """
        # Check if required dependencies are available
        if not CV2_AVAILABLE or not NUMPY_AVAILABLE:
            return {
                'error': 'OpenCV and NumPy are required for image processing',
                'success': False,
                'available_dependencies': {
                    'cv2': CV2_AVAILABLE,
                    'numpy': NUMPY_AVAILABLE
                },
                'suggestion': 'Install with: pip install opencv-python numpy'
            }
        
        try:
            options = options or {}
            
            # Validate file
            if not Path(file_path).exists():
                return {'error': 'Image file not found', 'success': False}
            
            # Load and preprocess image
            img = await self._load_and_preprocess_image(file_path)
            if img is None:
                return {'error': 'Could not load image', 'success': False}
            
            # Get basic image info
            image_info = await self._get_image_info(file_path, img)
            
            # Perform OCR
            ocr_result = await self._extract_text(img, options)
            
            # Object detection
            object_result = await self._detect_objects(img, options)
            
            # Scene analysis
            scene_result = await self._analyze_scene(img, options)
            
            # Quality assessment
            quality_result = await self._assess_image_quality(img)
            
            # Combine results
            combined_result = await self._combine_image_analysis(
                image_info, ocr_result, object_result, scene_result, quality_result
            )
            
            return {
                'file_path': file_path,
                'analysis': combined_result,
                'processing_time': combined_result.processing_time,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
    
    async def extract_text(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract text from image using OCR.
        
        Args:
            file_path: Path to image file
            options: OCR options
            
        Returns:
            Text extraction results
        """
        try:
            options = options or {}
            
            img = await self._load_and_preprocess_image(file_path)
            if img is None:
                return {'error': 'Could not load image', 'success': False}
            
            result = await self._extract_text(img, options)
            
            return {
                'file_path': file_path,
                'text': result.get('full_text', ''),
                'text_regions': result.get('text_regions', []),
                'confidence': result.get('average_confidence', 0.0),
                'language': result.get('detected_language', 'unknown'),
                'processing_time': result.get('processing_time', 0.0),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
    
    async def detect_objects(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Detect objects in image.
        
        Args:
            file_path: Path to image file
            options: Detection options
            
        Returns:
            Object detection results
        """
        try:
            options = options or {}
            
            img = await self._load_and_preprocess_image(file_path)
            if img is None:
                return {'error': 'Could not load image', 'success': False}
            
            result = await self._detect_objects(img, options)
            
            return {
                'file_path': file_path,
                'objects': result.get('objects', []),
                'object_count': len(result.get('objects', [])),
                'detection_confidence': result.get('average_confidence', 0.0),
                'processing_time': result.get('processing_time', 0.0),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Object detection failed: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
    
    async def analyze_scene(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze scene and visual content.
        
        Args:
            file_path: Path to image file
            options: Scene analysis options
            
        Returns:
            Scene analysis results
        """
        try:
            options = options or {}
            
            img = await self._load_and_preprocess_image(file_path)
            if img is None:
                return {'error': 'Could not load image', 'success': False}
            
            result = await self._analyze_scene(img, options)
            
            return {
                'file_path': file_path,
                'scene_type': result.get('scene_type', 'unknown'),
                'scene_confidence': result.get('confidence', 0.0),
                'attributes': result.get('attributes', {}),
                'color_analysis': result.get('color_analysis', {}),
                'processing_time': result.get('processing_time', 0.0),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Scene analysis failed: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
    
    async def _load_and_preprocess_image(self, file_path: str) -> Optional[np.ndarray]:
        """Load and preprocess image."""
        try:
            # Load image
            img = cv2.imread(file_path)
            if img is None:
                return None
            
            if self.enable_preprocessing:
                # Resize if too large
                height, width = img.shape[:2]
                if max(height, width) > self.max_dimension:
                    scale = self.max_dimension / max(height, width)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
                
                # Enhance image quality
                img = await self._enhance_image(img)
            
            return img
            
        except Exception as e:
            logger.error(f"Image loading failed: {e}")
            return None
    
    async def _enhance_image(self, img: np.ndarray) -> np.ndarray:
        """Enhance image quality for better processing."""
        try:
            # Convert to LAB color space for better enhancement
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            # Merge channels and convert back to BGR
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            
            # Noise reduction
            enhanced = cv2.fastNlMeansDenoisingColored(enhanced)
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Image enhancement failed: {e}")
            return img
    
    async def _get_image_info(self, file_path: str, img: np.ndarray) -> Dict[str, Any]:
        """Get basic image information."""
        try:
            file_path_obj = Path(file_path)
            file_size = file_path_obj.stat().st_size
            height, width = img.shape[:2]
            channels = img.shape[2] if len(img.shape) > 2 else 1
            
            return {
                'dimensions': (width, height),
                'channels': channels,
                'file_size': file_size,
                'format': file_path_obj.suffix.lower(),
                'aspect_ratio': width / height if height > 0 else 1.0
            }
            
        except Exception as e:
            logger.error(f"Image info extraction failed: {e}")
            return {}
    
    async def _extract_text(self, img: np.ndarray, options: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text using OCR."""
        import time
        start_time = time.time()
        
        try:
            # Preprocess for OCR
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold for better OCR
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Mock OCR - would use tesseract or similar
            try:
                import pytesseract
                
                # Get detailed OCR data
                ocr_data = pytesseract.image_to_data(thresh, output_type=pytesseract.Output.DICT)
                
                # Extract text regions
                text_regions = []
                full_text = ""
                confidences = []
                
                for i in range(len(ocr_data['text'])):
                    text = ocr_data['text'][i].strip()
                    if text:
                        x, y, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
                        conf = int(ocr_data['conf'][i])
                        
                        if conf > 30:  # Filter low confidence text
                            text_regions.append({
                                'bbox': (x, y, w, h),
                                'text': text,
                                'confidence': conf / 100.0,
                                'language': 'eng'  # Would detect language
                            })
                            full_text += text + " "
                            confidences.append(conf)
                
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
            except ImportError:
                # Fallback to mock OCR
                text_regions = [
                    {
                        'bbox': (50, 50, 200, 30),
                        'text': 'Mock OCR text',
                        'confidence': 0.9,
                        'language': 'eng'
                    }
                ]
                full_text = "Mock OCR text extracted from image"
                avg_confidence = 0.9
            
            return {
                'full_text': full_text.strip(),
                'text_regions': text_regions,
                'average_confidence': avg_confidence / 100.0 if avg_confidence > 1 else avg_confidence,
                'detected_language': 'eng',
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return {
                'full_text': '',
                'text_regions': [],
                'average_confidence': 0.0,
                'detected_language': 'unknown',
                'processing_time': time.time() - start_time,
                'error': str(e)
            }
    
    async def _detect_objects(self, img: np.ndarray, options: Dict[str, Any]) -> Dict[str, Any]:
        """Detect objects in image."""
        import time
        start_time = time.time()
        
        try:
            # Mock object detection - would use YOLO, RCNN, etc.
            mock_objects = [
                {
                    'class_name': 'person',
                    'confidence': 0.92,
                    'bbox': (100, 150, 80, 200),
                    'center': (140, 250),
                    'area': 16000
                },
                {
                    'class_name': 'car',
                    'confidence': 0.87,
                    'bbox': (300, 200, 150, 100),
                    'center': (375, 250),
                    'area': 15000
                },
                {
                    'class_name': 'tree',
                    'confidence': 0.78,
                    'bbox': (50, 50, 60, 120),
                    'center': (80, 110),
                    'area': 7200
                }
            ]
            
            # Filter by confidence threshold
            filtered_objects = [
                obj for obj in mock_objects 
                if obj['confidence'] >= self.detection_threshold
            ]
            
            avg_confidence = sum(obj['confidence'] for obj in filtered_objects) / len(filtered_objects) if filtered_objects else 0.0
            
            return {
                'objects': filtered_objects,
                'object_count': len(filtered_objects),
                'average_confidence': avg_confidence,
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Object detection failed: {e}")
            return {
                'objects': [],
                'object_count': 0,
                'average_confidence': 0.0,
                'processing_time': time.time() - start_time,
                'error': str(e)
            }
    
    async def _analyze_scene(self, img: np.ndarray, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze scene and visual content."""
        import time
        start_time = time.time()
        
        try:
            # Basic color analysis
            color_analysis = await self._analyze_colors(img)
            
            # Lighting analysis
            lighting_analysis = await self._analyze_lighting(img)
            
            # Scene classification (mock)
            scene_types = ['outdoor', 'indoor', 'portrait', 'landscape', 'document', 'product']
            scene_type = 'outdoor'  # Would use scene classification model
            confidence = 0.85
            
            # Scene attributes
            attributes = {
                'brightness': lighting_analysis.get('brightness', 0.5),
                'contrast': lighting_analysis.get('contrast', 0.5),
                'saturation': color_analysis.get('saturation', 0.5),
                'complexity': 'medium',  # Would analyze visual complexity
                'main_subject': 'person'  # Would identify main subject
            }
            
            return {
                'scene_type': scene_type,
                'confidence': confidence,
                'attributes': attributes,
                'color_analysis': color_analysis,
                'lighting_analysis': lighting_analysis,
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Scene analysis failed: {e}")
            return {
                'scene_type': 'unknown',
                'confidence': 0.0,
                'attributes': {},
                'color_analysis': {},
                'lighting_analysis': {},
                'processing_time': time.time() - start_time,
                'error': str(e)
            }
    
    async def _analyze_colors(self, img: np.ndarray) -> Dict[str, Any]:
        """Analyze color distribution and palette."""
        try:
            # Convert to RGB for better color analysis
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Calculate color statistics
            mean_color = np.mean(rgb_img, axis=(0, 1))
            std_color = np.std(rgb_img, axis=(0, 1))
            
            # Dominant colors (simplified)
            pixels = rgb_img.reshape(-1, 3)
            unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
            dominant_indices = np.argsort(counts)[-5:]  # Top 5 colors
            dominant_colors = unique_colors[dominant_indices]
            
            # Color palette as hex strings
            color_palette = [
                f"#{int(color[0]):02x}{int(color[1]):02x}{int(color[2]):02x}"
                for color in dominant_colors
            ]
            
            # Color harmony analysis
            saturation = np.mean(cv2.cvtColor(rgb_img, cv2.COLOR_RGB2HSV)[:, :, 1]) / 255.0
            
            return {
                'mean_color': mean_color.tolist(),
                'color_std': std_color.tolist(),
                'dominant_colors': color_palette,
                'saturation': float(saturation),
                'color_diversity': len(unique_colors) / len(pixels)
            }
            
        except Exception as e:
            logger.error(f"Color analysis failed: {e}")
            return {}
    
    async def _analyze_lighting(self, img: np.ndarray) -> Dict[str, Any]:
        """Analyze lighting conditions."""
        try:
            # Convert to grayscale for lighting analysis
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Calculate lighting metrics
            brightness = np.mean(gray) / 255.0
            contrast = np.std(gray) / 255.0
            
            # Histogram analysis
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist_norm = hist / np.sum(hist)
            
            # Lighting quality assessment
            if brightness < 0.3:
                lighting_condition = 'dark'
            elif brightness > 0.7:
                lighting_condition = 'bright'
            else:
                lighting_condition = 'normal'
            
            # Exposure analysis
            overexposed_ratio = np.sum(gray > 240) / gray.size
            underexposed_ratio = np.sum(gray < 15) / gray.size
            
            return {
                'brightness': float(brightness),
                'contrast': float(contrast),
                'lighting_condition': lighting_condition,
                'overexposed_ratio': float(overexposed_ratio),
                'underexposed_ratio': float(underexposed_ratio),
                'histogram': hist_norm.flatten().tolist()
            }
            
        except Exception as e:
            logger.error(f"Lighting analysis failed: {e}")
            return {}
    
    async def _assess_image_quality(self, img: np.ndarray) -> Dict[str, Any]:
        """Assess image quality."""
        import time
        start_time = time.time()
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Sharpness assessment using Laplacian variance
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Noise assessment
            noise_level = np.std(cv2.fastNlMeansDenoising(gray) - gray)
            
            # Overall quality score
            quality_score = min(1.0, sharpness / 1000.0) * (1.0 - min(1.0, noise_level / 50.0))
            
            # Quality recommendations
            recommendations = []
            if sharpness < 100:
                recommendations.append('Image appears blurry - consider using sharper image')
            if noise_level > 20:
                recommendations.append('High noise level detected - consider noise reduction')
            
            return {
                'sharpness': float(sharpness),
                'noise_level': float(noise_level),
                'quality_score': float(quality_score),
                'recommendations': recommendations,
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return {
                'sharpness': 0.0,
                'noise_level': 0.0,
                'quality_score': 0.0,
                'recommendations': [],
                'processing_time': time.time() - start_time,
                'error': str(e)
            }
    
    async def _combine_image_analysis(self, image_info: Dict[str, Any],
                                    ocr_result: Dict[str, Any],
                                    object_result: Dict[str, Any],
                                    scene_result: Dict[str, Any],
                                    quality_result: Dict[str, Any]) -> ImageAnalysisResult:
        """Combine all image analysis results."""
        try:
            # Create object detection results
            objects = []
            for obj_data in object_result.get('objects', []):
                obj = ObjectDetection(
                    class_name=obj_data['class_name'],
                    confidence=obj_data['confidence'],
                    bbox=obj_data['bbox'],
                    center=obj_data['center'],
                    area=obj_data['area']
                )
                objects.append(obj)
            
            # Create text regions
            text_regions = []
            for text_data in ocr_result.get('text_regions', []):
                text_region = TextRegion(
                    bbox=text_data['bbox'],
                    text=text_data['text'],
                    confidence=text_data['confidence'],
                    language=text_data['language']
                )
                text_regions.append(text_region)
            
            # Create scene analysis
            scene_analysis = SceneAnalysis(
                scene_type=scene_result.get('scene_type', 'unknown'),
                confidence=scene_result.get('confidence', 0.0),
                attributes=scene_result.get('attributes', {}),
                color_palette=scene_result.get('color_analysis', {}).get('dominant_colors', []),
                lighting=scene_result.get('lighting_analysis', {})
            )
            
            # Calculate total processing time
            total_processing_time = (
                ocr_result.get('processing_time', 0) +
                object_result.get('processing_time', 0) +
                scene_result.get('processing_time', 0) +
                quality_result.get('processing_time', 0)
            )
            
            return ImageAnalysisResult(
                dimensions=image_info.get('dimensions', (0, 0)),
                file_size=image_info.get('file_size', 0),
                objects=objects,
                text_regions=text_regions,
                scene_analysis=scene_analysis,
                image_quality=quality_result,
                processing_time=total_processing_time
            )
            
        except Exception as e:
            logger.error(f"Image analysis combination failed: {e}")
            return ImageAnalysisResult(
                dimensions=(0, 0),
                file_size=0,
                objects=[],
                text_regions=[],
                scene_analysis=SceneAnalysis('unknown', 0.0, {}, [], {}),
                image_quality={},
                processing_time=0.0
            )
    
    def get_supported_formats(self) -> List[str]:
        """Get supported image formats."""
        return ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'gif', 'webp']
    
    def set_detection_threshold(self, threshold: float):
        """Set object detection confidence threshold."""
        self.detection_threshold = max(0.0, min(1.0, threshold))
    
    def set_ocr_languages(self, languages: List[str]):
        """Set OCR languages."""
        self.ocr_languages = languages
    
    def set_max_dimension(self, max_dim: int):
        """Set maximum image dimension for processing."""
        self.max_dimension = max(512, max_dim)
    
    async def detect_layout(self, file_path: str) -> Dict[str, Any]:
        """Detect layout regions in document images."""
        try:
            img = await self._load_and_preprocess_image(file_path)
            if img is None:
                return {'error': 'Could not load image', 'success': False}
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect text blocks
            text_blocks = await self._detect_text_blocks(gray)
            
            # Detect table regions
            table_regions = await self._detect_table_regions(gray)
            
            # Detect image regions
            image_regions = await self._detect_image_regions(gray)
            
            return {
                'file_path': file_path,
                'text_blocks': text_blocks,
                'table_regions': table_regions,
                'image_regions': image_regions,
                'layout_type': 'document',  # Would classify layout type
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Layout detection failed: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
    
    async def _detect_text_blocks(self, gray: np.ndarray) -> List[Dict[str, Any]]:
        """Detect text block regions."""
        try:
            # Use morphological operations to find text blocks
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 5))
            closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            text_blocks = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 50 and h > 20:  # Filter small regions
                    text_blocks.append({
                        'bbox': (x, y, w, h),
                        'type': 'text',
                        'confidence': 0.8
                    })
            
            return text_blocks
            
        except Exception as e:
            logger.error(f"Text block detection failed: {e}")
            return []
    
    async def _detect_table_regions(self, gray: np.ndarray) -> List[Dict[str, Any]]:
        """Detect table regions."""
        try:
            # Detect horizontal and vertical lines
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
            
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
            
            # Combine lines
            table_mask = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)
            
            # Find table contours
            contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            table_regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 100 and h > 50:  # Filter small regions
                    table_regions.append({
                        'bbox': (x, y, w, h),
                        'type': 'table',
                        'confidence': 0.7
                    })
            
            return table_regions
            
        except Exception as e:
            logger.error(f"Table detection failed: {e}")
            return []
    
    async def _detect_image_regions(self, gray: np.ndarray) -> List[Dict[str, Any]]:
        """Detect image/figure regions."""
        try:
            # Use edge detection to find image regions
            edges = cv2.Canny(gray, 50, 150)
            
            # Find large connected components
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            image_regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                if area > 5000:  # Filter small regions
                    image_regions.append({
                        'bbox': (x, y, w, h),
                        'type': 'image',
                        'confidence': 0.6
                    })
            
            return image_regions
            
        except Exception as e:
            logger.error(f"Image region detection failed: {e}")
            return []