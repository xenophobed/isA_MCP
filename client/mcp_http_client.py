#!/usr/bin/env python
"""
Custom MCP HTTP Client
Works with load balancer by using raw HTTP requests instead of streamablehttp_client
"""
import asyncio
import json
import aiohttp
from typing import Dict, List, Any, Optional
import uuid

class MCPHTTPClient:
    """Custom MCP client using raw HTTP requests"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_id = 0
        self.server_info = None
        self.capabilities = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        # Create persistent session with appropriate settings
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=3600,  # 1 hour keep-alive
        )
        
        timeout = aiohttp.ClientTimeout(
            total=None,  # No total timeout for persistent connections
            connect=30,
            sock_read=3600  # 1 hour read timeout
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": "MCP-HTTP-Client/1.0",
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json"
            }
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_next_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id
    
    async def _send_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """Send JSON-RPC request to MCP server"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with.")
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": method
        }
        
        if params:
            payload["params"] = params
        
        try:
            async with self.session.post(f"{self.base_url}/", json=payload) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")
                
                # Handle SSE response
                content_type = response.headers.get('content-type', '')
                if 'text/event-stream' in content_type:
                    # Read SSE stream
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]  # Remove 'data: ' prefix
                            try:
                                data = json.loads(data_str)
                                if 'error' in data:
                                    raise Exception(f"MCP Error: {data['error']}")
                                return data.get('result', data)
                            except json.JSONDecodeError:
                                continue
                    # If we get here, no valid SSE data was found
                    raise Exception("No valid SSE data received")
                else:
                    # Handle regular JSON response
                    data = await response.json()
                    if 'error' in data:
                        raise Exception(f"MCP Error: {data['error']}")
                    return data.get('result', data)
                    
        except Exception as e:
            raise Exception(f"Request failed: {e}")
    
    async def initialize(self) -> Dict:
        """Initialize MCP session"""
        print("🔌 Initializing MCP session...")
        
        result = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "MCP-HTTP-Client",
                "version": "1.0.0"
            }
        })
        
        self.server_info = result.get('serverInfo', {})
        self.capabilities = result.get('capabilities', {})
        
        print(f"✅ Connected to: {self.server_info.get('name', 'Unknown Server')}")
        return result
    
    async def list_tools(self) -> List[Dict]:
        """List available tools"""
        result = await self._send_request("tools/list")
        return result.get('tools', [])
    
    async def list_resources(self) -> List[Dict]:
        """List available resources"""
        result = await self._send_request("resources/list")
        return result.get('resources', [])
    
    async def list_prompts(self) -> List[Dict]:
        """List available prompts"""
        result = await self._send_request("prompts/list")
        return result.get('prompts', [])
    
    async def call_tool(self, name: str, arguments: Dict) -> Any:
        """Call a tool"""
        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        
        # Handle tool result format
        if isinstance(result, dict) and 'content' in result:
            content = result['content']
            if isinstance(content, list) and len(content) > 0:
                first_content = content[0]
                if isinstance(first_content, dict) and 'text' in first_content:
                    return first_content['text']
                else:
                    return str(first_content)
            return str(content)
        
        return result
    
    async def read_resource(self, uri: str) -> Any:
        """Read a resource"""
        result = await self._send_request("resources/read", {
            "uri": uri
        })
        
        # Handle resource result format
        if isinstance(result, dict) and 'contents' in result:
            contents = result['contents']
            if isinstance(contents, list) and len(contents) > 0:
                first_content = contents[0]
                if isinstance(first_content, dict) and 'text' in first_content:
                    return first_content['text']
                else:
                    return str(first_content)
            return str(contents)
        
        return result
    
    async def get_prompt(self, name: str, arguments: Optional[Dict] = None) -> Any:
        """Get a prompt"""
        params: Dict[str, Any] = {"name": name}
        if arguments:
            params["arguments"] = arguments
            
        result = await self._send_request("prompts/get", params)
        
        # Handle prompt result format
        if isinstance(result, dict) and 'messages' in result:
            messages = result['messages']
            if isinstance(messages, list):
                prompt_text = ""
                for message in messages:
                    if isinstance(message, dict) and 'content' in message:
                        content = message['content']
                        if isinstance(content, dict) and 'text' in content:
                            prompt_text += content['text'] + "\n"
                        else:
                            prompt_text += str(content) + "\n"
                return prompt_text.strip()
            return str(messages)
        
        return result

async def test_custom_client():
    """Test the custom MCP client"""
    print("🧪 Testing Custom MCP HTTP Client")
    print("=" * 50)
    
    # Test load balancer connection
    print("\n1️⃣ Testing Load Balancer Connection")
    try:
        async with MCPHTTPClient("http://localhost/mcp") as client:
            # Initialize
            init_result = await client.initialize()
            print(f"✅ Initialization: {init_result['serverInfo']['name']}")
            
            # List tools
            tools = await client.list_tools()
            print(f"✅ Found {len(tools)} tools")
            
            # List resources
            resources = await client.list_resources()
            print(f"✅ Found {len(resources)} resources")
            
            # Test a simple tool call
            if tools:
                tool_name = tools[0]['name']
                print(f"🔧 Testing tool: {tool_name}")
                
                # Try a simple tool call based on available tools
                if tool_name == "check_security_status":
                    result = await client.call_tool(tool_name, {})
                    print(f"✅ Tool result: {str(result)[:100]}...")
                elif tool_name == "get_weather":
                    result = await client.call_tool(tool_name, {"city": "London"})
                    print(f"✅ Tool result: {str(result)[:100]}...")
                else:
                    print(f"ℹ️  Skipping tool test for {tool_name}")
            
            print("🎉 Load balancer connection SUCCESSFUL!")
            
    except Exception as e:
        print(f"❌ Load balancer test failed: {e}")
    
    # Test direct connection for comparison
    print("\n2️⃣ Testing Direct Connection")
    try:
        async with MCPHTTPClient("http://localhost:8001/mcp") as client:
            init_result = await client.initialize()
            print(f"✅ Direct connection: {init_result['serverInfo']['name']}")
            print("🎉 Direct connection SUCCESSFUL!")
            
    except Exception as e:
        print(f"❌ Direct connection test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_custom_client()) 