from typing import Optional
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

async def crawl_webpage(url: str, max_depth: Optional[int] = 1) -> str:
    """
    Crawl and scrape webpage content using Playwright.
    
    Args:
        url: The URL to crawl
        max_depth: Maximum depth to crawl (default: 1)
        
    Returns:
        str: Scraped content in markdown format
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Navigate to URL
            await page.goto(url)
            
            # Wait for content to load
            await page.wait_for_load_state('networkidle')
            
            # Get page content
            content = await page.content()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract text content
            text_content = soup.get_text(separator='\n', strip=True)
            
            # Close browser
            await browser.close()
            
            return text_content
            
    except Exception as e:
        logger.error(f"Error crawling webpage {url}: {e}")
        raise 