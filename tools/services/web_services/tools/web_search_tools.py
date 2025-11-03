#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Search Tools - Clean MCP Tool Wrapper

Thin MCP wrapper for web search functionality.
All business logic is in WebSearchService.

Core Function:
- web_search: Universal search with optional AI summarization and citations

Architecture:
- This file: MCP tool interface + progress tracking
- web_search_service.py: Business logic for search and summarization
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations
from tools.base_tool import BaseTool
from tools.services.web_services.services.web_search_service import WebSearchService
from tools.services.web_services.tools.context import WebSearchProgressReporter
from core.security import SecurityLevel
from core.logging import get_logger

logger = get_logger(__name__)


class WebSearchTool(BaseTool):
    """Web search tool with progress tracking"""

    def __init__(self):
        super().__init__()
        self.search_service = WebSearchService()
        self.progress_reporter = WebSearchProgressReporter(self)

    async def web_search_impl(
        self,
        query: str,
        count: int = 10,
        user_id: str = None,

        # Search filters
        freshness: str = None,
        result_filter: str = None,
        goggle_type: str = None,
        extra_snippets: bool = True,

        # AI-powered features
        summarize: bool = False,
        summarize_count: int = 5,
        include_citations: bool = True,
        citation_style: str = "inline",
        rag_mode: str = "simple",

        # Deep search
        deep_search: bool = False,
        depth: int = 2,
        max_results_per_level: int = 5,

        # Context (will be injected by FastMCP)
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Enhanced web search with AI-powered summarization and inline citations

        Provides basic search or AI-enhanced search with content extraction and summarization.

        Args:
            query: Search query text
            count: Number of results (default: 10, max: 20)
            user_id: User ID (required for summarization)

            # Search filters
            freshness: Time filter - 'day', 'week', 'month', 'year'
            result_filter: Result type - 'news', 'videos', 'discussions', 'faq'
            goggle_type: Predefined ranking - 'academic', 'technical', 'news'
            extra_snippets: Get extra content snippets

            # AI features
            summarize: Enable AI summarization (default: False)
            summarize_count: Number of results to summarize (default: 5)
            include_citations: Add inline citations [1][2] (default: True)
            citation_style: Citation style - "inline", "footnote", "endnote"
            rag_mode: RAG mode - "simple", "self_rag", "plan_rag"

            # Deep search features
            deep_search: Enable multi-strategy deep search (default: False)
            depth: Number of search iterations (default: 2, max: 3)
            max_results_per_level: Results per iteration (default: 5)

        Examples:
            # Basic search
            web_search(query="python programming")

            # Search with AI summary and citations
            web_search(
                query="AI agents 2024",
                user_id="user1",
                summarize=True,
                summarize_count=5
            )

            # Fresh news with summary
            web_search(
                query="latest AI news",
                freshness="day",
                result_filter="news",
                summarize=True,
                user_id="user1"
            )

            # Deep search for comprehensive research
            web_search(
                query="AI safety research",
                deep_search=True,
                depth=2,
                max_results_per_level=5,
                summarize=True,
                user_id="researcher"
            )
        """
        # Create progress operation at start (NEW WAY)
        operation_id = await self.create_progress_operation(
            metadata={
                "user_id": user_id or "anonymous",
                "query": query[:100],
                "summarize": summarize,
                "deep_search": deep_search,
                "operation": "web_search"
            }
        )

        try:
            # Validate user_id for AI features
            if summarize and not user_id:
                error_response = {
                    "status": "error",
                    "action": "web_search",
                    "error": "user_id is required for summarization",
                    "data": {"query": query},
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(error_response, ensure_ascii=False)

            await self.log_info(ctx, f"Starting web search: '{query}'")

            # Handle deep search mode
            if deep_search:
                if not user_id:
                    error_response = {
                        "status": "error",
                        "action": "web_search",
                        "error": "user_id is required for deep search",
                        "data": {"query": query},
                        "timestamp": datetime.now().isoformat()
                    }
                    return json.dumps(error_response, ensure_ascii=False)

                # Stage 1: Planning
                await self.progress_reporter.report_stage(
                    operation_id, "planning", "deep", f"analyzing query", pipeline_type="deep_search"
                )

                # Stage 2: Multi-stage searching (will be reported by service)
                await self.progress_reporter.report_stage(
                    operation_id, "searching", "deep", f"iteration 1/{depth}", pipeline_type="deep_search"
                )

                # Execute deep search
                result = await self.search_service.deep_search(
                    query=query,
                    user_id=user_id,
                    depth=depth,
                    max_results_per_level=max_results_per_level,
                    rag_mode=rag_mode
                )

                # Stage 5: Synthesis complete
                await self.progress_reporter.report_stage(
                    operation_id, "synthesizing", "deep", "finalizing results", pipeline_type="deep_search"
                )

                if result.get("success"):
                    await self.log_info(
                        ctx,
                        f"✅ Deep search complete: {result.get('total', 0)} results, "
                        f"{result['deep_search_metadata']['depth_completed']} iterations"
                    )

                # Report completion
                await self.progress_reporter.report_complete(
                    "deep",
                    {
                        "results": result.get("total", 0),
                        "depth": result.get("deep_search_metadata", {}).get("depth_completed", 0)
                    }
                )

                # Complete progress operation
                await self.complete_progress_operation(
                    operation_id,
                    result={
                        "results": result.get("total", 0),
                        "depth": result.get("deep_search_metadata", {}).get("depth_completed", 0)
                    }
                )

                # Extract context info
                context_info = self.extract_context_info(ctx)

                # Return response
                if result.get("success"):
                    return self.create_response(
                        "success",
                        "deep_search",
                        {
                            **result,
                            "operation_id": operation_id,  # ✅ Return operation_id for SSE monitoring
                            "context": context_info
                        }
                    )
                else:
                    return self.create_response(
                        "error",
                        "deep_search",
                        {
                            "query": query,
                            "context": context_info
                        },
                        result.get("error", "Unknown error")
                    )

            # Handle summarization mode
            elif summarize:
                # Stage 1: Searching (initial report)
                await self.progress_reporter.report_stage(
                    operation_id, "searching", "web", f"query: {query[:50]}"
                )

                # Create progress callback to bridge service -> MCP progress reporting
                async def progress_callback(stage_description: str, progress_value: float = 0.0):
                    """
                    Bridge function: maps service-layer progress to MCP progress reporter

                    Service calls:
                    - ("searching", 0.2) -> Searching stage
                    - ("fetching", 0.4) -> Fetching stage
                    - ("fetching URL 1/3", 0.5) -> Granular fetch progress
                    - ("generating summary", 0.8) -> Summarization stage
                    """
                    try:
                        # Map service progress to appropriate reporter methods
                        if stage_description == "searching":
                            await self.progress_reporter.report_stage(
                                operation_id, "searching", "web", "executing query"
                            )
                        elif stage_description == "fetching":
                            await self.progress_reporter.report_stage(
                                operation_id, "fetching", "web", "fetching URLs"
                            )
                        elif stage_description.startswith("fetching URL"):
                            # Extract URL index from "fetching URL 1/3" format
                            parts = stage_description.split()
                            if len(parts) >= 3:
                                url_part = parts[2]  # "1/3"
                                if "/" in url_part:
                                    current, total = url_part.split("/")
                                    await self.progress_reporter.report_granular_progress(
                                        operation_id, "fetching", "web",
                                        int(current), int(total), "url"
                                    )
                        elif stage_description == "generating summary":
                            await self.progress_reporter.report_stage(
                                operation_id, "synthesizing", "summarize", "generating AI summary"
                            )
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")

                # Call service with summarization and progress callback
                result = await self.search_service.search_with_summary(
                    query=query,
                    user_id=user_id,
                    count=count,
                    summarize_count=summarize_count,
                    include_citations=include_citations,
                    citation_style=citation_style,
                    rag_mode=rag_mode,
                    progress_callback=progress_callback,  # Pass progress callback
                    freshness=freshness,
                    result_filter=result_filter,
                    goggle_type=goggle_type,
                    extra_snippets=extra_snippets
                )

                if result.get("success"):
                    # Progress stages are handled in service
                    summary = result.get("summary", {})
                    await self.log_info(
                        ctx,
                        f"✅ Summary generated: {summary.get('sources_used', 0)} sources, "
                        f"{len(summary.get('citations', []))} citations"
                    )

            else:
                # Basic search only
                await self.progress_reporter.report_stage(
                    operation_id, "searching", "web", f"query: {query[:50]}"
                )

                result = await self.search_service.search(
                    query=query,
                    count=count,
                    freshness=freshness,
                    result_filter=result_filter,
                    goggle_type=goggle_type,
                    extra_snippets=extra_snippets
                )

                if result.get("success"):
                    await self.log_info(
                        ctx,
                        f"✅ Found {result.get('total', 0)} results"
                    )

            # Report completion
            await self.progress_reporter.report_complete(
                "web",
                {
                    "results": result.get("total", 0),
                    "summarized": result.get("summary", {}).get("sources_used", 0) if summarize else 0
                }
            )

            # Complete progress operation
            await self.complete_progress_operation(
                operation_id,
                result={
                    "results": result.get("total", 0),
                    "summarized": result.get("summary", {}).get("sources_used", 0) if summarize else 0
                }
            )

            # Extract context info (like digital_tools)
            context_info = self.extract_context_info(ctx)

            # Use create_response like digital_tools (returns Dict, not JSON string)
            if result.get("success"):
                return self.create_response(
                    "success",
                    "web_search",
                    {
                        **result,
                        "operation_id": operation_id,  # ✅ Return operation_id for SSE monitoring
                        "context": context_info  # Add context info
                    }
                )
            else:
                return self.create_response(
                    "error",
                    "web_search",
                    {
                        "query": query,
                        "context": context_info  # Add context info
                    },
                    result.get("error", "Unknown error")
                )

        except Exception as e:
            # Fail progress operation on error
            if 'operation_id' in locals():
                await self.fail_progress_operation(operation_id, str(e))

            await self.log_error(ctx, f"Web search failed: {str(e)}")

            # Extract context even in error case
            context_info = self.extract_context_info(ctx)

            return self.create_response(
                "error",
                "web_search",
                {
                    "query": query,
                    "context": context_info  # Add context info
                },
                f"Search failed: {str(e)}"
            )


def register_web_search_tools(mcp: FastMCP):
    """Register web search tool"""
    web_tool = WebSearchTool()

    # Register using BaseTool.register_tool() for proper Context injection
    web_tool.register_tool(
        mcp,
        web_tool.web_search_impl,
        name="web_search",
        description="Enhanced web search with AI-powered summarization and inline citations. "
                    "Keywords: search, web, internet, query, results, summarize, citations. "
                    "Category: web",
        security_level=SecurityLevel.LOW,
        timeout=120.0,
        annotations=ToolAnnotations(
            readOnlyHint=True
        )
    )

    logger.info("✅ Web Search Tools registered: 1 enhanced function")
    logger.info("🔍 web_search: Basic search + AI summarization + citations")
    logger.info("📄 Features: Inline citations [1][2], content extraction, progress tracking")

    return web_tool
