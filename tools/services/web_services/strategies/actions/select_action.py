#!/usr/bin/env python
"""
Select Action Strategy - Dropdown and select element handling
"""
from typing import Dict, Any, List
from playwright.async_api import Page
from ..base import ActionStrategy
from core.logging import get_logger

logger = get_logger(__name__)


class SelectActionStrategy(ActionStrategy):
    """Handle dropdown/select elements"""
    
    async def execute(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute select action on dropdown elements
        
        Params:
        - selector: CSS selector for select element
        - value: Option value to select
        - label: Option label/text to select
        - index: Option index to select
        - xpath: XPath selector for select element
        """
        try:
            # Locate the select element
            element = None
            
            if 'selector' in params:
                element = page.locator(params['selector'])
            elif 'xpath' in params:
                element = page.locator(f"xpath={params['xpath']}")
            elif 'label' in params:
                # Find select by its label
                element = page.get_by_label(params['label'])
            
            if not element:
                return {
                    'success': False,
                    'error': 'No select element found'
                }
            
            # Select by different strategies
            if 'value' in params:
                await element.select_option(value=params['value'])
                logger.info(f"Selected option by value: {params['value']}")
                return {'success': True, 'method': 'value', 'selected': params['value']}
            
            elif 'label' in params and 'selector' in params:
                # Label here means option text
                await element.select_option(label=params['label'])
                logger.info(f"Selected option by label: {params['label']}")
                return {'success': True, 'method': 'label', 'selected': params['label']}
            
            elif 'index' in params:
                await element.select_option(index=params['index'])
                logger.info(f"Selected option by index: {params['index']}")
                return {'success': True, 'method': 'index', 'selected': params['index']}
            
            elif 'text' in params:
                # Alternative: select by visible text
                await element.select_option(label=params['text'])
                logger.info(f"Selected option by text: {params['text']}")
                return {'success': True, 'method': 'text', 'selected': params['text']}
            
            return {
                'success': False,
                'error': 'No selection criteria provided (value, label, index, or text)'
            }
            
        except Exception as e:
            logger.error(f"Select action failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_action_name(self) -> str:
        return "select"
    
    def get_required_params(self) -> List[str]:
        return []  # Validated in validate_params
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Need element locator and selection criteria"""
        has_locator = any(key in params for key in ['selector', 'xpath', 'label'])
        has_selection = any(key in params for key in ['value', 'index', 'text'])
        return has_locator and (has_selection or 'label' in params)