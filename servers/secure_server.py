#!/usr/bin/env python
"""
Enhanced MCP Server with Authorization, Security, and Monitoring
Refactored into modular components
"""
import logging

# Core components (imported in tool modules as needed)
from resources.database.sqlite.memory import init_database, add_sample_data

# Tools
from tools.memory_tools import remember, forget, search_memories, get_all_memories
from tools.weather_tools import get_weather
from tools.admin_tools import (
    get_authorization_requests, approve_authorization, 
    get_monitoring_metrics, get_audit_log, get_metrics_resource
)

# MCP imports
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("Enhanced Secure MCP Server")

# =====================
# REGISTER TOOLS
# =====================

@mcp.tool()
async def remember_tool(key: str, value: str, category: str = "general", importance: int = 1, user_id: str = "default") -> str:
    """Store information in long-term memory with authorization"""
    return await remember(key, value, category, importance, user_id)

@mcp.tool()
async def forget_tool(key: str, user_id: str = "default") -> str:
    """Remove information from memory with high security authorization"""
    return await forget(key, user_id)

@mcp.tool()
async def search_memories_tool(query: str, category = None, min_importance: int = 1, user_id: str = "default") -> str:
    """Search through memories with security checks"""
    return await search_memories(query, category, min_importance, user_id)

@mcp.tool()
async def get_weather_tool(city: str, user_id: str = "default") -> str:
    """Get weather information with caching and monitoring"""
    return await get_weather(city, user_id)

@mcp.tool()
async def get_authorization_requests_tool(user_id: str = "admin") -> str:
    """Get pending authorization requests (admin only)"""
    return await get_authorization_requests(user_id)

@mcp.tool()
async def approve_authorization_tool(request_id: str, approved_by: str = "admin") -> str:
    """Approve an authorization request"""
    return await approve_authorization(request_id, approved_by)

@mcp.tool()
async def get_monitoring_metrics_tool(user_id: str = "admin") -> str:
    """Get system monitoring metrics"""
    return await get_monitoring_metrics(user_id)

@mcp.tool()
async def get_audit_log_tool(limit: int = 50, user_id: str = "admin") -> str:
    """Get audit log entries"""
    return await get_audit_log(limit, user_id)

# =====================
# REGISTER RESOURCES
# =====================

@mcp.resource("memory://all")
async def get_all_memories_resource() -> str:
    """Get all memories with monitoring"""
    return await get_all_memories()

@mcp.resource("monitoring://metrics")
async def get_metrics_resource_handler() -> str:
    """Get monitoring metrics as resource"""
    return await get_metrics_resource()

def main():
    """Main server function with enhanced security"""
    print("Starting Enhanced Secure MCP Server...")
    
    # Initialize database
    init_database()
    add_sample_data()
    
    print("Enhanced Secure MCP Server ready!")
    print("Security Features:")
    print("  - Authorization system for sensitive operations")
    print("  - Rate limiting and security pattern detection") 
    print("  - Comprehensive audit logging")
    print("  - Structured JSON responses")
    print("Tools: remember*, forget*, search_memories, get_weather, monitoring tools")
    print("Resources: memory://all, monitoring://metrics")
    print("* = Requires authorization")
    
    # Run the server
    mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()