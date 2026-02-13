#!/usr/bin/env python3
"""
Web Tools for MCP Server
MCP tool wrappers around web microservice HTTP client with SSE progress tracking
"""

import json
from typing import Optional, List
from mcp.server.fastmcp import FastMCP
from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from tools.base_tool import BaseTool

from .web_client import get_web_client

logger = get_logger(__name__)
tools = BaseTool()


def register_web_tools(mcp: FastMCP):
    """Register web tools that call web microservice via HTTP with SSE progress"""

    security_manager = get_security_manager()

    # ========== WEB SEARCH TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def web_search(
        query: str,
        count: int = 10,
        freshness: Optional[str] = None,
        result_filter: Optional[str] = None,
        goggle_type: Optional[str] = None,
    ) -> str:
        """Search the web for information. Use when user needs latest, current, or recent information.

        Intent patterns that require this tool:
        - "what is the latest..." / "what's the latest..."
        - "current news about..." / "recent news..."
        - "what's happening with..." / "updates on..."
        - "search for..." / "find information about..."
        - "look up..." / "research..."
        - Any question requiring up-to-date or real-time information

        Args:
            query: Search query string
            count: Number of results to return (default 10, max 20)
            freshness: Time filter - "day", "week", "month", "year" (optional)
            result_filter: Filter by type - "news", "videos", etc. (optional)
            goggle_type: Special filter type - "academic" for scholarly sources (optional)

        Returns:
            JSON string with search results including title, url, description for each result.
        """
        try:
            client = get_web_client()

            # Collect SSE messages and track progress
            progress_updates = []
            final_result = None

            async for message in client.search(
                query=query,
                count=count,
                freshness=freshness,
                result_filter=result_filter,
                goggle_type=goggle_type,
            ):
                # Track progress
                if "progress" in message:
                    progress_updates.append(
                        {"progress": message["progress"], "message": message.get("message", "")}
                    )

                # Capture final result
                if message.get("completed"):
                    final_result = message.get("result", {})

            # Return formatted response with progress history (JSON serialized for -> str return type)
            return json.dumps(
                tools.create_response(
                    status="success" if final_result else "error",
                    action="web_search",
                    data={
                        "query": query,
                        "results": final_result.get("results", []) if final_result else [],
                        "total_results": (
                            final_result.get("total_results", 0) if final_result else 0
                        ),
                        "execution_time": (
                            final_result.get("execution_time", 0) if final_result else 0
                        ),
                        "provider": (
                            final_result.get("provider", "brave") if final_result else "brave"
                        ),
                        "progress_history": progress_updates,
                    },
                )
            )

        except Exception as e:
            logger.error(f"Error in web_search: {e}")
            return json.dumps(
                tools.create_response(
                    status="error", action="web_search", data={"query": query}, error_message=str(e)
                )
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def deep_web_search(
        query: str, user_id: str, depth: int = 2, rag_mode: bool = True
    ) -> str:
        """Deep web search with multi-strategy approach and progress tracking

        Performs an intelligent deep search using multiple strategies:
        1. Initial broad search
        2. Query refinement based on results
        3. Follow-up targeted searches
        4. RAG-enhanced result processing

        Args:
            query: Search query string
            user_id: User identifier for personalization
            depth: Search depth level (1-3, default 2)
                - 1: Basic search
                - 2: Single refinement iteration
                - 3: Multiple refinement iterations
            rag_mode: Enable RAG (Retrieval-Augmented Generation) processing (default True)

        Returns:
            JSON string containing:
            - progress: Real-time progress through search stages
            - results: Comprehensive search results from all stages
            - refined_queries: List of refined queries used
            - total_results: Total number of unique results
            - execution_time: Total time taken
            - rag_summary: AI-generated summary if rag_mode=True

        Examples:
            # Standard deep search
            deep_web_search("machine learning trends", user_id="user123")

            # Thorough research
            deep_web_search("climate change solutions", user_id="user123", depth=3)

            # Quick deep search without RAG
            deep_web_search("quick topic", user_id="user123", depth=1, rag_mode=False)
        """
        try:
            client = get_web_client()

            # Collect SSE messages and track progress
            progress_updates = []
            final_result = None

            async for message in client.deep_search(
                query=query, user_id=user_id, depth=depth, rag_mode=rag_mode
            ):
                # Track progress
                if "progress" in message:
                    progress_updates.append(
                        {"progress": message["progress"], "message": message.get("message", "")}
                    )

                # Capture final result
                if message.get("completed"):
                    final_result = message.get("result", {})

            # Return formatted response (JSON serialized for -> str return type)
            return json.dumps(
                tools.create_response(
                    status="success" if final_result else "error",
                    action="deep_web_search",
                    data={
                        "query": query,
                        "results": final_result.get("results", []) if final_result else [],
                        "refined_queries": (
                            final_result.get("refined_queries", []) if final_result else []
                        ),
                        "total_results": (
                            final_result.get("total_results", 0) if final_result else 0
                        ),
                        "execution_time": (
                            final_result.get("execution_time", 0) if final_result else 0
                        ),
                        "rag_summary": final_result.get("rag_summary") if final_result else None,
                        "progress_history": progress_updates,
                    },
                )
            )

        except Exception as e:
            logger.error(f"Error in deep_web_search: {e}")
            return json.dumps(
                tools.create_response(
                    status="error",
                    action="deep_web_search",
                    data={"query": query, "user_id": user_id},
                    error_message=str(e),
                )
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def web_search_with_summary(
        query: str,
        user_id: str,
        count: int = 10,
        summarize_count: int = 5,
        include_citations: bool = True,
    ) -> str:
        """Web search with AI-powered summary and progress tracking

        Performs web search and generates an AI summary of top results.
        Useful for quick research and information synthesis.

        Args:
            query: Search query string
            user_id: User identifier for AI service billing
            count: Total number of search results (default 10, max 20)
            summarize_count: Number of top results to include in summary (default 5)
            include_citations: Include source citations in summary (default True)

        Returns:
            JSON string containing:
            - progress: Real-time progress through search and summarization
            - results: Full list of search results
            - summary: AI-generated summary of top results
            - citations: Source citations if include_citations=True
            - total_results: Number of results returned
            - execution_time: Total time taken

        Examples:
            # Basic search with summary
            web_search_with_summary("renewable energy", user_id="user123")

            # Detailed summary with more sources
            web_search_with_summary(
                "AI safety research",
                user_id="user123",
                count=15,
                summarize_count=8,
                include_citations=True
            )

            # Quick summary without citations
            web_search_with_summary(
                "quick topic",
                user_id="user123",
                summarize_count=3,
                include_citations=False
            )
        """
        try:
            client = get_web_client()

            # Collect SSE messages and track progress
            progress_updates = []
            final_result = None

            async for message in client.search_with_summary(
                query=query,
                user_id=user_id,
                count=count,
                summarize_count=summarize_count,
                include_citations=include_citations,
            ):
                # Track progress
                if "progress" in message:
                    progress_updates.append(
                        {"progress": message["progress"], "message": message.get("message", "")}
                    )

                # Capture final result
                if message.get("completed"):
                    final_result = message.get("result", {})

            # Return formatted response (JSON serialized for -> str return type)
            return json.dumps(
                tools.create_response(
                    status="success" if final_result else "error",
                    action="web_search_with_summary",
                    data={
                        "query": query,
                        "results": final_result.get("results", []) if final_result else [],
                        "summary": final_result.get("summary") if final_result else None,
                        "citations": final_result.get("citations", []) if final_result else [],
                        "total_results": (
                            final_result.get("total_results", 0) if final_result else 0
                        ),
                        "execution_time": (
                            final_result.get("execution_time", 0) if final_result else 0
                        ),
                        "progress_history": progress_updates,
                    },
                )
            )

        except Exception as e:
            logger.error(f"Error in web_search_with_summary: {e}")
            return json.dumps(
                tools.create_response(
                    status="error",
                    action="web_search_with_summary",
                    data={"query": query, "user_id": user_id},
                    error_message=str(e),
                )
            )

    # ========== WEB CRAWL TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def web_crawl(
        url: str,
        provider: str = "self_hosted_crawl",
        use_vlm: bool = False,
        analyze: bool = False,
        analysis_request: Optional[str] = None,
    ) -> str:
        """Crawl and extract content from a web page with progress tracking

        Crawls a web page and extracts structured content including title, text,
        markdown, HTML, links, and images. Optionally uses VLM for visual analysis.

        Args:
            url: Target URL to crawl
            provider: Crawl provider - "self_hosted_crawl", "firecrawl" (default "self_hosted_crawl")
            use_vlm: Use Vision Language Model for visual analysis (default False)
            analyze: Perform content analysis (default False)
            analysis_request: Specific analysis request (optional, e.g., "Summarize the main points")

        Returns:
            JSON string containing:
            - title: Page title
            - content: Extracted main content
            - markdown: Content in markdown format
            - html: Raw HTML content
            - links: List of extracted links
            - images: List of image URLs
            - analysis: Analysis results if requested
            - execution_time: Time taken to crawl
            - extraction_method: Method used for extraction

        Examples:
            # Basic crawl
            web_crawl("https://example.com")

            # Crawl with VLM analysis
            web_crawl("https://example.com", use_vlm=True)

            # Crawl with custom analysis
            web_crawl(
                "https://news.ycombinator.com",
                analyze=True,
                analysis_request="Extract the top 5 trending topics"
            )
        """
        try:
            client = get_web_client()

            # Collect SSE messages and track progress
            progress_updates = []
            final_data = None

            async for message in client.crawl(
                url=url,
                provider=provider,
                use_vlm=use_vlm,
                analyze=analyze,
                analysis_request=analysis_request,
            ):
                # Track progress
                if "progress" in message:
                    progress_updates.append(
                        {"progress": message["progress"], "message": message.get("message", "")}
                    )

                # Capture final result
                if message.get("data"):
                    final_data = message.get("data", {})

            # Return formatted response (JSON serialized for -> str return type)
            return json.dumps(
                tools.create_response(
                    status="success" if final_data else "error",
                    action="web_crawl",
                    data={
                        "url": url,
                        "title": final_data.get("title") if final_data else None,
                        "content": final_data.get("content") if final_data else None,
                        "markdown": final_data.get("markdown") if final_data else None,
                        "links": final_data.get("links", []) if final_data else [],
                        "images": final_data.get("images", []) if final_data else [],
                        "analysis": final_data.get("analysis") if final_data else None,
                        "extraction_method": (
                            final_data.get("extraction_method") if final_data else None
                        ),
                        "execution_time": final_data.get("execution_time", 0) if final_data else 0,
                        "progress_history": progress_updates,
                    },
                )
            )

        except Exception as e:
            logger.error(f"Error in web_crawl: {e}")
            return json.dumps(
                tools.create_response(
                    status="error", action="web_crawl", data={"url": url}, error_message=str(e)
                )
            )

    # ========== WEB AUTOMATION TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.HIGH)
    async def web_automation_execute(
        url: str,
        task: str,
        provider: str = "self_hosted",
        routing_strategy: str = "dom_first",
        use_vlm: bool = False,
    ) -> str:
        """Execute web automation task with progress tracking

        Automates interactions with web pages using AI-powered task execution.
        Can perform actions like clicking, filling forms, extracting data, etc.

        Args:
            url: Target URL for automation
            task: Task description in natural language
                Examples:
                - "Click on the 'More information' link"
                - "Fill the search box with 'AI news' and submit"
                - "Extract all product prices from the page"
            provider: Automation provider - "self_hosted", "browserbase" (default "self_hosted")
            routing_strategy: Execution strategy:
                - "dom_first": Use DOM analysis first (faster, cheaper)
                - "vlm_first": Use vision model first (more accurate)
                - "hybrid": Combine both approaches
            use_vlm: Force use of Vision Language Model (default False)

        Returns:
            JSON string containing:
            - task_result: Result of the automation task
            - actions_performed: List of actions executed
            - screenshots: Screenshots if captured
            - execution_time: Time taken
            - success: Whether task completed successfully

        Examples:
            # Click a link
            web_automation_execute(
                "https://example.com",
                "Click on the 'More information' link"
            )

            # Fill and submit form
            web_automation_execute(
                "https://google.com",
                "Search for 'AI news'",
                routing_strategy="dom_first"
            )

            # Use VLM for complex visual tasks
            web_automation_execute(
                "https://complex-ui.com",
                "Find and click the green submit button",
                use_vlm=True
            )
        """
        try:
            client = get_web_client()

            # Collect SSE messages and track progress
            progress_updates = []
            final_data = None

            async for message in client.automation_execute(
                url=url,
                task=task,
                provider=provider,
                routing_strategy=routing_strategy,
                use_vlm=use_vlm,
            ):
                # Track progress
                if "progress" in message:
                    progress_updates.append(
                        {"progress": message["progress"], "message": message.get("message", "")}
                    )

                # Capture final result
                if message.get("data"):
                    final_data = message.get("data", {})

            # Return formatted response (JSON serialized for -> str return type)
            return json.dumps(
                tools.create_response(
                    status="success" if final_data else "error",
                    action="web_automation_execute",
                    data={
                        "url": url,
                        "task": task,
                        "result": final_data if final_data else None,
                        "progress_history": progress_updates,
                    },
                )
            )

        except Exception as e:
            logger.error(f"Error in web_automation_execute: {e}")
            return json.dumps(
                tools.create_response(
                    status="error",
                    action="web_automation_execute",
                    data={"url": url, "task": task},
                    error_message=str(e),
                )
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def web_automation_search(
        query: str,
        search_engine: str = "google",
        task: Optional[str] = None,
        provider: str = "self_hosted",
        use_vlm: bool = False,
    ) -> str:
        """Execute automated web search with optional follow-up actions

        Performs automated search on specified search engine and optionally
        executes additional tasks on the results.

        Args:
            query: Search query
            search_engine: Search engine - "google", "bing", "duckduckgo" (default "google")
            task: Optional follow-up task after search
                Examples:
                - "Click on the first result"
                - "Extract titles from top 5 results"
            provider: Automation provider (default "self_hosted")
            use_vlm: Use Vision Language Model (default False)

        Returns:
            JSON string containing:
            - search_results: Search results obtained
            - task_result: Result of follow-up task if specified
            - execution_time: Time taken
            - success: Whether operation completed successfully

        Examples:
            # Simple search
            web_automation_search("Python tutorials")

            # Search with action
            web_automation_search(
                "best restaurants near me",
                task="Click on the first Yelp result"
            )

            # Use different search engine
            web_automation_search(
                "privacy-focused email",
                search_engine="duckduckgo"
            )
        """
        try:
            client = get_web_client()

            # Collect SSE messages and track progress
            progress_updates = []
            final_data = None

            async for message in client.automation_search(
                query=query,
                search_engine=search_engine,
                task=task,
                provider=provider,
                use_vlm=use_vlm,
            ):
                # Track progress
                if "progress" in message:
                    progress_updates.append(
                        {"progress": message["progress"], "message": message.get("message", "")}
                    )

                # Capture final result
                if message.get("data"):
                    final_data = message.get("data", {})

            # Return formatted response (JSON serialized for -> str return type)
            return json.dumps(
                tools.create_response(
                    status="success" if final_data else "error",
                    action="web_automation_search",
                    data={
                        "query": query,
                        "search_engine": search_engine,
                        "result": final_data if final_data else None,
                        "progress_history": progress_updates,
                    },
                )
            )

        except Exception as e:
            logger.error(f"Error in web_automation_search: {e}")
            return json.dumps(
                tools.create_response(
                    status="error",
                    action="web_automation_search",
                    data={"query": query},
                    error_message=str(e),
                )
            )

    # ========== UTILITY TOOLS ==========

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def web_service_health_check() -> str:
        """Check web service health status

        Verifies that the web service is running and accessible.
        Useful for debugging and monitoring.

        Returns:
            JSON string containing:
            - status: Service status ("healthy" or error message)
            - service_url: URL of the web service being used
            - response_time: Time taken to respond (ms)

        Example:
            web_service_health_check()
        """
        try:
            client = get_web_client()

            import time

            start_time = time.time()
            health = await client.health_check()
            response_time = (time.time() - start_time) * 1000

            return json.dumps(
                tools.create_response(
                    status="success",
                    action="web_service_health_check",
                    data={
                        "status": "healthy",
                        "service_url": client.service_url or "not discovered yet",
                        "response_time_ms": round(response_time, 2),
                        "health_data": health,
                    },
                )
            )

        except Exception as e:
            logger.error(f"Error checking web service health: {e}")
            return json.dumps(
                tools.create_response(
                    status="error", action="web_service_health_check", data={}, error_message=str(e)
                )
            )
