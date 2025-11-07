#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Crawl Progress Context Module

Specialized progress tracking for web crawling and content extraction operations.
Provides standardized 5-stage progress reporting for crawl operations.

Pipeline Stages:
1. Checking (20%) - Validate URL and robots.txt compliance
2. Fetching (40%) - Fetch HTML content
3. Extracting (60%) - Extract content using readability/BS4
4. Analyzing (80%) - Analyze and synthesize content
5. Synthesizing (100%) - Generate final report (for multi-URL comparison)

Supported Operations: Single URL crawl, Multi-URL comparison
"""

from typing import Dict, Any, Optional
from tools.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class WebCrawlProgressReporter:
    """
    Specialized progress reporting for web crawl operations

    Provides a standardized 5-stage pipeline progress tracking:
    1. Checking (20%) - Validate URL and robots.txt compliance
    2. Fetching (40%) - Fetch HTML content
    3. Extracting (60%) - Extract content using readability/BS4/VLM
    4. Analyzing (80%) - Analyze and synthesize content
    5. Synthesizing (100%) - Generate final report (for comparison)

    Supports: Single URL crawl, Multi-URL comparison, Enhanced extraction

    Example:
        reporter = WebCrawlProgressReporter(base_tool)

        # Create operation at start
        operation_id = await base_tool.create_progress_operation(metadata={...})

        # Stage 1: Checking
        await reporter.report_stage(operation_id, "checking", "web", "robots.txt compliance")

        # Stage 2: Fetching
        await reporter.report_stage(operation_id, "fetching", "web", url)

        # Stage 3: Extracting
        await reporter.report_stage(operation_id, "extracting", "web", "readability extraction")

        # Stage 4: Analyzing (if analysis_request provided)
        await reporter.report_stage(operation_id, "analyzing", "web", "generating analysis")

        # Complete operation
        await base_tool.complete_progress_operation(operation_id, result={...})
    """

    # Single URL crawl pipeline stages
    CRAWL_STAGES = {
        "checking": {"step": 1, "weight": 20, "label": "Checking"},
        "fetching": {"step": 2, "weight": 40, "label": "Fetching"},
        "extracting": {"step": 3, "weight": 60, "label": "Extracting"},
        "analyzing": {"step": 4, "weight": 80, "label": "Analyzing"}
    }

    # Multi-URL comparison pipeline stages
    COMPARE_STAGES = {
        "checking": {"step": 1, "weight": 15, "label": "Checking"},
        "fetching": {"step": 2, "weight": 40, "label": "Fetching"},
        "extracting": {"step": 3, "weight": 60, "label": "Extracting"},
        "analyzing": {"step": 4, "weight": 80, "label": "Analyzing"},
        "synthesizing": {"step": 5, "weight": 100, "label": "Synthesizing"}
    }

    # Operation type display names
    OPERATION_NAMES = {
        "web": "Web Crawl",
        "compare": "Multi-URL Comparison",
        "extract": "Content Extraction"
    }

    # Stage-specific prefixes for logging
    STAGE_PREFIXES = {
        "checking": "[CHECK]",
        "fetching": "[FETCH]",
        "extracting": "[EXTRACT]",
        "analyzing": "[ANALYZE]",
        "synthesizing": "[SYNTH]"
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
        pipeline_type: str = "crawl"
    ):
        """
        Report progress for a pipeline stage using ProgressManager

        Args:
            operation_id: Operation ID for progress tracking (use ProgressManager)
            stage: Pipeline stage name (varies by pipeline_type)
            operation_type: Operation type - "web", "compare", "extract"
            sub_progress: Optional granular progress within stage
            details: Optional additional details for logging
            pipeline_type: Type of pipeline - "crawl" or "compare"

        Pipeline Types & Stages:
            crawl: checking -> fetching -> extracting -> analyzing (4 stages)
            compare: checking -> fetching -> extracting -> analyzing -> synthesizing (5 stages)

        Examples:
            # Single URL crawl
            await reporter.report_stage(operation_id, "checking", "web", "robots.txt", pipeline_type="crawl")
            -> Progress: 20% "Checking Web Crawl - robots.txt"

            # Multi-URL comparison
            await reporter.report_stage(operation_id, "synthesizing", "compare", "generating report", pipeline_type="compare")
            -> Progress: 100% "Synthesizing Multi-URL Comparison - generating report"

        Note: Client monitors progress via SSE: GET /progress/{operation_id}/stream
        """
        # Select the appropriate stage dictionary
        if pipeline_type == "compare":
            stages = self.COMPARE_STAGES
            total_stages = 5
        else:
            stages = self.CRAWL_STAGES
            total_stages = 4

        if stage not in stages:
            logger.warning(f"Unknown stage '{stage}' for pipeline type '{pipeline_type}', skipping progress report")
            return

        stage_info = stages[stage]
        operation_name = self.OPERATION_NAMES.get(operation_type, operation_type.upper())

        # Build progress message
        message = f"{stage_info['label']}"

        # Add operation type if meaningful
        if operation_type not in ["web"]:
            message += f" {operation_name}"

        if sub_progress:
            message += f" - {sub_progress}"

        # Report using ProgressManager
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
        item_type: str = "url",
        pipeline_type: str = "crawl"
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
            item_type: Type of item being processed (e.g., "url", "page")
            pipeline_type: Type of pipeline

        Examples:
            # Fetching multiple URLs
            for i in range(1, total_urls + 1):
                await reporter.report_granular_progress(operation_id, "fetching", "compare", i, total_urls, "url")
            -> Progress: 40% "Fetching - url 1/5"
            -> Progress: 40% "Fetching - url 2/5"
            ...
        """
        sub_progress = f"{item_type} {current}/{total}"
        await self.report_stage(operation_id, stage, operation_type, sub_progress, pipeline_type=pipeline_type)

    async def report_robots_check(
        self,
        operation_id: Optional[str],
        url: str,
        allowed: bool,
        reason: str = ""
    ):
        """
        Report robots.txt compliance check

        Args:
            operation_id: Operation ID for progress tracking
            url: URL being checked
            allowed: Whether crawling is allowed
            reason: Reason for the decision

        Example:
            await reporter.report_robots_check(operation_id, "https://example.com", True, "allowed by robots.txt")
            -> Progress: 20% "Checking - robots.txt allows access"
        """
        status = "allows access" if allowed else "blocks access"
        sub_progress = f"robots.txt {status}"
        if reason:
            sub_progress += f" ({reason})"
        await self.report_stage(operation_id, "checking", "web", sub_progress)

    async def report_fetch_progress(
        self,
        operation_id: Optional[str],
        url: str,
        status: str = "fetching"
    ):
        """
        Report URL fetching progress

        Args:
            operation_id: Operation ID for progress tracking
            url: URL being fetched
            status: Fetch status (fetching, fetched, failed)

        Example:
            await reporter.report_fetch_progress(operation_id, "https://example.com", "fetched")
            -> Progress: 40% "Fetching - example.com"
        """
        # Extract domain from URL for brevity
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            sub_progress = f"{domain}"
        except:
            sub_progress = url[:50]

        if status != "fetching":
            sub_progress += f" ({status})"

        await self.report_stage(operation_id, "fetching", "web", sub_progress)

    async def report_extraction_progress(
        self,
        operation_id: Optional[str],
        method: str,
        status: str = "extracting"
    ):
        """
        Report content extraction progress

        Args:
            operation_id: Operation ID for progress tracking
            method: Extraction method (readability, bs4, vlm)
            status: Extraction status

        Examples:
            await reporter.report_extraction_progress(operation_id, "readability", "extracting")
            -> Progress: 60% "Extracting - readability"

            await reporter.report_extraction_progress(operation_id, "bs4", "extracted")
            -> Progress: 60% "Extracting - bs4 (extracted)"
        """
        sub_progress = f"{method}"
        if status != "extracting":
            sub_progress += f" ({status})"

        await self.report_stage(operation_id, "extracting", "web", sub_progress)

    async def report_analysis_progress(
        self,
        operation_id: Optional[str],
        content_length: int,
        status: str = "analyzing"
    ):
        """
        Report content analysis progress

        Args:
            operation_id: Operation ID for progress tracking
            content_length: Content length being analyzed
            status: Analysis status

        Example:
            await reporter.report_analysis_progress(operation_id, 5000, "generating analysis")
            -> Progress: 80% "Analyzing - generating analysis (5000 chars)"
        """
        sub_progress = f"{status} ({content_length} chars)"
        await self.report_stage(operation_id, "analyzing", "web", sub_progress)

    async def report_comparison_synthesis(
        self,
        operation_id: Optional[str],
        url_count: int,
        status: str = "generating report"
    ):
        """
        Report comparison report synthesis progress

        Args:
            operation_id: Operation ID for progress tracking
            url_count: Number of URLs being compared
            status: Synthesis status

        Example:
            await reporter.report_comparison_synthesis(operation_id, 5, "generating report")
            -> Progress: 100% "Synthesizing - generating report (5 URLs)"
        """
        sub_progress = f"{status} ({url_count} URLs)"
        await self.report_stage(operation_id, "synthesizing", "compare", sub_progress, pipeline_type="compare")

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
                "method": "readability",
                "word_count": 500,
                "success": True
            })
            -> "[DONE] Web Crawl complete | {'method': 'readability', 'word_count': 500, ...}"
        """
        operation_name = self.OPERATION_NAMES.get(operation_type, operation_type.upper())
        message = f"[DONE] {operation_name} complete"

        if summary:
            message += f" | {summary}"

        logger.info(message)


class CrawlOperationDetector:
    """
    Utility class to detect and categorize crawl operations
    """

    @classmethod
    def detect_operation_type(cls, url: str, options: Dict[str, Any]) -> str:
        """
        Detect operation type from URL and options

        Args:
            url: Target URL (or list of URLs)
            options: Crawl options dict

        Returns:
            Operation type: "web", "compare"

        Example:
            detect_operation_type("https://example.com", {}) -> "web"
            detect_operation_type(["url1", "url2"], {"analysis_request": "compare"}) -> "compare"
        """
        # Check if multiple URLs
        if isinstance(url, list) and len(url) > 1:
            return "compare"
        return "web"

    @classmethod
    def should_analyze(cls, options: Dict[str, Any]) -> bool:
        """
        Determine if analysis is needed

        Args:
            options: Crawl options

        Returns:
            True if analysis is needed
        """
        return bool(options.get("analysis_request"))

    @classmethod
    def get_extraction_method_priority(cls) -> list:
        """
        Get extraction method priority order

        Returns:
            List of extraction methods in priority order
        """
        return ["readability", "bs4", "vlm"]
