#!/usr/bin/env python3
"""
MCP Client - Helper for testing MCP tools
Provides a clean interface for calling MCP tools via HTTP requests
"""

import json
import aiohttp
from typing import Dict, Any, Optional, List


class MCPClient:
    """Client for calling MCP tools via HTTP requests"""
    
    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url
        self.mcp_endpoint = f"{base_url}/mcp/"
        self.capabilities_endpoint = f"{base_url}/capabilities"
        self.discover_endpoint = f"{base_url}/discover"
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call an MCP tool via JSON-RPC protocol
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool response as dictionary
        """
        if arguments is None:
            arguments = {}
        
        # MCP JSON-RPC call structure
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.mcp_endpoint,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"
                    }
                ) as response:
                    if response.status == 200:
                        # Handle SSE format response
                        response_text = await response.text()
                        
                        # Parse SSE format: "event: message\ndata: {json_data}"
                        if "data: " in response_text:
                            lines = response_text.strip().split('\n')
                            for line in lines:
                                if line.startswith('data: '):
                                    json_data = line[6:]  # Remove "data: " prefix
                                    try:
                                        result = json.loads(json_data)
                                        return result
                                    except json.JSONDecodeError:
                                        return {
                                            "error": f"Invalid JSON in SSE data: {json_data}",
                                            "status": "error",
                                            "action": tool_name
                                        }
                        
                        # Fallback: try to parse as regular JSON
                        try:
                            result = json.loads(response_text)
                            return result
                        except json.JSONDecodeError:
                            return {
                                "error": f"Could not parse response: {response_text}",
                                "status": "error", 
                                "action": tool_name
                            }
                    else:
                        error_text = await response.text()
                        return {
                            "error": f"HTTP {response.status}: {error_text}",
                            "status": "error",
                            "action": tool_name
                        }
        except Exception as e:
            return {
                "error": str(e),
                "status": "error",
                "action": tool_name
            }
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get available tools from capabilities endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.capabilities_endpoint) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {
                            "error": f"HTTP {response.status}",
                            "text": await response.text(),
                            "status": "error"
                        }
        except Exception as e:
            return {
                "error": str(e),
                "status": "error"
            }
    
    async def discover_tools(self, request: str) -> Dict[str, Any]:
        """Discover relevant tools for a request"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.discover_endpoint,
                    json={"request": request},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {
                            "error": f"HTTP {response.status}",
                            "text": await response.text(),
                            "status": "error"
                        }
        except Exception as e:
            return {
                "error": str(e),
                "status": "error"
            }
    
    async def list_tools(self) -> List[str]:
        """Get list of available tool names"""
        capabilities = await self.get_capabilities()
        if capabilities.get("status") == "success":
            tools = capabilities.get("capabilities", {}).get("tools", {}).get("available", [])
            return tools if isinstance(tools, list) else []
        return []
    
    async def tool_exists(self, tool_name: str) -> bool:
        """Check if a tool exists"""
        tools = await self.list_tools()
        return tool_name in tools
    
    def parse_tool_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse MCP tool response and extract the actual tool result
        
        MCP responses have the format:
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "actual_tool_json_response"
                    }
                ]
            }
        }
        """
        # If already an error response, return as-is
        if response.get("status") == "error":
            return response
            
        if "result" in response:
            result = response["result"]
            if "content" in result and len(result["content"]) > 0:
                content = result["content"][0]
                if content.get("type") == "text":
                    try:
                        # Parse the JSON string in the text field
                        parsed = json.loads(content["text"])
                        return parsed
                    except json.JSONDecodeError:
                        # If it's not JSON, return as is
                        return {"text": content["text"], "status": "success"}
        
        # Handle error responses in MCP format
        if "error" in response:
            return {
                "status": "error",
                "error": response["error"].get("message", "Unknown MCP error"),
                "error_code": response["error"].get("code", -1)
            }
        
        # Return the response as-is if we can't parse it
        return response
    
    async def call_tool_and_parse(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call tool and automatically parse the response
        
        This is a convenience method that combines call_tool and parse_tool_response
        """
        response = await self.call_tool(tool_name, arguments)
        return self.parse_tool_response(response)


# Convenience instance for testing
default_client = MCPClient()


# Convenience functions for testing
async def call_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to call a tool with the default client"""
    return await default_client.call_tool_and_parse(tool_name, kwargs)


async def get_capabilities() -> Dict[str, Any]:
    """Convenience function to get capabilities with the default client"""
    return await default_client.get_capabilities()


async def discover_tools(request: str) -> Dict[str, Any]:
    """Convenience function to discover tools with the default client"""
    return await default_client.discover_tools(request)


async def list_tools() -> List[str]:
    """Convenience function to list tools with the default client"""
    return await default_client.list_tools()