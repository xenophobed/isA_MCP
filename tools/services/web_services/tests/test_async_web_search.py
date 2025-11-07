#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Async Web Search with Real-time SSE Progress Monitoring
=============================================================

This script tests the async background task approach to see if HTTP clients
can monitor real-time progress via SSE streaming.

Test Flow:
1. Call start_web_search_async() -> Get operation_id immediately
2. Connect to SSE stream: /progress/{operation_id}/stream
3. Monitor real-time progress updates
4. Call get_web_search_result() to retrieve final result

Expected Outcome:
✅ HTTP client should see real-time progress updates as the search executes
"""

import asyncio
import aiohttp
import json
from datetime import datetime


class AsyncWebSearchClient:
    """Client for testing async web search with SSE monitoring"""

    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url
        self.mcp_endpoint = f"{base_url}/mcp"
        self.progress_stream_url = f"{base_url}/progress"

    async def call_tool(self, tool_name: str, arguments: dict):
        """Call MCP tool"""
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

                if "data: " in response_text:
                    lines = response_text.strip().split('\n')
                    for line in lines:
                        if line.startswith('data: '):
                            data = json.loads(line[6:])
                            if "result" in data:
                                result = data["result"]
                                if "content" in result and len(result["content"]) > 0:
                                    content = result["content"][0]
                                    if content.get("type") == "text":
                                        try:
                                            return json.loads(content["text"])
                                        except json.JSONDecodeError:
                                            return {"text": content["text"]}
                            return data

                return json.loads(response_text)

    async def stream_progress_with_httpx(self, operation_id: str):
        """
        Monitor progress via SSE using httpx (supports HTTP/2)
        """
        try:
            import httpx

            stream_url = f"{self.progress_stream_url}/{operation_id}/stream"
            progress_updates = []

            print(f"📡 Connecting to SSE stream: {stream_url}\n")

            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream('GET', stream_url) as response:
                    if response.status_code != 200:
                        print(f"❌ SSE connection failed: HTTP {response.status_code}")
                        return progress_updates

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
                                progress = data.get('progress', 0)
                                message = data.get('message', '')
                                status = data.get('status', '')
                                current = data.get('current', 0)
                                total = data.get('total', 0)

                                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                print(f"  [{timestamp}] {progress:5.1f}% | Stage {current}/{total} | {message} [{status}]")

                                progress_updates.append({
                                    "timestamp": timestamp,
                                    "progress": progress,
                                    "message": message,
                                    "status": status
                                })

                            elif event_type == 'done':
                                print(f"\n✅ Task completed!")
                                return progress_updates

                            elif event_type == 'error':
                                print(f"\n❌ Task failed: {data.get('error')}")
                                return progress_updates

            return progress_updates

        except ImportError:
            print("❌ httpx not installed. Install with: pip install httpx")
            return []
        except Exception as e:
            print(f"❌ SSE streaming error: {e}")
            return []


async def test_async_deep_search():
    """
    Test deep search with real-time SSE monitoring (NEW UNIFIED METHOD)

    This is the KEY test to verify if HTTP clients can see real-time progress
    """
    print("=" * 80)
    print("🧪 TEST: Deep Search with Real-time SSE Monitoring (Unified)")
    print("=" * 80)
    print()

    client = AsyncWebSearchClient()

    # Test query
    query = "AI safety research 2024"

    # Generate custom operation_id for monitoring
    import uuid
    operation_id = str(uuid.uuid4())

    print(f"Query: '{query}'")
    print(f"Mode: Deep Search (with SSE monitoring)")
    print(f"Operation ID: {operation_id}")
    print()

    try:
        # Step 1: Start search with custom operation_id (in background)
        print("🚀 Step 1: Starting deep search with custom operation_id...\n")

        search_task = asyncio.create_task(
            client.call_tool("web_search", {
                "query": query,
                "user_id": "test_user",
                "deep_search": True,
                "depth": 2,
                "max_results_per_level": 5,
                "summarize": True,
                "operation_id": operation_id  # ✅ Provide custom ID
            })
        )

        # Wait for operation to be created in Redis
        await asyncio.sleep(2)

        # Step 2: Monitor progress via SSE concurrently
        print("=" * 80)
        print("📊 Step 2: Monitoring Real-time Progress via SSE")
        print("=" * 80)
        print()

        progress_task = asyncio.create_task(
            client.stream_progress_with_httpx(operation_id)
        )

        # Wait for both to complete
        result, progress_updates = await asyncio.gather(search_task, progress_task)

        print(f"\n📈 Total progress updates received: {len(progress_updates)}")

        # Step 3: Check final result
        print("\n" + "=" * 80)
        print("📥 Step 3: Final Result")
        print("=" * 80)
        print()

        if result.get('status') == 'success':
            result_data = result.get('data', {})

            print(f"✅ Result retrieved successfully!")
            print(f"   Results: {result_data.get('total', 0)}")
            print(f"   Success: {result_data.get('success', False)}")
            print(f"   Operation ID: {result_data.get('operation_id', 'N/A')}")

            # Show metadata
            metadata = result_data.get('deep_search_metadata', {})
            if metadata:
                print(f"\n   🔍 Deep Search Metadata:")
                print(f"      Iterations: {metadata.get('depth_completed', 0)}")
                print(f"      Execution time: {metadata.get('execution_time', 0):.2f}s")
                print(f"      Strategies: {', '.join(metadata.get('strategies_used', []))}")

            # Show top results
            results = result_data.get('results', [])[:3]
            if results:
                print(f"\n   🏆 Top 3 Results:")
                for i, r in enumerate(results, 1):
                    print(f"      [{i}] {r.get('title', 'N/A')[:70]}")
                    print(f"          Score: {r.get('fusion_score', 0):.4f}")
        else:
            print(f"❌ Failed: {result.get('error')}")

        # Analysis
        print("\n" + "=" * 80)
        print("📊 ANALYSIS")
        print("=" * 80)
        print()

        if len(progress_updates) > 0:
            print(f"✅ SUCCESS! HTTP client received {len(progress_updates)} real-time progress updates!")
            print(f"   This proves the async background task approach works for SSE monitoring.")
            print()
            print(f"   Progress Timeline:")
            for i, update in enumerate(progress_updates, 1):
                print(f"      {i}. [{update['timestamp']}] {update['progress']:.1f}% - {update['message']}")
        else:
            print(f"❌ FAILED! No progress updates received.")
            print(f"   Possible reasons:")
            print(f"   1. httpx not installed")
            print(f"   2. SSE connection issue")
            print(f"   3. Task completed too quickly")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_async_basic_search():
    """Test basic search with simple usage (no custom operation_id)"""
    print("\n" + "=" * 80)
    print("🧪 TEST: Basic Search (Simple Usage)")
    print("=" * 80)
    print()

    client = AsyncWebSearchClient()

    query = "Python async programming"
    print(f"Query: '{query}'")
    print(f"Mode: Basic Search (no monitoring)")
    print()

    try:
        # Simple search - no custom operation_id
        print("🚀 Starting simple search...\n")

        result = await client.call_tool("web_search", {
            "query": query,
            "count": 10
        })

        if result.get('status') == 'success':
            result_data = result.get('data', {})
            print(f"✅ Results: {result_data.get('total', 0)}")
            print(f"   Operation ID: {result_data.get('operation_id', 'N/A')}")
            print(f"\n💡 Note: Operation ID is returned even without monitoring")
        else:
            print(f"❌ Failed: {result.get('error')}")

    except Exception as e:
        print(f"❌ Test failed: {e}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("🧪 Async Web Search SSE Streaming Test Suite")
    print("=" * 80)
    print("\nTesting if HTTP clients can see real-time progress via SSE")
    print("Server: http://localhost:8081")
    print()

    try:
        # Test 1: Deep search (comprehensive test)
        await test_async_deep_search()

        # Test 2: Basic search (quick test)
        await test_async_basic_search()

        print("\n" + "=" * 80)
        print("✅ All tests completed!")
        print("=" * 80)

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
