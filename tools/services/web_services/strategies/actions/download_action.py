#!/usr/bin/env python
"""
File Download Action Strategy - Handle file downloads
"""
from typing import Dict, Any, List
from pathlib import Path
from playwright.async_api import Page, Download
from ..base import ActionStrategy
from core.logging import get_logger

logger = get_logger(__name__)


class DownloadActionStrategy(ActionStrategy):
    """Handle file download actions"""

    async def execute(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute download action

        Params:
        - trigger: How to trigger download
          - "click": Click on element (requires selector or coordinates)
          - "navigate": Navigate to URL directly
        - selector: CSS selector for download link/button (for trigger=click)
        - url: Direct download URL (for trigger=navigate)
        - save_path: Path to save downloaded file (optional, defaults to /tmp/downloads/)
        - filename: Override filename (optional)
        - timeout: Download timeout in milliseconds (default: 30000)
        - wait_for_complete: Wait for download to complete (default: True)

        Example:
        - {"trigger": "click", "selector": "a.download-btn", "save_path": "/tmp/myfile.pdf"}
        - {"trigger": "navigate", "url": "https://example.com/file.zip"}
        """
        try:
            trigger = params.get('trigger', 'click')
            timeout = params.get('timeout', 30000)
            wait_for_complete = params.get('wait_for_complete', True)
            save_path = params.get('save_path')
            filename_override = params.get('filename')

            # Setup download handler
            download_info = None

            async with page.expect_download(timeout=timeout) as download_context:
                if trigger == 'click':
                    # Click to trigger download
                    selector = params.get('selector')
                    if not selector:
                        return {
                            'success': False,
                            'error': 'Selector required for click trigger'
                        }

                    element = page.locator(selector)
                    await element.click()
                    logger.info(f"Clicked download trigger: {selector}")

                elif trigger == 'navigate':
                    # Navigate to download URL
                    url = params.get('url')
                    if not url:
                        return {
                            'success': False,
                            'error': 'URL required for navigate trigger'
                        }

                    await page.goto(url)
                    logger.info(f"Navigated to download URL: {url}")

                else:
                    return {
                        'success': False,
                        'error': f'Invalid trigger type: {trigger}'
                    }

            # Get the download object
            download: Download = await download_context.value

            # Get suggested filename
            suggested_filename = await download.suggested_filename()
            final_filename = filename_override or suggested_filename

            # Determine save path
            if save_path:
                save_path = Path(save_path)
                if save_path.is_dir():
                    save_path = save_path / final_filename
            else:
                # Default to /tmp/downloads/
                save_path = Path(f"/tmp/downloads/{final_filename}")

            # Create directory if needed
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # Save the download
            await download.save_as(str(save_path))
            logger.info(f"Download saved: {save_path}")

            # Get download info
            download_info = {
                'success': True,
                'action': 'download',
                'filename': final_filename,
                'suggested_filename': suggested_filename,
                'save_path': str(save_path.absolute()),
                'exists': save_path.exists(),
                'size_bytes': save_path.stat().st_size if save_path.exists() else 0,
                'url': await download.url() if hasattr(download, 'url') else None
            }

            # Wait for download to complete if requested
            if wait_for_complete:
                failure = await download.failure()
                if failure:
                    download_info['success'] = False
                    download_info['error'] = f'Download failed: {failure}'
                    logger.error(f"Download failed: {failure}")

            return download_info

        except TimeoutError:
            logger.error("Download timeout - no download was triggered")
            return {
                'success': False,
                'error': 'Download timeout - no download was triggered within timeout period'
            }
        except Exception as e:
            logger.error(f"Download action failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_action_name(self) -> str:
        return "download"

    def get_required_params(self) -> List[str]:
        return ['trigger']

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate download parameters"""
        trigger = params.get('trigger')

        if trigger == 'click':
            return 'selector' in params
        elif trigger == 'navigate':
            return 'url' in params

        return False