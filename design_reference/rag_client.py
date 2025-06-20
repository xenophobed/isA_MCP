#!/usr/bin/env python3
"""
Example client for MCP RAG Server
Shows how to interact with the RAG pipeline through MCP
"""

import asyncio
import json
import logging
from typing import List, Dict, Any

from mcp.client import StdioClientSession
from mcp.client.models import ClientCapabilities
from mcp.types import CallToolResult, ListResourcesResult, ReadResourceResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGClient:
    """Client for interacting with MCP RAG Server"""
    
    def __init__(self, server_command: List[str]):
        self.server_command = server_command
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = StdioClientSession(self.server_command)
        await self.session.__aenter__()
        
        # Initialize the session
        await self.session.initialize(
            client_capabilities=ClientCapabilities(
                roots={},
                sampling={}
            )
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.__aexit__(exc_type, exc_val, exc_tb)
    
    async def list_resources(self) -> List[Dict]:
        """List available vector database resources"""
        result = await self.session.list_resources()
        return [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mimeType
            }
            for resource in result.resources
        ]
    
    async def get_collection_info(self, collection_name: str) -> Dict:
        """Get information about a vector collection"""
        uri = f"vectordb://collections/{collection_name}"
        result = await self.session.read_resource(uri)
        return json.loads(result.contents[0].text)
    
    async def get_documents(self, collection_name: str) -> List[Dict]:
        """Get all documents from a collection"""
        uri = f"vectordb://documents/{collection_name}"
        result = await self.session.read_resource(uri)
        return json.loads(result.contents[0].text)
    
    async def embed_text(self, text: str, normalize: bool = True) -> Dict:
        """Generate embeddings for text"""
        result = await self.session.call_tool("embed_text", {
            "text": text,
            "normalize": normalize
        })
        return json.loads(result.content[0].text)
    
    async def add_documents(self, documents: List[str], ids: List[str] = None, metadatas: List[Dict] = None) -> Dict:
        """Add documents to the vector database"""
        args = {"documents": documents}
        if ids:
            args["ids"] = ids
        if metadatas:
            args["metadatas"] = metadatas
        
        result = await self.session.call_tool("add_documents", args)
        return json.loads(result.content[0].text)
    
    async def search_similar(self, query: str, n_results: int = 5, include_distances: bool = True) -> Dict:
        """Search for similar documents"""
        result = await self.session.call_tool("search_similar", {
            "query": query,
            "n_results": n_results,
            "include_distances": include_distances
        })
        return json.loads(result.content[0].text)
    
    async def rag_query(self, query: str, n_results: int = 3, min_similarity: float = 0.0) -> Dict:
        """Perform full RAG query"""
        result = await self.session.call_tool("rag_query", {
            "query": query,
            "n_results": n_results,
            "min_similarity": min_similarity
        })
        return json.loads(result.content[0].text)

async def demo_rag_pipeline():
    """Demonstrate the RAG pipeline functionality"""
    
    # Sample documents for the demo
    sample_documents = [
        "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.",
        "Vector databases are specialized databases designed to store and query high-dimensional vectors efficiently.",
        "Retrieval-Augmented Generation (RAG) combines information retrieval with language generation to provide more accurate responses.",
        "ChromaDB is an open-source embedding database that makes it easy to build applications with embeddings.",
        "The Model Context Protocol (MCP) enables AI applications to securely connect to data sources and tools."
    ]
    
    sample_metadata = [
        {"topic": "machine_learning", "difficulty": "beginner"},
        {"topic": "databases", "difficulty": "intermediate"},
        {"topic": "nlp", "difficulty": "advanced"},
        {"topic": "databases", "difficulty": "beginner"},
        {"topic": "protocols", "difficulty": "intermediate"}
    ]
    
    # Initialize the RAG client
    async with RAGClient(["python", "mcp_rag_server.py"]) as client:
        
        print("=== MCP RAG Pipeline Demo ===\n")
        
        # 1. List available resources
        print("1. Available Resources:")
        resources = await client.list_resources()
        for resource in resources:
            print(f"   - {resource['name']}: {resource['description']}")
        print()
        
        # 2. Add sample documents
        print("2. Adding sample documents...")
        add_result = await client.add_documents(
            documents=sample_documents,
            metadatas=sample_metadata
        )
        print(f"   Added {add_result['added_count']} documents")
        print(f"   Collection size: {add_result['collection_size']}")
        print()
        
        # 3. Get collection information
        print("3. Collection Information:")
        collection_info = await client.get_collection_info("rag_documents")
        print(f"   Collection: {collection_info['collection_name']}")
        print(f"   Documents: {collection_info['document_count']}")
        print(f"   Model: {collection_info['embedding_model']}")
        print()
        
        # 4. Test embedding generation
        print("4. Testing embedding generation...")
        embed_result = await client.embed_text("What is machine learning?")
        print(f"   Generated embedding with {embed_result['dimension']} dimensions")
        print(f"   First 5 values: {embed_result['embedding'][:5]}")
        print()
        
        # 5. Test similarity search
        print("5. Similarity Search:")
        search_query = "What are vector databases?"
        search_result = await client.search_similar(search_query, n_results=3)
        print(f"   Query: '{search_query}'")
        print(f"   Found {search_result['total_found']} similar documents:")
        for i, doc in enumerate(search_result['results']):
            print(f"   {i+1}. (Similarity: {doc['similarity']:.3f}) {doc['document'][:100]}...")
        print()
        
        # 6. Full RAG query
        print("6. RAG Query:")
        rag_query = "How does RAG work with embeddings?"
        rag_result = await client.rag_query(rag_query, n_results=2)
        print(f"   Query: '{rag_query}'")
        print(f"   Retrieved {rag_result['retrieved_count']} relevant documents")
        print("   Generated Context:")
        print(f"   {rag_result['context'][:300]}...")
        print()
        print("   RAG Prompt:")
        print(f"   {rag_result['rag_prompt'][:200]}...")
        print()
        
        # 7. Show document sources
        print("7. Source Information:")
        for i, source in enumerate(rag_result['sources']):
            print(f"   Source {i+1}: ID={source['id']}, Similarity={source['similarity']:.3f}")
            if source['metadata']:
                print(f"   Metadata: {source['metadata']}")
        print()

async def interactive_rag_demo():
    """Interactive RAG demo"""
    async with RAGClient(["python", "mcp_rag_server.py"]) as client:
        print("=== Interactive RAG Demo ===")
        print("Enter queries to search the vector database (type 'quit' to exit)")
        
        while True:
            try:
                query = input("\nEnter your query: ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not query:
                    continue
                
                # Perform RAG query
                result = await client.rag_query(query, n_results=3, min_similarity=0.1)
                
                print(f"\nFound {result['retrieved_count']} relevant documents:")
                print("=" * 50)
                print(result['context'])
                print("=" * 50)
                
                if result['sources']:
                    print("\nSources:")
                    for i, source in enumerate(result['sources']):
                        print(f"{i+1}. Similarity: {source['similarity']:.3f}")
                        if source['metadata']:
                            print(f"   Metadata: {source['metadata']}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive_rag_demo())
    else:
        asyncio.run(demo_rag_pipeline())