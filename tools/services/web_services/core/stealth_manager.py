#!/usr/bin/env python
"""
Stealth Manager for Web Services
Advanced anti-detection techniques for web automation
"""
import random
import asyncio
from typing import Dict, Any, List
from playwright.async_api import BrowserContext, Page

from core.logging import get_logger

logger = get_logger(__name__)

class StealthManager:
    """Advanced stealth techniques for web automation"""
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
        ]
        
        self.viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 720}
        ]
        
        self.languages = [
            ["en-US", "en"],
            ["en-GB", "en"],
            ["en-CA", "en"]
        ]
        
        self.timezones = [
            "America/New_York",
            "America/Los_Angeles", 
            "America/Chicago",
            "Europe/London",
            "Europe/Berlin"
        ]
    
    async def create_stealth_context(self, browser_type: str = "chrome"):
        """Create stealth browser context - placeholder for browser integration"""
        # This is a placeholder - actual implementation would need browser instance
        logger.info(f"Stealth context configuration prepared for {browser_type}")
        return {
            "viewport": self._random_viewport(),
            "user_agent": self._random_user_agent(),
            "locale": random.choice(['en-US', 'en-GB', 'en-CA']),
            "timezone_id": random.choice(['America/New_York', 'America/Los_Angeles']),
            "extra_http_headers": self._generate_headers()
        }
    
    async def apply_stealth_context(self, context: BrowserContext, level: str = "medium"):
        """Apply stealth techniques to browser context"""
        try:
            if level == "high":
                await self._apply_high_stealth(context)
            elif level == "medium":
                await self._apply_medium_stealth(context)
            else:
                await self._apply_basic_stealth(context)
            
            logger.info(f"Applied {level} stealth configuration")
            
        except Exception as e:
            logger.error(f"Failed to apply stealth configuration: {e}")
    
    async def _apply_basic_stealth(self, context: BrowserContext):
        """Apply basic stealth techniques"""
        await context.add_init_script("""
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        """)
    
    async def _apply_medium_stealth(self, context: BrowserContext):
        """Apply medium level stealth techniques"""
        stealth_script = """
        // Remove webdriver traces
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Mock plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        
        // Mock languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        
        // Hide automation indicators
        delete window.__playwright;
        delete window.__pw_manual;
        """
        
        await context.add_init_script(stealth_script)
    
    async def _apply_high_stealth(self, context: BrowserContext):
        """Apply high level stealth techniques"""
        advanced_stealth_script = """
        // Remove all webdriver traces
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Mock chrome object
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Hide automation indicators
        delete window.__playwright;
        delete window.__pw_manual;
        delete window.__PW_inspect;
        """
        
        await context.add_init_script(advanced_stealth_script)
    
    def _random_viewport(self):
        """Get random viewport"""
        return random.choice(self.viewports)
    
    def _random_user_agent(self):
        """Get random user agent"""
        return random.choice(self.user_agents)
    
    def _generate_headers(self):
        """Generate stealth headers"""
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get stealth manager status"""
        return {
            "available_user_agents": len(self.user_agents),
            "available_viewports": len(self.viewports),
            "available_languages": len(self.languages),
            "available_timezones": len(self.timezones),
            "stealth_levels": ["basic", "medium", "high"]
        }