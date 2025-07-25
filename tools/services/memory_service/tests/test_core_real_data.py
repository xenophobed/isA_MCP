#!/usr/bin/env python3
"""
Test Core Memory Tools with Real Data
测试核心memory_tools功能与真实数据
"""

import asyncio
import json
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.mcp_client import default_client

async def test_core_real_data():
    """测试核心功能与真实数据"""
    
    user_id = "8735f5bb-9e97-4461-aef8-0197e6e1b008"
    session_id = "test_session_summarization_001"  # 已知存在的session
    
    print("🧪 Core Real Data Test")
    print("=" * 40)
    print(f"👤 User: {user_id}")
    print(f"📱 Session: {session_id}")
    
    # Test 1: get_session_context
    print(f"\n🔍 Test 1: get_session_context")
    try:
        args = {
            "user_id": user_id,
            "session_id": session_id,
            "include_summaries": True,
            "max_recent_messages": 2
        }
        
        raw_response = await default_client.call_tool("get_session_context", args)
        parsed_response = default_client.parse_tool_response(raw_response)
        
        if parsed_response.get("status") == "success":
            data = parsed_response.get("data", {})
            print(f"  ✅ Session found: {data.get('session_found')}")
            print(f"  📊 Total messages: {data.get('total_messages')}")
            summary = data.get('conversation_summary', '')
            print(f"  📄 Has summary: {len(summary) > 0} ({len(summary)} chars)")
            topics = data.get('conversation_state', {}).get('topics', [])
            print(f"  🏷️  Topics: {len(topics)} extracted")
        else:
            print(f"  ❌ Failed: {parsed_response.get('error_message')}")
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")
    
    # Test 2: search_memories (simple query)
    print(f"\n🔍 Test 2: search_memories")
    try:
        args = {
            "user_id": user_id,
            "query": "machine learning",
            "top_k": 3
        }
        
        raw_response = await default_client.call_tool("search_memories", args)
        parsed_response = default_client.parse_tool_response(raw_response)
        
        if parsed_response.get("status") == "success":
            data = parsed_response.get("data", {})
            total = data.get("total_results", 0)
            print(f"  ✅ Found {total} results")
            
            if total > 0:
                results = data.get("results", [])
                for i, result in enumerate(results[:2], 1):
                    mem_type = result.get("memory_type", "unknown")
                    score = result.get("similarity_score", 0)
                    print(f"    {i}. [{mem_type}] Score: {score:.3f}")
        else:
            print(f"  ❌ Failed: {parsed_response.get('error_message')}")
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")
    
    # Test 3: get_memory_statistics
    print(f"\n🔍 Test 3: get_memory_statistics")
    try:
        args = {"user_id": user_id}
        
        raw_response = await default_client.call_tool("get_memory_statistics", args)
        parsed_response = default_client.parse_tool_response(raw_response)
        
        if parsed_response.get("status") == "success":
            data = parsed_response.get("data", {})
            total = data.get("total_memories", 0)
            print(f"  ✅ Total memories: {total}")
            
            by_type = data.get("by_type", {})
            active_types = {k: v for k, v in by_type.items() if v > 0}
            print(f"  📈 Active types: {len(active_types)}")
        else:
            print(f"  ❌ Failed: {parsed_response.get('error_message')}")
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")
    
    print(f"\n🎯 Core functionality test complete!")

if __name__ == "__main__":
    asyncio.run(test_core_real_data())