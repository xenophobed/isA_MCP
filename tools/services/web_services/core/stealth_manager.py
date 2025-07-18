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
        """Apply high level stealth techniques with advanced fingerprinting"""
        advanced_stealth_script = """
        // Remove all webdriver traces
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Mock chrome object with realistic data
        window.chrome = {
            runtime: {
                onConnect: undefined,
                onMessage: undefined
            },
            loadTimes: function() {
                return {
                    requestTime: Date.now() / 1000 - Math.random() * 2,
                    startLoadTime: Date.now() / 1000 - Math.random() * 1.5,
                    commitLoadTime: Date.now() / 1000 - Math.random() * 1,
                    finishDocumentLoadTime: Date.now() / 1000 - Math.random() * 0.5,
                    finishLoadTime: Date.now() / 1000 - Math.random() * 0.2,
                    firstPaintTime: Date.now() / 1000 - Math.random() * 0.3,
                    firstPaintAfterLoadTime: 0,
                    navigationType: 'Other',
                    wasFetchedViaSpdy: false,
                    wasNpnNegotiated: false,
                    npnNegotiatedProtocol: 'unknown',
                    wasAlternateProtocolAvailable: false,
                    connectionInfo: 'http/1.1'
                };
            },
            csi: function() {
                return {
                    startE: Date.now() - Math.random() * 1000,
                    onloadT: Date.now() - Math.random() * 800,
                    pageT: Date.now() - Math.random() * 600,
                    tran: 15
                };
            },
            app: {
                InstallState: {
                    DISABLED: 'disabled',
                    INSTALLED: 'installed',
                    NOT_INSTALLED: 'not_installed'
                },
                getDetails: function() {
                    return {
                        id: 'fake-extension-id',
                        name: 'Fake Extension',
                        version: '1.0.0'
                    };
                }
            }
        };
        
        // Override permissions with realistic responses
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = function(parameters) {
            const permissionStatus = {
                state: parameters.name === 'notifications' ? 'default' : 'granted',
                onchange: null
            };
            return Promise.resolve(permissionStatus);
        };
        
        // Mock realistic plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [];
                plugins.length = 5;
                plugins[0] = {
                    name: 'Chrome PDF Plugin',
                    filename: 'internal-pdf-viewer',
                    description: 'Portable Document Format'
                };
                plugins[1] = {
                    name: 'Chrome PDF Viewer',
                    filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                    description: ''
                };
                plugins[2] = {
                    name: 'Native Client',
                    filename: 'internal-nacl-plugin',
                    description: ''
                };
                plugins[3] = {
                    name: 'WebKit built-in PDF',
                    filename: 'WebKit built-in PDF',
                    description: 'Portable Document Format'
                };
                plugins[4] = {
                    name: 'Microsoft Edge PDF Plugin',
                    filename: 'edge-pdf-plugin',
                    description: 'Portable Document Format'
                };
                return plugins;
            }
        });
        
        // Mock realistic languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'zh-CN', 'zh']
        });
        
        // Mock realistic platform
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32'
        });
        
        // Mock realistic hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8
        });
        
        // Mock realistic device memory
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8
        });
        
        // Mock realistic connection
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                effectiveType: '4g',
                downlink: 10,
                rtt: 50
            })
        });
        
        // Mock realistic screen
        Object.defineProperty(screen, 'colorDepth', {
            get: () => 24
        });
        
        Object.defineProperty(screen, 'pixelDepth', {
            get: () => 24
        });
        
        // Mock realistic timezone
        try {
            Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
                value: function() {
                    return {
                        locale: 'en-US',
                        timeZone: 'America/New_York',
                        hour12: true,
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                    };
                }
            });
        } catch(e) {}
        
        // Mock realistic getUserMedia
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            const originalGetUserMedia = navigator.mediaDevices.getUserMedia;
            navigator.mediaDevices.getUserMedia = function(constraints) {
                return originalGetUserMedia.call(this, constraints);
            };
        }
        
        // Mock realistic battery API
        Object.defineProperty(navigator, 'getBattery', {
            get: () => () => Promise.resolve({
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 0.8 + Math.random() * 0.2
            })
        });
        
        // Mock realistic canvas fingerprinting protection
        const originalGetContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, attributes) {
            const context = originalGetContext.call(this, type, attributes);
            if (type === '2d' && context) {
                const originalGetImageData = context.getImageData;
                context.getImageData = function(x, y, width, height) {
                    const imageData = originalGetImageData.call(this, x, y, width, height);
                    // Add slight noise to canvas data
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] += Math.floor(Math.random() * 3) - 1;
                        imageData.data[i + 1] += Math.floor(Math.random() * 3) - 1;
                        imageData.data[i + 2] += Math.floor(Math.random() * 3) - 1;
                    }
                    return imageData;
                };
            }
            return context;
        };
        
        // Mock realistic WebGL fingerprinting protection
        const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 7936) { // VENDOR
                return 'Intel Inc.';
            }
            if (parameter === 7937) { // RENDERER
                return 'Intel(R) HD Graphics 630';
            }
            return originalGetParameter.call(this, parameter);
        };
        
        // Hide automation indicators
        delete window.__playwright;
        delete window.__pw_manual;
        delete window.__PW_inspect;
        delete window.__webdriver_evaluate;
        delete window.__webdriver_script_func;
        delete window.__webdriver_script_fn;
        delete window.__fxdriver_evaluate;
        delete window.__driver_unwrapped;
        delete window.__webdriver_unwrapped;
        delete window.__driver_evaluate;
        delete window.__selenium_evaluate;
        delete window.__fxdriver_unwrapped;
        delete window.__nightmare;
        delete window.nightmare;
        delete window.phantomjs;
        delete window._phantom;
        delete window.callPhantom;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        
        // Override toString for functions to hide traces
        const originalToString = Function.prototype.toString;
        Function.prototype.toString = function() {
            const result = originalToString.call(this);
            return result.replace(/\\n\\s*\\[native code\\]\\n/g, ' [native code] ');
        };
        
        // Mock realistic performance timing
        Object.defineProperty(performance, 'timing', {
            get: () => ({
                navigationStart: Date.now() - Math.random() * 1000,
                unloadEventStart: 0,
                unloadEventEnd: 0,
                redirectStart: 0,
                redirectEnd: 0,
                fetchStart: Date.now() - Math.random() * 800,
                domainLookupStart: Date.now() - Math.random() * 700,
                domainLookupEnd: Date.now() - Math.random() * 600,
                connectStart: Date.now() - Math.random() * 500,
                connectEnd: Date.now() - Math.random() * 400,
                secureConnectionStart: Date.now() - Math.random() * 350,
                requestStart: Date.now() - Math.random() * 300,
                responseStart: Date.now() - Math.random() * 200,
                responseEnd: Date.now() - Math.random() * 100,
                domLoading: Date.now() - Math.random() * 80,
                domInteractive: Date.now() - Math.random() * 60,
                domContentLoadedEventStart: Date.now() - Math.random() * 40,
                domContentLoadedEventEnd: Date.now() - Math.random() * 30,
                domComplete: Date.now() - Math.random() * 20,
                loadEventStart: Date.now() - Math.random() * 10,
                loadEventEnd: Date.now() - Math.random() * 5
            })
        });
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