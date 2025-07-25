#!/usr/bin/env python3
"""
Test Memory Tools - Simple Version
测试重写后的memory_tools.py与memory_service的完全兼容性
"""

import asyncio
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.mcp_client import default_client

async def test_memory_tools_simple():
    """测试重写后的memory_tools的核心功能"""
    user_id = "8735f5bb-9e97-4461-aef8-0197e6e1b008"
    
    print("🧪 Memory Tools Simple Test")
    print("=" * 50)
    print(f"👤 User ID: {user_id}")
    
    # Test core storage functions that exist in memory_service
    test_cases = [
        {
            "tool": "store_factual_memory",
            "args": {
                "user_id": user_id,
                "dialog_content": "Claude is an AI assistant created by Anthropic.",
                "importance_score": 0.8
            }
        },
        {
            "tool": "store_semantic_memory", 
            "args": {
                "user_id": user_id,
                "dialog_content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.",
                "importance_score": 0.7
            }
        },
        {
            "tool": "search_memories",
            "args": {
                "user_id": user_id,
                "query": "AI assistant",
                "top_k": 5
            }
        },
        {
            "tool": "search_facts_by_subject",
            "args": {
                "user_id": user_id,
                "subject": "Claude",
                "limit": 5
            }
        },
        {
            "tool": "get_memory_statistics",
            "args": {
                "user_id": user_id
            }
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        tool_name = test_case["tool"]
        args = test_case["args"]
        
        print(f"\n📝 Test {i}: {tool_name}")
        try:
            raw_response = await default_client.call_tool(tool_name, args)
            parsed_response = default_client.parse_tool_response(raw_response)
            
            success = parsed_response.get("status") == "success"
            results.append({"tool": tool_name, "success": success})
            
            status_emoji = "✅" if success else "❌"
            print(f"  {status_emoji} Status: {parsed_response.get('status')}")
            
            if success:
                data = parsed_response.get("data", {})
                if "total_results" in data:
                    print(f"  📊 Results: {data['total_results']}")
                elif "memory_id" in data:
                    print(f"  🆔 Memory ID: {data['memory_id'][:8]}...")
                elif "total_memories" in data:
                    print(f"  📈 Total memories: {data['total_memories']}")
            else:
                error_msg = parsed_response.get("error_message", "Unknown error")
                print(f"  💥 Error: {error_msg}")
                
        except Exception as e:
            results.append({"tool": tool_name, "success": False})
            print(f"  ❌ Exception: {e}")
    
    # Summary
    print(f"\n📊 Test Summary:")
    print("=" * 50)
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Memory tools are fully compatible with memory_service.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        for result in results:
            if not result["success"]:
                print(f"  ❌ {result['tool']}")

if __name__ == "__main__":
    asyncio.run(test_memory_tools_simple())