#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Async Web Crawl with Real-time SSE Progress Monitoring
============================================================

This script tests web crawl operations with real-time progress monitoring via SSE streaming.

Test Flow:
1. Call web_crawl() with custom operation_id
2. Connect to SSE stream: /progress/{operation_id}/stream
3. Monitor real-time progress updates
4. Retrieve final result
"""

import asyncio
import aiohttp
import json
from datetime import datetime


class AsyncWebCrawlClient:
    """Client for testing async web crawl with SSE monitoring"""

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
        """Monitor progress via SSE using httpx"""
        try:
            import httpx

            stream_url = f"{self.progress_stream_url}/{operation_id}/stream"
            progress_updates = []

            print(f"[STREAM] Connecting to SSE: {stream_url}\n")

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


async def test_single_crawl():
    """Test single URL crawl with SSE monitoring"""
    print("=" * 80)
    print("[TEST] Single URL Crawl with Real-time SSE Monitoring")
    print("=" * 80)
    print()

    client = AsyncWebCrawlClient()
    url = "https://en.wikipedia.org/wiki/Artificial_intelligence"

    import uuid
    operation_id = str(uuid.uuid4())

    print(f"URL: {url}")
    print(f"Operation ID: {operation_id}")
    print()

    try:
        print("[START] Starting web crawl with custom operation_id...\n")

        crawl_task = asyncio.create_task(
            client.call_tool("web_crawl", {
                "url": url,
                "analysis_request": "extract main content and analyze key topics",
                "operation_id": operation_id
            })
        )

        await asyncio.sleep(2)

        print("=" * 80)
        print("[PROGRESS] Monitoring Real-time Progress via SSE")
        print("=" * 80)
        print()

        progress_task = asyncio.create_task(
            client.stream_progress_with_httpx(operation_id)
        )

        result, progress_updates = await asyncio.gather(crawl_task, progress_task)

        print(f"\n[STATS] Total progress updates received: {len(progress_updates)}")
        print("\n" + "=" * 80)
        print("[RESULT] Final Result")
        print("=" * 80)
        print()

        if result.get('status') == 'success':
            result_data = result.get('data', {})
            print(f"[SUCCESS] Result retrieved successfully!")
            print(f"   Success: {result_data.get('success', False)}")

            crawl_result = result_data.get('result', {})
            print(f"\n   [CRAWL] Details:")
            print(f"      Method: {crawl_result.get('method', 'N/A')}")
            print(f"      Word count: {crawl_result.get('word_count', 0)}")
            print(f"      Title: {crawl_result.get('title', 'N/A')[:70]}")
        else:
            print(f"[ERROR] Failed: {result.get('error')}")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_multi_crawl():
    """Test multi-URL comparison with SSE monitoring"""
    print("\n" + "=" * 80)
    print("[TEST] Multi-URL Comparison with Real-time SSE Monitoring")
    print("=" * 80)
    print()

    client = AsyncWebCrawlClient()
    urls = [
        "https://en.wikipedia.org/wiki/Machine_learning",
        "https://en.wikipedia.org/wiki/Deep_learning"
    ]

    import uuid
    operation_id = str(uuid.uuid4())

    print(f"URLs: {len(urls)} URLs")
    print(f"Operation ID: {operation_id}")
    print()

    try:
        print("[START] Starting multi-URL crawl...\n")

        crawl_task = asyncio.create_task(
            client.call_tool("web_crawl_compare", {
                "urls": urls,
                "analysis_request": "compare the key concepts and approaches",
                "operation_id": operation_id
            })
        )

        await asyncio.sleep(2)

        print("=" * 80)
        print("[PROGRESS] Monitoring Real-time Progress via SSE")
        print("=" * 80)
        print()

        progress_task = asyncio.create_task(
            client.stream_progress_with_httpx(operation_id)
        )

        result, progress_updates = await asyncio.gather(crawl_task, progress_task)

        print(f"\n[STATS] Total progress updates received: {len(progress_updates)}")
        print("\n" + "=" * 80)
        print("[RESULT] Final Result")
        print("=" * 80)
        print()

        if result.get('status') == 'success':
            result_data = result.get('data', {})
            print(f"[SUCCESS] Result retrieved successfully!")
            print(f"   URLs processed: {result_data.get('urls_count', 0)}")

            individual_results = result_data.get('individual_results', [])
            if individual_results:
                print(f"\n   [DETAIL] Individual Results:")
                for i, ir in enumerate(individual_results, 1):
                    success = ir.get('success', False)
                    url = ir.get('url', 'N/A')
                    status_icon = "[OK]" if success else "[FAIL]"
                    print(f"      [{i}] {status_icon} {url[:70]}")
        else:
            print(f"[ERROR] Failed: {result.get('error')}")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_basic_crawl():
    """Test basic crawl without progress monitoring"""
    print("\n" + "=" * 80)
    print("[TEST] Basic Crawl (Simple Usage - No Monitoring)")
    print("=" * 80)
    print()

    client = AsyncWebCrawlClient()
    url = "https://example.com"

    print(f"URL: {url}")
    print()

    try:
        print("[START] Starting simple crawl...\n")

        result = await client.call_tool("web_crawl", {
            "url": url
        })

        if result.get('status') == 'success':
            result_data = result.get('data', {})
            crawl_result = result_data.get('result', {})
            print(f"[SUCCESS] Success!")
            print(f"   Method: {crawl_result.get('method', 'N/A')}")
            print(f"   Word count: {crawl_result.get('word_count', 0)}")
            print(f"   Operation ID: {result_data.get('operation_id', 'N/A')}")
        else:
            print(f"[ERROR] Failed: {result.get('error')}")

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("Async Web Crawl SSE Streaming Test Suite")
    print("=" * 80)
    print("\nTesting real-time progress via SSE")
    print("Server: http://localhost:8081")
    print()

    try:
        await test_single_crawl()
        await test_multi_crawl()
        await test_basic_crawl()

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
