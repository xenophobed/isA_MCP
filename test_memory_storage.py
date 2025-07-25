#!/usr/bin/env python3
"""
Test memory storage directly
"""

import asyncio
import json
import httpx

async def test_memory_storage():
    """Test memory storage and check database directly"""
    
    user_id = "550e8400-e29b-41d4-a716-446655440000"
    
    print("🔍 Testing Memory Storage Directly")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer mcp_vyL0yjEgrBP2q6YkuKDqU0wTAia1nkYJzpN_W_JB2jg"
        }
        
        # Test 1: Store factual memory
        print("1. Testing factual memory storage...")
        factual_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "store_factual_memory_from_dialog",
                "arguments": {
                    "user_id": user_id,
                    "dialog_content": "Hello, I'm John Smith. I'm a software engineer at Google working on AI systems. I love Python programming and machine learning.",
                    "importance_score": 0.8
                }
            }
        }
        
        response = await client.post("http://localhost:8081/mcp/", json=factual_payload, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            # Parse SSE response
            content = response.text
            if "data:" in content:
                data_line = [line for line in content.split('\n') if line.startswith('data:')][0]
                data = json.loads(data_line[5:])  # Remove "data:" prefix
                result = data.get('result', {})
                if result.get('content'):
                    result_text = result['content'][0]['text']
                    result_json = json.loads(result_text)
                    print(f"   Result: {result_json.get('status')} - {result_json.get('message', '')[:100]}")
        
        # Wait a bit for processing
        await asyncio.sleep(2)
        
        # Test 2: Store episodic memory  
        print("\n2. Testing episodic memory storage...")
        episodic_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "store_episodic_memory_from_dialog",
                "arguments": {
                    "user_id": user_id,
                    "dialog_content": "Yesterday I had an amazing team meeting where we discussed the new AI project. Sarah presented brilliant ideas about neural networks, and Mike suggested using transformers. The meeting lasted 2 hours and everyone was excited.",
                    "importance_score": 0.7
                }
            }
        }
        
        response = await client.post("http://localhost:8081/mcp/", json=episodic_payload, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            content = response.text
            if "data:" in content:
                data_line = [line for line in content.split('\n') if line.startswith('data:')][0]
                data = json.loads(data_line[5:])
                result = data.get('result', {})
                if result.get('content'):
                    result_text = result['content'][0]['text']
                    result_json = json.loads(result_text)
                    print(f"   Result: {result_json.get('status')} - {result_json.get('message', '')[:100]}")
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Test 3: Check what's actually in the database
        print("\n3. Checking database after storage...")
        
        from core.database.supabase_client import get_supabase_client
        db = get_supabase_client()
        
        # Check factual memories
        factual_result = db.table('factual_memories').select('*').eq('user_id', user_id).execute()
        print(f"   factual_memories: {len(factual_result.data)} records")
        for record in factual_result.data:
            print(f"     Subject: {record.get('subject', 'N/A')}")
            print(f"     Predicate: {record.get('predicate', 'N/A')}")  
            print(f"     Object: {record.get('object_value', 'N/A')[:50]}...")
            
        # Check episodic memories
        episodic_result = db.table('episodic_memories').select('*').eq('user_id', user_id).execute()
        print(f"   episodic_memories: {len(episodic_result.data)} records")
        for record in episodic_result.data:
            print(f"     Title: {record.get('episode_title', 'N/A')}")
            print(f"     Summary: {record.get('summary', 'N/A')[:50]}...")
        
        # Test 4: Now test search after storage
        print("\n4. Testing search after storage...")
        search_payload = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "user_id": user_id,
                    "query": "software engineer Google",
                    "limit": 5,
                    "similarity_threshold": 0.1
                }
            }
        }
        
        response = await client.post("http://localhost:8081/mcp/", json=search_payload, headers=headers)
        print(f"   Search status: {response.status_code}")
        if response.status_code == 200:
            content = response.text
            if "data:" in content:
                data_line = [line for line in content.split('\n') if line.startswith('data:')][0]
                data = json.loads(data_line[5:])
                result = data.get('result', {})
                if result.get('content'):
                    result_text = result['content'][0]['text']
                    result_json = json.loads(result_text)
                    print(f"   Search results: {result_json.get('data', {}).get('count', 0)} found")

if __name__ == "__main__":
    asyncio.run(test_memory_storage())