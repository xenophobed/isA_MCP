#!/usr/bin/env python
"""
Image Helper Functions

Utility functions for image processing and screenshot management.
"""

import tempfile
import os
from typing import Union
from playwright.async_api import Page


async def save_screenshot(page: Page, filename: str = None) -> str:
    """
    Take screenshot and save to file
    
    Args:
        page: Playwright page
        filename: Optional filename, creates temp file if not provided
        
    Returns:
        Path to saved screenshot
    """
    if filename:
        await page.screenshot(path=filename)
        return filename
    else:
        screenshot = await page.screenshot()
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(screenshot)
            return tmp.name


def prepare_image_input(image: Union[str, bytes]) -> str:
    """
    Prepare image input - convert bytes to temp file if needed
    
    Args:
        image: Image file path or bytes
        
    Returns:
        File path to image
    """
    if isinstance(image, str):
        # Already a file path
        return image
    elif isinstance(image, bytes):
        # Create temporary file for bytes
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(image)
            return tmp.name
    else:
        raise ValueError(f"Unsupported image type: {type(image)}")


def cleanup_temp_file(file_path: str):
    """
    Clean up temporary file safely
    
    Args:
        file_path: Path to file to delete
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except:
        pass  # Ignore cleanup errors