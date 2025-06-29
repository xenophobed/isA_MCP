#!/usr/bin/env python
"""
Web Tools for MCP Server
Simple and powerful web search with two modes: simple (direct API) and deep (full workflow)
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.config import get_settings

# Essential imports for search functionality
from tools.services.web_services.engines.search_engine import SearchEngine, SearchProvider, BraveSearchStrategy
from tools.services.web_services.core.browser_manager import BrowserManager
from tools.services.web_services.core.session_manager import SessionManager
from tools.services.web_services.core.stealth_manager import StealthManager
from tools.services.web_services.engines.extraction_engine import ExtractionEngine
from tools.services.web_services.strategies.extraction import LLMExtractionStrategy, PredefinedLLMSchemas
from tools.services.web_services.strategies.filtering import SemanticFilter
from tools.services.web_services.utils.rate_limiter import RateLimiter
from tools.services.web_services.utils.human_behavior import HumanBehavior

logger = get_logger(__name__)

# Global instances
_search_engine: Optional[SearchEngine] = None
_browser_manager: Optional[BrowserManager] = None
_session_manager: Optional[SessionManager] = None
_stealth_manager: Optional[StealthManager] = None
_human_behavior: Optional[HumanBehavior] = None
_extraction_engine: Optional[ExtractionEngine] = None
_rate_limiter: Optional[RateLimiter] = None
_shared_llm_extractor: Optional[LLMExtractionStrategy] = None  # 共享LLM实例

async def _initialize_search_services():
    """Initialize only essential search services"""
    global _search_engine, _browser_manager, _session_manager, _stealth_manager, _human_behavior, _extraction_engine, _rate_limiter, _shared_llm_extractor
    
    try:
        if _search_engine is None:
            print("🔧 Initializing web search services...")
            
            # Core search engine
            _search_engine = SearchEngine()
            print("✅ SearchEngine created")
            
            # Add Brave search strategy using config manager
            settings = get_settings()
            brave_api_key = settings.brave_api_key
            if brave_api_key:
                brave_strategy = BraveSearchStrategy(brave_api_key)
                _search_engine.register_strategy(SearchProvider.BRAVE, brave_strategy)
                print(f"✅ Brave search strategy registered with key: {brave_api_key[:8]}...")
            else:
                print("⚠️ BRAVE_TOKEN not found in configuration (.env file)")
            
            # Only initialize browser/extraction for deep mode (lazy loading)
            _browser_manager = BrowserManager()
            _session_manager = SessionManager()
            _stealth_manager = StealthManager()
            _human_behavior = HumanBehavior()
            _extraction_engine = ExtractionEngine()
            _rate_limiter = RateLimiter()
            
            # 初始化共享LLM提取器
            article_schema = PredefinedLLMSchemas.get_article_extraction_schema()
            _shared_llm_extractor = LLMExtractionStrategy(article_schema)
            
            print("✅ Deep search components ready (will initialize on first use)")
            print("✅ Stealth Manager and Human Behavior initialized")
            print("✅ Shared LLM extractor initialized")
            
            logger.info("Web search services initialized")
        else:
            print("ℹ️ Web search services already initialized")
            
    except Exception as e:
        print(f"❌ Failed to initialize web search services: {e}")
        raise

def register_web_tools(mcp):
    """Register web search and extraction tools with the MCP server"""
    
    security_manager = get_security_manager()
    
    @mcp.tool()
    # @security_manager.security_check  # Disabled for testing
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
            
            # Initialize browser services
            if not _browser_manager.initialized:
                print("🔧 Initializing browser for crawling...")
                await _browser_manager.initialize()
            
            # Create enhanced stealth session for crawling
            session_id = f"crawl_extract_{user_id}_{hash(str(url_list))}"
            page = await _session_manager.get_or_create_session(session_id, "stealth")
            
            # Apply stealth configuration to browser context
            if _stealth_manager and page.context:
                await _stealth_manager.apply_stealth_context(page.context, level="high")
                print("🛡️ Enhanced stealth protection activated")
            
            # Apply human navigation behavior
            if _human_behavior:
                await _human_behavior.apply_human_navigation(page)
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
                            if _human_behavior:
                                await _human_behavior.random_mouse_movement(page, movements=2)
                            
                            # 人类行为：模拟阅读页面
                            await page.wait_for_timeout(2000)  # 等待2秒模拟人类反应时间
                            
                            if _human_behavior:
                                await _human_behavior.simulate_reading(page, reading_time_factor=0.5)
                            
                            await page.wait_for_load_state('networkidle', timeout=15000)
                        else:
                            # 普通网站的标准导航，仍然使用人类行为增强
                            await page.goto(url, wait_until='networkidle', timeout=30000)
                            
                            # 添加少量人类行为模拟
                            if _human_behavior:
                                await _human_behavior.human_navigation_pause(page)
                                
                    except Exception as nav_error:
                        logger.warning(f"Navigation failed with networkidle, trying domcontentloaded: {nav_error}")
                        # 降级策略：如果networkidle失败，使用domcontentloaded
                        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        
                        # 即使在降级模式下也添加人类行为
                        if _human_behavior:
                            await _human_behavior.random_delay(2000, 4000)
                    
                    # 根据schema决定使用共享实例还是创建新实例
                    if extraction_schema == "article" and _shared_llm_extractor:
                        # 使用共享LLM实例 (article schema)
                        page_data = await _shared_llm_extractor.extract(page, "")
                    else:
                        # 创建专用LLM实例 (其他schema)
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
    # @security_manager.security_check  # Disabled for testing
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
            from isa_model.inference import AIFactory
            
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
    # @security_manager.security_check  # Disabled for testing
    async def web_search(
        query: str,
        mode: str = "simple",  # "simple" or "deep"
        max_results: int = 10,
        providers: str = '["brave"]',  # JSON array
        filters: str = "{}",  # JSON: {"language": "en", "freshness": "week", etc.}
        user_id: str = "default"
    ) -> str:
        """Web search with two modes: simple (direct API) and deep (full workflow)
        
        Simple Mode:
        - Direct Brave API response with URLs and metadata
        - Fast, lightweight, perfect for basic searches
        - Returns: URLs, titles, snippets, metadata (age, language, etc.)
        
        Deep Mode:
        - Full 4-step workflow: Search → Automation → Extract → Synthesize
        - Crawls pages, extracts structured data, applies AI analysis
        - Returns: Rich extracted content, analysis, and insights
        
        Args:
            query: Search query
            mode: "simple" (direct API) or "deep" (full workflow)
            max_results: Number of results to return
            providers: JSON array of providers ["brave", "google", "bing"]
            filters: JSON object with search filters
            user_id: User identifier for session management
        
        Keywords: search, web, api, brave, deep, workflow, extraction
        Category: web-search
        """
        await _initialize_search_services()
        
        if _search_engine is None:
            raise Exception("Search engine not initialized")
        
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
                return await _deep_search(query, search_providers, max_results, filter_config, user_id)
            else:
                raise ValueError(f"Invalid mode: {mode}. Use 'simple' or 'deep'")
                
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
        # Apply rate limiting
        await _rate_limiter.wait_for_rate_limit(f"search_{providers[0].value}")
        
        # Execute search with filters
        search_params = {"count": max_results}
        search_params.update(filters)
        
        if len(providers) == 1:
            search_results = await _search_engine.search(
                query=query,
                provider=providers[0],
                **search_params
            )
        else:
            multi_results = await _search_engine.multi_search(
                query=query,
                providers=providers,
                **search_params
            )
            search_results = await _search_engine.aggregate_results(multi_results, deduplicate=True)
        
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

async def _deep_search(query: str, providers: List[SearchProvider], max_results: int, filters: Dict, user_id: str) -> str:
    """Deep mode: Full 4-step workflow implementation"""
    try:
        # Initialize browser services for deep mode
        if not _browser_manager.initialized:
            print("🔧 Initializing browser for deep search...")
            await _browser_manager.initialize()
        
        logger.info("🚀 Starting 4-step deep search workflow...")
        
        # STEP 1: Search & Filter
        print("📋 Step 1: Search & Filter")
        search_params = {"count": max_results * 2}  # Get more for filtering
        search_params.update(filters)
        
        if len(providers) == 1:
            search_results = await _search_engine.search(
                query=query,
                provider=providers[0],
                **search_params
            )
        else:
            multi_results = await _search_engine.multi_search(
                query=query,
                providers=providers,
                **search_params
            )
            search_results = await _search_engine.aggregate_results(multi_results, deduplicate=True)
        
        step1_results = [result.to_dict() for result in search_results[:max_results]]
        print(f"   ✅ Found {len(step1_results)} filtered results")
        
        # STEP 2: Web Automation (Navigate to pages)
        print("🤖 Step 2: Web Automation")
        session_id = f"deep_search_{user_id}_{hash(query)}"
        page = await _session_manager.get_or_create_session(session_id, "stealth")
        
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
                "step1_search_filter": f"{len(step1_results)} results",
                "step2_automation": "stealth_navigation",
                "step3_extract": f"{len(extracted_data)} items",
                "step4_synthesis": "completed"
            },
            "data": synthesized_results,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Deep search workflow completed: 4 steps processed")
        return json.dumps(response, indent=2)
        
    except Exception as e:
        logger.error(f"❌ Deep search failed: {e}")
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
        from isa_model.inference.ai_factory import AIFactory
        
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
        
        # Get LLM and perform analysis
        ai_factory = AIFactory()
        llm = ai_factory.get_llm()
        analysis_response = await llm.ainvoke(analysis_prompt)
        
        # Parse analysis into structured format
        analysis_results = {
            'query_context': query,
            'analysis_depth': analysis_depth,
            'raw_analysis': analysis_response.content if hasattr(analysis_response, 'content') else str(analysis_response),
            'insights': [],
            'themes': [],
            'quality_score': 0.8,  # Default score
            'metadata': {
                'items_analyzed': len(data_items),
                'analysis_timestamp': datetime.now().isoformat()
            }
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