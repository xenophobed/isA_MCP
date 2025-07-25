#!/usr/bin/env python3
"""
Debug similarity calculation
"""

import asyncio
import os
import json
from tools.services.intelligence_service.isa_client import ISAClient

async def test_similarity():
    """Test ISA similarity calculation"""
    
    # Set up environment
    os.environ['ISA_API_URL'] = 'http://localhost:8082'
    
    isa_client = ISAClient()
    
    try:
        # Test similarity calculation
        text1 = "software engineer"
        text2 = "Bob, a software engineer at Microsoft. I specialize in distributed systems"
        
        print(f"Testing similarity between:")
        print(f"Text 1: {text1}")
        print(f"Text 2: {text2}")
        
        similarity = await isa_client.compute_similarity(text1, text2)
        print(f"Similarity score: {similarity}")
        
        # Test with very different texts
        text3 = "I like pizza and cats"
        similarity2 = await isa_client.compute_similarity(text1, text3)
        print(f"Similarity with different text: {similarity2}")
        
        # Test embedding generation
        embedding = await isa_client.embed_single(text1)
        print(f"Embedding dimensions: {len(embedding) if embedding else 'None'}")
        
        # Test if ISA service is responsive
        print("Testing ISA service health...")
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8082/health")
            print(f"ISA Health: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_similarity())