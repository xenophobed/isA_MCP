# ISA MCP Client - Complete Guide (Based on Real Tests)

## 📚 Overview

The ISA MCP Client provides a production-ready interface to interact with the MCP server. All examples below are tested and verified working.

**Current Capabilities** (as of testing):
- ✅ 88 Tools
- ✅ 50 Prompts
- ✅ 9 Resources
- ✅ Semantic Search
- ✅ Progress Tracking (SSE + HTTP)
- ✅ HIL (Human-in-the-Loop) - 4 methods

---

## 🚀 Quick Start

### Installation

```bash
cd /path/to/isA_MCP
# Server should be running on http://localhost:8081
python main.py
```

### Basic Usage

```python
#!/usr/bin/env python3
import asyncio
import aiohttp
import json
from typing import Dict, Any

class MCPClient:
    """Simple standalone MCP client"""

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

                return json.loads(response_text)

    def parse_tool_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse MCP tool response"""
        if "result" in response:
            result = response["result"]

            # Check for error
            if result.get("isError"):
                if "content" in result:
                    content = result["content"][0]
                    return {
                        "status": "error",
                        "error": content.get("text", "Unknown error")
                    }

            # Check for structuredContent (used by HIL tools)
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


# Example usage
async def main():
    client = MCPClient()

    # Check server health
    health = await client.get_health()
    print(f"Server: {health['status']}")
    print(f"Tools: {health['capabilities']['tools']}")

    # Call a tool
    result = await client.call_tool_and_parse("get_weather", {"city": "Tokyo"})
    print(f"Weather: {result['data']['current']['temperature']}°C")

asyncio.run(main())
```

---

## 📖 Core Features

### 1. Server Health Check

**Tested & Working ✅**

```python
async def check_health():
    client = MCPClient(base_url="http://localhost:8081")
    health = await client.get_health()

    print(f"Status: {health['status']}")
    # Output: healthy ✅ HOT RELOAD IS WORKING PERFECTLY!

    print(f"Tools: {health['capabilities']['tools']}")      # 88
    print(f"Prompts: {health['capabilities']['prompts']}")  # 50
    print(f"Resources: {health['capabilities']['resources']}")  # 9
```

### 2. List Tools

**Tested & Working ✅**

```python
async def list_tools():
    client = MCPClient()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{client.mcp_endpoint}",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
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
                        tools = data['result']['tools']

                        print(f"Total tools: {len(tools)}")
                        for tool in tools[:10]:
                            print(f"  - {tool['name']}")
                        break
```

### 3. Semantic Search

**Tested & Working ✅**

```python
async def search_tools(query: str):
    """Search for tools using semantic search"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8081/search",
            json={
                "query": query,
                "type": "tool",  # or "prompt", "resource", or omit for all
                "limit": 5,
                "score_threshold": 0.3
            }
        ) as response:
            results = await response.json()

    print(f"Found {results['count']} tools:")
    for result in results['results']:
        print(f"  - {result['name']} (score: {result['score']:.3f})")
        print(f"    {result['description'][:80]}...")

# Example output:
# Found 3 tools:
#   - get_weather (score: 0.670)
#     Get check query weather temperature forecast conditions city location...
#   - stream_weather (score: 0.553)
#     Stream continuous real-time weather updates live monitoring periodic...
#   - batch_weather (score: 0.423)
#     Batch multiple cities weather query parallel sequential list processing...
```

### 4. Call Tools

**Tested & Working ✅**

```python
async def call_weather_tool():
    client = MCPClient()

    # Simple tool call
    result = await client.call_tool_and_parse("get_weather", {
        "city": "Tokyo"
    })

    if result.get('status') == 'success':
        data = result['data']
        print(f"City: {data['city']}")
        print(f"Temperature: {data['current']['temperature']}°C")
        print(f"Condition: {data['current']['condition']}")

    # Output:
    # City: Tokyo
    # Temperature: 18.0°C
    # Condition: Rainy

# Calculator example
async def call_calculator():
    client = MCPClient()

    result = await client.call_tool_and_parse("calculator", {
        "operation": "add",
        "a": 10,
        "b": 20
    })

    print(f"Result: {result['data']['result']}")  # 30.0
```

### 5. Concurrent Tool Calls

**Tested & Working ✅ (0.05s for 3 calls)**

```python
async def concurrent_calls():
    client = MCPClient()

    # Execute 3 calculations in parallel
    results = await asyncio.gather(
        client.call_tool_and_parse("calculator", {"operation": "add", "a": 10, "b": 20}),
        client.call_tool_and_parse("calculator", {"operation": "add", "a": 30, "b": 40}),
        client.call_tool_and_parse("calculator", {"operation": "add", "a": 50, "b": 60})
    )

    for i, result in enumerate(results, 1):
        print(f"{i}. Result: {result['data']['result']}")

    # Output:
    # 1. Result: 30.0
    # 2. Result: 70.0
    # 3. Result: 110.0
```

---

## 📦 Resources

**Tested & Working ✅ (9 resources available)**

### List Resources

```python
async def list_resources():
    client = MCPClient()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{client.mcp_endpoint}",
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
                        resources = data['result']['resources']

                        for resource in resources:
                            print(f"{resource['name']}: {resource['uri']}")
                        break

# Output:
# get_pii_config: guardrail://config/pii
# get_medical_config: guardrail://config/medical
# get_compliance_policies: guardrail://policies/compliance
# ... (9 total)
```

### Read Resource

```python
async def read_resource(uri: str):
    """Read a resource by URI"""
    client = MCPClient()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{client.mcp_endpoint}",
            json={
                "jsonrpc": "2.0",
                "method": "resources/read",
                "id": 1,
                "params": {"uri": uri}
            },
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

                        if 'result' in data:
                            result = data['result']
                            contents = result.get('contents', [])
                            if contents:
                                content = contents[0]
                                print(f"MIME Type: {content['mimeType']}")
                                print(f"Content: {content['text'][:200]}...")
                        break

# Example
await read_resource("guardrail://config/pii")
```

---

## 📝 Prompts

**Tested & Working ✅ (50 prompts available)**

### List Prompts

```python
async def list_prompts():
    client = MCPClient()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{client.mcp_endpoint}",
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
                        prompts = data['result']['prompts']

                        for prompt in prompts[:5]:
                            print(f"{prompt['name']}")
                            print(f"  {prompt.get('description', 'N/A')[:80]}...")
                        break

# Output:
# intelligent_rag_search_prompt
#   Generate a prompt for intelligent RAG search and retrieval workflow...
# rag_collection_analysis_prompt
#   Generate a prompt for analyzing and understanding RAG collections...
# ... (50 total)
```

### Get Prompt

```python
async def get_prompt(name: str, arguments: dict):
    """Get a prompt with arguments"""
    client = MCPClient()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{client.mcp_endpoint}",
            json={
                "jsonrpc": "2.0",
                "method": "prompts/get",
                "id": 1,
                "params": {
                    "name": name,
                    "arguments": arguments
                }
            },
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

                        if 'result' in data:
                            result = data['result']
                            messages = result.get('messages', [])
                            if messages:
                                msg = messages[0]
                                print(f"Role: {msg['role']}")
                                content = msg['content']
                                print(f"Content: {content['text'][:200]}...")
                        break

# Example
await get_prompt("intelligent_rag_search_prompt", {
    "query": "What is AI?",
    "available_tools": "search, analyze",
    "available_resources": "docs",
    "context": "Learning about AI"
})

# Output:
# Role: user
# Content: # Intelligent RAG Search and Retrieval Strategy
#
# ## User Query: "What is AI?"
#
# ## Your Mission
# You are an intelligent RAG (Retrieval-Augmented Generation) assistant...
```

---

## 👤 HIL (Human-in-the-Loop) - 4 Methods

**All 4 methods tested & working ✅**

### 1. Authorization (`request_authorization`)

**Status: `authorization_requested`**

```python
async def test_authorization():
    client = MCPClient()

    result = await client.call_tool_and_parse("test_authorization_low_risk", {})

    # HIL tools return different status
    if result.get('status') == 'authorization_requested':
        print(f"HIL Type: {result['hil_type']}")  # authorization
        print(f"Action: {result['action']}")      # ask_human

        data = result['data']
        print(f"Request Action: {data['action']}")
        print(f"Risk Level: {data['risk_level']}")
        print(f"Reason: {data['reason']}")
        print(f"Options: {result['options']}")  # ['approve', 'reject']

# Output:
# HIL Type: authorization
# Action: ask_human
# Request Action: Update cache TTL configuration
# Risk Level: low
# Reason: Increase cache duration from 5 minutes to 10 minutes...
# Options: ['approve', 'reject']
```

### 2. Input Collection (`request_input`)

**Status: `human_input_requested`**

```python
async def test_input():
    client = MCPClient()

    result = await client.call_tool_and_parse("test_input_credentials", {})

    if result.get('status') == 'human_input_requested':
        print(f"HIL Type: {result['hil_type']}")  # input
        print(f"Action: {result['action']}")      # ask_human

        data = result['data']
        print(f"Prompt: {data['prompt']}")
        print(f"Input Type: {data['input_type']}")
        print(f"Options: {result['options']}")  # ['submit', 'skip', 'cancel']

# Output:
# HIL Type: input
# Action: ask_human
# Prompt: Enter OpenAI API Key
# Input Type: credentials
# Options: ['submit', 'skip', 'cancel']
```

### 3. Content Review (`request_review`)

**Status: `human_input_requested`**

```python
async def test_review():
    client = MCPClient()

    result = await client.call_tool_and_parse("test_review_execution_plan", {})

    if result.get('status') == 'human_input_requested':
        print(f"HIL Type: {result['hil_type']}")  # review
        print(f"Action: {result['action']}")      # ask_human

        data = result['data']
        print(f"Content Type: {data['content_type']}")  # execution_plan
        print(f"Editable: {data['editable']}")          # True

        # Content is a structured dict
        content = data['content']
        print(f"Plan Title: {content['plan_title']}")
        print(f"Tasks: {content['total_tasks']}")
        print(f"Options: {result['options']}")  # ['approve', 'edit', 'reject']

# Output:
# HIL Type: review
# Action: ask_human
# Content Type: execution_plan
# Editable: True
# Plan Title: E-commerce Website Deployment Plan
# Tasks: 4
# Options: ['approve', 'edit', 'reject']
```

### 4. Input + Authorization (`request_input_with_authorization`)

**Status: `authorization_requested`**

```python
async def test_combined():
    client = MCPClient()

    result = await client.call_tool_and_parse("test_input_with_auth_payment", {})

    if result.get('status') == 'authorization_requested':
        print(f"HIL Type: {result['hil_type']}")  # input_with_authorization
        print(f"Action: {result['action']}")      # ask_human

        data = result['data']
        print(f"Input Prompt: {data['input_prompt']}")
        print(f"Input Type: {data['input_type']}")
        print(f"Authorization Reason: {data['authorization_reason']}")
        print(f"Risk Level: {data['risk_level']}")

# Output:
# HIL Type: input_with_authorization
# Action: ask_human
# Input Prompt: Enter payment amount in USD
# Input Type: payment_amount
# Authorization Reason: Process payment transaction of $500...
# Risk Level: high
```

---

## ⏱️ Progress Tracking

### Method 1: SSE Streaming (Recommended)

**Tested & Working ✅**

```python
async def stream_progress(base_url: str, operation_id: str, callback=None):
    """Monitor progress via SSE streaming"""
    try:
        import httpx

        stream_url = f"{base_url}/progress/{operation_id}/stream"

        async with httpx.AsyncClient(timeout=300.0) as http_client:
            async with http_client.stream('GET', stream_url) as response:
                if response.status_code != 200:
                    return {"status": "error", "error": f"HTTP {response.status_code}"}

                event_type = None
                final_data = None

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
                            return {"status": "error", "error": data.get('error')}

        return final_data or {"status": "error", "error": "Stream ended"}

    except Exception as e:
        return {"status": "error", "error": str(e)}


# Complete example
async def start_and_stream(base_url: str, task_type: str,
                          duration_seconds: int = 30, steps: int = 10,
                          callback=None):
    """Start task and stream progress (one-liner)"""
    client = MCPClient(base_url)

    # Start task
    response = await client.call_tool_and_parse("start_long_task", {
        "task_type": task_type,
        "duration_seconds": duration_seconds,
        "steps": steps
    })

    if response.get('status') != 'success':
        return response

    operation_id = response['data']['operation_id']

    # Stream progress
    final_data = await stream_progress(base_url, operation_id, callback)

    # Get final result
    if final_data and final_data.get('status') == 'completed':
        result = await client.call_tool_and_parse("get_task_result", {
            "operation_id": operation_id
        })
        return result

    return final_data


# Usage
async def main():
    def on_progress(data):
        print(f"Progress: {data['progress']:.0f}% - {data['message']}")

    result = await start_and_stream(
        base_url="http://localhost:8081",
        task_type="data_analysis",
        duration_seconds=10,
        steps=5,
        callback=on_progress
    )

    print(f"Final result: {result}")

# Output:
# Progress: 20% - Processing step 1/5 - data_analysis
# Progress: 40% - Processing step 2/5 - data_analysis
# Progress: 60% - Processing step 3/5 - data_analysis
# Progress: 80% - Processing step 4/5 - data_analysis
# Progress: 100% - Processing step 5/5 - data_analysis
# Progress: 100% - Completed 5 steps successfully
# Final result: {...}
```

### Method 2: HTTP Polling (Fallback)

**Tested & Working ✅**

```python
async def poll_progress():
    client = MCPClient()

    # Start task
    response = await client.call_tool_and_parse("start_long_task", {
        "task_type": "data_processing",
        "duration_seconds": 5,
        "steps": 3
    })

    operation_id = response['data']['operation_id']
    print(f"Task started: {operation_id[:8]}...")

    # Poll for progress
    for i in range(10):
        await asyncio.sleep(1)

        progress = await client.call_tool_and_parse("get_task_progress", {
            "operation_id": operation_id
        })

        if progress.get('status') == 'success':
            data = progress['data']
            prog = data['progress']
            msg = data['message']
            status = data['status']

            print(f"{prog:.0f}% - {msg} [{status}]")

            if status == 'completed':
                print("Task completed!")
                break

# Output:
# Task started: cc31cfe9...
#   33% - Processing step 1/3 - data_processing [running]
#   67% - Processing step 2/3 - data_processing [running]
#   100% - Processing step 3/3 - data_processing [running]
#   100% - Completed 3 steps successfully [completed]
# Task completed!
```

---

## 🔄 Batch Operations

**Tested & Working ✅**

```python
async def batch_weather():
    client = MCPClient()

    cities = ["Tokyo", "New York", "London"]

    result = await client.call_tool_and_parse("batch_weather", {
        "cities": cities,
        "parallel": True  # Use parallel processing
    })

    if result.get('status') == 'success':
        data = result['data']
        print(f"Total cities: {data['total_cities']}")
        print(f"Successful: {data['successful']}")
        print(f"Failed: {data['failed']}")

        for r in data['results']:
            print(f"- {r['city']}: {r['status']}")

# Output:
# Total cities: 3
# Successful: 3
# Failed: 0
# - Tokyo: success
# - New York: success
# - London: success
```

---

## 🛡️ Error Handling

**Tested & Working ✅**

```python
async def error_handling():
    client = MCPClient()

    # Try to call non-existent tool
    result = await client.call_tool_and_parse("nonexistent_tool", {})

    if result.get('status') == 'error':
        print(f"Error handled correctly: {result.get('error')}")

    # Output:
    # Error handled correctly: Unknown tool: nonexistent_tool
```

---

## 📊 Complete Example: All 17 Scenarios

See `examples/mcp_client_example.py` for a comprehensive example covering:

1. ✅ Server Health Check
2. ✅ List Available Tools (88 tools)
3. ✅ Semantic Search for Tools
4. ✅ Call Simple Tool (get_weather)
5. ✅ Search Tools by Category
6. ✅ Progress Tracking (SSE Streaming)
7. ✅ Concurrent Tool Calls (0.05s for 3)
8. ✅ Search All Types (Tools + Prompts + Resources)
9. ✅ Error Handling
10. ✅ Quick Progress Test (HTTP Polling)
11. ✅ List and Read Resources (9 resources)
12. ✅ List and Get Prompts (50 prompts)
13. ✅ HIL - Authorization Request
14. ✅ HIL - Input Collection
15. ✅ HIL - Content Review
16. ✅ Batch Weather Query
17. ✅ HIL - Combined Input + Authorization ⭐ (4th method)

Run it:
```bash
python examples/mcp_client_example.py

# Expected output:
# ✅ All 17 examples completed successfully!
```

---

## 🎯 Best Practices

### 1. Use Semantic Search

```python
# ✅ Good: Find tools efficiently
results = await search_tools("weather information")

# ❌ Bad: List all and filter manually
all_tools = await list_tools()
filtered = [t for t in all_tools if 'weather' in t]
```

### 2. Use SSE for Progress

```python
# ✅ Good: Real-time updates
result = await start_and_stream(task, callback=show_progress)

# ⚠️ OK: Polling (fallback)
result = await poll_until_complete(op_id, callback=show_progress)
```

### 3. Concurrent Tool Calls

```python
# ✅ Good: Parallel execution (3x faster)
results = await asyncio.gather(
    call_tool("tool1", arg="a"),
    call_tool("tool2", arg="b"),
    call_tool("tool3", arg="c")
)

# ❌ Bad: Sequential (3x slower)
result1 = await call_tool("tool1", arg="a")
result2 = await call_tool("tool2", arg="b")
result3 = await call_tool("tool3", arg="c")
```

### 4. Parse HIL Responses

```python
# HIL tools use different status values:
# - Authorization: "authorization_requested"
# - Input: "human_input_requested"
# - Review: "human_input_requested"
# - Combined: "authorization_requested"

# Always check structuredContent for HIL tools
if "structuredContent" in result:
    parsed = result["structuredContent"]["result"]
    status = parsed["status"]
    hil_type = parsed["hil_type"]
```

---

## 🚀 Production Tips

### Environment Variables

```bash
export MCP_URL="http://localhost:8081"
```

### Connection Pooling

```python
# Reuse client instance
client = MCPClient()
for i in range(100):
    result = await client.call_tool_and_parse("tool", {})
```

### Timeout Handling

```python
try:
    async with asyncio.timeout(30):  # 30 second timeout
        result = await client.call_tool_and_parse("long_task", {})
except asyncio.TimeoutError:
    print("Request timed out")
```

---

## 📝 Testing

Run the test suite:
```bash
# Run all 17 examples
python examples/mcp_client_example.py

# Expected output:
# ✅ All 17 examples completed successfully!
#
# 📊 Coverage Summary:
#   ✓ Basic Tools (calculator, weather)
#   ✓ Progress Tracking (SSE streaming + HTTP polling)
#   ✓ Semantic Search (tools, prompts, resources)
#   ✓ Resources (list, read)
#   ✓ Prompts (list, get)
#   ✓ HIL - All 4 Methods (authorization, input, review, combined)
#   ✓ Batch Operations (parallel processing)
#   ✓ Error Handling
#   ✓ Concurrent Calls
```

---

## 🎉 Summary

The ISA MCP Client provides:

- ✅ **88 Tools** ready to use
- ✅ **50 Prompts** for intelligent workflows
- ✅ **9 Resources** for configuration and data
- ✅ **4 HIL Methods** for human interaction
- ✅ **Semantic Search** for tool discovery
- ✅ **SSE Streaming** for real-time progress
- ✅ **HTTP Polling** as fallback
- ✅ **Concurrent Execution** for performance
- ✅ **Error Handling** with proper status codes
- ✅ **Production Ready** - all tested and verified

**Start building AI workflows in minutes, not hours!** 🚀

---

## 📚 See Also

- **Examples**: `examples/mcp_client_example.py` - 17 comprehensive scenarios (All 4 HIL methods!)
- **Base Tool**: `tools/base_tool.py` - Tool implementation guide
- **HIL Tools**: `tools/example_tools/hil_example_tools.py` - All 4 HIL methods demonstrated
- **Server**: `main.py` - MCP server implementation
