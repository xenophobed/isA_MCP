#!/usr/bin/env python
"""
File Upload Action Strategy - Handle file uploads
"""
from typing import Dict, Any, List
from pathlib import Path
from playwright.async_api import Page
from ..base import ActionStrategy
from core.logging import get_logger

logger = get_logger(__name__)


class UploadActionStrategy(ActionStrategy):
    """Handle file upload actions"""
    
    async def execute(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute file upload action
        
        Params:
        - files: Single file path or list of file paths
        - selector: CSS selector for file input
        - accept: Accept attribute pattern (optional, for validation)
        
        Example:
        - {"files": "/path/to/file.pdf", "selector": "input[type='file']"}
        - {"files": ["/path/to/file1.pdf", "/path/to/file2.jpg"], "selector": "#file-upload"}
        """
        try:
            files = params.get('files')
            selector = params.get('selector', 'input[type="file"]')
            
            if not files:
                return {
                    'success': False,
                    'error': 'No files specified for upload'
                }
            
            # Convert single file to list
            if isinstance(files, str):
                files = [files]
            
            # Validate files exist
            valid_files = []
            for file_path in files:
                path = Path(file_path)
                if path.exists() and path.is_file():
                    valid_files.append(str(path.absolute()))
                else:
                    logger.warning(f"File not found: {file_path}")
            
            if not valid_files:
                return {
                    'success': False,
                    'error': 'No valid files found for upload'
                }
            
            # Find the file input element
            try:
                file_input = page.locator(selector)
                
                # Check if input accepts the file type
                if 'accept' in params:
                    accept_attr = await file_input.get_attribute('accept')
                    if accept_attr:
                        logger.info(f"File input accepts: {accept_attr}")
                
                # Upload the files
                if len(valid_files) == 1:
                    await file_input.set_input_files(valid_files[0])
                    logger.info(f"Uploaded file: {valid_files[0]}")
                else:
                    # Multiple file upload
                    await file_input.set_input_files(valid_files)
                    logger.info(f"Uploaded {len(valid_files)} files")
                
                # Wait a moment for upload to register
                await page.wait_for_timeout(500)
                
                return {
                    'success': True,
                    'action': 'upload',
                    'files_uploaded': valid_files,
                    'count': len(valid_files),
                    'selector': selector
                }
                
            except Exception as e:
                # Try alternative upload method (for hidden inputs)
                if 'force' in params and params['force']:
                    try:
                        # Make input visible and try again
                        await page.evaluate(f"""
                            const input = document.querySelector('{selector}');
                            if (input) {{
                                input.style.display = 'block';
                                input.style.visibility = 'visible';
                                input.style.opacity = '1';
                            }}
                        """)
                        
                        file_input = page.locator(selector)
                        await file_input.set_input_files(valid_files)
                        
                        return {
                            'success': True,
                            'action': 'upload',
                            'files_uploaded': valid_files,
                            'count': len(valid_files),
                            'forced': True
                        }
                    except:
                        pass
                
                raise e
            
        except Exception as e:
            logger.error(f"Upload action failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'selector': selector
            }
    
    def get_action_name(self) -> str:
        return "upload"
    
    def get_required_params(self) -> List[str]:
        return ['files']
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate upload parameters"""
        return 'files' in params