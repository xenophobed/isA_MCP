#!/usr/bin/env python
"""
Wait Action Strategy - Smart waiting capabilities
"""
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
import asyncio
from ..base import ActionStrategy
from core.logging import get_logger

logger = get_logger(__name__)


class WaitActionStrategy(ActionStrategy):
    """Smart waiting strategies for dynamic content"""
    
    async def execute(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute wait action with various strategies
        
        Params:
        - wait_for: Type of wait ('selector', 'text', 'url', 'load_state', 'timeout', 'function')
        - selector: CSS selector to wait for (for wait_for='selector')
        - text: Text to wait for on page
        - url: URL pattern to wait for
        - state: Element state ('visible', 'hidden', 'attached', 'detached')
        - load_state: Page load state ('domcontentloaded', 'load', 'networkidle')
        - timeout: Max wait time in ms (default: 30000)
        - function: JavaScript function to evaluate
        """
        try:
            wait_for = params.get('wait_for', 'timeout')
            timeout = params.get('timeout', 30000)
            
            # Wait for selector
            if wait_for == 'selector' and 'selector' in params:
                state = params.get('state', 'visible')
                element = page.locator(params['selector'])
                
                if state == 'visible':
                    await element.wait_for(state='visible', timeout=timeout)
                elif state == 'hidden':
                    await element.wait_for(state='hidden', timeout=timeout)
                elif state == 'attached':
                    await element.wait_for(state='attached', timeout=timeout)
                elif state == 'detached':
                    await element.wait_for(state='detached', timeout=timeout)
                
                logger.info(f"Waited for selector {params['selector']} to be {state}")
                return {'success': True, 'method': 'selector', 'state': state}
            
            # Wait for text
            elif wait_for == 'text' and 'text' in params:
                await page.wait_for_function(
                    f"document.body.innerText.includes('{params['text']}')",
                    timeout=timeout
                )
                logger.info(f"Waited for text: {params['text']}")
                return {'success': True, 'method': 'text'}
            
            # Wait for URL change
            elif wait_for == 'url' and 'url' in params:
                await page.wait_for_url(params['url'], timeout=timeout)
                logger.info(f"Waited for URL: {params['url']}")
                return {'success': True, 'method': 'url'}
            
            # Wait for load state
            elif wait_for == 'load_state':
                load_state = params.get('load_state', 'networkidle')
                await page.wait_for_load_state(load_state, timeout=timeout)
                logger.info(f"Waited for load state: {load_state}")
                return {'success': True, 'method': 'load_state', 'state': load_state}
            
            # Wait for JavaScript function
            elif wait_for == 'function' and 'function' in params:
                await page.wait_for_function(params['function'], timeout=timeout)
                logger.info(f"Waited for function: {params['function'][:50]}...")
                return {'success': True, 'method': 'function'}
            
            # Simple timeout wait
            elif wait_for == 'timeout' or 'duration' in params:
                duration = params.get('duration', params.get('timeout', 1000))
                await asyncio.sleep(duration / 1000)
                logger.info(f"Waited for {duration}ms")
                return {'success': True, 'method': 'timeout', 'duration': duration}
            
            # Wait for navigation
            elif wait_for == 'navigation':
                async with page.expect_navigation(timeout=timeout):
                    pass  # Wait for navigation to complete
                logger.info("Waited for navigation")
                return {'success': True, 'method': 'navigation'}
            
            return {
                'success': False,
                'error': f'Invalid wait_for type: {wait_for}'
            }
            
        except Exception as e:
            logger.error(f"Wait action failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_action_name(self) -> str:
        return "wait"
    
    def get_required_params(self) -> List[str]:
        return []  # wait_for has default value
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Always valid with default timeout"""
        return True