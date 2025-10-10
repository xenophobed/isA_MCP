#!/usr/bin/env python
"""
Navigate Action Strategy - Browser navigation actions
"""
from typing import Dict, Any, List
from playwright.async_api import Page
from ..base import ActionStrategy
from core.logging import get_logger

logger = get_logger(__name__)


class NavigateActionStrategy(ActionStrategy):
    """Handle browser navigation actions"""
    
    async def execute(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute navigation action
        
        Params:
        - action: 'goto', 'back', 'forward', 'reload', 'stop'
        - url: URL to navigate to (for 'goto' action)
        - wait_until: Wait condition for goto ('load', 'domcontentloaded', 'networkidle')
        - timeout: Navigation timeout in ms
        """
        try:
            action = params.get('action', 'goto')
            timeout = params.get('timeout', 30000)
            
            if action == 'goto' and 'url' in params:
                wait_until = params.get('wait_until', 'domcontentloaded')
                await page.goto(
                    params['url'],
                    wait_until=wait_until,
                    timeout=timeout
                )
                logger.info(f"Navigated to: {params['url']}")
                return {'success': True, 'action': 'goto', 'url': params['url']}
            
            elif action == 'back':
                await page.go_back(timeout=timeout)
                logger.info("Navigated back")
                return {'success': True, 'action': 'back', 'url': page.url}
            
            elif action == 'forward':
                await page.go_forward(timeout=timeout)
                logger.info("Navigated forward")
                return {'success': True, 'action': 'forward', 'url': page.url}
            
            elif action == 'reload' or action == 'refresh':
                await page.reload(timeout=timeout)
                logger.info("Page reloaded")
                return {'success': True, 'action': 'reload', 'url': page.url}
            
            elif action == 'stop':
                # Stop loading the page
                await page.evaluate('window.stop()')
                logger.info("Stopped page loading")
                return {'success': True, 'action': 'stop'}
            
            return {
                'success': False,
                'error': f'Invalid navigation action: {action}'
            }
            
        except Exception as e:
            logger.error(f"Navigate action failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_action_name(self) -> str:
        return "navigate"
    
    def get_required_params(self) -> List[str]:
        return []  # Validated based on action type
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate based on action type"""
        action = params.get('action', 'goto')
        if action == 'goto':
            return 'url' in params
        return True  # Other actions don't need additional params