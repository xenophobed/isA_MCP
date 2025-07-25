#!/usr/bin/env python3
"""
Test Session Memory Summarization Functionality
测试session memory的自动总结功能
"""

import asyncio
import json
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.mcp_client import default_client

async def test_session_summarization():
    """测试session memory的自动总结功能"""
    user_id = "8735f5bb-9e97-4461-aef8-0197e6e1b008"
    session_id = "test_session_summarization_001"
    
    print("🧪 Session Memory Summarization Test")
    print("=" * 50)
    print(f"👤 User ID: {user_id}")
    print(f"📱 Session ID: {session_id}")
    
    # Step 1: Store a session message with rich content
    print("\n📝 Step 1: Storing session message with rich content...")
    store_args = {
        "user_id": user_id,
        "session_id": session_id,
        "message_content": "We discussed implementing a new machine learning pipeline for our recommendation system. The key requirements are: 1) Real-time inference with <100ms latency, 2) Support for both collaborative filtering and content-based approaches, 3) A/B testing framework integration, 4) Scalability to handle 1M+ users. We decided to use PyTorch for the models, Redis for caching, and Kubernetes for deployment. Next steps include setting up the development environment and creating the initial model prototypes.",
        "message_type": "human",
        "role": "user",
        "importance_score": 0.8
    }
    
    try:
        raw_response = await default_client.call_tool("store_session_message", store_args)
        parsed_response = default_client.parse_tool_response(raw_response)
        
        if parsed_response.get("status") == "success":
            print("  ✅ Session message stored successfully")
            memory_id = parsed_response.get("data", {}).get("memory_id")
            print(f"  🆔 Memory ID: {memory_id}")
        else:
            print(f"  ❌ Failed to store: {parsed_response.get('error_message', 'Unknown error')}")
            return
            
    except Exception as e:
        print(f"  ❌ Exception storing message: {e}")
        return
    
    # Step 2: Get session context (should show basic info without summary)
    print("\n📄 Step 2: Getting initial session context...")
    context_args = {
        "user_id": user_id,
        "session_id": session_id,
        "include_summaries": True,
        "max_recent_messages": 5
    }
    
    try:
        raw_response = await default_client.call_tool("get_session_context", context_args)
        parsed_response = default_client.parse_tool_response(raw_response)
        
        if parsed_response.get("status") == "success":
            data = parsed_response.get("data", {})
            print("  ✅ Session context retrieved")
            print(f"  📊 Total messages: {data.get('total_messages', 0)}")
            print(f"  📝 Current summary: '{data.get('conversation_summary', '(empty)')}'")
            print(f"  🏷️  Topics extracted: {data.get('conversation_state', {}).get('topics', [])}")
        else:
            print(f"  ❌ Failed to get context: {parsed_response.get('error_message', 'Unknown error')}")
            
    except Exception as e:
        print(f"  ❌ Exception getting context: {e}")
    
    # Step 3: Test automatic summarization
    print("\n🤖 Step 3: Testing automatic summarization...")
    
    # Test different compression levels
    compression_levels = ["brief", "medium", "detailed"]
    
    for level in compression_levels:
        print(f"\n  🔍 Testing '{level}' compression level...")
        
        # Use memory_service directly to test summarization
        try:
            from tools.services.memory_service.memory_service import memory_service
            
            result = await memory_service.summarize_session(
                user_id=user_id,
                session_id=session_id,
                force_update=True,
                compression_level=level
            )
            
            if result.success:
                print(f"    ✅ {level.capitalize()} summary generated")
                print(f"    📝 Summary: {result.data.get('summary', 'No summary')[:150]}...")
                print(f"    🎯 Confidence: {result.data.get('confidence', 'N/A')}")
            else:
                print(f"    ❌ Failed: {result.message}")
                
        except Exception as e:
            print(f"    ❌ Exception: {e}")
    
    # Step 4: Get final session context with summary
    print("\n📋 Step 4: Getting final session context with summary...")
    
    try:
        raw_response = await default_client.call_tool("get_session_context", context_args)
        parsed_response = default_client.parse_tool_response(raw_response)
        
        if parsed_response.get("status") == "success":
            data = parsed_response.get("data", {})
            print("  ✅ Final session context retrieved")
            print(f"  📝 Final summary: '{data.get('conversation_summary', '(empty)')[:200]}...'")
            print(f"  ⏰ Last summary at: {data.get('last_summary_at', 'Never')}")
            print(f"  📊 Messages since summary: {data.get('messages_since_last_summary', 0)}")
        else:
            print(f"  ❌ Failed to get final context: {parsed_response.get('error_message', 'Unknown error')}")
            
    except Exception as e:
        print(f"  ❌ Exception getting final context: {e}")
    
    # Summary
    print(f"\n🎯 Session Memory Summarization Test Complete")
    print("=" * 50)
    print("✅ Features tested:")
    print("  - Session message storage with topic extraction")
    print("  - Automatic session context retrieval")
    print("  - AI-powered summarization with multiple compression levels")
    print("  - Summary persistence and retrieval")

if __name__ == "__main__":
    asyncio.run(test_session_summarization())