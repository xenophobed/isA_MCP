#!/usr/bin/env python3
"""
Digital Asset Detector

Core component for detecting and classifying digital asset types.
Determines the most appropriate processing strategy for each asset.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import mimetypes

# Set up logger first
logger = logging.getLogger(__name__)

# Optional imports with fallbacks
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logger.warning("PyMuPDF not available, PDF analysis will be limited")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL not available, image analysis will be limited")

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    logger.warning("python-magic not available, using mimetypes fallback")

from ...models.base_models import AssetType

class AssetDetector:
    """
    Digital asset type detector.
    
    Identifies asset types and provides initial classification
    to determine optimal processing strategy.
    """
    
    def __init__(self):
        self.supported_formats = {
            'application/pdf': AssetType.PDF_NATIVE,  # Will be refined to scanned vs native
            'image/jpeg': AssetType.IMAGE,
            'image/png': AssetType.IMAGE,
            'image/tiff': AssetType.IMAGE,
            'image/bmp': AssetType.IMAGE,
            'application/vnd.ms-powerpoint': AssetType.POWERPOINT,
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': AssetType.POWERPOINT,
            'audio/mpeg': AssetType.AUDIO,
            'audio/wav': AssetType.AUDIO,
            'audio/mp4': AssetType.AUDIO,
            'video/mp4': AssetType.VIDEO,
            'video/avi': AssetType.VIDEO,
            'video/quicktime': AssetType.VIDEO,
        }
    
    async def detect_asset_type(self, file_path: str) -> AssetType:
        """
        Detect the type of digital asset.
        
        Args:
            file_path: Path to the digital asset
            
        Returns:
            Detected asset type
        """
        try:
            if not Path(file_path).exists():
                logger.error(f"File not found: {file_path}")
                return AssetType.UNKNOWN
            
            # Get MIME type
            mime_type = self._get_mime_type(file_path)
            
            # Basic type detection
            if mime_type == 'application/pdf':
                # Special handling for PDFs to determine scanned vs native
                return await self._detect_pdf_type(file_path)
            
            # Standard type mapping
            asset_type = self.supported_formats.get(mime_type, AssetType.UNKNOWN)
            
            logger.info(f"Detected asset type: {asset_type.value} for {file_path}")
            return asset_type
            
        except Exception as e:
            logger.error(f"Asset type detection failed: {e}")
            return AssetType.UNKNOWN
    
    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type of file."""
        try:
            if HAS_MAGIC:
                # Try python-magic first (more accurate)
                mime_type = magic.from_file(file_path, mime=True)
                return mime_type
            else:
                # Fallback to mimetypes
                mime_type, _ = mimetypes.guess_type(file_path)
                return mime_type or 'application/octet-stream'
        except:
            # Final fallback to mimetypes
            mime_type, _ = mimetypes.guess_type(file_path)
            return mime_type or 'application/octet-stream'
    
    async def _detect_pdf_type(self, file_path: str) -> AssetType:
        """
        Detect if PDF is scanned or native.
        
        Key indicators:
        - Native PDF: Has extractable text, vector graphics
        - Scanned PDF: Mostly images, minimal extractable text
        """
        try:
            if not HAS_PYMUPDF:
                # Without PyMuPDF, assume native PDF
                logger.warning("PyMuPDF not available, assuming native PDF")
                return AssetType.PDF_NATIVE
            
            # Method 1: Check text extraction ratio
            text_ratio = await self._calculate_text_ratio(file_path)
            
            # Method 2: Check image content ratio
            image_ratio = await self._calculate_image_ratio(file_path)
            
            # Method 3: Check font information
            has_fonts = await self._check_font_presence(file_path)
            
            # Decision logic - more lenient for native PDFs
            logger.info(f"PDF analysis: text_ratio={text_ratio:.3f}, has_fonts={has_fonts}, image_ratio={image_ratio:.3f}")
            
            # If we have extractable text and fonts, it's likely native
            if text_ratio > 0.05 and has_fonts:
                return AssetType.PDF_NATIVE
            # If we have significant text even without fonts
            elif text_ratio > 0.2:
                return AssetType.PDF_NATIVE
            # If image ratio is very high, it's likely scanned
            elif image_ratio > 0.9:
                return AssetType.PDF_SCANNED
            else:
                # Default to native PDF for print documents
                return AssetType.PDF_NATIVE
                
        except Exception as e:
            logger.error(f"PDF type detection failed: {e}")
            # Default to native PDF if detection fails
            return AssetType.PDF_NATIVE
    
    async def _calculate_text_ratio(self, file_path: str) -> float:
        """Calculate the ratio of extractable text to total content."""
        try:
            doc = fitz.open(file_path)
            total_chars = 0
            text_chars = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get text content
                text = page.get_text()
                text_chars += len(text.strip())
                
                # Estimate total content (including images)
                blocks = page.get_text("dict")["blocks"]
                total_chars += sum(len(str(block)) for block in blocks)
            
            doc.close()
            
            if total_chars == 0:
                return 0.0
            
            ratio = text_chars / total_chars
            logger.debug(f"Text ratio: {ratio:.3f}")
            return ratio
            
        except Exception as e:
            logger.error(f"Text ratio calculation failed: {e}")
            return 0.0
    
    async def _calculate_image_ratio(self, file_path: str) -> float:
        """Calculate the ratio of image content to total content."""
        try:
            doc = fitz.open(file_path)
            total_area = 0
            image_area = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_rect = page.rect
                total_area += page_rect.width * page_rect.height
                
                # Get image blocks
                image_list = page.get_images()
                for img in image_list:
                    try:
                        # Get image dimensions
                        img_rect = page.get_image_bbox(img)
                        if img_rect:
                            image_area += img_rect.width * img_rect.height
                    except:
                        continue
            
            doc.close()
            
            if total_area == 0:
                return 0.0
            
            ratio = image_area / total_area
            logger.debug(f"Image ratio: {ratio:.3f}")
            return ratio
            
        except Exception as e:
            logger.error(f"Image ratio calculation failed: {e}")
            return 0.0
    
    async def _check_font_presence(self, file_path: str) -> bool:
        """Check if PDF contains font information (indicator of native PDF)."""
        try:
            doc = fitz.open(file_path)
            
            # Check for fonts in the first few pages
            for page_num in range(min(3, len(doc))):
                page = doc[page_num]
                fonts = page.get_fonts()
                
                if fonts:
                    doc.close()
                    logger.debug(f"Found {len(fonts)} fonts")
                    return True
            
            doc.close()
            return False
            
        except Exception as e:
            logger.error(f"Font check failed: {e}")
            return False
    
    def get_supported_formats(self) -> Dict[str, str]:
        """Get list of supported formats."""
        return {
            mime_type: asset_type.value 
            for mime_type, asset_type in self.supported_formats.items()
        }
    
    def is_supported(self, file_path: str) -> bool:
        """Check if file format is supported."""
        mime_type = self._get_mime_type(file_path)
        return mime_type in self.supported_formats
    
    async def get_asset_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get basic metadata about the asset."""
        try:
            file_path_obj = Path(file_path)
            stat = file_path_obj.stat()
            
            metadata = {
                'file_name': file_path_obj.name,
                'file_size': stat.st_size,
                'mime_type': self._get_mime_type(file_path),
                'extension': file_path_obj.suffix.lower(),
                'created_time': stat.st_ctime,
                'modified_time': stat.st_mtime,
                'is_supported': self.is_supported(file_path)
            }
            
            # Add format-specific metadata
            if metadata['mime_type'] == 'application/pdf':
                pdf_metadata = await self._get_pdf_metadata(file_path)
                metadata.update(pdf_metadata)
            elif metadata['mime_type'].startswith('image/'):
                image_metadata = await self._get_image_metadata(file_path)
                metadata.update(image_metadata)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return {'error': str(e)}
    
    async def _get_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get PDF-specific metadata."""
        try:
            doc = fitz.open(file_path)
            metadata = {
                'page_count': len(doc),
                'pdf_version': getattr(doc, 'pdf_version', 'unknown'),
                'is_encrypted': doc.is_encrypted,
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'subject': doc.metadata.get('subject', ''),
                'creator': doc.metadata.get('creator', ''),
                'producer': doc.metadata.get('producer', ''),
            }
            doc.close()
            return metadata
        except Exception as e:
            logger.error(f"PDF metadata extraction failed: {e}")
            return {}
    
    async def _get_image_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get image-specific metadata."""
        try:
            with Image.open(file_path) as img:
                metadata = {
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                    'format': img.format,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
                
                # EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    metadata['has_exif'] = True
                else:
                    metadata['has_exif'] = False
                
                return metadata
        except Exception as e:
            logger.error(f"Image metadata extraction failed: {e}")
            return {}
    
    # === FORMAT ANALYSIS METHODS (Integrated from format_analyzer.py) ===
    
    async def _analyze_scanned_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze scanned PDF characteristics.
        
        Focus on:
        - Page image quality
        - OCR feasibility
        - Layout complexity
        - Table detection potential
        """
        try:
            if not HAS_PYMUPDF:
                return {
                    'error': 'PyMuPDF not available for scanned PDF analysis',
                    'recommended_processing': ['basic_ocr']
                }
                
            doc = fitz.open(file_path)
            analysis = {
                'page_count': len(doc),
                'pages_analysis': [],
                'ocr_feasibility': 'high',
                'layout_complexity': 'medium',
                'table_detection_potential': 'medium',
                'recommended_processing': ['ocr', 'layout_analysis']
            }
            
            # Analyze first few pages for performance
            pages_to_analyze = min(3, len(doc))
            
            for page_num in range(pages_to_analyze):
                page = doc[page_num]
                page_analysis = await self._analyze_pdf_page(page, page_num)
                analysis['pages_analysis'].append(page_analysis)
            
            doc.close()
            
            # Aggregate analysis
            aggregated = await self._aggregate_pdf_analysis(analysis['pages_analysis'])
            analysis.update(aggregated)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Scanned PDF analysis failed: {e}")
            return {
                'error': str(e),
                'recommended_processing': ['basic_ocr']
            }
    
    async def _analyze_native_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze native PDF characteristics.
        
        Focus on:
        - Text extraction quality
        - Embedded images
        - Table structures
        - Font analysis
        """
        try:
            if not HAS_PYMUPDF:
                return {
                    'error': 'PyMuPDF not available for native PDF analysis',
                    'recommended_processing': ['text_extraction']
                }
                
            doc = fitz.open(file_path)
            analysis = {
                'page_count': len(doc),
                'text_extraction_quality': 'high',
                'embedded_images_count': 0,
                'table_structures': [],
                'font_analysis': {},
                'recommended_processing': ['text_extraction', 'image_analysis']
            }
            
            # Analyze text content
            total_text_length = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                total_text_length += len(text)
                
                # Count embedded images
                images = page.get_images()
                analysis['embedded_images_count'] += len(images)
                
                # Analyze fonts (first page only for performance)
                if page_num == 0:
                    fonts = page.get_fonts()
                    analysis['font_analysis'] = {
                        'font_count': len(fonts),
                        'fonts': [font[3] for font in fonts]  # Font names
                    }
            
            analysis['total_text_length'] = total_text_length
            analysis['text_density'] = total_text_length / len(doc) if len(doc) > 0 else 0
            
            # Add table detection if significant content
            if analysis['text_density'] > 100:
                analysis['recommended_processing'].append('table_detection')
            
            doc.close()
            return analysis
            
        except Exception as e:
            logger.error(f"Native PDF analysis failed: {e}")
            return {
                'error': str(e),
                'recommended_processing': ['text_extraction']
            }
    
    async def _analyze_image(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze image characteristics.
        
        Focus on:
        - Layout region detection
        - Text regions
        - Table regions
        - Image quality for OCR
        """
        try:
            # Get basic image info with PIL
            with Image.open(file_path) as img:
                width, height = img.size
                mode = img.mode
                format_type = img.format
            
            analysis = {
                'width': width,
                'height': height,
                'aspect_ratio': width / height,
                'mode': mode,
                'format': format_type,
                'layout_regions': {},
                'text_regions': [],
                'table_regions': [],
                'image_quality': {},
                'ocr_feasibility': 'high',
                'recommended_processing': ['layout_detection', 'ocr', 'vlm_analysis']
            }
            
            # Advanced analysis with OpenCV if available
            if HAS_OPENCV:
                img_cv = cv2.imread(file_path)
                if img_cv is not None:
                    # Image quality assessment
                    analysis['image_quality'] = await self._assess_image_quality(img_cv)
                    
                    # Layout region detection
                    analysis['layout_regions'] = await self._detect_layout_regions(img_cv)
                    
                    # OCR feasibility assessment
                    analysis['ocr_feasibility'] = await self._assess_ocr_feasibility(img_cv)
            else:
                logger.warning("OpenCV not available, using basic image analysis")
                analysis['image_quality'] = {'note': 'Basic analysis only - OpenCV not available'}
            
            return analysis
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return {
                'error': str(e),
                'recommended_processing': ['basic_vlm_analysis']
            }
    
    async def _analyze_powerpoint(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze PowerPoint characteristics.
        
        Focus on:
        - Slide count estimation
        - Content types per slide
        - Processing recommendations
        """
        try:
            # Basic analysis without python-pptx dependency
            file_size = Path(file_path).stat().st_size
            
            analysis = {
                'estimated_slide_count': max(1, file_size // (50 * 1024)),  # Rough estimate
                'content_types': {'text': 'likely', 'images': 'likely', 'tables': 'possible'},
                'text_extraction_potential': 'high',
                'recommended_processing': ['slide_extraction', 'image_analysis', 'text_extraction']
            }
            
            logger.info(f"PowerPoint analysis completed for {file_path} (basic mode)")
            return analysis
            
        except Exception as e:
            logger.error(f"PowerPoint analysis failed: {e}")
            return {
                'error': str(e),
                'recommended_processing': ['basic_text_extraction']
            }
    
    async def _analyze_audio(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze audio characteristics.
        
        Focus on:
        - File size and estimated duration
        - Audio processing recommendations
        """
        try:
            file_size = Path(file_path).stat().st_size
            
            # Rough duration estimate (assuming average bitrate)
            estimated_duration = file_size / (128 * 1024 / 8)  # 128 kbps estimate
            
            analysis = {
                'estimated_duration_seconds': int(estimated_duration),
                'file_size_bytes': file_size,
                'estimated_speakers': 1,
                'content_type': 'speech',
                'quality_score': 0.8,  # Default assumption
                'recommended_processing': ['speech_recognition', 'speaker_identification']
            }
            
            # Add emotion analysis for longer audio
            if estimated_duration > 60:  # Over 1 minute
                analysis['recommended_processing'].append('emotion_analysis')
            
            logger.info(f"Audio analysis completed for {file_path} (basic mode)")
            return analysis
            
        except Exception as e:
            logger.error(f"Audio analysis failed: {e}")
            return {
                'error': str(e),
                'recommended_processing': ['basic_transcription']
            }
    
    async def _analyze_video(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze video characteristics.
        
        Focus on:
        - File size and estimated properties
        - Video processing recommendations
        """
        try:
            file_size = Path(file_path).stat().st_size
            
            analysis = {
                'file_size_bytes': file_size,
                'estimated_duration_seconds': file_size // (1024 * 1024),  # Rough estimate
                'estimated_frame_rate': 30,  # Default assumption
                'estimated_resolution': {'width': 1920, 'height': 1080},  # Default assumption
                'has_audio': True,  # Assume yes
                'content_complexity': 'medium',
                'recommended_processing': ['frame_analysis', 'audio_extraction', 'object_detection']
            }
            
            logger.info(f"Video analysis completed for {file_path} (basic mode)")
            return analysis
            
        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            return {
                'error': str(e),
                'recommended_processing': ['basic_frame_extraction']
            }
    
    # === HELPER METHODS FOR ANALYSIS ===
    
    async def _analyze_pdf_page(self, page, page_num: int) -> Dict[str, Any]:
        """Analyze individual PDF page."""
        try:
            # Convert page to image for analysis
            pix = page.get_pixmap()
            
            # Basic page analysis
            analysis = {
                'page_number': page_num,
                'width': pix.width,
                'height': pix.height,
                'text_blocks': len(page.get_text_blocks()),
                'image_count': len(page.get_images()),
                'estimated_complexity': 'medium'
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"PDF page analysis failed: {e}")
            return {'page_number': page_num, 'error': str(e)}
    
    async def _aggregate_pdf_analysis(self, pages_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate analysis from multiple PDF pages."""
        try:
            if not pages_analysis:
                return {}
            
            # Calculate averages and totals
            valid_pages = [p for p in pages_analysis if 'error' not in p]
            if not valid_pages:
                return {'error': 'No valid page analysis results'}
            
            avg_width = sum(p.get('width', 0) for p in valid_pages) / len(valid_pages)
            avg_height = sum(p.get('height', 0) for p in valid_pages) / len(valid_pages)
            total_text_blocks = sum(p.get('text_blocks', 0) for p in valid_pages)
            total_images = sum(p.get('image_count', 0) for p in valid_pages)
            
            # Determine complexity
            complexity = 'low'
            if total_text_blocks > 10 or total_images > 5:
                complexity = 'medium'
            if total_text_blocks > 20 or total_images > 10:
                complexity = 'high'
            
            return {
                'average_page_dimensions': {'width': avg_width, 'height': avg_height},
                'total_text_blocks': total_text_blocks,
                'total_images': total_images,
                'overall_complexity': complexity,
                'recommended_processing': self._get_pdf_processing_recommendations(complexity, total_images)
            }
            
        except Exception as e:
            logger.error(f"PDF aggregation failed: {e}")
            return {'error': str(e)}
    
    async def _assess_image_quality(self, img) -> Dict[str, Any]:
        """Assess image quality for OCR."""
        try:
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Calculate metrics
            blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            brightness = np.mean(gray)
            contrast = np.std(gray)
            
            # Assess quality
            quality_score = 0.0
            if blur_score > 100:
                quality_score += 0.4  # Good sharpness
            if 50 < brightness < 200:
                quality_score += 0.3  # Good brightness
            if contrast > 30:
                quality_score += 0.3  # Good contrast
            
            return {
                'blur_score': float(blur_score),
                'brightness': float(brightness),
                'contrast': float(contrast),
                'quality_score': quality_score,
                'ocr_suitability': 'high' if quality_score > 0.7 else 'medium' if quality_score > 0.4 else 'low'
            }
            
        except Exception as e:
            logger.error(f"Image quality assessment failed: {e}")
            return {'error': str(e)}
    
    async def _detect_layout_regions(self, img) -> Dict[str, Any]:
        """Detect layout regions in image."""
        try:
            # Simplified layout detection
            height, width = img.shape[:2]
            
            # Basic region estimation
            regions = {
                'text_regions': [
                    {'x': 50, 'y': 50, 'width': width-100, 'height': 100, 'confidence': 0.8}
                ],
                'table_regions': [
                    {'x': 50, 'y': 200, 'width': width-100, 'height': 150, 'confidence': 0.6}
                ],
                'image_regions': [
                    {'x': 50, 'y': 400, 'width': width-100, 'height': 200, 'confidence': 0.9}
                ]
            }
            
            return regions
            
        except Exception as e:
            logger.error(f"Layout region detection failed: {e}")
            return {'error': str(e)}
    
    async def _assess_ocr_feasibility(self, img) -> str:
        """Assess OCR feasibility for image."""
        try:
            # Simple assessment based on image characteristics
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Check for text-like patterns
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            if edge_density > 0.1:
                return 'high'
            elif edge_density > 0.05:
                return 'medium'
            else:
                return 'low'
                
        except Exception as e:
            logger.error(f"OCR feasibility assessment failed: {e}")
            return 'unknown'
    
    def _get_pdf_processing_recommendations(self, complexity: str, image_count: int) -> List[str]:
        """Get processing recommendations based on PDF characteristics."""
        recommendations = ['ocr']
        
        if complexity in ['medium', 'high']:
            recommendations.append('layout_analysis')
        
        if image_count > 0:
            recommendations.append('image_extraction')
        
        if complexity == 'high':
            recommendations.append('table_detection')
        
        return recommendations