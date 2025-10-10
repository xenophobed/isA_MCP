#!/usr/bin/env python
"""
Type Action Strategy - Enhanced text input capabilities
Supports clear before type, delayed typing, and multiple location strategies
"""
from typing import Dict, Any, List
from playwright.async_api import Page
import asyncio
from ..base import ActionStrategy
from core.logging import get_logger

logger = get_logger(__name__)


class TypeActionStrategy(ActionStrategy):
    """Enhanced type action with multiple features"""
    
    async def execute(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute type action with enhanced features
        
        Params:
        - text: Text to type (required)
        - selector: CSS selector for input field
        - x, y: Coordinates to click before typing
        - xpath: XPath selector
        - label: Input label
        - placeholder: Input placeholder text
        - clear_first: Clear field before typing (default: True)
        - delay: Delay between keystrokes in ms
        - press_enter: Press Enter after typing
        - press_tab: Press Tab after typing
        """
        try:
            text = params.get('text', '')
            
            # Locate the input field
            element = None
            method = None
            
            # Priority 1: CSS Selector
            if 'selector' in params:
                element = page.locator(params['selector'])
                method = 'selector'
            
            # Priority 2: Coordinates (click first)
            elif 'x' in params and 'y' in params:
                await page.mouse.click(params['x'], params['y'])
                await asyncio.sleep(0.2)  # Small delay after click
                method = 'coordinates'
            
            # Priority 3: Label
            elif 'label' in params:
                element = page.get_by_label(params['label'])
                method = 'label'
            
            # Priority 4: Placeholder
            elif 'placeholder' in params:
                element = page.get_by_placeholder(params['placeholder'])
                method = 'placeholder'
            
            # Priority 5: XPath
            elif 'xpath' in params:
                element = page.locator(f"xpath={params['xpath']}")
                method = 'xpath'
            
            # If we have an element, interact with it
            if element:
                # Click to focus
                await element.click()
                await asyncio.sleep(0.1)
                
                # Clear if requested (default: True for form fields)
                if params.get('clear_first', True):
                    # Triple-click to select all, then delete
                    await element.click(click_count=3)
                    await page.keyboard.press('Delete')
                    # Alternative: Ctrl+A then Delete
                    # await page.keyboard.press('Control+A')
                    # await page.keyboard.press('Delete')
            
            # Type the text
            if params.get('delay'):
                # Type with delay between keystrokes
                await page.keyboard.type(text, delay=params['delay'])
            else:
                # Fast typing
                if element:
                    await element.fill(text)
                else:
                    await page.keyboard.type(text)
            
            logger.info(f"Typed text: '{text[:50]}...' using {method}")
            
            # Optional: Press Enter or Tab after typing
            if params.get('press_enter'):
                await page.keyboard.press('Enter')
                logger.info("Pressed Enter after typing")
            elif params.get('press_tab'):
                await page.keyboard.press('Tab')
                logger.info("Pressed Tab after typing")
            
            return {
                'success': True,
                'method': method,
                'text_length': len(text)
            }
            
        except Exception as e:
            logger.error(f"Type action failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_action_name(self) -> str:
        return "type"
    
    def get_required_params(self) -> List[str]:
        return ['text']
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Text is required, plus at least one location strategy"""
        if 'text' not in params:
            return False
        
        location_strategies = ['selector', 'x', 'label', 'placeholder', 'xpath']
        
        # Check if coordinates are provided together
        if 'x' in params:
            return 'y' in params
        
        # Check if any location strategy is provided
        return any(key in params for key in location_strategies)