#!/usr/bin/env python
"""
Browser Manager for Web Services
Manages multiple browser instances with different profiles and configurations
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from core.logging import get_logger

logger = get_logger(__name__)

class BrowserManager:
    """Manages browser instances and contexts with different profiles"""
    
    def __init__(self):
        self.playwright = None
        self.browsers: Dict[str, Browser] = {}
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}
        self.config = self._load_config()
        self.initialized = False
    
    def _load_config(self) -> Dict[str, Any]:
        """Load browser configuration"""
        config_path = Path(__file__).parent.parent / "configs" / "profile.json"
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load browser config: {e}")
        
        # Default configuration
        return {
            "profiles": {
                "stealth": {
                    "headless": True,
                    "args": [
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-extensions",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--disable-component-extensions-with-background-pages",
                        "--disable-default-apps",
                        "--disable-features=TranslateUI",
                        "--disable-ipc-flooding-protection",
                        "--disable-hang-monitor",
                        "--disable-prompt-on-repost",
                        "--disable-sync",
                        "--disable-domain-reliability",
                        "--disable-background-networking",
                        "--disable-component-update",
                        "--disable-client-side-phishing-detection",
                        "--disable-datasaver-prompt",
                        "--disable-desktop-notifications",
                        "--disable-device-discovery-notifications",
                        "--disable-infobars",
                        "--disable-notifications",
                        "--disable-password-generation",
                        "--disable-permissions-api",
                        "--disable-plugins-discovery",
                        "--disable-print-preview",
                        "--disable-speech-api",
                        "--disable-tab-for-desktop-share",
                        "--disable-translate",
                        "--disable-voice-input",
                        "--disable-wake-on-wifi",
                        "--disable-web-security",
                        "--allow-running-insecure-content",
                        "--ignore-ssl-errors",
                        "--ignore-certificate-errors",
                        "--ignore-certificate-errors-spki-list",
                        "--ignore-urlfetcher-cert-requests",
                        "--disable-popup-blocking",
                        "--disable-plugins",
                        "--disable-images",
                        "--disable-javascript",
                        "--enable-javascript",
                        "--disable-plugins-discovery",
                        "--disable-bundled-ppapi-flash",
                        "--disable-webgl",
                        "--disable-threaded-animation",
                        "--disable-threaded-scrolling",
                        "--disable-in-process-stack-traces",
                        "--disable-histogram-customizer",
                        "--disable-gl-extensions",
                        "--disable-composited-antialiasing",
                        "--disable-canvas-aa",
                        "--disable-3d-apis",
                        "--disable-accelerated-2d-canvas",
                        "--disable-accelerated-jpeg-decoding",
                        "--disable-accelerated-mjpeg-decode",
                        "--disable-app-list-dismiss-on-blur",
                        "--disable-accelerated-video-decode",
                        "--num-raster-threads=4",
                        "--enable-viewport",
                        "--enable-aggressive-domstorage-flushing",
                        "--enable-logging",
                        "--log-level=0",
                        "--v=99",
                        "--single-process",
                        "--no-zygote",
                        "--no-first-run",
                        "--enable-automation",
                        "--disable-automation",
                        "--test-type"
                    ],
                    "viewport": {"width": 1920, "height": 1080},
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "extra_http_headers": {
                        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                        "Upgrade-Insecure-Requests": "1",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                },
                "automation": {
                    "headless": False,
                    "slow_mo": 100,
                    "args": ["--no-sandbox"],
                    "viewport": {"width": 1280, "height": 720},
                    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                "monitoring": {
                    "headless": True,
                    "timeout": 60000,
                    "args": ["--no-sandbox", "--disable-dev-shm-usage"],
                    "viewport": {"width": 1920, "height": 1080}
                }
            },
            "timeouts": {
                "default": 30000,
                "navigation": 30000,
                "element": 10000
            }
        }
    
    async def initialize(self):
        """Initialize Playwright and browser instances"""
        if self.initialized:
            return
        
        try:
            self.playwright = await async_playwright().start()
            logger.info("Playwright initialized")
            self.initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            raise
    
    async def get_browser(self, profile_name: str = "stealth") -> Browser:
        """Get or create browser instance for specified profile"""
        if not self.initialized:
            await self.initialize()
        
        if profile_name not in self.browsers:
            profile_config = self.config["profiles"].get(profile_name, self.config["profiles"]["stealth"])
            
            try:
                browser = await self.playwright.chromium.launch(
                    headless=profile_config.get("headless", True),
                    args=profile_config.get("args", []),
                    slow_mo=profile_config.get("slow_mo", 0),
                    timeout=profile_config.get("timeout", 30000)
                )
                
                self.browsers[profile_name] = browser
                logger.info(f"Browser created for profile: {profile_name}")
                
            except Exception as e:
                logger.error(f"Failed to create browser for profile {profile_name}: {e}")
                raise
        
        return self.browsers[profile_name]
    
    async def get_context(self, profile_name: str = "stealth", context_id: str = None) -> BrowserContext:
        """Get or create browser context for specified profile"""
        context_key = f"{profile_name}_{context_id}" if context_id else profile_name
        
        if context_key not in self.contexts:
            browser = await self.get_browser(profile_name)
            profile_config = self.config["profiles"].get(profile_name, self.config["profiles"]["stealth"])
            
            try:
                context_options = {
                    "viewport": profile_config.get("viewport", {"width": 1920, "height": 1080}),
                    "user_agent": profile_config.get("user_agent"),
                    "java_script_enabled": profile_config.get("javascript_enabled", True),
                    "ignore_https_errors": profile_config.get("ignore_https_errors", True),
                    "extra_http_headers": profile_config.get("extra_http_headers", {})
                }
                
                # Remove None values
                context_options = {k: v for k, v in context_options.items() if v is not None}
                
                context = await browser.new_context(**context_options)
                
                # Add stealth scripts for stealth profile
                if profile_name == "stealth":
                    await self._apply_stealth_scripts(context)
                
                self.contexts[context_key] = context
                logger.info(f"Context created: {context_key}")
                
            except Exception as e:
                logger.error(f"Failed to create context {context_key}: {e}")
                raise
        
        return self.contexts[context_key]
    
    async def get_page(self, profile_name: str = "stealth", context_id: str = None, page_id: str = None) -> Page:
        """Get or create page for specified profile and context"""
        page_key = f"{profile_name}_{context_id}_{page_id}" if all([context_id, page_id]) else f"{profile_name}_default"
        
        if page_key not in self.pages:
            context = await self.get_context(profile_name, context_id)
            
            try:
                page = await context.new_page()
                
                # Set timeouts
                timeouts = self.config.get("timeouts", {})
                page.set_default_timeout(timeouts.get("default", 30000))
                page.set_default_navigation_timeout(timeouts.get("navigation", 30000))
                
                self.pages[page_key] = page
                logger.info(f"Page created: {page_key}")
                
            except Exception as e:
                logger.error(f"Failed to create page {page_key}: {e}")
                raise
        
        return self.pages[page_key]
    
    async def _apply_stealth_scripts(self, context: BrowserContext):
        """Apply stealth scripts to context"""
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
        
        await context.add_init_script(stealth_script)
    
    async def close_page(self, page_key: str):
        """Close specific page"""
        if page_key in self.pages:
            try:
                await self.pages[page_key].close()
                del self.pages[page_key]
                logger.info(f"Page closed: {page_key}")
            except Exception as e:
                logger.warning(f"Failed to close page {page_key}: {e}")
    
    async def close_context(self, context_key: str):
        """Close specific context and all its pages"""
        if context_key in self.contexts:
            try:
                # Close all pages in this context
                pages_to_close = [k for k in self.pages.keys() if k.startswith(context_key)]
                for page_key in pages_to_close:
                    await self.close_page(page_key)
                
                # Close context
                await self.contexts[context_key].close()
                del self.contexts[context_key]
                logger.info(f"Context closed: {context_key}")
            except Exception as e:
                logger.warning(f"Failed to close context {context_key}: {e}")
    
    async def close_browser(self, profile_name: str):
        """Close specific browser and all its contexts"""
        if profile_name in self.browsers:
            try:
                # Close all contexts for this browser
                contexts_to_close = [k for k in self.contexts.keys() if k.startswith(profile_name)]
                for context_key in contexts_to_close:
                    await self.close_context(context_key)
                
                # Close browser
                await self.browsers[profile_name].close()
                del self.browsers[profile_name]
                logger.info(f"Browser closed: {profile_name}")
            except Exception as e:
                logger.warning(f"Failed to close browser {profile_name}: {e}")
    
    async def cleanup_all(self):
        """Close all browsers, contexts, and pages"""
        try:
            # Close all pages
            for page_key in list(self.pages.keys()):
                await self.close_page(page_key)
            
            # Close all contexts
            for context_key in list(self.contexts.keys()):
                await self.close_context(context_key)
            
            # Close all browsers
            for profile_name in list(self.browsers.keys()):
                await self.close_browser(profile_name)
            
            # Stop playwright
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            self.initialized = False
            logger.info("Browser manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current status of browser manager"""
        return {
            "initialized": self.initialized,
            "browsers": list(self.browsers.keys()),
            "contexts": list(self.contexts.keys()),
            "pages": list(self.pages.keys()),
            "total_browsers": len(self.browsers),
            "total_contexts": len(self.contexts),
            "total_pages": len(self.pages)
        }