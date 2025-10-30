#!/usr/bin/env python
"""
Web Search Service - Enhanced Web Search with AI Features
Provides search functionality with optional AI-powered summarization and citations
"""

from typing import Dict, Any, List, Optional

from core.logging import get_logger
from core.config import get_settings
from ..engines.search_engine import SearchEngine, SearchProvider, BraveSearchStrategy

logger = get_logger(__name__)


class WebSearchService:
    """Enhanced web search service with AI summarization and citations"""

    def __init__(self):
        self.search_engine = SearchEngine()
        self._initialized = False
        self.crawl_service = None  # Lazy loaded
        self.deep_search_orchestrator = None  # Lazy loaded
        logger.info("✅ WebSearchService initialized")

    async def initialize(self):
        """初始化搜索引擎"""
        if self._initialized:
            return

        # Get settings from centralized config
        settings = get_settings()

        # 注册Brave搜索
        brave_api_key = settings.brave_api_key
        if brave_api_key:
            brave_strategy = BraveSearchStrategy(brave_api_key)
            self.search_engine.register_strategy(SearchProvider.BRAVE, brave_strategy)
            logger.info("✅ Brave search registered")
        else:
            logger.warning("⚠️ No Brave API key found in config")

        self._initialized = True
    
    async def search(
        self,
        query: str,
        count: int = 10,
        freshness: str = None,
        result_filter: str = None,
        goggle_type: str = None,
        extra_snippets: bool = True,
        deep_search: bool = False
    ) -> Dict[str, Any]:
        """
        Enhanced search with advanced features

        Args:
            query: 搜索查询
            count: 结果数量
            freshness: 时间过滤 - 'day', 'week', 'month', 'year'
            result_filter: 结果类型 - 'news', 'videos', 'discussions', 'faq'
            goggle_type: 预定义排名 - 'academic', 'technical', 'news'
            extra_snippets: 获取额外内容片段
            deep_search: 执行深度搜索

        Returns:
            搜索结果字典
        """
        try:
            await self.initialize()

            logger.info(f"🔍 Searching: {query}")

            # Import enums for parameter conversion
            from ..engines.search_engine import SearchFreshness, ResultFilter

            # Build kwargs for enhanced search
            search_kwargs = {
                "count": count,
                "extra_snippets": extra_snippets
            }

            # Add optional parameters
            if freshness:
                if freshness.upper() in ['DAY', 'WEEK', 'MONTH', 'YEAR']:
                    search_kwargs["freshness"] = SearchFreshness[freshness.upper()]
                else:
                    search_kwargs["freshness"] = freshness

            if result_filter:
                if result_filter.upper() in ['DISCUSSIONS', 'FAQ', 'NEWS', 'VIDEOS', 'INFOBOX', 'LOCATIONS']:
                    search_kwargs["result_filter"] = ResultFilter[result_filter.upper()]
                else:
                    search_kwargs["result_filter"] = result_filter

            if goggle_type:
                search_kwargs["goggle_type"] = goggle_type

            # Execute search
            if deep_search:
                # Use deep search
                strategy = self.search_engine.strategies.get("brave")
                if strategy:
                    results = await strategy.deep_search(query, depth=2, max_results_per_level=count)
                else:
                    return {
                        "success": False,
                        "error": "Deep search not available",
                        "query": query,
                        "results": [],
                        "urls": []
                    }
            else:
                # Regular enhanced search
                results = await self.search_engine.search(query, **search_kwargs)

            # Format results
            formatted_results = [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "score": r.score,
                    "type": r.type,
                    "all_content": r.get_all_content()[:500]  # Limit content size
                }
                for r in results
            ]

            # Build response
            response = {
                "success": True,
                "query": query,
                "total": len(results),
                "results": formatted_results,
                "urls": [r.url for r in results]
            }

            # Add search params if not basic search
            if freshness or result_filter or goggle_type or deep_search:
                response["search_params"] = {
                    "freshness": str(search_kwargs.get("freshness")) if "freshness" in search_kwargs else None,
                    "filter": str(search_kwargs.get("result_filter")) if "result_filter" in search_kwargs else None,
                    "goggle": search_kwargs.get("goggle_type"),
                    "extra_snippets": extra_snippets,
                    "count": count
                }
                if deep_search:
                    response["search_type"] = "deep"

            return response

        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": [],
                "urls": []
            }
    
    async def get_urls(self, query: str, count: int = 5) -> List[str]:
        """获取搜索结果的URL列表（用于爬虫）"""
        result = await self.search(query, count)
        return result.get("urls", [])

    def _get_crawl_service(self):
        """Lazy load crawl service to avoid circular imports"""
        if self.crawl_service is None:
            from .web_crawl_service import WebCrawlService
            self.crawl_service = WebCrawlService()
        return self.crawl_service

    def _get_deep_search_orchestrator(self):
        """Lazy load deep search orchestrator"""
        if self.deep_search_orchestrator is None:
            from .deep_search import DeepSearchOrchestrator
            self.deep_search_orchestrator = DeepSearchOrchestrator(self.search_engine)
            logger.info("✅ Deep search orchestrator initialized")
        return self.deep_search_orchestrator

    async def search_with_summary(
        self,
        query: str,
        user_id: str,
        count: int = 10,
        summarize_count: int = 5,
        include_citations: bool = True,
        citation_style: str = "inline",
        rag_mode: str = "simple",
        progress_callback=None,  # Progress callback function
        **search_kwargs
    ) -> Dict[str, Any]:
        """
        Search with AI-powered summarization and inline citations

        Business logic for:
        1. Execute search
        2. Fetch and extract content from top N results
        3. Generate summary with citations using RAG

        Args:
            query: Search query
            user_id: User ID for RAG context
            count: Total search results
            summarize_count: Number of results to summarize
            include_citations: Enable inline citations [1][2]
            citation_style: "inline", "footnote", or "endnote"
            rag_mode: RAG mode for summary generation
            **search_kwargs: Additional search parameters (freshness, filter, etc.)

        Returns:
            Dict with search results + summary with citations
        """
        try:
            import asyncio  # Import once at the start

            # Report progress: Stage 1 - Searching
            if progress_callback:
                await progress_callback("searching", 0.2)

            # Step 1: Execute search
            search_result = await self.search(query, count, **search_kwargs)

            if not search_result.get("success"):
                return search_result

            results = search_result.get("results", [])
            if not results:
                return search_result

            # Report progress: Stage 2 - Fetching content
            if progress_callback:
                await progress_callback("fetching", 0.4)

            # Step 2: Fetch content from top N results
            logger.info(f"Fetching content from top {summarize_count} results for summarization")

            crawl_service = self._get_crawl_service()
            urls_to_fetch = [r["url"] for r in results[:summarize_count]]
            fetched_contents = []

            for idx, url in enumerate(urls_to_fetch):
                try:
                    # Report progress for each URL
                    if progress_callback:
                        progress = 0.4 + (0.3 * (idx / len(urls_to_fetch)))
                        await progress_callback(f"fetching URL {idx+1}/{len(urls_to_fetch)}", progress)

                    logger.info(f"Fetching {idx+1}/{len(urls_to_fetch)}: {url}")

                    # Use crawl service to extract content with timeout
                    # Skip analysis_request to avoid expensive LLM call - we just need raw content for summarization
                    crawl_result = await asyncio.wait_for(
                        crawl_service.crawl_and_analyze(
                            url,
                            analysis_request=None  # Skip LLM analysis for faster fetching
                        ),
                        timeout=20.0  # 20 second timeout per URL
                    )

                    if crawl_result.get("success"):
                        content = crawl_result.get("content", "")
                        fetched_contents.append({
                            "url": url,
                            "title": results[idx].get("title", ""),
                            "content": content[:2000],  # Limit for context window
                            "snippet": results[idx].get("snippet", "")
                        })
                        logger.info(f"✅ Fetched {len(content)} chars from {url}")

                except asyncio.TimeoutError:
                    logger.warning(f"Timeout fetching {url} (>10s)")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to fetch {url}: {e}")
                    continue

            if not fetched_contents:
                logger.warning("No content fetched, returning search results without summary")
                return search_result

            # Report progress: Stage 3 - Generating summary
            if progress_callback:
                await progress_callback("generating summary", 0.8)

            # Step 3: Generate summary with citations using ISA Model Client
            logger.info(f"Generating summary using ISA Model Client")

            from isa_model.inference_client import AsyncISAModel
            from core.consul_discovery import discover_service

            # Use Consul service discovery to find model service
            model_api_url = discover_service('model_service', default_url='http://localhost:8082')
            logger.info(f"Using model service at: {model_api_url}")

            # Build context with citations
            context_parts = []
            for idx, content_data in enumerate(fetched_contents, 1):
                citation_marker = f"[{idx}]" if include_citations else ""
                context_parts.append(
                    f"{citation_marker} {content_data['title']}\n"
                    f"URL: {content_data['url']}\n"
                    f"Content: {content_data['content']}\n"
                )

            context_text = "\n---\n".join(context_parts)

            # Generate summary with LLM (with timeout)
            try:
                async with AsyncISAModel(base_url=model_api_url) as client:
                    # Use asyncio.wait_for to add timeout
                    response = await asyncio.wait_for(
                        client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are a helpful assistant that summarizes web search results. "
                                              f"Include inline citations using [1], [2], etc. when referencing sources."
                                              if include_citations else
                                              "You are a helpful assistant that summarizes web search results."
                                },
                                {
                                    "role": "user",
                                    "content": f"Query: {query}\n\n"
                                              f"Sources:\n{context_text}\n\n"
                                              f"Please provide a comprehensive summary answering the query, "
                                              f"using the sources provided above."
                                }
                            ],
                            temperature=0.3
                        ),
                        timeout=15.0  # 15 second timeout for LLM call
                    )
                    summary_text = response.choices[0].message.content
                    logger.info(f"✅ LLM generated summary: {len(summary_text)} chars")
            except Exception as e:
                logger.error(f"Failed to generate summary with LLM: {e}")
                # Fallback: simple concatenation
                summary_text = f"Search results for '{query}':\n\n" + "\n\n".join([
                    f"[{idx}] {c['title']}: {c['snippet']}"
                    for idx, c in enumerate(fetched_contents, 1)
                ])

            # Build citation list
            citations = []
            for idx, content_data in enumerate(fetched_contents, 1):
                citations.append({
                    "id": idx,
                    "title": content_data["title"],
                    "url": content_data["url"],
                    "snippet": content_data["snippet"]
                })

            # Add summary to response
            search_result["summary"] = {
                "text": summary_text,
                "citations": citations,
                "citation_style": citation_style,
                "sources_used": len(fetched_contents),
                "total_content_analyzed": sum(len(c["content"]) for c in fetched_contents),
                "rag_mode": rag_mode
            }

            logger.info(f"✅ Summary generated: {len(summary_text)} chars, {len(citations)} citations")

            return search_result

        except Exception as e:
            logger.error(f"❌ Search with summary failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": [],
                "urls": []
            }

    async def deep_search(
        self,
        query: str,
        user_id: str,
        depth: int = 2,
        max_results_per_level: int = 10,
        rag_mode: str = "auto",
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Execute deep search with multi-strategy fusion and query analysis

        Args:
            query: Search query
            user_id: User ID (required for summarization)
            depth: Number of search iterations (1-3)
            max_results_per_level: Max results per iteration
            rag_mode: RAG mode - "auto", "simple", "self_rag", "plan_rag", "crag"
            progress_callback: Optional progress callback

        Returns:
            Dict with deep search results and metadata
        """
        try:
            await self.initialize()

            logger.info(f"🚀 Starting deep search: '{query}' (depth={depth})")

            # Get orchestrator
            orchestrator = self._get_deep_search_orchestrator()

            # Import deep search models
            from .deep_search import DeepSearchConfig, RAGMode

            # Map rag_mode string to enum
            try:
                rag_mode_enum = RAGMode(rag_mode)
            except ValueError:
                logger.warning(f"Invalid RAG mode '{rag_mode}', using AUTO")
                rag_mode_enum = RAGMode.AUTO

            # Create config
            config = DeepSearchConfig(
                query=query,
                user_id=user_id,
                depth=min(depth, 3),  # Cap at 3
                max_results_per_level=max_results_per_level,
                rag_mode=rag_mode_enum,
                progress_callback=progress_callback
            )

            # Execute deep search
            result = await orchestrator.execute_deep_search(config)

            if not result.success:
                return {
                    "success": False,
                    "error": result.error,
                    "query": query
                }

            # Format results for response
            formatted_results = []
            for fused_result in result.results:
                formatted_results.append({
                    "url": fused_result.url,
                    "title": fused_result.title,
                    "snippet": fused_result.snippet,
                    "fusion_score": fused_result.fusion_score,
                    "strategies": [s.value for s in fused_result.source_strategies],
                    "strategy_scores": fused_result.strategy_scores,
                    "type": fused_result.result_type
                })

            # Build response
            response = {
                "success": True,
                "query": query,
                "total": len(formatted_results),
                "results": formatted_results,
                "deep_search_metadata": {
                    "execution_time": result.execution_time,
                    "depth_completed": result.depth_completed,
                    "strategies_used": [s.value for s in result.strategies_used],
                    "rag_mode": result.rag_mode_used.value,
                    "query_profile": {
                        "complexity": result.query_profile.complexity.value if result.query_profile else "unknown",
                        "domain": result.query_profile.domain.value if result.query_profile else "unknown",
                        "query_type": result.query_profile.query_type.value if result.query_profile else "unknown"
                    } if result.query_profile else None,
                    "iterations": result.iterations
                }
            }

            logger.info(
                f"✅ Deep search complete: {len(formatted_results)} results in {result.execution_time:.2f}s"
            )

            return response

        except Exception as e:
            logger.error(f"❌ Deep search failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": []
            }

    async def close(self):
        """清理资源"""
        await self.search_engine.close()
        if self.crawl_service:
            await self.crawl_service.close()
        logger.info("✅ WebSearchService closed")


# 测试函数
async def test_search():
    """简单测试"""
    import asyncio
    
    service = WebSearchService()
    
    try:
        result = await service.search("python tutorial", count=3)
        print(f"Success: {result['success']}")
        print(f"Found: {result['total']} results")
        
        for i, res in enumerate(result['results']):
            print(f"{i+1}. {res['title']}")
            print(f"   {res['url']}")
    
    finally:
        await service.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_search())