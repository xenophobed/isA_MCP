#!/usr/bin/env python3
"""
Test working memory fix
"""

import asyncio
import sys
import os
import json

# Add the project root to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from tools.mcp_client import default_client

TEST_USER_ID = "8735f5bb-9e97-4461-aef8-0197e6e1b008"

async def test_working_memory():
    """Test the fixed get_active_working_memories"""
    
    print("🔧 Testing Working Memory Fix")
    print("=" * 40)
    
    try:
        raw_response = await default_client.call_tool("get_active_working_memories", {
            "user_id": TEST_USER_ID
        })
        parsed_response = default_client.parse_tool_response(raw_response)
        
        print(f"📋 Response: {json.dumps(parsed_response, indent=2)}")
        
        if parsed_response.get("status") == "success":
            print("✅ Working memory fix successful!")
            data = parsed_response.get("data", {})
            print(f"📊 Total results: {data.get('total_results', 0)}")
            
            results = data.get('results', [])
            for i, result in enumerate(results):
                print(f"  {i+1}. ID: {result.get('id', '')[:8]}...")
                print(f"     Content: {result.get('content', '')[:50]}...")
                print(f"     Context Type: {result.get('context_type', 'unknown')}")
                print(f"     Priority: {result.get('priority', 'unknown')}")
        else:
            print(f"❌ Still failing: {parsed_response.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"💥 Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_working_memory())