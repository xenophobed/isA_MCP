#!/usr/bin/env python
"""
RAG Tools for MCP Server with Supabase pgvector
Provides retrieval-augmented generation capabilities
"""
import json
from typing import Dict, Any, List
from datetime import datetime

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.monitoring import monitor_manager
from tools.services.rag_service.rag_client import get_rag_client

logger = get_logger(__name__)

def register_rag_tools(mcp):
    """Register all RAG tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    rag_client = get_rag_client()
    
    @mcp.tool()
    @security_manager.security_check
    async def search_rag_documents(query: str, collection: str = "", limit: int = 5, 
                                 threshold: float = 0.0, search_type: str = "vector",
                                 user_id: str = "default") -> str:
        """Search for similar documents in RAG collections using vector or text search
        
        This tool searches through document collections using either vector similarity
        (semantic search) or text matching (keyword search).
        
        Args:
            query: Search query text
            collection: Collection name to search in (optional, searches all if not specified)
            limit: Maximum number of results to return (default: 5)
            threshold: Similarity threshold 0-1 (default: 0.0, returns all matches)
            search_type: 'vector' for semantic search or 'text' for keyword search (default: vector)
            user_id: User identifier for tracking
        
        Returns:
            JSON string with search results
        
        Keywords: search, documents, rag, vector, similarity, semantic, text, query, find, retrieve
        Category: rag
        """
        try:
            search_params = {
                "query": query,
                "collection": collection if collection else None,
                "limit": limit,
                "threshold": threshold,
                "search_type": search_type
            }
            
            result = await rag_client.search_documents(search_params)
            
            # Format response
            response = {
                "status": "success" if result["success"] else "error",
                "action": "search_rag_documents",
                "query": query,
                "search_type": search_type,
                "collection": collection,
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"RAG search performed: '{query}' in {collection or 'all collections'}")
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Error in RAG search: {e}")
            return json.dumps({
                "status": "error",
                "action": "search_rag_documents",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def add_rag_documents(documents: str, user_id: str = "default") -> str:
        """Add documents to RAG collections with vector embeddings
        
        This tool adds documents to RAG collections, automatically generating
        vector embeddings for semantic search capabilities.
        
        Args:
            documents: JSON string containing document data. Each document should have:
                      - content: The document text (required)
                      - collection: Collection name (optional, defaults to 'default')
                      - metadata: Additional metadata dict (optional)
                      - source: Document source identifier (optional)
                      - id: Document ID (optional, auto-generated if not provided)
            user_id: User identifier for tracking
        
        Returns:
            JSON string with operation result
        
        Keywords: add, documents, rag, vector, embeddings, store, index, upload, create
        Category: rag
        """
        try:
            # Parse documents input
            try:
                docs_data = json.loads(documents)
                if not isinstance(docs_data, list):
                    docs_data = [docs_data]
            except json.JSONDecodeError:
                return json.dumps({
                    "status": "error",
                    "action": "add_rag_documents",
                    "error": "Invalid JSON format for documents",
                    "timestamp": datetime.now().isoformat()
                })
            
            result = await rag_client.add_documents(docs_data)
            
            response = {
                "status": "success" if result["success"] else "error",
                "action": "add_rag_documents",
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
            
            if result["success"]:
                logger.info(f"Added {len(result['added_documents'])} documents to RAG")
            else:
                logger.error(f"Failed to add RAG documents: {result.get('error')}")
            
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Error adding RAG documents: {e}")
            return json.dumps({
                "status": "error",
                "action": "add_rag_documents",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    @mcp.tool()
    @security_manager.security_check
    async def list_rag_collections(user_id: str = "default") -> str:
        """List all RAG document collections
        
        This tool retrieves a list of all document collections in the RAG system
        along with their statistics.
        
        Args:
            user_id: User identifier for tracking
        
        Returns:
            JSON string with collections list
        
        Keywords: list, collections, rag, status, overview, statistics, catalog
        Category: rag
        """
        try:
            result = await rag_client.list_collections(user_id)
            
            response = {
                "status": "success" if result["success"] else "error",
                "action": "list_rag_collections",
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Listed RAG collections for user {user_id}")
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Error listing RAG collections: {e}")
            return json.dumps({
                "status": "error",
                "action": "list_rag_collections",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    @mcp.tool()
    @security_manager.security_check
    async def get_rag_collection_stats(collection_name: str, user_id: str = "default") -> str:
        """Get detailed statistics for a specific RAG collection
        
        This tool provides detailed information about a specific document collection,
        including document count, size statistics, and usage metrics.
        
        Args:
            collection_name: Name of the collection to analyze
            user_id: User identifier for tracking
        
        Returns:
            JSON string with collection statistics
        
        Keywords: statistics, collection, rag, stats, info, details, metrics, analysis
        Category: rag
        """
        try:
            result = await rag_client.get_collection_stats(collection_name, user_id)
            
            response = {
                "status": "success" if result["success"] else "error",
                "action": "get_rag_collection_stats",
                "collection": collection_name,
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Retrieved stats for RAG collection '{collection_name}'")
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Error getting RAG collection stats: {e}")
            return json.dumps({
                "status": "error",
                "action": "get_rag_collection_stats",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.HIGH)
    async def delete_rag_documents(delete_params: str, user_id: str = "default") -> str:
        """Delete documents from RAG collections
        
        This tool removes documents from RAG collections. Requires high authorization
        due to the destructive nature of the operation.
        
        Args:
            delete_params: JSON string with deletion parameters:
                          - document_ids: List of document IDs to delete (optional)
                          - collection_name: Collection name to delete entirely (optional)
                          - delete_all: Boolean to delete all documents (optional, dangerous)
            user_id: User identifier for tracking
        
        Returns:
            JSON string with deletion result
        
        Keywords: delete, remove, documents, rag, cleanup, purge, destroy, clear
        Category: rag
        """
        try:
            # Parse delete parameters
            try:
                params = json.loads(delete_params)
            except json.JSONDecodeError:
                return json.dumps({
                    "status": "error",
                    "action": "delete_rag_documents",
                    "error": "Invalid JSON format for delete_params",
                    "timestamp": datetime.now().isoformat()
                })
            
            result = await rag_client.delete_documents(params)
            
            response = {
                "status": "success" if result["success"] else "error",
                "action": "delete_rag_documents",
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
            
            if result["success"]:
                logger.info(f"Deleted {result['deleted_count']} RAG documents")
            else:
                logger.error(f"Failed to delete RAG documents: {result.get('error')}")
            
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Error deleting RAG documents: {e}")
            return json.dumps({
                "status": "error",
                "action": "delete_rag_documents",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    @mcp.tool()
    @security_manager.security_check
    async def generate_rag_embeddings(texts: str, model_name: str = "default", user_id: str = "default") -> str:
        """Generate vector embeddings for text content
        
        This tool generates vector embeddings for given text content using the
        configured embedding model.
        
        Args:
            texts: JSON string containing list of texts to embed
            model_name: Embedding model name (default uses system default)
            user_id: User identifier for tracking
        
        Returns:
            JSON string with embedding vectors
        
        Keywords: embeddings, vector, generate, encode, transform, ai, model, similarity
        Category: rag
        """
        try:
            # Parse texts input
            try:
                texts_list = json.loads(texts)
                if not isinstance(texts_list, list):
                    texts_list = [texts_list]
            except json.JSONDecodeError:
                return json.dumps({
                    "status": "error",
                    "action": "generate_rag_embeddings",
                    "error": "Invalid JSON format for texts",
                    "timestamp": datetime.now().isoformat()
                })
            
            result = await rag_client.generate_embeddings(texts_list, model_name)
            
            response = {
                "status": "success" if result["success"] else "error",
                "action": "generate_rag_embeddings",
                "model_name": model_name,
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
            
            if result["success"]:
                logger.info(f"Generated embeddings for {len(texts_list)} texts")
            else:
                logger.error(f"Failed to generate embeddings: {result.get('error')}")
            
            return json.dumps(response)
            
        except Exception as e:
            logger.error(f"Error generating RAG embeddings: {e}")
            return json.dumps({
                "status": "error",
                "action": "generate_rag_embeddings",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    logger.info("RAG tools registered successfully")