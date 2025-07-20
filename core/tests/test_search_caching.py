#!/usr/bin/env python3
"""
Test search service caching and performance optimizations
"""

import asyncio
import sys
import os
import time

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
        """Get tools from capabilities endpoint"""
        capabilities = await self.client.get_capabilities()
        if capabilities.get("status") == "success":
            tools_data = capabilities.get("capabilities", {}).get("tools", {})
            tool_names = tools_data.get("available", [])
            
            # Create tool objects with names
            tools = []
            for name in tool_names:
                tool = type('Tool', (), {'name': name, 'description': f"Tool: {name}"})()
                tools.append(tool)
            return tools
        return []
        
    async def list_prompts(self):
        """Get prompts from capabilities endpoint"""
        capabilities = await self.client.get_capabilities()
        if capabilities.get("status") == "success":
            prompts_data = capabilities.get("capabilities", {}).get("prompts", {})
            prompt_names = prompts_data.get("available", [])
            
            # Create prompt objects with names
            prompts = []
            for name in prompt_names:
                prompt = type('Prompt', (), {'name': name, 'description': f"Prompt: {name}"})()
                prompts.append(prompt)
            return prompts
        return []
        
    async def list_resources(self):
        """Get resources from capabilities endpoint"""
        capabilities = await self.client.get_capabilities()
        if capabilities.get("status") == "success":
            resources_data = capabilities.get("capabilities", {}).get("resources", {})
            resource_uris = resources_data.get("available", [])
            
            # Create resource objects with URIs
            resources = []
            for uri in resource_uris:
                resource = type('Resource', (), {'uri': uri, 'description': f"Resource: {uri}"})()
                resources.append(resource)
            return resources
        return []

async def test_search_caching():
    """Test search caching performance"""
    print("🚀 Testing search service caching and performance...")
    
    try:
        # Initialize search service
        mcp_client = MCPClient()
        mcp_server = MCPServerAdapter(mcp_client)
        search_service = UnifiedSearchService()
        await search_service.initialize(mcp_server)
        
        # Test queries
        test_queries = [
            "memory storage information",
            "generate images and visuals", 
            "business strategy analysis",
            "web search automation"
        ]
        
        print("\n🔍 Testing cache performance with repeated queries...")
        
        for query in test_queries:
            print(f"\n📝 Query: '{query}'")
            
            # First search (cold cache)
            start_time = time.time()
            results1 = await search_service.search(query, max_results=5)
            first_time = (time.time() - start_time) * 1000
            print(f"   🆕 First search: {len(results1)} results in {first_time:.1f}ms")
            
            # Second search (warm cache)
            start_time = time.time()
            results2 = await search_service.search(query, max_results=5)
            second_time = (time.time() - start_time) * 1000
            print(f"   ⚡ Cached search: {len(results2)} results in {second_time:.1f}ms")
            
            # Calculate speedup
            if second_time > 0:
                speedup = first_time / second_time
                print(f"   📈 Speedup: {speedup:.1f}x faster")
        
        # Test cache statistics
        print("\n📊 Cache Statistics:")
        stats = search_service.get_cache_stats()
        
        search_cache = stats['search_results_cache']
        print(f"   🔍 Search Results Cache:")
        print(f"      Total entries: {search_cache['total_entries']}")
        print(f"      Fresh entries: {search_cache['fresh_entries']}")
        print(f"      Max size: {search_cache['max_size']}")
        
        embedding_cache = stats['query_embeddings_cache']
        print(f"   🧠 Query Embeddings Cache:")
        print(f"      Total entries: {embedding_cache['total_entries']}")
        print(f"      Fresh entries: {embedding_cache['fresh_entries']}")
        print(f"      Max size: {embedding_cache['max_size']}")
        
        print(f"   ⏰ Cache TTL: {stats['cache_ttl_seconds']} seconds")
        
        # Test cache clearing
        print("\n🧹 Testing cache clearing...")
        search_service.clear_caches()
        stats_after_clear = search_service.get_cache_stats()
        print(f"   Search cache entries after clear: {stats_after_clear['search_results_cache']['total_entries']}")
        print(f"   Embedding cache entries after clear: {stats_after_clear['query_embeddings_cache']['total_entries']}")
        
        print("\n✅ Caching tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Caching test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_concurrent_search():
    """Test concurrent search performance"""
    print("\n🏃‍♂️ Testing concurrent search performance...")
    
    try:
        # Initialize search service
        mcp_client = MCPClient()
        mcp_server = MCPServerAdapter(mcp_client)
        search_service = UnifiedSearchService()
        await search_service.initialize(mcp_server)
        
        # Concurrent queries
        queries = [
            "memory data storage",
            "image generation tools", 
            "business analysis prompts",
            "web automation scripts",
            "analytics and reporting"
        ]
        
        # Sequential execution
        print("🔄 Sequential execution:")
        start_time = time.time()
        sequential_results = []
        for query in queries:
            results = await search_service.search(query, max_results=3)
            sequential_results.append(len(results))
        sequential_time = (time.time() - start_time) * 1000
        print(f"   ⏱️ Total time: {sequential_time:.1f}ms")
        print(f"   📊 Results: {sequential_results}")
        
        # Concurrent execution
        print("\n🚀 Concurrent execution:")
        start_time = time.time()
        
        # Create concurrent tasks
        tasks = [search_service.search(query, max_results=3) for query in queries]
        concurrent_results_raw = await asyncio.gather(*tasks)
        concurrent_results = [len(results) for results in concurrent_results_raw]
        
        concurrent_time = (time.time() - start_time) * 1000
        print(f"   ⏱️ Total time: {concurrent_time:.1f}ms")
        print(f"   📊 Results: {concurrent_results}")
        
        # Calculate improvement
        if concurrent_time > 0:
            improvement = sequential_time / concurrent_time
            print(f"   📈 Concurrent speedup: {improvement:.1f}x faster")
        
        print("\n✅ Concurrent search tests completed!")
        
    except Exception as e:
        print(f"\n❌ Concurrent search test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all caching and performance tests"""
    print("🧪 Starting Search Service Caching and Performance Tests\n")
    print("🔔 Note: This test requires the MCP server to be running on localhost:8081")
    
    try:
        # Test server connection
        mcp_client = MCPClient()
        capabilities = await mcp_client.get_capabilities()
        
        if capabilities.get("status") != "success":
            print("❌ MCP server not available")
            print("💡 Start the server with: python smart_mcp_server.py")
            return
            
        await test_search_caching()
        await test_concurrent_search()
        
        print("\n🎉 All caching and performance tests completed successfully!")
        
    except Exception as e:
        print(f"\n💥 Tests failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())