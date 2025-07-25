#!/usr/bin/env python3
"""
Debug remaining Unknown error tools
"""

import asyncio
import sys
import os
import json

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.mcp_client import default_client

async def debug_remaining_tools():
    """Debug tools still showing Unknown error"""
    user_id = "8735f5bb-9e97-4461-aef8-0197e6e1b008"
    
    print("🔍 Debugging remaining tools with 'Unknown error'...")
    print("="*60)
    
    # Debug search_concepts_by_category
    print("\n🔧 Debugging search_concepts_by_category...")
    args = {
        "user_id": user_id,
        "category": "AI/ML",
        "limit": 5
    }
    
    try:
        raw_response = await default_client.call_tool("search_concepts_by_category", args)
        parsed_response = default_client.parse_tool_response(raw_response)
        print(f"Raw: {json.dumps(raw_response, indent=2)}")
        print(f"Parsed: {json.dumps(parsed_response, indent=2)}")
    except Exception as e:
        print(f"Exception: {e}")
    
    # Debug get_session_context  
    print("\n🔧 Debugging get_session_context...")
    args = {
        "user_id": user_id,
        "session_id": "test_session_memory_tools",
        "include_summaries": True,
        "max_recent_messages": 5
    }
    
    try:
        raw_response = await default_client.call_tool("get_session_context", args)
        parsed_response = default_client.parse_tool_response(raw_response)
        print(f"Raw: {json.dumps(raw_response, indent=2)}")
        print(f"Parsed: {json.dumps(parsed_response, indent=2)}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(debug_remaining_tools())