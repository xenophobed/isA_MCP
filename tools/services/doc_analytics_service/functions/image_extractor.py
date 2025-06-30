#!/usr/bin/env python3
"""
Image extraction tool
"""

import logging
import os
import shutil
from typing import Dict, Any, Optional

from ..adapters.file_adapters.document_adapter import DocumentAdapter

logger = logging.getLogger(__name__)

def extract_images_from_document(file_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract all embedded images from a document.
    
    Args:
        file_path: Path to document file
        output_dir: Directory to save extracted images (optional)
        
    Returns:
        Image extraction results
    """
    try:
        adapter = DocumentAdapter()
        success = adapter.connect({'file_path': file_path})
        
        if not success:
            return {"error": "Failed to load document", "status": "failed"}
        
        extracted_images = adapter.get_extracted_images()
        
        # Copy images to output directory if specified
        saved_images = []
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
            for img in extracted_images:
                if img.image_path and os.path.exists(img.image_path):
                    filename = f"{img.image_id}.{img.metadata.get('format', 'png')}"
                    dest_path = os.path.join(output_dir, filename)
                    shutil.copy2(img.image_path, dest_path)
                    saved_images.append({
                        'image_id': img.image_id,
                        'saved_path': dest_path,
                        'page_number': img.page_number,
                        'original_path': img.image_path
                    })
        
        adapter.disconnect()
        
        return {
            "status": "success",
            "file_path": file_path,
            "images_extracted": len(extracted_images),
            "extracted_images": [
                {
                    "image_id": img.image_id,
                    "page_number": img.page_number,
                    "image_path": img.image_path,
                    "image_type": img.image_type,
                    "bbox": img.bbox,
                    "metadata": img.metadata
                }
                for img in extracted_images
            ],
            "saved_images": saved_images if output_dir else []
        }
        
    except Exception as e:
        logger.error(f"Image extraction failed: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "file_path": file_path
        }

def get_document_images_summary(file_path: str) -> Dict[str, Any]:
    """
    Get summary of all images in a document (both page images and extracted images).
    
    Args:
        file_path: Path to document file
        
    Returns:
        Images summary
    """
    try:
        adapter = DocumentAdapter()
        success = adapter.connect({'file_path': file_path})
        
        if not success:
            return {"error": "Failed to load document", "status": "failed"}
        
        page_images = adapter.get_page_images()
        extracted_images = adapter.get_extracted_images()
        
        # Group extracted images by page
        images_by_page = {}
        for img in extracted_images:
            page_num = img.page_number
            if page_num not in images_by_page:
                images_by_page[page_num] = []
            images_by_page[page_num].append({
                'image_id': img.image_id,
                'image_type': img.image_type,
                'format': img.metadata.get('format'),
                'size_bytes': img.metadata.get('size_bytes')
            })
        
        adapter.disconnect()
        
        return {
            "status": "success",
            "file_path": file_path,
            "summary": {
                "total_pages": len(page_images),
                "total_extracted_images": len(extracted_images),
                "page_images_available": len(page_images),
                "images_by_page": images_by_page
            },
            "page_images": page_images,
            "extracted_images_detail": [
                {
                    "image_id": img.image_id,
                    "page_number": img.page_number,
                    "image_type": img.image_type,
                    "metadata": img.metadata
                }
                for img in extracted_images
            ]
        }
        
    except Exception as e:
        logger.error(f"Images summary failed: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "file_path": file_path
        }

def convert_document_to_images(file_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert document pages to images.
    
    Args:
        file_path: Path to document file
        output_dir: Directory to save images (optional)
        
    Returns:
        Image conversion results
    """
    try:
        adapter = DocumentAdapter()
        success = adapter.connect({'file_path': file_path})
        
        if not success:
            return {"error": "Failed to load document", "status": "failed"}
        
        page_images = adapter.get_page_images()
        
        # Copy images to output directory if specified
        saved_images = []
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
            for i, image_path in enumerate(page_images):
                if image_path and os.path.exists(image_path):
                    filename = f"page_{i+1}.png"
                    dest_path = os.path.join(output_dir, filename)
                    shutil.copy2(image_path, dest_path)
                    saved_images.append(dest_path)
        
        structure = adapter._analyze_structure()
        adapter.disconnect()
        
        return {
            "status": "success",
            "file_path": file_path,
            "pages_converted": len(page_images),
            "image_paths": saved_images if output_dir else page_images,
            "temp_directory": structure.get('temp_directory'),
            "page_breakdown": structure.get('page_types', {})
        }
        
    except Exception as e:
        logger.error(f"Image conversion failed: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "file_path": file_path
        }