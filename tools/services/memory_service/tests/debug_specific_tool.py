#!/usr/bin/env python3
"""
Debug specific failing tool to get actual error
"""

import asyncio
import sys
import os
import json
import traceback

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.mcp_client import default_client

async def debug_store_episode():
    """Debug the failing store_episode tool"""
    print("🔍 Debugging store_episode tool...")
    print("="*50)
    
    user_id = "8735f5bb-9e97-4461-aef8-0197e6e1b008"
    
    episode_args = {
        "user_id": user_id,
        "event_type": "conference",
        "content": "Attended keynote on transformer architecture at AI Summit 2024",
        "location": "San Francisco Convention Center",
        "participants": "Dr. Sarah Chen, Prof. Michael Liu",
        "emotional_valence": 0.8
    }
    
    print(f"Arguments: {json.dumps(episode_args, indent=2)}")
    print()
    
    try:
        print("📞 Calling MCP tool...")
        raw_response = await default_client.call_tool("store_episode", episode_args)
        
        print("📥 Raw MCP Response:")
        print(json.dumps(raw_response, indent=2))
        print()
        
        print("📤 Parsed Response:")
        parsed_response = default_client.parse_tool_response(raw_response)
        print(json.dumps(parsed_response, indent=2))
        
        # Check if there's an error in the response content
        if 'result' in raw_response and 'content' in raw_response['result']:
            content = raw_response['result']['content']
            if isinstance(content, list) and len(content) > 0:
                text_content = content[0].get('text', '')
                if 'error' in text_content.lower():
                    print("\n🚨 Found error in response content:")
                    print(text_content)
        
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")
        print(f"Exception type: {type(e).__name__}")
        print("\n🔍 Full traceback:")
        traceback.print_exc()

async def debug_search_facts_by_type():
    """Debug the failing search_facts_by_type tool"""
    print("\n\n🔍 Debugging search_facts_by_type tool...")
    print("="*50)
    
    user_id = "8735f5bb-9e97-4461-aef8-0197e6e1b008"
    
    search_args = {
        "user_id": user_id,
        "fact_type": "technology",
        "limit": 5
    }
    
    print(f"Arguments: {json.dumps(search_args, indent=2)}")
    print()
    
    try:
        print("📞 Calling MCP tool...")
        raw_response = await default_client.call_tool("search_facts_by_type", search_args)
        
        print("📥 Raw MCP Response:")
        print(json.dumps(raw_response, indent=2))
        print()
        
        print("📤 Parsed Response:")
        parsed_response = default_client.parse_tool_response(raw_response)
        print(json.dumps(parsed_response, indent=2))
        
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")
        print(f"Exception type: {type(e).__name__}")
        print("\n🔍 Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_store_episode())
    asyncio.run(debug_search_facts_by_type())