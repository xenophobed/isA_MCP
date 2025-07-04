#!/usr/bin/env python3
"""
Real MCP Tool Call Testing
Tests actual tool execution via MCP JSON-RPC protocol
"""
import asyncio
import json
import aiohttp
import time
from typing import Dict, Any, List

async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """Call an MCP tool via JSON-RPC protocol"""
    if arguments is None:
        arguments = {}
    
    # MCP JSON-RPC call structure
    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time()),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "http://localhost:8081/mcp/",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            ) as response:
                if response.status == 200:
                    # Handle SSE response format
                    text = await response.text()
                    if "event: message" in text and "data: " in text:
                        # Extract JSON from SSE format - handle \r\n line endings
                        lines = text.replace('\r\n', '\n').strip().split('\n')
                        for line in lines:
                            if line.startswith("data: "):
                                json_data = line[6:]  # Remove "data: " prefix
                                try:
                                    result = json.loads(json_data)
                                    # Check if this is a successful tool call
                                    if "result" in result:
                                        tool_result = result["result"]
                                        if isinstance(tool_result, dict) and not tool_result.get("isError", False):
                                            return {"result": tool_result}
                                        elif isinstance(tool_result, dict) and tool_result.get("content"):
                                            # Extract the actual content
                                            content = tool_result["content"]
                                            if isinstance(content, list) and len(content) > 0:
                                                return {"result": {"content": content[0].get("text", "")}}
                                    return result
                                except json.JSONDecodeError:
                                    continue
                    else:
                        # Try parsing as regular JSON
                        try:
                            result = json.loads(text)
                            return result
                        except json.JSONDecodeError:
                            pass
                    
                    return {
                        "error": "Failed to parse SSE response",
                        "response_text": text[:500]
                    }
                else:
                    text = await response.text()
                    return {
                        "error": f"HTTP {response.status}",
                        "response_text": text[:500]  # Limit text length
                    }
    except asyncio.TimeoutError:
        return {"error": "Timeout after 30 seconds"}
    except Exception as e:
        return {"error": f"Exception: {str(e)}"}

async def test_critical_tools():
    """Test critical tools that use ISA client"""
    print("🧪 Testing real MCP tool calls...")
    
    # Define test cases for critical ISA client tools
    test_cases = [
        # Basic tools first
        {
            "name": "get_weather",
            "args": {"city": "New York"},
            "description": "Weather API call"
        },
        {
            "name": "remember", 
            "args": {"key": "test_key", "value": "test_value", "category": "testing"},
            "description": "Memory storage"
        },
        {
            "name": "search_memories",
            "args": {"query": "test"},
            "description": "Memory search"
        },
        
        # ISA Client critical tools
        {
            "name": "generate_image",
            "args": {"prompt": "a simple red circle", "width": 256, "height": 256},
            "description": "ISA Client - Image generation"
        },
        {
            "name": "search_rag_documents",
            "args": {"query": "machine learning", "collection": "default", "limit": 3},
            "description": "ISA Client - RAG search"
        },
        {
            "name": "generate_rag_embeddings",
            "args": {"texts": '["hello world", "machine learning"]', "model_name": "default"},
            "description": "ISA Client - Embeddings"
        },
        {
            "name": "quick_rag_question",
            "args": {"question": "What is machine learning?", "file_path": "test.txt"},
            "description": "ISA Client - RAG Q&A"
        },
        {
            "name": "data_query",
            "args": {"natural_query": "Get test value", "source_connection": "test"},
            "description": "ISA Client - Data query"
        },
        
        # Other tools
        {
            "name": "format_response",
            "args": {"content": "# Test Content\nThis is a test", "format": "markdown"},
            "description": "Response formatting"
        },
        {
            "name": "check_security_status",
            "args": {},
            "description": "Security status check"
        },
        {
            "name": "get_monitoring_metrics",
            "args": {},
            "description": "Monitoring metrics"
        },
        {
            "name": "list_background_tasks",
            "args": {},
            "description": "Background tasks list"
        }
    ]
    
    results = {}
    successful_calls = []
    failed_calls = []
    isa_client_tools = []
    
    print(f"Testing {len(test_cases)} critical tools...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        tool_name = test_case["name"]
        args = test_case["args"]
        description = test_case["description"]
        
        print(f"🔧 {i}/{len(test_cases)} Testing {tool_name} ({description})")
        
        # Call the tool
        result = await call_mcp_tool(tool_name, args)
        results[tool_name] = result
        
        # Analyze result
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
            failed_calls.append(tool_name)
        elif "result" in result:
            print(f"   ✅ Success!")
            successful_calls.append(tool_name)
            
            # Check if it's an ISA client tool
            if "ISA Client" in description:
                isa_client_tools.append(tool_name)
            
            # Show some result details
            tool_result = result.get("result", {})
            if isinstance(tool_result, dict):
                if "content" in tool_result:
                    content_preview = str(tool_result["content"])[:100]
                    print(f"      📝 Content: {content_preview}...")
                elif "status" in tool_result:
                    print(f"      📊 Status: {tool_result['status']}")
                elif "message" in tool_result:
                    message_preview = str(tool_result["message"])[:100]
                    print(f"      💬 Message: {message_preview}...")
                elif "data" in tool_result:
                    print(f"      📊 Data returned: {type(tool_result['data'])}")
            elif isinstance(tool_result, str):
                print(f"      📝 Response: {tool_result[:100]}...")
        else:
            print(f"   ⚠️ Unexpected response format")
            failed_calls.append(tool_name)
        
        print()  # Empty line for readability
    
    # Summary
    print("=" * 60)
    print("📊 Tool Call Test Summary:")
    print(f"   📋 Total tested: {len(test_cases)}")
    print(f"   ✅ Successful: {len(successful_calls)}")
    print(f"   ❌ Failed: {len(failed_calls)}")
    print(f"   🎯 ISA client tools working: {len(isa_client_tools)}")
    
    success_rate = (len(successful_calls) / len(test_cases)) * 100
    print(f"   📈 Success rate: {success_rate:.1f}%")
    
    if successful_calls:
        print(f"\n✅ Successful tool calls:")
        for tool in successful_calls:
            marker = "🎯" if tool in [t["name"] for t in test_cases if "ISA Client" in t["description"]] else "✓"
            print(f"   {marker} {tool}")
    
    if failed_calls:
        print(f"\n❌ Failed tool calls:")
        for tool in failed_calls:
            print(f"   ✗ {tool}")
    
    # ISA Client specific analysis
    isa_tools_in_tests = [t["name"] for t in test_cases if "ISA Client" in t["description"]]
    working_isa_tools = [t for t in isa_tools_in_tests if t in successful_calls]
    
    print(f"\n🎯 ISA Client Integration Analysis:")
    print(f"   📋 ISA tools tested: {len(isa_tools_in_tests)}")
    print(f"   ✅ ISA tools working: {len(working_isa_tools)}")
    
    if len(working_isa_tools) == len(isa_tools_in_tests):
        print("   🎉 All ISA client tools are working!")
    elif len(working_isa_tools) > 0:
        print("   ⚠️ Some ISA client tools need attention")
    else:
        print("   ❌ ISA client integration has issues")
    
    # Save detailed results
    test_summary = {
        "test_timestamp": time.time(),
        "total_tested": len(test_cases),
        "successful_calls": len(successful_calls),
        "failed_calls": len(failed_calls),
        "success_rate": success_rate,
        "successful_tools": successful_calls,
        "failed_tools": failed_calls,
        "isa_client_analysis": {
            "isa_tools_tested": isa_tools_in_tests,
            "isa_tools_working": working_isa_tools,
            "isa_success_rate": (len(working_isa_tools) / len(isa_tools_in_tests)) * 100 if isa_tools_in_tests else 0
        },
        "detailed_results": results
    }
    
    with open("tests/mcp/tool_call_results.json", "w") as f:
        json.dump(test_summary, f, indent=2)
    
    print(f"\n📁 Detailed results saved to tests/mcp/tool_call_results.json")
    
    return test_summary

async def test_extended_tools():
    """Test additional tools for comprehensive coverage"""
    print("\n🔬 Testing extended tool set...")
    
    extended_tests = [
        {
            "name": "add_rag_documents",
            "args": {
                "documents": [
                    {"content": "Test document about AI", "metadata": {"title": "AI Test"}}
                ]
            },
            "description": "ISA Client - RAG document addition"
        },
        {
            "name": "search_products",
            "args": {"query": "laptop", "category": "electronics", "max_results": 3},
            "description": "Product search"
        },
        {
            "name": "create_background_task",
            "args": {"task_type": "test_task", "parameters": {"test": "value"}},
            "description": "Background task creation"
        },
        {
            "name": "get_weather_cache_status",
            "args": {},
            "description": "Weather cache status"
        }
    ]
    
    extended_results = {}
    for test_case in extended_tests:
        tool_name = test_case["name"] 
        print(f"🔧 Testing {tool_name}...")
        
        result = await call_mcp_tool(tool_name, test_case["args"])
        extended_results[tool_name] = result
        
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
        elif "result" in result:
            print(f"   ✅ Success!")
        else:
            print(f"   ⚠️ Unexpected response")
    
    return extended_results

async def main():
    """Run comprehensive tool call testing"""
    print("🚀 Starting MCP Tool Call Testing")
    print("=" * 60)
    
    # Test critical tools
    critical_results = await test_critical_tools()
    
    # Test extended tools
    extended_results = await test_extended_tools()
    
    # Final summary
    total_success_rate = critical_results["success_rate"]
    isa_success_rate = critical_results["isa_client_analysis"]["isa_success_rate"]
    
    print(f"\n🎯 Final Assessment:")
    print(f"   Overall success rate: {total_success_rate:.1f}%")
    print(f"   ISA client success rate: {isa_success_rate:.1f}%")
    
    if total_success_rate >= 80 and isa_success_rate >= 80:
        print("   🎉 MCP server with ISA client integration is working excellently!")
    elif total_success_rate >= 60:
        print("   ✅ MCP server is working well with some tools needing attention")
    else:
        print("   ⚠️ MCP server needs significant attention")
    
    print(f"\n📊 All test results saved to tests/mcp/tool_call_results.json")

if __name__ == "__main__":
    asyncio.run(main())