#!/usr/bin/env python3
"""
ChromaDB 基础向量数据库服务

提供内存级向量存储和检索功能，支持定期清理和会话管理。
"""

import uuid
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Timer

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from isa_model.client import ISAModelClient
    ISACLIENT_AVAILABLE = True
except ImportError:
    ISACLIENT_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ChromaCollection:
    """ChromaDB 集合信息"""
    name: str
    created_at: datetime
    last_accessed: datetime
    document_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class ChromaService:
    """
    ChromaDB 基础服务
    
    功能：
    - 内存级向量存储
    - 自动过期清理
    - 会话管理
    - 嵌入模型管理
    """
    
    def __init__(self, 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 cleanup_interval_minutes: int = 30,
                 collection_ttl_minutes: int = 120):
        """
        初始化 ChromaDB 服务
        
        Args:
            embedding_model: 嵌入模型名称
            cleanup_interval_minutes: 清理间隔（分钟）
            collection_ttl_minutes: 集合生存时间（分钟）
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB is required. Install with: pip install chromadb")
        
        self.cleanup_interval = cleanup_interval_minutes * 60  # 转换为秒
        self.collection_ttl = collection_ttl_minutes * 60  # 转换为秒
        self.collections: Dict[str, ChromaCollection] = {}
        
        # 初始化 ChromaDB 客户端（内存模式）
        self.chroma_client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=None  # 纯内存模式
        ))
        
        # 初始化嵌入模型 - 使用 ISA Client
        self.embedding_model_name = embedding_model
        self.use_openai_embedding = False
        self.use_sentence_transformers = False
        
        # 1. 优先使用 ISA Client embedding
        if ISACLIENT_AVAILABLE:
            try:
                self.isa_client = ISAModelClient()
                self.use_openai_embedding = True
                logger.info("ChromaService: Using ISA Model embedding")
            except Exception as e:
                logger.warning(f"ChromaService: Failed to load ISA Client: {e}")
        
        # 2. 后备使用 SentenceTransformers
        if not self.use_openai_embedding and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
                self.use_sentence_transformers = True
                logger.info(f"ChromaService: Using SentenceTransformers model: {embedding_model}")
            except Exception as e:
                logger.warning(f"ChromaService: Failed to load SentenceTransformers: {e}")
        
        # 3. 最后使用 ChromaDB 默认
        if not self.use_openai_embedding and not self.use_sentence_transformers:
            logger.info("ChromaService: Using ChromaDB default embeddings")
        
        # 启动定期清理
        self._start_cleanup_timer()
        
        logger.info(f"ChromaService initialized - cleanup every {cleanup_interval_minutes}min, TTL {collection_ttl_minutes}min")
    
    def create_collection(self, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        创建新的向量集合
        
        Args:
            name: 集合名称（可选，自动生成）
            metadata: 集合元数据
            
        Returns:
            集合名称
        """
        if name is None:
            name = f"collection_{uuid.uuid4().hex[:8]}"
        
        try:
            # 在 ChromaDB 中创建集合
            chroma_collection = self.chroma_client.create_collection(
                name=name,
                metadata=metadata or {}
            )
            
            # 记录集合信息
            collection_info = ChromaCollection(
                name=name,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                metadata=metadata or {}
            )
            
            self.collections[name] = collection_info
            
            logger.info(f"ChromaService: Created collection '{name}'")
            return name
            
        except Exception as e:
            logger.error(f"ChromaService: Failed to create collection '{name}': {e}")
            raise
    
    def get_collection(self, name: str):
        """获取 ChromaDB 集合对象"""
        if name in self.collections:
            # 更新访问时间
            self.collections[name].last_accessed = datetime.now()
            return self.chroma_client.get_collection(name)
        else:
            raise ValueError(f"Collection '{name}' not found")
    
    async def add_documents(self, collection_name: str, documents: List[str], 
                     ids: Optional[List[str]] = None, 
                     metadatas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        向集合添加文档
        
        Args:
            collection_name: 集合名称
            documents: 文档内容列表
            ids: 文档ID列表（可选）
            metadatas: 文档元数据列表（可选）
            
        Returns:
            添加结果
        """
        try:
            collection = self.get_collection(collection_name)
            
            # 生成ID（如果未提供）
            if ids is None:
                ids = [f"doc_{uuid.uuid4().hex[:8]}" for _ in documents]
            
            # 生成嵌入向量
            if self.use_openai_embedding:
                # 使用 OpenAI embedding service
                embeddings = []
                for doc in documents:
                    try:
                        result = await self.isa_client.invoke(
                            input_data=doc,
                            task="embed",
                            service_type="embedding"
                        )
                        
                        if result.get('success'):
                            embedding = result.get('result', [])
                        else:
                            raise Exception(f"Embedding failed: {result.get('error')}")
                        embeddings.append(embedding)
                    except Exception as e:
                        logger.error(f"OpenAI embedding failed for document: {e}")
                        # 使用零向量作为后备
                        embeddings.append([0.0] * 1536)  # OpenAI text-embedding-3-small 维度
                
                collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
            elif self.use_sentence_transformers:
                embeddings = self.embedding_model.encode(documents).tolist()
                collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
            else:
                collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
            
            # 更新文档计数
            self.collections[collection_name].document_count += len(documents)
            
            logger.debug(f"ChromaService: Added {len(documents)} documents to '{collection_name}'")
            
            return {
                "status": "success",
                "collection_name": collection_name,
                "documents_added": len(documents),
                "document_ids": ids
            }
            
        except Exception as e:
            logger.error(f"ChromaService: Failed to add documents to '{collection_name}': {e}")
            return {
                "status": "failed",
                "error": str(e),
                "collection_name": collection_name
            }
    
    async def query_collection(self, collection_name: str, query_texts: List[str], 
                        n_results: int = 3) -> Dict[str, Any]:
        """
        查询集合
        
        Args:
            collection_name: 集合名称
            query_texts: 查询文本列表
            n_results: 返回结果数量
            
        Returns:
            查询结果
        """
        try:
            collection = self.get_collection(collection_name)
            
            # 执行查询
            if self.use_openai_embedding:
                # 使用 OpenAI embedding 进行查询
                query_embeddings = []
                for query_text in query_texts:
                    try:
                        result = await self.isa_client.invoke(
                            input_data=query_text,
                            task="embed",
                            service_type="embedding"
                        )
                        
                        if result.get('success'):
                            embedding = result.get('result', [])
                        else:
                            raise Exception(f"Query embedding failed: {result.get('error')}")
                        query_embeddings.append(embedding)
                    except Exception as e:
                        logger.error(f"OpenAI embedding failed for query: {e}")
                        # 使用零向量作为后备
                        query_embeddings.append([0.0] * 1536)
                
                results = collection.query(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"]
                )
            elif self.use_sentence_transformers:
                query_embeddings = self.embedding_model.encode(query_texts).tolist()
                results = collection.query(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"]
                )
            else:
                results = collection.query(
                    query_texts=query_texts,
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"]
                )
            
            logger.debug(f"ChromaService: Queried '{collection_name}' with {len(query_texts)} queries")
            
            return {
                "status": "success",
                "collection_name": collection_name,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"ChromaService: Failed to query '{collection_name}': {e}")
            return {
                "status": "failed",
                "error": str(e),
                "collection_name": collection_name
            }
    
    def delete_collection(self, collection_name: str) -> bool:
        """删除集合"""
        try:
            if collection_name in self.collections:
                self.chroma_client.delete_collection(collection_name)
                del self.collections[collection_name]
                logger.info(f"ChromaService: Deleted collection '{collection_name}'")
                return True
            return False
        except Exception as e:
            logger.error(f"ChromaService: Failed to delete collection '{collection_name}': {e}")
            return False
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """列出所有集合"""
        collections_info = []
        for name, info in self.collections.items():
            collections_info.append({
                "name": name,
                "created_at": info.created_at.isoformat(),
                "last_accessed": info.last_accessed.isoformat(),
                "document_count": info.document_count,
                "metadata": info.metadata
            })
        return collections_info
    
    def cleanup_expired_collections(self) -> int:
        """清理过期的集合"""
        current_time = datetime.now()
        expired_collections = []
        
        for name, info in self.collections.items():
            time_since_access = (current_time - info.last_accessed).total_seconds()
            if time_since_access > self.collection_ttl:
                expired_collections.append(name)
        
        cleaned_count = 0
        for collection_name in expired_collections:
            if self.delete_collection(collection_name):
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"ChromaService: Cleaned up {cleaned_count} expired collections")
        
        return cleaned_count
    
    def _start_cleanup_timer(self):
        """启动定期清理定时器"""
        def cleanup_task():
            try:
                self.cleanup_expired_collections()
            except Exception as e:
                logger.error(f"ChromaService: Cleanup task failed: {e}")
            finally:
                # 重新启动定时器
                self._start_cleanup_timer()
        
        timer = Timer(self.cleanup_interval, cleanup_task)
        timer.daemon = True  # 守护线程，主程序退出时自动结束
        timer.start()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        total_documents = sum(info.document_count for info in self.collections.values())
        
        return {
            "total_collections": len(self.collections),
            "total_documents": total_documents,
            "embedding_model": self.embedding_model_name,
            "use_openai_embedding": self.use_openai_embedding,
            "use_sentence_transformers": self.use_sentence_transformers,
            "cleanup_interval_seconds": self.cleanup_interval,
            "collection_ttl_seconds": self.collection_ttl,
            "chromadb_available": CHROMADB_AVAILABLE,
            "isaclient_available": ISACLIENT_AVAILABLE,
            "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE
        }

# 全局服务实例
_chroma_service = None

def get_chroma_service() -> ChromaService:
    """获取全局 ChromaDB 服务实例"""
    global _chroma_service
    if _chroma_service is None:
        _chroma_service = ChromaService()
    return _chroma_service

def create_chroma_service(embedding_model: str = "all-MiniLM-L6-v2",
                         cleanup_interval_minutes: int = 30,
                         collection_ttl_minutes: int = 120) -> ChromaService:
    """创建新的 ChromaDB 服务实例"""
    global _chroma_service
    _chroma_service = ChromaService(
        embedding_model=embedding_model,
        cleanup_interval_minutes=cleanup_interval_minutes,
        collection_ttl_minutes=collection_ttl_minutes
    )
    return _chroma_service