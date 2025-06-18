#!/usr/bin/env python
"""
Multi-Port MCP Server Deployment
Run your MCP server on multiple ports for nginx load balancing
"""
import argparse
import asyncio
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

# Your existing imports
from core.logging import get_logger
from core.security import initialize_security
from core.monitoring import monitor_manager
from tools.memory_tools import register_memory_tools
from tools.weather_tools import register_weather_tools
from tools.admin_tools import register_admin_tools
from tools.client_interaction_tools import register_client_interaction_tools
from prompts.system_prompts import register_system_prompts
from resources.memory_resources import register_memory_resources
from resources.monitoring_resources import register_monitoring_resources
from resources.database_init import initialize_database

logger = get_logger(__name__)

async def health_check(request):
    """Health check endpoint for load balancer"""
    return JSONResponse({
        "status": "healthy",
        "service": "MCP Server",
        "timestamp": asyncio.get_event_loop().time()
    })

def create_mcp_server():
    """Create and configure MCP server instance"""
    mcp = FastMCP("Enhanced Secure MCP Server", stateless_http=True)
    
    # Initialize security manager
    security_manager = initialize_security(monitor_manager)
    
    # Register all components
    logger.info("Registering MCP components...")
    register_memory_tools(mcp)
    register_weather_tools(mcp)
    register_admin_tools(mcp)
    register_client_interaction_tools(mcp)
    register_system_prompts(mcp)
    register_memory_resources(mcp)
    register_monitoring_resources(mcp)
    
    return mcp

def add_health_endpoint(app: Starlette):
    """Add health check endpoint to Starlette app"""
    # Add health route to existing routes
    health_route = Route("/health", health_check)
    app.router.routes.append(health_route)

async def run_server(port: int):
    """Run MCP server on specified port"""
    print(f"🚀 Starting MCP Server on port {port}...")
    
    # Initialize database (do this once)
    initialize_database()
    
    # Create MCP server
    mcp = create_mcp_server()
    
    # Get the ASGI app for HTTP deployment
    app = mcp.streamable_http_app()
    
    # Add health endpoint to the Starlette app
    add_health_endpoint(app)
    
    # Run with uvicorn
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

def main():
    """Main function with port argument"""
    parser = argparse.ArgumentParser(description="Run MCP Server on specified port")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Port to run server on")
    args = parser.parse_args()
    
    print(f"✅ MCP Server starting on port {args.port}")
    print("🔐 Security Features: Authorization, Rate limiting, Audit logging")
    print("🎯 Available at: /mcp endpoint")
    
    # Run the server
    asyncio.run(run_server(args.port))

if __name__ == "__main__":
    main()