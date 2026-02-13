#!/usr/bin/env python3
"""
ISA MCP Client - Production-Ready Client for MCP Server

This client can be used by other services to interact with the MCP server.
It supports the meta-search approach: discover → get_tool_schema → execute

Usage:
    from client import MCPClient, AsyncMCPClient

    # Async usage (recommended)
    async with AsyncMCPClient() as client:
        # Discover tools
        tools = await client.discover("schedule a meeting")

        # Get schema before calling
        schema = await client.get_tool_schema("create_calendar_event")

        # Execute tool
        result = await client.execute("create_calendar_event", {"title": "Meeting"})

    # Sync wrapper for simple scripts
    client = MCPClient()
    tools = client.discover("weather")
    result = client.execute("get_weather", {"city": "Tokyo"})
"""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from contextlib import asynccontextmanager
from enum import Enum

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    import httpx
except ImportError:
    httpx = None

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


class MCPClientMode(str, Enum):
    """MCP Client connection mode"""

    HTTP = "http"  # Connect to HTTP server (default)
    STDIO = "stdio"  # Spawn local process and communicate via stdio
    AUTO = "auto"  # Try HTTP first, fallback to stdio


@dataclass
class ToolMatch:
    """Represents a discovered tool match"""

    name: str
    type: str
    description: str
    score: float
    skill: Optional[str] = None
    input_schema: Optional[Dict] = None
    output_schema: Optional[Dict] = None


@dataclass
class SearchResult:
    """Result from discover/search operation"""

    matches: List[ToolMatch]
    skills_matched: List[str]
    total_found: int

    def best_match(self) -> Optional[ToolMatch]:
        """Get the highest scoring match"""
        return self.matches[0] if self.matches else None

    def by_skill(self, skill_id: str) -> List[ToolMatch]:
        """Filter matches by skill"""
        return [m for m in self.matches if m.skill == skill_id]


class MCPClientError(Exception):
    """Base exception for MCP client errors"""

    pass


class MCPConnectionError(MCPClientError):
    """Connection error"""

    pass


class MCPToolError(MCPClientError):
    """Tool execution error"""

    pass


class AsyncMCPClient:
    """
    Async MCP Client for service-to-service communication

    Supports the meta-search workflow:
    1. discover() - Find relevant tools using hierarchical search
    2. get_tool_schema() - Get input schema before calling
    3. execute() - Execute the tool

    Also provides direct access to:
    - call_tool() - Direct tool call (when you know the tool name)
    - list_tools/prompts/resources() - List all items
    - get_prompt() - Get prompt with arguments
    - read_resource() - Read resource by URI
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        timeout: float = 30.0,
        auth_token: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.mcp_endpoint = f"{self.base_url}/mcp"
        self.search_endpoint = f"{self.base_url}/search"
        self.api_endpoint = f"{self.base_url}/api/v1"
        self.health_endpoint = f"{self.base_url}/health"
        self.timeout = timeout
        self.auth_token = auth_token
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Initialize the HTTP session"""
        if aiohttp is None:
            raise ImportError("aiohttp is required. Install with: pip install aiohttp")

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        """Close the HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def _ensure_session(self):
        """Ensure session is connected"""
        if self._session is None:
            await self.connect()

    def _parse_sse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Server-Sent Events response format"""
        if "data: " in response_text:
            lines = response_text.strip().split("\n")
            for line in lines:
                if line.startswith("data: "):
                    try:
                        return json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
        # Fallback to regular JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"error": "Invalid response format", "raw": response_text}

    def _parse_tool_result(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse MCP tool response into clean format"""
        if "result" in response:
            result = response["result"]

            # Check for error
            if result.get("isError"):
                if "content" in result and len(result["content"]) > 0:
                    return {
                        "status": "error",
                        "error": result["content"][0].get("text", "Unknown error"),
                    }

            # Check for structuredContent (HIL tools, etc.)
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

        # JSON-RPC error
        if "error" in response:
            return {"status": "error", "error": response["error"].get("message", "Unknown error")}

        return response

    # =========================================================================
    # Meta-Search Methods (Recommended Workflow)
    # =========================================================================

    async def discover(
        self,
        query: str,
        item_type: Optional[str] = None,
        limit: int = 5,
        strategy: str = "hierarchical",
    ) -> SearchResult:
        """
        Discover tools/prompts/resources using hierarchical semantic search.

        This is the first step in the recommended workflow:
        1. discover() → 2. get_tool_schema() → 3. execute()

        Args:
            query: Natural language description of what you want to do
            item_type: Filter by type - "tool", "prompt", or "resource"
            limit: Maximum results to return
            strategy: Search strategy - "hierarchical", "direct", or "hybrid"

        Returns:
            SearchResult with matches, skills, and total count

        Example:
            result = await client.discover("schedule a meeting")
            if result.matches:
                best = result.best_match()
                print(f"Best match: {best.name} (score: {best.score})")
        """
        await self._ensure_session()

        payload = {"query": query, "limit": limit, "strategy": strategy, "include_schemas": False}
        if item_type:
            payload["item_type"] = item_type

        try:
            async with self._session.post(
                f"{self.api_endpoint}/search", json=payload, headers=self._get_headers()
            ) as response:
                data = await response.json()

                matches = [
                    ToolMatch(
                        name=t.get("name", ""),
                        type=t.get("type", "tool"),
                        description=t.get("description", ""),
                        score=t.get("score", 0.0),
                        skill=t.get("primary_skill_id"),
                        input_schema=t.get("inputSchema"),
                        output_schema=t.get("outputSchema"),
                    )
                    for t in data.get("tools", [])
                ]

                skills = [s.get("id") for s in data.get("matched_skills", [])]

                return SearchResult(
                    matches=matches, skills_matched=skills, total_found=len(matches)
                )
        except Exception as e:
            logger.error(f"discover() failed: {e}")
            return SearchResult(matches=[], skills_matched=[], total_found=0)

    async def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """
        Get the input/output schema for a tool.

        Use this after discover() to understand what parameters a tool needs.

        Args:
            tool_name: Exact name of the tool

        Returns:
            Dict with name, description, input_schema
        """
        # Use the meta-tool if available, otherwise list and find
        result = await self.call_tool("get_tool_schema", {"tool_name": tool_name})

        if result.get("status") == "error":
            # Fallback: search tools list
            tools = await self.list_tools()
            for tool in tools:
                if tool.get("name") == tool_name:
                    return {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "input_schema": tool.get("inputSchema", {}),
                    }
            return {"error": f"Tool '{tool_name}' not found"}

        return result

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a discovered tool.

        This is the final step in the recommended workflow.
        Use after discover() and get_tool_schema().

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters matching the input schema

        Returns:
            Tool execution result
        """
        # Use the execute meta-tool if available
        result = await self.call_tool("execute", {"tool_name": tool_name, "parameters": parameters})

        # If execute meta-tool fails, try direct call
        if result.get("status") == "error" and "not found" in str(result.get("error", "")).lower():
            return await self.call_tool(tool_name, parameters)

        return result

    async def list_skills(self) -> List[Dict[str, Any]]:
        """
        List all skill categories.

        Skills are high-level categories that group related tools.
        Use this to understand what capabilities exist.
        """
        result = await self.call_tool("list_skills", {})
        return result.get("skills", [])

    # =========================================================================
    # Prompt Meta-Tools (for meta-tools-only mode)
    # =========================================================================

    async def list_all_prompts(self) -> List[Dict[str, Any]]:
        """
        List all available prompts via meta-tool.

        Use this in meta-tools-only mode to access internal prompts.
        Returns prompts with their arguments.
        """
        result = await self.call_tool("list_prompts", {})
        return result.get("prompts", [])

    async def get_prompt_by_name(
        self, prompt_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get a prompt with rendered arguments via meta-tool.

        Use this in meta-tools-only mode to access internal prompts.

        Args:
            prompt_name: Name of the prompt
            arguments: Arguments to render into the prompt

        Returns:
            Rendered prompt with messages
        """
        return await self.call_tool(
            "get_prompt", {"prompt_name": prompt_name, "arguments": arguments}
        )

    # =========================================================================
    # Resource Meta-Tools (for meta-tools-only mode)
    # =========================================================================

    async def list_all_resources(self) -> List[Dict[str, Any]]:
        """
        List all available resources via meta-tool.

        Use this in meta-tools-only mode to access internal resources.
        """
        result = await self.call_tool("list_resources", {})
        return result.get("resources", [])

    async def read_resource_by_uri(self, uri: str) -> Dict[str, Any]:
        """
        Read a resource by URI via meta-tool.

        Use this in meta-tools-only mode to access internal resources.

        Args:
            uri: Resource URI (e.g., "knowledge://stats/global")

        Returns:
            Resource content with mime_type
        """
        return await self.call_tool("read_resource", {"uri": uri})

    # =========================================================================
    # Direct Access Methods
    # =========================================================================

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool directly (when you know the exact tool name).

        For discovery workflow, use discover() → execute() instead.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Parsed tool result
        """
        await self._ensure_session()

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        try:
            async with self._session.post(
                self.mcp_endpoint, json=payload, headers=self._get_headers()
            ) as response:
                response_text = await response.text()
                data = self._parse_sse_response(response_text)
                return self._parse_tool_result(data)
        except Exception as e:
            logger.error(f"call_tool({tool_name}) failed: {e}")
            return {"status": "error", "error": str(e)}

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools"""
        await self._ensure_session()

        payload = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}

        try:
            async with self._session.post(
                self.mcp_endpoint, json=payload, headers=self._get_headers()
            ) as response:
                response_text = await response.text()
                data = self._parse_sse_response(response_text)
                return data.get("result", {}).get("tools", [])
        except Exception as e:
            logger.error(f"list_tools() failed: {e}")
            return []

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List all available prompts"""
        await self._ensure_session()

        payload = {"jsonrpc": "2.0", "method": "prompts/list", "id": 1}

        try:
            async with self._session.post(
                self.mcp_endpoint, json=payload, headers=self._get_headers()
            ) as response:
                response_text = await response.text()
                data = self._parse_sse_response(response_text)
                return data.get("result", {}).get("prompts", [])
        except Exception as e:
            logger.error(f"list_prompts() failed: {e}")
            return []

    async def get_prompt(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a prompt with rendered arguments.

        Args:
            name: Prompt name
            arguments: Arguments to render into the prompt
        """
        await self._ensure_session()

        payload = {
            "jsonrpc": "2.0",
            "method": "prompts/get",
            "id": 1,
            "params": {"name": name, "arguments": arguments},
        }

        try:
            async with self._session.post(
                self.mcp_endpoint, json=payload, headers=self._get_headers()
            ) as response:
                response_text = await response.text()
                data = self._parse_sse_response(response_text)
                return data.get("result", {})
        except Exception as e:
            logger.error(f"get_prompt({name}) failed: {e}")
            return {"error": str(e)}

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available resources"""
        await self._ensure_session()

        payload = {"jsonrpc": "2.0", "method": "resources/list", "id": 1}

        try:
            async with self._session.post(
                self.mcp_endpoint, json=payload, headers=self._get_headers()
            ) as response:
                response_text = await response.text()
                data = self._parse_sse_response(response_text)
                return data.get("result", {}).get("resources", [])
        except Exception as e:
            logger.error(f"list_resources() failed: {e}")
            return []

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a resource by URI.

        Args:
            uri: Resource URI (e.g., "knowledge://stats/global")
        """
        await self._ensure_session()

        payload = {"jsonrpc": "2.0", "method": "resources/read", "id": 1, "params": {"uri": uri}}

        try:
            async with self._session.post(
                self.mcp_endpoint, json=payload, headers=self._get_headers()
            ) as response:
                response_text = await response.text()
                data = self._parse_sse_response(response_text)
                return data.get("result", {})
        except Exception as e:
            logger.error(f"read_resource({uri}) failed: {e}")
            return {"error": str(e)}

    # =========================================================================
    # Health & Status
    # =========================================================================

    async def health(self) -> Dict[str, Any]:
        """Check server health"""
        await self._ensure_session()

        try:
            async with self._session.get(
                self.health_endpoint, headers=self._get_headers()
            ) as response:
                return await response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def is_healthy(self) -> bool:
        """Quick health check"""
        result = await self.health()
        return "healthy" in str(result.get("status", "")).lower()

    async def get_default_tools(self) -> List[Dict[str, Any]]:
        """
        Get default tools (meta-tools that are always available).

        Default tools are the gateway tools for accessing all other capabilities:
        - discover, get_tool_schema, execute
        - list_skills, list_prompts, get_prompt, list_resources, read_resource

        Returns:
            List of default tool definitions
        """
        await self._ensure_session()

        try:
            async with self._session.get(
                f"{self.api_endpoint}/tools/defaults", headers=self._get_headers()
            ) as response:
                data = await response.json()
                return data.get("tools", [])
        except Exception as e:
            logger.error(f"get_default_tools() failed: {e}")
            return []

    # =========================================================================
    # Progress Tracking
    # =========================================================================

    async def start_task(
        self, task_type: str, duration_seconds: int = 30, steps: int = 10
    ) -> Dict[str, Any]:
        """Start a long-running task"""
        return await self.call_tool(
            "start_long_task",
            {"task_type": task_type, "duration_seconds": duration_seconds, "steps": steps},
        )

    async def get_task_progress(self, operation_id: str) -> Dict[str, Any]:
        """Get task progress by operation ID"""
        return await self.call_tool("get_task_progress", {"operation_id": operation_id})

    async def get_task_result(self, operation_id: str) -> Dict[str, Any]:
        """Get task result after completion"""
        return await self.call_tool("get_task_result", {"operation_id": operation_id})

    async def stream_progress(
        self, operation_id: str, callback: Optional[Callable[[Dict], None]] = None
    ) -> Dict[str, Any]:
        """
        Stream task progress via SSE.

        Args:
            operation_id: Operation ID from start_task()
            callback: Optional callback for each progress update

        Returns:
            Final progress data
        """
        if httpx is None:
            raise ImportError("httpx required for streaming. Install with: pip install httpx")

        stream_url = f"{self.base_url}/progress/{operation_id}/stream"
        final_data = None

        async with httpx.AsyncClient(timeout=300.0) as http_client:
            async with http_client.stream("GET", stream_url) as response:
                if response.status_code != 200:
                    return {"status": "error", "error": f"HTTP {response.status_code}"}

                event_type = None

                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data_str = line.split(":", 1)[1].strip()
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        if event_type == "progress":
                            final_data = data
                            if callback:
                                callback(data)
                        elif event_type == "done":
                            return final_data or data
                        elif event_type == "error":
                            return {"status": "error", "error": data.get("error")}

        return final_data or {"status": "error", "error": "Stream ended"}

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def search_and_execute(
        self, query: str, parameters: Dict[str, Any], item_type: str = "tool"
    ) -> Dict[str, Any]:
        """
        One-liner: Discover best matching tool and execute it.

        Args:
            query: What you want to do
            parameters: Parameters for the tool
            item_type: Type to search for

        Returns:
            Tool execution result
        """
        result = await self.discover(query, item_type=item_type, limit=1)
        if not result.matches:
            return {"status": "error", "error": f"No tools found for: {query}"}

        best = result.best_match()
        return await self.execute(best.name, parameters)

    async def get_prompt_text(self, name: str, arguments: Dict[str, Any]) -> str:
        """Get rendered prompt text (convenience method)"""
        result = await self.get_prompt(name, arguments)
        messages = result.get("messages", [])
        if messages:
            content = messages[0].get("content", {})
            return content.get("text", "")
        return ""


class MCPClient:
    """
    Synchronous wrapper for AsyncMCPClient.

    Useful for simple scripts and non-async codebases.
    For async code, use AsyncMCPClient directly.

    Usage:
        client = MCPClient()
        result = client.discover("weather")
        data = client.execute("get_weather", {"city": "Tokyo"})
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        timeout: float = 30.0,
        auth_token: Optional[str] = None,
    ):
        self._async_client = AsyncMCPClient(base_url, timeout, auth_token)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop"""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
            return self._loop

    def _run(self, coro):
        """Run coroutine synchronously"""
        loop = self._get_loop()
        if loop.is_running():
            # If we're already in an async context, create a task
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)

    def __enter__(self):
        self._run(self._async_client.connect())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._run(self._async_client.close())

    # Meta-search methods
    def discover(self, query: str, item_type: Optional[str] = None, limit: int = 5) -> SearchResult:
        """Discover tools using hierarchical search"""
        return self._run(self._async_client.discover(query, item_type, limit))

    def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """Get tool input schema"""
        return self._run(self._async_client.get_tool_schema(tool_name))

    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool"""
        return self._run(self._async_client.execute(tool_name, parameters))

    def list_skills(self) -> List[Dict[str, Any]]:
        """List skill categories"""
        return self._run(self._async_client.list_skills())

    # Meta-tools for prompts/resources (meta-tools-only mode)
    def list_all_prompts(self) -> List[Dict[str, Any]]:
        """List all prompts via meta-tool"""
        return self._run(self._async_client.list_all_prompts())

    def get_prompt_by_name(self, prompt_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get prompt via meta-tool"""
        return self._run(self._async_client.get_prompt_by_name(prompt_name, arguments))

    def list_all_resources(self) -> List[Dict[str, Any]]:
        """List all resources via meta-tool"""
        return self._run(self._async_client.list_all_resources())

    def read_resource_by_uri(self, uri: str) -> Dict[str, Any]:
        """Read resource via meta-tool"""
        return self._run(self._async_client.read_resource_by_uri(uri))

    # Direct methods
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool directly"""
        return self._run(self._async_client.call_tool(tool_name, arguments))

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools"""
        return self._run(self._async_client.list_tools())

    def list_prompts(self) -> List[Dict[str, Any]]:
        """List all prompts"""
        return self._run(self._async_client.list_prompts())

    def get_prompt(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get prompt with arguments"""
        return self._run(self._async_client.get_prompt(name, arguments))

    def list_resources(self) -> List[Dict[str, Any]]:
        """List all resources"""
        return self._run(self._async_client.list_resources())

    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read resource by URI"""
        return self._run(self._async_client.read_resource(uri))

    # Health
    def health(self) -> Dict[str, Any]:
        """Check server health"""
        return self._run(self._async_client.health())

    def is_healthy(self) -> bool:
        """Quick health check"""
        return self._run(self._async_client.is_healthy())

    def get_default_tools(self) -> List[Dict[str, Any]]:
        """Get default tools (meta-tools)"""
        return self._run(self._async_client.get_default_tools())

    # Convenience
    def search_and_execute(self, query: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Discover and execute in one call"""
        return self._run(self._async_client.search_and_execute(query, parameters))


# =============================================================================
# Quick Test / Example
# =============================================================================


async def _test_client():
    """Test the client"""
    print("Testing AsyncMCPClient...")

    async with AsyncMCPClient() as client:
        # Health check
        print("\n1. Health Check:")
        health = await client.health()
        print(f"   Status: {health.get('status')}")

        # Discover
        print("\n2. Discover 'weather' tools:")
        result = await client.discover("get weather information")
        print(f"   Found {result.total_found} matches")
        for match in result.matches[:3]:
            print(f"   - {match.name} (score: {match.score:.3f})")

        # List tools
        print("\n3. List all tools:")
        tools = await client.list_tools()
        print(f"   Total tools: {len(tools)}")

        # List prompts
        print("\n4. List all prompts:")
        prompts = await client.list_prompts()
        print(f"   Total prompts: {len(prompts)}")

        # List resources
        print("\n5. List all resources:")
        resources = await client.list_resources()
        print(f"   Total resources: {len(resources)}")

        # Execute tool
        print("\n6. Execute 'calculator' tool:")
        result = await client.call_tool("calculator", {"operation": "add", "a": 10, "b": 20})
        print(f"   Result: {result}")

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(_test_client())
