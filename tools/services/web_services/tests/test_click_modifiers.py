#!/usr/bin/env python3
"""
Test for coordinate-based click with modifiers functionality
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.services.web_services.strategies.actions.click_action import ClickActionStrategy


class TestClickActionModifiers:
    """Test coordinate-based click with modifiers"""
    
    @pytest.mark.asyncio
    async def test_coordinate_click_with_modifiers(self):
        """Test that coordinate-based click properly handles modifiers"""
        # Create mock page with mouse and keyboard
        page = MagicMock()
        page.mouse = AsyncMock()
        page.keyboard = AsyncMock()
        
        # Create click action strategy
        strategy = ClickActionStrategy()
        
        # Test parameters with modifiers
        params = {
            'x': 100,
            'y': 200,
            'modifiers': ['Control', 'Shift'],
            'button': 'left',
            'click_count': 1
        }
        
        # Execute the click action
        result = await strategy.execute(page, params)
        
        # Verify modifiers were pressed down in order
        page.keyboard.down.assert_any_call('Control')
        page.keyboard.down.assert_any_call('Shift')
        
        # Verify mouse click was called with correct parameters
        page.mouse.click.assert_called_once_with(100, 200, button='left', click_count=1)
        
        # Verify modifiers were released in reverse order
        page.keyboard.up.assert_any_call('Shift')
        page.keyboard.up.assert_any_call('Control')
        
        # Check result
        assert result['success'] is True
        assert result['method'] == 'coordinates'
    
    @pytest.mark.asyncio
    async def test_coordinate_click_without_modifiers(self):
        """Test that coordinate-based click works without modifiers"""
        # Create mock page
        page = MagicMock()
        page.mouse = AsyncMock()
        page.keyboard = AsyncMock()
        
        strategy = ClickActionStrategy()
        
        # Test parameters without modifiers
        params = {
            'x': 150,
            'y': 250,
            'button': 'right',
            'click_count': 2
        }
        
        result = await strategy.execute(page, params)
        
        # Verify no keyboard events were called
        page.keyboard.down.assert_not_called()
        page.keyboard.up.assert_not_called()
        
        # Verify mouse click was called
        page.mouse.click.assert_called_once_with(150, 250, button='right', click_count=2)
        
        assert result['success'] is True
        assert result['method'] == 'coordinates'
    
    @pytest.mark.asyncio
    async def test_coordinate_click_modifier_cleanup_on_exception(self):
        """Test that modifiers are properly released even if click fails"""
        # Create mock page where mouse.click raises an exception
        page = MagicMock()
        page.mouse = AsyncMock()
        page.mouse.click.side_effect = Exception("Click failed")
        page.keyboard = AsyncMock()
        
        strategy = ClickActionStrategy()
        
        params = {
            'x': 100,
            'y': 200,
            'modifiers': ['Control', 'Alt']
        }
        
        result = await strategy.execute(page, params)
        
        # Verify modifiers were pressed
        page.keyboard.down.assert_any_call('Control')
        page.keyboard.down.assert_any_call('Alt')
        
        # Verify modifiers were still released despite the exception
        page.keyboard.up.assert_any_call('Alt')
        page.keyboard.up.assert_any_call('Control')
        
        # Check that the error was handled
        assert result['success'] is False
        assert 'Click failed' in result['error']
    
    @pytest.mark.asyncio
    async def test_element_click_with_modifiers_unchanged(self):
        """Test that element-based clicks with modifiers still work as before"""
        # Create mock page and element
        page = MagicMock()
        element = AsyncMock()
        page.locator.return_value = element
        
        strategy = ClickActionStrategy()
        
        # Test element-based click with modifiers (should work as before)
        params = {
            'selector': '.test-button',
            'modifiers': ['Control'],
            'force': True
        }
        
        result = await strategy.execute(page, params)
        
        # Verify element click was called with modifiers
        element.click.assert_called_once_with(
            force=True,
            button='left',
            click_count=1,
            modifiers=['Control']
        )
        
        assert result['success'] is True
        assert result['method'] == 'selector'


if __name__ == "__main__":
    # Run a simple test
    async def run_simple_test():
        test_instance = TestClickActionModifiers()
        await test_instance.test_coordinate_click_with_modifiers()
        print("✓ Coordinate click with modifiers test passed")
        
        await test_instance.test_coordinate_click_without_modifiers()
        print("✓ Coordinate click without modifiers test passed")
        
        await test_instance.test_coordinate_click_modifier_cleanup_on_exception()
        print("✓ Modifier cleanup on exception test passed")
        
        await test_instance.test_element_click_with_modifiers_unchanged()
        print("✓ Element click with modifiers test passed")
        
        print("\nAll tests passed! ✅")
    
    asyncio.run(run_simple_test())