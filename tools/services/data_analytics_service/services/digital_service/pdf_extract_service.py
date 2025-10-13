#!/usr/bin/env python3
"""
Simple PDF Extract Service - Optimized with Dask

Simple, fast PDF extraction service that:
- Input: PDF file, user_id, optional metadata/options
- Options: "text" (text only) or "full" (text + image extraction)
- Output: chunks of text (nothing more)

No preprocessing, no graph analytics, no complex workflows.
Just PDF → text chunks with Dask parallel processing.

Uses existing production services:
- PDFProcessor: For unified PDF processing (text + images)
- ImageAnalyzer: For parallel image text extraction with Dask
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime

# Optional: Dask for parallel processing (fallback to asyncio if not available)
try:
    import dask
    from dask.distributed import Client, as_completed
    from dask import delayed
    HAS_DASK = True
except ImportError:
    HAS_DASK = False
    logging.warning("Dask not available, will use asyncio for parallel processing")

# Use existing production services
from ...processors.file_processors.pdf_processor import PDFProcessor
from ....intelligence_service.vision.image_analyzer import analyze

logger = logging.getLogger(__name__)

class PDFExtractService:
    """
    Simple PDF Extract Service - PDF to text chunks only
    
    Features:
    - Fast PDF text extraction
    - Optional image text extraction (with Dask parallelization)
    - Simple chunking (no intelligent preprocessing)
    - Dask parallel processing for image analysis
    - Clean, minimal interface
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.service_name = "simple_pdf_extract_service"
        self.version = "1.0.0"
        self.config = config or {}
        
        # Simple configuration
        self.chunk_size = self.config.get('chunk_size', 2000)
        self.chunk_overlap = self.config.get('chunk_overlap', 200)
        
        # Core processor
        self.pdf_processor = PDFProcessor(self.config)
        
        # Dask client for parallel processing
        self.dask_client = None
        
        logger.info("Simple PDF Extract Service initialized")
    
    async def initialize_dask(self, workers: int = 4, threads_per_worker: int = 2):
        """Initialize Dask client for parallel processing"""
        if not HAS_DASK:
            logger.warning("Dask not available, cannot initialize")
            return False

        try:
            self.dask_client = Client(
                processes=True,
                n_workers=workers,
                threads_per_worker=threads_per_worker,
                silence_logs=False
            )
            logger.info(f"Dask client initialized: {workers} workers, {threads_per_worker} threads each")
            return True
        except Exception as e:
            logger.warning(f"Dask initialization failed: {e}")
            return False
    
    def close_dask(self):
        """Close Dask client"""
        if self.dask_client:
            try:
                self.dask_client.close()
                self.dask_client = None
                logger.info("Dask client closed")
            except Exception as e:
                logger.warning(f"Dask close error: {e}")
    
    async def extract_pdf_to_chunks(
        self,
        pdf_path: str,
        user_id: int,
        options: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract PDF to text chunks
        
        Args:
            pdf_path: Path to PDF file
            user_id: User ID
            options: {"mode": "text" or "full", "max_workers": int}
            metadata: Optional metadata
            
        Returns:
            {"success": bool, "chunks": List[str], "processing_time": float}
        """
        start_time = time.time()
        
        try:
            options = options or {}
            metadata = metadata or {}
            mode = options.get('mode', 'text')  # "text" or "full"
            
            # Validate input
            if not Path(pdf_path).exists():
                return {
                    'success': False,
                    'error': f'PDF file not found: {pdf_path}',
                    'processing_time': time.time() - start_time
                }
            
            logger.info(f"Extracting PDF: {pdf_path} (mode: {mode})")
            
            if mode == "text":
                # Step 1: Text-only mode (fast)
                text_result = await self._extract_text_only(pdf_path)
                
                if not text_result.get('success'):
                    return {
                        'success': False,
                        'error': f"Text extraction failed: {text_result.get('error')}",
                        'processing_time': time.time() - start_time
                    }
                
                full_text = text_result.get('text', '')
                pages_processed = text_result.get('pages', 0)
                images_processed = 0
                
            else:
                # Step 2: Full mode - integrate text and image content by page
                combined_result = await self._extract_text_and_images_integrated(pdf_path, options)
                
                if not combined_result.get('success'):
                    return {
                        'success': False,
                        'error': f"Full extraction failed: {combined_result.get('error')}",
                        'processing_time': time.time() - start_time
                    }
                
                full_text = combined_result.get('combined_text', '')
                pages_processed = combined_result.get('pages_processed', 0)
                images_processed = combined_result.get('images_processed', 0)
            
            # Step 3: Create simple chunks
            chunks = self._create_simple_chunks(full_text)
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'chunks': chunks,
                'chunk_count': len(chunks),
                'total_characters': len(full_text),
                'pages_processed': pages_processed,
                'images_processed': images_processed,
                'mode': mode,
                'user_id': user_id,
                'processing_time': processing_time,
                'metadata': {
                    'pdf_path': pdf_path,
                    'extracted_at': datetime.now().isoformat(),
                    **metadata
                }
            }
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    async def _extract_text_only(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text only (fast) using existing PDFProcessor"""
        try:
            # Use PDFProcessor unified processing - text only mode
            result = await self.pdf_processor.process_pdf_unified(pdf_path, {
                'extract_text': True,
                'extract_images': False,
                'extract_tables': False
            })
            
            if result.get('success'):
                text_extraction = result.get('text_extraction', {})
                return {
                    'success': True,
                    'text': text_extraction.get('full_text', ''),
                    'pages': result.get('total_pages', 0),
                    'processing_time': text_extraction.get('processing_time', 0)
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Text extraction failed')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _extract_text_and_images_integrated(self, pdf_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and integrate text and image content by page"""
        try:
            # Use PDFProcessor unified processing to get everything
            result = await self.pdf_processor.process_pdf_unified(pdf_path, {
                'extract_text': True,
                'extract_images': True,
                'extract_tables': False
            })
            
            if not result.get('success'):
                return {
                    'success': False,
                    'error': f"PDF processing failed: {result.get('error')}"
                }
            
            # Get text extraction results
            text_extraction = result.get('text_extraction', {})
            page_texts = text_extraction.get('pages', [])
            
            # Get image analysis results
            image_analysis = result.get('image_analysis', {})
            vision_analyses = image_analysis.get('vision_analyses', [])  # Full page images
            extracted_images = image_analysis.get('extracted_images', [])  # Embedded images
            
            # Organize images by page
            images_by_page = {}
            
            # Add full page images
            for vision_page in vision_analyses:
                page_num = vision_page.get('page_number', 0)
                if page_num not in images_by_page:
                    images_by_page[page_num] = []
                images_by_page[page_num].append({
                    'type': 'page',
                    'image_data': vision_page.get('page_image_data', ''),
                    'reason': vision_page.get('analysis_reason', 'unknown')
                })
            
            # Add embedded images
            for img in extracted_images:
                page_num = img.get('page_number', 0)
                if page_num not in images_by_page:
                    images_by_page[page_num] = []
                images_by_page[page_num].append({
                    'type': 'embedded',
                    'image_data': img.get('image_data', ''),
                    'size': f"{img.get('width', 0)}x{img.get('height', 0)}"
                })
            
            # Process images in parallel with Dask
            all_images = []
            image_page_mapping = []
            
            for page_num, page_images in images_by_page.items():
                for img in page_images:
                    all_images.append(img)
                    image_page_mapping.append(page_num)
            
            if not all_images:
                # No images to process, return text only
                return {
                    'success': True,
                    'combined_text': '\n\n'.join(page_texts),
                    'pages_processed': len(page_texts),
                    'images_processed': 0
                }
            
            logger.info(f"Processing {len(all_images)} images for text extraction and integration")
            
            # Process images in parallel
            if self.dask_client:
                image_texts = await self._process_images_with_dask(all_images)
            else:
                image_texts = await self._process_images_with_asyncio(all_images)
            
            # Integrate image texts with page texts
            page_image_texts = {}
            for i, image_text in enumerate(image_texts):
                if image_text and image_text.strip():
                    page_num = image_page_mapping[i]
                    if page_num not in page_image_texts:
                        page_image_texts[page_num] = []
                    page_image_texts[page_num].append({
                        'text': image_text.strip(),
                        'type': all_images[i]['type']
                    })
            
            # Combine text and image content by page
            combined_pages = []
            total_images_processed = sum(1 for text in image_texts if text and text.strip())
            
            for page_num, page_text in enumerate(page_texts, 1):
                combined_page_content = page_text
                
                # Add image text for this page
                if page_num in page_image_texts:
                    page_image_content = []
                    for img_text in page_image_texts[page_num]:
                        page_image_content.append(f"[{img_text['type'].title()} Image Text]: {img_text['text']}")
                    
                    if page_image_content:
                        combined_page_content += "\n\n" + "\n\n".join(page_image_content)
                
                combined_pages.append(combined_page_content)
            
            # Join all pages
            combined_text = '\n\n'.join(combined_pages)
            
            return {
                'success': True,
                'combined_text': combined_text,
                'pages_processed': len(page_texts),
                'images_processed': total_images_processed
            }
            
        except Exception as e:
            logger.error(f"Integrated text and image extraction failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _extract_image_text_parallel(self, pdf_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text from images using existing PDFProcessor + ImageAnalyzer with Dask"""
        try:
            # Use PDFProcessor to get all images (page images + embedded images)
            result = await self.pdf_processor.process_pdf_unified(pdf_path, {
                'extract_text': False,
                'extract_images': True,
                'extract_tables': False
            })
            
            if not result.get('success'):
                return {
                    'success': False,
                    'error': f"PDF image extraction failed: {result.get('error')}"
                }
            
            # Extract images from PDFProcessor result
            image_analysis = result.get('image_analysis', {})
            vision_analyses = image_analysis.get('vision_analyses', [])  # Full page images
            extracted_images = image_analysis.get('extracted_images', [])  # Embedded images
            
            all_images = []
            
            # Add full page images (for pages with no text or containing images)
            for vision_page in vision_analyses:
                all_images.append({
                    'type': 'page',
                    'page_number': vision_page.get('page_number', 0),
                    'image_data': vision_page.get('page_image_data', ''),
                    'index': len(all_images)
                })
            
            # Add embedded images
            for img in extracted_images:
                all_images.append({
                    'type': 'embedded',
                    'page_number': img.get('page_number', 0),
                    'image_data': img.get('image_data', ''),
                    'index': len(all_images)
                })
            
            if not all_images:
                return {
                    'success': True,
                    'text': '',
                    'images_processed': 0
                }
            
            logger.info(f"Processing {len(all_images)} images for text extraction using ImageAnalyzer")
            
            # Process images in parallel with Dask
            if self.dask_client:
                image_texts = await self._process_images_with_dask(all_images)
            else:
                image_texts = await self._process_images_with_asyncio(all_images)
            
            # Combine all image text
            combined_text = ""
            successful_count = 0
            
            for i, text in enumerate(image_texts):
                if text and text.strip():
                    img_info = all_images[i]
                    combined_text += f"\n--- {img_info['type'].title()} {i+1} (Page {img_info['page_number']}) ---\n"
                    combined_text += text.strip() + "\n"
                    successful_count += 1
            
            return {
                'success': True,
                'text': combined_text,
                'images_processed': successful_count,
                'total_images': len(all_images)
            }
            
        except Exception as e:
            logger.error(f"Image text extraction failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _process_images_with_dask(self, images: List[Dict[str, Any]]) -> List[str]:
        """Process images in parallel using Dask + ImageAnalyzer"""
        if not HAS_DASK:
            logger.warning("Dask not available, falling back to asyncio")
            return await self._process_images_with_asyncio(images)

        try:
            @delayed
            def analyze_image_dask(image_data: str) -> str:
                """Dask delayed function for image analysis"""
                import asyncio
                async def _analyze():
                    try:
                        # Use existing ImageAnalyzer
                        result = await analyze(
                            image=image_data,
                            prompt="Extract all text visible in this image. Return only the text content, maintaining original formatting."
                        )
                        if result.success:
                            return result.response.strip()
                        else:
                            logger.warning(f"Image analysis failed: {result.error}")
                            return ""
                    except Exception as e:
                        logger.warning(f"Image analysis exception: {e}")
                        return ""

                # Run async function in new event loop for Dask
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(_analyze())
                finally:
                    loop.close()

            # Create delayed tasks for each image
            tasks = []
            for img in images:
                if img['image_data']:  # Only process if image data exists
                    task = analyze_image_dask(img['image_data'])
                    tasks.append(task)
                else:
                    tasks.append(delayed(lambda: "")())

            # Execute in parallel with Dask
            logger.info(f"Executing {len(tasks)} image analysis tasks with Dask + ImageAnalyzer...")
            results = dask.compute(*tasks)

            return list(results)

        except Exception as e:
            logger.error(f"Dask image processing failed: {e}")
            # Fallback to asyncio
            return await self._process_images_with_asyncio(images)
    
    async def _process_images_with_asyncio(self, images: List[Dict[str, Any]]) -> List[str]:
        """Process images with asyncio + ImageAnalyzer (fallback)"""
        try:
            semaphore = asyncio.Semaphore(5)  # Limit concurrent VLM requests
            
            async def analyze_single(img: Dict[str, Any]) -> str:
                async with semaphore:
                    try:
                        if not img['image_data']:
                            return ""
                        
                        # Use existing ImageAnalyzer
                        result = await analyze(
                            image=img['image_data'],
                            prompt="Extract all text visible in this image. Return only the text content, maintaining original formatting."
                        )
                        if result.success:
                            return result.response.strip()
                        else:
                            logger.warning(f"Image analysis failed: {result.error}")
                            return ""
                    except Exception as e:
                        logger.warning(f"Image analysis exception: {e}")
                        return ""
            
            # Execute with asyncio
            logger.info(f"Executing {len(images)} image analysis tasks with asyncio + ImageAnalyzer...")
            tasks = [analyze_single(img) for img in images]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions in results
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Image processing exception: {result}")
                    processed_results.append("")
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Asyncio image processing failed: {e}")
            return [""] * len(images)
    
    def _create_simple_chunks(self, text: str) -> List[str]:
        """Create simple text chunks (no complex preprocessing)"""
        if not text or len(text) <= self.chunk_size:
            return [text.strip()] if text.strip() else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            if end >= len(text):
                # Last chunk
                chunk = text[start:].strip()
                if chunk:
                    chunks.append(chunk)
                break
            else:
                # Find word boundary
                chunk_end = text.rfind(' ', start + self.chunk_size - 200, end)
                if chunk_end <= start:
                    chunk_end = end
                
                chunk = text[start:chunk_end].strip()
                if chunk:
                    chunks.append(chunk)
                
                # Move to next chunk with overlap
                start = chunk_end - self.chunk_overlap
                if start < 0:
                    start = chunk_end
        
        return chunks
    
    async def batch_extract_pdfs(
        self,
        pdf_paths: List[str],
        user_id: int,
        options: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract multiple PDFs in parallel
        
        Args:
            pdf_paths: List of PDF file paths
            user_id: User ID
            options: Processing options
            metadata: Optional metadata
            
        Returns:
            {"success": bool, "results": List[Dict], "summary": Dict}
        """
        start_time = time.time()
        
        try:
            options = options or {}
            max_concurrent = options.get('max_concurrent', 4)
            
            logger.info(f"Batch processing {len(pdf_paths)} PDFs")
            
            # Process PDFs concurrently
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_single_pdf(pdf_path: str) -> Dict[str, Any]:
                async with semaphore:
                    return await self.extract_pdf_to_chunks(
                        pdf_path=pdf_path,
                        user_id=user_id,
                        options=options,
                        metadata=metadata
                    )
            
            # Execute all tasks
            tasks = [process_single_pdf(pdf_path) for pdf_path in pdf_paths]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful_results = []
            failed_results = []
            total_chunks = 0
            total_characters = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        'pdf_path': pdf_paths[i] if i < len(pdf_paths) else 'unknown',
                        'error': str(result)
                    })
                elif result.get('success'):
                    successful_results.append(result)
                    total_chunks += result.get('chunk_count', 0)
                    total_characters += result.get('total_characters', 0)
                else:
                    failed_results.append(result)
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'results': successful_results,
                'failed_results': failed_results,
                'summary': {
                    'total_pdfs': len(pdf_paths),
                    'successful_count': len(successful_results),
                    'failed_count': len(failed_results),
                    'total_chunks': total_chunks,
                    'total_characters': total_characters,
                    'processing_time': processing_time,
                    'max_concurrent': max_concurrent
                }
            }
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }