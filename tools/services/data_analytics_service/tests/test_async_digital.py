#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Async Digital Tools with Real-time SSE Progress Monitoring
===============================================================

This script tests the async background task approach for digital_tools
to verify if HTTP clients can monitor real-time progress via SSE streaming.

Test Flow:
1. Call store_knowledge() with operation_id -> Monitor progress via SSE
2. Call search_knowledge() -> Get results
3. Call knowledge_response() with operation_id -> Monitor RAG progress via SSE

Expected Outcome:
✅ HTTP client should see real-time progress updates as storage/RAG executes
"""

import asyncio
import aiohttp
import json
from datetime import datetime


class AsyncDigitalClient:
    """Client for testing async digital tools with SSE monitoring"""

    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url
        self.mcp_endpoint = f"{base_url}/mcp"
        self.progress_stream_url = f"{base_url}/progress"

    async def call_tool(self, tool_name: str, arguments: dict, debug: bool = False):
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

                if debug:
                    print(f"\n[DEBUG] Response length: {len(response_text)} chars")
                    print(f"[DEBUG] Response preview: {response_text[:200]}...")

                # Handle SSE format (data: {...})
                if "data: " in response_text:
                    lines = response_text.strip().split('\n')
                    result_data = None

                    # Parse all SSE messages and find the last one with result
                    for line in lines:
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                # Look for result field (tool response)
                                if "result" in data:
                                    result = data["result"]
                                    if "content" in result and len(result["content"]) > 0:
                                        content = result["content"][0]
                                        if content.get("type") == "text":
                                            try:
                                                result_data = json.loads(content["text"])
                                            except json.JSONDecodeError:
                                                result_data = {"text": content["text"], "status": "unknown"}
                            except json.JSONDecodeError:
                                continue

                    if result_data:
                        if debug:
                            print(f"[DEBUG] Parsed response: {json.dumps(result_data, indent=2)[:300]}")
                        return result_data

                    if debug:
                        print(f"[DEBUG] No result found in SSE messages")
                    return {"status": "error", "error": "No result in response"}

                # Handle plain JSON
                parsed = json.loads(response_text)
                if debug:
                    print(f"[DEBUG] Plain JSON response: {json.dumps(parsed, indent=2)[:200]}")
                return parsed

    async def stream_progress_with_httpx(self, operation_id: str):
        """
        Monitor progress via SSE using httpx (supports HTTP/2)
        """
        try:
            import httpx

            stream_url = f"{self.progress_stream_url}/{operation_id}/stream"
            progress_updates = []

            print(f"[SSE] Connecting to SSE stream: {stream_url}\n")

            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream('GET', stream_url) as response:
                    if response.status_code != 200:
                        print(f"[ERROR] SSE connection failed: HTTP {response.status_code}")
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
                                print(f"\n[SUCCESS] Task completed!")
                                return progress_updates

                            elif event_type == 'error':
                                print(f"\n[ERROR] Task failed: {data.get('error')}")
                                return progress_updates

            return progress_updates

        except ImportError:
            print("[ERROR] httpx not installed. Install with: pip install httpx")
            return []
        except Exception as e:
            print(f"[ERROR] SSE streaming error: {e}")
            return []


async def test_async_store_knowledge():
    """
    Test store_knowledge with real-time SSE monitoring

    This tests the 4-stage storage pipeline:
    1. Processing (25%)
    2. Extraction (50%)
    3. Embedding (75%)
    4. Storing (100%)
    """
    print("=" * 80)
    print("TEST 1: Store Knowledge with Real-time SSE Monitoring")
    print("=" * 80)
    print()

    client = AsyncDigitalClient()

    # Test content
    test_content = """
    Artificial Intelligence (AI) is the simulation of human intelligence by machines.
    Machine learning is a subset of AI that enables systems to learn from data.
    Deep learning is a type of machine learning using neural networks.
    """

    # Generate custom operation_id for monitoring
    import uuid
    operation_id = str(uuid.uuid4())

    print(f"Content: {len(test_content)} chars")
    print(f"Content Type: text")
    print(f"Operation ID: {operation_id}")
    print()

    try:
        # Step 1: Start storage with custom operation_id (in background)
        print("[STEP 1] Starting text storage with custom operation_id...\n")

        storage_task = asyncio.create_task(
            client.call_tool("store_knowledge", {
                "user_id": "test_user",
                "content": test_content,
                "content_type": "text",
                "metadata": {"source": "test", "topic": "AI"},
                "options": {"rag_mode": "simple"},
                "operation_id": operation_id
            }, debug=True)
        )

        # Wait for operation to be created in Redis (increased wait time)
        await asyncio.sleep(2)

        # Step 2: Monitor progress via SSE concurrently
        print("=" * 80)
        print("[STEP 2] Monitoring Real-time Progress via SSE")
        print("=" * 80)
        print()

        progress_task = asyncio.create_task(
            client.stream_progress_with_httpx(operation_id)
        )

        # Wait for both to complete
        result, progress_updates = await asyncio.gather(storage_task, progress_task)

        print(f"\n[SUMMARY] Total progress updates received: {len(progress_updates)}")

        # Step 3: Check final result
        print("\n" + "=" * 80)
        print("[STEP 3] Final Result")
        print("=" * 80)
        print()

        if result.get('status') == 'success':
            result_data = result.get('data', {})

            print(f"[SUCCESS] Storage completed successfully!")
            print(f"   Success: {result_data.get('success', False)}")
            print(f"   Content Type: {result_data.get('content_type', 'N/A')}")
            print(f"   Operation ID: {result_data.get('operation_id', 'N/A')}")

            # Show metadata
            metadata = result_data.get('metadata', {})
            if metadata:
                print(f"\n   [METADATA] Storage Metadata:")
                for key, value in metadata.items():
                    print(f"      {key}: {value}")

        else:
            print(f"[ERROR] Failed: {result.get('error')}")

        # Analysis
        print("\n" + "=" * 80)
        print("[ANALYSIS]")
        print("=" * 80)
        print()

        if len(progress_updates) > 0:
            print(f"[SUCCESS] HTTP client received {len(progress_updates)} real-time progress updates!")
            print(f"   This proves the async background task approach works for digital tools.")
            print()
            print(f"   Progress Timeline:")
            for i, update in enumerate(progress_updates, 1):
                print(f"      {i}. [{update['timestamp']}] {update['progress']:.1f}% - {update['message']}")
        else:
            print(f"[WARNING] No progress updates received.")
            print(f"   Possible reasons:")
            print(f"   1. Task completed too quickly (text storage is fast)")
            print(f"   2. httpx not installed")
            print(f"   3. SSE connection issue")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_async_knowledge_response():
    """
    Test knowledge_response with real-time SSE monitoring (simple_rag)

    This tests the 4-stage RAG pipeline:
    1. Processing (25%) - Query analysis
    2. Retrieval (50%) - Context retrieval
    3. Preparation (75%) - Context preparation
    4. Generation (100%) - AI response generation
    """
    print("\n" + "=" * 80)
    print("TEST 2: Knowledge Response with Real-time SSE Monitoring (Simple RAG)")
    print("=" * 80)
    print()

    client = AsyncDigitalClient()

    # Test query
    query = "What is machine learning?"

    # Generate custom operation_id for monitoring
    import uuid
    operation_id = str(uuid.uuid4())

    print(f"Query: '{query}'")
    print(f"RAG Mode: simple")
    print(f"Operation ID: {operation_id}")
    print()

    try:
        # Step 1: Start RAG response with custom operation_id (in background)
        print("[STEP 1] Starting RAG response with custom operation_id...\n")

        response_task = asyncio.create_task(
            client.call_tool("knowledge_response", {
                "user_id": "test_user",
                "query": query,
                "response_options": {
                    "rag_mode": "simple",
                    "context_limit": 3,
                    "enable_citations": True
                },
                "operation_id": operation_id
            }, debug=True)
        )

        # Wait for operation to be created in Redis (increased wait time)
        await asyncio.sleep(2)

        # Step 2: Monitor progress via SSE concurrently
        print("=" * 80)
        print("[STEP 2] Monitoring Real-time RAG Progress via SSE")
        print("=" * 80)
        print()

        progress_task = asyncio.create_task(
            client.stream_progress_with_httpx(operation_id)
        )

        # Wait for both to complete
        result, progress_updates = await asyncio.gather(response_task, progress_task)

        print(f"\n[SUMMARY] Total progress updates received: {len(progress_updates)}")

        # Step 3: Check final result
        print("\n" + "=" * 80)
        print("[STEP 3] Final RAG Result")
        print("=" * 80)
        print()

        if result.get('status') == 'success':
            result_data = result.get('data', {})

            print(f"[SUCCESS] RAG response generated successfully!")
            print(f"   Success: {result_data.get('success', False)}")
            print(f"   RAG Mode: {result_data.get('rag_mode_used', 'N/A')}")
            print(f"   Response Type: {result_data.get('response_type', 'N/A')}")
            print(f"   Operation ID: {result_data.get('operation_id', 'N/A')}")

            # Show response preview
            response_text = result_data.get('response', result_data.get('answer', ''))
            if response_text:
                print(f"\n   [RESPONSE] Preview (first 200 chars):")
                print(f"      {response_text[:200]}...")

            # Show context info
            context_items = result_data.get('context_items', 0)
            if context_items > 0:
                print(f"\n   [CONTEXT] Used:")
                print(f"      Items: {context_items}")
                print(f"      Citations: {result_data.get('inline_citations_enabled', False)}")

        else:
            print(f"[ERROR] Failed: {result.get('error')}")

        # Analysis
        print("\n" + "=" * 80)
        print("[ANALYSIS]")
        print("=" * 80)
        print()

        if len(progress_updates) > 0:
            print(f"[SUCCESS] HTTP client received {len(progress_updates)} real-time RAG progress updates!")
            print(f"   This proves the async RAG pipeline works with SSE monitoring.")
            print()
            print(f"   RAG Progress Timeline:")
            for i, update in enumerate(progress_updates, 1):
                print(f"      {i}. [{update['timestamp']}] {update['progress']:.1f}% - {update['message']}")
        else:
            print(f"[WARNING] No progress updates received.")
            print(f"   Possible reasons:")
            print(f"   1. RAG generation completed too quickly")
            print(f"   2. httpx not installed")
            print(f"   3. SSE connection issue")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_complete_flow():
    """
    Test complete flow: Store -> Search -> Response

    This tests the full knowledge lifecycle without SSE monitoring
    (for quick validation)
    """
    print("\n" + "=" * 80)
    print("TEST 3: Complete Flow (Store -> Search -> Response)")
    print("=" * 80)
    print()

    client = AsyncDigitalClient()

    test_content = """
    Python is a high-level programming language known for simplicity.
    It supports multiple programming paradigms including OOP and functional.
    """

    try:
        # Step 1: Store
        print("[STEP 1] Storing knowledge...")
        store_result = await client.call_tool("store_knowledge", {
            "user_id": "test_user_flow",
            "content": test_content,
            "content_type": "text",
            "options": {"rag_mode": "simple"}
        })

        if store_result.get('status') == 'success':
            print(f"   [SUCCESS] Stored successfully")
        else:
            print(f"   [ERROR] Storage failed: {store_result.get('error')}")
            return

        # Wait for indexing
        await asyncio.sleep(2)

        # Step 2: Search
        print("\n[STEP 2] Searching knowledge...")
        search_result = await client.call_tool("search_knowledge", {
            "user_id": "test_user_flow",
            "query": "Python programming",
            "search_options": {"top_k": 3}
        })

        if search_result.get('status') == 'success':
            result_data = search_result.get('data', {})
            total = result_data.get('total_results', 0)
            print(f"   [SUCCESS] Found {total} results")
        else:
            print(f"   [ERROR] Search failed: {search_result.get('error')}")
            return

        # Step 3: Generate response
        print("\n[STEP 3] Generating RAG response...")
        response_result = await client.call_tool("knowledge_response", {
            "user_id": "test_user_flow",
            "query": "What is Python?",
            "response_options": {
                "rag_mode": "simple",
                "context_limit": 3
            }
        })

        if response_result.get('status') == 'success':
            result_data = response_result.get('data', {})
            response_text = result_data.get('response', result_data.get('answer', ''))
            print(f"   [SUCCESS] Response generated ({len(response_text)} chars)")
            print(f"\n   [RESPONSE] Preview:")
            print(f"      {response_text[:200]}...")
        else:
            print(f"   [ERROR] Response failed: {response_result.get('error')}")

        print("\n[SUCCESS] Complete flow test passed!")

    except Exception as e:
        print(f"\n[ERROR] Complete flow test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("Async Digital Tools SSE Streaming Test Suite")
    print("=" * 80)
    print("\nTesting if HTTP clients can see real-time progress via SSE")
    print("Server: http://localhost:8081")
    print("Mode: Simple RAG (fast and reliable)")
    print()

    try:
        # Test 1: Store knowledge with SSE monitoring
        await test_async_store_knowledge()

        # Test 2: Knowledge response with SSE monitoring
        await test_async_knowledge_response()

        # Test 3: Complete flow (quick validation)
        await test_complete_flow()

        print("\n" + "=" * 80)
        print("[SUCCESS] All tests completed!")
        print("=" * 80)

    except KeyboardInterrupt:
        print("\n\n[WARNING] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
