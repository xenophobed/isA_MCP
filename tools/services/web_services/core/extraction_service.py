#!/usr/bin/env python
"""
Extraction Service for Web Services
Handles complex extraction workflows and content processing
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.logging import get_logger
from .web_service_manager import get_web_service_manager
from ..strategies.extraction import PredefinedLLMSchemas, LLMExtractionStrategy
from ..strategies.filtering import SemanticFilter

logger = get_logger(__name__)

class ExtractionService:
    """High-level extraction service for complex content workflows"""
    
    def __init__(self):
        self.service_manager = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize the extraction service"""
        if self.initialized:
            return
            
        self.service_manager = await get_web_service_manager()
        self.initialized = True
        logger.info("🔍 Extraction Service initialized")
    
    async def extract_from_urls(
        self,
        urls: List[str],
        extraction_schema: str = "article",
        filter_query: str = "",
        max_urls: int = 5,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """Extract structured data from multiple URLs"""
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"🕷️ Starting extraction from {len(urls)} URLs")
        
        # Limit URLs
        url_list = urls[:max_urls]
        
        # Get required services
        browser_manager = self.service_manager.get_browser_manager()
        session_manager = self.service_manager.get_session_manager()
        stealth_manager = self.service_manager.get_stealth_manager()
        human_behavior = self.service_manager.get_human_behavior()
        
        # Initialize browser if needed
        if not browser_manager.initialized:
            await browser_manager.initialize()
        
        # Create session
        session_id = f"extract_{user_id}_{hash(str(url_list))}"
        page = await session_manager.get_or_create_session(session_id, "stealth")
        
        # Apply stealth and human behavior
        if stealth_manager and page.context:
            await stealth_manager.apply_stealth_context(page.context, level="high")
        
        if human_behavior:
            await human_behavior.apply_human_navigation(page)
        
        # Setup extraction schema
        schema = self._get_extraction_schema(extraction_schema)
        
        # Setup semantic filtering
        semantic_filter = None
        if filter_query.strip():
            semantic_filter = SemanticFilter(
                user_query=filter_query,
                similarity_threshold=0.6,
                min_chunk_length=100
            )
        
        # Process URLs
        all_extracted_data = []
        processing_stats = {
            "total_urls": len(url_list),
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_items_extracted": 0,
            "processing_times": []
        }
        
        for i, url in enumerate(url_list):
            start_time = datetime.now()
            
            try:
                logger.info(f"🔍 Processing URL {i+1}/{len(url_list)}: {url}")
                
                # Enhanced navigation with stealth
                await self._navigate_with_stealth(page, url, human_behavior)
                
                # Extract data
                extracted_data = await self._extract_data_from_page(
                    page, schema, extraction_schema
                )
                
                # Apply filtering
                if semantic_filter and extracted_data:
                    extracted_data = await self._apply_semantic_filtering(
                        extracted_data, semantic_filter
                    )
                
                # Add metadata
                if extracted_data:
                    for item in extracted_data:
                        item.update({
                            "source_url": url,
                            "extraction_timestamp": datetime.now().isoformat(),
                            "extraction_schema": schema.get("name", "custom"),
                            "extraction_index": i
                        })
                    
                    all_extracted_data.extend(extracted_data)
                    processing_stats["successful_extractions"] += 1
                    processing_stats["total_items_extracted"] += len(extracted_data)
                    
                    logger.info(f"✅ Extracted {len(extracted_data)} items from {url}")
                else:
                    logger.warning(f"⚠️ No data extracted from {url}")
                    processing_stats["failed_extractions"] += 1
                
                # Record processing time
                processing_time = (datetime.now() - start_time).total_seconds()
                processing_stats["processing_times"].append(processing_time)
                
            except Exception as e:
                processing_stats["failed_extractions"] += 1
                processing_time = (datetime.now() - start_time).total_seconds()
                processing_stats["processing_times"].append(processing_time)
                logger.error(f"❌ Failed to extract from {url}: {e}")
                continue
        
        # Cleanup
        if semantic_filter:
            await semantic_filter.close()
        
        # Calculate statistics
        avg_processing_time = (
            sum(processing_stats["processing_times"]) / len(processing_stats["processing_times"])
            if processing_stats["processing_times"] else 0
        )
        
        return {
            "status": "success",
            "action": "extract_from_urls",
            "data": {
                "extracted_items": all_extracted_data,
                "extraction_schema": {
                    "name": schema.get("name", "custom"),
                    "type": schema.get("content_type", "general"),
                    "fields": [f.get("name") for f in schema.get("fields", [])]
                },
                "filtering": {
                    "enabled": bool(filter_query.strip()),
                    "query": filter_query if filter_query.strip() else None,
                    "method": "semantic_similarity" if filter_query.strip() else None
                },
                "processing_stats": {
                    **processing_stats,
                    "average_processing_time_seconds": round(avg_processing_time, 2),
                    "success_rate": round(
                        processing_stats["successful_extractions"] / processing_stats["total_urls"] * 100, 1
                    ) if processing_stats["total_urls"] > 0 else 0
                }
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_extraction_schema(self, extraction_schema: str) -> Dict[str, Any]:
        """Get extraction schema configuration"""
        if extraction_schema == "article":
            return PredefinedLLMSchemas.get_article_extraction_schema()
        elif extraction_schema == "product":
            return PredefinedLLMSchemas.get_product_extraction_schema()
        elif extraction_schema == "contact":
            return PredefinedLLMSchemas.get_contact_extraction_schema()
        elif extraction_schema == "event":
            return PredefinedLLMSchemas.get_event_extraction_schema()
        elif extraction_schema == "research":
            return PredefinedLLMSchemas.get_research_extraction_schema()
        else:
            # Try to parse as custom schema
            try:
                schema = json.loads(extraction_schema)
                if not isinstance(schema, dict) or "fields" not in schema:
                    raise ValueError("Custom schema must have 'fields' key")
                return schema
            except json.JSONDecodeError:
                # Fallback to article schema
                logger.warning(f"Invalid extraction_schema, using article schema")
                return PredefinedLLMSchemas.get_article_extraction_schema()
    
    async def _navigate_with_stealth(self, page, url: str, human_behavior):
        """Navigate to URL with stealth and human behavior"""
        # Enhanced navigation for sensitive sites
        if any(site in url for site in ["amazon.com", "walmart.com", "target.com"]):
            logger.info(f"🛡️ Detected sensitive site, using full stealth mode")
            
            # Set realistic headers
            await page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1"
            })
            
            # Navigate with human behavior
            await page.goto(url, wait_until='domcontentloaded', timeout=45000)
            
            if human_behavior:
                await human_behavior.random_mouse_movement(page, movements=2)
                await human_behavior.simulate_reading(page, reading_time_factor=0.5)
            
            await page.wait_for_load_state('networkidle', timeout=15000)
        else:
            # Standard navigation with light human behavior
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            if human_behavior:
                await human_behavior.human_navigation_pause(page)
    
    async def _extract_data_from_page(self, page, schema: Dict[str, Any], extraction_schema: str) -> List[Dict[str, Any]]:
        """Extract data from a single page"""
        # Use shared LLM extractor for article schema
        if extraction_schema == "article":
            shared_extractor = self.service_manager.get_shared_llm_extractor()
            return await shared_extractor.extract(page, "")
        else:
            # Create dedicated extractor for other schemas
            extractor = LLMExtractionStrategy(schema)
            try:
                return await extractor.extract(page, "")
            finally:
                await extractor.close()
    
    async def _apply_semantic_filtering(
        self, 
        data: List[Dict[str, Any]], 
        semantic_filter: SemanticFilter
    ) -> List[Dict[str, Any]]:
        """Apply semantic filtering to extracted data"""
        filtered_data = []
        
        for item in data:
            # Combine text fields for filtering
            item_text = " ".join([
                str(item.get("title", "")),
                str(item.get("content", "")),
                str(item.get("description", "")),
                str(item.get("summary", ""))
            ]).strip()
            
            if item_text:
                filtered_text = await semantic_filter.filter(item_text)
                if filtered_text.strip():  # Keep if content remains after filtering
                    filtered_data.append(item)
        
        return filtered_data
    
    async def cleanup(self):
        """Cleanup extraction service resources"""
        if self.service_manager:
            # Service manager handles its own cleanup
            pass
        self.initialized = False
        logger.info("🧹 Extraction Service cleaned up")