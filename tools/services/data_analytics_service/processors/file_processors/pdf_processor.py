#!/usr/bin/env python3
"""
PDF Processor

Handles native PDF text extraction and PDF-specific processing.
Uses pypdf for native PDF text extraction and other PDF utilities.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

# Set up logger first
logger = logging.getLogger(__name__)

# Optional imports with fallbacks
try:
    import PyPDF2 as pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
    logger.warning("PyPDF2 not available, will use PyMuPDF as fallback")

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logger.warning("PyMuPDF not available, PDF processing will be limited")

@dataclass
class PDFTextResult:
    """PDF text extraction result"""
    full_text: str
    page_texts: List[str]
    text_blocks: List[Dict[str, Any]]
    confidence: float
    language: str
    processing_time: float
    extraction_method: str

@dataclass
class PDFMetadata:
    """PDF metadata extraction result"""
    page_count: int
    file_size: int
    pdf_version: str
    title: str
    author: str
    subject: str
    creator: str
    producer: str
    creation_date: Optional[str]
    modification_date: Optional[str]
    is_encrypted: bool

class PDFProcessor:
    """
    PDF processor for native PDF text extraction and PDF-specific operations.
    
    Handles:
    - Native PDF text extraction using pypdf
    - PDF metadata extraction
    - PDF page analysis
    - PDF structure analysis
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.default_language = self.config.get('default_language', 'auto')
        
        # Check dependencies
        if not HAS_PYPDF:
            logger.warning("PyPDF2 not available, some PDF processing features will be limited")
    
    async def extract_native_pdf_text(self, pdf_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract text from native PDF using pypdf.
        
        Args:
            pdf_path: Path to PDF file
            options: Processing options
            
        Returns:
            PDF text extraction results
        """
        import time
        start_time = time.time()
        
        try:
            options = options or {}
            
            full_text = ""
            page_texts = []
            text_blocks = []
            
            # Try pypdf first, fallback to PyMuPDF
            if HAS_PYPDF:
                try:
                    with open(pdf_path, 'rb') as file:
                        pdf_reader = pypdf.PdfReader(file)
                        
                        for page_num, page in enumerate(pdf_reader.pages):
                            try:
                                page_text = page.extract_text()
                                page_texts.append(page_text)
                                full_text += page_text + "\n"
                                
                                # Create text blocks for each page
                                if page_text.strip():
                                    text_blocks.append({
                                        'page': page_num + 1,
                                        'text': page_text,
                                        'bbox': None,  # pypdf doesn't provide bbox easily
                                        'confidence': 1.0
                                    })
                            except Exception as e:
                                logger.warning(f"Failed to extract text from page {page_num}: {e}")
                                page_texts.append("")
                    
                    extraction_method = 'pypdf'
                except Exception as e:
                    logger.warning(f"pypdf extraction failed: {e}, trying PyMuPDF")
                    raise e
                    
            else:
                # Use PyMuPDF as fallback
                if not HAS_PYMUPDF:
                    raise ImportError("Neither pypdf nor PyMuPDF available")
                
                doc = fitz.open(pdf_path)
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    try:
                        page_text = page.get_text()
                        page_texts.append(page_text)
                        full_text += page_text + "\n"
                        
                        # Create text blocks for each page
                        if page_text.strip():
                            text_blocks.append({
                                'page': page_num + 1,
                                'text': page_text,
                                'bbox': None,
                                'confidence': 1.0
                            })
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {e}")
                        page_texts.append("")
                
                doc.close()
                extraction_method = 'pymupdf'
            
            processing_time = time.time() - start_time
            
            return {
                'pdf_path': pdf_path,
                'full_text': full_text,
                'pages': page_texts,
                'text_blocks': text_blocks,
                'confidence': 1.0,
                'language': self.default_language,
                'processing_time': processing_time,
                'extraction_method': extraction_method,
                'success': True
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Native PDF text extraction failed: {e}")
            return {
                'pdf_path': pdf_path,
                'error': str(e),
                'processing_time': processing_time,
                'success': False
            }
    
    async def extract_pdf_metadata(self, pdf_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract PDF metadata.
        
        Args:
            pdf_path: Path to PDF file
            options: Processing options
            
        Returns:
            PDF metadata
        """
        try:
            if not HAS_PYPDF:
                raise ImportError("PyPDF2 not available")
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                # Get basic info
                page_count = len(pdf_reader.pages)
                file_size = Path(pdf_path).stat().st_size
                
                # Get metadata
                metadata = pdf_reader.metadata or {}
                
                return {
                    'pdf_path': pdf_path,
                    'page_count': page_count,
                    'file_size': file_size,
                    'pdf_version': getattr(pdf_reader, 'pdf_version', 'unknown'),
                    'title': metadata.get('/Title', ''),
                    'author': metadata.get('/Author', ''),
                    'subject': metadata.get('/Subject', ''),
                    'creator': metadata.get('/Creator', ''),
                    'producer': metadata.get('/Producer', ''),
                    'creation_date': str(metadata.get('/CreationDate', '')),
                    'modification_date': str(metadata.get('/ModDate', '')),
                    'is_encrypted': pdf_reader.is_encrypted,
                    'success': True
                }
            
        except Exception as e:
            logger.error(f"PDF metadata extraction failed: {e}")
            return {
                'pdf_path': pdf_path,
                'error': str(e),
                'success': False
            }
    
    async def analyze_pdf_structure(self, pdf_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze PDF structure and layout.
        
        Args:
            pdf_path: Path to PDF file
            options: Analysis options
            
        Returns:
            PDF structure analysis
        """
        try:
            if not HAS_PYPDF:
                raise ImportError("PyPDF2 not available")
            
            options = options or {}
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                page_info = []
                
                for page_num, page in enumerate(pdf_reader.pages):
                    # Get page dimensions
                    mediabox = page.mediabox
                    page_width = float(mediabox.width)
                    page_height = float(mediabox.height)
                    
                    # Check for content
                    page_text = page.extract_text()
                    has_text = bool(page_text.strip())
                    
                    # Check for images (basic check)
                    has_images = '/XObject' in page.get('/Resources', {})
                    
                    page_info.append({
                        'page_number': page_num + 1,
                        'width': page_width,
                        'height': page_height,
                        'rotation': page.rotation,
                        'has_text': has_text,
                        'has_images': has_images,
                        'text_length': len(page_text)
                    })
                
                return {
                    'pdf_path': pdf_path,
                    'total_pages': len(pdf_reader.pages),
                    'page_info': page_info,
                    'is_encrypted': pdf_reader.is_encrypted,
                    'success': True
                }
            
        except Exception as e:
            logger.error(f"PDF structure analysis failed: {e}")
            return {
                'pdf_path': pdf_path,
                'error': str(e),
                'success': False
            }
    
    async def extract_pdf_images_info(self, pdf_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract information about images in PDF.
        
        Args:
            pdf_path: Path to PDF file
            options: Processing options
            
        Returns:
            PDF images information
        """
        try:
            if not HAS_PYMUPDF:
                logger.warning("PyMuPDF not available, using limited image detection")
                return await self._extract_images_info_basic(pdf_path, options)
            
            doc = fitz.open(pdf_path)
            image_info = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    image_info.append({
                        'page_number': page_num + 1,
                        'image_index': img_index,
                        'xref': img[0],
                        'smask': img[1],
                        'width': img[2],
                        'height': img[3],
                        'bpc': img[4],
                        'colorspace': img[5],
                        'alt': img[6],
                        'name': img[7],
                        'filter': img[8]
                    })
            
            doc.close()
            
            return {
                'pdf_path': pdf_path,
                'total_images': len(image_info),
                'images': image_info,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"PDF image info extraction failed: {e}")
            return {
                'pdf_path': pdf_path,
                'error': str(e),
                'success': False
            }
    
    async def _extract_images_info_basic(self, pdf_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Basic image info extraction using pypdf only."""
        try:
            if not HAS_PYPDF:
                raise ImportError("PyPDF2 not available")
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                image_count = 0
                pages_with_images = []
                
                for page_num, page in enumerate(pdf_reader.pages):
                    resources = page.get('/Resources', {})
                    if '/XObject' in resources:
                        xobjects = resources['/XObject']
                        if xobjects:
                            image_count += len(xobjects)
                            pages_with_images.append(page_num + 1)
                
                return {
                    'pdf_path': pdf_path,
                    'total_images': image_count,
                    'pages_with_images': pages_with_images,
                    'images': [],  # Basic info only
                    'success': True
                }
            
        except Exception as e:
            logger.error(f"Basic PDF image info extraction failed: {e}")
            return {
                'pdf_path': pdf_path,
                'error': str(e),
                'success': False
            }
    
    def get_supported_formats(self) -> List[str]:
        """Get supported PDF formats."""
        return ['pdf']
    
    def is_available(self) -> bool:
        """Check if PDF processor is available."""
        return HAS_PYPDF
    
    async def extract_pdf_images(self, pdf_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract images from PDF as separate image files.
        
        Args:
            pdf_path: Path to PDF file
            options: Processing options
            
        Returns:
            Extracted images information and data
        """
        try:
            if not HAS_PYMUPDF:
                raise ImportError("PyMuPDF not available for image extraction")
            
            options = options or {}
            doc = fitz.open(pdf_path)
            extracted_images = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Extract image data
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        if pix.n < 5:  # Skip CMYK images
                            # Convert to PNG bytes
                            img_data = pix.pil_tobytes(format="PNG")
                            
                            # Convert to base64 for easy handling
                            import base64
                            img_base64 = base64.b64encode(img_data).decode('utf-8')
                            image_data_url = f'data:image/png;base64,{img_base64}'
                            
                            extracted_images.append({
                                'page_number': page_num + 1,
                                'image_index': img_index,
                                'width': pix.width,
                                'height': pix.height,
                                'image_data': image_data_url,
                                'format': 'PNG',
                                'size_bytes': len(img_data)
                            })
                        
                        pix = None
                        
                    except Exception as e:
                        logger.warning(f"Failed to extract image {img_index} on page {page_num}: {e}")
                        continue
            
            doc.close()
            
            return {
                'pdf_path': pdf_path,
                'total_images': len(extracted_images),
                'images': extracted_images,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"PDF image extraction failed: {e}")
            return {
                'pdf_path': pdf_path,
                'error': str(e),
                'success': False
            }
    
    async def process_pdf_unified(self, pdf_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        统一PDF处理方法：
        1. 使用PyMuPDF提取所有能提取的文字
        2. 对于无法提取文字的区域/页面，提取为图像
        3. 使用Vision模型分析图像内容
        4. 统一返回文字+图像分析结果
        
        Args:
            pdf_path: PDF文件路径
            options: 处理选项
            
        Returns:
            统一处理结果
        """
        try:
            if not HAS_PYMUPDF:
                raise Exception("PyMuPDF is required for unified PDF processing")
            
            options = options or {}
            extract_text = options.get('extract_text', True)
            extract_images = options.get('extract_images', True)
            extract_tables = options.get('extract_tables', True)
            max_pages = options.get('max_pages', None)  # Add page limit support
            
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # Determine how many pages to process
            pages_to_process = total_pages
            if max_pages is not None and max_pages > 0:
                pages_to_process = min(max_pages, total_pages)
                logger.info(f"PDF page limit: processing {pages_to_process} of {total_pages} pages")
            
            result = {
                'pdf_path': pdf_path,
                'total_pages': total_pages,
                'pages_processed': pages_to_process,
                'success': True
            }
            
            # 存储结果
            page_texts = []
            all_text = ""
            extracted_images = []
            text_blocks = []
            vision_analyses = []
            tables = []
            
            # 逐页处理 - 使用页面限制
            for page_num in range(pages_to_process):
                page = doc[page_num]
                page_result = {
                    'page_number': page_num + 1,
                    'has_text': False,
                    'has_images': False,
                    'needs_vision_analysis': False
                }
                
                # 1. 尝试提取文字
                if extract_text:
                    page_text = page.get_text()
                    page_text = page_text.strip()
                    
                    if page_text:
                        page_result['has_text'] = True
                        page_texts.append(page_text)
                        all_text += page_text + "\n\n"
                        
                        # 提取文字块位置信息
                        blocks = page.get_text("dict")["blocks"]
                        for block in blocks:
                            if block.get("type") == 0:  # 文字块
                                text_blocks.append({
                                    'page_number': page_num + 1,
                                    'bbox': block.get("bbox"),
                                    'text': block.get("text", "")
                                })
                    else:
                        # 没有文字，需要用Vision分析
                        page_result['needs_vision_analysis'] = True
                
                # 2. 检查并提取图像
                if extract_images:
                    image_list = page.get_images()
                    if image_list:
                        page_result['has_images'] = True
                        
                        # 提取图像
                        for img_index, img in enumerate(image_list):
                            try:
                                xref = img[0]
                                pix = fitz.Pixmap(doc, xref)
                                if pix.n < 5:  # Skip CMYK images
                                    img_data = pix.pil_tobytes(format="PNG")
                                    import base64
                                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                                    image_data_url = f'data:image/png;base64,{img_base64}'
                                    
                                    extracted_images.append({
                                        'page_number': page_num + 1,
                                        'image_index': img_index,
                                        'width': pix.width,
                                        'height': pix.height,
                                        'image_data': image_data_url,
                                        'format': 'PNG',
                                        'size_bytes': len(img_data)
                                    })
                                pix = None
                            except Exception as e:
                                logger.warning(f"Failed to extract image {img_index} on page {page_num}: {e}")
                
                # 3. 如果页面没有文字或需要图像分析，转换页面为图像并用Vision分析
                if page_result['needs_vision_analysis'] or (page_result['has_images'] and extract_images):
                    try:
                        # 将页面转换为图像
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                        img_data = pix.pil_tobytes(format="PNG")
                        import base64
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        page_image_data = f'data:image/png;base64,{img_base64}'
                        
                        # 准备Vision分析（实际调用会在这里）
                        # 这里为了保持统一处理，我们收集需要分析的页面
                        vision_analyses.append({
                            'page_number': page_num + 1,
                            'page_image_data': page_image_data,
                            'analysis_reason': 'no_text' if page_result['needs_vision_analysis'] else 'has_images',
                            'width': pix.width,
                            'height': pix.height
                        })
                        
                        pix = None
                    except Exception as e:
                        logger.warning(f"Failed to convert page {page_num} to image: {e}")
                
                # 4. 简单表格检测（基于文字块位置）
                if extract_tables and page_result['has_text']:
                    # 简化的表格检测：查找对齐的文字块
                    tables_on_page = self._detect_simple_tables(text_blocks, page_num + 1)
                    tables.extend(tables_on_page)
            
            doc.close()
            
            # 组装结果
            if extract_text:
                result['text_extraction'] = {
                    'full_text': all_text.strip(),
                    'pages': page_texts,
                    'text_blocks': text_blocks,
                    'confidence': 1.0,
                    'language': 'auto',
                    'extraction_method': 'unified_pymupdf'
                }
            
            if extract_images:
                result['image_analysis'] = {
                    'total_images': len(extracted_images),
                    'extracted_images': extracted_images,
                    'vision_analyses': vision_analyses,  # 这些需要用Vision模型分析
                    'pages_needing_vision': len(vision_analyses)
                }
            
            if extract_tables:
                result['table_extraction'] = {
                    'total_tables': len(tables),
                    'tables': tables,
                    'table_analyses': tables,
                    'extraction_method': 'text_based_detection'
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Unified PDF processing failed: {e}")
            return {
                'pdf_path': pdf_path,
                'error': str(e),
                'success': False
            }
    
    def _detect_simple_tables(self, text_blocks: List[Dict[str, Any]], page_number: int) -> List[Dict[str, Any]]:
        """简单的表格检测：基于文字块对齐"""
        tables = []
        
        # 过滤当前页面的文字块
        page_blocks = [block for block in text_blocks if block['page_number'] == page_number]
        
        if len(page_blocks) > 3:  # 至少需要几个文字块才可能是表格
            # 简化逻辑：查找y坐标相近的文字块（可能是表格行）
            rows = {}
            for block in page_blocks:
                if block['bbox']:
                    y = block['bbox'][1]  # y坐标
                    y_key = round(y / 10) * 10  # 对齐到10像素
                    if y_key not in rows:
                        rows[y_key] = []
                    rows[y_key].append(block)
            
            # 如果有多行都有多个文字块，可能是表格
            table_rows = [row_blocks for row_blocks in rows.values() if len(row_blocks) > 1]
            
            if len(table_rows) > 1:
                tables.append({
                    'page_number': page_number,
                    'table_type': 'text_aligned',
                    'row_count': len(table_rows),
                    'confidence': 0.7,
                    'content': 'Detected aligned text blocks indicating possible table structure'
                })
        
        return tables

    def get_capabilities(self) -> Dict[str, Any]:
        """Get processor capabilities."""
        return {
            'text_extraction': HAS_PYPDF or HAS_PYMUPDF,
            'image_extraction': HAS_PYMUPDF,
            'metadata_extraction': HAS_PYPDF,
            'structure_analysis': HAS_PYPDF,
            'image_info_extraction': HAS_PYPDF or HAS_PYMUPDF,
            'unified_processing': HAS_PYMUPDF,
            'supported_formats': self.get_supported_formats()
        }