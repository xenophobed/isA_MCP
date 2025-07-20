#!/usr/bin/env python3
"""
Test file for the unified search service
Tests search across tools, prompts, and resources using the existing capabilities system
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
            
            # Create tool objects with names (descriptions would need separate API calls)
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

async def test_server_connection():
    """Test connection to MCP server"""
    print("🌐 Testing MCP server connection...")
    
    try:
        mcp_client = MCPClient()
        capabilities = await mcp_client.get_capabilities()
        
        if capabilities.get("status") == "success":
            caps = capabilities.get("capabilities", {})
            tools_count = caps.get("tools", {}).get("count", 0)
            prompts_count = caps.get("prompts", {}).get("count", 0) 
            resources_count = caps.get("resources", {}).get("count", 0)
            
            print(f"  ✅ Server running: {tools_count} tools, {prompts_count} prompts, {resources_count} resources")
            return mcp_client
        else:
            print(f"  ❌ Server error: {capabilities}")
            return None
            
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        print("  💡 Make sure the MCP server is running on localhost:8081")
        return None

async def test_initialization():
    """Test search service initialization with real MCP server"""
    print("\n🚀 Testing search service initialization...")
    
    # Test server connection first
    mcp_client = await test_server_connection()
    if not mcp_client:
        print("  ⏭️ Skipping tests - server not available")
        return None
    
    # Create adapter and search service
    mcp_server = MCPServerAdapter(mcp_client)
    search_service = UnifiedSearchService()
    
    await search_service.initialize(mcp_server)
    
    # Check if capabilities were loaded
    tools_count = len(search_service.capabilities_cache['tools'])
    prompts_count = len(search_service.capabilities_cache['prompts'])
    resources_count = len(search_service.capabilities_cache['resources'])
    
    print(f"  ✅ Initialized search service: {tools_count} tools, {prompts_count} prompts, {resources_count} resources")
    
    return search_service

async def test_capabilities_summary():
    """Test getting capabilities summary"""
    print("\n📊 Testing capabilities summary...")
    
    search_service = await test_initialization()
    if not search_service:
        return
    
    summary = await search_service.get_capabilities_summary()
    
    for item_type, info in summary.items():
        print(f"  📂 {item_type}: {info['total']} items")
        for category, count in info['categories'].items():
            print(f"    - {category}: {count}")

async def test_similarity_search():
    """Test similarity-based search"""
    print("\n🧠 Testing similarity search...")
    
    search_service = UnifiedSearchService()
    await search_service.initialize(MockMCPServer())
    
    test_queries = [
        "I need to store information about users",
        "Create marketing content for business",
        "Generate beautiful images and visuals",
        "Search for information online",
        "Get product data from ecommerce store",
        "Check the weather forecast",
        "Analyze data and statistics",
        "Write creative stories",
        "Scientific research and analysis",
        "System administration tasks"
    ]
    
    for query in test_queries:
        try:
            results = await search_service.search(query, max_results=3)
            print(f"  🔍 '{query}':")
            for result in results:
                print(f"    - {result.name} ({result.type}) - {result.similarity_score:.3f}")
        except Exception as e:
            print(f"    ❌ Error: {e}")

async def test_category_search():
    """Test searching by category"""
    print("\n📂 Testing category search...")
    
    search_service = UnifiedSearchService()
    await search_service.initialize(MockMCPServer())
    
    # Test different categories
    categories = ["memory", "vision", "web", "ecommerce", "custom", "business_commerce", "creative_artistic"]
    
    for category in categories:
        results = await search_service.search_by_category(category)
        print(f"  📁 Category '{category}': {len(results)} items")
        for result in results[:3]:  # Show top 3
            print(f"    - {result.name} ({result.type})")

async def test_keyword_search():
    """Test searching by keywords"""
    print("\n🔍 Testing keyword search...")
    
    search_service = UnifiedSearchService()
    await search_service.initialize(MockMCPServer())
    
    test_keywords = [
        ["memory", "store"],
        ["image", "generate"],
        ["business", "strategy"],
        ["weather", "forecast"],
        ["data", "analysis"],
        ["creative", "story"],
        ["research", "science"],
        ["ecommerce", "product"]
    ]
    
    for keywords in test_keywords:
        results = await search_service.search_by_keywords(keywords)
        print(f"  🏷️ Keywords {keywords}: {len(results)} items")
        for result in results[:2]:  # Show top 2
            print(f"    - {result.name} ({result.type})")

async def test_filtered_search():
    """Test search with filters"""
    print("\n🎯 Testing filtered search...")
    
    search_service = UnifiedSearchService()
    await search_service.initialize(MockMCPServer())
    
    # Test type-specific search
    filters = SearchFilter(types=['tool'])
    results = await search_service.search("generate images", filters)
    print(f"  🔧 Tools only: {len(results)} results")
    
    filters = SearchFilter(types=['prompt'])
    results = await search_service.search("business strategy", filters)
    print(f"  💬 Prompts only: {len(results)} results")
    
    filters = SearchFilter(types=['resource'])
    results = await search_service.search("memory data", filters)
    print(f"  📦 Resources only: {len(results)} results")
    
    # Test category + type filter
    filters = SearchFilter(types=['prompt'], categories=['business_commerce'])
    results = await search_service.search("", filters)
    print(f"  💼 Business prompts: {len(results)} results")
    
    # Test keyword + similarity filter
    filters = SearchFilter(keywords=['memory'], min_similarity=0.5)
    results = await search_service.search("store information", filters)
    print(f"  🧠 High similarity memory items: {len(results)} results")

async def test_omni_prompts_discovery():
    """Test that omni prompts are properly discovered and categorized"""
    print("\n🌟 Testing omni prompts discovery...")
    
    search_service = UnifiedSearchService()
    await search_service.initialize(MockMCPServer())
    
    # Look for omni categories
    omni_categories = [
        "custom", "business_commerce", "education_learning", "technology_innovation",
        "marketing_media", "health_wellness", "lifestyle_personal", "professional_career",
        "news_current_events", "creative_artistic", "science_research"
    ]
    
    for category in omni_categories:
        results = await search_service.search_by_category(category, "prompt")
        if results:
            print(f"  ⚡ {category}: {len(results)} prompts")
            for result in results:
                print(f"    - {result.name}")

async def test_cross_type_search():
    """Test search across all types simultaneously"""
    print("\n🔄 Testing cross-type search...")
    
    search_service = UnifiedSearchService()
    await search_service.initialize(MockMCPServer())
    
    # Search for "memory" across all types
    results = await search_service.search("memory", max_results=10)
    
    print(f"  🔍 Search 'memory' across all types: {len(results)} results")
    
    # Group by type
    by_type = {}
    for result in results:
        if result.type not in by_type:
            by_type[result.type] = []
        by_type[result.type].append(result)
    
    for item_type, items in by_type.items():
        print(f"    {item_type}: {len(items)} items")
        for item in items[:2]:
            print(f"      - {item.name} (score: {item.similarity_score:.3f})")

async def test_search_performance():
    """Test search performance with various query sizes"""
    print("\n⚡ Testing search performance...")
    
    search_service = UnifiedSearchService()
    await search_service.initialize(MockMCPServer())
    
    import time
    
    queries = [
        "memory",
        "business strategy analysis",
        "generate creative content for marketing campaigns",
        "comprehensive data analysis using statistical methods and machine learning algorithms"
    ]
    
    for query in queries:
        start_time = time.time()
        results = await search_service.search(query)
        end_time = time.time()
        
        print(f"  📈 Query length {len(query.split())}: {len(results)} results in {(end_time-start_time)*1000:.1f}ms")

async def get_test_search_service():
    """Get initialized search service for tests"""
    mcp_client = MCPClient()
    try:
        capabilities = await mcp_client.get_capabilities()
        if capabilities.get("status") != "success":
            return None
    except:
        return None
        
    mcp_server = MCPServerAdapter(mcp_client)
    search_service = UnifiedSearchService()
    await search_service.initialize(mcp_server)
    return search_service

async def main():
    """Run all tests"""
    print("🧪 Starting Unified Search Service Tests\n")
    print("🔔 Note: This test requires the MCP server to be running on localhost:8081")
    print("   Start the server with: python smart_mcp_server.py\n")
    
    try:
        # Test initialization first
        search_service = await test_initialization()
        if not search_service:
            print("\n⚠️ Tests skipped - MCP server not available")
            print("💡 To run tests:")
            print("   1. Start the MCP server: python smart_mcp_server.py")  
            print("   2. Wait for 'Server running on http://localhost:8081'")
            print("   3. Run this test again")
            return
            
        await test_capabilities_summary()
        
        # The rest require the search service to be initialized
        print("\n🔍 Running search tests with real MCP data...")
        
        # Update these tests to use the initialized search service
        await test_similarity_search_real(search_service)
        await test_category_search_real(search_service) 
        await test_keyword_search_real(search_service)
        await test_filtered_search_real(search_service)
        await test_omni_prompts_discovery_real(search_service)
        await test_cross_type_search_real(search_service)
        await test_search_performance_real(search_service)
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

# Updated test functions that use real search service
async def test_similarity_search_real(search_service):
    """Test similarity-based search with real data"""
    print("\n🧠 Testing similarity search with real MCP data...")
    
    test_queries = [
        "I need to store information about users",
        "Create marketing content for business", 
        "Generate beautiful images and visuals",
        "Search for information online",
        "Get product data from ecommerce store"
    ]
    
    for query in test_queries:
        try:
            results = await search_service.search(query, max_results=3)
            print(f"  🔍 '{query}': {len(results)} results")
            for result in results:
                print(f"    - {result.name} ({result.type}) - {result.similarity_score:.3f}")
        except Exception as e:
            print(f"    ❌ Error: {e}")

async def test_category_search_real(search_service):
    """Test searching by category with real data"""
    print("\n📂 Testing category search with real data...")
    
    summary = await search_service.get_capabilities_summary()
    
    for item_type, info in summary.items():
        print(f"  📁 {item_type} categories:")
        for category in list(info['categories'].keys())[:3]:  # Show top 3 categories
            results = await search_service.search_by_category(category)
            print(f"    - {category}: {len(results)} items")

async def test_keyword_search_real(search_service):
    """Test searching by keywords with real data"""
    print("\n🔍 Testing keyword search with real data...")
    
    test_keywords = [
        ["memory", "store"],
        ["image", "generate"], 
        ["business", "strategy"],
        ["data", "analysis"]
    ]
    
    for keywords in test_keywords:
        results = await search_service.search_by_keywords(keywords)
        print(f"  🏷️ Keywords {keywords}: {len(results)} items")

async def test_filtered_search_real(search_service):
    """Test search with filters using real data"""
    print("\n🎯 Testing filtered search with real data...")
    
    # Test type-specific search
    filters = SearchFilter(types=['tool'])
    results = await search_service.search("generate", filters)
    print(f"  🔧 Tools only: {len(results)} results")
    
    filters = SearchFilter(types=['prompt'])  
    results = await search_service.search("business", filters)
    print(f"  💬 Prompts only: {len(results)} results")
    
    filters = SearchFilter(types=['resource'])
    results = await search_service.search("memory", filters)
    print(f"  📦 Resources only: {len(results)} results")

async def test_omni_prompts_discovery_real(search_service):
    """Test that omni prompts are discovered in real data"""
    print("\n🌟 Testing omni prompts discovery with real data...")
    
    # Look for business prompts specifically
    filters = SearchFilter(types=['prompt'], categories=['business_commerce'])
    results = await search_service.search("", filters, max_results=10)
    
    print(f"  💼 Business commerce prompts found: {len(results)}")
    for result in results:
        print(f"    - {result.name}")

async def test_cross_type_search_real(search_service):
    """Test search across all types with real data"""
    print("\n🔄 Testing cross-type search with real data...")
    
    results = await search_service.search("memory", max_results=10)
    
    # Group by type
    by_type = {}
    for result in results:
        if result.type not in by_type:
            by_type[result.type] = []
        by_type[result.type].append(result)
    
    print(f"  🔍 Search 'memory' found: {len(results)} total results")
    for item_type, items in by_type.items():
        print(f"    {item_type}: {len(items)} items")

async def test_search_performance_real(search_service):
    """Test search performance with real data"""
    print("\n⚡ Testing search performance with real data...")
    
    import time
    
    queries = ["memory", "business analysis", "generate creative content"]
    
    for query in queries:
        start_time = time.time()
        results = await search_service.search(query)
        end_time = time.time()
        
        print(f"  📈 '{query}': {len(results)} results in {(end_time-start_time)*1000:.1f}ms")

if __name__ == "__main__":
    asyncio.run(main())