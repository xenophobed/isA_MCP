#!/usr/bin/env python3
"""
Test search service monitoring and metrics
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.search_service import UnifiedSearchService, SearchFilter
from tools.mcp_client import MCPClient
from core.logging import get_logger

logger = get_logger(__name__)

class MCPServerAdapter:
    """Adapter to make MCPClient compatible with our search service"""
    
    def __init__(self, mcp_client: MCPClient):
        self.client = mcp_client
        
    async def list_tools(self):
        capabilities = await self.client.get_capabilities()
        if capabilities.get("status") == "success":
            tools_data = capabilities.get("capabilities", {}).get("tools", {})
            tool_names = tools_data.get("available", [])
            
            tools = []
            for name in tool_names:
                tool = type('Tool', (), {'name': name, 'description': f"Tool: {name}"})()
                tools.append(tool)
            return tools
        return []
        
    async def list_prompts(self):
        capabilities = await self.client.get_capabilities()
        if capabilities.get("status") == "success":
            prompts_data = capabilities.get("capabilities", {}).get("prompts", {})
            prompt_names = prompts_data.get("available", [])
            
            prompts = []
            for name in prompt_names:
                prompt = type('Prompt', (), {'name': name, 'description': f"Prompt: {name}"})()
                prompts.append(prompt)
            return prompts
        return []
        
    async def list_resources(self):
        capabilities = await self.client.get_capabilities()
        if capabilities.get("status") == "success":
            resources_data = capabilities.get("capabilities", {}).get("resources", {})
            resource_uris = resources_data.get("available", [])
            
            resources = []
            for uri in resource_uris:
                resource = type('Resource', (), {'uri': uri, 'description': f"Resource: {uri}"})()
                resources.append(resource)
            return resources
        return []

async def test_monitoring_metrics():
    """Test monitoring and metrics collection"""
    print("📊 Testing search service monitoring...")
    
    try:
        # Initialize search service
        mcp_client = MCPClient()
        mcp_server = MCPServerAdapter(mcp_client)
        search_service = UnifiedSearchService()
        await search_service.initialize(mcp_server)
        
        # Reset metrics to start fresh
        search_service.reset_monitoring_metrics()
        
        # Perform several searches
        test_queries = [
            "memory storage",
            "image generation", 
            "business analysis",
            "web automation",
            "data analytics"
        ]
        
        print("🔍 Performing test searches...")
        for i, query in enumerate(test_queries):
            results = await search_service.search(query, max_results=3)
            print(f"   Search {i+1}: '{query}' -> {len(results)} results")
        
        # Get monitoring metrics
        print("\n📈 Monitoring Metrics:")
        metrics = search_service.get_monitoring_metrics()
        
        # Display main metrics
        main_metrics = metrics.get('metrics', {})
        print(f"   Total searches: {main_metrics.get('total_searches', 0)}")
        print(f"   Successful searches: {main_metrics.get('successful_searches', 0)}")
        print(f"   Failed searches: {main_metrics.get('failed_searches', 0)}")
        print(f"   Cached searches: {main_metrics.get('cached_searches', 0)}")
        print(f"   Fallback searches: {main_metrics.get('fallback_searches', 0)}")
        print(f"   Success rate: {main_metrics.get('success_rate', 0):.1%}")
        print(f"   Cache hit rate: {main_metrics.get('cache_hit_rate', 0):.1%}")
        print(f"   Average response time: {main_metrics.get('avg_response_time_ms', 0):.1f}ms")
        print(f"   Average results per search: {main_metrics.get('avg_results_per_search', 0):.1f}")
        
        # Display recent performance
        recent_5min = metrics.get('recent_5min', {})
        print(f"\n⏰ Recent Performance (5 min):")
        print(f"   Searches: {recent_5min.get('total_searches', 0)}")
        print(f"   Avg response time: {recent_5min.get('avg_response_time_ms', 0):.1f}ms")
        print(f"   Success rate: {recent_5min.get('success_rate', 0):.1%}")
        print(f"   Searches per minute: {recent_5min.get('searches_per_minute', 0):.1f}")
        
        # Display health status
        health = metrics.get('health', {})
        print(f"\n🏥 Health Status: {health.get('status', 'unknown')}")
        
        health_checks = health.get('checks', {})
        for check_name, check_data in health_checks.items():
            status = check_data.get('status', 'unknown')
            value = check_data.get('value', 0)
            print(f"   {check_name}: {status} (value: {value})")
        
        print("\n✅ Monitoring test completed!")
        
    except Exception as e:
        print(f"\n❌ Monitoring test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_health_checks():
    """Test health check functionality"""
    print("\n🏥 Testing health check functionality...")
    
    try:
        # Initialize search service
        mcp_client = MCPClient()
        mcp_server = MCPServerAdapter(mcp_client)
        search_service = UnifiedSearchService()
        await search_service.initialize(mcp_server)
        
        # Get initial health status
        health_status = search_service.get_health_status()
        print(f"   Health status: {health_status.get('status', 'unknown')}")
        
        checks = health_status.get('checks', {})
        for check_name, check_info in checks.items():
            status = check_info.get('status', 'unknown')
            value = check_info.get('value', 'N/A')
            threshold = check_info.get('threshold', 'N/A')
            message = check_info.get('message', '')
            
            print(f"   {check_name}:")
            print(f"     Status: {status}")
            print(f"     Value: {value}")
            print(f"     Threshold: {threshold}")
            if message:
                print(f"     Message: {message}")
        
        print("\n✅ Health check test completed!")
        
    except Exception as e:
        print(f"\n❌ Health check test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all monitoring tests"""
    print("🧪 Starting Search Service Monitoring Tests\n")
    print("🔔 Note: This test requires the MCP server to be running on localhost:8081")
    
    try:
        # Test server connection
        mcp_client = MCPClient()
        capabilities = await mcp_client.get_capabilities()
        
        if capabilities.get("status") != "success":
            print("❌ MCP server not available")
            print("💡 Start the server with: python smart_mcp_server.py")
            return
            
        await test_monitoring_metrics()
        await test_health_checks()
        
        print("\n🎉 All monitoring tests completed successfully!")
        
    except Exception as e:
        print(f"\n💥 Tests failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())