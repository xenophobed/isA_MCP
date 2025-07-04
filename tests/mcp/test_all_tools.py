#!/usr/bin/env python3
"""
Comprehensive test for all MCP tools via /mcp/ endpoint
Tests ISA client integration by calling all 45 tools
"""
import asyncio
import json
import aiohttp
import sys
from typing import Dict, Any, List

async def test_tool_via_mcp(tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """Test a tool via MCP JSON-RPC protocol using /mcp/ endpoint"""
    if arguments is None:
        arguments = {}
    
    # MCP JSON-RPC call structure
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Use correct /mcp/ endpoint with proper headers
            async with session.post(
                "http://localhost:8081/mcp/",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    return {
                        "error": f"HTTP {response.status}",
                        "text": await response.text()
                    }
    except Exception as e:
        return {"error": str(e)}

async def get_all_tools() -> List[str]:
    """Get list of all available tools"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8081/capabilities") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("capabilities", {}).get("tools", {}).get("available", [])
                else:
                    print(f"Failed to get capabilities: {response.status}")
                    return []
    except Exception as e:
        print(f"Error getting tools: {e}")
        return []

async def test_all_tools():
    """Test all available tools with appropriate parameters"""
    print("🧪 Testing all MCP tools via /mcp/ endpoint...")
    
    # Get all available tools
    tools = await get_all_tools()
    print(f"Found {len(tools)} tools to test")
    
    # Comprehensive test cases for different tools
    test_cases = {
        # Weather tools
        "get_weather": {"location": "New York", "units": "metric"},
        "clear_weather_cache": {},
        "get_weather_cache_status": {},
        
        # Memory tools
        "remember": {"key": "test_key", "value": "test_value", "category": "testing"},
        "forget": {"key": "test_key"},
        "update_memory": {"key": "test_key", "value": "updated_value"},
        "search_memories": {"query": "test"},
        
        # Image generation (ISA client test)
        "generate_image": {"prompt": "a simple red circle on white background", "width": 512, "height": 512},
        
        # Web tools (ISA client tests)
        "web_search": {"query": "python programming tutorial", "max_results": 3},
        "crawl_and_extract": {
            "urls": "[\"https://httpbin.org/json\"]",
            "extraction_schema": "article",
            "max_urls": 1
        },
        "synthesize_and_generate": {
            "extracted_data": "[{\"title\": \"Test\", \"content\": \"Test content\"}]",
            "query": "test synthesis"
        },
        
        # E-commerce tools
        "search_products": {"query": "laptop", "category": "electronics", "max_results": 5},
        "get_product_details": {"product_id": "test123"},
        "add_to_cart": {"product_id": "test123", "quantity": 1},
        "view_cart": {},
        "get_user_info": {},
        "save_shipping_address": {
            "address": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "zip": "12345"
        },
        "start_checkout": {},
        "process_payment": {"payment_method": "test", "amount": 10.00},
        
        # Background task tools
        "create_background_task": {"task_type": "test", "parameters": {"test": "value"}},
        "list_background_tasks": {},
        "pause_background_task": {"task_id": "test123"},
        "resume_background_task": {"task_id": "test123"},
        "delete_background_task": {"task_id": "test123"},
        
        # Event sourcing
        "get_event_sourcing_status": {},
        
        # RAG tools (ISA client tests)
        "search_rag_documents": {"query": "test query", "collection": "default", "limit": 5},
        "add_rag_documents": {
            "documents": [
                {"content": "Test document content", "metadata": {"title": "Test"}}
            ]
        },
        "list_rag_collections": {},
        "get_rag_collection_stats": {"collection": "default"},
        "delete_rag_documents": {"collection": "default", "document_ids": ["test123"]},
        "generate_rag_embeddings": {"texts": ["test text"], "model_name": "default"},
        "quick_rag_question": {"question": "What is testing?", "collection": "default"},
        
        # Data analytics tools (ISA client tests)
        "data_sourcing": {"source_type": "test", "parameters": {"test": "value"}},
        "data_query": {
            "query": "SELECT 1 as test",
            "database": "test_db"
        },
        "generate_visualization": {
            "data": [{"x": 1, "y": 2}],
            "chart_type": "bar",
            "title": "Test Chart"
        },
        
        # Security and monitoring
        "get_authorization_requests": {},
        "approve_authorization": {"request_id": "test123"},
        "get_monitoring_metrics": {},
        "get_audit_log": {"limit": 10},
        "ask_human": {"question": "This is a test question for human approval"},
        "request_authorization": {"action": "test_action", "resource": "test_resource"},
        "check_security_status": {},
        
        # Utility tools
        "format_response": {"content": "test content", "format": "markdown"},
        
        # Autonomous task tools
        "plan_autonomous_task": {"task_description": "Test autonomous task"},
        "get_autonomous_status": {}
    }
    
    results = {}
    successful_tools = []
    failed_tools = []
    
    for i, tool in enumerate(tools, 1):
        print(f"\n🔧 Testing tool {i}/{len(tools)}: {tool}")
        
        # Get test arguments for this tool
        args = test_cases.get(tool, {})
        
        try:
            result = await test_tool_via_mcp(tool, args)
            results[tool] = result
            
            if "error" in result:
                print(f"   ❌ Error: {result['error']}")
                failed_tools.append(tool)
            elif "result" in result:
                print(f"   ✅ Success: Tool responded")
                successful_tools.append(tool)
                # Show first part of response for verification
                result_content = result.get("result", {})
                if isinstance(result_content, dict):
                    if "content" in result_content:
                        print(f"      📝 Content length: {len(str(result_content['content']))}")
                    elif "status" in result_content:
                        print(f"      📊 Status: {result_content['status']}")
                    elif "message" in result_content:
                        print(f"      💬 Message: {result_content['message'][:100]}...")
            else:
                print(f"   ⚠️ Unexpected response format")
                failed_tools.append(tool)
                
        except Exception as e:
            print(f"   💥 Exception: {e}")
            results[tool] = {"error": f"Exception: {e}"}
            failed_tools.append(tool)
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"   ✅ Successful: {len(successful_tools)}")
    print(f"   ❌ Failed: {len(failed_tools)}")
    print(f"   📈 Success Rate: {len(successful_tools)/len(tools)*100:.1f}%")
    
    if successful_tools:
        print(f"\n✅ Successful tools:")
        for tool in successful_tools[:10]:  # Show first 10
            print(f"   • {tool}")
        if len(successful_tools) > 10:
            print(f"   ... and {len(successful_tools)-10} more")
    
    if failed_tools:
        print(f"\n❌ Failed tools:")
        for tool in failed_tools[:10]:  # Show first 10
            print(f"   • {tool}")
        if len(failed_tools) > 10:
            print(f"   ... and {len(failed_tools)-10} more")
    
    # Save detailed results
    results_file = "tests/mcp/tool_test_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "summary": {
                "total_tools": len(tools),
                "successful": len(successful_tools),
                "failed": len(failed_tools),
                "success_rate": len(successful_tools)/len(tools)*100,
                "successful_tools": successful_tools,
                "failed_tools": failed_tools
            },
            "detailed_results": results
        }, f, indent=2)
    print(f"   📁 Detailed results saved to {results_file}")
    
    return results, successful_tools, failed_tools

if __name__ == "__main__":
    asyncio.run(test_all_tools())