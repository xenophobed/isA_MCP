#!/usr/bin/env python3
"""
GraphRAG Client Demo
Comprehensive demonstration of GraphRAG capabilities through MCP
"""

import asyncio
import json
import logging
from typing import List, Dict, Any
from mcp.client import StdioClientSession
from mcp.client.models import ClientCapabilities

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphRAGClient:
    """Client for GraphRAG MCP Server"""
    
    def __init__(self, server_command: List[str]):
        self.server_command = server_command
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = StdioClientSession(self.server_command)
        await self.session.__aenter__()
        
        await self.session.initialize(
            client_capabilities=ClientCapabilities(roots={}, sampling={})
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.__aexit__(exc_type, exc_val, exc_tb)
    
    async def ingest_document(self, content: str, title: str = None, source: str = None, metadata: dict = None) -> Dict:
        """Ingest a document into the knowledge graph"""
        args = {"content": content}
        if title:
            args["title"] = title
        if source:
            args["source"] = source
        if metadata:
            args["metadata"] = metadata
        
        result = await self.session.call_tool("ingest_document", args)
        return json.loads(result.content[0].text)
    
    async def semantic_search(self, query: str, search_type: str = "both", limit: int = 10) -> Dict:
        """Perform semantic search"""
        result = await self.session.call_tool("semantic_search", {
            "query": query,
            "search_type": search_type,
            "limit": limit
        })
        return json.loads(result.content[0].text)
    
    async def graph_traversal(self, start_entity: str, max_depth: int = 3, 
                            relationship_types: List[str] = None, return_paths: bool = False) -> Dict:
        """Traverse the knowledge graph"""
        args = {
            "start_entity": start_entity,
            "max_depth": max_depth,
            "return_paths": return_paths
        }
        if relationship_types:
            args["relationship_types"] = relationship_types
        
        result = await self.session.call_tool("graph_traversal", args)
        return json.loads(result.content[0].text)
    
    async def community_detection(self, algorithm: str = "louvain", min_community_size: int = 3) -> Dict:
        """Detect communities in the graph"""
        result = await self.session.call_tool("community_detection", {
            "algorithm": algorithm,
            "min_community_size": min_community_size
        })
        return json.loads(result.content[0].text)
    
    async def graphrag_query(self, query: str, context_depth: int = 2, 
                           max_entities: int = 10, reasoning_mode: str = "hybrid") -> Dict:
        """Perform comprehensive GraphRAG query"""
        result = await self.session.call_tool("graphrag_query", {
            "query": query,
            "context_depth": context_depth,
            "max_entities": max_entities,
            "reasoning_mode": reasoning_mode
        })
        return json.loads(result.content[0].text)
    
    async def entity_linking(self, similarity_threshold: float = 0.85, merge_duplicates: bool = True) -> Dict:
        """Link similar entities"""
        result = await self.session.call_tool("entity_linking", {
            "similarity_threshold": similarity_threshold,
            "merge_duplicates": merge_duplicates
        })
        return json.loads(result.content[0].text)
    
    async def graph_summarization(self, target: str, summary_type: str = "comprehensive") -> Dict:
        """Generate graph summaries"""
        result = await self.session.call_tool("graph_summarization", {
            "target": target,
            "summary_type": summary_type
        })
        return json.loads(result.content[0].text)
    
    async def get_graph_statistics(self) -> Dict:
        """Get graph statistics"""
        result = await self.session.read_resource("graphrag://graph/statistics")
        return json.loads(result.contents[0].text)
    
    async def get_all_entities(self) -> List[Dict]:
        """Get all entities"""
        result = await self.session.read_resource("graphrag://entities/all")
        return json.loads(result.contents[0].text)
    
    async def get_all_communities(self) -> List[Dict]:
        """Get all communities"""
        result = await self.session.read_resource("graphrag://communities/all")
        return json.loads(result.contents[0].text)

# Sample knowledge base for demonstration
SAMPLE_DOCUMENTS = [
    {
        "title": "Introduction to Machine Learning",
        "content": """Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data without being explicitly programmed. It involves statistical techniques that enable computers to improve their performance on a specific task through experience. Key concepts include supervised learning, unsupervised learning, and reinforcement learning. Popular algorithms include neural networks, decision trees, and support vector machines. Applications span from natural language processing to computer vision.""",
        "source": "ml_textbook_chapter1.pdf",
        "metadata": {"domain": "computer_science", "difficulty": "beginner", "topics": ["machine_learning", "artificial_intelligence"]}
    },
    {
        "title": "Deep Learning and Neural Networks",
        "content": """Deep learning is a specialized subset of machine learning that uses artificial neural networks with multiple layers to model and understand complex patterns in data. Convolutional Neural Networks (CNNs) are particularly effective for image recognition tasks, while Recurrent Neural Networks (RNNs) and Long Short-Term Memory (LSTM) networks excel at sequential data processing. Transformer architectures have revolutionized natural language processing. Deep learning requires large datasets and significant computational resources, often utilizing GPUs for training.""",
        "source": "deep_learning_handbook.pdf",
        "metadata": {"domain": "computer_science", "difficulty": "advanced", "topics": ["deep_learning", "neural_networks", "transformers"]}
    },
    {
        "title": "Knowledge Graphs and Semantic Web",
        "content": """Knowledge graphs are structured representations of real-world entities and their relationships, typically stored as graph databases. They consist of nodes representing entities and edges representing relationships between them. The Semantic Web uses ontologies and RDF triples to create machine-readable knowledge. Knowledge graphs enable advanced reasoning, question answering, and knowledge discovery. Major examples include Google's Knowledge Graph, Wikidata, and corporate knowledge bases. Neo4j is a popular graph database for implementing knowledge graphs.""",
        "source": "semantic_web_guide.pdf",
        "metadata": {"domain": "computer_science", "difficulty": "intermediate", "topics": ["knowledge_graphs", "semantic_web", "graph_databases"]}
    },
    {
        "title": "Natural Language Processing Fundamentals",
        "content": """Natural Language Processing (NLP) is a field that combines computational linguistics with machine learning to enable computers to understand, interpret, and generate human language. Core tasks include tokenization, part-of-speech tagging, named entity recognition, sentiment analysis, and machine translation. Modern NLP heavily relies on transformer models like BERT, GPT, and T5. Applications include chatbots, search engines, and automated content generation. NLP faces challenges with context understanding, ambiguity resolution, and multilingual processing.""",
        "source": "nlp_foundations.pdf",
        "metadata": {"domain": "computer_science", "difficulty": "intermediate", "topics": ["nlp", "computational_linguistics", "transformers"]}
    },
    {
        "title": "Graph Neural Networks and AI",
        "content": """Graph Neural Networks (GNNs) are a class of deep learning models designed to work with graph-structured data. They can learn representations of nodes, edges, and entire graphs by aggregating information from local neighborhoods. Popular GNN variants include Graph Convolutional Networks (GCNs), GraphSAGE, and Graph Attention Networks (GATs). GNNs are particularly useful for tasks involving social networks, molecular property prediction, and knowledge graph completion. They bridge the gap between traditional machine learning and graph analytics.""",
        "source": "gnn_research_paper.pdf",
        "metadata": {"domain": "computer_science", "difficulty": "advanced", "topics": ["graph_neural_networks", "deep_learning", "graph_analytics"]}
    },
    {
        "title": "Retrieval-Augmented Generation Systems",
        "content": """Retrieval-Augmented Generation (RAG) combines information retrieval with language generation to produce more accurate and contextually relevant responses. RAG systems first retrieve relevant documents from a knowledge base using semantic search, then use this context to generate responses. This approach helps reduce hallucinations in large language models and enables them to access up-to-date information. GraphRAG extends this concept by incorporating graph-structured knowledge, allowing for more sophisticated reasoning about relationships and multi-hop connections.""",
        "source": "rag_systems_overview.pdf",
        "metadata": {"domain": "computer_science", "difficulty": "advanced", "topics": ["rag", "information_retrieval", "language_generation"]}
    }
]

async def comprehensive_demo():
    """Comprehensive demonstration of GraphRAG capabilities"""
    
    async with GraphRAGClient(["python", "graphrag_mcp_server.py"]) as client:
        print("🚀 GraphRAG MCP Server Demo")
        print("=" * 50)
        
        # Phase 1: Knowledge Ingestion
        print("\n📚 Phase 1: Knowledge Ingestion")
        print("-" * 30)
        
        ingested_docs = []
        for i, doc in enumerate(SAMPLE_DOCUMENTS):
            print(f"Ingesting document {i+1}: {doc['title']}")
            result = await client.ingest_document(
                content=doc['content'],
                title=doc['title'],
                source=doc['source'],
                metadata=doc['metadata']
            )
            ingested_docs.append(result)
            print(f"  ✓ Extracted {result['entities_extracted']} entities, {result['relationships_extracted']} relationships")
        
        print(f"\n📊 Total documents ingested: {len(ingested_docs)}")
        
        # Phase 2: Graph Analysis
        print("\n🔍 Phase 2: Graph Analysis")
        print("-" * 30)
        
        # Get graph statistics
        stats = await client.get_graph_statistics()
        print("Graph Statistics:")
        for node_stat in stats['node_statistics']:
            print(f"  - {node_stat['label']}: {node_stat['count']} nodes")
        for rel_stat in stats['relationship_statistics']:
            print(f"  - {rel_stat['type']}: {rel_stat['count']} relationships")
        
        # Phase 3: Entity Linking
        print("\n🔗 Phase 3: Entity Linking")
        print("-" * 30)
        
        linking_result = await client.entity_linking(similarity_threshold=0.85)
        print(f"Entity Linking Results:")
        print(f"  - Entities compared: {linking_result['entities_compared']}")
        print(f"  - Similar pairs found: {linking_result['similar_pairs_found']}")
        print(f"  - Entities merged: {linking_result['entities_merged']}")
        
        if linking_result['similar_pairs']:
            print("  Top similar entity pairs:")
            for pair in linking_result['similar_pairs'][:3]:
                print(f"    • {pair['entity1_name']} ↔ {pair['entity2_name']} (similarity: {pair['similarity']:.3f})")
        
        # Phase 4: Community Detection
        print("\n🏘️ Phase 4: Community Detection")
        print("-" * 30)
        
        communities = await client.community_detection(algorithm="louvain", min_community_size=2)
        print(f"Community Detection Results:")
        print(f"  - Communities found: {communities['communities_found']}")
        print(f"  - Total entities in communities: {communities['total_entities_in_communities']}")
        
        if communities['communities']:
            print("  Discovered communities:")
            for i, community in enumerate(communities['communities'][:3]):
                print(f"    Community {i+1}: {community['size']} entities, density: {community['density']:.3f}")
                print(f"      Members: {', '.join(community['members'][:5])}")
        
        # Phase 5: Semantic Search
        print("\n🔎 Phase 5: Semantic Search")
        print("-" * 30)
        
        search_queries = [
            "neural networks and deep learning",
            "graph databases and knowledge representation",
            "natural language processing applications"
        ]
        
        for query in search_queries:
            print(f"\nSearching: '{query}'")
            search_result = await client.semantic_search(query, limit=3)
            
            print("  Top entities:")
            for entity in search_result['entities'][:2]:
                print(f"    • {entity['name']} ({entity['type']}) - similarity: {entity['score']:.3f}")
            
            print("  Top documents:")
            for doc in search_result['documents'][:2]:
                print(f"    • {doc['title']} - similarity: {doc['score']:.3f}")
        
        # Phase 6: Graph Traversal
        print("\n🗺️ Phase 6: Graph Traversal")
        print("-" * 30)
        
        # Get some entities to traverse from
        entities = await client.get_all_entities()
        if entities:
            start_entity = entities[0]['name']
            print(f"Traversing from entity: '{start_entity}'")
            
            traversal = await client.graph_traversal(
                start_entity=start_entity,
                max_depth=2,
                return_paths=True
            )
            
            print(f"  - Unique nodes found: {traversal['unique_nodes']}")
            print(f"  - Unique relationships: {traversal['unique_relationships']}")
            
            if traversal.get('paths'):
                print(f"  - Total paths: {len(traversal['paths'])}")
                for i, path in enumerate(traversal['paths'][:2]):
                    path_names = [node['name'] for node in path['nodes']]
                    print(f"    Path {i+1}: {' → '.join(path_names)}")
        
        # Phase 7: Advanced GraphRAG Queries
        print("\n🧠 Phase 7: Advanced GraphRAG Queries")
        print("-" * 30)
        
        complex_queries = [
            "How do neural networks relate to natural language processing?",
            "What is the connection between knowledge graphs and machine learning?",
            "Explain the role of transformers in modern AI systems"
        ]
        
        for query in complex_queries:
            print(f"\n🤔 GraphRAG Query: '{query}'")
            rag_result = await client.graphrag_query(
                query=query,
                context_depth=2,
                max_entities=8,
                reasoning_mode="hybrid"
            )
            
            print(f"  📊 Retrieved Context:")
            print(f"    - Relevant entities: {rag_result['relevant_entities']}")
            print(f"    - Context nodes: {rag_result['context_nodes']}")
            print(f"    - Relationships: {rag_result['context_relationships']}")
            print(f"    - Communities involved: {rag_result['communities_involved']}")
            
            print(f"  📝 Generated Context Summary:")
            context_preview = rag_result['context'][:300] + "..." if len(rag_result['context']) > 300 else rag_result['context']
            print(f"    {context_preview}")
            
            print(f"  🎯 RAG Prompt Preview:")
            prompt_preview = rag_result['rag_prompt'][:200] + "..." if len(rag_result['rag_prompt']) > 200 else rag_result['rag_prompt']
            print(f"    {prompt_preview}")
        
        # Phase 8: Graph Summarization
        print("\n📋 Phase 8: Graph Summarization")
        print("-" * 30)
        
        # Global graph summary
        global_summary = await client.graph_summarization("global")
        print("Global Graph Summary:")
        print(f"  {global_summary['summary']}")
        
        # Entity-specific summaries
        if entities:
            for entity in entities[:2]:
                entity_summary = await client.graph_summarization(entity['name'])
                print(f"\nEntity Summary - {entity['name']}:")
                print(f"  {entity_summary['summary']}")
        
        print("\n🎉 Demo Complete!")
        print("=" * 50)

async def interactive_graphrag():
    """Interactive GraphRAG query interface"""
    
    async with GraphRAGClient(["python", "graphrag_mcp_server.py"]) as client:
        print("🧠 Interactive GraphRAG Interface")
        print("Type 'help' for commands, 'quit' to exit")
        print("-" * 40)
        
        while True:
            try:
                user_input = input("\nGraphRAG> ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if user_input.lower() == 'help':
                    print("""
Available commands:
  search <query>          - Semantic search
  traverse <entity>       - Graph traversal from entity
  communities            - Show detected communities
  stats                  - Graph statistics
  summarize <target>     - Summarize graph/entity
  rag <query>           - Full GraphRAG query
  entities              - List all entities
  
Examples:
  rag How do neural networks work?
  search machine learning
  traverse "neural networks"
  communities
                    """)
                    continue
                
                if not user_input:
                    continue
                
                parts = user_input.split(' ', 1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if command == 'search':
                    if not args:
                        print("Usage: search <query>")
                        continue
                    
                    result = await client.semantic_search(args, limit=5)
                    print(f"\n🔍 Search Results for '{args}':")
                    
                    if result['entities']:
                        print("Entities:")
                        for entity in result['entities']:
                            print(f"  • {entity['name']} ({entity['type']}) - {entity['score']:.3f}")
                    
                    if result['documents']:
                        print("Documents:")
                        for doc in result['documents']:
                            print(f"  • {doc['title']} - {doc['score']:.3f}")
                
                elif command == 'traverse':
                    if not args:
                        print("Usage: traverse <entity_name>")
                        continue
                    
                    result = await client.graph_traversal(args, max_depth=2)
                    print(f"\n🗺️ Traversal from '{args}':")
                    print(f"  Nodes found: {result['unique_nodes']}")
                    print(f"  Relationships: {result['unique_relationships']}")
                    
                    if result['relationships']:
                        print("  Key relationships:")
                        for rel in result['relationships'][:5]:
                            print(f"    {rel['start']} --{rel['type']}--> {rel['end']}")
                
                elif command == 'communities':
                    result = await client.get_all_communities()
                    print(f"\n🏘️ Detected Communities:")
                    for i, community in enumerate(result[:5]):
                        print(f"  Community {i+1}: {community['name']} (size: {community['size']})")
                
                elif command == 'stats':
                    result = await client.get_graph_statistics()
                    print(f"\n📊 Graph Statistics:")
                    for node_stat in result['node_statistics']:
                        print(f"  {node_stat['label']}: {node_stat['count']}")
                
                elif command == 'summarize':
                    target = args if args else "global"
                    result = await client.graph_summarization(target)
                    print(f"\n📋 Summary of '{target}':")
                    print(f"  {result['summary']}")
                
                elif command == 'rag':
                    if not args:
                        print("Usage: rag <query>")
                        continue
                    
                    result = await client.graphrag_query(args, reasoning_mode="hybrid")
                    print(f"\n🧠 GraphRAG Response for '{args}':")
                    print(f"  Context entities: {result['relevant_entities']}")
                    print(f"  Graph context: {result['context_nodes']} nodes, {result['context_relationships']} relationships")
                    print(f"\n📝 Context:")
                    print(f"  {result['context'][:500]}{'...' if len(result['context']) > 500 else ''}")
                
                elif command == 'entities':
                    result = await client.get_all_entities()
                    print(f"\n👥 All Entities ({len(result)} total):")
                    for entity in result[:10]:
                        print(f"  • {entity['name']} ({entity['type']})")
                    if len(result) > 10:
                        print(f"  ... and {len(result) - 10} more")
                
                else:
                    print(f"Unknown command: {command}. Type 'help' for available commands.")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

async def benchmark_graphrag():
    """Benchmark GraphRAG performance"""
    
    import time
    
    async with GraphRAGClient(["python", "graphrag_mcp_server.py"]) as client:
        print("⚡ GraphRAG Performance Benchmark")
        print("-" * 40)
        
        # Benchmark queries
        test_queries = [
            "machine learning algorithms",
            "neural network architectures",
            "graph database applications",
            "natural language processing",
            "deep learning frameworks"
        ]
        
        # Semantic search benchmark
        print("\n🔍 Semantic Search Benchmark:")
        search_times = []
        for query in test_queries:
            start_time = time.time()
            await client.semantic_search(query, limit=5)
            search_time = time.time() - start_time
            search_times.append(search_time)
            print(f"  '{query}': {search_time:.3f}s")
        
        print(f"  Average search time: {sum(search_times)/len(search_times):.3f}s")
        
        # GraphRAG query benchmark
        print("\n🧠 GraphRAG Query Benchmark:")
        rag_times = []
        for query in test_queries[:3]:  # Fewer queries as these are more expensive
            start_time = time.time()
            await client.graphrag_query(f"Explain {query} in detail", max_entities=5)
            rag_time = time.time() - start_time
            rag_times.append(rag_time)
            print(f"  'Explain {query}': {rag_time:.3f}s")
        
        print(f"  Average GraphRAG time: {sum(rag_times)/len(rag_times):.3f}s")
        
        # Graph traversal benchmark
        entities = await client.get_all_entities()
        if entities:
            print("\n🗺️ Graph Traversal Benchmark:")
            traversal_times = []
            for entity in entities[:3]:
                start_time = time.time()
                await client.graph_traversal(entity['name'], max_depth=2)
                traversal_time = time.time() - start_time
                traversal_times.append(traversal_time)
                print(f"  From '{entity['name']}': {traversal_time:.3f}s")
            
            print(f"  Average traversal time: {sum(traversal_times)/len(traversal_times):.3f}s")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "interactive":
            asyncio.run(interactive_graphrag())
        elif mode == "benchmark":
            asyncio.run(benchmark_graphrag())
        else:
            print("Usage: python graphrag_client_demo.py [interactive|benchmark]")
    else:
        asyncio.run(comprehensive_demo())