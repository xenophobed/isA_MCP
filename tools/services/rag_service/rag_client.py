#!/usr/bin/env python
"""
RAG Client for MCP Server with Supabase pgvector
提供检索增强生成(RAG)功能的客户端实现，使用Supabase和pgvector
"""
import asyncio
import json
import os
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.logging import get_logger
from core.supabase_client import get_supabase_client
from isa_model.inference.ai_factory import AIFactory

logger = get_logger(__name__)

class RAGClient:
    """RAG客户端，用于处理文档存储、检索和生成，使用Supabase pgvector"""
    
    def __init__(self):
        """初始化RAG客户端"""
        self.supabase = get_supabase_client()
        self.ai_factory = AIFactory()
        self.embedding_service = self.ai_factory.get_embedding_service()
        
        # 确保数据库表存在
        asyncio.create_task(self._ensure_tables())
        logger.info("RAG Client initialized with Supabase pgvector")
    
    async def _ensure_tables(self):
        """确保RAG所需的数据库表存在"""
        try:
            # 检查表是否存在，如果不存在则创建
            # 这些表应该在Supabase中手动创建，这里只是验证
            await self.supabase.client.table('rag_documents').select('*').limit(1).execute()
            logger.info("RAG tables verified")
        except Exception as e:
            logger.warning(f"RAG tables may not exist: {e}")
            logger.info("Please create RAG tables in Supabase manually")
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        添加文档到向量数据库
        
        Args:
            documents: 文档数据列表，每个文档包含:
                - content: 文档内容
                - metadata: 元数据 (可选)
                - collection: 集合名称 (可选，默认为default)
                - source: 来源 (可选)
            
        Returns:
            操作结果
        """
        try:
            added_docs = []
            
            for doc in documents:
                content = doc.get("content", "")
                if not content:
                    continue
                    
                collection = doc.get("collection", "default")
                metadata = doc.get("metadata", {})
                source = doc.get("source", "")
                doc_id = doc.get("id", str(uuid.uuid4()))
                
                # 生成向量嵌入
                try:
                    embedding = await self.embedding_service.create_text_embedding(content)
                except Exception as e:
                    logger.error(f"Failed to generate embedding for document {doc_id}: {e}")
                    continue
                
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
                result = self.supabase.client.table('rag_documents').insert(doc_data).execute()
                
                if result.data:
                    added_docs.append(doc_id)
                    logger.info(f"Added document {doc_id} to collection {collection}")
            
            return {
                "success": True,
                "added_documents": added_docs,
                "message": f"Successfully added {len(added_docs)} documents"
            }
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_documents(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        搜索相似文档，使用pgvector进行向量相似度搜索
        
        Args:
            search_params: 搜索参数
                - query: 搜索查询文本
                - collection: 集合名称 (可选)
                - limit: 返回结果数量 (默认5)
                - threshold: 相似度阈值 (0-1，默认0.0)
                - search_type: 搜索类型 ("vector" 或 "text"，默认"vector")
            
        Returns:
            搜索结果
        """
        try:
            query = search_params.get("query", "")
            collection = search_params.get("collection")
            limit = search_params.get("limit", 5)
            threshold = search_params.get("threshold", 0.0)
            search_type = search_params.get("search_type", "vector")
            
            if not query:
                return {
                    "success": False,
                    "error": "Query cannot be empty"
                }
            
            if search_type == "vector":
                # 生成查询向量
                try:
                    query_embedding = await self.embedding_service.create_text_embedding(query)
                except Exception as e:
                    logger.error(f"Failed to generate query embedding: {e}")
                    return {
                        "success": False,
                        "error": f"Failed to generate query embedding: {e}"
                    }
                
                # 构建向量搜索查询
                # 使用pgvector的余弦相似度搜索
                query_builder = self.supabase.client.rpc(
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
                query_builder = self.supabase.client.table('rag_documents').select(
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
                
                logger.info(f"Found {len(matching_docs)} matching documents for query: {query}")
                
                return {
                    "success": True,
                    "documents": matching_docs,
                    "total_found": len(matching_docs),
                    "search_type": search_type
                }
            else:
                return {
                    "success": True,
                    "documents": [],
                    "total_found": 0,
                    "search_type": search_type
                }
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_documents(self, delete_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        删除文档
        
        Args:
            delete_params: 删除参数
                - document_ids: 文档ID列表 (可选)
                - collection_name: 集合名称 (可选，删除整个集合)
                - delete_all: 是否删除所有文档 (可选)
            
        Returns:
            删除结果
        """
        try:
            document_ids = delete_params.get("document_ids", [])
            collection_name = delete_params.get("collection_name")
            delete_all = delete_params.get("delete_all", False)
            
            deleted_count = 0
            
            if delete_all:
                # 删除所有文档
                result = self.supabase.client.table('rag_documents').delete().neq('id', '').execute()
                deleted_count = len(result.data) if result.data else 0
                logger.warning(f"Deleted all documents: {deleted_count}")
                
            elif collection_name:
                # 删除整个集合
                result = self.supabase.client.table('rag_documents').delete().eq('collection_name', collection_name).execute()
                deleted_count = len(result.data) if result.data else 0
                logger.info(f"Deleted collection {collection_name} with {deleted_count} documents")
                    
            elif document_ids:
                # 删除指定文档
                for doc_id in document_ids:
                    result = self.supabase.client.table('rag_documents').delete().eq('id', doc_id).execute()
                    if result.data:
                        deleted_count += 1
                        logger.info(f"Deleted document {doc_id}")
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "message": f"Successfully deleted {deleted_count} documents"
            }
            
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_collections(self, user_id: str = "default") -> Dict[str, Any]:
        """
        列出所有集合
        
        Args:
            user_id: 用户ID
            
        Returns:
            集合列表
        """
        try:
            # 获取所有不同的集合名称
            result = self.supabase.client.table('rag_documents').select('collection_name').execute()
            
            if not result.data:
                return {
                    "success": True,
                    "collections": [],
                    "total_collections": 0
                }
            
            # 统计每个集合的文档数量
            collections_info = {}
            for doc in result.data:
                collection_name = doc.get('collection_name', 'default')
                if collection_name not in collections_info:
                    collections_info[collection_name] = 0
                collections_info[collection_name] += 1
            
            collections_list = []
            for name, count in collections_info.items():
                collections_list.append({
                    "name": name,
                    "document_count": count,
                    "created_at": datetime.now().isoformat()
                })
            
            return {
                "success": True,
                "collections": collections_list,
                "total_collections": len(collections_list)
            }
            
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_collection_stats(self, collection_name: str, user_id: str = "default") -> Dict[str, Any]:
        """
        获取集合统计信息
        
        Args:
            collection_name: 集合名称
            user_id: 用户ID
            
        Returns:
            集合统计信息
        """
        try:
            result = self.supabase.client.table('rag_documents').select('content').eq('collection_name', collection_name).execute()
            
            if not result.data:
                return {
                    "success": False,
                    "error": f"Collection {collection_name} not found"
                }
            
            total_docs = len(result.data)
            total_chars = sum(len(doc.get('content', '')) for doc in result.data)
            
            return {
                "success": True,
                "stats": {
                    "collection_name": collection_name,
                    "document_count": total_docs,
                    "total_characters": total_chars,
                    "average_doc_length": total_chars / total_docs if total_docs > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_embeddings(self, texts: List[str], model_name: str = "default") -> Dict[str, Any]:
        """
        生成文本嵌入向量
        
        Args:
            texts: 文本列表
            model_name: 模型名称
            
        Returns:
            嵌入向量结果
        """
        try:
            embeddings = []
            
            for text in texts:
                try:
                    embedding = await self.embedding_service.create_text_embedding(text)
                    embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"Failed to generate embedding for text: {e}")
                    embeddings.append(None)
            
            return {
                "success": True,
                "embeddings": embeddings,
                "model_name": self.embedding_service.model_name,
                "dimension": len(embeddings[0]) if embeddings and embeddings[0] else 0
            }
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# 全局实例
_rag_client = None

def get_rag_client() -> RAGClient:
    """获取RAG客户端实例"""
    global _rag_client
    if _rag_client is None:
        _rag_client = RAGClient()
    return _rag_client