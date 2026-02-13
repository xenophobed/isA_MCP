#!/usr/bin/env python
"""
Image Helper Functions

Utility functions for image processing and screenshot management.

NOTE: Playwright is now optional. If not available, screenshot functionality
will be disabled. Use external vision service for screenshot capabilities.
"""

import tempfile
import os
import logging
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    # Only import for type checking, not at runtime
    from playwright.async_api import Page
else:
    # Try to import but don't fail if not available
    try:
        from playwright.async_api import Page
    except (ImportError, ModuleNotFoundError):
        Page = None

logger = logging.getLogger(__name__)


async def save_screenshot(page, filename: str = None) -> str:
    """
    Take screenshot and save to file

    NOTE: Requires playwright to be installed. If not available, raises ImportError.

    Args:
        page: Playwright page (if playwright available)
        filename: Optional filename, creates temp file if not provided

    Returns:
        Path to saved screenshot

    Raises:
        ImportError: If playwright is not installed
    """
    if Page is None:
        raise ImportError(
            "Playwright not available. Screenshot functionality disabled. "
            "Use external vision service for screenshots."
        )

    if filename:
        await page.screenshot(path=filename)
        return filename
    else:
        screenshot = await page.screenshot()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
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
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
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
