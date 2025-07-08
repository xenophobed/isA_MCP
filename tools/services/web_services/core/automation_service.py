#!/usr/bin/env python
"""
Automation Service for Web Services
Handles complex automation tasks and workflows
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from playwright.async_api import Page

from core.logging import get_logger
from .web_service_manager import get_web_service_manager
from ..strategies.extraction import PredefinedLLMSchemas, LLMExtractionStrategy
from ..strategies.filtering import SemanticFilter

logger = get_logger(__name__)

class AutomationService:
    """High-level automation service for complex web workflows"""
    
    def __init__(self):
        self.service_manager = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize the automation service"""
        if self.initialized:
            return
            
        self.service_manager = await get_web_service_manager()
        self.initialized = True
        logger.info("🤖 Automation Service initialized")
    
    async def perform_site_search(
        self, 
        base_url: str, 
        search_query: str, 
        max_results: int = 10,
        session_id: str = "automation"
    ) -> Dict[str, Any]:
        """Perform intelligent site search with automation"""
        if not self.initialized:
            await self.initialize()
            
        logger.info(f"🔍 Performing site search on {base_url} for '{search_query}'")
        
        # Get required services
        session_manager = self.service_manager.get_session_manager()
        human_behavior = self.service_manager.get_human_behavior()
        stealth_manager = self.service_manager.get_stealth_manager()
        
        # Create stealth session
        page = await session_manager.get_or_create_session(session_id, "stealth")
        
        # Apply stealth and human behavior
        if stealth_manager and page.context:
            await stealth_manager.apply_stealth_context(page.context, level="high")
        
        if human_behavior:
            await human_behavior.apply_human_navigation(page)
        
        try:
            # Navigate to base URL
            await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
            
            # Try to find search functionality
            search_results = await self._find_and_execute_search(page, search_query, max_results)
            
            return {
                "status": "success",
                "base_url": base_url,
                "search_query": search_query,
                "results": search_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Site search failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _find_and_execute_search(self, page: Page, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Find search functionality and execute search"""
        # Common search selectors
        search_selectors = [
            'input[type="search"]',
            'input[name*="search"]',
            'input[placeholder*="search"]',
            'input[id*="search"]',
            '.search-input',
            '#search-input',
            'input[name="q"]',
            'input[name="query"]'
        ]
        
        search_input = None
        for selector in search_selectors:
            try:
                search_input = await page.wait_for_selector(selector, timeout=5000)
                if search_input:
                    break
            except:
                continue
        
        if not search_input:
            raise Exception("No search input found on page")
        
        # Perform search
        await search_input.fill(query)
        
        # Try to find and click search button
        search_button_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Search")',
            'button:has-text("Go")',
            '.search-button',
            '#search-button'
        ]
        
        search_button = None
        for selector in search_button_selectors:
            try:
                search_button = await page.wait_for_selector(selector, timeout=2000)
                if search_button:
                    break
            except:
                continue
        
        if search_button:
            await search_button.click()
        else:
            # Try pressing Enter
            await search_input.press('Enter')
        
        # Wait for results
        await page.wait_for_load_state('networkidle', timeout=10000)
        
        # Extract search results
        return await self._extract_search_results(page, max_results)
    
    async def _extract_search_results(self, page: Page, max_results: int) -> List[Dict[str, Any]]:
        """Extract search results from page"""
        results = []
        
        # Common result selectors
        result_selectors = [
            '.search-result',
            '.result',
            '.search-item',
            '[data-testid*="result"]',
            'article',
            '.item'
        ]
        
        for selector in result_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    for i, element in enumerate(elements[:max_results]):
                        try:
                            # Extract title
                            title_elem = await element.query_selector('h1, h2, h3, h4, .title, .heading')
                            title = await title_elem.text_content() if title_elem else ""
                            
                            # Extract link
                            link_elem = await element.query_selector('a')
                            link = await link_elem.get_attribute('href') if link_elem else ""
                            
                            # Extract description
                            desc_elem = await element.query_selector('p, .description, .summary')
                            description = await desc_elem.text_content() if desc_elem else ""
                            
                            if title or link:
                                results.append({
                                    "title": title.strip(),
                                    "url": urljoin(page.url, link) if link else "",
                                    "description": description.strip(),
                                    "position": i + 1
                                })
                        except:
                            continue
                    
                    if results:
                        break
            except:
                continue
        
        return results[:max_results]
    
    async def perform_link_filtering(
        self, 
        page_url: str, 
        filter_criteria: Dict[str, Any],
        session_id: str = "automation"
    ) -> Dict[str, Any]:
        """Filter links on a page based on criteria"""
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"🔗 Filtering links on {page_url}")
        
        # Get required services
        session_manager = self.service_manager.get_session_manager()
        
        # Create session
        page = await session_manager.get_or_create_session(session_id, "stealth")
        
        try:
            # Navigate to page
            await page.goto(page_url, wait_until='domcontentloaded', timeout=30000)
            
            # Extract all links
            links = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(link => ({
                        text: link.textContent.trim(),
                        url: link.href,
                        title: link.title || '',
                        class: link.className || ''
                    }));
                }
            """)
            
            # Apply filters
            filtered_links = self._apply_link_filters(links, filter_criteria)
            
            return {
                "status": "success",
                "page_url": page_url,
                "total_links": len(links),
                "filtered_links": filtered_links,
                "filter_criteria": filter_criteria,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Link filtering failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _apply_link_filters(self, links: List[Dict[str, Any]], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply filtering criteria to links"""
        filtered = links
        
        # Filter by text content
        if criteria.get('text_contains'):
            text_filter = criteria['text_contains'].lower()
            filtered = [link for link in filtered if text_filter in link['text'].lower()]
        
        # Filter by URL pattern
        if criteria.get('url_contains'):
            url_filter = criteria['url_contains'].lower()
            filtered = [link for link in filtered if url_filter in link['url'].lower()]
        
        # Filter by domain
        if criteria.get('domain_filter'):
            domain_filter = criteria['domain_filter'].lower()
            filtered = [link for link in filtered if domain_filter in urlparse(link['url']).netloc.lower()]
        
        # Exclude patterns
        if criteria.get('exclude_patterns'):
            exclude_patterns = [p.lower() for p in criteria['exclude_patterns']]
            filtered = [
                link for link in filtered 
                if not any(pattern in link['url'].lower() or pattern in link['text'].lower() 
                          for pattern in exclude_patterns)
            ]
        
        # Limit results
        max_results = criteria.get('max_results', 50)
        return filtered[:max_results]
    
    async def perform_form_automation(
        self, 
        page_url: str, 
        form_data: Dict[str, Any],
        session_id: str = "automation"
    ) -> Dict[str, Any]:
        """Automate form filling and submission"""
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"📝 Automating form on {page_url}")
        
        # Get required services
        session_manager = self.service_manager.get_session_manager()
        human_behavior = self.service_manager.get_human_behavior()
        
        # Create session
        page = await session_manager.get_or_create_session(session_id, "automation")
        
        try:
            # Navigate to page
            await page.goto(page_url, wait_until='domcontentloaded', timeout=30000)
            
            # Fill form fields
            filled_fields = []
            for field_name, field_value in form_data.items():
                if field_name == '_submit':
                    continue
                    
                # Try multiple selectors for the field
                field_selectors = [
                    f'input[name="{field_name}"]',
                    f'input[id="{field_name}"]',
                    f'textarea[name="{field_name}"]',
                    f'select[name="{field_name}"]',
                    f'[data-testid="{field_name}"]'
                ]
                
                field_element = None
                for selector in field_selectors:
                    try:
                        field_element = await page.wait_for_selector(selector, timeout=5000)
                        if field_element:
                            break
                    except:
                        continue
                
                if field_element:
                    # Human-like typing
                    if human_behavior:
                        await human_behavior.human_type(field_element, str(field_value))
                    else:
                        await field_element.fill(str(field_value))
                    
                    filled_fields.append(field_name)
                    
                    # Human-like delay between fields
                    if human_behavior:
                        await human_behavior.random_delay(500, 1500)
            
            # Submit form if requested
            submitted = False
            if form_data.get('_submit', False):
                submit_selectors = [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Submit")',
                    'button:has-text("Send")',
                    '.submit-button'
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_button = await page.wait_for_selector(selector, timeout=5000)
                        if submit_button:
                            await submit_button.click()
                            submitted = True
                            break
                    except:
                        continue
            
            return {
                "status": "success",
                "page_url": page_url,
                "filled_fields": filled_fields,
                "submitted": submitted,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Form automation failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def perform_data_collection(
        self, 
        page_url: str, 
        collection_config: Dict[str, Any],
        session_id: str = "automation"
    ) -> Dict[str, Any]:
        """Collect structured data from a page"""
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"📊 Collecting data from {page_url}")
        
        # Get required services
        session_manager = self.service_manager.get_session_manager()
        extraction_engine = self.service_manager.get_extraction_engine()
        
        # Create session
        page = await session_manager.get_or_create_session(session_id, "stealth")
        
        try:
            # Navigate to page
            await page.goto(page_url, wait_until='domcontentloaded', timeout=30000)
            
            # Determine extraction strategy
            extraction_type = collection_config.get('type', 'article')
            
            # Get appropriate schema
            if extraction_type == 'article':
                schema = PredefinedLLMSchemas.get_article_extraction_schema()
            elif extraction_type == 'product':
                schema = PredefinedLLMSchemas.get_product_extraction_schema()
            elif extraction_type == 'contact':
                schema = PredefinedLLMSchemas.get_contact_extraction_schema()
            else:
                schema = PredefinedLLMSchemas.get_article_extraction_schema()
            
            # Extract data
            extractor = LLMExtractionStrategy(schema)
            extracted_data = await extractor.extract(page, "")
            await extractor.close()
            
            # Apply post-processing if configured
            if collection_config.get('filter_query'):
                filter_query = collection_config['filter_query']
                semantic_filter = SemanticFilter(
                    user_query=filter_query,
                    similarity_threshold=0.6,
                    min_chunk_length=100
                )
                
                # Filter extracted data
                filtered_data = []
                for item in extracted_data:
                    item_text = " ".join([
                        str(item.get("title", "")),
                        str(item.get("content", "")),
                        str(item.get("description", ""))
                    ]).strip()
                    
                    if item_text:
                        filtered_text = await semantic_filter.filter(item_text)
                        if filtered_text.strip():
                            filtered_data.append(item)
                
                extracted_data = filtered_data
                await semantic_filter.close()
            
            return {
                "status": "success",
                "page_url": page_url,
                "extraction_type": extraction_type,
                "collected_data": extracted_data,
                "items_count": len(extracted_data),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Data collection failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def cleanup(self):
        """Cleanup automation service resources"""
        if self.service_manager:
            # Service manager handles its own cleanup
            pass
        self.initialized = False
        logger.info("🧹 Automation Service cleaned up")