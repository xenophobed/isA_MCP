#!/usr/bin/env python
"""
Scroll Action Strategy - Page and element scrolling
"""
from typing import Dict, Any, List
from playwright.async_api import Page
from ..base import ActionStrategy
from core.logging import get_logger

logger = get_logger(__name__)


class ScrollActionStrategy(ActionStrategy):
    """Handle page and element scrolling"""
    
    async def execute(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute scroll action
        
        Params:
        - direction: 'up', 'down', 'left', 'right', 'top', 'bottom'
        - amount: Pixels to scroll (for up/down/left/right)
        - selector: Element to scroll (optional, defaults to page)
        - smooth: Smooth scrolling (default: True)
        - x: Horizontal scroll position (absolute)
        - y: Vertical scroll position (absolute)
        """
        try:
            direction = params.get('direction', 'down')
            amount = params.get('amount', 300)
            smooth = params.get('smooth', True)
            
            # Determine target element
            if 'selector' in params:
                # Scroll specific element
                element = page.locator(params['selector'])
                
                if direction == 'top':
                    await element.evaluate('(el) => el.scrollTop = 0')
                elif direction == 'bottom':
                    await element.evaluate('(el) => el.scrollTop = el.scrollHeight')
                elif direction == 'down':
                    await element.evaluate(f'(el) => el.scrollBy(0, {amount})')
                elif direction == 'up':
                    await element.evaluate(f'(el) => el.scrollBy(0, -{amount})')
                elif direction == 'left':
                    await element.evaluate(f'(el) => el.scrollBy(-{amount}, 0)')
                elif direction == 'right':
                    await element.evaluate(f'(el) => el.scrollBy({amount}, 0)')
                
                logger.info(f"Scrolled element {params['selector']} {direction} by {amount}px")
                return {'success': True, 'method': 'element', 'direction': direction}
            
            else:
                # Scroll the page
                if direction == 'top':
                    await page.evaluate('window.scrollTo(0, 0)')
                elif direction == 'bottom':
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                elif direction == 'down':
                    await page.evaluate(f'window.scrollBy(0, {amount})')
                elif direction == 'up':
                    await page.evaluate(f'window.scrollBy(0, -{amount})')
                elif direction == 'left':
                    await page.evaluate(f'window.scrollBy(-{amount}, 0)')
                elif direction == 'right':
                    await page.evaluate(f'window.scrollBy({amount}, 0)')
                
                # Absolute positioning
                elif 'x' in params or 'y' in params:
                    x = params.get('x', 0)
                    y = params.get('y', 0)
                    behavior = 'smooth' if smooth else 'auto'
                    await page.evaluate(f'''
                        window.scrollTo({{
                            left: {x},
                            top: {y},
                            behavior: '{behavior}'
                        }})
                    ''')
                    logger.info(f"Scrolled to position ({x}, {y})")
                    return {'success': True, 'method': 'absolute', 'x': x, 'y': y}
                
                logger.info(f"Scrolled page {direction} by {amount}px")
                return {'success': True, 'method': 'page', 'direction': direction}
            
        except Exception as e:
            logger.error(f"Scroll action failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_action_name(self) -> str:
        return "scroll"
    
    def get_required_params(self) -> List[str]:
        return []  # Direction has default value
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Scroll always valid with defaults"""
        return True