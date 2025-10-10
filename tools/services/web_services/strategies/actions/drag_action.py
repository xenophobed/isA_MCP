#!/usr/bin/env python
"""
Drag and Drop Action Strategy - Handle drag-drop interactions
"""
from typing import Dict, Any, List
from playwright.async_api import Page
from ..base import ActionStrategy
from core.logging import get_logger

logger = get_logger(__name__)


class DragActionStrategy(ActionStrategy):
    """Handle drag and drop actions"""

    async def execute(self, page: Page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute drag and drop action

        Params:
        - source: Source element (selector or coordinates)
        - target: Target element (selector or coordinates)
        - source_selector: CSS selector for source element
        - target_selector: CSS selector for target element
        - source_x, source_y: Coordinates of source element
        - target_x, target_y: Coordinates of target element
        - offset_x, offset_y: Offset for drop position (optional)
        - smooth: Use smooth dragging with intermediate steps (default: False)
        - steps: Number of steps for smooth drag (default: 10)

        Example:
        - {"source_selector": "#item1", "target_selector": "#dropzone"}
        - {"source_x": 100, "source_y": 200, "target_x": 400, "target_y": 500}
        - {"source_selector": ".draggable", "target_x": 500, "target_y": 300}
        """
        try:
            smooth = params.get('smooth', False)
            steps = params.get('steps', 10)
            offset_x = params.get('offset_x', 0)
            offset_y = params.get('offset_y', 0)

            # Determine source
            source_selector = params.get('source_selector') or params.get('source')
            source_x = params.get('source_x')
            source_y = params.get('source_y')

            # Determine target
            target_selector = params.get('target_selector') or params.get('target')
            target_x = params.get('target_x')
            target_y = params.get('target_y')

            # Method 1: Both selectors (preferred)
            if source_selector and target_selector:
                source_element = page.locator(source_selector)
                target_element = page.locator(target_selector)

                # Use Playwright's drag_to method
                await source_element.drag_to(
                    target_element,
                    source_position={'x': offset_x, 'y': offset_y} if offset_x or offset_y else None,
                    timeout=10000
                )

                logger.info(f"Dragged {source_selector} to {target_selector}")

                return {
                    'success': True,
                    'action': 'drag',
                    'source': source_selector,
                    'target': target_selector,
                    'method': 'selector_to_selector'
                }

            # Method 2: Selector to coordinates
            elif source_selector and target_x is not None and target_y is not None:
                source_element = page.locator(source_selector)

                # Get source position
                box = await source_element.bounding_box()
                if not box:
                    return {
                        'success': False,
                        'error': 'Source element not visible'
                    }

                start_x = box['x'] + box['width'] / 2
                start_y = box['y'] + box['height'] / 2

                # Perform drag
                await self._drag_by_coordinates(
                    page,
                    start_x, start_y,
                    target_x + offset_x, target_y + offset_y,
                    smooth, steps
                )

                logger.info(f"Dragged {source_selector} to ({target_x}, {target_y})")

                return {
                    'success': True,
                    'action': 'drag',
                    'source': source_selector,
                    'target': f'({target_x}, {target_y})',
                    'method': 'selector_to_coordinates'
                }

            # Method 3: Coordinates to selector
            elif source_x is not None and source_y is not None and target_selector:
                target_element = page.locator(target_selector)

                # Get target position
                box = await target_element.bounding_box()
                if not box:
                    return {
                        'success': False,
                        'error': 'Target element not visible'
                    }

                end_x = box['x'] + box['width'] / 2 + offset_x
                end_y = box['y'] + box['height'] / 2 + offset_y

                # Perform drag
                await self._drag_by_coordinates(
                    page,
                    source_x, source_y,
                    end_x, end_y,
                    smooth, steps
                )

                logger.info(f"Dragged ({source_x}, {source_y}) to {target_selector}")

                return {
                    'success': True,
                    'action': 'drag',
                    'source': f'({source_x}, {source_y})',
                    'target': target_selector,
                    'method': 'coordinates_to_selector'
                }

            # Method 4: Pure coordinates
            elif all(v is not None for v in [source_x, source_y, target_x, target_y]):
                await self._drag_by_coordinates(
                    page,
                    source_x, source_y,
                    target_x + offset_x, target_y + offset_y,
                    smooth, steps
                )

                logger.info(f"Dragged ({source_x}, {source_y}) to ({target_x}, {target_y})")

                return {
                    'success': True,
                    'action': 'drag',
                    'source': f'({source_x}, {source_y})',
                    'target': f'({target_x}, {target_y})',
                    'method': 'coordinates_to_coordinates'
                }

            else:
                return {
                    'success': False,
                    'error': 'Invalid drag parameters - need source and target'
                }

        except Exception as e:
            logger.error(f"Drag action failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _drag_by_coordinates(
        self,
        page: Page,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        smooth: bool = False,
        steps: int = 10
    ):
        """Perform drag operation using coordinates"""

        # Move to start position
        await page.mouse.move(start_x, start_y)
        await page.wait_for_timeout(100)

        # Press mouse button
        await page.mouse.down()
        await page.wait_for_timeout(100)

        if smooth and steps > 1:
            # Smooth drag with intermediate steps
            dx = (end_x - start_x) / steps
            dy = (end_y - start_y) / steps

            for i in range(1, steps + 1):
                x = start_x + dx * i
                y = start_y + dy * i
                await page.mouse.move(x, y)
                await page.wait_for_timeout(20)
        else:
            # Direct drag
            await page.mouse.move(end_x, end_y)
            await page.wait_for_timeout(100)

        # Release mouse button
        await page.mouse.up()
        await page.wait_for_timeout(100)

    def get_action_name(self) -> str:
        return "drag"

    def get_required_params(self) -> List[str]:
        return []  # Flexible params based on drag method

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate drag parameters"""
        # Check if we have valid source and target combinations
        has_source_selector = 'source_selector' in params or 'source' in params
        has_source_coords = 'source_x' in params and 'source_y' in params
        has_target_selector = 'target_selector' in params or 'target' in params
        has_target_coords = 'target_x' in params and 'target_y' in params

        has_source = has_source_selector or has_source_coords
        has_target = has_target_selector or has_target_coords

        return has_source and has_target