#!/usr/bin/env python
"""
Action Executor - Coordinates and executes browser action strategies
Central hub for all automation actions with enhanced capabilities
"""
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
import asyncio

from core.logging import get_logger
from ..strategies.base import ActionStrategy
from ..strategies.actions import (
    ClickActionStrategy,
    TypeActionStrategy,
    SelectActionStrategy,
    ScrollActionStrategy,
    HoverActionStrategy,
    WaitActionStrategy,
    NavigateActionStrategy,
    CheckboxActionStrategy,
    IFrameActionStrategy,
    UploadActionStrategy,
    DownloadActionStrategy,
    DragActionStrategy
)

logger = get_logger(__name__)


class ActionExecutor:
    """
    Coordinates execution of browser actions using strategy pattern
    Provides unified interface for all automation actions
    """
    
    def __init__(self):
        """Initialize with all available action strategies"""
        self.strategies: Dict[str, ActionStrategy] = {}
        self._register_default_strategies()
        logger.info(f"✅ ActionExecutor initialized with {len(self.strategies)} strategies")
    
    def _register_default_strategies(self):
        """Register all default action strategies"""
        default_strategies = [
            ClickActionStrategy(),
            TypeActionStrategy(),
            SelectActionStrategy(),
            ScrollActionStrategy(),
            HoverActionStrategy(),
            WaitActionStrategy(),
            NavigateActionStrategy(),
            CheckboxActionStrategy(),
            IFrameActionStrategy(),
            UploadActionStrategy(),
            DownloadActionStrategy(),
            DragActionStrategy()
        ]

        for strategy in default_strategies:
            self.register_strategy(strategy)
    
    def register_strategy(self, strategy: ActionStrategy):
        """Register a new action strategy"""
        name = strategy.get_action_name()
        self.strategies[name] = strategy
        logger.debug(f"Registered action strategy: {name}")
    
    async def execute_action(
        self,
        page: Page,
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single action using the appropriate strategy
        
        Args:
            page: Playwright page instance
            action: Action dictionary with 'action' field and parameters
            
        Returns:
            Execution result dictionary
        """
        try:
            action_type = action.get('action', 'click')
            
            # Special handling for press/key actions
            if action_type == 'press' or action_type == 'key':
                return await self._execute_key_press(page, action)
            
            # Special handling for screenshot
            if action_type == 'screenshot':
                return await self._execute_screenshot(page, action)
            
            # Get the appropriate strategy
            strategy = self.strategies.get(action_type)
            if not strategy:
                logger.warning(f"Unknown action type: {action_type}")
                return {
                    'success': False,
                    'error': f'Unknown action type: {action_type}',
                    'available_actions': list(self.strategies.keys())
                }
            
            # Validate parameters
            if not strategy.validate_params(action):
                required = strategy.get_required_params()
                return {
                    'success': False,
                    'error': f'Invalid parameters for {action_type}',
                    'required_params': required
                }
            
            # Execute the action
            logger.info(f"Executing action: {action_type}")
            result = await strategy.execute(page, action)
            
            # Add action type to result
            result['action_type'] = action_type
            return result
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'action': action
            }
    
    async def execute_action_sequence(
        self,
        page: Page,
        actions: List[Dict[str, Any]],
        delay_between_actions: int = 500,
        stop_on_error: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a sequence of actions
        
        Args:
            page: Playwright page instance
            actions: List of action dictionaries
            delay_between_actions: Delay in ms between actions
            stop_on_error: Stop execution on first error
            
        Returns:
            Summary of execution results
        """
        results = []
        successful = 0
        failed = 0
        
        for i, action in enumerate(actions):
            logger.info(f"Executing action {i+1}/{len(actions)}: {action.get('action', 'unknown')}")
            
            # Execute the action
            result = await self.execute_action(page, action)
            results.append(result)
            
            if result.get('success'):
                successful += 1
            else:
                failed += 1
                if stop_on_error:
                    logger.warning(f"Stopping execution due to error in action {i+1}")
                    break
            
            # Delay between actions (except after last action)
            if i < len(actions) - 1 and delay_between_actions > 0:
                await asyncio.sleep(delay_between_actions / 1000)
        
        return {
            'total_actions': len(actions),
            'executed': len(results),
            'successful': successful,
            'failed': failed,
            'results': results,
            'stopped_early': len(results) < len(actions)
        }
    
    async def _execute_key_press(self, page: Page, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute keyboard press action"""
        try:
            key = action.get('key', 'Enter')
            modifiers = action.get('modifiers', [])
            
            if modifiers:
                # Handle key combinations like Ctrl+A
                key_combo = '+'.join(modifiers + [key])
                await page.keyboard.press(key_combo)
                logger.info(f"Pressed key combination: {key_combo}")
            else:
                await page.keyboard.press(key)
                logger.info(f"Pressed key: {key}")
            
            return {'success': True, 'action_type': 'press', 'key': key}
            
        except Exception as e:
            logger.error(f"Key press failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_screenshot(self, page: Page, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute screenshot action"""
        try:
            path = action.get('path', 'screenshot.png')
            full_page = action.get('full_page', False)
            selector = action.get('selector')
            
            if selector:
                # Screenshot specific element
                element = page.locator(selector)
                screenshot = await element.screenshot(path=path)
                logger.info(f"Screenshot of element {selector} saved to {path}")
            else:
                # Screenshot page
                screenshot = await page.screenshot(
                    path=path,
                    full_page=full_page
                )
                logger.info(f"Screenshot saved to {path} (full_page: {full_page})")
            
            return {
                'success': True,
                'action_type': 'screenshot',
                'path': path
            }
            
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_available_actions(self) -> List[str]:
        """Get list of available action types"""
        return list(self.strategies.keys()) + ['press', 'key', 'screenshot']
    
    def get_action_info(self, action_type: str) -> Dict[str, Any]:
        """Get information about a specific action type"""
        if action_type in ['press', 'key']:
            return {
                'action': action_type,
                'description': 'Press keyboard key',
                'parameters': {
                    'key': 'Key to press (e.g., Enter, Tab, Escape)',
                    'modifiers': 'Optional list of modifier keys (Control, Shift, Alt)'
                }
            }
        
        if action_type == 'screenshot':
            return {
                'action': 'screenshot',
                'description': 'Take screenshot of page or element',
                'parameters': {
                    'path': 'Path to save screenshot',
                    'full_page': 'Capture full page (default: False)',
                    'selector': 'Optional CSS selector for element screenshot'
                }
            }
        
        strategy = self.strategies.get(action_type)
        if strategy:
            return {
                'action': action_type,
                'required_params': strategy.get_required_params(),
                'description': f'{action_type} action strategy'
            }
        
        return {
            'error': f'Unknown action type: {action_type}',
            'available': self.get_available_actions()
        }


# Singleton instance
_executor_instance: Optional[ActionExecutor] = None


def get_action_executor() -> ActionExecutor:
    """Get singleton ActionExecutor instance"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = ActionExecutor()
    return _executor_instance