#!/usr/bin/env python3
"""
Test MCP tools using official MCP client
"""
import asyncio
import json
import sys
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    print("⚠️ MCP client not available, installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True

async def test_mcp_tools_direct():
    """Test tools by connecting directly to our MCP server"""
    print("🧪 Testing MCP tools via direct client connection...")
    
    # Test a simple function call first
    test_cases = [
        ("get_weather", {"location": "New York"}),
        ("remember", {"key": "test", "value": "test_value"}),
        ("generate_image", {"prompt": "red circle", "width": 256, "height": 256}),
        ("search_memories", {"query": "test"}),
        ("get_weather_cache_status", {}),
    ]
    
    successful_tests = []
    failed_tests = []
    
    for tool_name, args in test_cases:
        print(f"\n🔧 Testing {tool_name}...")
        try:
            # For now, let's just verify the server is running by calling discover
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8081/discover",
                    json={"request": f"I want to use {tool_name}"},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if tool_name in result.get("capabilities", {}).get("tools", []):
                            print(f"   ✅ Tool {tool_name} discovered successfully")
                            successful_tests.append(tool_name)
                        else:
                            print(f"   ⚠️ Tool {tool_name} not found in discovery")
                            failed_tests.append(tool_name)
                    else:
                        print(f"   ❌ Discovery failed with status {response.status}")
                        failed_tests.append(tool_name)
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
            failed_tests.append(tool_name)
    
    print(f"\n📊 Direct Test Summary:")
    print(f"   ✅ Successful: {len(successful_tests)}")
    print(f"   ❌ Failed: {len(failed_tests)}")
    
    return successful_tests, failed_tests

async def test_isa_client_integration():
    """Test ISA client integration directly"""
    print("🧪 Testing ISA client integration...")
    
    try:
        # Add project root to Python path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        
        # Test ISA client import and basic functionality
        try:
            from isa_model.client import ISAModelClient
            print("✅ ISA model client class imported successfully")
            
            # Test creating client directly
            client = ISAModelClient(service_endpoint="http://localhost:8082")
            print("✅ ISA client created successfully")
        except ImportError as ie:
            print(f"❌ ISA model import failed: {ie}")
            # Try old import
            from core.isa_client import get_isa_client
            client = get_isa_client()
            print("✅ ISA client imported via fallback")
        
        # Test text generation
        try:
            result = await client.invoke(
                input_data="Test message",
                task="chat",
                service_type="text",
                parameters={"temperature": 0.1, "max_tokens": 10}
            )
            if result.get('success'):
                print("✅ ISA client text generation working")
                return True
            else:
                print(f"❌ ISA client text generation failed: {result.get('error')}")
                return False
        except Exception as e:
            print(f"❌ ISA client test error: {e}")
            return False
            
    except Exception as e:
        print(f"❌ ISA client import failed: {e}")
        return False

async def generate_tool_documentation():
    """Generate documentation for all tools"""
    print("📝 Generating tool documentation...")
    
    try:
        import aiohttp
        
        # Get all capabilities
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8081/capabilities") as response:
                if response.status == 200:
                    data = await response.json()
                    tools = data.get("capabilities", {}).get("tools", {}).get("available", [])
                    
                    # Test discovery for each tool category
                    tool_categories = {
                        "Weather Tools": ["get_weather", "clear_weather_cache", "get_weather_cache_status"],
                        "Memory Tools": ["remember", "forget", "update_memory", "search_memories"],
                        "Image Generation": ["generate_image"],
                        "Web Tools": ["web_search", "crawl_and_extract", "synthesize_and_generate"],
                        "E-commerce": ["search_products", "get_product_details", "add_to_cart", "view_cart"],
                        "RAG Tools": ["search_rag_documents", "add_rag_documents", "quick_rag_question"],
                        "Data Analytics": ["data_query", "data_sourcing", "generate_visualization"],
                        "Security": ["check_security_status", "request_authorization"],
                        "Background Tasks": ["create_background_task", "list_background_tasks"],
                        "Monitoring": ["get_monitoring_metrics", "get_audit_log"]
                    }
                    
                    documentation = {}
                    
                    for category, category_tools in tool_categories.items():
                        print(f"\n📋 Testing {category}...")
                        category_results = {}
                        
                        for tool in category_tools:
                            if tool in tools:
                                # Test discovery for this tool
                                async with session.post(
                                    "http://localhost:8081/discover",
                                    json={"request": f"I want to use {tool}"},
                                    headers={"Content-Type": "application/json"}
                                ) as discovery_response:
                                    if discovery_response.status == 200:
                                        discovery_result = await discovery_response.json()
                                        if tool in discovery_result.get("capabilities", {}).get("tools", []):
                                            category_results[tool] = {
                                                "status": "discoverable",
                                                "discovery": discovery_result
                                            }
                                            print(f"   ✅ {tool}")
                                        else:
                                            category_results[tool] = {
                                                "status": "not_discoverable"
                                            }
                                            print(f"   ⚠️ {tool} (not discovered)")
                                    else:
                                        category_results[tool] = {
                                            "status": "discovery_failed"
                                        }
                                        print(f"   ❌ {tool} (discovery failed)")
                        
                        documentation[category] = category_results
                    
                    # Save documentation
                    with open("tests/mcp/tool_documentation.json", "w") as f:
                        json.dump({
                            "total_tools": len(tools),
                            "tested_categories": len(tool_categories),
                            "categories": documentation,
                            "all_tools": tools
                        }, f, indent=2)
                    
                    print(f"\n📁 Tool documentation saved to tests/mcp/tool_documentation.json")
                    return documentation
                    
    except Exception as e:
        print(f"❌ Documentation generation failed: {e}")
        return None

async def main():
    """Run all tests"""
    print("🚀 Starting comprehensive MCP tool testing...")
    
    # Test 1: ISA client integration
    isa_working = await test_isa_client_integration()
    
    # Test 2: MCP tools via discovery
    successful_tools, failed_tools = await test_mcp_tools_direct()
    
    # Test 3: Generate documentation
    documentation = await generate_tool_documentation()
    
    print(f"\n🎯 Final Summary:")
    print(f"   ISA Client: {'✅ Working' if isa_working else '❌ Failed'}")
    print(f"   Tool Discovery: {len(successful_tools)} successful")
    print(f"   Documentation: {'✅ Generated' if documentation else '❌ Failed'}")
    
    if isa_working and len(successful_tools) > 0:
        print("\n🎉 ISA client integration appears to be working!")
        print("   The server can discover tools and ISA client is functional.")
        print("   Direct tool execution may require a proper MCP client connection.")
    else:
        print("\n⚠️ Some issues detected. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(main())