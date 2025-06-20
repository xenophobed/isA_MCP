#!/usr/bin/env python
"""
Web Scraper Tools for MCP Server
Handles web scraping operations with modern Playwright support and security
"""
import json
import asyncio
import time
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin
from pathlib import Path

# Playwright for modern web scraping
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError

# BeautifulSoup for HTML parsing fallback
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.monitoring import monitor_manager

logger = get_logger(__name__)

# Global scraper state
_browser = None
_context = None
_rate_limiter = {}

class ScraperConfig:
    """Scraper configuration"""
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    TIMEOUT = 30
    RATE_LIMIT_DELAY = 2.0
    MAX_PAGES = 100
    MAX_CONCURRENT = 10

def _check_rate_limit(domain: str) -> bool:
    """Check if request is within rate limits"""
    now = time.time()
    if domain not in _rate_limiter:
        _rate_limiter[domain] = []
    
    # Clean old entries (1 minute window)
    _rate_limiter[domain] = [
        timestamp for timestamp in _rate_limiter[domain]
        if now - timestamp < 60
    ]
    
    # Max 30 requests per minute per domain
    if len(_rate_limiter[domain]) >= 30:
        return False
    
    _rate_limiter[domain].append(now)
    return True

async def _initialize_browser():
    """Initialize Playwright browser if not already done"""
    global _browser, _context
    
    if _browser and _context:
        return
    
    try:
        playwright = await async_playwright().start()
        
        _browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions'
            ]
        )
        
        _context = await _browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=ScraperConfig.USER_AGENTS[0],
            java_script_enabled=True,
            ignore_https_errors=True
        )
        
        # Add stealth script
        await _context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        """)
        
        logger.info("Playwright browser initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize browser: {e}")
        raise

async def _scrape_with_playwright(url: str, enable_javascript: bool = True) -> Dict[str, Any]:
    """Scrape using Playwright for dynamic content"""
    await _initialize_browser()
    
    page = await _context.new_page()
    start_time = time.time()
    
    try:
        # Navigate to page
        response = await page.goto(
            url,
            wait_until='networkidle',
            timeout=ScraperConfig.TIMEOUT * 1000
        )
        
        # Wait for dynamic content
        await page.wait_for_timeout(1000)
        
        # Extract data
        title = await page.title()
        html = await page.content()
        
        # Extract text content
        content = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script, style');
                scripts.forEach(el => el.remove());
                return document.body.innerText || document.body.textContent || '';
            }
        """)
        
        # Extract links
        links = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]')).map(el => el.href)
        """)
        
        # Extract images
        images = await page.evaluate("""
            () => Array.from(document.querySelectorAll('img[src]')).map(el => el.src)
        """)
        
        # Extract metadata
        metadata = await page.evaluate("""
            () => {
                const meta = {};
                document.querySelectorAll('meta').forEach(el => {
                    const name = el.getAttribute('name') || el.getAttribute('property');
                    const content = el.getAttribute('content');
                    if (name && content) {
                        meta[name] = content;
                    }
                });
                return meta;
            }
        """)
        
        load_time = time.time() - start_time
        
        return {
            "url": url,
            "title": title,
            "content": content.strip(),
            "html": html,
            "links": links,
            "images": images,
            "metadata": metadata,
            "status_code": response.status,
            "load_time": load_time,
            "method": "playwright"
        }
        
    finally:
        await page.close()

def _scrape_with_requests(url: str) -> Dict[str, Any]:
    """Fallback scraping using requests + BeautifulSoup"""
    start_time = time.time()
    
    session = requests.Session()
    retry_strategy = Retry(total=3, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    session.headers.update({
        'User-Agent': ScraperConfig.USER_AGENTS[0]
    })
    
    try:
        response = session.get(url, timeout=ScraperConfig.TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract data
        title = soup.title.string if soup.title else ""
        content = soup.get_text(strip=True, separator=' ')
        
        # Extract links
        links = [urljoin(url, link.get('href')) for link in soup.find_all('a', href=True)]
        
        # Extract images
        images = [urljoin(url, img.get('src')) for img in soup.find_all('img', src=True)]
        
        # Extract metadata
        metadata = {}
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                metadata[name] = content
        
        load_time = time.time() - start_time
        
        return {
            "url": url,
            "title": title,
            "content": content,
            "html": str(soup),
            "links": links,
            "images": images,
            "metadata": metadata,
            "status_code": response.status_code,
            "load_time": load_time,
            "method": "requests"
        }
        
    except Exception as e:
        logger.error(f"Requests scraping failed for {url}: {e}")
        raise

async def _cleanup_browser():
    """Clean up browser resources"""
    global _browser, _context
    
    try:
        if _context:
            await _context.close()
            _context = None
        if _browser:
            await _browser.close()
            _browser = None
        logger.info("Browser cleanup completed")
    except Exception as e:
        logger.warning(f"Browser cleanup warning: {e}")

def register_web_scraper_tools(mcp):
    """Register all web scraper tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def scrape_webpage(
        url: str, 
        enable_javascript: bool = True,
        take_screenshot: bool = False,
        user_id: str = "default"
    ) -> str:
        """Scrape a single webpage with modern anti-detection techniques"""
        
        # Validate URL
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError("Invalid URL format")
        except Exception as e:
            result = {
                "status": "error",
                "action": "scrape_webpage",
                "error": f"URL validation failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"URL validation failed: {url} - {e}")
            return json.dumps(result)
        
        domain = parsed_url.netloc
        
        # Check rate limits
        if not _check_rate_limit(domain):
            result = {
                "status": "error",
                "action": "scrape_webpage",
                "error": f"Rate limit exceeded for domain: {domain}",
                "timestamp": datetime.now().isoformat()
            }
            logger.warning(f"Rate limit exceeded for {domain}")
            return json.dumps(result)
        
        # Add delay for politeness
        await asyncio.sleep(ScraperConfig.RATE_LIMIT_DELAY)
        
        try:
            if enable_javascript:
                scrape_data = await _scrape_with_playwright(url, enable_javascript)
            else:
                scrape_data = _scrape_with_requests(url)
            
            # Take screenshot if requested and using Playwright
            screenshot_path = None
            if take_screenshot and enable_javascript:
                try:
                    await _initialize_browser()
                    page = await _context.new_page()
                    await page.goto(url)
                    screenshot_path = f"screenshots/{hashlib.md5(url.encode()).hexdigest()}.png"
                    Path("screenshots").mkdir(exist_ok=True)
                    await page.screenshot(path=screenshot_path, full_page=True)
                    await page.close()
                    scrape_data["screenshot_path"] = screenshot_path
                except Exception as e:
                    logger.warning(f"Screenshot failed: {e}")
            
            result = {
                "status": "success",
                "action": "scrape_webpage",
                "data": scrape_data,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Successfully scraped {url} in {scrape_data['load_time']:.2f}s using {scrape_data['method']}")
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "scrape_webpage",
                "error": f"Scraping failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Scraping failed for {url}: {e}")
            return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.HIGH)
    async def scrape_multiple_pages(
        urls: str,  # JSON string of URLs
        max_concurrent: int = 3,
        enable_javascript: bool = True,
        user_id: str = "default"
    ) -> str:
        """Scrape multiple webpages concurrently with rate limiting"""
        
        # Parse URLs
        try:
            url_list = json.loads(urls)
            if not isinstance(url_list, list):
                raise ValueError("URLs must be a JSON array")
        except json.JSONDecodeError as e:
            result = {
                "status": "error",
                "action": "scrape_multiple_pages",
                "error": f"Invalid JSON format for URLs: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        # Validate limits
        if len(url_list) > ScraperConfig.MAX_PAGES:
            result = {
                "status": "error",
                "action": "scrape_multiple_pages",
                "error": f"Too many URLs. Maximum allowed: {ScraperConfig.MAX_PAGES}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        if max_concurrent > ScraperConfig.MAX_CONCURRENT:
            max_concurrent = ScraperConfig.MAX_CONCURRENT
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    result = await scrape_webpage(url, enable_javascript, False, user_id)
                    parsed_result = json.loads(result)
                    return {
                        "url": url,
                        "success": parsed_result["status"] == "success",
                        "data": parsed_result.get("data", {}),
                        "error": parsed_result.get("error")
                    }
                except Exception as e:
                    return {
                        "url": url,
                        "success": False,
                        "error": str(e)
                    }
        
        # Execute concurrent scraping
        start_time = time.time()
        tasks = [scrape_with_semaphore(url) for url in url_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed = [r for r in results if isinstance(r, dict) and not r.get("success")]
        exceptions = [r for r in results if not isinstance(r, dict)]
        
        total_time = time.time() - start_time
        
        result = {
            "status": "completed",
            "action": "scrape_multiple_pages",
            "data": {
                "total_urls": len(url_list),
                "successful": len(successful),
                "failed": len(failed) + len(exceptions),
                "results": successful,
                "errors": failed,
                "execution_time": total_time
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Batch scraping completed: {len(successful)}/{len(url_list)} successful in {total_time:.2f}s")
        return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    async def extract_page_links(
        url: str,
        link_pattern: str = "",
        user_id: str = "default"
    ) -> str:
        """Extract all links from a webpage with optional filtering"""
        
        try:
            # First scrape the page
            scrape_result = await scrape_webpage(url, True, False, user_id)
            parsed_result = json.loads(scrape_result)
            
            if parsed_result["status"] != "success":
                return scrape_result  # Return the error from scraping
            
            links = parsed_result["data"]["links"]
            
            # Filter links by pattern if provided
            filtered_links = links
            if link_pattern and link_pattern.strip():
                import re
                try:
                    regex = re.compile(link_pattern, re.IGNORECASE)
                    filtered_links = [link for link in links if regex.search(link)]
                except re.error as e:
                    result = {
                        "status": "error",
                        "action": "extract_page_links",
                        "error": f"Invalid regex pattern: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }
                    return json.dumps(result)
            
            result = {
                "status": "success",
                "action": "extract_page_links",
                "data": {
                    "url": url,
                    "links": filtered_links,
                    "total_found": len(filtered_links),
                    "total_on_page": len(links),
                    "pattern": link_pattern
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Extracted {len(filtered_links)} links from {url}")
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "extract_page_links",
                "error": f"Link extraction failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Link extraction failed for {url}: {e}")
            return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    async def search_page_content(
        url: str,
        search_terms: str,  # JSON string of search terms
        case_sensitive: bool = False,
        user_id: str = "default"
    ) -> str:
        """Search for specific content within a webpage"""
        
        # Parse search terms
        try:
            terms_list = json.loads(search_terms)
            if not isinstance(terms_list, list):
                raise ValueError("Search terms must be a JSON array")
        except json.JSONDecodeError as e:
            result = {
                "status": "error",
                "action": "search_page_content",
                "error": f"Invalid JSON format for search terms: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        try:
            # First scrape the page
            scrape_result = await scrape_webpage(url, True, False, user_id)
            parsed_result = json.loads(scrape_result)
            
            if parsed_result["status"] != "success":
                return scrape_result  # Return the error from scraping
            
            content = parsed_result["data"]["content"]
            
            # Search for terms
            import re
            search_results = {}
            flags = 0 if case_sensitive else re.IGNORECASE
            
            for term in terms_list:
                matches = re.findall(re.escape(term), content, flags)
                search_results[term] = {
                    "count": len(matches),
                    "found": len(matches) > 0
                }
            
            result = {
                "status": "success",
                "action": "search_page_content",
                "data": {
                    "url": url,
                    "search_results": search_results,
                    "content_length": len(content),
                    "case_sensitive": case_sensitive
                },
                "timestamp": datetime.now().isoformat()
            }
            
            found_terms = sum(1 for r in search_results.values() if r["found"])
            logger.info(f"Content search on {url}: {found_terms}/{len(terms_list)} terms found")
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "search_page_content",
                "error": f"Content search failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Content search failed for {url}: {e}")
            return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    async def get_scraper_status(user_id: str = "admin") -> str:
        """Get web scraper status and statistics (admin only)"""
        
        if user_id != "admin":
            result = {
                "status": "error",
                "action": "get_scraper_status",
                "error": "Admin access required",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        try:
            status_data = {
                "browser_initialized": _browser is not None,
                "context_active": _context is not None,
                "rate_limiter": {
                    domain: len(timestamps) 
                    for domain, timestamps in _rate_limiter.items()
                },
                "config": {
                    "timeout": ScraperConfig.TIMEOUT,
                    "rate_limit_delay": ScraperConfig.RATE_LIMIT_DELAY,
                    "max_pages": ScraperConfig.MAX_PAGES,
                    "max_concurrent": ScraperConfig.MAX_CONCURRENT
                }
            }
            
            result = {
                "status": "success",
                "action": "get_scraper_status",
                "data": status_data,
                "timestamp": datetime.now().isoformat()
            }
            
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "get_scraper_status",
                "error": f"Status retrieval failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.HIGH)
    async def cleanup_scraper_resources(user_id: str = "admin") -> str:
        """Clean up browser resources (admin only)"""
        
        if user_id != "admin":
            result = {
                "status": "error",
                "action": "cleanup_scraper_resources",
                "error": "Admin access required",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(result)
        
        try:
            await _cleanup_browser()
            
            result = {
                "status": "success",
                "action": "cleanup_scraper_resources",
                "data": {"message": "Browser resources cleaned up successfully"},
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("Scraper resources cleaned up by admin")
            return json.dumps(result)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "cleanup_scraper_resources",
                "error": f"Cleanup failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Scraper cleanup failed: {e}")
            return json.dumps(result)