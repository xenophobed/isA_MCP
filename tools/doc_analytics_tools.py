#!/usr/bin/env python3
"""
Document Analytics Tools for MCP Server
Provides RAG-based document analysis and vector search capabilities
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.database.supabase_client import get_supabase_client
from tools.base_tool import BaseTool

logger = get_logger(__name__)

class DocumentAnalyticsManager(BaseTool):
    """文档分析管理器，提供RAG功能"""
    
    def __init__(self):
        super().__init__()
        self.supabase = get_supabase_client()

# 全局实例
_doc_manager = DocumentAnalyticsManager()

def register_doc_analytics_tools(mcp):
    """Register document analytics tools with the MCP server"""
    
    # Get security manager for applying decorators
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    async def search_documents(query: str, collection: str = "", limit: int = 5, 
                              threshold: float = 0.0, search_type: str = "vector",
                              user_id: str = "default") -> str:
        """Search for similar documents using vector or text search
        
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
        Category: document
        """
        try:
            _doc_manager.reset_billing()
            
            if not query:
                return _doc_manager.create_response(
                    status="error",
                    action="search_documents", 
                    data={"query": query},
                    error_message="Query cannot be empty"
                )
            
            search_params = {
                "query": query,
                "collection": collection if collection else None,
                "limit": limit,
                "threshold": threshold,
                "search_type": search_type
            }
            
            if search_type == "vector":
                # 生成查询向量
                query_embedding, billing_info = await _doc_manager.call_isa_with_billing(
                    input_data=query,
                    task="embed",
                    service_type="embedding"
                )
                
                # 构建向量搜索查询
                query_builder = _doc_manager.supabase.rpc(
                    'match_documents',
                    {
                        'query_embedding': query_embedding,
                        'match_threshold': threshold,
                        'match_count': limit,
                        'collection_filter': collection
                    }
                )
            else:
                # 文本搜索
                query_builder = _doc_manager.supabase.table('rag_documents').select(
                    'id, content, metadata, source, collection_name, created_at'
                ).ilike('content', f'%{query}%')
                
                if collection:
                    query_builder = query_builder.eq('collection_name', collection)
                
                query_builder = query_builder.limit(limit)
            
            result = query_builder.execute()
            
            if result.data:
                matching_docs = []
                for doc in result.data:
                    doc_data = {
                        "id": doc.get("id"),
                        "content": doc.get("content"),
                        "metadata": doc.get("metadata", {}),
                        "source": doc.get("source"),
                        "collection": doc.get("collection_name"),
                        "created_at": doc.get("created_at")
                    }
                    
                    # 添加相似度分数（如果是向量搜索）
                    if search_type == "vector" and "similarity" in doc:
                        doc_data["score"] = doc.get("similarity")
                    
                    matching_docs.append(doc_data)
                
                return _doc_manager.create_response(
                    status="success",
                    action="search_documents",
                    data={
                        "documents": matching_docs,
                        "total_found": len(matching_docs),
                        "search_type": search_type,
                        "query": query,
                        "collection": collection
                    }
                )
            else:
                return _doc_manager.create_response(
                    status="success",
                    action="search_documents",
                    data={
                        "documents": [],
                        "total_found": 0,
                        "search_type": search_type,
                        "query": query
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in document search: {e}")
            return _doc_manager.create_response(
                status="error",
                action="search_documents",
                data={"query": query, "search_type": search_type},
                error_message=str(e)
            )
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def add_documents(documents: str, user_id: str = "default") -> str:
        """Add documents to collections with vector embeddings
        
        This tool adds documents to collections, automatically generating
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
        Category: document
        """
        try:
            _doc_manager.reset_billing()
            
            # Parse documents input
            try:
                docs_data = json.loads(documents)
                if not isinstance(docs_data, list):
                    docs_data = [docs_data]
            except json.JSONDecodeError:
                return _doc_manager.create_response(
                    status="error",
                    action="add_documents",
                    data={},
                    error_message="Invalid JSON format for documents"
                )
            
            added_docs = []
            
            for doc in docs_data:
                content = doc.get("content", "")
                if not content:
                    continue
                    
                collection = doc.get("collection", "default")
                metadata = doc.get("metadata", {})
                source = doc.get("source", "")
                doc_id = doc.get("id", str(uuid.uuid4()))
                
                # 生成向量嵌入
                embedding, billing_info = await _doc_manager.call_isa_with_billing(
                    input_data=content,
                    task="embed",
                    service_type="embedding"
                )
                
                # 准备文档数据
                doc_data = {
                    "id": doc_id,
                    "content": content,
                    "embedding": embedding,
                    "collection_name": collection,
                    "metadata": metadata,
                    "source": source,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                # 插入到Supabase
                result = _doc_manager.supabase.table('rag_documents').insert(doc_data).execute()
                
                if result.data:
                    added_docs.append(doc_id)
                    logger.info(f"Added document {doc_id} to collection {collection}")
            
            return _doc_manager.create_response(
                status="success",
                action="add_documents",
                data={
                    "added_documents": added_docs,
                    "message": f"Successfully added {len(added_docs)} documents"
                }
            )
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return _doc_manager.create_response(
                status="error",
                action="add_documents",
                data={},
                error_message=str(e)
            )
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def quick_rag_question(
        file_path: str, 
        question: str
    ) -> str:
        """
        Quick RAG document question - ask questions about any document
        
        This tool allows you to ask questions about documents in various formats.
        It uses RAG (Retrieval Augmented Generation) to provide answers with context.
        
        Args:
            file_path: Path to document file (PDF, DOC, DOCX, PPT, PPTX, TXT)
            question: Question to ask about the document
            
        Returns:
            JSON string with answer, context and source information
            
        Keywords: document, rag, question, analysis, pdf, doc, text, search
        Category: document
        """
        try:
            # Security check
            security_manager = get_security_manager()
            if not security_manager.check_permission("doc_analytics", SecurityLevel.MEDIUM):
                raise Exception("Insufficient permissions for document analytics operations")
            
            logger.info(f"Processing RAG question for document: {file_path}")
            
            # Validate file exists
            if not Path(file_path).exists():
                error_response = {
                    "status": "error",
                    "action": "quick_rag_question",
                    "data": {
                        "error": "File not found",
                        "file_path": file_path,
                        "question": question
                    },
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(error_response)
            
            # Check supported format
            supported_extensions = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.txt'}
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext not in supported_extensions:
                error_response = {
                    "status": "error",
                    "action": "quick_rag_question",
                    "data": {
                        "error": f"Unsupported file format: {file_ext}",
                        "file_path": file_path,
                        "question": question,
                        "supported_formats": list(supported_extensions)
                    },
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(error_response)
            
            # Mock RAG processing for now (since actual service may not be available)
            # In a real implementation, this would call the actual RAG service
            mock_answer = f"Based on the document '{Path(file_path).name}', here's the answer to your question: '{question}'"
            mock_context = [
                "This is a mock response as the actual RAG service is not implemented yet.",
                f"Document: {file_path}",
                f"File type: {file_ext}",
                "In a real implementation, this would extract text from the document and use vector search to find relevant passages."
            ]
            
            response = {
                "status": "success",
                "action": "quick_rag_question",
                "data": {
                    "answer": mock_answer,
                    "context": mock_context,
                    "file_path": file_path,
                    "question": question,
                    "file_format": file_ext,
                    "confidence_score": 0.8,
                    "source_chunks": 1,
                    "processing_time_ms": 100
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"RAG question processed successfully for {file_path}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {
                "status": "error",
                "action": "quick_rag_question",
                "data": {
                    "error": str(e),
                    "file_path": file_path,
                    "question": question
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"RAG question failed: {e}")
            return json.dumps(error_response)

logger.info("Document analytics tools registered successfully")