#!/usr/bin/env python3
"""
Enhanced GraphRAG MCP Client v1.6
Provides Graph-based RAG capabilities through MCP
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

class GraphRAGClient:
    """GraphRAG MCP Client implementation"""
    
    def __init__(self, server_url: str = "http://localhost:8002/mcp"):
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
        """Connect to GraphRAG MCP server"""
        print(f"🔌 Connecting to GraphRAG server at {self.server_url}...")
        
        try:
            # Create streamable HTTP client
            self.client_context = streamablehttp_client(self.server_url)
            self.read, self.write, _ = await self.client_context.__aenter__()
            
            # Create session
            self.session_context = ClientSession(self.read, self.write)
            self.session = await self.session_context.__aenter__()
            
            # Initialize session
            await self.session.initialize()
            print("✅ GraphRAG session initialized")
            
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
    
    # === Graph Operations ===
    
    async def create_node(self, label: str, properties: Dict) -> Dict:
        """Create a node in the graph"""
        return await self.call_tool("create_node", {
            "label": label,
            "properties": properties
        })
    
    async def create_relationship(self, from_node_id: str, to_node_id: str,
                                rel_type: str, properties: Optional[Dict] = None) -> Dict:
        """Create a relationship between nodes"""
        return await self.call_tool("create_relationship", {
            "from_node_id": from_node_id,
            "to_node_id": to_node_id,
            "rel_type": rel_type,
            "properties": properties
        })
    
    async def query_graph(self, cypher_query: str, params: Optional[Dict] = None) -> Dict:
        """Execute a Cypher query"""
        return await self.call_tool("query_graph", {
            "query": cypher_query,
            "params": params
        })
    
    # === GraphRAG Operations ===
    
    async def add_document_graph(self, document: str, metadata: Optional[Dict] = None,
                               extract_entities: bool = True) -> Dict:
        """Add a document with graph structure"""
        return await self.call_tool("add_document_graph", {
            "document": document,
            "metadata": metadata,
            "extract_entities": extract_entities
        })
    
    async def search_graph_similar(self, query: str, n_results: int = 5,
                                 include_related: bool = True,
                                 max_hops: int = 2) -> Dict:
        """Search for similar content using graph structure"""
        return await self.call_tool("search_graph_similar", {
            "query": query,
            "n_results": n_results,
            "include_related": include_related,
            "max_hops": max_hops
        })
    
    async def graphrag_query(self, query: str, n_results: int = 3,
                           min_similarity: float = 0.0,
                           use_graph_context: bool = True,
                           max_hops: int = 2) -> Dict:
        """Perform full GraphRAG query"""
        return await self.call_tool("graphrag_query", {
            "query": query,
            "n_results": n_results,
            "min_similarity": min_similarity,
            "use_graph_context": use_graph_context,
            "max_hops": max_hops
        })

async def test_graphrag_operations():
    """Test GraphRAG operations"""
    print("🧪 Testing GraphRAG Operations")
    print("=" * 50)
    
    async with GraphRAGClient() as client:
        # Test 1: Create nodes and relationships
        print("\n📝 Test 1: Creating graph structure...")
        
        # Create document nodes
        doc1 = await client.create_node("Document", {
            "text": "Python is a versatile programming language.",
            "type": "technology"
        })
        doc2 = await client.create_node("Document", {
            "text": "Neo4j is a graph database.",
            "type": "technology"
        })
        
        # Create relationship
        rel = await client.create_relationship(
            doc1["node_id"],
            doc2["node_id"],
            "RELATED_TO",
            {"weight": 0.8}
        )
        print("✅ Created graph structure")
        
        # Test 2: Add document with automatic graph structure
        print("\n🔄 Test 2: Adding document with graph structure...")
        doc_result = await client.add_document_graph(
            "Machine learning models in Python often use TensorFlow or PyTorch.",
            {"type": "tutorial"}
        )
        print(f"✅ Added document with {doc_result.get('entity_count', 0)} entities")
        
        # Test 3: Graph-based search
        print("\n🔍 Test 3: Searching with graph context...")
        search_result = await client.search_graph_similar(
            "programming languages and databases",
            include_related=True
        )
        if search_result.get("results"):
            print("✅ Found related content:")
            for item in search_result["results"]:
                print(f"   - {item.get('text', '')} (relevance: {item.get('score', 0):.2f})")
        
        # Test 4: GraphRAG query
        print("\n🤖 Test 4: Performing GraphRAG query...")
        rag_result = await client.graphrag_query(
            "How are Python and databases connected?",
            use_graph_context=True
        )
        print("\n✅ GraphRAG Response:")
        print(f"Query: {rag_result.get('query', '')}")
        print(f"Answer: {rag_result.get('answer', '')}")
        print(f"Graph Context: {rag_result.get('graph_context', '')}")
        
        # Test 5: Custom graph query
        print("\n📊 Test 5: Running custom Cypher query...")
        cypher_result = await client.query_graph("""
            MATCH (d:Document)-[r:RELATED_TO]->(other:Document)
            WHERE d.type = 'technology'
            RETURN d.text, type(r), other.text
        """)
        print("✅ Graph query results:")
        for record in cypher_result.get("records", []):
            print(f"   {record[0]} --[{record[1]}]--> {record[2]}")
        
        print("\n🎉 All GraphRAG tests completed!")

if __name__ == "__main__":
    asyncio.run(test_graphrag_operations())
