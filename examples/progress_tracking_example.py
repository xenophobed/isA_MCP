#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Progress Tracking Example - New ProgressManager Pattern
========================================================

This example demonstrates the CORRECT way to implement progress tracking
in MCP tools using the new ProgressManager architecture.

Key Changes:
- ❌ OLD: Pass `ctx` to progress reporter methods
- ✅ NEW: Create `operation_id` at start, pass it to progress reporter methods

Architecture:
- ProgressManager: Redis-based, stateless progress tracking
- SSE Streaming: Real-time progress updates via GET /progress/{operation_id}/stream
- Progress Context Modules: Standardized reporting for different service types
"""

from typing import Dict, Any, Optional
from tools.base_tool import BaseTool
from mcp.server.fastmcp import Context


class ProgressTrackingExampleTool(BaseTool):
    """Example tool demonstrating new progress tracking pattern"""

    def __init__(self):
        super().__init__()
        # Initialize progress reporter (varies by service type)
        from tools.services.data_analytics_service.tools.context.digital_progress_context import (
            DigitalAssetProgressReporter
        )
        self.progress_reporter = DigitalAssetProgressReporter(self)

    # ============================================================================
    # EXAMPLE 1: Basic Progress Tracking
    # ============================================================================

    async def process_document_new_way(
        self,
        user_id: str,
        document_path: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """
        ✅ CORRECT: New ProgressManager pattern

        Steps:
        1. Create progress operation → get operation_id
        2. Pass operation_id (not ctx) to all progress reporter methods
        3. Complete operation when done
        4. Return operation_id to client for SSE monitoring
        """
        try:
            # Step 1: Create progress operation (NEW WAY)
            operation_id = await self.create_progress_operation(
                metadata={
                    "user_id": user_id,
                    "document_path": document_path,
                    "operation": "process_document"
                }
            )

            # Step 2: Report progress using operation_id (NEW WAY)
            # ✅ Pass operation_id (not ctx!)
            await self.progress_reporter.report_stage(
                operation_id,  # ✅ NEW: operation_id
                "processing",
                "pdf",
                pipeline_type="ingestion"
            )

            # Simulate document processing
            await self._extract_text(document_path)

            await self.progress_reporter.report_stage(
                operation_id,  # ✅ NEW: operation_id
                "extraction",
                "pdf",
                "extracting pages",
                pipeline_type="ingestion"
            )

            # More processing...
            result = await self._analyze_content()

            await self.progress_reporter.report_stage(
                operation_id,  # ✅ NEW: operation_id
                "embedding",
                "pdf",
                pipeline_type="ingestion"
            )

            await self.progress_reporter.report_stage(
                operation_id,  # ✅ NEW: operation_id
                "storing",
                "pdf",
                pipeline_type="ingestion"
            )

            # Step 3: Complete operation (NEW WAY)
            await self.complete_progress_operation(
                operation_id,
                result={"pages": 10, "success": True}
            )

            # Step 4: Return operation_id for client monitoring
            return self.create_response(
                "success",
                "process_document",
                {
                    "operation_id": operation_id,  # ✅ Client can monitor via SSE
                    "result": result,
                    "message": "Processing started. Monitor via: GET /progress/{operation_id}/stream",
                    "context": self.extract_context_info(ctx)
                }
            )

        except Exception as e:
            # Fail operation on error
            if 'operation_id' in locals():
                await self.fail_progress_operation(operation_id, str(e))

            return self.create_response(
                "error",
                "process_document",
                {"user_id": user_id},
                error_message=str(e)
            )

    # ============================================================================
    # EXAMPLE 2: Granular Progress (loops/batches)
    # ============================================================================

    async def process_multi_page_document(
        self,
        user_id: str,
        document_path: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """
        ✅ CORRECT: Granular progress reporting in loops
        """
        operation_id = await self.create_progress_operation(
            metadata={"user_id": user_id, "operation": "multi_page_processing"}
        )

        try:
            total_pages = 20  # Example

            # Stage 1: Processing
            await self.progress_reporter.report_stage(
                operation_id, "processing", "pdf"
            )

            # Stage 2: Extraction with granular progress
            for page_num in range(1, total_pages + 1):
                # Process page...
                await self._process_page(page_num)

                # Report granular progress
                await self.progress_reporter.report_granular_progress(
                    operation_id,  # ✅ NEW: operation_id
                    "extraction",
                    "pdf",
                    current=page_num,
                    total=total_pages,
                    item_type="page",
                    pipeline_type="ingestion"
                )

            # Stage 3: Embedding
            await self.progress_reporter.report_stage(
                operation_id, "embedding", "pdf"
            )

            # Stage 4: Storage with specific targets
            await self.progress_reporter.report_storage_progress(
                operation_id,  # ✅ NEW: operation_id
                "pdf",
                "minio",
                "uploading",
                pipeline_type="ingestion"
            )

            await self.progress_reporter.report_storage_progress(
                operation_id,  # ✅ NEW: operation_id
                "pdf",
                "vector_db",
                "indexing",
                pipeline_type="ingestion"
            )

            # Complete with summary
            await self.progress_reporter.report_complete(
                "pdf",  # ✅ NEW: No ctx parameter!
                {"pages": total_pages, "success": True}
            )

            await self.complete_progress_operation(
                operation_id,
                result={"total_pages": total_pages}
            )

            return self.create_response(
                "success",
                "process_multi_page_document",
                {
                    "operation_id": operation_id,
                    "pages_processed": total_pages,
                    "context": self.extract_context_info(ctx)
                }
            )

        except Exception as e:
            await self.fail_progress_operation(operation_id, str(e))
            raise

    # ============================================================================
    # EXAMPLE 3: Using Different Progress Reporters
    # ============================================================================

    async def web_search_example(
        self,
        query: str,
        user_id: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """
        ✅ CORRECT: Using WebSearchProgressReporter
        """
        # Use web search progress reporter
        from tools.services.web_services.tools.context.search_progress_context import (
            WebSearchProgressReporter
        )
        search_reporter = WebSearchProgressReporter(self)

        operation_id = await self.create_progress_operation(
            metadata={"query": query, "user_id": user_id}
        )

        try:
            # Search pipeline stages
            await search_reporter.report_stage(
                operation_id,  # ✅ NEW
                "searching",
                "web",
                pipeline_type="search"
            )

            # Execute search...
            results = await self._perform_search(query)

            await search_reporter.report_stage(
                operation_id,  # ✅ NEW
                "fetching",
                "web",
                f"fetching {len(results)} URLs",
                pipeline_type="search"
            )

            # Fetch content...
            content = await self._fetch_content(results)

            await search_reporter.report_stage(
                operation_id,  # ✅ NEW
                "processing",
                "web",
                "analyzing content",
                pipeline_type="search"
            )

            await search_reporter.report_stage(
                operation_id,  # ✅ NEW
                "synthesizing",
                "web",
                "generating summary",
                pipeline_type="search"
            )

            await search_reporter.report_complete(
                "web",  # ✅ NEW: No ctx!
                {"results": len(results)}
            )

            await self.complete_progress_operation(operation_id, {"results": len(results)})

            return self.create_response(
                "success",
                "web_search",
                {
                    "operation_id": operation_id,
                    "results": results,
                    "context": self.extract_context_info(ctx)
                }
            )

        except Exception as e:
            await self.fail_progress_operation(operation_id, str(e))
            raise

    # ============================================================================
    # ❌ WRONG WAY (Old Pattern) - DO NOT USE!
    # ============================================================================

    async def process_document_old_way_WRONG(
        self,
        user_id: str,
        document_path: str,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """
        ❌ WRONG: Old Context-based pattern (DEPRECATED)

        Problems:
        - Passes ctx to progress methods (won't work with new reporters)
        - No operation_id for client monitoring
        - Doesn't work with stateless HTTP/SSE
        """
        try:
            # ❌ WRONG: Passing ctx instead of operation_id
            await self.progress_reporter.report_stage(
                ctx,  # ❌ OLD: This won't work!
                "processing",
                "pdf"
            )

            # ... rest of processing ...

            # ❌ No operation_id to return for monitoring
            return self.create_response(
                "success",
                "process_document",
                {"result": "done"}
            )

        except Exception as e:
            return self.create_response(
                "error",
                "process_document",
                {},
                error_message=str(e)
            )

    # ============================================================================
    # Helper Methods
    # ============================================================================

    async def _extract_text(self, path: str):
        """Simulate text extraction"""
        import asyncio
        await asyncio.sleep(0.1)

    async def _analyze_content(self) -> Dict[str, Any]:
        """Simulate content analysis"""
        import asyncio
        await asyncio.sleep(0.1)
        return {"pages": 10, "words": 5000}

    async def _process_page(self, page_num: int):
        """Simulate page processing"""
        import asyncio
        await asyncio.sleep(0.05)

    async def _perform_search(self, query: str):
        """Simulate search"""
        import asyncio
        await asyncio.sleep(0.1)
        return [{"url": "https://example.com", "title": "Example"}]

    async def _fetch_content(self, results):
        """Simulate content fetching"""
        import asyncio
        await asyncio.sleep(0.1)
        return "content"


# ============================================================================
# CLIENT-SIDE MONITORING EXAMPLE
# ============================================================================

CLIENT_MONITORING_EXAMPLE = """
# How clients monitor progress (SSE Streaming):

# 1. Call the tool and get operation_id
response = await call_tool("process_document", {
    "user_id": "user123",
    "document_path": "/path/to/doc.pdf"
})

operation_id = response["data"]["operation_id"]

# 2. Monitor progress via SSE (Server-Sent Events)
import httpx

async with httpx.AsyncClient() as client:
    async with client.stream(
        "GET",
        f"http://localhost:8081/progress/{operation_id}/stream"
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                print(f"Progress: {data['progress']}% - {data['message']}")

                if data['status'] == 'completed':
                    print("Done!", data['result'])
                    break
                elif data['status'] == 'failed':
                    print("Failed:", data['error'])
                    break

# 3. Alternative: Polling (not recommended, SSE is better)
status = await call_tool("get_task_progress", {
    "operation_id": operation_id
})
"""


# ============================================================================
# MIGRATION CHECKLIST
# ============================================================================

MIGRATION_CHECKLIST = """
✅ Progress Tracking Migration Checklist
=========================================

For each tool method that uses progress tracking:

1. ✅ Create operation_id at method start:
   operation_id = await self.create_progress_operation(metadata={...})

2. ✅ Update all progress_reporter calls:
   OLD: await self.progress_reporter.report_stage(ctx, ...)
   NEW: await self.progress_reporter.report_stage(operation_id, ...)

3. ✅ Update report_complete calls:
   OLD: await self.progress_reporter.report_complete(ctx, asset_type, summary)
   NEW: await self.progress_reporter.report_complete(asset_type, summary)

4. ✅ Complete operation at end:
   await self.complete_progress_operation(operation_id, result={...})

5. ✅ Handle errors:
   await self.fail_progress_operation(operation_id, error_message)

6. ✅ Return operation_id to client:
   return self.create_response("success", "my_tool", {
       "operation_id": operation_id,
       ...
   })

7. ✅ Remove any ctx parameters from progress calls

Files to update:
- tools/services/data_analytics_service/tools/digital_tools.py (~25 calls)
- tools/services/data_analytics_service/tools/data_tools.py (~20 calls)
- tools/services/web_services/tools/web_search_tools.py (~11 calls)
- tools/services/web_services/tools/web_automation_tools.py (~8 calls)
"""


if __name__ == "__main__":
    print("Progress Tracking Example")
    print("=" * 70)
    print()
    print("This example shows the CORRECT way to implement progress tracking")
    print("using the new ProgressManager architecture.")
    print()
    print("Key Points:")
    print("  1. Create operation_id at start")
    print("  2. Pass operation_id (not ctx) to progress methods")
    print("  3. Complete operation when done")
    print("  4. Return operation_id for client monitoring")
    print()
    print("Client Monitoring:")
    print(CLIENT_MONITORING_EXAMPLE)
    print()
    print(MIGRATION_CHECKLIST)
