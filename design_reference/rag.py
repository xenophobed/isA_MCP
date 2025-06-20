#!/usr/bin/env python3
"""
MCP Server for RAG Pipeline with Vector Database
Provides resources for vector collections and tools for embedding/retrieval
"""

import json
import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence
from dataclasses import dataclass
import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    CallToolResult,
    ListResourcesResult,
    ListToolsResult,
    ReadResourceResult,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VectorDBConfig:
    """Configuration for vector database"""
    db_path: str = "./chroma_db"
    collection_name: str = "rag_documents"
    embedding_model: str = "all-MiniLM-L6-v2"
    dimension: int = 384

class RAGServer:
    """MCP Server for RAG pipeline operations"""
    
    def __init__(self, config: VectorDBConfig):
        self.config = config
        self.server = Server("rag-server")
        self.client = None
        self.collection = None
        self.embedding_model = None
        self._setup_handlers()
    
    async def initialize(self):
        """Initialize vector database and embedding model"""
        try:
            # Initialize ChromaDB
            self.client = chromadb.PersistentClient(
                path=self.config.db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(self.config.embedding_model)
            
            logger.info(f"Initialized RAG server with collection: {self.config.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG server: {e}")
            raise
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_resources()
        async def list_resources() -> ListResourcesResult:
            """List available vector database resources"""
            resources = []
            
            # Collection info resource
            resources.append(Resource(
                uri=f"vectordb://collections/{self.config.collection_name}",
                name=f"Collection: {self.config.collection_name}",
                description="Vector database collection information and statistics",
                mimeType="application/json"
            ))
            
            # Documents resource
            resources.append(Resource(
                uri=f"vectordb://documents/{self.config.collection_name}",
                name="Stored Documents",
                description="List of documents stored in the vector database",
                mimeType="application/json"
            ))
            
            return ListResourcesResult(resources=resources)
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> ReadResourceResult:
            """Read vector database resources"""
            
            if uri.startswith("vectordb://collections/"):
                collection_name = uri.split("/")[-1]
                if collection_name == self.config.collection_name:
                    count = self.collection.count()
                    metadata = self.collection.metadata
                    
                    info = {
                        "collection_name": collection_name,
                        "document_count": count,
                        "metadata": metadata,
                        "embedding_model": self.config.embedding_model,
                        "dimension": self.config.dimension
                    }
                    
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=json.dumps(info, indent=2)
                        )]
                    )
            
            elif uri.startswith("vectordb://documents/"):
                collection_name = uri.split("/")[-1]
                if collection_name == self.config.collection_name:
                    # Get all documents
                    results = self.collection.get(include=["documents", "metadatas", "ids"])
                    
                    documents = []
                    for i, doc_id in enumerate(results["ids"]):
                        doc_info = {
                            "id": doc_id,
                            "document": results["documents"][i][:200] + "..." if len(results["documents"][i]) > 200 else results["documents"][i],
                            "metadata": results["metadatas"][i] if results["metadatas"] else {}
                        }
                        documents.append(doc_info)
                    
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=json.dumps(documents, indent=2)
                        )]
                    )
            
            raise ValueError(f"Unknown resource URI: {uri}")
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available RAG tools"""
            tools = [
                Tool(
                    name="embed_text",
                    description="Generate embeddings for text using the configured model",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text to embed"},
                            "normalize": {"type": "boolean", "default": True, "description": "Whether to normalize embeddings"}
                        },
                        "required": ["text"]
                    }
                ),
                Tool(
                    name="add_documents",
                    description="Add documents to the vector database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "documents": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of documents to add"
                            },
                            "ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of document IDs"
                            },
                            "metadatas": {
                                "type": "array",
                                "items": {"type": "object"},
                                "description": "Optional list of metadata objects"
                            }
                        },
                        "required": ["documents"]
                    }
                ),
                Tool(
                    name="search_similar",
                    description="Search for similar documents in the vector database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query text"},
                            "n_results": {"type": "integer", "default": 5, "description": "Number of results to return"},
                            "where": {"type": "object", "description": "Optional metadata filter"},
                            "include_distances": {"type": "boolean", "default": True, "description": "Include similarity distances"}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="delete_documents",
                    description="Delete documents from the vector database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of document IDs to delete"
                            },
                            "where": {"type": "object", "description": "Optional metadata filter for deletion"}
                        }
                    }
                ),
                Tool(
                    name="rag_query",
                    description="Perform full RAG query: retrieve relevant documents and format for LLM",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "User query"},
                            "n_results": {"type": "integer", "default": 3, "description": "Number of documents to retrieve"},
                            "min_similarity": {"type": "number", "default": 0.0, "description": "Minimum similarity threshold"},
                            "include_sources": {"type": "boolean", "default": True, "description": "Include source information"}
                        },
                        "required": ["query"]
                    }
                )
            ]
            
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> CallToolResult:
            """Handle tool calls"""
            
            try:
                if name == "embed_text":
                    text = arguments["text"]
                    normalize = arguments.get("normalize", True)
                    
                    # Generate embedding
                    embedding = self.embedding_model.encode(text, normalize_embeddings=normalize)
                    
                    result = {
                        "embedding": embedding.tolist(),
                        "dimension": len(embedding),
                        "model": self.config.embedding_model
                    }
                    
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                    )
                
                elif name == "add_documents":
                    documents = arguments["documents"]
                    ids = arguments.get("ids")
                    metadatas = arguments.get("metadatas")
                    
                    # Generate IDs if not provided
                    if not ids:
                        ids = [f"doc_{i}_{hash(doc) % 10000}" for i, doc in enumerate(documents)]
                    
                    # Add documents to collection
                    self.collection.add(
                        documents=documents,
                        ids=ids,
                        metadatas=metadatas
                    )
                    
                    result = {
                        "added_count": len(documents),
                        "ids": ids,
                        "collection_size": self.collection.count()
                    }
                    
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                    )
                
                elif name == "search_similar":
                    query = arguments["query"]
                    n_results = arguments.get("n_results", 5)
                    where = arguments.get("where")
                    include_distances = arguments.get("include_distances", True)
                    
                    # Perform similarity search
                    include_list = ["documents", "metadatas", "ids"]
                    if include_distances:
                        include_list.append("distances")
                    
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=n_results,
                        where=where,
                        include=include_list
                    )
                    
                    # Format results
                    formatted_results = []
                    for i in range(len(results["ids"][0])):
                        doc_result = {
                            "id": results["ids"][0][i],
                            "document": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                        }
                        if include_distances:
                            doc_result["distance"] = results["distances"][0][i]
                            doc_result["similarity"] = 1 - results["distances"][0][i]
                        
                        formatted_results.append(doc_result)
                    
                    result = {
                        "query": query,
                        "results": formatted_results,
                        "total_found": len(formatted_results)
                    }
                    
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                    )
                
                elif name == "delete_documents":
                    ids = arguments.get("ids")
                    where = arguments.get("where")
                    
                    if ids:
                        self.collection.delete(ids=ids)
                        deleted_count = len(ids)
                    elif where:
                        # Delete by metadata filter
                        self.collection.delete(where=where)
                        deleted_count = "unknown"  # ChromaDB doesn't return count
                    else:
                        raise ValueError("Must provide either 'ids' or 'where' parameter")
                    
                    result = {
                        "deleted_count": deleted_count,
                        "collection_size": self.collection.count()
                    }
                    
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                    )
                
                elif name == "rag_query":
                    query = arguments["query"]
                    n_results = arguments.get("n_results", 3)
                    min_similarity = arguments.get("min_similarity", 0.0)
                    include_sources = arguments.get("include_sources", True)
                    
                    # Retrieve relevant documents
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=n_results,
                        include=["documents", "metadatas", "ids", "distances"]
                    )
                    
                    # Filter by similarity threshold
                    relevant_docs = []
                    for i in range(len(results["ids"][0])):
                        similarity = 1 - results["distances"][0][i]
                        if similarity >= min_similarity:
                            doc_info = {
                                "content": results["documents"][0][i],
                                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                                "id": results["ids"][0][i],
                                "similarity": similarity
                            }
                            relevant_docs.append(doc_info)
                    
                    # Format for RAG prompt
                    context = "\n\n".join([
                        f"Document {i+1}:\n{doc['content']}"
                        for i, doc in enumerate(relevant_docs)
                    ])
                    
                    sources = []
                    if include_sources:
                        sources = [
                            {
                                "id": doc["id"],
                                "similarity": doc["similarity"],
                                "metadata": doc["metadata"]
                            }
                            for doc in relevant_docs
                        ]
                    
                    result = {
                        "query": query,
                        "context": context,
                        "sources": sources,
                        "retrieved_count": len(relevant_docs),
                        "rag_prompt": f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer based on the provided context:"
                    }
                    
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                    )
                
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )

async def main():
    """Main entry point"""
    config = VectorDBConfig()
    rag_server = RAGServer(config)
    
    # Initialize the server
    await rag_server.initialize()
    
    # Run the MCP server
    async with stdio_server() as (read_stream, write_stream):
        await rag_server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="rag-server",
                server_version="1.0.0",
                capabilities=rag_server.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())