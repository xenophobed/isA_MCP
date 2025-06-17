#!/usr/bin/env python
"""
Enhanced MCP Server with Authorization, Security, and Monitoring
Refactored into modular components
"""
import logging

# Core components (imported in tool modules as needed)
from resources.database.sqlite.memory import init_database, add_sample_data

# Security
from core.security import SecurityLevel, AuthorizationResult, AuthorizationRequest, SecurityPolicy, AuthorizationManager


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