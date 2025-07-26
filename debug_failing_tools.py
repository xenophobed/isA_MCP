#!/usr/bin/env python3
"""
Debug failing memory tools to understand specific errors
"""

import asyncio
import sys
import os
import json
import traceback

# Add the project root to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from tools.mcp_client import default_client

TEST_USER_ID = "8735f5bb-9e97-4461-aef8-0197e6e1b008"

async def debug_tool(tool_name, args):
    """Debug a specific tool with detailed error reporting"""
    print(f"\n{'='*50}")
    print(f"🔍 DEBUGGING: {tool_name}")
    print(f"{'='*50}")
    print(f"📝 Args: {json.dumps(args, indent=2)}")
    
    try:
        print("📡 Calling tool...")
        raw_response = await default_client.call_tool(tool_name, args)
        print(f"📥 Raw response type: {type(raw_response)}")
        print(f"📥 Raw response: {raw_response}")
        
        print("🔍 Parsing response...")
        parsed_response = default_client.parse_tool_response(raw_response)
        print(f"📋 Parsed response: {json.dumps(parsed_response, indent=2)}")
        
        status = parsed_response.get("status")
        if status == "success":
            print("✅ SUCCESS!")
        else:
            print(f"❌ FAILED - Status: {status}")
            error_msg = parsed_response.get("error_message")
            if error_msg:
                print(f"💥 Error message: {error_msg}")
        
        return parsed_response
        
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")
        print(f"📋 Exception type: {type(e)}")
        print(f"📋 Traceback:")
        traceback.print_exc()
        return {"status": "exception", "error": str(e)}

async def main():
    """Debug the failing tools"""
    
    print("🔧 MEMORY TOOLS DEBUGGING SESSION")
    print("Investigating failing tools from comprehensive test")
    
    # Debug the 3 failing tools
    
    # 1. store_factual_memory
    await debug_tool(
        "store_factual_memory",
        {
            "user_id": TEST_USER_ID,
            "dialog_content": "Claude is an AI assistant created by Anthropic.",
            "importance_score": 0.8
        }
    )
    
    # 2. store_semantic_memory
    await debug_tool(
        "store_semantic_memory",
        {
            "user_id": TEST_USER_ID,
            "dialog_content": "Machine learning is a subset of artificial intelligence.",
            "importance_score": 0.9
        }
    )
    
    # 3. get_active_working_memories
    await debug_tool(
        "get_active_working_memories",
        {
            "user_id": TEST_USER_ID
        }
    )
    
    print(f"\n{'='*50}")
    print("🏁 DEBUG SESSION COMPLETE")
    print(f"{'='*50}")

if __name__ == "__main__":
    asyncio.run(main())