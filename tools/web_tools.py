#!/usr/bin/env python
"""
Web Tools for MCP Server
Advanced web automation, crawling, search, and monitoring with Playwright and vision-guided automation
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.monitoring import monitor_manager

from tools.services.web_services.core.browser_manager import BrowserManager
from tools.services.web_services.core.session_manager import SessionManager
from tools.services.web_services.core.stealth_manager import StealthManager
from tools.services.web_services.core.vision_analyzer import VisionAnalyzer
from tools.services.web_services.utils.rate_limiter import RateLimiter
from tools.services.web_services.utils.proxy_manager import ProxyManager
from tools.services.web_services.utils.human_behavior import HumanBehavior

logger = get_logger(__name__)

# Global service instances
_browser_manager: Optional[BrowserManager] = None
_session_manager: Optional[SessionManager] = None
_stealth_manager: Optional[StealthManager] = None
_vision_analyzer: Optional[VisionAnalyzer] = None
_rate_limiter: Optional[RateLimiter] = None
_proxy_manager: Optional[ProxyManager] = None
_human_behavior: Optional[HumanBehavior] = None

async def _initialize_services():
    """Initialize all web service instances"""
    global _browser_manager, _session_manager, _stealth_manager, _vision_analyzer
    global _rate_limiter, _proxy_manager, _human_behavior
    
    try:
        if _browser_manager is None:
            print("🔧 Initializing web services...")
            _browser_manager = BrowserManager()
            print("✅ BrowserManager created")
            
            _session_manager = SessionManager()
            print("✅ SessionManager created")
            
            _stealth_manager = StealthManager()
            print("✅ StealthManager created")
            
            _vision_analyzer = VisionAnalyzer()
            print("✅ VisionAnalyzer created")
            
            _rate_limiter = RateLimiter()
            print("✅ RateLimiter created")
            
            _proxy_manager = ProxyManager()
            print("✅ ProxyManager created")
            
            _human_behavior = HumanBehavior()
            print("✅ HumanBehavior created")
            
            print("🔧 Initializing browser manager...")
            await _browser_manager.initialize()
            print("✅ Web services fully initialized")
            
            logger.info("Web services initialized")
        else:
            print("ℹ️ Web services already initialized")
            
    except Exception as e:
        print(f"❌ Failed to initialize web services: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise

def register_web_tools(mcp):
    """Register all web tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    # WEB AUTOMATION TOOLS
    @mcp.tool()
    # @security_manager.security_check  # Disabled for testing
    # @security_manager.require_authorization(SecurityLevel.HIGH)  # Disabled for testing
    async def automate_web_login(
        url: str,
        credentials: str,  # JSON string with username/password
        login_selectors: str = "",  # Optional custom selectors
        user_id: str = "default"
    ) -> str:
        """Automate login process using vision-guided automation
        
        This tool performs automated login on websites using either provided
        selectors or vision-guided element detection for maximum compatibility.
        
        Keywords: automation, login, authenticate, credentials, vision, guided
        Category: web-automation
        """
        await _initialize_services()
        
        # Ensure services are initialized
        if _human_behavior is None or _vision_analyzer is None or _session_manager is None:
            raise Exception("Web services failed to initialize properly")
        
        try:
            # Parse credentials - handle multiple formats
            if isinstance(credentials, dict):
                creds = credentials
            else:
                try:
                    # Try JSON first
                    creds = json.loads(credentials)
                except json.JSONDecodeError:
                    # Try key=value format like "username=x&password=y" or "username=x password=y"
                    creds = {}
                    if '=' in credentials:
                        # Handle both & and space separators
                        if '&' in credentials:
                            parts = credentials.split('&')
                        elif ' and ' in credentials:
                            parts = credentials.split(' and ')
                        else:
                            parts = credentials.split()
                        
                        for part in parts:
                            if '=' in part:
                                key, value = part.split('=', 1)
                                creds[key.strip()] = value.strip()
                    
                    # If still no creds found, try natural language parsing
                    if not creds:
                        import re
                        # Look for patterns like "username=tomsmith and password=SuperSecretPassword"
                        username_match = re.search(r'username[=:\s]+([^\s,&]+)', credentials, re.IGNORECASE)
                        password_match = re.search(r'password[=:\s]+([^\s,&!]+[!]?)', credentials, re.IGNORECASE)
                        
                        if username_match and password_match:
                            creds = {
                                'username': username_match.group(1),
                                'password': password_match.group(1)
                            }
                    
                    if not creds:
                        raise ValueError("Could not parse credentials from input format")
            
            if not isinstance(creds, dict) or 'username' not in creds or 'password' not in creds:
                raise ValueError("Credentials must contain username and password")
            
            # Get browser session with stealth configuration
            session_id = f"login_{user_id}_{hash(url)}"
            print(f"🔍 DEBUG: Session manager status: {_session_manager is not None}")
            print(f"🔍 DEBUG: Vision analyzer status: {_vision_analyzer is not None}")
            print(f"🔍 DEBUG: Human behavior status: {_human_behavior is not None}")
            
            if _session_manager is None:
                raise Exception("Session manager not initialized. Web services may not be properly set up.")
            
            page = await _session_manager.get_or_create_session(session_id, "stealth")
            
            # Apply human-like behavior
            await _human_behavior.apply_human_navigation(page)
            
            # Navigate to login page
            await page.goto(url, wait_until='networkidle')
            
            # Use vision-guided login if no selectors provided
            if not login_selectors:
                login_elements = await _vision_analyzer.identify_login_form(page)
            else:
                login_elements = json.loads(login_selectors)
            
            # Perform login with human-like behavior
            username_selector = login_elements.get('username', '')
            password_selector = login_elements.get('password', '')
            submit_selector = login_elements.get('submit', '')
            
            await _human_behavior.human_type(page, username_selector, creds.get('username', ''))
            await _human_behavior.random_delay(500, 1500)
            await _human_behavior.human_type(page, password_selector, creds.get('password', ''))
            await _human_behavior.random_delay(500, 1500)
            await _human_behavior.human_click(page, submit_selector)
            
            # Wait for login completion
            await page.wait_for_load_state('networkidle')
            
            # Verify login success
            current_url = page.url
            title = await page.title()
            
            result = {
                "status": "success",
                "action": "automate_web_login",
                "data": {
                    "original_url": url,
                    "current_url": current_url,
                    "title": title,
                    "session_id": session_id,
                    "login_successful": current_url != url  # Basic success detection
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Web login automation completed for {url}")
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "automate_web_login", 
                "error": f"Login automation failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Login automation failed for {url}: {e}")
            return json.dumps(result)
    
    @mcp.tool()
    # @security_manager.security_check  # Disabled for testing
    # @security_manager.require_authorization(SecurityLevel.MEDIUM)  # Disabled for testing
    async def automate_web_search(
        url: str,
        search_query: str,
        search_config: str = "{}",  # JSON config for search
        user_id: str = "default"
    ) -> str:
        """Automate web search using vision-guided element detection
        
        This tool performs automated searches on websites by detecting
        search forms and input fields using vision-guided automation.
        
        Keywords: automation, search, query, vision, guided, forms
        Category: web-automation
        """
        await _initialize_services()
        
        # Ensure services are initialized
        if _human_behavior is None or _vision_analyzer is None or _session_manager is None:
            raise Exception("Web services failed to initialize properly")
        
        try:
            config = json.loads(search_config) if search_config else {}
            
            # Get browser session
            session_id = f"search_{user_id}_{hash(url)}"
            page = await _session_manager.get_or_create_session(session_id, "automation")
            
            # Navigate to search page
            await page.goto(url, wait_until='networkidle')
            
            # Use vision to identify search elements
            search_elements = await _vision_analyzer.identify_search_form(page)
            
            # Perform search with human-like behavior
            await _human_behavior.human_type(page, search_elements['input'], search_query)
            await _human_behavior.random_delay(500, 1000)
            await _human_behavior.human_click(page, search_elements['submit'])
            
            # Wait for results
            await page.wait_for_load_state('networkidle')
            
            # Extract search results
            results = await _vision_analyzer.extract_search_results(page)
            
            result = {
                "status": "success",
                "action": "automate_web_search",
                "data": {
                    "search_url": url,
                    "query": search_query,
                    "results_url": page.url,
                    "results": results,
                    "total_results": len(results)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Web search automation completed: {len(results)} results for '{search_query}'")
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "automate_web_search",
                "error": f"Search automation failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Search automation failed: {e}")
            return json.dumps(result)
    
    @mcp.tool()
    # @security_manager.security_check  # Disabled for testing
    # @security_manager.require_authorization(SecurityLevel.HIGH)  # Disabled for testing
    async def automate_file_download(
        url: str,
        download_config: str,  # JSON config for download
        user_id: str = "default"
    ) -> str:
        """Automate file downloads from websites
        
        This tool automates the download process from websites by detecting
        download links and handling various download scenarios.
        
        Keywords: automation, download, files, links, content
        Category: web-automation
        """
        await _initialize_services()
        
        # Ensure services are initialized
        if _session_manager is None or _vision_analyzer is None:
            raise Exception("Web services failed to initialize properly")
        
        try:
            config = json.loads(download_config)
            
            # Get browser session with download handling
            session_id = f"download_{user_id}_{hash(url)}"
            page = await _session_manager.get_or_create_session(session_id, "automation")
            
            # Set up download handling
            downloads = []
            page.on("download", lambda download: downloads.append(download))
            
            # Navigate to page
            await page.goto(url, wait_until='networkidle')
            
            # Find and click download links based on config
            if 'link_text' in config:
                await page.click(f"text={config['link_text']}")
            elif 'selector' in config:
                await page.click(config['selector'])
            else:
                # Use vision to identify download links
                download_links = await _vision_analyzer.identify_download_links(page)
                if download_links:
                    await page.click(download_links[0]['selector'])
            
            # Wait for download to start
            await page.wait_for_timeout(3000)
            
            # Process downloads
            download_info = []
            for download in downloads:
                await download.save_as(f"downloads/{download.suggested_filename}")
                download_info.append({
                    "filename": download.suggested_filename,
                    "url": download.url,
                    "size": await download.path().stat().st_size if await download.path().exists() else 0
                })
            
            result = {
                "status": "success",
                "action": "automate_file_download",
                "data": {
                    "source_url": url,
                    "downloads": download_info,
                    "total_downloads": len(download_info)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"File download automation completed: {len(download_info)} files")
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "automate_file_download",
                "error": f"Download automation failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Download automation failed: {e}")
            return json.dumps(result)
    
    # WEB SEARCH TOOLS
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def intelligent_web_search(
        query: str,
        search_engines: str = '["google", "bing"]',  # JSON array
        max_results: int = 10,
        search_type: str = "general",
        user_id: str = "default"
    ) -> str:
        """Perform intelligent web searches across multiple search engines
        
        This tool performs comprehensive web searches across multiple search
        engines with intelligent result aggregation and deduplication.
        
        Keywords: search, engines, google, bing, intelligent, results
        Category: web-search
        """
        await _initialize_services()
        
        # Ensure services are initialized
        if _rate_limiter is None or _session_manager is None:
            raise Exception("Web services failed to initialize properly")
        
        try:
            engines = json.loads(search_engines)
            all_results = []
            
            for engine in engines:
                try:
                    # Rate limiting per engine
                    await _rate_limiter.wait_for_rate_limit(f"search_{engine}")
                    
                    session_id = f"search_{engine}_{user_id}"
                    page = await _session_manager.get_or_create_session(session_id, "stealth")
                    
                    # Engine-specific search
                    if engine == "google":
                        results = await _perform_google_search(page, query, max_results)
                    elif engine == "bing":
                        results = await _perform_bing_search(page, query, max_results)
                    else:
                        continue
                    
                    # Add engine info to results
                    for result in results:
                        result['search_engine'] = engine
                    
                    all_results.extend(results)
                    
                except Exception as e:
                    logger.warning(f"Search failed for {engine}: {e}")
                    continue
            
            # Deduplicate and rank results
            unique_results = _deduplicate_search_results(all_results)
            ranked_results = unique_results[:max_results]
            
            result = {
                "status": "success",
                "action": "intelligent_web_search",
                "data": {
                    "query": query,
                    "search_engines": engines,
                    "results": ranked_results,
                    "total_results": len(ranked_results),
                    "search_type": search_type
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Intelligent web search completed: {len(ranked_results)} results for '{query}'")
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "intelligent_web_search",
                "error": f"Intelligent search failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Intelligent search failed: {e}")
            return json.dumps(result)
    
    # WEB CRAWLING TOOLS
    @mcp.tool()
    # @security_manager.security_check  # Disabled for testing
    # @security_manager.require_authorization(SecurityLevel.HIGH)  # Disabled for testing
    async def intelligent_web_crawl(
        start_url: str,
        crawl_config: str,  # JSON config
        max_pages: int = 50,
        user_id: str = "default"
    ) -> str:
        """Perform intelligent web crawling with vision-guided navigation
        
        This tool performs intelligent web crawling by following links
        and extracting content based on vision-guided understanding.
        
        Keywords: crawl, spider, navigation, links, content, extraction
        Category: web-crawling
        """
        await _initialize_services()
        
        # Ensure services are initialized
        if _session_manager is None or _rate_limiter is None or _vision_analyzer is None or _human_behavior is None:
            raise Exception("Web services failed to initialize properly")
        
        try:
            config = json.loads(crawl_config)
            
            crawled_urls = set()
            crawl_queue = [start_url]
            crawl_results = []
            
            session_id = f"crawl_{user_id}_{hash(start_url)}"
            page = await _session_manager.get_or_create_session(session_id, "stealth")
            
            while crawl_queue and len(crawled_urls) < max_pages:
                current_url = crawl_queue.pop(0)
                
                if current_url in crawled_urls:
                    continue
                
                try:
                    # Rate limiting
                    await _rate_limiter.wait_for_rate_limit("crawl")
                    
                    # Navigate to page
                    await page.goto(current_url, wait_until='networkidle')
                    crawled_urls.add(current_url)
                    
                    # Extract page data
                    page_data = await _vision_analyzer.extract_page_content(page, config)
                    page_data['url'] = current_url
                    crawl_results.append(page_data)
                    
                    # Find and queue new links
                    if config.get('follow_links', True):
                        new_links = await _vision_analyzer.find_relevant_links(page, config)
                        crawl_queue.extend([link for link in new_links if link not in crawled_urls])
                    
                    # Human-like delay
                    await _human_behavior.random_delay(1000, 3000)
                    
                except Exception as e:
                    logger.warning(f"Failed to crawl {current_url}: {e}")
                    continue
            
            result = {
                "status": "success",
                "action": "intelligent_web_crawl",
                "data": {
                    "start_url": start_url,
                    "pages_crawled": len(crawled_urls),
                    "results": crawl_results,
                    "config": config
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Web crawling completed: {len(crawled_urls)} pages from {start_url}")
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "intelligent_web_crawl",
                "error": f"Web crawling failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Web crawling failed: {e}")
            return json.dumps(result)
    
    # WEB MONITORING TOOLS
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def monitor_website_changes(
        url: str,
        monitor_config: str,  # JSON config
        user_id: str = "default"
    ) -> str:
        """Monitor website for changes using vision-based detection
        
        This tool monitors websites for changes by taking screenshots
        and using vision analysis to detect meaningful changes.
        
        Keywords: monitor, changes, detection, vision, screenshots, tracking
        Category: web-monitoring
        """
        await _initialize_services()
        
        # Ensure services are initialized
        if _session_manager is None or _vision_analyzer is None:
            raise Exception("Web services failed to initialize properly")
        
        try:
            config = json.loads(monitor_config)
            
            session_id = f"monitor_{user_id}_{hash(url)}"
            page = await _session_manager.get_or_create_session(session_id, "monitoring")
            
            # Navigate to page
            await page.goto(url, wait_until='networkidle')
            
            # Take current screenshot
            current_screenshot = await page.screenshot(full_page=True)
            
            # Compare with previous screenshot if exists
            previous_screenshot_path = f"monitoring/{hash(url)}_previous.png"
            changes_detected = False
            change_details = {}
            
            if await _vision_analyzer.screenshot_exists(previous_screenshot_path):
                changes_detected, change_details = await _vision_analyzer.compare_screenshots(
                    previous_screenshot_path, current_screenshot, config
                )
            
            # Save current screenshot as previous
            current_screenshot_path = f"monitoring/{hash(url)}_current.png"
            with open(current_screenshot_path, 'wb') as f:
                f.write(current_screenshot)
            
            # Extract current page content for detailed monitoring
            content_data = await _vision_analyzer.extract_monitoring_data(page, config)
            
            result = {
                "status": "success",
                "action": "monitor_website_changes",
                "data": {
                    "url": url,
                    "changes_detected": changes_detected,
                    "change_details": change_details,
                    "content_data": content_data,
                    "screenshot_path": current_screenshot_path,
                    "monitor_config": config
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Website monitoring completed for {url}: changes={'detected' if changes_detected else 'none'}")
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "monitor_website_changes",
                "error": f"Website monitoring failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Website monitoring failed: {e}")
            return json.dumps(result)
    
    # ADMIN AND STATUS TOOLS
    @mcp.tool()
    @security_manager.security_check
    async def get_web_tools_status(user_id: str = "admin") -> str:
        """Get web tools status and statistics
        
        This tool provides administrative information about the web tools
        service including browser status, active sessions, and configuration.
        
        Keywords: admin, status, statistics, monitoring, sessions
        Category: web-admin
        """
        if user_id != "admin":
            result = {
                "status": "error",
                "action": "get_web_tools_status",
                "error": "Admin access required",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        await _initialize_services()
        
        # Ensure services are initialized
        if _browser_manager is None or _session_manager is None or _rate_limiter is None:
            raise Exception("Web services failed to initialize properly")
        
        try:
            status_data = {
                "browser_manager": await _browser_manager.get_status(),
                "session_manager": await _session_manager.get_status(),
                "rate_limiter": await _rate_limiter.get_status(),
                "services_initialized": _browser_manager is not None
            }
            
            result = {
                "status": "success",
                "action": "get_web_tools_status",
                "data": status_data,
                "timestamp": datetime.now().isoformat()
            }
            
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "get_web_tools_status", 
                "error": f"Status retrieval failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)

# Helper functions for search engines
async def _perform_google_search(page, query: str, max_results: int) -> List[Dict]:
    """Perform Google search and extract results"""
    # Ensure vision analyzer is available
    if _vision_analyzer is None:
        raise Exception("Vision analyzer not initialized")
    
    search_url = f"https://www.google.com/search?q={query}"
    await page.goto(search_url, wait_until='networkidle')
    
    # Extract search results using vision analyzer
    return await _vision_analyzer.extract_google_results(page, max_results)

async def _perform_bing_search(page, query: str, max_results: int) -> List[Dict]:
    """Perform Bing search and extract results"""
    # Ensure vision analyzer is available
    if _vision_analyzer is None:
        raise Exception("Vision analyzer not initialized")
    
    search_url = f"https://www.bing.com/search?q={query}"
    await page.goto(search_url, wait_until='networkidle')
    
    # Extract search results using vision analyzer
    return await _vision_analyzer.extract_bing_results(page, max_results)

def _deduplicate_search_results(results: List[Dict]) -> List[Dict]:
    """Remove duplicate search results based on URL"""
    seen_urls = set()
    unique_results = []
    
    for result in results:
        url = result.get('url', '')
        if url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    return unique_results