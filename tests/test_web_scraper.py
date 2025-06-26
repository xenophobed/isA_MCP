#!/usr/bin/env python3
"""
Test Web Scraper Tools Integration with Smart Server
"""
import asyncio
import json
from smart_server import SmartMCPServer

async def test_web_scraper_integration():
    """Test web scraper tools integration"""
    print("🧪 Testing Web Scraper Tools Integration...")
    
    # Create smart server
    smart_server = SmartMCPServer()
    await smart_server.initialize()
    
    # Test 1: Check if web tools are loaded
    status = smart_server.get_status()
    print(f"✅ Loaded tools: {status['loaded_tools']}")
    assert 'web' in status['loaded_tools'], "Web tools not loaded!"
    
    # Test 2: AI tool selection for web scraping request
    print("\n🔍 Testing AI tool selection for web scraping...")
    result = await smart_server.analyze_and_load_tools("scrape example.com website")
    print(f"AI recommended tools: {result['recommended_tools']}")
    
    # Verify web scraping tools are recommended
    web_tools = [tool for tool in result['recommended_tools'] if 'scrape' in tool]
    assert len(web_tools) > 0, "No web scraping tools recommended!"
    print(f"✅ Web scraping tools recommended: {web_tools}")
    
    # Test 3: Check available web scraper tools
    print("\n📋 Checking available web scraper tools...")
    mcp = smart_server.mcp
    tools = await mcp.list_tools()
    web_scraper_tools = [tool.name for tool in tools if any(keyword in tool.name for keyword in ['scrape', 'extract', 'search_page'])]
    print(f"Available web scraper tools: {web_scraper_tools}")
    
    expected_tools = ['scrape_webpage', 'scrape_multiple_pages', 'extract_page_links', 'search_page_content', 'get_scraper_status', 'cleanup_scraper_resources']
    for expected_tool in expected_tools:
        assert expected_tool in web_scraper_tools, f"Missing tool: {expected_tool}"
    
    print(f"✅ All {len(expected_tools)} web scraper tools are available!")
    
    # Test 4: Verify tool metadata
    print("\n📝 Checking tool metadata...")
    scrape_tool = next((tool for tool in tools if tool.name == 'scrape_webpage'), None)
    assert scrape_tool is not None, "scrape_webpage tool not found!"
    
    # Check if docstring contains keywords and category
    docstring = scrape_tool.description or ""
    assert 'Keywords:' in docstring, "Tool missing keywords metadata"
    assert 'Category: web' in docstring, "Tool missing web category"
    print("✅ Tool metadata includes keywords and category")
    
    print("\n🎉 All tests passed! Web scraper tools are successfully integrated!")
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_web_scraper_integration())
        print(f"\n✅ Integration test completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()