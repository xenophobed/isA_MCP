#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Search Progress Context Module

Universal progress tracking for web search and content extraction pipeline.
Provides standardized 4-stage progress reporting for all search operations.

Pipeline Stages:
1. Searching (25%) - Execute search query
2. Fetching (50%) - Fetch and extract content from URLs
3. Processing (75%) - Process and analyze content
4. Synthesizing (100%) - Generate summary and citations

Supported Operations: Basic search, Deep search, Content extraction, Summarization
"""

from typing import Dict, Any, Optional
from tools.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class WebSearchProgressReporter:
    """
    Universal progress reporting for all web search operations

    Provides a standardized 4-stage pipeline progress tracking:
    1. Searching (25%) - Execute search query
    2. Fetching (50%) - Fetch and extract content from URLs
    3. Processing (75%) - Process and analyze content
    4. Synthesizing (100%) - Generate summary and citations

    Supports: Basic search, Deep search, Content extraction, Summarization with citations

    Example:
        reporter = WebSearchProgressReporter(base_tool)

        # Create operation at start
        operation_id = await base_tool.create_progress_operation(metadata={...})

        # Stage 1: Searching
        await reporter.report_stage(operation_id, "searching", "web", "executing query")

        # Stage 2: Fetching with granular progress
        for i in range(1, total_urls + 1):
            await reporter.report_granular_progress(operation_id, "fetching", "web", i, total_urls, "page")

        # Stage 3: Processing
        await reporter.report_stage(operation_id, "processing", "web", "extracting content")

        # Stage 4: Synthesizing
        await reporter.report_stage(operation_id, "synthesizing", "web", "generating summary")

        # Complete operation
        await base_tool.complete_progress_operation(operation_id, result={...})
    """

    # Search pipeline stages (for basic search)
    SEARCH_STAGES = {
        "searching": {"step": 1, "weight": 25, "label": "Searching"},
        "fetching": {"step": 2, "weight": 50, "label": "Fetching"},
        "processing": {"step": 3, "weight": 75, "label": "Processing"},
        "synthesizing": {"step": 4, "weight": 100, "label": "Synthesizing"}
    }

    # Deep search pipeline stages (for investigative search)
    DEEP_SEARCH_STAGES = {
        "planning": {"step": 1, "weight": 20, "label": "Planning"},
        "searching": {"step": 2, "weight": 40, "label": "Multi-Stage Search"},
        "fetching": {"step": 3, "weight": 60, "label": "Content Fetching"},
        "analyzing": {"step": 4, "weight": 80, "label": "Deep Analysis"},
        "synthesizing": {"step": 5, "weight": 100, "label": "Synthesis"}
    }

    # Crawl pipeline stages (for web_crawl)
    CRAWL_STAGES = {
        "fetching": {"step": 1, "weight": 33, "label": "Fetching"},
        "extracting": {"step": 2, "weight": 67, "label": "Extracting"},
        "analyzing": {"step": 3, "weight": 100, "label": "Analyzing"}
    }

    # Default to search stages
    STAGES = SEARCH_STAGES

    # Operation type display names
    OPERATION_NAMES = {
        "web": "Web Search",
        "deep": "Deep Search",
        "crawl": "Web Crawl",
        "summarize": "Summarization",
        "citation": "Citation Generation"
    }

    # Stage-specific prefixes for logging
    STAGE_PREFIXES = {
        "searching": "[SEARCH]",
        "fetching": "[FETCH]",
        "processing": "[PROC]",
        "synthesizing": "[SYNTH]",
        "planning": "[PLAN]",
        "analyzing": "[ANALYZE]",
        "extracting": "[EXTRACT]"
    }

    def __init__(self, base_tool: BaseTool):
        """
        Initialize progress reporter

        Args:
            base_tool: BaseTool instance for accessing Context methods
        """
        self.base_tool = base_tool

    async def report_stage(
        self,
        operation_id: Optional[str],
        stage: str,
        operation_type: str,
        sub_progress: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        pipeline_type: str = "search"
    ):
        """
        Report progress for a pipeline stage using ProgressManager (NEW WAY)

        Args:
            operation_id: Operation ID for progress tracking (use ProgressManager)
            stage: Pipeline stage name (varies by pipeline_type)
            operation_type: Operation type - "web", "deep", "crawl", "summarize"
            sub_progress: Optional granular progress within stage
            details: Optional additional details for logging
            pipeline_type: Type of pipeline - "search", "deep_search", or "crawl"

        Pipeline Types & Stages:
            search: searching -> fetching -> processing -> synthesizing (4 stages)
            deep_search: planning -> searching -> fetching -> analyzing -> synthesizing (5 stages)
            crawl: fetching -> extracting -> analyzing (3 stages)

        Examples:
            # Basic search
            await reporter.report_stage(operation_id, "searching", "web", pipeline_type="search")
            -> Progress: 25% "Searching Web Search" (via ProgressManager)

            # Deep search with planning
            await reporter.report_stage(operation_id, "planning", "deep", "generating queries", pipeline_type="deep_search")
            -> Progress: 20% "Planning Deep Search - generating queries"

            # Crawl with extraction
            await reporter.report_stage(operation_id, "extracting", "crawl", "readability", pipeline_type="crawl")
            -> Progress: 67% "Extracting Web Crawl - readability"

        Note: Client monitors progress via SSE: GET /progress/{operation_id}/stream
        """
        # Select the appropriate stage dictionary
        if pipeline_type == "deep_search":
            stages = self.DEEP_SEARCH_STAGES
            total_stages = 5
        elif pipeline_type == "crawl":
            stages = self.CRAWL_STAGES
            total_stages = 3
        else:
            stages = self.SEARCH_STAGES
            total_stages = 4

        if stage not in stages:
            logger.warning(f"Unknown stage '{stage}' for pipeline type '{pipeline_type}', skipping progress report")
            return

        stage_info = stages[stage]
        operation_name = self.OPERATION_NAMES.get(operation_type, operation_type.upper())

        # Build progress message
        message = f"{stage_info['label']}"

        # Add operation type if meaningful
        if operation_type not in ["web", "search"]:
            message += f" {operation_name}"

        if sub_progress:
            message += f" - {sub_progress}"

        # Report using ProgressManager (NEW WAY)
        if operation_id:
            await self.base_tool.update_progress_operation(
                operation_id,
                progress=float(stage_info["weight"]),  # 0-100
                current=stage_info["step"],
                total=total_stages,
                message=message
            )

        # Also log for debugging
        prefix = self.STAGE_PREFIXES.get(stage, "[INFO]")
        log_msg = f"{prefix} Stage {stage_info['step']}/{total_stages} ({stage_info['weight']}%): {message}"
        if details:
            log_msg += f" | {details}"

        logger.info(log_msg)

    async def report_granular_progress(
        self,
        operation_id: Optional[str],
        stage: str,
        operation_type: str,
        current: int,
        total: int,
        item_type: str = "item",
        pipeline_type: str = "search"
    ):
        """
        Report granular progress within a stage (for loops/batches)

        This is useful for long-running operations that process multiple items.

        Args:
            operation_id: Operation ID for progress tracking
            stage: Current pipeline stage
            operation_type: Operation type
            current: Current item number (1-indexed)
            total: Total number of items
            item_type: Type of item being processed (e.g., "page", "url", "result")
            pipeline_type: Type of pipeline

        Examples:
            # Fetching multiple URLs
            for i in range(1, total_urls + 1):
                await reporter.report_granular_progress(operation_id, "fetching", "web", i, total_urls, "url")
            -> Progress: 50% "Fetching - url 1/10"
            -> Progress: 50% "Fetching - url 2/10"
            ...

            # Processing search results
            for i in range(1, total_results + 1):
                await reporter.report_granular_progress(operation_id, "processing", "web", i, total_results, "result")
            -> Progress: 75% "Processing - result 5/20"
        """
        sub_progress = f"{item_type} {current}/{total}"
        await self.report_stage(operation_id, stage, operation_type, sub_progress, pipeline_type=pipeline_type)

    async def report_search_progress(
        self,
        operation_id: Optional[str],
        query: str,
        provider: str = "brave",
        result_count: int = 0
    ):
        """
        Report search execution progress

        Args:
            operation_id: Operation ID for progress tracking
            query: Search query
            provider: Search provider name
            result_count: Number of results found

        Example:
            await reporter.report_search_progress(operation_id, "AI agents", "brave", 10)
            -> Progress: 25% "Searching - brave: 10 results"
        """
        sub_progress = f"{provider}: {result_count} results"
        await self.report_stage(operation_id, "searching", "web", sub_progress)

    async def report_fetch_progress(
        self,
        operation_id: Optional[str],
        url: str,
        current: int,
        total: int,
        method: str = "readability"
    ):
        """
        Report URL fetching progress

        Args:
            operation_id: Operation ID for progress tracking
            url: URL being fetched
            current: Current URL number
            total: Total URLs
            method: Extraction method (readability, bs4, vlm)

        Example:
            await reporter.report_fetch_progress(operation_id, "https://example.com", 3, 10, "readability")
            -> Progress: 50% "Fetching - url 3/10 (readability)"
        """
        sub_progress = f"url {current}/{total} ({method})"
        await self.report_stage(operation_id, "fetching", "web", sub_progress)

    async def report_summarization_progress(
        self,
        operation_id: Optional[str],
        content_length: int,
        source_count: int,
        status: str = "generating"
    ):
        """
        Report summarization progress

        Args:
            operation_id: Operation ID for progress tracking
            content_length: Total content length being summarized
            source_count: Number of sources
            status: "generating", "adding citations", "completed"

        Examples:
            await reporter.report_summarization_progress(operation_id, 5000, 5, "generating")
            -> Progress: 100% "Synthesizing - generating summary (5 sources, 5000 chars)"

            await reporter.report_summarization_progress(operation_id, 5000, 5, "adding citations")
            -> Progress: 100% "Synthesizing - adding citations (5 sources)"
        """
        if status == "generating":
            sub_progress = f"generating summary ({source_count} sources, {content_length} chars)"
        elif status == "adding citations":
            sub_progress = f"adding citations ({source_count} sources)"
        else:
            sub_progress = f"{status} ({source_count} sources)"

        await self.report_stage(operation_id, "synthesizing", "summarize", sub_progress)

    async def report_deep_search_iteration(
        self,
        operation_id: Optional[str],
        iteration: int,
        total_iterations: int,
        query: str
    ):
        """
        Report deep search iteration progress

        Args:
            operation_id: Operation ID for progress tracking
            iteration: Current iteration number
            total_iterations: Total iterations planned
            query: Current search query

        Example:
            await reporter.report_deep_search_iteration(operation_id, 2, 3, "machine learning frameworks")
            -> Progress: 40% "Multi-Stage Search Deep Search - iteration 2/3: machine learning frameworks"
        """
        sub_progress = f"iteration {iteration}/{total_iterations}: {query[:50]}"
        await self.report_stage(operation_id, "searching", "deep", sub_progress, pipeline_type="deep_search")

    async def report_complete(
        self,
        operation_type: str,
        summary: Optional[Dict[str, Any]] = None
    ):
        """
        Report completion of entire pipeline

        Args:
            operation_type: Operation type
            summary: Optional summary statistics

        Example:
            await reporter.report_complete("web", {
                "results": 10,
                "urls_fetched": 5,
                "summary_length": 500,
                "citations": 5
            })
            -> "[DONE] Web Search complete | {'results': 10, 'urls_fetched': 5, ...}"
        """
        operation_name = self.OPERATION_NAMES.get(operation_type, operation_type.upper())
        message = f"[DONE] {operation_name} complete"

        if summary:
            message += f" | {summary}"

        logger.info(message)


class SearchOperationDetector:
    """
    Utility class to detect and categorize search operations
    """

    @classmethod
    def detect_operation_type(cls, query: str, options: Dict[str, Any]) -> str:
        """
        Detect operation type from query and options

        Args:
            query: Search query
            options: Search options dict

        Returns:
            Operation type: "web", "deep", "summarize"

        Example:
            detect_operation_type("AI", {"deep_search": True}) -> "deep"
            detect_operation_type("AI", {"summarize": True}) -> "summarize"
        """
        if options.get("deep_search") or options.get("deep_mode"):
            return "deep"
        elif options.get("summarize"):
            return "summarize"
        else:
            return "web"

    @classmethod
    def should_fetch_content(cls, options: Dict[str, Any]) -> bool:
        """
        Determine if content fetching is needed

        Args:
            options: Search options

        Returns:
            True if content fetching is needed
        """
        return (
            options.get("summarize", False) or
            options.get("deep_search", False) or
            options.get("fetch_content", False)
        )
