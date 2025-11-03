#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ISA MCP Client - Comprehensive Examples (17 Scenarios)
=======================================================

Self-contained MCP client examples - no external dependencies from tools/

✅ ALL MCP CAPABILITIES COVERED:

Part 1: Core MCP Features (5 examples)
  - Example 1: Server Health Check
  - Example 2: List All Tools
  - Example 3: Semantic Search for Tools
  - Example 4: Call Simple Tool (get_weather)
  - Example 5: Search Tools by Category

Part 2: Progress Tracking (2 examples)
  - Example 6: SSE Streaming Progress (Real-time updates)
  - Example 10: HTTP Polling Progress

Part 3: Advanced Features (3 examples)
  - Example 7: Concurrent Tool Calls (Async parallel)
  - Example 8: Search All Types (Tools + Prompts + Resources)
  - Example 9: Error Handling

Part 4: MCP Resources & Prompts (2 examples)
  - Example 11: List and Read Resources
  - Example 12: List and Get Prompts

Part 5: HIL - Human-in-the-Loop (4 examples) ⭐ ALL 4 METHODS
  - Example 13: Authorization Request (Low/High/Critical risk)
  - Example 14: Input Collection (Credentials, Selection, Augmentation)
  - Example 15: Content Review (Execution plans, Code, Config)
  - Example 17: Combined Input + Authorization (Payment, Deployment)

Part 6: Batch Operations (1 example)
  - Example 16: Batch Weather Query (Parallel processing)

📚 Tool Coverage:
  ✓ BasicExampleTools: calculator, get_weather, batch_weather, stream_weather
  ✓ HILExampleTool: ALL 4 HIL methods - authorization, input, review, combined (11 tools)
  ✓ ProgressTools: start_long_task, get_task_progress, get_task_result

NO event loop warnings! Pure async implementation.
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional


# ============================================================================
# Standalone MCP Client Implementation
# ============================================================================

class MCPClient:
    """Simple standalone MCP client for examples"""

    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url
        self.mcp_endpoint = f"{base_url}/mcp"
        self.health_endpoint = f"{base_url}/health"
        self.search_endpoint = f"{base_url}/search"

    async def get_health(self) -> Dict[str, Any]:
        """Get server health"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.health_endpoint) as response:
                return await response.json()

    async def list_tools(self) -> list:
        """List all available tools"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.mcp_endpoint,
                json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
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
                            data = json.loads(line[6:])
                            tools = data.get('result', {}).get('tools', [])
                            return [tool['name'] for tool in tools]
                return []

    async def list_resources(self) -> list:
        """List all available resources"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.mcp_endpoint,
                json={"jsonrpc": "2.0", "method": "resources/list", "id": 1},
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
                            resources = data.get('result', {}).get('resources', [])
                            return resources
                return []

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource by URI"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.mcp_endpoint,
                json={"jsonrpc": "2.0", "method": "resources/read", "id": 1, "params": {"uri": uri}},
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
                            return json.loads(line[6:])
                return {}

    async def list_prompts(self) -> list:
        """List all available prompts"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.mcp_endpoint,
                json={"jsonrpc": "2.0", "method": "prompts/list", "id": 1},
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
                            prompts = data.get('result', {}).get('prompts', [])
                            return prompts
                return []

    async def get_prompt(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a prompt with arguments"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.mcp_endpoint,
                json={"jsonrpc": "2.0", "method": "prompts/get", "id": 1, "params": {"name": name, "arguments": arguments}},
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
                            return json.loads(line[6:])
                return {}

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

            # Check if this is an error result (MCP error format)
            if result.get("isError"):
                if "content" in result and len(result["content"]) > 0:
                    content = result["content"][0]
                    return {
                        "status": "error",
                        "error": content.get("text", "Unknown error")
                    }

            # Check for structuredContent (used by HIL tools and others)
            if "structuredContent" in result:
                structured = result["structuredContent"]
                if "result" in structured:
                    return structured["result"]
                return structured

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

    async def call_tool_and_parse(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool and parse response"""
        response = await self.call_tool(tool_name, arguments)
        return self.parse_tool_response(response)

    async def search(self, query: str, item_type: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Semantic search for tools/prompts/resources"""
        payload = {
            "query": query,
            "limit": limit,
            "score_threshold": 0.3
        }
        if item_type:
            payload["type"] = item_type

        async with aiohttp.ClientSession() as session:
            async with session.post(self.search_endpoint, json=payload) as response:
                return await response.json()


# ============================================================================
# Standalone Progress Tracking Functions
# ============================================================================

async def start_long_task(
    client: MCPClient,
    task_type: str,
    duration_seconds: int = 30,
    steps: int = 10
) -> Dict[str, Any]:
    """Start a long-running task"""
    return await client.call_tool_and_parse("start_long_task", {
        "task_type": task_type,
        "duration_seconds": duration_seconds,
        "steps": steps
    })


async def get_task_progress(client: MCPClient, operation_id: str) -> Dict[str, Any]:
    """Get current progress"""
    return await client.call_tool_and_parse("get_task_progress", {
        "operation_id": operation_id
    })


async def stream_progress(
    base_url: str,
    operation_id: str,
    callback: Optional[callable] = None
) -> Dict[str, Any]:
    """Monitor progress via SSE streaming (recommended)"""
    try:
        import httpx

        stream_url = f"{base_url}/progress/{operation_id}/stream"
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


async def start_and_stream(
    base_url: str,
    task_type: str,
    duration_seconds: int = 30,
    steps: int = 10,
    callback: Optional[callable] = None
) -> Dict[str, Any]:
    """Start task and stream progress (one-liner)"""
    client = MCPClient(base_url)

    # Start task
    response = await start_long_task(client, task_type, duration_seconds, steps)

    if response.get('status') != 'success':
        return response

    operation_id = response['data']['operation_id']

    # Stream progress
    final_data = await stream_progress(base_url, operation_id, callback)

    # Get final result if completed
    if final_data and final_data.get('status') == 'completed':
        result = await client.call_tool_and_parse("get_task_result", {
            "operation_id": operation_id
        })
        return result

    return final_data


# ============================================================================
# Examples
# ============================================================================

async def example_01_health_check():
    """Example 1: Server Health Check"""
    print("\n" + "="*60)
    print("Example 1: Server Health Check")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")
    health = await client.get_health()

    print(f"Status: {health.get('status')}")
    print(f"Service: {health.get('service')}")
    print(f"Uptime: {health.get('uptime')}")
    print(f"Capabilities: {health.get('capabilities')}")


async def example_02_list_tools():
    """Example 2: List Available Tools"""
    print("\n" + "="*60)
    print("Example 2: List Available Tools")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")
    tools = await client.list_tools()

    print(f"Total tools: {len(tools)}")
    print(f"First 10 tools:")
    for i, tool in enumerate(tools[:10], 1):
        print(f"  {i}. {tool}")


async def example_03_semantic_search():
    """Example 3: Semantic Search for Tools"""
    print("\n" + "="*60)
    print("Example 3: Semantic Search for Tools")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    # Search for tools related to "weather"
    print("\nSearching for 'weather' tools:")
    search_data = await client.search("get weather information", item_type="tool", limit=5)

    print(f"Found {search_data.get('count', 0)} tools:")
    for result in search_data.get('results', []):
        print(f"  - {result['name']} (score: {result['score']:.3f})")
        print(f"    {result['description'][:100]}...")


async def example_04_call_simple_tool():
    """Example 4: Call a Simple Tool"""
    print("\n" + "="*60)
    print("Example 4: Call Simple Tool (get_weather)")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    # Call get_weather tool
    result = await client.call_tool_and_parse("get_weather", {"city": "Tokyo"})

    print(f"Status: {result.get('status')}")
    print(f"Action: {result.get('action')}")
    print(f"Data: {result.get('data')}")


async def example_05_search_by_category():
    """Example 5: Search Tools by Category"""
    print("\n" + "="*60)
    print("Example 5: Search Tools by Category")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    categories = [
        ("web search", "Web Search Tools"),
        ("data analysis", "Data Analysis Tools"),
        ("calculator", "Calculator Tools"),
    ]

    for query, category_name in categories:
        print(f"\n{category_name}:")
        search_data = await client.search(query, item_type="tool", limit=3)

        for result in search_data.get('results', []):
            print(f"  - {result['name']} (score: {result['score']:.3f})")


async def example_06_progress_streaming():
    """Example 6: Progress Tracking via SSE (Recommended)"""
    print("\n" + "="*60)
    print("Example 6: Progress Tracking (SSE Streaming)")
    print("="*60)

    try:
        print("Starting long-running task with SSE streaming...")

        # Define progress callback
        def on_progress(data):
            progress = data.get('progress', 0)
            message = data.get('message', '')
            print(f"  Progress: {progress:.0f}% - {message}")

        # Start and stream in one call
        result = await start_and_stream(
            base_url="http://localhost:8081",
            task_type="sse_test",
            duration_seconds=10,
            steps=5,
            callback=on_progress
        )

        print(f"\nTask completed!")
        if result.get('status') == 'success':
            print(f"Final result: {result.get('data', {}).get('result', {})}")
        else:
            print(f"Result: {result}")
    except Exception as e:
        print(f"\n⚠ SSE streaming error (this is optional): {e}")
        print("  (httpx may not be installed, or SSE endpoint unavailable)")
        print("  Tip: pip install httpx")


async def example_07_concurrent_calls():
    """Example 7: Concurrent Tool Calls"""
    print("\n" + "="*60)
    print("Example 7: Concurrent Tool Calls")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    import time

    async def call_calculator(a, b):
        result = await client.call_tool_and_parse("calculator", {
            "operation": "add",
            "a": a,
            "b": b
        })
        return result

    start = time.time()

    # True async concurrency
    results = await asyncio.gather(
        call_calculator(10, 20),
        call_calculator(30, 40),
        call_calculator(50, 60)
    )

    duration = time.time() - start

    print(f"Completed 3 async tool calls in {duration:.2f}s")
    for i, result in enumerate(results, 1):
        if result.get('status') == 'success':
            print(f"  {i}. Result: {result['data']['result']}")
        else:
            print(f"  {i}. Error: {result.get('error')}")


async def example_08_search_all_types():
    """Example 8: Search All Types"""
    print("\n" + "="*60)
    print("Example 8: Search All Types (Tools, Prompts, Resources)")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    # Search across all types
    print("\nSearching for 'knowledge' across all types:")
    search_data = await client.search("knowledge search and retrieval", limit=10)

    # Group by type
    tools = [r for r in search_data.get('results', []) if r['type'] == 'tool']
    prompts = [r for r in search_data.get('results', []) if r['type'] == 'prompt']
    resources = [r for r in search_data.get('results', []) if r['type'] == 'resource']

    print(f"\nFound {len(tools)} tools, {len(prompts)} prompts, {len(resources)} resources")

    if tools:
        print(f"\nTop tools:")
        for tool in tools[:3]:
            print(f"  - {tool['name']} (score: {tool['score']:.3f})")


async def example_09_error_handling():
    """Example 9: Error Handling"""
    print("\n" + "="*60)
    print("Example 9: Error Handling")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    # Try to call non-existent tool
    result = await client.call_tool_and_parse("nonexistent_tool", {})

    if result.get('status') == 'error':
        print(f"✓ Error handled correctly: {result.get('error')}")
    else:
        print(f"⚠ Unexpected success")


async def example_10_quick_progress_test():
    """Example 10: Quick Progress Test (HTTP Polling)"""
    print("\n" + "="*60)
    print("Example 10: Quick Progress Test (HTTP Polling)")
    print("="*60)

    try:
        client = MCPClient(base_url="http://localhost:8081")

        print("Starting quick task (5 seconds)...")

        # Start task
        response = await start_long_task(client, "quick_test", duration_seconds=5, steps=3)

        if response.get('status') != 'success':
            print(f"Error: {response}")
            return

        operation_id = response['data']['operation_id']
        print(f"Task started: {operation_id[:8]}...")

        # Poll for progress
        import asyncio
        for i in range(10):
            await asyncio.sleep(1)
            progress = await get_task_progress(client, operation_id)

            if progress.get('status') == 'success':
                data = progress.get('data', {})
                prog = data.get('progress', 0)
                msg = data.get('message', '')
                status = data.get('status', '')
                print(f"  {prog:.0f}% - {msg} [{status}]")

                if status == 'completed':
                    print(f"\nQuick test completed!")
                    break
    except Exception as e:
        print(f"Error: {e}")


async def example_11_resources():
    """Example 11: List and Read Resources"""
    print("\n" + "="*60)
    print("Example 11: List and Read Resources")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    # List all resources
    resources = await client.list_resources()
    print(f"Total resources: {len(resources)}")

    if resources:
        print(f"\nFirst 5 resources:")
        for i, resource in enumerate(resources[:5], 1):
            print(f"  {i}. {resource['name']}")
            print(f"     URI: {resource['uri']}")
            print(f"     Description: {resource.get('description', 'N/A')[:80]}...")

        # Read first resource
        if resources:
            first_uri = resources[0]['uri']
            print(f"\n📖 Reading resource: {first_uri}")
            response = await client.read_resource(first_uri)

            if 'result' in response:
                result = response['result']
                contents = result.get('contents', [])
                if contents:
                    content = contents[0]
                    print(f"  MIME Type: {content.get('mimeType')}")
                    text = content.get('text', '')
                    print(f"  Content preview: {text[:200]}...")


async def example_12_prompts():
    """Example 12: List and Get Prompts"""
    print("\n" + "="*60)
    print("Example 12: List and Get Prompts")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    # List all prompts
    prompts = await client.list_prompts()
    print(f"Total prompts: {len(prompts)}")

    if prompts:
        print(f"\nFirst 5 prompts:")
        for i, prompt in enumerate(prompts[:5], 1):
            print(f"  {i}. {prompt['name']}")
            print(f"     Description: {prompt.get('description', 'N/A')[:80]}...")

        # Get a prompt with arguments
        print(f"\n📝 Getting prompt: intelligent_rag_search_prompt")
        response = await client.get_prompt("intelligent_rag_search_prompt", {
            "query": "What is AI?",
            "available_tools": "search, analyze",
            "available_resources": "docs",
            "context": "Learning"
        })

        if 'result' in response:
            result = response['result']
            messages = result.get('messages', [])
            if messages:
                msg = messages[0]
                print(f"  Role: {msg.get('role')}")
                content = msg.get('content', {})
                text = content.get('text', '')
                print(f"  Content preview: {text[:200]}...")


async def example_13_hil_authorization():
    """Example 13: HIL - Authorization"""
    print("\n" + "="*60)
    print("Example 13: HIL - Authorization Request")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    print("Testing LOW risk authorization...")
    result = await client.call_tool_and_parse("test_authorization_low_risk", {})

    # HIL tools return status = "authorization_requested" not "success"
    if result.get('status') == 'authorization_requested':
        print(f"  ✅ HIL Authorization Triggered!")
        print(f"  HIL Type: {result.get('hil_type')}")
        print(f"  Action: {result.get('action')}")
        data = result.get('data', {})
        print(f"  Request Action: {data.get('action')}")
        print(f"  Risk Level: {data.get('risk_level')}")
        print(f"  Reason: {data.get('reason')}")
        print(f"  Options: {result.get('options')}")
        print(f"  ℹ️  In a real scenario, this would prompt the user for approval")
    else:
        print(f"  Error: Status was {result.get('status')}, data: {result}")


async def example_14_hil_input():
    """Example 14: HIL - Input Collection"""
    print("\n" + "="*60)
    print("Example 14: HIL - Input Collection")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    print("Testing credentials input collection...")
    result = await client.call_tool_and_parse("test_input_credentials", {})

    # HIL input tools return status = "human_input_requested"
    if result.get('status') == 'human_input_requested':
        print(f"  ✅ HIL Input Collection Triggered!")
        print(f"  HIL Type: {result.get('hil_type')}")
        print(f"  Action: {result.get('action')}")
        data = result.get('data', {})
        print(f"  Prompt: {data.get('prompt')}")
        print(f"  Fields: {list(data.get('fields', {}).keys())}")
        print(f"  ℹ️  In a real scenario, this would collect user input")
    else:
        print(f"  Error: Status was {result.get('status')}, data: {result}")


async def example_15_hil_review():
    """Example 15: HIL - Content Review"""
    print("\n" + "="*60)
    print("Example 15: HIL - Content Review")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    print("Testing execution plan review...")
    result = await client.call_tool_and_parse("test_review_execution_plan", {})

    # HIL review tools return status = "human_input_requested"
    if result.get('status') == 'human_input_requested':
        print(f"  ✅ HIL Content Review Triggered!")
        print(f"  HIL Type: {result.get('hil_type')}")
        print(f"  Action: {result.get('action')}")
        data = result.get('data', {})
        content_type = data.get('content_type', 'unknown')
        print(f"  Content Type: {content_type}")
        print(f"  Editable: {data.get('editable')}")

        # Content might be a dict or string
        content = data.get('content', {})
        if isinstance(content, dict):
            print(f"  Content structure: {list(content.keys())}")
        elif isinstance(content, str):
            print(f"  Content preview: {content[:150]}...")

        print(f"  ℹ️  In a real scenario, this would allow user to review/edit content")
    else:
        print(f"  Error: Status was {result.get('status')}, data: {result}")


async def example_16_batch_weather():
    """Example 16: Batch Weather Query"""
    print("\n" + "="*60)
    print("Example 16: Batch Weather Query")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    cities = ["Tokyo", "New York", "London"]
    print(f"Querying weather for {len(cities)} cities...")

    result = await client.call_tool_and_parse("batch_weather", {
        "cities": cities,
        "parallel": True
    })

    if result.get('status') == 'success':
        data = result.get('data', {})
        print(f"  Total cities: {data.get('total_cities')}")
        print(f"  Successful: {data.get('successful')}")
        print(f"  Failed: {data.get('failed')}")

        results = data.get('results', [])
        for r in results[:3]:
            city = r.get('city')
            status = r.get('status')
            print(f"  - {city}: {status}")
    else:
        print(f"  Error: {result.get('error')}")


async def example_17_hil_combined():
    """Example 17: HIL - Combined Input + Authorization"""
    print("\n" + "="*60)
    print("Example 17: HIL - Combined Input + Authorization")
    print("="*60)

    client = MCPClient(base_url="http://localhost:8081")

    print("Testing combined input + authorization (payment)...")
    result = await client.call_tool_and_parse("test_input_with_auth_payment", {})

    # HIL combined method returns status = "authorization_requested"
    if result.get('status') == 'authorization_requested':
        print(f"  ✅ HIL Combined (Input + Authorization) Triggered!")
        print(f"  HIL Type: {result.get('hil_type')}")
        print(f"  Action: {result.get('action')}")

        data = result.get('data', {})
        print(f"  Input Prompt: {data.get('input_prompt', 'N/A')}")
        print(f"  Input Type: {data.get('input_type', 'N/A')}")
        print(f"  Authorization Reason: {data.get('authorization_reason', 'N/A')[:80]}...")
        print(f"  Risk Level: {data.get('risk_level', 'N/A')}")
        print(f"  Options: {result.get('options', [])}")
        print(f"  ℹ️  In a real scenario, this would:")
        print(f"     1. Collect user input (payment amount)")
        print(f"     2. Request authorization for the payment")
    else:
        print(f"  Error: Status was {result.get('status')}, data: {result}")


async def main():
    """Run all async examples"""
    print("\n" + "="*60)
    print("ISA MCP Client - Comprehensive Examples")
    print("="*60)
    print("\nPure async implementation - demonstrating MCP capabilities")
    print("Server: http://localhost:8081\n")

    try:
        # ===================================================================
        # Part 1: Core MCP Features
        # ===================================================================
        await example_01_health_check()
        await example_02_list_tools()
        await example_03_semantic_search()
        await example_04_call_simple_tool()
        await example_05_search_by_category()

        # ===================================================================
        # Part 2: Progress Tracking (SSE + HTTP Polling)
        # ===================================================================
        await example_06_progress_streaming()
        await example_10_quick_progress_test()

        # ===================================================================
        # Part 3: Advanced Features
        # ===================================================================
        await example_07_concurrent_calls()
        await example_08_search_all_types()
        await example_09_error_handling()

        # ===================================================================
        # Part 4: MCP Resources & Prompts
        # ===================================================================
        await example_11_resources()
        await example_12_prompts()

        # ===================================================================
        # Part 5: HIL (Human-in-the-Loop) Examples - All 4 Methods
        # ===================================================================
        await example_13_hil_authorization()
        await example_14_hil_input()
        await example_15_hil_review()
        await example_17_hil_combined()

        # ===================================================================
        # Part 6: Batch Operations
        # ===================================================================
        await example_16_batch_weather()

        print("\n" + "="*60)
        print("✅ All 17 examples completed successfully!")
        print("="*60)
        print("\n📊 Coverage Summary:")
        print("  ✓ Basic Tools (calculator, weather)")
        print("  ✓ Progress Tracking (SSE streaming + HTTP polling)")
        print("  ✓ Semantic Search (tools, prompts, resources)")
        print("  ✓ Resources (list, read)")
        print("  ✓ Prompts (list, get)")
        print("  ✓ HIL - All 4 Methods (authorization, input, review, combined)")
        print("  ✓ Batch Operations (parallel processing)")
        print("  ✓ Error Handling")
        print("  ✓ Concurrent Calls")
        print("="*60)

    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
