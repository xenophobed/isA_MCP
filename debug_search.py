#!/usr/bin/env python3
"""
Debug memory search functionality
"""

import asyncio
import json
import httpx

async def test_search():
    """Test memory search directly"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test simple search
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "query": "software engineer",
                    "limit": 5,
                    "similarity_threshold": 0.1
                }
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer mcp_vyL0yjEgrBP2q6YkuKDqU0wTAia1nkYJzpN_W_JB2jg"
        }
        
        print("Sending request...")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = await client.post(
            "http://localhost:8081/mcp/",
            json=payload,
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        try:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
        except:
            print(f"Raw response: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_search())