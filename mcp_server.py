#!/usr/bin/env python
"""
Refactored Enhanced MCP Server with Modular Architecture
Organized with tools, prompts, and resources in separate modules
"""
from mcp.server.fastmcp import FastMCP

# Core components
from core.logging import get_logger
from core.security import initialize_security
from core.monitoring import monitor_manager

# Modular components
from tools.memory_tools import register_memory_tools
from tools.weather_tools import register_weather_tools
from tools.admin_tools import register_admin_tools
from tools.client_interaction_tools import register_client_interaction_tools
from prompts.system_prompts import register_system_prompts
from resources.memory_resources import register_memory_resources
from resources.monitoring_resources import register_monitoring_resources
from resources.database_init import initialize_database

logger = get_logger(__name__)

# Create MCP server
mcp = FastMCP("Enhanced Secure MCP Server")

# Initialize security manager with monitoring integration
security_manager = initialize_security(monitor_manager)

# Register all components
def register_all_components():
    """Register all tools, prompts, and resources"""
    logger.info("Registering MCP components...")
    
    # Register tools
    register_memory_tools(mcp)
    register_weather_tools(mcp)
    register_admin_tools(mcp)
    register_client_interaction_tools(mcp)
    
    # Register prompts
    register_system_prompts(mcp)
    
    # Register resources
    register_memory_resources(mcp)
    register_monitoring_resources(mcp)
    
    logger.info("All MCP components registered successfully")

# Security is now applied directly at the tool level during registration

async def cleanup():
    """Cleanup function"""
    logger.info("Cleaning up MCP server...")

def main():
    """Main server function"""
    print("🚀 Starting Refactored Enhanced MCP Server...")
    print("=" * 60)
    
    # Initialize database
    logger.info("Initializing database...")
    initialize_database()
    
    # Register all components (security is applied at tool level)
    register_all_components()
    
    print("✅ Refactored Enhanced MCP Server ready!")
    print("🏗️ Architecture:")
    print("  📁 Tools: Memory, Weather, Admin operations")
    print("  📝 Prompts: Security analysis, Memory organization, Monitoring")
    print("  📊 Resources: Memory data, Monitoring metrics, Health status")
    print("🔐 Security Features:")
    print("  - Authorization system for sensitive operations")
    print("  - Rate limiting and security pattern detection") 
    print("  - Comprehensive audit logging")
    print("  - Structured JSON responses")
    print("🎯 Available Tools:")
    print("  - remember* (Medium security)")
    print("  - forget* (High security)")
    print("  - update_memory* (Medium security)")
    print("  - search_memories (Low security)")
    print("  - get_weather (Low security)")
    print("  - get_authorization_requests* (Admin only)")
    print("  - approve_authorization* (Admin only)")
    print("  - get_monitoring_metrics* (Admin only)")
    print("  - get_audit_log* (Admin only)")
    print("  - ask_human (Client interaction)")
    print("  - request_authorization (Authorization workflow)")
    print("  - check_security_status (Security monitoring)")
    print("  - format_response (Response formatting)")
    print("📊 Available Resources:")
    print("  - memory://all")
    print("  - memory://category/{category}")
    print("  - weather://cache")
    print("  - monitoring://metrics")
    print("  - monitoring://health")
    print("  - monitoring://audit")
    print("📝 Available Prompts:")
    print("  - security_analysis_prompt")
    print("  - memory_organization_prompt")
    print("  - monitoring_report_prompt")
    print("  - user_assistance_prompt")
    print("* = Requires authorization/admin access")
    print("=" * 60)
    
    # Run the server
    logger.info("Starting MCP server with streamable HTTP transport...")
    mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()
