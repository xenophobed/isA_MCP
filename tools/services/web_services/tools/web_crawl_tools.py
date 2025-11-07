#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Crawl Tools - Clean MCP Tool Wrapper

Thin MCP wrapper for web crawling functionality.
All business logic is in WebCrawlService.

Core Functions:
- web_crawl: Intelligent web page crawling with hybrid extraction
- web_crawl_compare: Multi-URL comparison and analysis

Architecture:
- This file: MCP tool interface + progress tracking
- web_crawl_service.py: Business logic for crawling and extraction
- crawl_progress_context.py: Progress reporting and SSE streaming
"""

from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations
from tools.base_tool import BaseTool
from tools.services.web_services.services.web_crawl_service import WebCrawlService
from tools.services.web_services.tools.context import WebCrawlProgressReporter
from core.security import SecurityLevel
from core.logging import get_logger

logger = get_logger(__name__)


class WebCrawlTool(BaseTool):
    """Web crawl tool with progress tracking"""

    def __init__(self):
        super().__init__()
        self.crawl_service = WebCrawlService()
        self.progress_reporter = WebCrawlProgressReporter(self)

    async def web_crawl_impl(
        self,
        url: str,
        analysis_request: Optional[str] = None,

        # Progress monitoring (optional)
        operation_id: Optional[str] = None,

        # Context (will be injected by FastMCP)
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Intelligently crawl and analyze web pages with hybrid extraction

        Uses a smart extraction strategy:
        1. **Default**: BeautifulSoup4 (fast, clean text extraction)
        2. **Enhanced**: Readability + BS4 (article content, metadata, SEO)
        3. **Fallback**: VLM analysis (screenshot-based for dynamic content)

        Extraction modes:
        - **Basic** (no analysis_request): Fast text, headings, paragraphs, links
        - **Enhanced** (with analysis_request): Full structured data extraction including:
          * Tables with preserved structure
          * Images with alt text and dimensions
          * Video detection (HTML5 and iframe embeds)
          * Code block extraction with language detection
          * Form structure and fields
          * OpenGraph, Twitter Cards, JSON-LD metadata
          * SEO analysis (title, meta, H1/H2, links, schema.org)
          * Flesch Reading Ease readability scoring
          * Detailed extraction statistics

        Features:
        - Robots.txt compliance checking
        - Automatic fallback to VLM for dynamic content
        - AI-powered content analysis and summarization
        - Progress tracking via SSE

        Args:
            url: Target web page URL
            analysis_request: Optional analysis request (triggers enhanced mode)
                             e.g., "extract main article content", "analyze SEO"
            operation_id: Optional operation ID for SSE progress monitoring

        Examples:
            # Basic crawl
            web_crawl(url="https://example.com")

            # Enhanced crawl with analysis
            web_crawl(
                url="https://example.com",
                analysis_request="extract tables and forms"
            )

            # With progress monitoring
            import uuid
            op_id = str(uuid.uuid4())

            # Start crawl with custom operation_id
            crawl_task = asyncio.create_task(
                web_crawl(url="https://example.com", operation_id=op_id)
            )

            # Concurrently monitor progress via SSE
            await stream_progress(op_id)

            # Get result
            result = await crawl_task
        """
        # Create or use provided progress operation
        if not operation_id:
            operation_id = await self.create_progress_operation(
                metadata={
                    "url": url,
                    "has_analysis": bool(analysis_request),
                    "operation": "web_crawl"
                }
            )
        else:
            # Use client-provided operation_id
            await self.create_progress_operation(
                operation_id=operation_id,
                metadata={
                    "url": url,
                    "has_analysis": bool(analysis_request),
                    "operation": "web_crawl"
                }
            )

        try:
            await self.log_info(ctx, f"Starting web crawl: {url}")

            # Stage 1: Checking robots.txt
            await self.progress_reporter.report_stage(
                operation_id, "checking", "web", "robots.txt compliance"
            )

            # Stage 2: Fetching content
            await self.progress_reporter.report_stage(
                operation_id, "fetching", "web", url
            )

            # Stage 3: Extracting content
            await self.progress_reporter.report_stage(
                operation_id, "extracting", "web", "extracting page content"
            )

            # Execute crawl
            result = await self.crawl_service.crawl_and_analyze(url, analysis_request)

            # Stage 4: Analyzing (if requested)
            if analysis_request:
                await self.progress_reporter.report_stage(
                    operation_id, "analyzing", "web", "analyzing content"
                )

            # Report completion
            if result.get("success"):
                extraction_method = result.get("result", {}).get("method", "unknown")
                word_count = result.get("result", {}).get("word_count", 0)

                await self.log_info(
                    ctx,
                    f"✅ Crawl complete: {extraction_method}, {word_count} words"
                )

                await self.progress_reporter.report_complete(
                    "web",
                    {
                        "method": extraction_method,
                        "word_count": word_count
                    }
                )

                # Complete progress operation
                await self.complete_progress_operation(
                    operation_id,
                    result={
                        "method": extraction_method,
                        "word_count": word_count
                    }
                )
            else:
                error_msg = result.get("error", "Unknown error")
                await self.log_error(ctx, f"Crawl failed: {error_msg}")
                await self.fail_progress_operation(operation_id, error_msg)

            # Extract context info
            context_info = self.extract_context_info(ctx)

            # Return response
            if result.get("success"):
                return self.create_response(
                    "success",
                    "web_crawl",
                    {
                        **result,
                        "operation_id": operation_id,  # ✅ Return operation_id for SSE monitoring
                        "context": context_info
                    }
                )
            else:
                return self.create_response(
                    "error",
                    "web_crawl",
                    {
                        "url": url,
                        "context": context_info
                    },
                    result.get("error", "Unknown error")
                )

        except Exception as e:
            # Fail progress operation on error
            if 'operation_id' in locals():
                await self.fail_progress_operation(operation_id, str(e))

            await self.log_error(ctx, f"Web crawl failed: {str(e)}")

            # Extract context even in error case
            context_info = self.extract_context_info(ctx)

            return self.create_response(
                "error",
                "web_crawl",
                {
                    "url": url,
                    "context": context_info
                },
                f"Crawl failed: {str(e)}"
            )

    async def web_crawl_compare_impl(
        self,
        urls: List[str],
        analysis_request: str,

        # Progress monitoring (optional)
        operation_id: Optional[str] = None,

        # Context (will be injected by FastMCP)
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Crawl and compare multiple web pages

        Crawls multiple URLs and generates a comprehensive comparison report
        analyzing similarities, differences, and patterns across the pages.

        Features:
        - Parallel crawling of multiple URLs
        - Individual page analysis
        - AI-powered comparison and synthesis
        - Progress tracking for each URL
        - Structured comparison report

        Args:
            urls: List of URLs to compare (2-10 URLs recommended)
            analysis_request: Comparison request (e.g., "compare product features",
                            "analyze pricing strategies", "compare article topics")
            operation_id: Optional operation ID for SSE progress monitoring

        Examples:
            # Compare product pages
            web_crawl_compare(
                urls=["https://site1.com/product", "https://site2.com/product"],
                analysis_request="compare product features and pricing"
            )

            # Analyze news coverage
            web_crawl_compare(
                urls=["https://news1.com/article", "https://news2.com/article"],
                analysis_request="compare news coverage and perspectives"
            )

            # With progress monitoring
            import uuid
            op_id = str(uuid.uuid4())

            crawl_task = asyncio.create_task(
                web_crawl_compare(
                    urls=["https://site1.com", "https://site2.com"],
                    analysis_request="compare content",
                    operation_id=op_id
                )
            )

            # Monitor via SSE
            await stream_progress(op_id)

            result = await crawl_task
        """
        # Create or use provided progress operation
        if not operation_id:
            operation_id = await self.create_progress_operation(
                metadata={
                    "urls_count": len(urls),
                    "urls": urls[:3],  # First 3 URLs
                    "analysis_request": analysis_request[:100],
                    "operation": "web_crawl_compare"
                }
            )
        else:
            # Use client-provided operation_id
            await self.create_progress_operation(
                operation_id=operation_id,
                metadata={
                    "urls_count": len(urls),
                    "urls": urls[:3],
                    "analysis_request": analysis_request[:100],
                    "operation": "web_crawl_compare"
                }
            )

        try:
            await self.log_info(ctx, f"Starting multi-URL crawl: {len(urls)} URLs")

            # Validate URL count
            if len(urls) < 2:
                error_msg = "At least 2 URLs are required for comparison"
                await self.fail_progress_operation(operation_id, error_msg)
                return self.create_response(
                    "error",
                    "web_crawl_compare",
                    {"urls": urls},
                    error_msg
                )

            if len(urls) > 10:
                error_msg = "Maximum 10 URLs allowed for comparison"
                await self.fail_progress_operation(operation_id, error_msg)
                return self.create_response(
                    "error",
                    "web_crawl_compare",
                    {"urls": urls},
                    error_msg
                )

            # Stage 1: Checking
            await self.progress_reporter.report_stage(
                operation_id, "checking", "compare", f"{len(urls)} URLs", pipeline_type="compare"
            )

            # Stage 2: Fetching (with granular progress)
            for i, url in enumerate(urls, 1):
                await self.progress_reporter.report_granular_progress(
                    operation_id, "fetching", "compare", i, len(urls), "url", pipeline_type="compare"
                )

                await self.log_info(ctx, f"Processing URL {i}/{len(urls)}: {url}")

            # Execute comparison
            result = await self.crawl_service.crawl_and_compare_multiple(urls, analysis_request)

            # Stage 5: Synthesizing comparison
            await self.progress_reporter.report_stage(
                operation_id, "synthesizing", "compare", "generating comparison report", pipeline_type="compare"
            )

            # Report completion
            if result.get("success"):
                successful_count = sum(
                    1 for r in result.get("individual_results", [])
                    if r.get("success")
                )

                await self.log_info(
                    ctx,
                    f"✅ Comparison complete: {successful_count}/{len(urls)} URLs succeeded"
                )

                await self.progress_reporter.report_complete(
                    "compare",
                    {
                        "total_urls": len(urls),
                        "successful": successful_count
                    }
                )

                # Complete progress operation
                await self.complete_progress_operation(
                    operation_id,
                    result={
                        "total_urls": len(urls),
                        "successful": successful_count
                    }
                )
            else:
                error_msg = result.get("error", "Unknown error")
                await self.log_error(ctx, f"Comparison failed: {error_msg}")
                await self.fail_progress_operation(operation_id, error_msg)

            # Extract context info
            context_info = self.extract_context_info(ctx)

            # Return response
            if result.get("success"):
                return self.create_response(
                    "success",
                    "web_crawl_compare",
                    {
                        **result,
                        "operation_id": operation_id,  # ✅ Return operation_id for SSE monitoring
                        "context": context_info
                    }
                )
            else:
                return self.create_response(
                    "error",
                    "web_crawl_compare",
                    {
                        "urls": urls,
                        "context": context_info
                    },
                    result.get("error", "Unknown error")
                )

        except Exception as e:
            # Fail progress operation on error
            if 'operation_id' in locals():
                await self.fail_progress_operation(operation_id, str(e))

            await self.log_error(ctx, f"Multi-URL crawl failed: {str(e)}")

            # Extract context even in error case
            context_info = self.extract_context_info(ctx)

            return self.create_response(
                "error",
                "web_crawl_compare",
                {
                    "urls": urls,
                    "context": context_info
                },
                f"Comparison failed: {str(e)}"
            )


def register_web_crawl_tools(mcp: FastMCP):
    """Register web crawl tools"""
    crawl_tool = WebCrawlTool()

    # Register web_crawl
    crawl_tool.register_tool(
        mcp,
        crawl_tool.web_crawl_impl,
        name="web_crawl",
        description="Intelligently crawl and analyze web pages with hybrid extraction. "
                    "Supports robots.txt compliance, readability extraction, BS4 parsing, "
                    "and VLM fallback for dynamic content. Real-time progress monitoring via SSE. "
                    "Keywords: crawl, scrape, extract, analyze, web, page, content, readability, seo, progress. "
                    "Category: web",
        security_level=SecurityLevel.LOW,
        timeout=120.0,
        annotations=ToolAnnotations(
            readOnlyHint=True
        )
    )

    # Register web_crawl_compare
    crawl_tool.register_tool(
        mcp,
        crawl_tool.web_crawl_compare_impl,
        name="web_crawl_compare",
        description="Crawl and compare multiple web pages with AI-powered analysis. "
                    "Generates comprehensive comparison reports analyzing similarities, differences, "
                    "and patterns across pages. Real-time progress monitoring via SSE. "
                    "Keywords: compare, crawl, analyze, multiple, urls, comparison, progress. "
                    "Category: web",
        security_level=SecurityLevel.LOW,
        timeout=300.0,  # Longer timeout for multiple URLs
        annotations=ToolAnnotations(
            readOnlyHint=True
        )
    )

    logger.info("✅ Web Crawl Tools registered: 2 functions")
    logger.info("🕷️ web_crawl: Hybrid extraction with progress tracking")
    logger.info("🔀 web_crawl_compare: Multi-URL comparison and analysis")
    logger.info("")
    logger.info("📊 Usage:")
    logger.info("   Simple: web_crawl(url='https://example.com')")
    logger.info("   Enhanced: web_crawl(url='...', analysis_request='extract tables')")
    logger.info("   Compare: web_crawl_compare(urls=[...], analysis_request='compare features')")
    logger.info("   With progress: web_crawl(url='...', operation_id='custom-id')")
    logger.info("   Monitor via SSE: GET /progress/{operation_id}/stream")

    return crawl_tool
