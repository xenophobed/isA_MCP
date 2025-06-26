#!/usr/bin/env python3
"""
Enhanced RAG MCP Client v1.5
Provides RAG (Retrieval Augmented Generation) capabilities through MCP
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

class RAGClient:
    """RAG MCP Client implementation"""
    
    def __init__(self, server_url: str = "http://localhost:8001/mcp"):
        self.server_url = server_url
        self.session = None
        self.client_context = None
        self.session_context = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def connect(self):
        """Connect to RAG MCP server"""
        print(f"🔌 Connecting to RAG server at {self.server_url}...")
        
        try:
            # Create streamable HTTP client
            self.client_context = streamablehttp_client(self.server_url)
            self.read, self.write, _ = await self.client_context.__aenter__()
            
            # Create session
            self.session_context = ClientSession(self.read, self.write)
            self.session = await self.session_context.__aenter__()
            
            # Initialize session
            await self.session.initialize()
            print("✅ RAG session initialized")
            
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.session_context:
                await self.session_context.__aexit__(None, None, None)
            if self.client_context:
                await self.client_context.__aexit__(None, None, None)
            print("🧹 Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    async def call_tool(self, name: str, arguments: Dict) -> Dict:
        """Call an MCP tool and return the result"""
        if not self.session:
            return {"error": "No session available"}
        
        try:
            print(f"🔧 Calling tool: {name}")
            result = await self.session.call_tool(name, arguments)
            
            if hasattr(result, 'content') and result.content:
                content = result.content[0].text
                return json.loads(content)
            return {"error": "No content in response"}
            
        except Exception as e:
            print(f"❌ Tool call failed: {e}")
            return {"error": str(e)}
    
    # === RAG Operations ===
    
    async def embed_text(self, text: str, normalize: bool = True) -> Dict:
        """Generate embeddings for text"""
        return await self.call_tool("embed_text", {
            "text": text,
            "normalize": normalize
        })
    
    async def add_documents(self, documents: List[str], ids: Optional[List[str]] = None,
                          metadatas: Optional[List[Dict]] = None) -> Dict:
        """Add documents to the vector database"""
        return await self.call_tool("add_documents", {
            "documents": documents,
            "ids": ids,
            "metadatas": metadatas
        })
    
    async def search_similar(self, query: str, n_results: int = 5,
                           where: Optional[Dict] = None,
                           include_distances: bool = True) -> Dict:
        """Search for similar documents"""
        return await self.call_tool("search_similar", {
            "query": query,
            "n_results": n_results,
            "where": where,
            "include_distances": include_distances
        })
    
    async def delete_documents(self, ids: Optional[List[str]] = None,
                             where: Optional[Dict] = None) -> Dict:
        """Delete documents from the vector database"""
        return await self.call_tool("delete_documents", {
            "ids": ids,
            "where": where
        })
    
    async def rag_query(self, query: str, n_results: int = 3,
                       min_similarity: float = 0.0,
                       include_sources: bool = True) -> Dict:
        """Perform full RAG query"""
        return await self.call_tool("rag_query", {
            "query": query,
            "n_results": n_results,
            "min_similarity": min_similarity,
            "include_sources": include_sources
        })

async def test_rag_operations():
    """Test RAG operations"""
    print("🧪 Testing RAG Operations")
    print("=" * 50)
    
    async with RAGClient() as client:
        # Test 1: Add documents
        print("\n📝 Test 1: Adding documents...")
        docs = [
            "The quick brown fox jumps over the lazy dog.",
            "Python is a versatile programming language.",
            "Machine learning is transforming technology."
        ]
        add_result = await client.add_documents(docs)
        print(f"✅ Added {add_result.get('added_count', 0)} documents")
        
        # Test 2: Generate embeddings
        print("\n🧮 Test 2: Generating embeddings...")
        embed_result = await client.embed_text("Test embedding generation")
        print(f"✅ Generated embedding with dimension: {embed_result.get('dimension', 0)}")
        
        # Test 3: Search similar documents
        print("\n🔍 Test 3: Searching similar documents...")
        search_result = await client.search_similar("programming languages")
        if search_result.get("results"):
            print("✅ Found similar documents:")
            for doc in search_result["results"]:
                print(f"   - {doc.get('document', '')} (similarity: {doc.get('similarity', 0):.2f})")
        
        # Test 4: RAG query
        print("\n🤖 Test 4: Performing RAG query...")
        rag_result = await client.rag_query("What is Python used for?")
        print("\n✅ RAG Response:")
        print(f"Query: {rag_result.get('query', '')}")
        print(f"Context: {rag_result.get('context', '')}")
        print(f"Retrieved: {rag_result.get('retrieved_count', 0)} documents")
        
        # Test 5: Delete documents
        print("\n🗑️ Test 5: Deleting documents...")
        delete_result = await client.delete_documents(where={"type": "test"})
        print(f"✅ Deletion status: {delete_result.get('status', 'unknown')}")
        
        print("\n🎉 All RAG tests completed!")

if __name__ == "__main__":
    asyncio.run(test_rag_operations())
