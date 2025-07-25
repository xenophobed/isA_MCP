#!/usr/bin/env python3
"""
Debug memory search step by step
"""

import asyncio
import json
import os
from tools.services.memory_service.memory_service import memory_service
from tools.services.memory_service.models import MemorySearchQuery, MemoryType

async def debug_memory_search():
    """Debug memory search step by step"""
    
    user_id = "550e8400-e29b-41d4-a716-446655440000"
    query_text = "software engineer"
    
    print("🔍 DEBUG: Memory Search Step by Step")
    print("=" * 50)
    
    try:
        # 1. Check if memories exist in database
        print("1. Checking database for stored memories...")
        
        # Direct database check
        from core.database.supabase_client import get_supabase_client
        db = get_supabase_client()
        
        # Check each memory type with correct content fields
        memory_content_fields = {
            "factual_memories": "object_value",
            "episodic_memories": "summary", 
            "semantic_memories": "definition",
            "procedural_memories": "expected_outcome",
            "working_memories": "current_step",
            "session_memories": "conversation_summary"
        }
        
        for memory_type, content_field in memory_content_fields.items():
            result = db.table(memory_type).select(f"id, user_id, {content_field}").eq("user_id", user_id).execute()
            print(f"   {memory_type}: {len(result.data)} records")
            if result.data:
                for item in result.data[:2]:  # Show first 2 records
                    content = item.get(content_field, "No content")
                    print(f"     - ID: {item['id']}")
                    print(f"       Content: {content[:100] if content else 'Empty'}...")
        
        print("\n2. Testing embedding generation...")
        
        # Test embedding generation for our query
        from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator
        embedder = EmbeddingGenerator()
        
        query_embedding = await embedder.embed_single(query_text)
        print(f"   Query '{query_text}' embedding: {len(query_embedding)} dimensions")
        
        # Test similarity with a known memory content  
        test_content = "Bob, a software engineer at Microsoft. I specialize in distributed systems"
        similarity = await embedder.compute_similarity(query_text, test_content)
        print(f"   Similarity with test content: {similarity:.3f}")
        
        print("\n3. Testing memory search query...")
        
        # Create search query
        search_query = MemorySearchQuery(
            query=query_text,
            user_id=user_id,
            memory_types=[MemoryType.FACTUAL, MemoryType.EPISODIC],
            top_k=5,
            similarity_threshold=0.1  # Very low threshold
        )
        
        print(f"   Query: {search_query.query}")
        print(f"   User ID: {search_query.user_id}")
        print(f"   Memory types: {[t.value for t in search_query.memory_types]}")
        print(f"   Threshold: {search_query.similarity_threshold}")
        
        # Execute search
        print("\n4. Executing memory search...")
        results = await memory_service.search_memories(search_query)
        
        print(f"   Found {len(results)} results")
        
        if results:
            print("\n   Results:")
            for i, result in enumerate(results):
                print(f"     {i+1}. Type: {result.memory.memory_type}")
                print(f"        Content: {result.memory.content[:100]}...")
                print(f"        Similarity: {result.similarity_score:.3f}")
                print(f"        Rank: {result.rank}")
        else:
            print("   ❌ No results found!")
            
            # Let's debug why no results
            print("\n5. Debugging why no results...")
            
            # Check each engine individually
            for memory_type in [MemoryType.FACTUAL, MemoryType.EPISODIC]:
                print(f"\n   Testing {memory_type.value} engine...")
                engine = memory_service.get_engine(memory_type)
                
                # Get raw data from database
                raw_result = engine.db.table(engine.table_name).select('*').eq('user_id', user_id).execute()
                print(f"     Raw DB records: {len(raw_result.data)}")
                
                if raw_result.data:
                    # Test search on this engine
                    engine_results = await engine.search_memories(search_query)
                    print(f"     Engine search results: {len(engine_results)}")
                    
                    # Check individual memory similarity
                    content_field = memory_content_fields.get(engine.table_name, 'content')
                    for raw_memory in raw_result.data[:2]:
                        content = raw_memory.get(content_field, '')
                        if content:
                            sim = await embedder.compute_similarity(query_text, content)
                            passes_threshold = sim >= search_query.similarity_threshold
                            print(f"       Content: {content[:50]}...")
                            print(f"       Similarity: {sim:.3f} (passes threshold: {passes_threshold})")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_memory_search())