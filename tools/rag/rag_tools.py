#!/usr/bin/env python
"""
RAG Tools for MCP Server
提供检索增强生成(RAG)功能的工具集
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from tools.services.rag_client import RAGClient

logger = get_logger(__name__)

def register_rag_tools(mcp):
    """注册 RAG 工具集"""
    
    # Get security manager
    security_manager = get_security_manager()
    
    # Initialize RAG client
    try:
        rag_client = RAGClient()
        logger.info("RAG client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG client: {e}")
        rag_client = None
    
    # ====== 文档管理工具 ======
    
    @mcp.tool()
    @security_manager.security_check
    async def add_documents(
        documents: List[str],
        collection_name: str = "default",
        document_ids: List[str] = None,
        metadata: List[dict] = None,
        user_id: str = "default"
    ) -> str:
        """
        添加文档到向量数据库
        
        Args:
            documents: 文档内容列表
            collection_name: 集合名称
            document_ids: 文档ID列表（可选）
            metadata: 文档元数据列表（可选）
            user_id: 用户ID
        """
        if not rag_client:
            return json.dumps({"status": "error", "message": "RAG service unavailable"})
        
        try:
            # 验证输入
            if not documents:
                return json.dumps({"status": "error", "message": "No documents provided"})
            
            # 准备文档数据
            doc_data = []
            for i, doc in enumerate(documents):
                doc_item = {
                    "content": doc,
                    "collection": collection_name,
                    "user_id": user_id,
                    "created_at": datetime.now().isoformat()
                }
                
                # 添加自定义ID
                if document_ids and i < len(document_ids):
                    doc_item["id"] = document_ids[i]
                else:
                    doc_item["id"] = f"doc_{collection_name}_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # 添加元数据
                if metadata and i < len(metadata):
                    doc_item["metadata"] = metadata[i]
                else:
                    doc_item["metadata"] = {}
                
                doc_data.append(doc_item)
            
            # 添加到向量数据库
            result = await rag_client.add_documents(doc_data)
            
            if result.get("success"):
                return json.dumps({
                    "status": "success",
                    "data": {
                        "message": f"Successfully added {len(doc_data)} documents",
                        "collection": collection_name,
                        "document_count": len(doc_data),
                        "document_ids": [doc["id"] for doc in doc_data]
                    },
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": result.get("error", "Failed to add documents")
                })
                
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.tool()
    @security_manager.security_check
    async def search_documents(
        query: str,
        collection_name: str = "default",
        limit: int = 5,
        similarity_threshold: float = 0.0,
        include_metadata: bool = True,
        user_id: str = "default"
    ) -> str:
        """
        搜索相似文档
        
        Args:
            query: 搜索查询
            collection_name: 集合名称
            limit: 返回结果数量
            similarity_threshold: 相似度阈值
            include_metadata: 是否包含元数据
            user_id: 用户ID
        """
        if not rag_client:
            return json.dumps({"status": "error", "message": "RAG service unavailable"})
        
        try:
            search_params = {
                "query": query,
                "collection": collection_name,
                "limit": limit,
                "threshold": similarity_threshold,
                "user_id": user_id
            }
            
            result = await rag_client.search_documents(search_params)
            
            if result.get("success"):
                documents = []
                for doc in result.get("documents", []):
                    doc_result = {
                        "id": doc.get("id"),
                        "content": doc.get("content"),
                        "similarity_score": doc.get("score", 0.0)
                    }
                    
                    if include_metadata:
                        doc_result["metadata"] = doc.get("metadata", {})
                    
                    documents.append(doc_result)
                
                return json.dumps({
                    "status": "success",
                    "data": {
                        "query": query,
                        "documents": documents,
                        "total_found": len(documents),
                        "collection": collection_name,
                        "search_params": {
                            "limit": limit,
                            "threshold": similarity_threshold
                        }
                    },
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": result.get("error", "Search failed")
                })
                
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.tool()
    @security_manager.security_check
    async def delete_documents(
        document_ids: List[str] = None,
        collection_name: str = None,
        delete_all: bool = False,
        user_id: str = "default"
    ) -> str:
        """
        删除文档
        
        Args:
            document_ids: 要删除的文档ID列表
            collection_name: 要删除的集合名称（删除整个集合）
            delete_all: 是否删除所有文档（危险操作）
            user_id: 用户ID
        """
        if not rag_client:
            return json.dumps({"status": "error", "message": "RAG service unavailable"})
        
        try:
            if delete_all:
                # 删除所有文档 - 需要特殊授权
                result = await rag_client.delete_all_documents(user_id)
                operation = "delete_all"
            elif collection_name:
                # 删除整个集合
                result = await rag_client.delete_collection(collection_name, user_id)
                operation = f"delete_collection_{collection_name}"
            elif document_ids:
                # 删除指定文档
                result = await rag_client.delete_documents_by_ids(document_ids, user_id)
                operation = f"delete_documents_{len(document_ids)}"
            else:
                return json.dumps({
                    "status": "error",
                    "message": "Must specify document_ids, collection_name, or delete_all=True"
                })
            
            if result.get("success"):
                return json.dumps({
                    "status": "success",
                    "data": {
                        "message": f"Successfully completed {operation}",
                        "deleted_count": result.get("deleted_count", 0),
                        "operation": operation
                    },
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": result.get("error", "Delete operation failed")
                })
                
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    # ====== RAG 查询工具 ======
    
    @mcp.tool()
    @security_manager.security_check
    async def rag_query(
        question: str,
        collection_name: str = "default",
        max_documents: int = 3,
        similarity_threshold: float = 0.1,
        include_sources: bool = True,
        user_id: str = "default"
    ) -> str:
        """
        执行 RAG 查询（检索+生成）
        
        Args:
            question: 用户问题
            collection_name: 搜索的集合
            max_documents: 最大检索文档数
            similarity_threshold: 相似度阈值
            include_sources: 是否包含源文档
            user_id: 用户ID
        """
        if not rag_client:
            return json.dumps({"status": "error", "message": "RAG service unavailable"})
        
        try:
            # 1. 检索相关文档
            search_params = {
                "query": question,
                "collection": collection_name,
                "limit": max_documents,
                "threshold": similarity_threshold,
                "user_id": user_id
            }
            
            search_result = await rag_client.search_documents(search_params)
            
            if not search_result.get("success"):
                return json.dumps({
                    "status": "error",
                    "message": "Failed to retrieve documents"
                })
            
            retrieved_docs = search_result.get("documents", [])
            
            if not retrieved_docs:
                return json.dumps({
                    "status": "success",
                    "data": {
                        "question": question,
                        "answer": "I couldn't find any relevant documents to answer your question.",
                        "sources": [],
                        "retrieved_count": 0
                    }
                })
            
            # 2. 生成回答
            context_text = "\n\n".join([doc.get("content", "") for doc in retrieved_docs])
            
            generation_params = {
                "question": question,
                "context": context_text,
                "max_length": 500
            }
            
            generation_result = await rag_client.generate_answer(generation_params)
            
            if generation_result.get("success"):
                response_data = {
                    "question": question,
                    "answer": generation_result.get("answer", ""),
                    "retrieved_count": len(retrieved_docs),
                    "collection": collection_name
                }
                
                if include_sources:
                    response_data["sources"] = [
                        {
                            "id": doc.get("id"),
                            "content": doc.get("content", "")[:200] + "..." if len(doc.get("content", "")) > 200 else doc.get("content", ""),
                            "similarity_score": doc.get("score", 0.0),
                            "metadata": doc.get("metadata", {})
                        }
                        for doc in retrieved_docs
                    ]
                
                return json.dumps({
                    "status": "success",
                    "data": response_data,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": "Failed to generate answer"
                })
                
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    # ====== 集合管理工具 ======
    
    @mcp.tool()
    @security_manager.security_check
    async def list_collections(user_id: str = "default") -> str:
        """
        列出所有文档集合
        
        Args:
            user_id: 用户ID
        """
        if not rag_client:
            return json.dumps({"status": "error", "message": "RAG service unavailable"})
        
        try:
            result = await rag_client.list_collections(user_id)
            
            if result.get("success"):
                collections = []
                for collection in result.get("collections", []):
                    collections.append({
                        "name": collection.get("name"),
                        "document_count": collection.get("document_count", 0),
                        "created_at": collection.get("created_at"),
                        "last_updated": collection.get("last_updated")
                    })
                
                return json.dumps({
                    "status": "success",
                    "data": {
                        "collections": collections,
                        "total_collections": len(collections)
                    },
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": result.get("error", "Failed to list collections")
                })
                
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    @mcp.tool()
    @security_manager.security_check
    async def get_collection_stats(
        collection_name: str,
        user_id: str = "default"
    ) -> str:
        """
        获取集合统计信息
        
        Args:
            collection_name: 集合名称
            user_id: 用户ID
        """
        if not rag_client:
            return json.dumps({"status": "error", "message": "RAG service unavailable"})
        
        try:
            result = await rag_client.get_collection_stats(collection_name, user_id)
            
            if result.get("success"):
                stats = result.get("stats", {})
                
                return json.dumps({
                    "status": "success",
                    "data": {
                        "collection_name": collection_name,
                        "document_count": stats.get("document_count", 0),
                        "total_tokens": stats.get("total_tokens", 0),
                        "average_document_length": stats.get("avg_doc_length", 0),
                        "created_at": stats.get("created_at"),
                        "last_updated": stats.get("last_updated"),
                        "embedding_model": stats.get("embedding_model", "unknown")
                    },
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": result.get("error", "Collection not found")
                })
                
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    # ====== 嵌入工具 ======
    
    @mcp.tool()
    @security_manager.security_check
    async def generate_embeddings(
        texts: List[str],
        model_name: str = "default",
        normalize: bool = True,
        user_id: str = "default"
    ) -> str:
        """
        生成文本嵌入向量
        
        Args:
            texts: 文本列表
            model_name: 嵌入模型名称
            normalize: 是否标准化向量
            user_id: 用户ID
        """
        if not rag_client:
            return json.dumps({"status": "error", "message": "RAG service unavailable"})
        
        try:
            result = await rag_client.generate_embeddings(texts, model_name, normalize)
            
            if result.get("success"):
                embeddings = result.get("embeddings", [])
                
                return json.dumps({
                    "status": "success",
                    "data": {
                        "embeddings": embeddings,
                        "model_name": result.get("model_name"),
                        "dimension": result.get("dimension"),
                        "text_count": len(texts),
                        "normalized": normalize
                    },
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": result.get("error", "Failed to generate embeddings")
                })
                
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    logger.info("RAG tools registered successfully")