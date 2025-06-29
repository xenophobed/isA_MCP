#!/usr/bin/env python
"""
Extraction Engine for Web Services
Handles content extraction with multiple strategies (CSS, LLM, Regex)
Based on Crawl4AI's extraction architecture
"""
import asyncio
from typing import Dict, Any, List, Optional, Union
from playwright.async_api import Page
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger
from ..strategies.base import ExtractionStrategy, FilterStrategy, GenerationStrategy

logger = get_logger(__name__)

class ExtractionMode(Enum):
    """Content extraction modes"""
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    STRUCTURED = "structured"

@dataclass
class CrawlResult:
    """Standardized crawl result container (inspired by Crawl4AI)"""
    url: str
    success: bool
    status_code: Optional[int] = None
    title: Optional[str] = None
    raw_html: Optional[str] = None
    cleaned_html: Optional[str] = None
    markdown: Optional[str] = None
    text_content: Optional[str] = None
    extracted_data: Optional[List[Dict[str, Any]]] = None
    links: Optional[List[str]] = None
    images: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'url': self.url,
            'success': self.success,
            'status_code': self.status_code,
            'title': self.title,
            'raw_html': self.raw_html,
            'cleaned_html': self.cleaned_html,
            'markdown': self.markdown,
            'text_content': self.text_content,
            'extracted_data': self.extracted_data,
            'links': self.links,
            'images': self.images,
            'metadata': self.metadata,
            'processing_time': self.processing_time,
            'error_message': self.error_message
        }

class ExtractionEngine:
    """Main extraction engine with strategy support"""
    
    def __init__(self):
        self.extraction_strategies: Dict[str, ExtractionStrategy] = {}
        self.filter_strategies: Dict[str, FilterStrategy] = {}
        self.generation_strategies: Dict[str, GenerationStrategy] = {}
        
    def register_extraction_strategy(self, name: str, strategy: ExtractionStrategy):
        """Register an extraction strategy"""
        self.extraction_strategies[name] = strategy
        logger.info(f"✅ Registered extraction strategy: {name}")
    
    def register_filter_strategy(self, name: str, strategy: FilterStrategy):
        """Register a filter strategy"""
        self.filter_strategies[name] = strategy
        logger.info(f"✅ Registered filter strategy: {name}")
    
    def register_generation_strategy(self, name: str, strategy: GenerationStrategy):
        """Register a generation strategy"""
        self.generation_strategies[name] = strategy
        logger.info(f"✅ Registered generation strategy: {name}")
    
    async def crawl_page(
        self,
        page: Page,
        extraction_strategy: Optional[str] = None,
        filter_strategy: Optional[str] = None,
        generation_strategy: Optional[str] = "markdown",
        extract_links: bool = True,
        extract_images: bool = True
    ) -> CrawlResult:
        """Crawl a page and extract content using specified strategies"""
        
        start_time = asyncio.get_event_loop().time()
        url = page.url
        
        logger.info(f"🕷️ Starting page crawl: {url}")
        
        try:
            # Get basic page info
            title = await page.title()
            html_content = await page.content()
            
            result = CrawlResult(
                url=url,
                success=True,
                title=title,
                raw_html=html_content
            )
            
            # Extract text content
            text_content = await page.evaluate("""
                () => {
                    // Remove script and style elements
                    const scripts = document.querySelectorAll('script, style, nav, footer');
                    scripts.forEach(el => el.remove());
                    
                    // Get main content
                    const main = document.querySelector('main') || 
                                 document.querySelector('[role="main"]') ||
                                 document.querySelector('.content') ||
                                 document.querySelector('#content') ||
                                 document.body;
                    
                    return main ? main.innerText : document.body.innerText;
                }
            """)
            result.text_content = text_content
            
            # Apply content generation strategy
            if generation_strategy and generation_strategy in self.generation_strategies:
                logger.info(f"🔄 Applying generation strategy: {generation_strategy}")
                strategy = self.generation_strategies[generation_strategy]
                generated_content = await strategy.generate(html_content)
                
                if generation_strategy == "markdown":
                    result.markdown = generated_content
                else:
                    result.cleaned_html = generated_content
            
            # Apply content filtering if specified
            if filter_strategy and filter_strategy in self.filter_strategies:
                logger.info(f"🔄 Applying filter strategy: {filter_strategy}")
                filter_strat = self.filter_strategies[filter_strategy]
                if result.markdown:
                    result.markdown = await filter_strat.filter(result.markdown)
                if result.text_content:
                    result.text_content = await filter_strat.filter(result.text_content)
            
            # Apply data extraction strategy if specified
            if extraction_strategy and extraction_strategy in self.extraction_strategies:
                logger.info(f"🔄 Applying extraction strategy: {extraction_strategy}")
                extract_strat = self.extraction_strategies[extraction_strategy]
                result.extracted_data = await extract_strat.extract(page, html_content)
            
            # Extract links if requested
            if extract_links:
                links = await page.evaluate("""
                    () => {
                        const links = Array.from(document.querySelectorAll('a[href]'));
                        return links.map(link => link.href).filter(href => 
                            href.startsWith('http') || href.startsWith('/')
                        );
                    }
                """)
                result.links = list(set(links))  # Remove duplicates
            
            # Extract images if requested
            if extract_images:
                images = await page.evaluate("""
                    () => {
                        const images = Array.from(document.querySelectorAll('img[src]'));
                        return images.map(img => img.src).filter(src => 
                            src.startsWith('http') || src.startsWith('/')
                        );
                    }
                """)
                result.images = list(set(images))  # Remove duplicates
            
            # Add metadata
            metadata = await page.evaluate("""
                () => {
                    const meta = {};
                    
                    // Get meta tags
                    const metaTags = document.querySelectorAll('meta');
                    metaTags.forEach(tag => {
                        const name = tag.getAttribute('name') || tag.getAttribute('property');
                        const content = tag.getAttribute('content');
                        if (name && content) {
                            meta[name] = content;
                        }
                    });
                    
                    // Get canonical URL
                    const canonical = document.querySelector('link[rel="canonical"]');
                    if (canonical) {
                        meta.canonical_url = canonical.href;
                    }
                    
                    // Get language
                    const lang = document.documentElement.lang;
                    if (lang) {
                        meta.language = lang;
                    }
                    
                    return meta;
                }
            """)
            result.metadata = metadata
            
            # Calculate processing time
            end_time = asyncio.get_event_loop().time()
            result.processing_time = end_time - start_time
            
            logger.info(f"✅ Page crawl completed: {url} ({result.processing_time:.2f}s)")
            return result
            
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            logger.error(f"❌ Page crawl failed: {url} - {e}")
            
            return CrawlResult(
                url=url,
                success=False,
                error_message=str(e),
                processing_time=end_time - start_time
            )
    
    async def crawl_url(
        self,
        url: str,
        browser_manager,
        session_id: Optional[str] = None,
        **crawl_options
    ) -> CrawlResult:
        """Crawl a URL using browser manager"""
        
        logger.info(f"🌐 Crawling URL: {url}")
        
        try:
            # Get or create session
            if session_id:
                page = await browser_manager.get_session(session_id)
            else:
                browser = await browser_manager.get_browser("stealth")
                context = await browser.new_context()
                page = await context.new_page()
            
            # Navigate to URL
            await page.goto(url, wait_until='networkidle')
            
            # Crawl the page
            result = await self.crawl_page(page, **crawl_options)
            
            # Close page if not using session
            if not session_id:
                await page.close()
                await context.close()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ URL crawl failed: {url} - {e}")
            return CrawlResult(
                url=url,
                success=False,
                error_message=str(e)
            )
    
    def get_available_strategies(self) -> Dict[str, List[str]]:
        """Get list of available strategies"""
        return {
            'extraction': list(self.extraction_strategies.keys()),
            'filter': list(self.filter_strategies.keys()),
            'generation': list(self.generation_strategies.keys())
        }