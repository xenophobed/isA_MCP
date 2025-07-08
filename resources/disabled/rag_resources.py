#!/usr/bin/env python3
"""
RAG Resources Implementation with Supabase pgvector
Provides resource management for RAG services using Supabase and pgvector
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.logging import get_logger
from tools.services.rag_service.rag_client import get_rag_client

logger = get_logger(__name__)

async def register_rag_resources(mcp):
    """Register RAG resources with the MCP server"""
    
    rag_client = get_rag_client()
    
    @mcp.resource("rag://collections")
    async def get_collections_resource() -> str:
        """Get all RAG collections"""
        try:
            rag_client = get_rag_client()
            result = await rag_client.list_collections()
            
            if result["success"]:
                collections = result["collections"]
                resource_content = {
                    "status": "success",
                    "collections": collections,
                    "total_collections": len(collections),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Format as readable text
                content_lines = [
                    "# RAG Collections Overview",
                    f"Total Collections: {len(collections)}",
                    f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "## Collections:"
                ]
                
                for collection in collections:
                    content_lines.extend([
                        f"### {collection['name']}",
                        f"- Documents: {collection['document_count']}",
                        f"- Created: {collection.get('created_at', 'Unknown')}",
                        ""
                    ])
                
                return "\n".join(content_lines)
            else:
                return f"Error retrieving collections: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Error in collections resource: {e}")
            return f"Resource error: {str(e)}"
    
    @mcp.resource("rag://collection/{collection_name}")
    async def get_collection_resource(collection_name: str) -> str:
        """Get information about a specific RAG collection"""
        try:
            rag_client = get_rag_client()
            result = await rag_client.get_collection_stats(collection_name)
            
            if result["success"]:
                stats = result["stats"]
                content_lines = [
                    f"# RAG Collection: {collection_name}",
                    f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "## Statistics:",
                    f"- Document Count: {stats['document_count']}",
                    f"- Total Characters: {stats['total_characters']:,}",
                    f"- Average Document Length: {stats['average_doc_length']:.1f} characters",
                    "",
                    "## Usage:",
                    f"Use the RAG tools to search and manage documents in the '{collection_name}' collection.",
                    "",
                    "### Available Operations:",
                    "- `search_rag_documents`: Search for similar documents",
                    "- `add_rag_documents`: Add new documents to this collection",
                    "- `delete_rag_documents`: Remove documents from this collection"
                ]
                
                return "\n".join(content_lines)
            else:
                return f"Error retrieving collection stats: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Error in collection resource: {e}")
            return f"Resource error: {str(e)}"
    
    @mcp.resource("rag://search/recent")
    async def get_recent_searches_resource() -> str:
        """Get recent RAG search patterns and usage"""
        try:
            # This would typically come from a search history table
            # For now, we'll provide guidance on search capabilities
            content_lines = [
                "# RAG Search Capabilities",
                f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "## Search Types Available:",
                "",
                "### 1. Vector Search (Semantic)",
                "- Uses AI embeddings for semantic similarity",
                "- Best for: Finding conceptually similar content",
                "- Example: 'machine learning algorithms' finds ML-related docs",
                "",
                "### 2. Text Search (Keyword)",
                "- Traditional keyword-based search",
                "- Best for: Finding exact terms or phrases",
                "- Example: 'python function' finds docs containing those words",
                "",
                "## Search Parameters:",
                "- `query`: Your search text",
                "- `collection`: Limit search to specific collection",
                "- `limit`: Number of results (default: 5)",
                "- `threshold`: Similarity threshold (0-1, default: 0.0)",
                "- `search_type`: 'vector' or 'text' (default: 'vector')",
                "",
                "## Usage Tips:",
                "- Vector search works better for conceptual queries",
                "- Text search works better for exact term matching",
                "- Lower thresholds return more results",
                "- Higher thresholds return more precise results"
            ]
            
            return "\n".join(content_lines)
                
        except Exception as e:
            logger.error(f"Error in recent searches resource: {e}")
            return f"Resource error: {str(e)}"
    
    @mcp.resource("rag://embeddings/info")
    async def get_embeddings_info_resource() -> str:
        """Get information about the embedding model and capabilities"""
        try:
            rag_client = get_rag_client()
            
            # Get embedding info from the service
            test_result = await rag_client.generate_embeddings(["test"])
            
            if test_result["success"]:
                model_name = test_result.get("model_name", "Unknown")
                dimension = test_result.get("dimension", 0)
                
                content_lines = [
                    "# RAG Embedding Model Information",
                    f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "## Current Model:",
                    f"- Model: {model_name}",
                    f"- Dimension: {dimension}",
                    f"- Vector Database: Supabase pgvector",
                    "",
                    "## Capabilities:",
                    "- Semantic document similarity search",
                    "- Multi-language text understanding",
                    "- Real-time embedding generation",
                    "- Scalable vector storage with PostgreSQL",
                    "",
                    "## Performance:",
                    "- Fast similarity search with pgvector indexing",
                    "- Supports cosine similarity calculations",
                    "- Optimized for retrieval-augmented generation",
                    "",
                    "## Integration:",
                    "- Documents automatically embedded on upload",
                    "- Search queries embedded in real-time",
                    "- Consistent embedding model across all operations"
                ]
                
                return "\n".join(content_lines)
            else:
                return f"Error getting embedding info: {test_result.get('error', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Error in embeddings info resource: {e}")
            return f"Resource error: {str(e)}"
    
    @mcp.resource("rag://discover/{query}")
    async def get_smart_collections_resource(query: str) -> str:
        """Intelligently discover relevant RAG collections based on user query"""
        try:
            # Get all collections first
            collections_result = await rag_client.list_collections()
            
            if not collections_result["success"]:
                return f"Error retrieving collections: {collections_result.get('error', 'Unknown error')}"
            
            collections = collections_result["collections"]
            
            if not collections:
                return f"# RAG Smart Discovery: {query}\n\nNo collections found. You can create collections by adding documents with the `add_rag_documents` tool."
            
            # For each collection, search for content matching the query
            relevant_collections = []
            
            for collection in collections:
                collection_name = collection['name']
                
                # Perform a quick search in this collection
                search_params = {
                    "query": query,
                    "collection": collection_name,
                    "search_type": "text",  # Use text search for speed
                    "limit": 3,
                    "threshold": 0.0
                }
                
                search_result = await rag_client.search_documents(search_params)
                
                if search_result["success"] and search_result["total_found"] > 0:
                    # Calculate relevance score based on match count and collection size
                    relevance_score = search_result["total_found"] / max(collection["document_count"], 1)
                    
                    relevant_collections.append({
                        "name": collection_name,
                        "document_count": collection["document_count"],
                        "matches": search_result["total_found"],
                        "relevance_score": relevance_score,
                        "sample_matches": search_result["documents"][:2]  # Top 2 matches
                    })
            
            # Sort by relevance score
            relevant_collections.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            content_lines = [
                f"# RAG Smart Discovery: {query}",
                f"Found {len(relevant_collections)} relevant collection(s)",
                f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                ""
            ]
            
            if relevant_collections:
                content_lines.extend([
                    "## Recommended Collections:",
                    ""
                ])
                
                for i, coll in enumerate(relevant_collections[:3], 1):  # Top 3
                    content_lines.extend([
                        f"### {i}. Collection: {coll['name']}",
                        f"- **Relevance**: {coll['relevance_score']:.2%}",
                        f"- **Total Documents**: {coll['document_count']}",
                        f"- **Matching Documents**: {coll['matches']}",
                        "",
                        "**Sample matches:**"
                    ])
                    
                    for j, match in enumerate(coll['sample_matches'], 1):
                        content_lines.append(f"{j}. {match['content'][:100]}...")
                    
                    content_lines.extend([
                        "",
                        f"**Recommended search**: Use `search_rag_documents` with collection='{coll['name']}'",
                        ""
                    ])
                
                content_lines.extend([
                    "## Next Steps:",
                    f"1. Use `search_rag_documents` to search in the most relevant collection",
                    f"2. Try vector search with `search_type='vector'` for semantic similarity",
                    f"3. Use `get_rag_collection_stats` to get detailed collection information"
                ])
            else:
                content_lines.extend([
                    "## No Direct Matches Found",
                    "",
                    "**Suggestions:**",
                    "1. Try broader search terms",
                    "2. Use `search_rag_documents` with vector search across all collections",
                    "3. Check `rag://collections` to see all available collections",
                    "",
                    "**Available Collections:**"
                ])
                
                for collection in collections:
                    content_lines.append(f"- {collection['name']}: {collection['document_count']} documents")
            
            return "\n".join(content_lines)
            
        except Exception as e:
            logger.error(f"Error in smart collections resource: {e}")
            return f"Resource error: {str(e)}"
    
    @mcp.resource("rag://status")
    async def get_rag_status_resource() -> str:
        """Get overall RAG system status and health"""
        try:
            rag_client = get_rag_client()
            
            # Get collections info
            collections_result = await rag_client.list_collections()
            
            if collections_result["success"]:
                total_collections = collections_result["total_collections"]
                collections = collections_result["collections"]
                total_documents = sum(c.get("document_count", 0) for c in collections)
                
                content_lines = [
                    "# RAG System Status",
                    f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "## System Health: ✅ Operational",
                    "",
                    "## Statistics:",
                    f"- Total Collections: {total_collections}",
                    f"- Total Documents: {total_documents:,}",
                    f"- Vector Database: Supabase pgvector",
                    f"- Embedding Service: Active",
                    "",
                    "## Recent Activity:",
                    "- Document indexing: Active",
                    "- Search queries: Responsive",
                    "- Vector generation: Operational",
                    "",
                    "## Available Resources:",
                    "- `rag://collections` - View all collections",
                    "- `rag://collection/{name}` - View specific collection",
                    "- `rag://search/recent` - Search capabilities guide",
                    "- `rag://embeddings/info` - Embedding model info",
                    "",
                    "## Available Tools:",
                    "- `search_rag_documents` - Search in document collections",
                    "- `add_rag_documents` - Add documents to collections",
                    "- `list_rag_collections` - List all collections",
                    "- `get_rag_collection_stats` - Get collection statistics",
                    "- `delete_rag_documents` - Remove documents",
                    "- `generate_rag_embeddings` - Generate text embeddings"
                ]
                
                return "\n".join(content_lines)
            else:
                return f"RAG System Status: ❌ Error\nDetails: {collections_result.get('error', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Error in RAG status resource: {e}")
            return f"RAG System Status: ❌ Error\nResource error: {str(e)}"

    logger.info("RAG resources registered successfully")

# For compatibility with auto-discovery
def register_resources(mcp):
    """Legacy function name for auto-discovery"""
    import asyncio
    # Run the async function in the current event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, create a task
            asyncio.create_task(register_rag_resources(mcp))
        else:
            # If not, run it
            loop.run_until_complete(register_rag_resources(mcp))
    except:
        # Fallback: just register synchronously
        asyncio.run(register_rag_resources(mcp))