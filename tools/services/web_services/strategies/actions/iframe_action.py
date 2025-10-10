#!/usr/bin/env python
"""
iFrame Action Strategy - Handle iframe switching and interactions
"""
from typing import Dict, Any, List
from playwright.async_api import Page, FrameLocator
from ..base import ActionStrategy
from core.logging import get_logger

logger = get_logger(__name__)


class IFrameActionStrategy(ActionStrategy):
    """Handle iframe switching and interactions"""
    
    def __init__(self):
        self.current_frame_stack: List[str] = []  # Track frame navigation
    
    async def execute(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute iframe action

        Params:
        - mode: 'enter', 'exit', 'switch', 'info' (operation mode)
        - selector: CSS selector for iframe (for enter/switch)
        - name: Name attribute of iframe
        - index: Index of iframe (0-based)
        - url: URL pattern to match iframe src

        Example:
        - {"action": "iframe", "mode": "enter", "selector": "#content-frame"}
        - {"action": "iframe", "mode": "enter", "name": "payment-iframe"}
        - {"action": "iframe", "mode": "enter", "index": 0}
        - {"action": "iframe", "mode": "exit"}  # Return to main frame
        - {"action": "iframe", "mode": "info"}  # Get iframe info
        """
        try:
            # Support both 'mode' and 'operation' for backwards compatibility
            action = params.get('mode') or params.get('operation', 'enter')
            
            if action == 'enter' or action == 'switch':
                # Find the iframe
                frame_locator = None
                
                if 'selector' in params:
                    frame_locator = page.frame_locator(params['selector'])
                    logger.info(f"Entering iframe with selector: {params['selector']}")
                    
                elif 'name' in params:
                    frame_locator = page.frame_locator(f'iframe[name="{params["name"]}"]')
                    logger.info(f"Entering iframe with name: {params['name']}")
                    
                elif 'index' in params:
                    # Get all iframes and select by index
                    frame_locator = page.frame_locator(f'iframe').nth(params['index'])
                    logger.info(f"Entering iframe at index: {params['index']}")
                    
                elif 'url' in params:
                    # Find iframe by src URL pattern
                    frame_locator = page.frame_locator(f'iframe[src*="{params["url"]}"]')
                    logger.info(f"Entering iframe with URL pattern: {params['url']}")
                
                if not frame_locator:
                    return {
                        'success': False,
                        'error': 'No iframe locator strategy provided'
                    }
                
                # Store frame context for nested navigation
                frame_id = params.get('selector') or params.get('name') or str(params.get('index'))
                self.current_frame_stack.append(frame_id)
                
                # Return the frame locator for subsequent actions
                return {
                    'success': True,
                    'action': 'enter',
                    'frame_id': frame_id,
                    'frame_locator': frame_locator,
                    'frame_stack_depth': len(self.current_frame_stack)
                }
            
            elif action == 'exit' or action == 'leave':
                # Return to parent frame or main document
                if self.current_frame_stack:
                    exited_frame = self.current_frame_stack.pop()
                    logger.info(f"Exited iframe: {exited_frame}")
                else:
                    logger.info("Returned to main document")
                
                return {
                    'success': True,
                    'action': 'exit',
                    'frame_stack_depth': len(self.current_frame_stack)
                }
            
            elif action == 'info':
                # Get information about iframes on the page
                iframe_info = await self._get_iframe_info(page)
                return {
                    'success': True,
                    'action': 'info',
                    'iframes': iframe_info,
                    'count': len(iframe_info)
                }
            
            else:
                return {
                    'success': False,
                    'error': f'Invalid iframe action: {action}'
                }
            
        except Exception as e:
            logger.error(f"iFrame action failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_iframe_info(self, page: Page) -> List[Dict[str, Any]]:
        """Get information about all iframes on the page"""
        try:
            iframe_info = await page.evaluate("""() => {
                const iframes = Array.from(document.querySelectorAll('iframe'));
                return iframes.map((iframe, index) => ({
                    index: index,
                    id: iframe.id || null,
                    name: iframe.name || null,
                    src: iframe.src || null,
                    width: iframe.width || iframe.style.width || null,
                    height: iframe.height || iframe.style.height || null,
                    visible: iframe.offsetParent !== null,
                    sandbox: iframe.sandbox ? iframe.sandbox.toString() : null,
                    title: iframe.title || null
                }));
            }""")
            return iframe_info if iframe_info else []
        except Exception as e:
            logger.error(f"Failed to get iframe info: {e}")
            return []
    
    def get_action_name(self) -> str:
        return "iframe"
    
    def get_required_params(self) -> List[str]:
        return []  # No strictly required params, depends on action
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate based on action type"""
        action = params.get('action', 'enter')
        
        if action in ['enter', 'switch']:
            # Need at least one locator strategy
            locator_strategies = ['selector', 'name', 'index', 'url']
            return any(key in params for key in locator_strategies)
        
        # exit and info don't need additional params
        return True