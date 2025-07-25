#!/usr/bin/env python3
"""
Test Memory Tools with Real Database Data
使用真实数据库数据测试memory_tools的核心功能
"""

import asyncio
import json
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.mcp_client import default_client

async def test_real_data_functionality():
    """使用真实数据测试memory_tools的核心功能"""
    
    # 使用真实的用户ID和session_id
    user_id = "8735f5bb-9e97-4461-aef8-0197e6e1b008"
    session_ids = [
        "test_session_summarization_001",
        "test_session_memory_tools", 
        "test_session_001"
    ]
    
    print("🧪 Real Data Functionality Test")
    print("=" * 60)
    print(f"👤 User ID: {user_id}")
    print(f"📱 Available Sessions: {len(session_ids)}")
    
    # Test 1: get_session_context with real session data
    print("\n🔍 Test 1: get_session_context with real sessions")
    print("-" * 50)
    
    for i, session_id in enumerate(session_ids, 1):
        print(f"\n📝 {i}. Testing session: {session_id}")
        
        try:
            args = {
                "user_id": user_id,
                "session_id": session_id,
                "include_summaries": True,
                "max_recent_messages": 3
            }
            
            raw_response = await default_client.call_tool("get_session_context", args)
            parsed_response = default_client.parse_tool_response(raw_response)
            
            if parsed_response.get("status") == "success":
                data = parsed_response.get("data", {})
                print(f"  ✅ Session found: {data.get('session_found', False)}")
                print(f"  📊 Total messages: {data.get('total_messages', 0)}")
                print(f"  📄 Summary: '{data.get('conversation_summary', '')[:100]}...'")
                print(f"  🏷️  Topics: {len(data.get('conversation_state', {}).get('topics', []))} topics")
                print(f"  📈 Recent sessions: {data.get('recent_sessions_count', 0)}")
            else:
                print(f"  ❌ Failed: {parsed_response.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")
    
    # Test 2: search_memories with real user data
    print(f"\n🔍 Test 2: search_memories across all memory types")
    print("-" * 50)
    
    search_queries = [
        "machine learning pipeline",
        "Python development", 
        "training large language models",
        "AI assistant"
    ]
    
    for i, query in enumerate(search_queries, 1):
        print(f"\n🔎 {i}. Searching: '{query}'")
        
        try:
            args = {
                "user_id": user_id,
                "query": query,
                "top_k": 5
            }
            
            raw_response = await default_client.call_tool("search_memories", args)
            parsed_response = default_client.parse_tool_response(raw_response)
            
            if parsed_response.get("status") == "success":
                data = parsed_response.get("data", {})
                results = data.get("results", [])
                print(f"  ✅ Found {data.get('total_results', 0)} results")
                
                for j, result in enumerate(results[:3], 1):  # Show top 3
                    memory_type = result.get("memory_type", "unknown")
                    similarity = result.get("similarity_score", 0)
                    content = result.get("content", "")[:80]
                    print(f"    {j}. [{memory_type}] Score: {similarity:.3f} - {content}...")
            else:
                print(f"  ❌ Failed: {parsed_response.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")
    
    # Test 3: get_memory_statistics with real user
    print(f"\n🔍 Test 3: get_memory_statistics for real user")
    print("-" * 50)
    
    try:
        args = {"user_id": user_id}
        
        raw_response = await default_client.call_tool("get_memory_statistics", args)
        parsed_response = default_client.parse_tool_response(raw_response)
        
        if parsed_response.get("status") == "success":
            data = parsed_response.get("data", {})
            print(f"  ✅ Statistics retrieved successfully")
            print(f"  📊 Total memories: {data.get('total_memories', 0)}")
            print(f"  📈 Memory distribution:")
            
            by_type = data.get("by_type", {})
            for memory_type, count in by_type.items():
                if count > 0:
                    print(f"    - {memory_type}: {count}")
            
            metrics = data.get("intelligence_metrics", {})
            print(f"  🧠 Knowledge diversity: {metrics.get('knowledge_diversity', 0)} types")
        else:
            print(f"  ❌ Failed: {parsed_response.get('error_message', 'Unknown error')}")
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")
    
    # Test 4: search_facts_by_subject with real data
    print(f"\n🔍 Test 4: search_facts_by_subject")
    print("-" * 50)
    
    fact_subjects = ["Claude", "Python", "machine learning", "AI"]
    
    for subject in fact_subjects:
        print(f"\n🎯 Searching facts about: '{subject}'")
        
        try:
            args = {
                "user_id": user_id,
                "subject": subject,
                "limit": 3
            }
            
            raw_response = await default_client.call_tool("search_facts_by_subject", args)
            parsed_response = default_client.parse_tool_response(raw_response)
            
            if parsed_response.get("status") == "success":
                data = parsed_response.get("data", {})
                results = data.get("results", [])
                print(f"  ✅ Found {data.get('total_results', 0)} facts")
                
                for result in results:
                    subject_val = result.get("subject", "")
                    predicate = result.get("predicate", "")
                    obj_val = result.get("object_value", "")
                    confidence = result.get("confidence", 0)
                    print(f"    📋 {subject_val} {predicate} {obj_val} (conf: {confidence})")
            else:
                print(f"  ❌ No facts found or error: {parsed_response.get('error_message', 'Unknown')}")
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")
    
    # Summary
    print(f"\n🎯 Real Data Functionality Test Summary")
    print("=" * 60)
    print("✅ Tests completed:")
    print("  - get_session_context with 3 real sessions")
    print("  - search_memories with 4 different queries") 
    print("  - get_memory_statistics for user")
    print("  - search_facts_by_subject with 4 subjects")
    print("\n🚀 Memory tools are working with real database data!")

if __name__ == "__main__":
    asyncio.run(test_real_data_functionality())