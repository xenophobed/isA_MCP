#!/usr/bin/env python3
"""
Smart MCP Server with AI-Powered Capability Discovery
Auto-discovery system for tools, prompts, and resources
"""

import argparse
import asyncio
import uvicorn
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.middleware import Middleware
from starlette.staticfiles import StaticFiles
import logging

# Core services
from core.security import initialize_security
from core.monitoring import monitor_manager
from core.auto_discovery import AutoDiscoverySystem

# AI selectors
from tools.core.tool_selector import ToolSelector
from prompts.prompt_selector import PromptSelector
from resources.resource_selector import ResourceSelector
from core.search_service import get_search_service

logger = logging.getLogger(__name__)

class SmartMCPServer:
    """Clean, AI-powered MCP server with automatic discovery"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.mcp = None
        self.tool_selector = None
        self.prompt_selector = None
        self.resource_selector = None
        self.search_service = None
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
        
        # Database tables are created via migrations, no init needed
        print("  ✅ Database ready (tables created via migrations)")
        
        print("✅ Core services ready")
    
    async def _register_all_capabilities(self):
        """Use auto-discovery system to register all capabilities"""
        print("📦 Auto-discovering and registering all capabilities...")
        
        # Use the auto-discovery system
        auto_discovery = AutoDiscoverySystem()
        await auto_discovery.auto_register_with_mcp(self.mcp)
        
        print("✅ Auto-discovery completed")
    
    async def _initialize_ai_selectors(self):
        """Initialize AI-powered capability selectors"""
        print("🧠 Initializing AI selectors...")
        
        # Tool selector with MCP server integration
        try:
            self.tool_selector = ToolSelector()
            # Initialize with MCP server to read actual registered tools
            await self.tool_selector.initialize_with_mcp(self.mcp)
            print("  ✅ Tool selector ready (connected to MCP)")
        except Exception as e:
            print(f"  ⚠️ Tool selector failed: {e}")
            self.tool_selector = None
        
        # Prompt selector with MCP server integration
        try:
            self.prompt_selector = PromptSelector()
            # Initialize with MCP server to read actual registered prompts
            await self.prompt_selector.initialize_with_mcp(self.mcp)
            print("  ✅ Prompt selector ready (connected to MCP)")
        except Exception as e:
            print(f"  ⚠️ Prompt selector failed: {e}")
            self.prompt_selector = None
        
        # Resource selector with MCP server integration
        try:
            self.resource_selector = ResourceSelector()
            # Initialize with MCP server to read actual registered resources
            await self.resource_selector.initialize_with_mcp(self.mcp)
            print("  ✅ Resource selector ready (connected to MCP)")
        except Exception as e:
            print(f"  ⚠️ Resource selector failed: {e}")
            self.resource_selector = None
        
        # Unified search service
        try:
            self.search_service = await get_search_service(self.mcp)
            print("  ✅ Unified search service ready (connected to MCP)")
        except Exception as e:
            print(f"  ⚠️ Search service failed: {e}")
            self.search_service = None
        
        print("✅ AI selectors initialized and connected to MCP server")
    
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
    
    async def get_server_info(self) -> Dict:
        """Get comprehensive server information"""
        # Get actual counts from MCP server
        tools_count = 0
        prompts_count = 0
        resources_count = 0
        
        if self.mcp:
            try:
                tools = await self.mcp.list_tools()
                prompts = await self.mcp.list_prompts()
                resources = await self.mcp.list_resources()
                
                tools_count = len(tools)
                prompts_count = len(prompts)
                resources_count = len(resources)
            except Exception as e:
                logger.error(f"Failed to get MCP capabilities count: {e}")
        
        return {
            "server_name": "Smart MCP Server",
            "ai_selectors": {
                "tool_selector": self.tool_selector is not None,
                "prompt_selector": self.prompt_selector is not None,
                "resource_selector": self.resource_selector is not None
            },
            "capabilities_count": {
                "tools": tools_count,
                "prompts": prompts_count,
                "resources": resources_count
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
    server_info = await smart_server.get_server_info() if smart_server else {}
    
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
            server_info = await smart_server.get_server_info()
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
        if smart_server and smart_server.mcp:
            # Get capabilities from the MCP server using proper API
            tools = await smart_server.mcp.list_tools()
            prompts = await smart_server.mcp.list_prompts()
            resources = await smart_server.mcp.list_resources()
            
            return JSONResponse({
                "status": "success",
                "capabilities": {
                    "tools": {
                        "count": len(tools),
                        "available": [tool.name for tool in tools]
                    },
                    "prompts": {
                        "count": len(prompts),
                        "available": [prompt.name for prompt in prompts]
                    },
                    "resources": {
                        "count": len(resources),
                        "available": [str(resource.uri) for resource in resources]
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

async def search_endpoint(request):
    """Unified search across tools, prompts, and resources"""
    try:
        body = await request.json()
        query = body.get("query", "")
        filters = body.get("filters", {})
        max_results = body.get("max_results", 10)
        user_id = body.get("user_id")
        
        if not query.strip():
            return JSONResponse({
                "status": "error",
                "message": "Query is required"
            })
        
        # Get the search service from the smart server instance
        if hasattr(smart_server, 'search_service') and smart_server.search_service:
            from core.search_service import SearchFilter
            
            # Convert filters to SearchFilter object
            search_filter = SearchFilter(
                types=filters.get("types"),
                categories=filters.get("categories"), 
                keywords=filters.get("keywords"),
                min_similarity=filters.get("min_similarity", 0.25)
            )
            
            # Perform search with user filtering
            results = await smart_server.search_service.search(query, search_filter, max_results, user_id)
            
            # Convert results to JSON-serializable format
            search_results = []
            for result in results:
                search_results.append({
                    "name": result.name,
                    "type": result.type,
                    "description": result.description,
                    "similarity_score": result.similarity_score,
                    "category": result.category,
                    "keywords": result.keywords,
                    "metadata": result.metadata
                })
            
            return JSONResponse({
                "status": "success",
                "query": query,
                "filters": filters,
                "user_id": user_id,
                "results": search_results,
                "result_count": len(search_results),
                "max_results": max_results
            })
        else:
            return JSONResponse({
                "status": "error",
                "message": "Search service not available"
            })
            
    except Exception as e:
        logger.error(f"Search endpoint error: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        })

# =================== PORTAL ENDPOINTS ===================
def get_supabase_client():
    """Get Supabase client for portal queries"""
    from core.database.supabase_client import get_supabase_client
    return get_supabase_client()

async def portal_root(request):
    """Serve the management portal index page"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return JSONResponse({
            "error": "Management portal not found",
            "message": "Static files not available"
        }, status_code=404)

async def portal_tools(request):
    """Get MCP tools from database for portal"""
    try:
        db = get_supabase_client()
        result = db.table('mcp_tools').select('*').eq('is_active', True).order('call_count', desc=True).execute()
        
        tools = []
        for row in result.data:
            tools.append({
                "name": row["name"],
                "description": row["description"] or "MCP tool",
                "category": row["category"] or "utility",
                "inputSchema": row["input_schema"] if row["input_schema"] else {},
                "callCount": row["call_count"] or 0,
                "avgResponseTime": row["avg_response_time"] or 0,
                "successRate": float(row["success_rate"]) if row["success_rate"] else 100.0,
                "lastUsed": row["last_used"] if row["last_used"] else None,
                "isActive": row["is_active"]
            })
        
        return JSONResponse({"tools": tools})
        
    except Exception as e:
        logger.error(f"Error fetching tools: {e}")
        return JSONResponse({"tools": [], "error": str(e)})

async def portal_prompts(request):
    """Get MCP prompts from database for portal"""
    try:
        db = get_supabase_client()
        result = db.table('mcp_prompts').select('*').eq('is_active', True).order('usage_count', desc=True).execute()
        
        prompts = []
        for row in result.data:
            prompts.append({
                "name": row["name"],
                "description": row["description"] or "MCP prompt",
                "category": row["category"] or "user",
                "arguments": row["arguments"] if row["arguments"] else [],
                "content": row["content"] or "",
                "usageCount": row["usage_count"] or 0,
                "lastModified": row["last_modified"] if row["last_modified"] else None,
                "isActive": row["is_active"]
            })
        
        return JSONResponse({"prompts": prompts})
        
    except Exception as e:
        logger.error(f"Error fetching prompts: {e}")
        return JSONResponse({"prompts": [], "error": str(e)})

async def portal_resources(request):
    """Get MCP resources from database for portal"""
    try:
        db = get_supabase_client()
        result = db.table('mcp_resources').select('*').eq('is_active', True).order('access_count', desc=True).execute()
        
        resources = []
        for row in result.data:
            resources.append({
                "uri": row["uri"],
                "name": row["name"],
                "description": row["description"] or "MCP resource",
                "type": row["resource_type"] or "other",
                "mimeType": row["mime_type"] or "application/octet-stream",
                "size": row["size_bytes"] or 0,
                "accessCount": row["access_count"] or 0,
                "lastAccessed": row["last_accessed"] if row["last_accessed"] else None,
                "isActive": row["is_active"]
            })
        
        return JSONResponse({"resources": resources})
        
    except Exception as e:
        logger.error(f"Error fetching resources: {e}")
        return JSONResponse({"resources": [], "error": str(e)})

async def portal_call_tool(request):
    """Call an MCP tool from portal and update usage stats"""
    global smart_server
    if smart_server and smart_server.mcp:
        try:
            data = await request.json()
            tool_name = data.get("name")
            arguments = data.get("arguments", {})
            
            # Record the tool call start time
            import time
            from datetime import datetime
            start_time = time.time()
            
            # Call the tool
            result = await smart_server.mcp.call_tool(tool_name, arguments)
            
            # Calculate response time
            response_time = int((time.time() - start_time) * 1000)  # Convert to ms
            
            # Update usage statistics in database
            try:
                db = get_supabase_client()
                
                # Get current tool stats
                current_tool = db.table('mcp_tools').select('call_count, avg_response_time').eq('name', tool_name).single().execute()
                
                if current_tool.data:
                    current_count = current_tool.data['call_count'] or 0
                    current_avg = current_tool.data['avg_response_time'] or 0
                    
                    # Calculate new average response time
                    new_avg = int((current_avg * current_count + response_time) / (current_count + 1)) if current_count > 0 else response_time
                    
                    # Update tool statistics
                    db.table('mcp_tools').update({
                        'call_count': current_count + 1,
                        'last_used': datetime.now().isoformat(),
                        'avg_response_time': new_avg
                    }).eq('name', tool_name).execute()
                    
            except Exception as e:
                logger.error(f"Failed to update tool stats: {e}")
            
            return JSONResponse({"result": result})
            
        except Exception as e:
            # Update error statistics if possible
            try:
                db = get_supabase_client()
                db.table('mcp_tools').update({
                    'last_used': datetime.now().isoformat()
                }).eq('name', data.get("name", "unknown")).execute()
            except:
                pass
            
            logger.error(f"Tool call failed: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({"error": "Server not available"}, status_code=503)

async def security_levels_endpoint(request):
    """Get security levels for all tools"""
    try:
        # Get the search service from the smart server instance
        if hasattr(smart_server, 'search_service') and smart_server.search_service:
            security_levels = await smart_server.search_service.get_tool_security_levels()
            
            return JSONResponse({
                "status": "success",
                "security_levels": security_levels,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return JSONResponse({
                "status": "error",
                "message": "Search service not available"
            }, status_code=503)
            
    except Exception as e:
        logger.error(f"Error in security levels endpoint: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

async def security_search_endpoint(request):
    """Search tools by security level"""
    try:
        body = await request.json()
        security_level = body.get("security_level", "").upper()
        max_results = body.get("max_results", 20)
        
        if not security_level:
            return JSONResponse({
                "status": "error",
                "message": "security_level is required (LOW, MEDIUM, HIGH, CRITICAL)"
            }, status_code=400)
            
        if security_level not in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'DEFAULT']:
            return JSONResponse({
                "status": "error", 
                "message": "Invalid security_level. Must be: LOW, MEDIUM, HIGH, CRITICAL, or DEFAULT"
            }, status_code=400)
        
        # Get the search service from the smart server instance
        if hasattr(smart_server, 'search_service') and smart_server.search_service:
            results = await smart_server.search_service.search_by_security_level(security_level, max_results)
            
            # Convert results to JSON-serializable format
            search_results = []
            for result in results:
                search_results.append({
                    "name": result.name,
                    "type": result.type,
                    "description": result.description,
                    "similarity_score": result.similarity_score,
                    "category": result.category,
                    "keywords": result.keywords,
                    "metadata": result.metadata
                })
            
            return JSONResponse({
                "status": "success",
                "security_level": security_level,
                "results": search_results,
                "result_count": len(search_results),
                "max_results": max_results,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return JSONResponse({
                "status": "error",
                "message": "Search service not available"
            }, status_code=503)
            
    except Exception as e:
        logger.error(f"Error in security search endpoint: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

def add_endpoints(app: Starlette):
    """Add custom API endpoints and management portal"""
    from core.secure_endpoints import add_auth_endpoints
    
    # Check if static directory exists
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    
    routes = [
        Route("/health", health_check),
        Route("/discover", discover_endpoint, methods=["POST"]),
        Route("/stats", stats_endpoint),
        Route("/capabilities", capabilities_endpoint),
        Route("/search", search_endpoint, methods=["POST"]),
        Route("/security/levels", security_levels_endpoint),
        Route("/security/search", security_search_endpoint, methods=["POST"]),
        # Admin API endpoints (separate from MCP endpoints)
        Route("/admin/tools", portal_tools),
        Route("/admin/prompts", portal_prompts),
        Route("/admin/resources", portal_resources),
        Route("/admin/call-tool", portal_call_tool, methods=["POST"]),
        # Portal root
        Route("/", portal_root),
        Route("/portal", portal_root),
        Route("/admin", portal_root),
    ]
    
    for route in routes:
        app.router.routes.append(route)
    
    # Mount static files if directory exists
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        print(f"  ✅ Management portal mounted at /static")
    else:
        print(f"  ⚠️ Static directory not found at {static_dir}")
    
    # 添加安全认证端点
    add_auth_endpoints(app)

async def run_server(port: int = 8081):
    """Run the Smart MCP Server"""
    global smart_server
    
    # Initialize server
    smart_server = SmartMCPServer()
    mcp = await smart_server.initialize()
    
    # Get ASGI application
    app = mcp.streamable_http_app()
    
    # Add optional authentication middleware
    from core.mcp_auth_middleware import add_mcp_auth_middleware
    add_mcp_auth_middleware(app, smart_server.config)
    
    # Add custom endpoints
    add_endpoints(app)
    
    # Display server information
    server_info = await smart_server.get_server_info()
    print(f"🌐 Server: {server_info['server_name']}")
    print(f"🧠 AI Selectors: {sum(server_info['ai_selectors'].values())}/3 active")
    print(f"📦 Capabilities: {sum(server_info['capabilities_count'].values())} modules")
    print()
    print(f"🎯 MCP endpoint: http://0.0.0.0:{port}/mcp/")
    print(f"🎯 Management Portal: http://0.0.0.0:{port}/")
    print(f"🎯 API endpoints:")
    print(f"   • /health - Health check and server info")
    print(f"   • /discover (POST) - AI-powered capability discovery")
    print(f"   • /stats - AI selector statistics")
    print(f"   • /capabilities - List all available capabilities")
    print(f"   • /search (POST) - Unified search across tools, prompts, and resources")
    print(f"   • /admin/tools - List MCP tools (admin)")
    print(f"   • /admin/prompts - List MCP prompts (admin)") 
    print(f"   • /admin/resources - List MCP resources (admin)")
    print(f"   • /admin/call-tool (POST) - Execute MCP tool (admin)")
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
    parser.add_argument("--port", "-p", type=int, default=8081, help="Port to run server on")
    args = parser.parse_args()
    
    # Run server
    asyncio.run(run_server(args.port))

if __name__ == "__main__":
    main()