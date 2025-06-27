#!/usr/bin/env python
"""
Human Behavior Simulation for Web Automation
Provides human-like interactions to avoid detection during web automation
"""
import asyncio
import random
import math
from typing import Optional

from playwright.async_api import Page

from core.logging import get_logger

logger = get_logger(__name__)

class HumanBehavior:
    """Simulates human-like behavior for web automation"""
    
    def __init__(self):
        # Human typing patterns
        self.typing_speed_wpm = random.randint(35, 85)  # Words per minute
        self.typing_errors_rate = 0.02  # 2% error rate
        
        # Mouse movement patterns
        self.mouse_movement_speed = random.uniform(0.8, 2.0)
        
        # Random delay ranges (in milliseconds)
        self.short_delay_range = (100, 500)
        self.medium_delay_range = (500, 1500)
        self.long_delay_range = (1000, 3000)
    
    async def random_delay(self, min_ms: Optional[int] = None, max_ms: Optional[int] = None):
        """Add random delay to simulate human thinking/reaction time"""
        if min_ms is None or max_ms is None:
            min_ms, max_ms = self.short_delay_range
        
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)
    
    async def human_type(self, page: Page, element_ref, text: str, clear_first: bool = True):
        """Type text with human-like behavior including errors and corrections
        
        Args:
            element_ref: Either a CSS selector string or coordinate dict with x,y
        """
        try:
            # Handle both selector and coordinate-based element references
            if isinstance(element_ref, dict) and element_ref.get('type') == 'coordinate':
                # Coordinate-based approach
                x, y = element_ref['x'], element_ref['y']
                logger.info(f"🎯 Typing at coordinates ({x}, {y}) - {element_ref.get('description', 'field')}")
                
                # Click at coordinates to focus
                await page.mouse.click(x, y)
                await self.random_delay(200, 800)
                
                # Clear existing text if requested (using keyboard shortcuts)
                if clear_first:
                    await page.keyboard.press('Control+a')  # Select all
                    await self.random_delay(100, 300)
                    await page.keyboard.press('Delete')  # Delete selected text
                    await self.random_delay(100, 300)
                
                # Use keyboard.type for coordinate-based typing
                typing_target = 'coordinates'
            else:
                # Traditional selector-based approach
                selector = element_ref if isinstance(element_ref, str) else str(element_ref)
                logger.info(f"🎯 Typing with selector: {selector}")
                
                # Focus on the element
                await page.focus(selector)
                await self.random_delay(200, 800)
                
                # Clear existing text if requested
                if clear_first:
                    await page.fill(selector, "")
                    await self.random_delay(100, 300)
                
                typing_target = selector
            
            # Calculate typing speed (characters per minute to milliseconds per character)
            chars_per_minute = self.typing_speed_wpm * 5  # Average 5 chars per word
            ms_per_char = 60000 / chars_per_minute
            
            typed_text = ""
            for i, char in enumerate(text):
                # Simulate typing errors
                if random.random() < self.typing_errors_rate and char.isalpha():
                    # Type wrong character
                    wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                    
                    if typing_target == 'coordinates':
                        # Use keyboard for coordinate-based typing
                        await page.keyboard.type(wrong_char, delay=ms_per_char * random.uniform(0.8, 1.2))
                    else:
                        await page.type(typing_target, wrong_char, delay=ms_per_char * random.uniform(0.8, 1.2))
                    typed_text += wrong_char
                    
                    # Pause to "notice" the error
                    await self.random_delay(300, 1000)
                    
                    # Backspace to correct
                    if typing_target == 'coordinates':
                        await page.keyboard.press('Backspace')
                    else:
                        await page.press(typing_target, 'Backspace')
                    typed_text = typed_text[:-1]
                    await self.random_delay(100, 300)
                
                # Type the correct character
                char_delay = ms_per_char * random.uniform(0.5, 1.8)
                
                if typing_target == 'coordinates':
                    # Use keyboard for coordinate-based typing
                    await page.keyboard.type(char, delay=char_delay)
                else:
                    await page.type(typing_target, char, delay=char_delay)
                typed_text += char
                
                # Occasional longer pauses (thinking)
                if random.random() < 0.1:  # 10% chance
                    await self.random_delay(500, 2000)
            
            # Final pause before proceeding
            await self.random_delay(300, 1000)
            
        except Exception as e:
            logger.error(f"Failed to type text humanly: {e}")
            # Fallback to regular typing
            if isinstance(element_ref, dict) and element_ref.get('type') == 'coordinate':
                # For coordinates, just use keyboard typing
                await page.keyboard.type(text)
            else:
                selector = element_ref if isinstance(element_ref, str) else str(element_ref)
                await page.fill(selector, text)
    
    async def human_click(self, page: Page, element_ref, click_count: int = 1):
        """Click with human-like mouse movement and timing
        
        Args:
            element_ref: Either a CSS selector string or coordinate dict with x,y
        """
        try:
            # Handle both selector and coordinate-based element references
            if isinstance(element_ref, dict) and element_ref.get('type') == 'coordinate':
                # Direct coordinate-based clicking
                click_x, click_y = element_ref['x'], element_ref['y']
                logger.info(f"🎯 Clicking at coordinates ({click_x}, {click_y}) - {element_ref.get('description', 'element')}")
                
                # Add small random offset for more human-like behavior
                click_x += random.uniform(-3, 3)
                click_y += random.uniform(-3, 3)
                
            else:
                # Traditional selector-based approach
                selector = element_ref if isinstance(element_ref, str) else str(element_ref)
                logger.info(f"🎯 Clicking with selector: {selector}")
                
                # Get element bounding box for realistic mouse movement
                element = await page.query_selector(selector)
                if not element:
                    raise Exception(f"Element not found: {selector}")
                
                bbox = await element.bounding_box()
                if not bbox:
                    # Element might not be visible, try scrolling
                    await element.scroll_into_view_if_needed()
                    bbox = await element.bounding_box()
                
                if bbox:
                    # Calculate random click position within element
                    click_x = bbox['x'] + random.uniform(0.2, 0.8) * bbox['width']
                    click_y = bbox['y'] + random.uniform(0.2, 0.8) * bbox['height']
                else:
                    raise Exception(f"Could not get bounding box for element: {selector}")
            
            # Move mouse to position with human-like movement
            await self.human_mouse_move(page, click_x, click_y)
            
            # Small delay before clicking
            await self.random_delay(100, 500)
            
            # Perform the click(s)
            for i in range(click_count):
                await page.mouse.click(click_x, click_y)
                if i < click_count - 1:  # Don't delay after the last click
                    await self.random_delay(50, 200)
            
            # Post-click delay
            await self.random_delay(200, 800)
            
        except Exception as e:
            logger.error(f"Failed to click humanly: {e}")
            # Fallback to regular click
            if isinstance(element_ref, dict) and element_ref.get('type') == 'coordinate':
                # For coordinates, just click at the position
                await page.mouse.click(element_ref['x'], element_ref['y'])
            else:
                selector = element_ref if isinstance(element_ref, str) else str(element_ref)
                await page.click(selector)
    
    async def human_mouse_move(self, page: Page, target_x: float, target_y: float):
        """Move mouse with human-like curved trajectory"""
        try:
            # Get current mouse position (approximate)
            current_pos = await page.evaluate("() => ({ x: window.innerWidth / 2, y: window.innerHeight / 2 })")
            start_x, start_y = current_pos['x'], current_pos['y']
            
            # Calculate distance and movement parameters
            distance = math.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2)
            steps = max(5, int(distance / 20))  # More steps for longer distances
            
            # Generate curved path using bezier-like curve
            control_x = (start_x + target_x) / 2 + random.uniform(-50, 50)
            control_y = (start_y + target_y) / 2 + random.uniform(-50, 50)
            
            for i in range(steps + 1):
                t = i / steps
                
                # Quadratic bezier curve
                x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * control_x + t ** 2 * target_x
                y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * control_y + t ** 2 * target_y
                
                # Add small random variations
                x += random.uniform(-2, 2)
                y += random.uniform(-2, 2)
                
                await page.mouse.move(x, y)
                
                # Variable speed - slower at start and end, faster in middle
                speed_factor = 1 - abs(0.5 - t) * 2  # 0 at ends, 1 in middle
                delay = (20 + random.uniform(-5, 5)) * (2 - speed_factor) / self.mouse_movement_speed
                await asyncio.sleep(delay / 1000)
                
        except Exception as e:
            logger.warning(f"Failed to move mouse humanly: {e}")
    
    async def human_scroll(self, page: Page, direction: str = "down", amount: int = 3):
        """Scroll page with human-like behavior"""
        try:
            scroll_amounts = {
                "down": [0, -120],
                "up": [0, 120],
                "left": [-120, 0],
                "right": [120, 0]
            }
            
            if direction not in scroll_amounts:
                direction = "down"
            
            delta_x, delta_y = scroll_amounts[direction]
            
            for _ in range(amount):
                # Add slight variation to scroll amount
                varied_delta_x = delta_x + random.randint(-20, 20)
                varied_delta_y = delta_y + random.randint(-20, 20)
                
                await page.mouse.wheel(varied_delta_x, varied_delta_y)
                
                # Human-like pause between scrolls
                await self.random_delay(100, 400)
            
            # Pause after scrolling
            await self.random_delay(500, 1500)
            
        except Exception as e:
            logger.error(f"Failed to scroll humanly: {e}")
    
    async def human_navigation_pause(self, page: Page):
        """Add realistic pause for page navigation/loading"""
        # Wait for initial load
        await page.wait_for_load_state('domcontentloaded')
        
        # Human reading/processing time
        await self.random_delay(1000, 3000)
        
        # Wait for any dynamic content
        await page.wait_for_load_state('networkidle', timeout=10000)
        
        # Additional processing time
        await self.random_delay(500, 1500)
    
    async def simulate_reading(self, page: Page, reading_time_factor: float = 1.0):
        """Simulate human reading behavior with scrolling and pauses"""
        try:
            # Get page height to determine reading time
            page_height = await page.evaluate("document.body.scrollHeight")
            viewport_height = await page.evaluate("window.innerHeight")
            
            if page_height <= viewport_height:
                # Short page, just pause to read
                reading_time = random.randint(2000, 5000) * reading_time_factor
                await asyncio.sleep(reading_time / 1000)
                return
            
            # Calculate number of scrolls needed
            scrolls_needed = math.ceil(page_height / viewport_height)
            
            for i in range(scrolls_needed):
                # Read current section
                reading_time = random.randint(1500, 4000) * reading_time_factor
                await asyncio.sleep(reading_time / 1000)
                
                # Scroll to next section (unless it's the last one)
                if i < scrolls_needed - 1:
                    await self.human_scroll(page, "down", 1)
                    
                    # Brief pause after scrolling
                    await self.random_delay(300, 800)
            
        except Exception as e:
            logger.warning(f"Failed to simulate reading: {e}")
            # Fallback to simple delay
            await self.random_delay(3000, 8000)
    
    async def apply_human_navigation(self, page: Page):
        """Apply human-like behavior when navigating to a new page"""
        try:
            # Set random viewport size (within reasonable bounds)
            width = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            await page.set_viewport_size({"width": width, "height": height})
            
            # Random user agent selection would go here if needed
            
            # Set random geolocation (if permissions allow)
            try:
                lat = random.uniform(25.0, 49.0)  # US bounds
                lng = random.uniform(-125.0, -66.0)
                await page.context.set_geolocation({"latitude": lat, "longitude": lng})
            except:
                pass  # Ignore if geolocation setting fails
            
        except Exception as e:
            logger.warning(f"Failed to apply human navigation settings: {e}")
    
    async def random_mouse_movement(self, page: Page, movements: int = 3):
        """Perform random mouse movements to simulate human presence"""
        try:
            viewport = await page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
            
            for _ in range(movements):
                # Random position within viewport
                x = random.randint(50, viewport['width'] - 50)
                y = random.randint(50, viewport['height'] - 50)
                
                await self.human_mouse_move(page, x, y)
                await self.random_delay(500, 2000)
                
        except Exception as e:
            logger.warning(f"Failed to perform random mouse movements: {e}")
    
    def get_human_timing_config(self) -> dict:
        """Get current human behavior timing configuration"""
        return {
            "typing_speed_wpm": self.typing_speed_wpm,
            "typing_errors_rate": self.typing_errors_rate,
            "mouse_movement_speed": self.mouse_movement_speed,
            "delay_ranges": {
                "short": self.short_delay_range,
                "medium": self.medium_delay_range,
                "long": self.long_delay_range
            }
        }
    
    def update_human_profile(self, 
                           typing_speed_wpm: Optional[int] = None,
                           typing_errors_rate: Optional[float] = None,
                           mouse_movement_speed: Optional[float] = None):
        """Update human behavior profile"""
        if typing_speed_wpm:
            self.typing_speed_wpm = max(20, min(120, typing_speed_wpm))
        if typing_errors_rate is not None:
            self.typing_errors_rate = max(0.0, min(0.1, typing_errors_rate))
        if mouse_movement_speed:
            self.mouse_movement_speed = max(0.3, min(3.0, mouse_movement_speed))
        
        logger.info(f"Updated human behavior profile: WPM={self.typing_speed_wpm}, "
                   f"Errors={self.typing_errors_rate}, Speed={self.mouse_movement_speed}")