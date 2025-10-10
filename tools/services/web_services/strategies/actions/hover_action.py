#!/usr/bin/env python
"""
Hover Action Strategy - Mouse hover interactions
"""
from typing import Dict, Any, List
from playwright.async_api import Page
import asyncio
from ..base import ActionStrategy
from core.logging import get_logger

logger = get_logger(__name__)


class HoverActionStrategy(ActionStrategy):
    """Handle mouse hover interactions"""
    
    async def execute(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute hover action
        
        Params:
        - selector: CSS selector for element to hover
        - x, y: Coordinates to hover at
        - text: Text of element to hover
        - xpath: XPath selector
        - duration: How long to hover in ms (default: 500)
        - force: Force hover even if element is hidden
        """
        try:
            duration = params.get('duration', 500)
            
            # Priority 1: CSS Selector
            if 'selector' in params:
                element = page.locator(params['selector'])
                await element.hover(force=params.get('force', False))
                await asyncio.sleep(duration / 1000)
                logger.info(f"Hovered over element: {params['selector']}")
                return {'success': True, 'method': 'selector'}
            
            # Priority 2: Coordinates
            elif 'x' in params and 'y' in params:
                await page.mouse.move(params['x'], params['y'])
                await asyncio.sleep(duration / 1000)
                logger.info(f"Hovered at coordinates ({params['x']}, {params['y']})")
                return {'success': True, 'method': 'coordinates'}
            
            # Priority 3: Text
            elif 'text' in params:
                element = page.get_by_text(params['text'])
                await element.hover(force=params.get('force', False))
                await asyncio.sleep(duration / 1000)
                logger.info(f"Hovered over text: {params['text']}")
                return {'success': True, 'method': 'text'}
            
            # Priority 4: XPath
            elif 'xpath' in params:
                element = page.locator(f"xpath={params['xpath']}")
                await element.hover(force=params.get('force', False))
                await asyncio.sleep(duration / 1000)
                logger.info(f"Hovered over xpath: {params['xpath']}")
                return {'success': True, 'method': 'xpath'}
            
            return {
                'success': False,
                'error': 'No hover target specified'
            }
            
        except Exception as e:
            logger.error(f"Hover action failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_action_name(self) -> str:
        return "hover"
    
    def get_required_params(self) -> List[str]:
        return []  # Validated in validate_params
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Need at least one location strategy"""
        location_strategies = ['selector', 'x', 'text', 'xpath']
        
        if 'x' in params:
            return 'y' in params
        
        return any(key in params for key in location_strategies)