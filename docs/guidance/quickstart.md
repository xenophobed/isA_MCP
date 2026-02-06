# Quick Start

Get started with ISA MCP in minutes.

## Prerequisites

- Python 3.10+
- Running MCP server on `http://localhost:8081`

## Installation

```bash
cd /path/to/isA_MCP

# Start the server
python main.py
```

## Basic Client

```python
import asyncio
import aiohttp
import json
from typing import Dict, Any

class MCPClient:
    """Simple MCP client"""

    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url
        self.mcp_endpoint = f"{base_url}/mcp"

    async def get_health(self) -> Dict[str, Any]:
        """Get server health"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/health") as response:
                return await response.json()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
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
                    for line in response_text.strip().split('\n'):
                        if line.startswith('data: '):
                            return json.loads(line[6:])

                return json.loads(response_text)

    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse MCP tool response"""
        if "result" in response:
            result = response["result"]

            # Check for error
            if result.get("isError"):
                content = result.get("content", [{}])[0]
                return {"status": "error", "error": content.get("text", "Unknown error")}

            # Check for structuredContent (HIL tools)
            if "structuredContent" in result:
                structured = result["structuredContent"]
                return structured.get("result", structured)

            # Normal result
            if "content" in result and result["content"]:
                content = result["content"][0]
                if content.get("type") == "text":
                    try:
                        return json.loads(content["text"])
                    except json.JSONDecodeError:
                        return {"text": content["text"], "status": "success"}

        if "error" in response:
            return {"status": "error", "error": response["error"].get("message")}

        return response

    async def call_and_parse(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool and parse response"""
        response = await self.call_tool(tool_name, arguments)
        return self.parse_response(response)


async def main():
    client = MCPClient()

    # Check server health
    health = await client.get_health()
    print(f"Server: {health['status']}")
    print(f"Tools: {health['capabilities']['tools']}")
    print(f"Prompts: {health['capabilities']['prompts']}")
    print(f"Resources: {health['capabilities']['resources']}")

    # Call a tool
    result = await client.call_and_parse("get_weather", {"city": "Tokyo"})
    if result.get('status') == 'success':
        print(f"Temperature: {result['data']['current']['temperature']}°C")

asyncio.run(main())
```

## Core Operations

### Health Check

```python
health = await client.get_health()
# Output:
# {
#   "status": "healthy",
#   "capabilities": {"tools": 88, "prompts": 50, "resources": 9}
# }
```

### List Tools

```python
async with aiohttp.ClientSession() as session:
    async with session.post(
        "http://localhost:8081/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    ) as response:
        # Parse SSE response
        text = await response.text()
        for line in text.strip().split('\n'):
            if line.startswith('data: '):
                data = json.loads(line[6:])
                tools = data['result']['tools']
                print(f"Total tools: {len(tools)}")
```

### Call Tool

```python
result = await client.call_and_parse("calculator", {
    "operation": "add",
    "a": 10,
    "b": 20
})
print(f"Result: {result['data']['result']}")  # 30.0
```

### Semantic Search

```python
async with aiohttp.ClientSession() as session:
    async with session.post(
        "http://localhost:8081/search",
        json={
            "query": "weather information",
            "type": "tool",
            "limit": 5,
            "score_threshold": 0.3
        }
    ) as response:
        results = await response.json()

for tool in results['results']:
    print(f"{tool['name']} (score: {tool['score']:.3f})")
```

### List Resources

```python
async with aiohttp.ClientSession() as session:
    async with session.post(
        "http://localhost:8081/mcp",
        json={"jsonrpc": "2.0", "method": "resources/list", "id": 1},
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    ) as response:
        # Parse and display resources
        ...
```

### Get Prompt

```python
async with aiohttp.ClientSession() as session:
    async with session.post(
        "http://localhost:8081/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "prompts/get",
            "id": 1,
            "params": {
                "name": "intelligent_rag_search_prompt",
                "arguments": {
                    "query": "What is AI?",
                    "available_tools": "search, analyze",
                    "available_resources": "docs",
                    "context": "Learning about AI"
                }
            }
        },
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    ) as response:
        # Parse prompt response
        ...
```

## Concurrent Calls

Execute multiple tool calls in parallel:

```python
results = await asyncio.gather(
    client.call_and_parse("calculator", {"operation": "add", "a": 10, "b": 20}),
    client.call_and_parse("calculator", {"operation": "add", "a": 30, "b": 40}),
    client.call_and_parse("calculator", {"operation": "add", "a": 50, "b": 60})
)

for i, result in enumerate(results, 1):
    print(f"{i}. Result: {result['data']['result']}")
# Output: 30.0, 70.0, 110.0
```

## Error Handling

```python
result = await client.call_and_parse("nonexistent_tool", {})

if result.get('status') == 'error':
    print(f"Error: {result.get('error')}")
    # Output: Error: Unknown tool: nonexistent_tool
```

## Environment Variables

```bash
export MCP_URL="http://localhost:8081"
```

## Next Steps

- [Search Guide](./search.md) - Semantic and hierarchical search
- [HIL Guide](./hil.md) - Human-in-the-loop interactions
- [Progress Guide](./progress.md) - Progress tracking
- [Aggregator Guide](./aggregator.md) - External MCP servers
