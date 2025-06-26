#!/usr/bin/env python3
"""
Smart MCP Server with AI-Powered Capability Discovery
Auto-discovery system for tools, prompts, and resources
"""
import argparse
import asyncio
import uvicorn
import json
from typing import List, Dict, Optional
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import logging

# Core services
from core.security import initialize_security
from core.monitoring import monitor_manager
from core.auto_discovery import AutoDiscoverySystem
from resources.database_init import initialize_database

# AI selectors
from tools.core.tool_selector import ToolSelector
from prompts.prompt_selector import PromptSelector
from resources.resource_selector import ResourceSelector

logger = logging.getLogger(__name__)

class SmartMCPServer:
    """Clean, AI-powered MCP server with automatic discovery"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.mcp = None
        self.tool_selector = None
        self.prompt_selector = None
        self.resource_selector = None
        self.auto_discovery = AutoDiscoverySystem()
        self.config = config or {}
    
    async def initialize(self) -> FastMCP:
        """Initialize the complete MCP server with all capabilities"""
        print("🚀 Initializing Smart MCP Server...")
        
        # 1. Initialize core services
        await self._initialize_core_services()
        
        # 2. Create MCP server
        self.mcp = FastMCP("Smart MCP Server", stateless_http=True)
        
        # 3. Register all capabilities
        await self._register_all_capabilities()
        
        # 4. Initialize AI selectors
        await self._initialize_ai_selectors()
        
        print("✅ Smart MCP Server initialized successfully")
        return self.mcp
    
    async def _initialize_core_services(self):
        """Initialize security, monitoring, and database"""
        print("🔧 Initializing core services...")
        
        # Security manager
        initialize_security(monitor_manager)
        print("  ✅ Security manager initialized")
        
        # Database
        initialize_database()
        print("  ✅ Database initialized")
        
        print("✅ Core services ready")
    
    async def _register_all_capabilities(self):
        """Auto-discover and register all capabilities, then extract metadata from MCP server"""
        print("📦 Auto-discovering and registering capabilities...")
        
        # Use auto-discovery system for registration
        await self.auto_discovery.auto_register_with_mcp(self.mcp, self.config)
        
        print("✅ All capabilities auto-registered")
    
    async def _initialize_ai_selectors(self):
        """Initialize AI-powered capability selectors"""
        print("🧠 Initializing AI selectors...")
        
        # Tool selector with comprehensive tool metadata
        try:
            self.tool_selector = ToolSelector()
            # Use the comprehensive tool info extraction instead of auto-discovery metadata
            await self.tool_selector.initialize()  # This uses get_all_tool_info()
            print("  ✅ Tool selector ready")
        except Exception as e:
            print(f"  ⚠️ Tool selector failed: {e}")
            self.tool_selector = None
        
        # Prompt selector
        try:
            self.prompt_selector = PromptSelector()
            await self.prompt_selector.initialize()
            print("  ✅ Prompt selector ready")
        except Exception as e:
            print(f"  ⚠️ Prompt selector failed: {e}")
            self.prompt_selector = None
        
        # Resource selector
        try:
            self.resource_selector = ResourceSelector()
            await self.resource_selector.initialize()
            print("  ✅ Resource selector ready")
        except Exception as e:
            print(f"  ⚠️ Resource selector failed: {e}")
            self.resource_selector = None
        
        print("✅ AI selectors initialized")
    
    async def discover_capabilities(self, user_request: str) -> Dict:
        """AI-powered capability discovery based on user request"""
        print(f"🎯 Discovering capabilities for: '{user_request}'")
        
        result = {
            "status": "success",
            "user_request": user_request,
            "capabilities": {}
        }
        
        # Discover relevant tools
        if self.tool_selector:
            try:
                selected_tools = await self.tool_selector.select_tools(user_request, max_tools=5)
                result["capabilities"]["tools"] = selected_tools
                print(f"  🔧 Tools: {selected_tools}")
            except Exception as e:
                print(f"  ❌ Tool discovery failed: {e}")
                result["capabilities"]["tools"] = []
        
        # Discover relevant prompts
        if self.prompt_selector:
            try:
                selected_prompts = await self.prompt_selector.select_prompts(user_request, max_prompts=3)
                result["capabilities"]["prompts"] = selected_prompts
                print(f"  📝 Prompts: {selected_prompts}")
            except Exception as e:
                print(f"  ❌ Prompt discovery failed: {e}")
                result["capabilities"]["prompts"] = []
        
        # Discover relevant resources
        if self.resource_selector:
            try:
                selected_resources = await self.resource_selector.select_resources(user_request, max_resources=3)
                result["capabilities"]["resources"] = selected_resources
                print(f"  📊 Resources: {selected_resources}")
            except Exception as e:
                print(f"  ❌ Resource discovery failed: {e}")
                result["capabilities"]["resources"] = []
        
        print(f"✅ Capability discovery completed")
        return result
    
    def get_server_info(self) -> Dict:
        """Get comprehensive server information"""
        return {
            "server_name": "Smart MCP Server",
            "ai_selectors": {
                "tool_selector": self.tool_selector is not None,
                "prompt_selector": self.prompt_selector is not None,
                "resource_selector": self.resource_selector is not None
            },
            "capabilities_count": {
                "tools": len(self.auto_discovery.discovered_tools),
                "prompts": len(self.auto_discovery.discovered_prompts), 
                "resources": len(self.auto_discovery.discovered_resources)
            },
            "features": [
                "AI-powered capability discovery",
                "Vector similarity matching",
                "Dynamic tool selection",
                "Smart prompt routing",
                "Intelligent resource discovery",
                "Security and monitoring integration"
            ]
        }
    
    async def get_selector_stats(self) -> Dict:
        """Get statistics from all AI selectors"""
        stats = {}
        
        if self.tool_selector:
            try:
                stats["tools"] = await self.tool_selector.get_stats()
            except Exception as e:
                stats["tools"] = {"error": str(e)}
        
        if self.prompt_selector:
            try:
                stats["prompts"] = await self.prompt_selector.get_stats()
            except Exception as e:
                stats["prompts"] = {"error": str(e)}
        
        if self.resource_selector:
            try:
                stats["resources"] = await self.resource_selector.get_stats()
            except Exception as e:
                stats["resources"] = {"error": str(e)}
        
        return stats

# Global server instance
smart_server: Optional[SmartMCPServer] = None

# API Endpoints
async def health_check(request):
    """Health check endpoint"""
    global smart_server
    server_info = smart_server.get_server_info() if smart_server else {}
    
    return JSONResponse({
        "status": "healthy",
        "service": "Smart MCP Server",
        "server_info": server_info
    })

async def discover_endpoint(request):
    """AI-powered capability discovery endpoint"""
    global smart_server
    
    try:
        body = await request.body()
        data = json.loads(body) if body else {}
        user_request = data.get("request", "")
        
        if not user_request:
            return JSONResponse({
                "status": "error", 
                "message": "No request provided"
            })
        
        if smart_server:
            result = await smart_server.discover_capabilities(user_request)
            return JSONResponse(result)
        else:
            return JSONResponse({
                "status": "error", 
                "message": "Server not ready"
            })
            
    except Exception as e:
        return JSONResponse({
            "status": "error", 
            "message": str(e)
        })

async def stats_endpoint(request):
    """AI selector statistics endpoint"""
    global smart_server
    
    try:
        if smart_server:
            server_info = smart_server.get_server_info()
            selector_stats = await smart_server.get_selector_stats()
            
            return JSONResponse({
                "status": "success",
                "server_info": server_info,
                "selector_stats": selector_stats
            })
        else:
            return JSONResponse({
                "status": "error",
                "message": "Server not ready"
            })
            
    except Exception as e:
        return JSONResponse({
            "status": "error", 
            "message": str(e)
        })

async def capabilities_endpoint(request):
    """List all available capabilities"""
    try:
        if smart_server:
            # Get tool information
            tools_info = {}
            if smart_server.tool_selector and hasattr(smart_server.tool_selector, 'tools_info'):
                tools_info = smart_server.tool_selector.tools_info
            
            # Get prompt information
            prompts_info = {}
            if smart_server.prompt_selector and hasattr(smart_server.prompt_selector, 'prompts_info'):
                prompts_info = smart_server.prompt_selector.prompts_info
            
            # Get resource information
            resources_info = {}
            if smart_server.resource_selector and hasattr(smart_server.resource_selector, 'resources_info'):
                resources_info = smart_server.resource_selector.resources_info
            
            return JSONResponse({
                "status": "success",
                "capabilities": {
                    "tools": {
                        "count": len(tools_info),
                        "available": list(tools_info.keys())
                    },
                    "prompts": {
                        "count": len(prompts_info),
                        "available": list(prompts_info.keys())
                    },
                    "resources": {
                        "count": len(resources_info),
                        "available": list(resources_info.keys())
                    }
                }
            })
        else:
            return JSONResponse({
                "status": "error",
                "message": "Server not ready"
            })
    except Exception as e:
        return JSONResponse({
            "status": "error", 
            "message": str(e)
        })

def add_endpoints(app: Starlette):
    """Add custom API endpoints"""
    routes = [
        Route("/health", health_check),
        Route("/discover", discover_endpoint, methods=["POST"]),
        Route("/stats", stats_endpoint),
        Route("/capabilities", capabilities_endpoint)
    ]
    
    for route in routes:
        app.router.routes.append(route)

async def run_server(port: int = 4321):
    """Run the Smart MCP Server"""
    global smart_server
    
    print("🧠 Smart MCP Server")
    print("=" * 50)
    print("🎯 Features:")
    print("   • AI-powered capability discovery")
    print("   • Vector similarity matching")  
    print("   • Dynamic tool selection")
    print("   • Smart prompt routing")
    print("   • Intelligent resource discovery")
    print("   • Security and monitoring integration")
    print()
    
    # Initialize server
    smart_server = SmartMCPServer()
    mcp = await smart_server.initialize()
    
    # Get ASGI application
    app = mcp.streamable_http_app()
    
    # Add custom endpoints
    add_endpoints(app)
    
    # Display server information
    server_info = smart_server.get_server_info()
    print(f"🌐 Server: {server_info['server_name']}")
    print(f"🧠 AI Selectors: {sum(server_info['ai_selectors'].values())}/3 active")
    print(f"📦 Capabilities: {sum(server_info['capabilities_count'].values())} modules")
    print()
    print(f"🎯 MCP endpoint: http://0.0.0.0:{port}/mcp/")
    print(f"🎯 API endpoints:")
    print(f"   • /health - Health check and server info")
    print(f"   • /discover (POST) - AI-powered capability discovery")
    print(f"   • /stats - AI selector statistics")
    print(f"   • /capabilities - List all available capabilities")
    print()
    
    # Start server
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Smart MCP Server with AI-powered capability discovery")
    parser.add_argument("--port", "-p", type=int, default=4321, help="Port to run server on")
    args = parser.parse_args()
    
    # Run server
    asyncio.run(run_server(args.port))

if __name__ == "__main__":
    main()