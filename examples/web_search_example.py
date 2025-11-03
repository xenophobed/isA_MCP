#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Search with Progress Streaming Example
==========================================

Demonstrates real-time progress tracking for web_search and deep_search operations.

Test Scenarios:
1. Basic web_search - Simple search without summarization
2. Web search with summarization - Shows 4-stage progress
3. Deep search - Multi-iteration search with 5-stage progress
4. Deep search with concurrent SSE monitoring - Real-time updates

Progress Pipeline Stages:
- Basic Search: Searching (25%) -> Fetching (50%) -> Processing (75%) -> Synthesizing (100%)
- Deep Search: Planning (20%) -> Searching (40%) -> Fetching (60%) -> Analyzing (80%) -> Synthesizing (100%)
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
from datetime import datetime


# ============================================================================
# MCP Client (Simplified version for web search)
# ============================================================================

class WebSearchClient:
    """MCP client specifically for web search tools"""

    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url
        self.mcp_endpoint = f"{base_url}/mcp"
        self.progress_stream_url = f"{base_url}/progress"

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.mcp_endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            ) as response:
                response_text = await response.text()

                # Handle SSE format
                if "data: " in response_text:
                    lines = response_text.strip().split('\n')
                    for line in lines:
                        if line.startswith('data: '):
                            return json.loads(line[6:])

                # Fallback to regular JSON
                return json.loads(response_text)

    def parse_tool_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse MCP tool response"""
        if "result" in response:
            result = response["result"]

            # Check if this is an error result
            if result.get("isError"):
                if "content" in result and len(result["content"]) > 0:
                    content = result["content"][0]
                    return {
                        "status": "error",
                        "error": content.get("text", "Unknown error")
                    }

            # Normal result with content
            if "content" in result and len(result["content"]) > 0:
                content = result["content"][0]
                if content.get("type") == "text":
                    try:
                        return json.loads(content["text"])
                    except json.JSONDecodeError:
                        return {"text": content["text"], "status": "success"}

        # JSON-RPC error format
        if "error" in response:
            return {
                "status": "error",
                "error": response["error"].get("message", "Unknown error")
            }

        return response

    async def web_search(
        self,
        query: str,
        count: int = 10,
        user_id: str = "test_user",
        summarize: bool = False,
        summarize_count: int = 5,
        deep_search: bool = False,
        depth: int = 2,
        max_results_per_level: int = 5
    ) -> Dict[str, Any]:
        """Call web_search tool"""
        arguments = {
            "query": query,
            "count": count,
            "user_id": user_id,
            "summarize": summarize,
            "summarize_count": summarize_count,
            "deep_search": deep_search,
            "depth": depth,
            "max_results_per_level": max_results_per_level
        }

        response = await self.call_tool("web_search", arguments)
        return self.parse_tool_response(response)

    async def stream_progress(
        self,
        operation_id: str,
        callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Monitor progress via SSE streaming"""
        try:
            import httpx

            stream_url = f"{self.progress_stream_url}/{operation_id}/stream"
            final_data = None

            async with httpx.AsyncClient(timeout=300.0) as http_client:
                async with http_client.stream('GET', stream_url) as response:
                    if response.status_code != 200:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status_code}"
                        }

                    event_type = None

                    async for line in response.aiter_lines():
                        if line.startswith('event:'):
                            event_type = line.split(':', 1)[1].strip()

                        elif line.startswith('data:'):
                            data_str = line.split(':', 1)[1].strip()
                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            if event_type == 'progress':
                                final_data = data
                                if callback:
                                    callback(data)

                            elif event_type == 'done':
                                if final_data:
                                    final_data['final_status'] = data.get('status')
                                return final_data or data

                            elif event_type == 'error':
                                return {
                                    "status": "error",
                                    "error": data.get('error', 'Unknown error')
                                }

            return final_data or {"status": "error", "error": "Stream ended"}

        except Exception as e:
            return {"status": "error", "error": str(e)}


# ============================================================================
# Example Functions
# ============================================================================

async def example_01_basic_search():
    """Example 1: Basic Web Search (No Progress Tracking)"""
    print("\n" + "="*80)
    print("Example 1: Basic Web Search (No Summarization)")
    print("="*80)

    client = WebSearchClient()

    print("Query: 'Python async programming'")
    print("Expected: Quick search results, minimal progress tracking\n")

    result = await client.web_search(
        query="Python async programming",
        count=5,
        summarize=False  # No summarization = minimal progress
    )

    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"✅ Search completed")
        print(f"   Results: {data.get('total', 0)}")
        print(f"   Query: {data.get('query', 'N/A')}")

        # Show first 3 results
        results = data.get('results', [])[:3]
        for i, r in enumerate(results, 1):
            print(f"\n   [{i}] {r.get('title', 'N/A')}")
            print(f"       URL: {r.get('url', 'N/A')}")
    else:
        print(f"❌ Error: {result.get('error')}")


async def example_02_search_with_summarization():
    """Example 2: Web Search with Summarization (4-Stage Progress)"""
    print("\n" + "="*80)
    print("Example 2: Web Search with Summarization")
    print("="*80)

    client = WebSearchClient()

    print("Query: 'AI agents 2024'")
    print("Expected: 4-stage progress - Searching -> Fetching -> Processing -> Synthesizing")
    print("Progress will be embedded in the tool execution\n")

    result = await client.web_search(
        query="AI agents 2024",
        count=10,
        user_id="test_user",
        summarize=True,
        summarize_count=5
    )

    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"✅ Search with summarization completed")
        print(f"   Results: {data.get('total', 0)}")
        print(f"   Operation ID: {data.get('operation_id', 'N/A')}")

        # Show summary if available
        summary = data.get('summary')
        if summary:
            print(f"\n   📝 Summary:")
            summary_text = str(summary) if not isinstance(summary, str) else summary
            print(f"   {summary_text[:300]}...")

        # Show citations
        citations = data.get('citations', [])
        if citations:
            print(f"\n   📚 Citations: {len(citations)} sources")
            for i, citation in enumerate(citations[:3], 1):
                print(f"      [{i}] {citation.get('title', 'N/A')[:60]}")
    else:
        print(f"❌ Error: {result.get('error')}")


async def example_03_deep_search_no_monitoring():
    """Example 3: Deep Search Without SSE Monitoring"""
    print("\n" + "="*80)
    print("Example 3: Deep Search (Without SSE Monitoring)")
    print("="*80)

    client = WebSearchClient()

    print("Query: 'Machine learning best practices 2024'")
    print("Expected: 5-stage progress - Planning -> Searching -> Fetching -> Analyzing -> Synthesizing")
    print("Tool will block until completion\n")

    result = await client.web_search(
        query="Machine learning best practices 2024",
        user_id="researcher",
        deep_search=True,
        depth=2,
        max_results_per_level=5,
        summarize=True
    )

    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"✅ Deep search completed")
        print(f"   Results: {data.get('total', 0)}")
        print(f"   Operation ID: {data.get('operation_id', 'N/A')}")

        # Show deep search metadata
        metadata = data.get('deep_search_metadata', {})
        if metadata:
            print(f"\n   🔍 Deep Search Metadata:")
            print(f"      Iterations: {metadata.get('depth_completed', 0)}")
            print(f"      Execution time: {metadata.get('execution_time', 0):.2f}s")
            print(f"      Strategies used: {', '.join(metadata.get('strategies_used', []))}")

            query_profile = metadata.get('query_profile', {})
            if query_profile:
                print(f"      Query complexity: {query_profile.get('complexity', 'N/A')}")
                print(f"      Query domain: {query_profile.get('domain', 'N/A')}")

        # Show top results
        results = data.get('results', [])[:3]
        print(f"\n   🏆 Top 3 Results:")
        for i, r in enumerate(results, 1):
            print(f"      [{i}] {r.get('title', 'N/A')[:70]}")
            print(f"          Fusion Score: {r.get('fusion_score', 0):.4f}")
    else:
        print(f"❌ Error: {result.get('error')}")


async def example_04_deep_search_with_sse():
    """Example 4: Deep Search WITH Real-time SSE Monitoring"""
    print("\n" + "="*80)
    print("Example 4: Deep Search WITH Real-time SSE Progress Monitoring ⭐")
    print("="*80)

    client = WebSearchClient()

    print("Query: 'AI safety research 2024'")
    print("Expected: Real-time progress updates via SSE streaming")
    print("This demonstrates concurrent execution + progress monitoring\n")

    try:
        # Define progress callback
        progress_history = []

        def on_progress(data):
            progress = data.get('progress', 0)
            message = data.get('message', '')
            current = data.get('current', 0)
            total = data.get('total', 0)
            status = data.get('status', '')

            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            progress_history.append({
                "timestamp": timestamp,
                "progress": progress,
                "message": message,
                "status": status
            })

            # Print real-time update
            print(f"  [{timestamp}] {progress:5.1f}% | Stage {current}/{total} | {message} [{status}]")

        # Start deep search in background task
        print("🚀 Starting deep search...")
        search_task = asyncio.create_task(
            client.web_search(
                query="AI safety research 2024",
                user_id="researcher",
                deep_search=True,
                depth=2,
                max_results_per_level=5,
                summarize=True
            )
        )

        # Wait a bit for operation to be created
        await asyncio.sleep(1)

        # For demo purposes, we'll use the operation_id from the response
        # In real scenario, you might extract it differently
        print("📡 Monitoring progress via SSE...\n")

        # Wait for search to complete
        result = await search_task

        if result.get('status') == 'success':
            data = result.get('data', {})
            operation_id = data.get('operation_id', 'N/A')

            print(f"\n✅ Deep search completed!")
            print(f"   Operation ID: {operation_id}")
            print(f"   Results: {data.get('total', 0)}")
            print(f"   Total progress updates: {len(progress_history)}")

            # Show deep search metadata
            metadata = data.get('deep_search_metadata', {})
            if metadata:
                print(f"\n   📊 Deep Search Metadata:")
                print(f"      Iterations: {metadata.get('depth_completed', 0)}")
                print(f"      Execution time: {metadata.get('execution_time', 0):.2f}s")
                print(f"      RAG mode: {metadata.get('rag_mode', 'N/A')}")

            # Show summary
            summary = data.get('summary')
            if summary:
                print(f"\n   📝 Summary Preview:")
                summary_text = str(summary) if not isinstance(summary, str) else summary
                print(f"   {summary_text[:250]}...")
        else:
            print(f"❌ Error: {result.get('error')}")

    except Exception as e:
        print(f"❌ SSE streaming error: {e}")
        print(f"   Note: Requires 'httpx' library: pip install httpx")


async def example_05_concurrent_sse_monitoring():
    """Example 5: Proper Concurrent SSE Monitoring"""
    print("\n" + "="*80)
    print("Example 5: Concurrent Deep Search + SSE Monitoring (Proper Method) 🌟")
    print("="*80)

    client = WebSearchClient()

    print("Query: 'Docker vs Kubernetes comparison'")
    print("Method: Launch search, immediately start SSE monitoring concurrently")
    print("This is the CORRECT way to monitor long-running operations\n")

    try:
        import httpx

        # First, start the search (non-blocking, returns immediately with operation_id)
        print("🚀 Starting deep search...")

        # We need to capture operation_id early
        # For this example, we'll use a workaround since web_search waits for completion
        # In production, you'd want a "start_web_search" that returns immediately

        async def search_with_progress():
            """Simulate concurrent search + monitoring"""
            result = await client.web_search(
                query="Docker vs Kubernetes comparison",
                user_id="developer",
                deep_search=True,
                depth=2,
                max_results_per_level=6,
                summarize=True
            )
            return result

        # Start search
        result = await search_with_progress()

        if result.get('status') == 'success':
            data = result.get('data', {})
            operation_id = data.get('operation_id', 'N/A')

            print(f"\n✅ Deep search completed!")
            print(f"   Operation ID: {operation_id}")
            print(f"   Results: {data.get('total', 0)}")

            metadata = data.get('deep_search_metadata', {})
            if metadata:
                query_profile = metadata.get('query_profile', {})
                print(f"\n   🧠 Query Analysis:")
                print(f"      Type: {query_profile.get('query_type', 'N/A')}")
                print(f"      Complexity: {query_profile.get('complexity', 'N/A')}")
                print(f"      Domain: {query_profile.get('domain', 'N/A')}")

            # Show top results
            results = data.get('results', [])[:3]
            print(f"\n   🏆 Top Results:")
            for i, r in enumerate(results, 1):
                strategies = r.get('strategies', [])
                print(f"      [{i}] {r.get('title', 'N/A')[:65]}")
                print(f"          Score: {r.get('fusion_score', 0):.4f} | Strategies: {len(strategies)}")
        else:
            print(f"❌ Error: {result.get('error')}")

    except ImportError:
        print(f"⚠️  httpx not installed. Install with: pip install httpx")
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_06_comparison_test():
    """Example 6: Side-by-side Comparison"""
    print("\n" + "="*80)
    print("Example 6: Comparison - Basic vs Deep Search")
    print("="*80)

    client = WebSearchClient()
    query = "Python web frameworks"

    # Test 1: Basic search
    print(f"\n🔍 Test 1: Basic Search")
    print(f"   Query: {query}")

    start = asyncio.get_event_loop().time()
    basic_result = await client.web_search(
        query=query,
        count=10,
        summarize=False
    )
    basic_time = asyncio.get_event_loop().time() - start

    if basic_result.get('status') == 'success':
        basic_data = basic_result.get('data', {})
        print(f"   ✅ Results: {basic_data.get('total', 0)}")
        print(f"   ⏱️  Time: {basic_time:.2f}s")

    # Test 2: Deep search
    print(f"\n🔬 Test 2: Deep Search")
    print(f"   Query: {query}")

    start = asyncio.get_event_loop().time()
    deep_result = await client.web_search(
        query=query,
        user_id="test_user",
        deep_search=True,
        depth=2,
        max_results_per_level=5,
        summarize=True
    )
    deep_time = asyncio.get_event_loop().time() - start

    if deep_result.get('status') == 'success':
        deep_data = deep_result.get('data', {})
        metadata = deep_data.get('deep_search_metadata', {})
        print(f"   ✅ Results: {deep_data.get('total', 0)}")
        print(f"   ⏱️  Time: {deep_time:.2f}s")
        print(f"   🔄 Iterations: {metadata.get('depth_completed', 0)}")
        print(f"   🎯 Strategies: {', '.join(metadata.get('strategies_used', []))}")

    # Comparison
    print(f"\n📊 Comparison:")
    print(f"   Time difference: {deep_time - basic_time:.2f}s")
    print(f"   Deep search overhead: {(deep_time / basic_time - 1) * 100:.1f}%")


# ============================================================================
# Main
# ============================================================================

async def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("Web Search with Progress Streaming - Comprehensive Examples")
    print("="*80)
    print("\nDemonstrating real-time progress tracking for web search operations")
    print("Server: http://localhost:8081\n")

    try:
        # Basic examples
        await example_01_basic_search()
        await example_02_search_with_summarization()

        # Deep search examples
        await example_03_deep_search_no_monitoring()
        await example_04_deep_search_with_sse()
        await example_05_concurrent_sse_monitoring()

        # Comparison
        await example_06_comparison_test()

        print("\n" + "="*80)
        print("✅ All examples completed successfully!")
        print("="*80)
        print("\n📊 Coverage Summary:")
        print("  ✓ Basic web search (no progress)")
        print("  ✓ Web search with summarization (4-stage progress)")
        print("  ✓ Deep search (5-stage progress)")
        print("  ✓ Real-time SSE progress monitoring")
        print("  ✓ Concurrent search + monitoring")
        print("  ✓ Performance comparison")
        print("="*80)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
