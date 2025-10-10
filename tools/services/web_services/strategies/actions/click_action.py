#!/usr/bin/env python
"""
Click Action Strategy - Enhanced click capabilities
Supports multiple element location strategies
"""
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
from ..base import ActionStrategy
from core.logging import get_logger

logger = get_logger(__name__)


class ClickActionStrategy(ActionStrategy):
    """Enhanced click action with multiple location strategies"""
    
    async def execute(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute click action with multiple location strategies
        
        Params can include:
        - x, y: Coordinates for direct click
        - selector: CSS selector
        - text: Text content to click
        - xpath: XPath selector
        - role: ARIA role
        - label: ARIA label
        - index: Element index if multiple matches
        - force: Force click even if element is hidden
        - button: 'left', 'right', 'middle'
        - click_count: Number of clicks (double-click, etc.)
        - modifiers: List of keys to hold ['Control', 'Shift', 'Alt']
        """
        try:
            # Priority 1: Direct coordinates
            if 'x' in params and 'y' in params:
                modifiers = params.get('modifiers', [])
                
                # Hold down modifier keys if specified
                for modifier in modifiers:
                    await page.keyboard.down(modifier)
                
                try:
                    await page.mouse.click(
                        params['x'], 
                        params['y'],
                        button=params.get('button', 'left'),
                        click_count=params.get('click_count', 1)
                    )
                finally:
                    # Release modifier keys
                    for modifier in reversed(modifiers):
                        await page.keyboard.up(modifier)
                logger.info(f"Clicked at coordinates ({params['x']}, {params['y']})")
                return {'success': True, 'method': 'coordinates'}
            
            # Priority 2: CSS Selector
            if 'selector' in params:
                element = page.locator(params['selector'])
                if params.get('index') is not None:
                    element = element.nth(params['index'])
                    
                await element.click(
                    force=params.get('force', False),
                    button=params.get('button', 'left'),
                    click_count=params.get('click_count', 1),
                    modifiers=params.get('modifiers', [])
                )
                logger.info(f"Clicked element with selector: {params['selector']}")
                return {'success': True, 'method': 'selector'}
            
            # Priority 3: Text content
            if 'text' in params:
                element = page.get_by_text(params['text'])
                if params.get('exact', False):
                    element = page.get_by_text(params['text'], exact=True)
                    
                await element.click(
                    force=params.get('force', False),
                    button=params.get('button', 'left'),
                    click_count=params.get('click_count', 1)
                )
                logger.info(f"Clicked element with text: {params['text']}")
                return {'success': True, 'method': 'text'}
            
            # Priority 4: XPath
            if 'xpath' in params:
                await page.locator(f"xpath={params['xpath']}").click(
                    force=params.get('force', False)
                )
                logger.info(f"Clicked element with xpath: {params['xpath']}")
                return {'success': True, 'method': 'xpath'}
            
            # Priority 5: ARIA role
            if 'role' in params:
                element = page.get_by_role(
                    params['role'],
                    name=params.get('name'),
                    exact=params.get('exact', False)
                )
                await element.click(force=params.get('force', False))
                logger.info(f"Clicked element with role: {params['role']}")
                return {'success': True, 'method': 'role'}
            
            # Priority 6: ARIA label
            if 'label' in params:
                element = page.get_by_label(params['label'])
                await element.click(force=params.get('force', False))
                logger.info(f"Clicked element with label: {params['label']}")
                return {'success': True, 'method': 'label'}
            
            return {
                'success': False, 
                'error': 'No valid location strategy provided'
            }
            
        except Exception as e:
            logger.error(f"Click action failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_action_name(self) -> str:
        return "click"
    
    def get_required_params(self) -> List[str]:
        # At least one location strategy is required
        return []  # Validated in validate_params
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """At least one location strategy must be provided"""
        location_strategies = ['x', 'selector', 'text', 'xpath', 'role', 'label']
        
        # Check if coordinates are provided together
        if 'x' in params:
            return 'y' in params
        
        # Check if any other location strategy is provided
        return any(key in params for key in location_strategies)