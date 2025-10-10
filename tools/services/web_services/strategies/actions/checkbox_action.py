#!/usr/bin/env python
"""
Checkbox Action Strategy - Handle checkboxes and radio buttons
"""
from typing import Dict, Any, List
from playwright.async_api import Page
from ..base import ActionStrategy
from core.logging import get_logger

logger = get_logger(__name__)


class CheckboxActionStrategy(ActionStrategy):
    """Handle checkbox and radio button interactions"""
    
    async def execute(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute checkbox/radio button action
        
        Params:
        - selector: CSS selector for checkbox/radio
        - label: Label text for checkbox/radio
        - name: Name attribute value
        - value: Value for radio button selection
        - action: 'check', 'uncheck', 'toggle' (default: 'check')
        - force: Force action even if element is hidden
        """
        try:
            action = params.get('action', 'check')
            
            # Locate the checkbox/radio element
            element = None
            
            if 'selector' in params:
                element = page.locator(params['selector'])
            elif 'label' in params:
                element = page.get_by_label(params['label'])
            elif 'name' in params:
                element = page.locator(f'input[name="{params["name"]}"]')
                if 'value' in params:
                    # Radio button with specific value
                    element = page.locator(f'input[name="{params["name"]}"][value="{params["value"]}"]')
            
            if not element:
                return {
                    'success': False,
                    'error': 'No checkbox/radio element found'
                }
            
            # Perform the action
            if action == 'check':
                await element.check(force=params.get('force', False))
                logger.info("Checked checkbox/radio")
                return {'success': True, 'action': 'check'}
            
            elif action == 'uncheck':
                await element.uncheck(force=params.get('force', False))
                logger.info("Unchecked checkbox")
                return {'success': True, 'action': 'uncheck'}
            
            elif action == 'toggle':
                is_checked = await element.is_checked()
                if is_checked:
                    await element.uncheck(force=params.get('force', False))
                    logger.info("Toggled checkbox to unchecked")
                    return {'success': True, 'action': 'toggle', 'state': 'unchecked'}
                else:
                    await element.check(force=params.get('force', False))
                    logger.info("Toggled checkbox to checked")
                    return {'success': True, 'action': 'toggle', 'state': 'checked'}
            
            return {
                'success': False,
                'error': f'Invalid action: {action}'
            }
            
        except Exception as e:
            logger.error(f"Checkbox action failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_action_name(self) -> str:
        return "checkbox"
    
    def get_required_params(self) -> List[str]:
        return []  # Validated in validate_params
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Need at least one location strategy"""
        location_strategies = ['selector', 'label', 'name']
        return any(key in params for key in location_strategies)