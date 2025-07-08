#!/usr/bin/env python
"""
Web Tools for MCP Server
Simple and powerful web search with two modes: simple (direct API) and deep (full workflow)
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.logging import get_logger
from core.config import get_settings
from tools.base_tool import BaseTool

# Web Service Manager import
from tools.services.web_services.core.web_service_manager import get_web_service_manager, cleanup_web_service_manager

# Essential types for search functionality
from tools.services.web_services.engines.search_engine import SearchProvider
from tools.services.web_services.strategies.extraction import PredefinedLLMSchemas

logger = get_logger(__name__)

# Global web service manager instance
_web_service_manager = None

async def _initialize_search_services():
    """Initialize web services using the centralized service manager"""
    global _web_service_manager
    
    try:
        if _web_service_manager is None:
            print("🔧 Initializing web service manager...")
            _web_service_manager = await get_web_service_manager()
            print("✅ Web Service Manager initialized")
            logger.info("Web Service Manager initialized")
        else:
            print("ℹ️ Web Service Manager already initialized")
            
    except Exception as e:
        print(f"❌ Failed to initialize web service manager: {e}")
        raise

def register_web_tools(mcp):
    """Register web search and extraction tools with the MCP server"""
    
    # Create base tool instance for security management
    base_tool = BaseTool()
    
    @mcp.tool()
    # @base_tool.security_manager.security_check  # Disabled for testing
    async def crawl_and_extract(
        urls: str,  # JSON array of URLs to crawl
        extraction_schema: str = "article",  # "article", "product", "contact", "event", "research", or custom JSON
        filter_query: str = "",  # Optional query for semantic filtering
        max_urls: int = 5,
        user_id: str = "default"
    ) -> str:
        """Step 3: Crawl URLs and extract structured data using LLM-based extraction
        
        This implements the third step of our 4-step web workflow:
        Crawl & Extract → Extract filtered data from web pages
        
        Args:
            urls: JSON array of URLs to crawl and extract from
            extraction_schema: Predefined schema ("article", "product", "contact", "event", "research") or custom JSON schema
            filter_query: Optional query for semantic content filtering
            max_urls: Maximum number of URLs to process
            user_id: User identifier for session management
        
        Returns:
            JSON with extracted structured data, metadata, and processing stats
        
        Keywords: crawl, extract, llm, structured-data, content-extraction
        Category: web-extraction
        """
        await _initialize_search_services()
        
        try:
            # Parse inputs
            url_list = json.loads(urls) if isinstance(urls, str) else urls
            if not isinstance(url_list, list):
                raise ValueError("urls must be a JSON array of URL strings")
            
            # Limit URLs
            url_list = url_list[:max_urls]
            
            logger.info(f"🕷️ Starting crawl & extract for {len(url_list)} URLs")
            
            # Get services from manager
            browser_manager = _web_service_manager.get_browser_manager()
            session_manager = _web_service_manager.get_session_manager()
            stealth_manager = _web_service_manager.get_stealth_manager()
            human_behavior = _web_service_manager.get_human_behavior()
            shared_llm_extractor = _web_service_manager.get_shared_llm_extractor()
            
            # Initialize browser services
            if not browser_manager.initialized:
                print("🔧 Initializing browser for crawling...")
                await browser_manager.initialize()
            
            # Create enhanced stealth session for crawling
            session_id = f"crawl_extract_{user_id}_{hash(str(url_list))}"
            page = await session_manager.get_or_create_session(session_id, "stealth")
            
            # Apply stealth configuration to browser context
            if stealth_manager and page.context:
                await stealth_manager.apply_stealth_context(page.context, level="high")
                print("🛡️ Enhanced stealth protection activated")
            
            # Apply human navigation behavior
            if human_behavior:
                await human_behavior.apply_human_navigation(page)
                print("👤 Human-like navigation behavior applied")
            
            # Setup extraction strategy based on schema
            if extraction_schema == "article":
                schema = PredefinedLLMSchemas.get_article_extraction_schema()
            elif extraction_schema == "product":
                schema = PredefinedLLMSchemas.get_product_extraction_schema()
            elif extraction_schema == "contact":
                schema = PredefinedLLMSchemas.get_contact_extraction_schema()
            elif extraction_schema == "event":
                schema = PredefinedLLMSchemas.get_event_extraction_schema()
            elif extraction_schema == "research":
                schema = PredefinedLLMSchemas.get_research_extraction_schema()
            else:
                # Try to parse as custom schema JSON
                try:
                    schema = json.loads(extraction_schema)
                    if not isinstance(schema, dict) or "fields" not in schema:
                        raise ValueError("Custom schema must have 'fields' key")
                except json.JSONDecodeError:
                    # Fallback to article schema
                    schema = PredefinedLLMSchemas.get_article_extraction_schema()
                    logger.warning(f"Invalid extraction_schema, using article schema")
            
            # Setup semantic filtering if query provided
            semantic_filter = None
            if filter_query.strip():
                from tools.services.web_services.strategies.filtering import SemanticFilter
                semantic_filter = SemanticFilter(
                    user_query=filter_query,
                    similarity_threshold=0.6,
                    min_chunk_length=100
                )
            
            # Process each URL
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
                    
                    # 增强的页面导航，特别针对Amazon等电商网站
                    try:
                        # 对于Amazon等敏感网站，使用增强的人类行为模拟
                        if any(site in url for site in ["amazon.com", "walmart.com", "target.com"]):
                            print(f"   🛡️ 检测到敏感电商网站，启用完整人类行为模拟...")
                            
                            # 设置更真实的headers
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
                            
                            # 使用人类行为模拟进行导航
                            await page.goto(url, wait_until='domcontentloaded', timeout=45000)
                            
                            # 人类行为：随机鼠标移动
                            if human_behavior:
                                await human_behavior.random_mouse_movement(page, movements=2)
                            
                            # 人类行为：模拟阅读页面
                            await page.wait_for_timeout(2000)  # 等待2秒模拟人类反应时间
                            
                            if human_behavior:
                                await human_behavior.simulate_reading(page, reading_time_factor=0.5)
                            
                            await page.wait_for_load_state('networkidle', timeout=15000)
                        else:
                            # 普通网站的标准导航，仍然使用人类行为增强
                            await page.goto(url, wait_until='networkidle', timeout=30000)
                            
                            # 添加少量人类行为模拟
                            if human_behavior:
                                await human_behavior.human_navigation_pause(page)
                                
                    except Exception as nav_error:
                        logger.warning(f"Navigation failed with networkidle, trying domcontentloaded: {nav_error}")
                        # 降级策略：如果networkidle失败，使用domcontentloaded
                        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        
                        # 即使在降级模式下也添加人类行为
                        if human_behavior:
                            await human_behavior.random_delay(2000, 4000)
                    
                    # 根据schema决定使用共享实例还是创建新实例
                    if extraction_schema == "article" and shared_llm_extractor:
                        # 使用共享LLM实例 (article schema)
                        page_data = await shared_llm_extractor.extract(page, "")
                    else:
                        # 创建专用LLM实例 (其他schema)
                        from tools.services.web_services.strategies.extraction import LLMExtractionStrategy
                        llm_extractor = LLMExtractionStrategy(schema)
                        page_data = await llm_extractor.extract(page, "")
                        await llm_extractor.close()
                    
                    # Apply semantic filtering if configured
                    if semantic_filter and page_data:
                        # Filter each extracted item's content
                        filtered_data = []
                        for item in page_data:
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
                        page_data = filtered_data
                    
                    # Add metadata to extracted items
                    if page_data:
                        for item in page_data:
                            item.update({
                                "source_url": url,
                                "extraction_timestamp": datetime.now().isoformat(),
                                "extraction_schema": schema.get("name", "custom"),
                                "extraction_index": i
                            })
                        
                        all_extracted_data.extend(page_data)
                        processing_stats["successful_extractions"] += 1
                        processing_stats["total_items_extracted"] += len(page_data)
                        
                        logger.info(f"✅ Extracted {len(page_data)} items from {url}")
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
            
            # Collect billing information from services
            total_billing = {
                "total_cost_usd": 0.0,
                "service_breakdown": {},
                "operations_count": 0
            }
            
            # Add LLM extraction billing
            if shared_llm_extractor and hasattr(shared_llm_extractor, 'get_service_billing_info'):
                extraction_billing = shared_llm_extractor.get_service_billing_info()
                if extraction_billing:
                    total_billing["total_cost_usd"] += extraction_billing.get("total_cost_usd", 0.0)
                    total_billing["service_breakdown"]["llm_extraction"] = extraction_billing
                    total_billing["operations_count"] += extraction_billing.get("operation_count", 0)
            
            # Add semantic filter billing
            if semantic_filter and hasattr(semantic_filter, 'get_service_billing_info'):
                filter_billing = semantic_filter.get_service_billing_info()
                if filter_billing:
                    total_billing["total_cost_usd"] += filter_billing.get("total_cost_usd", 0.0)
                    total_billing["service_breakdown"]["semantic_filter"] = filter_billing
                    total_billing["operations_count"] += filter_billing.get("operation_count", 0)
            
            # Clean up semantic filter
            if semantic_filter:
                await semantic_filter.close()
            
            # Calculate average processing time
            avg_processing_time = (
                sum(processing_stats["processing_times"]) / len(processing_stats["processing_times"])
                if processing_stats["processing_times"] else 0
            )
            
            response = {
                "status": "success",
                "action": "crawl_and_extract",
                "workflow_step": "step_3_crawl_extract",
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
                        "success_rate": round(processing_stats["successful_extractions"] / processing_stats["total_urls"] * 100, 1) if processing_stats["total_urls"] > 0 else 0
                    }
                },
                "billing": total_billing,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Crawl & extract completed: {processing_stats['total_items_extracted']} items from {processing_stats['successful_extractions']}/{processing_stats['total_urls']} URLs")
            return json.dumps(response, indent=2)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "crawl_and_extract",
                "error": f"Crawl & extract failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"❌ Crawl & extract failed: {e}")
            return json.dumps(result, indent=2)
    
    @mcp.tool()
    # @base_tool.security_manager.security_check  # Disabled for testing
    async def synthesize_and_generate(
        extracted_data: str,  # JSON array of extracted data items
        query: str = "",  # Original search query for context
        output_format: str = "markdown",  # "markdown", "json", "summary", "report"
        analysis_depth: str = "medium",  # "basic", "medium", "deep"
        max_items: int = 50,
        user_id: str = "default"
    ) -> str:
        """Step 4: Synthesize extracted data and generate intelligent reports
        
        This implements the fourth step of our 4-step web workflow:
        Synthesis & Generate → Create intelligent summaries and insights
        
        Features:
        1. Data Aggregation - Merge and deduplicate extracted content
        2. Intelligent Analysis - LLM-powered insights and patterns
        3. Multi-format Output - Markdown, JSON, summaries, reports
        4. Content Ranking - Sort by relevance and importance
        
        Args:
            extracted_data: JSON array of extracted data items from crawl_and_extract
            query: Original search query to provide context for analysis
            output_format: Format for output ("markdown", "json", "summary", "report")
            analysis_depth: Level of analysis ("basic", "medium", "deep")
            max_items: Maximum number of items to process
            user_id: User identifier for session management
        
        Returns:
            JSON with synthesized content, analysis, and formatted output
        
        Keywords: synthesis, analysis, report, insights, aggregation
        Category: web-synthesis
        """
        await _initialize_search_services()
        
        try:
            # Parse input data
            data_items = json.loads(extracted_data) if isinstance(extracted_data, str) else extracted_data
            if not isinstance(data_items, list):
                raise ValueError("extracted_data must be a JSON array of data items")
            
            # Limit items for processing
            data_items = data_items[:max_items]
            
            logger.info(f"🧠 Starting synthesis & generation for {len(data_items)} items")
            
            # Import synthesis components
            from tools.services.web_services.strategies.filtering import SemanticFilter
            from tools.services.web_services.strategies.generation import MarkdownGenerator
            from core.isa_client import get_isa_client
            
            # 1. DATA AGGREGATION
            print("📊 Step 1: Data Aggregation & Deduplication")
            aggregated_data = await _aggregate_and_deduplicate(data_items, query)
            print(f"   ✅ Aggregated {len(aggregated_data)} unique items")
            
            # 2. INTELLIGENT ANALYSIS
            print("🧠 Step 2: Intelligent Analysis")
            analysis_results = await _perform_intelligent_analysis(
                aggregated_data, query, analysis_depth
            )
            print(f"   ✅ Analysis completed with {len(analysis_results.get('insights', []))} insights")
            
            # 3. MULTI-FORMAT OUTPUT
            print("📝 Step 3: Multi-format Output Generation")
            formatted_output = await _generate_formatted_output(
                aggregated_data, analysis_results, output_format, query
            )
            print(f"   ✅ Generated {output_format} format output")
            
            # 4. CONTENT RANKING
            print("🎯 Step 4: Content Ranking & Prioritization")
            ranked_content = await _rank_and_prioritize_content(
                aggregated_data, analysis_results, query
            )
            print(f"   ✅ Ranked {len(ranked_content)} content items")
            
            # Collect billing information
            total_billing = {
                "total_cost_usd": 0.0,
                "service_breakdown": {},
                "operations_count": 0
            }
            
            # Add analysis billing
            analysis_billing = analysis_results.get('billing_info', {})
            if analysis_billing:
                total_billing["total_cost_usd"] += analysis_billing.get("total_cost_usd", 0.0)
                total_billing["service_breakdown"]["intelligent_analysis"] = analysis_billing
                total_billing["operations_count"] += analysis_billing.get("operation_count", 0)
            
            # Compile final response
            response = {
                "status": "success",
                "action": "synthesize_and_generate",
                "workflow_step": "step_4_synthesis_generate",
                "data": {
                    "synthesis_summary": {
                        "original_items_count": len(data_items),
                        "aggregated_items_count": len(aggregated_data),
                        "analysis_depth": analysis_depth,
                        "output_format": output_format,
                        "query_context": query
                    },
                    "aggregated_data": aggregated_data,
                    "analysis_results": analysis_results,
                    "formatted_output": formatted_output,
                    "ranked_content": ranked_content,
                    "metadata": {
                        "processing_timestamp": datetime.now().isoformat(),
                        "user_id": user_id,
                        "synthesis_method": "llm_powered_analysis"
                    }
                },
                "billing": total_billing,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Synthesis & generation completed successfully")
            return json.dumps(response, indent=2)
            
        except Exception as e:
            result = {
                "status": "error",
                "action": "synthesize_and_generate",
                "error": f"Synthesis & generation failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"❌ Synthesis & generation failed: {e}")
            return json.dumps(result, indent=2)
    
    @mcp.tool()
    # @base_tool.security_manager.security_check  # Disabled for testing
    async def web_search(
        query: str,
        mode: str = "simple",  # "simple", "deep", or "automation"
        task_type: str = "general",  # "general", "site_search", "link_filter", "form_automation", "data_collection"
        automation_config: str = "{}",  # JSON: automation-specific configuration
        max_results: int = 10,
        providers: str = '["brave"]',  # JSON array
        filters: str = "{}",  # JSON: {"language": "en", "freshness": "week", etc.}
        user_id: str = "default"
    ) -> str:
        """Enhanced web search with three modes: simple, deep, and automation
        
        Simple Mode:
        - Direct Brave API response with URLs and metadata
        - Fast, lightweight, perfect for basic searches
        - Returns: URLs, titles, snippets, metadata (age, language, etc.)
        
        Deep Mode:
        - Full 4-step workflow: Search → Automation → Extract → Synthesize
        - Crawls pages, extracts structured data, applies AI analysis
        - Returns: Rich extracted content, analysis, and insights
        
        Automation Mode:
        - Advanced automation with task-specific behaviors
        - Supports: site_search, link_filter, form_automation, data_collection
        - Uses AI element detection and human behavior simulation
        - Returns: Task-specific results with automation metadata
        
        Args:
            query: Search query or automation target
            mode: "simple" (API), "deep" (workflow), or "automation" (advanced)
            task_type: Task for automation mode ("general", "site_search", "link_filter", "form_automation", "data_collection")
            automation_config: JSON config for automation tasks (site URLs, filter criteria, etc.)
            max_results: Number of results to return
            providers: JSON array of providers ["brave", "google", "bing"]
            filters: JSON object with search filters
            user_id: User identifier for session management
        
        Keywords: search, web, api, brave, deep, automation, ai-enhanced
        Category: web-search
        """
        await _initialize_search_services()
        
        if _web_service_manager is None:
            raise Exception("Web service manager not initialized")
        
        try:
            # Parse inputs
            providers_list = json.loads(providers) if providers else ["brave"]
            filter_config = json.loads(filters) if filters else {}
            
            # Convert providers to enums
            search_providers = []
            for p in providers_list:
                if p.lower() == "brave":
                    search_providers.append(SearchProvider.BRAVE)
                # Add other providers when available
            
            if not search_providers:
                search_providers = [SearchProvider.BRAVE]
            
            logger.info(f"🔍 Web search ({mode} mode): '{query}' using {[p.value for p in search_providers]}")
            
            if mode.lower() == "simple":
                return await _simple_search(query, search_providers, max_results, filter_config)
            elif mode.lower() == "deep":
                return await _deep_search(query, search_providers, max_results, filter_config, user_id, task_type)
            elif mode.lower() == "automation":
                automation_config_dict = json.loads(automation_config) if automation_config else {}
                return await _automation_search(query, search_providers, max_results, filter_config, user_id, task_type, automation_config_dict)
            else:
                raise ValueError(f"Invalid mode: {mode}. Use 'simple', 'deep', or 'automation'")
                
        except Exception as e:
            result = {
                "status": "error",
                "action": "web_search",
                "mode": mode,
                "error": f"Search failed: {str(e)}",
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"❌ Web search failed: {e}")
            return json.dumps(result)

async def _simple_search(query: str, providers: List[SearchProvider], max_results: int, filters: Dict) -> str:
    """Simple mode: Direct Brave API response"""
    try:
        # Get services from manager
        rate_limiter = _web_service_manager.get_rate_limiter()
        search_engine = _web_service_manager.get_search_engine()
        
        # Apply rate limiting
        await rate_limiter.wait_for_rate_limit(f"search_{providers[0].value}")
        
        # Execute search with filters
        search_params = {"count": max_results}
        search_params.update(filters)
        
        if len(providers) == 1:
            search_results = await search_engine.search(
                query=query,
                provider=providers[0],
                **search_params
            )
        else:
            multi_results = await search_engine.multi_search(
                query=query,
                providers=providers,
                **search_params
            )
            search_results = await search_engine.aggregate_results(multi_results, deduplicate=True)
        
        # Convert to simple response format
        results_data = []
        for result in search_results[:max_results]:
            result_dict = result.to_dict()
            results_data.append({
                "title": result_dict.get("title", ""),
                "url": result_dict.get("url", ""),
                "snippet": result_dict.get("snippet", ""),
                "metadata": result_dict.get("metadata", {})
            })
        
        response = {
            "status": "success",
            "action": "web_search",
            "mode": "simple",
            "data": {
                "query": query,
                "results": results_data,
                "total_results": len(results_data),
                "providers_used": [p.value for p in providers],
                "search_method": "direct_api"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Simple search completed: {len(results_data)} results")
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"❌ Simple search failed: {e}")
        raise

async def _deep_search(query: str, providers: List[SearchProvider], max_results: int, filters: Dict, user_id: str, task_type: str = "general") -> str:
    """Deep mode: True intelligent automation with site-specific searches"""
    try:
        # Get services from manager
        browser_manager = _web_service_manager.get_browser_manager()
        session_manager = _web_service_manager.get_session_manager()
        search_engine = _web_service_manager.get_search_engine()
        element_detector = _web_service_manager.get_service('element_detector')
        
        # Initialize browser services for deep mode
        if not browser_manager.initialized:
            print("🔧 Initializing browser for deep search...")
            await browser_manager.initialize()
        
        logger.info("🚀 Starting TRUE deep search with intelligent automation...")
        
        # PHASE 1: Initial Search & Filter
        print("📋 Phase 1: Initial Search & Intelligent Filtering")
        search_params = {"count": min(max_results, 10)}  # Respect Brave API limits
        search_params.update(filters)
        
        if len(providers) == 1:
            search_results = await search_engine.search(
                query=query,
                provider=providers[0],
                **search_params
            )
        else:
            multi_results = await search_engine.multi_search(
                query=query,
                providers=providers,
                **search_params
            )
            search_results = await search_engine.aggregate_results(multi_results, deduplicate=True)
        
        initial_results = [result.to_dict() for result in search_results[:max_results//2]]  # Save half for site-specific
        print(f"   ✅ Found {len(initial_results)} initial results")
        
        # PHASE 2: Site-Specific Intelligent Automation
        print("🤖 Phase 2: Site-Specific Intelligent Automation")
        site_specific_results = []
        
        # Define target sites for deep search
        target_sites = [
            {"name": "Reddit", "url": "https://www.reddit.com", "search_path": "/search"},
            {"name": "Twitter", "url": "https://twitter.com", "search_path": "/search"},
        ]
        
        session_id = f"deep_automation_{user_id}_{hash(query)}"
        page = await session_manager.get_or_create_session(session_id, "stealth")
        
        for site in target_sites[:2]:  # Limit to 2 sites to avoid timeout
            try:
                print(f"   🌐 Automating search on {site['name']}...")
                
                # Navigate to the site
                await page.goto(site['url'], wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)  # Wait for page to load
                
                # Use intelligent element detection to find search elements
                print(f"   🧠 Detecting search elements on {site['name']}...")
                search_elements = await element_detector.detect_search_elements(
                    page, 
                    target_elements=['search_input', 'search_button']
                )
                
                if 'search_input' in search_elements:
                    search_input = search_elements['search_input']
                    print(f"   🎯 Found search input at ({search_input.x}, {search_input.y})")
                    
                    # Perform automated search
                    await page.mouse.click(search_input.x, search_input.y)
                    await page.wait_for_timeout(500)
                    
                    # Clear and type query
                    await page.keyboard.press('Control+a')
                    await page.keyboard.type(query)
                    await page.wait_for_timeout(500)
                    
                    # Submit search
                    if 'search_button' in search_elements:
                        search_button = search_elements['search_button']
                        await page.mouse.click(search_button.x, search_button.y)
                    else:
                        await page.keyboard.press('Enter')
                    
                    # Wait for results and detect links
                    await page.wait_for_timeout(3000)
                    print(f"   🔗 Detecting result links on {site['name']}...")
                    
                    link_elements = await element_detector.detect_link_elements(
                        page,
                        target_links=['product_links', 'navigation_links']
                    )
                    
                    # Extract links from detected elements
                    for link_name, link_result in link_elements.items():
                        if link_result.metadata.get('href'):
                            site_specific_results.append({
                                'title': link_result.metadata.get('text', f"{site['name']} result"),
                                'url': link_result.metadata.get('href'),
                                'snippet': link_result.description,
                                'source': site['name'],
                                'automation_confidence': link_result.confidence,
                                'detection_strategy': link_result.strategy.value
                            })
                    
                    print(f"   ✅ Automated {site['name']} search: {len([r for r in site_specific_results if r['source'] == site['name']])} results")
                    
                else:
                    print(f"   ⚠️ Could not find search input on {site['name']}")
                    
            except Exception as site_error:
                print(f"   ❌ {site['name']} automation failed: {site_error}")
                logger.warning(f"Site automation failed for {site['name']}: {site_error}")
        
        # Combine initial and site-specific results
        all_results = initial_results + site_specific_results
        step1_results = all_results[:max_results]
        print(f"   ✅ Combined results: {len(step1_results)} total ({len(initial_results)} API + {len(site_specific_results)} automated)")
        
        # STEP 2: Web Automation (Navigate to pages)
        print("🤖 Step 2: Web Automation")
        session_id = f"deep_search_{user_id}_{hash(query)}"
        page = await session_manager.get_or_create_session(session_id, "stealth")
        
        # STEP 3: Crawl & Extract
        print("🕷️ Step 3: Crawl & Extract")
        extracted_data = []
        
        for i, result in enumerate(step1_results[:5]):  # Limit deep extraction to top 5
            try:
                url = result.get("url", "")
                if not url:
                    continue
                    
                print(f"   🔍 Extracting from: {url}")
                await page.goto(url, wait_until='networkidle')
                
                # Use LLM extraction for structured data
                from tools.services.web_services.strategies.extraction import LLMExtractionStrategy
                schema = PredefinedLLMSchemas.get_article_extraction_schema()
                llm_extractor = LLMExtractionStrategy(schema)
                
                page_data = await llm_extractor.extract(page, "")
                await llm_extractor.close()
                
                if page_data:
                    extracted_data.extend([{
                        **item,
                        "source_url": url,
                        "source_title": result.get("title", ""),
                        "extraction_index": i
                    } for item in page_data])
                
            except Exception as e:
                logger.warning(f"Failed to extract from {url}: {e}")
                continue
        
        print(f"   ✅ Extracted {len(extracted_data)} structured items")
        
        # STEP 4: Synthesis & Generate
        print("🧠 Step 4: Synthesis & Generate")
        
        # Simple synthesis: group by type, rank by relevance
        synthesized_results = {
            "search_summary": {
                "query": query,
                "total_sources": len(step1_results),
                "extracted_sources": len([d for d in extracted_data if d]),
                "key_findings": []
            },
            "structured_data": extracted_data,
            "source_urls": [r.get("url") for r in step1_results],
            "synthesis_method": "llm_extraction_grouping"
        }
        
        # Add key findings summary
        if extracted_data:
            titles = [item.get("title", "") for item in extracted_data if item.get("title")]
            synthesized_results["search_summary"]["key_findings"] = titles[:3]
        
        print(f"   ✅ Synthesis completed")
        
        response = {
            "status": "success",
            "action": "web_search",
            "mode": "deep",
            "workflow_steps": {
                "phase1_initial_search": f"{len(initial_results)} API results",
                "phase2_site_automation": f"{len(site_specific_results)} automated results from {len(target_sites)} sites",
                "step3_extraction": f"{len(extracted_data)} structured items",
                "step4_synthesis": "intelligent aggregation completed"
            },
            "data": {
                **synthesized_results,
                "automation_details": {
                    "sites_automated": [site['name'] for site in target_sites],
                    "total_automated_results": len(site_specific_results),
                    "element_detection_used": True,
                    "intelligent_navigation": True
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Deep search workflow completed: 4 steps processed")
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"❌ Deep search failed: {e}")
        raise

async def _automation_search(query: str, providers: List[SearchProvider], max_results: int, filters: Dict, user_id: str, task_type: str, automation_config: Dict) -> str:
    """Automation mode: Advanced task-specific automation with AI-enhanced capabilities"""
    try:
        # Get services from manager
        browser_manager = _web_service_manager.get_browser_manager()
        
        # Initialize browser services for automation mode
        if not browser_manager.initialized:
            print("🔧 Initializing browser for automation search...")
            await browser_manager.initialize()
        
        logger.info(f"🤖 Starting automation search workflow - Task: {task_type}")
        
        if task_type == "site_search":
            return await _handle_site_search(query, automation_config, user_id)
        elif task_type == "link_filter":
            return await _handle_link_filter(query, automation_config, providers, max_results, filters)
        elif task_type == "form_automation":
            return await _handle_form_automation(query, automation_config, user_id)
        elif task_type == "data_collection":
            return await _handle_data_collection(query, automation_config, user_id)
        else:
            # Default to enhanced general search with automation
            return await _handle_general_automation(query, providers, max_results, filters, user_id, automation_config)
            
    except Exception as e:
        logger.error(f"❌ Automation search failed: {e}")
        result = {
            "status": "error",
            "action": "web_search",
            "mode": "automation",
            "task_type": task_type,
            "error": f"Automation search failed: {str(e)}",
            "query": query,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)

async def _handle_site_search(query: str, config: Dict, user_id: str) -> str:
    """Handle site-specific search automation (Amazon, Twitter, etc.)"""
    try:
        target_site = config.get("site", "amazon.com")
        search_type = config.get("search_type", "product")  # product, content, user, etc.
        
        print(f"🔍 Site Search: {target_site} for '{query}'")
        
        # Get services from manager
        session_manager = _web_service_manager.get_session_manager()
        stealth_manager = _web_service_manager.get_stealth_manager()
        
        # Create enhanced stealth session
        session_id = f"site_search_{user_id}_{hash(target_site + query)}"
        page = await session_manager.get_or_create_session(session_id, "stealth")
        
        # Apply stealth configuration
        if stealth_manager and page.context:
            await stealth_manager.apply_stealth_context(page.context, level="high")
        
        if "amazon" in target_site.lower():
            return await _amazon_site_search(page, query, config)
        elif "twitter" in target_site.lower():
            return await _twitter_site_search(page, query, config)
        else:
            return await _generic_site_search(page, query, config, target_site)
            
    except Exception as e:
        logger.error(f"Site search failed: {e}")
        return json.dumps({
            "status": "error",
            "task_type": "site_search",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, indent=2)

async def _handle_link_filter(query: str, config: Dict, providers: List[SearchProvider], max_results: int, filters: Dict) -> str:
    """Handle intelligent link filtering using AI and semantic analysis"""
    try:
        print(f"🔍 Smart Link Filtering for: '{query}'")
        
        # Get services from manager  
        search_engine = _web_service_manager.get_search_engine()
        
        # Get initial search results (more than needed for filtering)
        search_params = {"count": max_results * 3}  # Get more links for better filtering
        search_params.update(filters)
        
        if len(providers) == 1:
            search_results = await search_engine.search(
                query=query,
                provider=providers[0],
                **search_params
            )
        else:
            multi_results = await search_engine.multi_search(
                query=query,
                providers=providers,
                **search_params
            )
            search_results = await search_engine.aggregate_results(multi_results, deduplicate=True)
        
        # Convert to URL list for filtering
        initial_urls = [result.to_dict() for result in search_results]
        print(f"   📊 Initial results: {len(initial_urls)} links")
        
        # Apply AI-enhanced filtering
        filtered_urls = await _apply_smart_filtering(initial_urls, query, config)
        
        response = {
            "status": "success",
            "action": "web_search", 
            "mode": "automation",
            "task_type": "link_filter",
            "data": {
                "query": query,
                "original_count": len(initial_urls),
                "filtered_count": len(filtered_urls),
                "filtered_results": filtered_urls[:max_results],
                "filter_criteria": config,
                "quality_stats": {
                    "high_quality": len([u for u in filtered_urls if u.get("quality_score", 0) > 0.8]),
                    "medium_quality": len([u for u in filtered_urls if 0.5 < u.get("quality_score", 0) <= 0.8]),
                    "low_quality": len([u for u in filtered_urls if u.get("quality_score", 0) <= 0.5])
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Link filtering completed: {len(filtered_urls)} high-quality links")
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Link filtering failed: {e}")
        return json.dumps({
            "status": "error",
            "task_type": "link_filter", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, indent=2)

async def _handle_form_automation(query: str, config: Dict, user_id: str) -> str:
    """Handle form automation tasks (filling, submitting, multi-step flows)"""
    try:
        target_url = config.get("url", "")
        form_data = config.get("form_data", {})
        
        if not target_url:
            raise ValueError("URL required for form automation")
        
        print(f"📝 Form Automation: {target_url}")
        
        # Get services from manager
        element_detector = _web_service_manager.get_element_detector()
        human_behavior = _web_service_manager.get_human_behavior()
        session_manager = _web_service_manager.get_session_manager()
        
        # Create session for form automation
        session_id = f"form_automation_{user_id}_{hash(target_url)}"
        page = await session_manager.get_or_create_session(session_id, "stealth")
        
        # Navigate to target page
        await page.goto(target_url, wait_until='networkidle')
        
        # Use intelligent element detection for form elements
        if element_detector:
            form_elements = await element_detector.detect_form_elements(page)
            
            # Fill form using human behavior simulation
            for field_name, field_value in form_data.items():
                if field_name in form_elements:
                    element = form_elements[field_name]
                    if human_behavior:
                        await human_behavior.human_type(page, element, field_value)
                        await human_behavior.random_delay(500, 1500)
        
        # Extract results after form interaction
        extraction_results = []
        if config.get("extract_after_submit", True):
            schema = PredefinedLLMSchemas.get_article_extraction_schema()
            from tools.services.web_services.strategies.extraction import LLMExtractionStrategy
            llm_extractor = LLMExtractionStrategy(schema)
            extraction_results = await llm_extractor.extract(page, "")
            await llm_extractor.close()
        
        response = {
            "status": "success", 
            "task_type": "form_automation",
            "data": {
                "url": target_url,
                "form_filled": True,
                "fields_processed": list(form_data.keys()),
                "extracted_data": extraction_results
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Form automation failed: {e}")
        return json.dumps({
            "status": "error",
            "task_type": "form_automation",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, indent=2)

async def _handle_data_collection(query: str, config: Dict, user_id: str) -> str:
    """Handle systematic data collection from multiple sources"""
    try:
        urls = config.get("urls", [])
        collection_schema = config.get("schema", "article")
        
        print(f"📊 Data Collection: {len(urls)} sources")
        
        # Get services from manager
        session_manager = _web_service_manager.get_session_manager()
        human_behavior = _web_service_manager.get_human_behavior()
        
        # Use existing crawl_and_extract logic but with automation enhancements
        session_id = f"data_collection_{user_id}_{hash(str(urls))}"
        page = await session_manager.get_or_create_session(session_id, "stealth")
        
        collected_data = []
        for i, url in enumerate(urls):
            try:
                print(f"   🔍 Collecting from: {url}")
                
                # Enhanced navigation with human behavior
                await page.goto(url, wait_until='networkidle')
                if human_behavior:
                    await human_behavior.simulate_reading(page, reading_time_factor=0.3)
                
                # Extract structured data
                if collection_schema == "product":
                    schema = PredefinedLLMSchemas.get_product_extraction_schema()
                elif collection_schema == "contact":
                    schema = PredefinedLLMSchemas.get_contact_extraction_schema()
                else:
                    schema = PredefinedLLMSchemas.get_article_extraction_schema()
                
                from tools.services.web_services.strategies.extraction import LLMExtractionStrategy
                llm_extractor = LLMExtractionStrategy(schema)
                page_data = await llm_extractor.extract(page, "")
                await llm_extractor.close()
                
                if page_data:
                    for item in page_data:
                        item.update({
                            "source_url": url,
                            "collection_index": i,
                            "collection_timestamp": datetime.now().isoformat()
                        })
                    collected_data.extend(page_data)
                    
            except Exception as e:
                logger.warning(f"Failed to collect from {url}: {e}")
                continue
        
        response = {
            "status": "success",
            "task_type": "data_collection", 
            "data": {
                "query": query,
                "sources_processed": len(urls),
                "items_collected": len(collected_data),
                "collection_schema": collection_schema,
                "collected_data": collected_data
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Data collection completed: {len(collected_data)} items")
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Data collection failed: {e}")
        return json.dumps({
            "status": "error",
            "task_type": "data_collection",
            "error": str(e), 
            "timestamp": datetime.now().isoformat()
        }, indent=2)

async def _handle_general_automation(query: str, providers: List[SearchProvider], max_results: int, filters: Dict, user_id: str, config: Dict) -> str:
    """Handle general automation-enhanced search with AI filtering"""
    try:
        print(f"🤖 General Automation Search: '{query}'")
        
        # Get services from manager
        search_engine = _web_service_manager.get_search_engine()
        
        # Enhanced search with automation features
        search_params = {"count": max_results * 2}
        search_params.update(filters)
        
        # Get search results
        if len(providers) == 1:
            search_results = await search_engine.search(
                query=query,
                provider=providers[0], 
                **search_params
            )
        else:
            multi_results = await search_engine.multi_search(
                query=query,
                providers=providers,
                **search_params
            )
            search_results = await search_engine.aggregate_results(multi_results, deduplicate=True)
        
        # Convert and apply smart filtering
        initial_results = [result.to_dict() for result in search_results]
        filtered_results = await _apply_smart_filtering(initial_results, query, config)
        
        response = {
            "status": "success",
            "action": "web_search",
            "mode": "automation", 
            "task_type": "general",
            "data": {
                "query": query,
                "results": filtered_results[:max_results],
                "total_results": len(filtered_results),
                "providers_used": [p.value for p in providers],
                "automation_features": ["ai_filtering", "quality_scoring", "relevance_ranking"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"General automation failed: {e}")
        raise

async def _apply_smart_filtering(urls: List[Dict], query: str, config: Dict) -> List[Dict]:
    """Apply AI-enhanced smart filtering to URL list"""
    try:
        # Extract filter criteria from config
        relevance_threshold = config.get("relevance_threshold", 0.6)
        quality_threshold = config.get("quality_threshold", 0.5)
        exclude_patterns = config.get("exclude_patterns", ["ads", "spam"])
        prefer_domains = config.get("prefer_domains", [])
        
        filtered_urls = []
        
        for url_data in urls:
            url = url_data.get("url", "")
            title = url_data.get("title", "")
            snippet = url_data.get("snippet", "")
            
            # Basic filtering: exclude unwanted patterns
            if any(pattern in url.lower() for pattern in exclude_patterns):
                continue
            
            # Quality scoring
            quality_score = _calculate_url_quality(url, title, snippet)
            
            # Relevance scoring using simple keyword matching
            relevance_score = _calculate_relevance(query, title, snippet)
            
            # Domain preference bonus
            domain_bonus = 0.1 if any(domain in url for domain in prefer_domains) else 0
            
            # Final scoring
            final_score = (quality_score * 0.4) + (relevance_score * 0.5) + domain_bonus
            
            # Apply thresholds
            if final_score >= quality_threshold and relevance_score >= relevance_threshold:
                url_data.update({
                    "quality_score": round(quality_score, 3),
                    "relevance_score": round(relevance_score, 3), 
                    "final_score": round(final_score, 3),
                    "filter_metadata": {
                        "passed_quality": quality_score >= quality_threshold,
                        "passed_relevance": relevance_score >= relevance_threshold,
                        "domain_bonus": domain_bonus > 0
                    }
                })
                filtered_urls.append(url_data)
        
        # Sort by final score
        filtered_urls.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        
        return filtered_urls
        
    except Exception as e:
        logger.error(f"Smart filtering failed: {e}")
        return urls  # Return original if filtering fails

def _calculate_url_quality(url: str, title: str, snippet: str) -> float:
    """Calculate URL quality score based on various factors"""
    score = 0.5  # Base score
    
    # Domain credibility
    if any(domain in url for domain in [".edu", ".gov", "wikipedia.org"]):
        score += 0.3
    elif any(domain in url for domain in ["reddit.com", "stackoverflow.com", "github.com"]):
        score += 0.2
    
    # Title quality
    if len(title) > 10 and len(title) < 100:
        score += 0.1
    
    # Snippet quality  
    if len(snippet) > 50:
        score += 0.1
    
    # URL structure (fewer subdirectories often better)
    if url.count('/') <= 4:
        score += 0.1
    
    return min(score, 1.0)

def _calculate_relevance(query: str, title: str, snippet: str) -> float:
    """Calculate relevance score using keyword matching"""
    query_words = set(query.lower().split())
    title_words = set(title.lower().split())
    snippet_words = set(snippet.lower().split())
    
    # Title relevance (higher weight)
    title_matches = len(query_words.intersection(title_words))
    title_score = (title_matches / len(query_words)) * 0.7 if query_words else 0
    
    # Snippet relevance
    snippet_matches = len(query_words.intersection(snippet_words))
    snippet_score = (snippet_matches / len(query_words)) * 0.3 if query_words else 0
    
    return min(title_score + snippet_score, 1.0)

async def _amazon_site_search(page, query: str, config: Dict) -> str:
    """Amazon-specific site search automation"""
    try:
        print("🛒 Amazon Site Search")
        
        # Navigate to Amazon
        await page.goto("https://amazon.com", wait_until='domcontentloaded')
        
        # Get services from manager
        human_behavior = _web_service_manager.get_human_behavior()
        element_detector = _web_service_manager.get_element_detector()
        
        # Apply human behavior
        if human_behavior:
            await human_behavior.random_delay(1000, 2000)
        
        # Find search box using intelligent detection
        search_results = []
        if element_detector:
            elements = await element_detector.detect_elements(page, ["search box", "search input"])
            
            if elements:
                search_box = elements[0]
                # Human-like typing
                if human_behavior:
                    await human_behavior.human_type(page, search_box, query)
                    await human_behavior.human_delay(500, 1000)
                
                # Find and click search button
                search_btn_elements = await element_detector.detect_elements(page, ["search button", "submit"])
                if search_btn_elements and human_behavior:
                    await human_behavior.human_click(page, search_btn_elements[0])
                    
                # Wait for results
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Extract product links
                schema = PredefinedLLMSchemas.get_product_extraction_schema()
                from tools.services.web_services.strategies.extraction import LLMExtractionStrategy
                llm_extractor = LLMExtractionStrategy(schema)
                search_results = await llm_extractor.extract(page, "")
                await llm_extractor.close()
        
        response = {
            "status": "success",
            "task_type": "site_search",
            "site": "amazon.com",
            "data": {
                "query": query,
                "results_found": len(search_results),
                "products": search_results
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Amazon site search failed: {e}")
        raise

async def _twitter_site_search(page, query: str, config: Dict) -> str:
    """Twitter-specific site search automation"""
    try:
        print("🐦 Twitter Site Search")
        
        # Navigate to Twitter search
        search_url = f"https://twitter.com/search?q={query.replace(' ', '%20')}"
        await page.goto(search_url, wait_until='domcontentloaded')
        
        # Get services from manager
        human_behavior = _web_service_manager.get_human_behavior()
        
        # Apply human behavior
        if human_behavior:
            await human_behavior.simulate_reading(page, reading_time_factor=0.5)
        
        # Extract tweets
        schema = {
            "name": "twitter_posts",
            "content_type": "social",
            "fields": [
                {"name": "text", "type": "string", "description": "Tweet text content"},
                {"name": "author", "type": "string", "description": "Tweet author username"},
                {"name": "timestamp", "type": "string", "description": "Tweet timestamp"},
                {"name": "engagement", "type": "object", "description": "Likes, retweets, replies"}
            ]
        }
        
        from tools.services.web_services.strategies.extraction import LLMExtractionStrategy
        llm_extractor = LLMExtractionStrategy(schema)
        search_results = await llm_extractor.extract(page, "")
        await llm_extractor.close()
        
        response = {
            "status": "success", 
            "task_type": "site_search",
            "site": "twitter.com",
            "data": {
                "query": query,
                "results_found": len(search_results),
                "tweets": search_results
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Twitter site search failed: {e}")
        raise

async def _generic_site_search(page, query: str, config: Dict, site: str) -> str:
    """Generic site search for any website"""
    try:
        print(f"🌐 Generic Site Search: {site}")
        
        # Navigate to site
        base_url = site if site.startswith("http") else f"https://{site}"
        await page.goto(base_url, wait_until='domcontentloaded')
        
        # Get services from manager
        element_detector = _web_service_manager.get_element_detector()
        human_behavior = _web_service_manager.get_human_behavior()
        
        # Try to find search functionality
        search_results = []
        if element_detector:
            # Look for search elements
            elements = await element_detector.detect_elements(page, ["search", "search box", "search input"])
            
            if elements and human_behavior:
                await human_behavior.human_type(page, elements[0], query)
                
                # Look for search button
                btn_elements = await element_detector.detect_elements(page, ["search button", "submit", "go"])
                if btn_elements:
                    await human_behavior.human_click(page, btn_elements[0])
                    await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Extract results
                schema = PredefinedLLMSchemas.get_article_extraction_schema()
                from tools.services.web_services.strategies.extraction import LLMExtractionStrategy
                llm_extractor = LLMExtractionStrategy(schema)
                search_results = await llm_extractor.extract(page, "")
                await llm_extractor.close()
        
        response = {
            "status": "success",
            "task_type": "site_search", 
            "site": site,
            "data": {
                "query": query,
                "results_found": len(search_results),
                "content": search_results
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"Generic site search failed: {e}")
        raise

async def _aggregate_and_deduplicate(data_items: List[Dict], query: str) -> List[Dict]:
    """Aggregate and deduplicate extracted data items"""
    try:
        # Group items by source URL and content similarity
        url_groups = {}
        
        for item in data_items:
            url = item.get('source_url', 'unknown')
            if url not in url_groups:
                url_groups[url] = []
            url_groups[url].append(item)
        
        # Deduplicate within each URL group
        aggregated = []
        for url, items in url_groups.items():
            # Remove exact duplicates based on title/content
            seen_content = set()
            for item in items:
                content_hash = hash(f"{item.get('title', '')}{item.get('content', '')[:200]}")
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    # Add aggregation metadata
                    item['aggregation_info'] = {
                        'group_url': url,
                        'duplicates_removed': len(items) - len(seen_content),
                        'aggregation_timestamp': datetime.now().isoformat()
                    }
                    aggregated.append(item)
        
        return aggregated
        
    except Exception as e:
        logger.error(f"Data aggregation failed: {e}")
        return data_items  # Return original if aggregation fails

async def _perform_intelligent_analysis(data_items: List[Dict], query: str, analysis_depth: str) -> Dict:
    """Perform LLM-powered intelligent analysis on aggregated data"""
    try:
        from tools.base_service import BaseService
        
        # Prepare analysis prompt based on depth
        if analysis_depth == "basic":
            analysis_prompt = f"""Analyze this web data for query '{query}'. Provide:
1. Key themes (max 3)
2. Main findings (max 3)
3. Data quality assessment

Data: {json.dumps(data_items[:10], indent=2)[:2000]}..."""
        elif analysis_depth == "deep":
            analysis_prompt = f"""Deep analysis of web data for query '{query}'. Provide:
1. Detailed theme analysis with evidence
2. Key insights and patterns
3. Content quality and credibility assessment
4. Potential biases or limitations
5. Actionable recommendations
6. Data gaps identified

Data: {json.dumps(data_items[:20], indent=2)[:4000]}..."""
        else:  # medium
            analysis_prompt = f"""Medium-depth analysis of web data for query '{query}'. Provide:
1. Theme identification (max 5)
2. Key insights with supporting evidence
3. Data quality assessment
4. Notable patterns or trends
5. Summary recommendations

Data: {json.dumps(data_items[:15], indent=2)[:3000]}..."""
        
        # Create temporary service for analysis
        analysis_service = BaseService("WebAnalysisService")
        result_data, billing_info = await analysis_service.call_isa_with_billing(
            input_data=analysis_prompt,
            task="chat",
            service_type="text",
            parameters={"temperature": 0.1},
            operation_name="intelligent_analysis"
        )
        
        analysis_response = result_data.get('text', '') if isinstance(result_data, dict) else str(result_data)
        
        # Parse analysis into structured format
        analysis_results = {
            'query_context': query,
            'analysis_depth': analysis_depth,
            'raw_analysis': str(analysis_response),
            'insights': [],
            'themes': [],
            'quality_score': 0.8,  # Default score
            'metadata': {
                'items_analyzed': len(data_items),
                'analysis_timestamp': datetime.now().isoformat()
            },
            'billing_info': analysis_service.get_billing_summary()
        }
        
        # Extract insights and themes from raw analysis
        analysis_text = analysis_results['raw_analysis']
        if 'themes' in analysis_text.lower():
            # Simple extraction - in production this would be more sophisticated
            lines = analysis_text.split('\n')
            for line in lines:
                if any(keyword in line.lower() for keyword in ['theme', 'insight', 'finding']):
                    clean_line = line.strip('- ').strip()
                    if len(clean_line) > 10:
                        if 'theme' in line.lower():
                            analysis_results['themes'].append(clean_line)
                        else:
                            analysis_results['insights'].append(clean_line)
        
        return analysis_results
        
    except Exception as e:
        logger.error(f"Intelligent analysis failed: {e}")
        return {
            'query_context': query,
            'analysis_depth': analysis_depth,
            'raw_analysis': f'Analysis failed: {str(e)}',
            'insights': ['Analysis could not be completed due to technical issues'],
            'themes': ['Error in analysis'],
            'quality_score': 0.0,
            'metadata': {
                'items_analyzed': len(data_items),
                'analysis_timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
        }

async def _generate_formatted_output(data_items: List[Dict], analysis_results: Dict, output_format: str, query: str) -> str:
    """Generate formatted output in the specified format"""
    try:
        if output_format == "markdown":
            # Generate comprehensive markdown report
            markdown_content = f"""# Web Research Report: {query}

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Executive Summary

{analysis_results.get('raw_analysis', 'No analysis available')[:500]}...

## Key Insights

"""            
            for i, insight in enumerate(analysis_results.get('insights', [])[:5], 1):
                markdown_content += f"{i}. {insight}\n"
            
            markdown_content += "\n## Data Sources\n\n"
            
            for i, item in enumerate(data_items[:10], 1):
                title = item.get('title', 'Untitled')
                url = item.get('source_url', '#')
                content_preview = item.get('content', '')[:150] + "..." if item.get('content') else "No content"
                markdown_content += f"### {i}. [{title}]({url})\n\n{content_preview}\n\n"
            
            markdown_content += f"\n---\n*Report generated from {len(data_items)} data sources*"
            return markdown_content
            
        elif output_format == "json":
            # Structured JSON output
            return json.dumps({
                'report_metadata': {
                    'query': query,
                    'generation_time': datetime.now().isoformat(),
                    'total_sources': len(data_items),
                    'format': 'json'
                },
                'analysis': analysis_results,
                'data_sources': data_items
            }, indent=2)
            
        elif output_format == "summary":
            # Concise summary format
            summary = f"Research Summary for '{query}'\n\n"
            summary += f"Analysis: {analysis_results.get('raw_analysis', 'No analysis')[:300]}...\n\n"
            summary += f"Key Sources ({len(data_items)}): \n"
            
            for item in data_items[:5]:
                title = item.get('title', 'Untitled')[:50]
                summary += f"- {title}\n"
            
            return summary
            
        elif output_format == "report":
            # Detailed report format
            report = f"COMPREHENSIVE RESEARCH REPORT\n"
            report += f"Query: {query}\n"
            report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += f"Sources Analyzed: {len(data_items)}\n"
            report += "="*60 + "\n\n"
            
            report += "ANALYSIS RESULTS:\n"
            report += analysis_results.get('raw_analysis', 'No analysis available') + "\n\n"
            
            report += "DETAILED SOURCE DATA:\n"
            for i, item in enumerate(data_items, 1):
                title = item.get('title', 'Untitled')
                url = item.get('source_url', 'No URL')
                content = item.get('content', 'No content')[:500]
                report += f"\n{i}. {title}\nURL: {url}\nContent: {content}...\n"
                if i >= 15:  # Limit to 15 items in report
                    break
            
            return report
            
        else:
            # Default to simple text format
            return f"Research results for '{query}': {len(data_items)} sources analyzed. {analysis_results.get('raw_analysis', 'No analysis')[:200]}..."
            
    except Exception as e:
        logger.error(f"Output generation failed: {e}")
        return f"Output generation failed: {str(e)}"

async def _rank_and_prioritize_content(data_items: List[Dict], analysis_results: Dict, query: str) -> List[Dict]:
    """Rank and prioritize content based on relevance and quality"""
    try:
        # Create scoring criteria
        ranked_items = []
        
        for item in data_items:
            score = 0.0
            
            # 1. Query relevance in title (weight: 30%)
            title = item.get('title', '').lower()
            query_words = query.lower().split()
            title_matches = sum(1 for word in query_words if word in title)
            title_score = (title_matches / len(query_words)) * 0.3 if query_words else 0
            score += title_score
            
            # 2. Content quality (weight: 25%)
            content = item.get('content', '')
            content_score = min(len(content) / 1000, 1.0) * 0.25  # Longer content scores higher (up to 1000 chars)
            score += content_score
            
            # 3. Source credibility (weight: 20%)
            url = item.get('source_url', '')
            credibility_score = 0.2  # Default
            if any(domain in url for domain in ['wikipedia.org', 'edu', 'gov']):
                credibility_score = 0.2
            elif any(domain in url for domain in ['reddit.com', 'stackoverflow.com']):
                credibility_score = 0.15
            score += credibility_score
            
            # 4. Extraction quality (weight: 15%)
            extraction_schema = item.get('extraction_schema', '')
            extraction_score = 0.15 if extraction_schema else 0.1
            score += extraction_score
            
            # 5. Recency bonus (weight: 10%)
            timestamp = item.get('extraction_timestamp', '')
            recency_score = 0.1 if timestamp else 0.05
            score += recency_score
            
            # Add ranking metadata
            ranked_item = item.copy()
            ranked_item['ranking_info'] = {
                'total_score': round(score, 3),
                'title_relevance': round(title_score, 3),
                'content_quality': round(content_score, 3),
                'source_credibility': round(credibility_score, 3),
                'extraction_quality': round(extraction_score, 3),
                'recency_bonus': round(recency_score, 3),
                'ranking_timestamp': datetime.now().isoformat()
            }
            
            ranked_items.append(ranked_item)
        
        # Sort by score (descending)
        ranked_items.sort(key=lambda x: x['ranking_info']['total_score'], reverse=True)
        
        # Add final rank positions
        for i, item in enumerate(ranked_items):
            item['ranking_info']['final_rank'] = i + 1
        
        return ranked_items
        
    except Exception as e:
        logger.error(f"Content ranking failed: {e}")
        return data_items  # Return original if ranking fails