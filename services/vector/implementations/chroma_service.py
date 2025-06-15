from typing import List, Dict, Any
from chromadb import Client as ChromaClient
import numpy as np
import logging
import uuid
from ..base_vector_service import BaseVectorService
from app.config.vector.chroma_config import ChromaConfig
from app.services.ai.models.ai_factory import AIFactory

logger = logging.getLogger(__name__)

class ChromaService(BaseVectorService):
    """ChromaDB vector database service wrapper"""
    
    def __init__(self, client: ChromaClient, config: ChromaConfig):
        self.client = client
        self.config = config
        self._collection = None
        self._embed_service = None
        self._vector_size = config.settings.vector_size

    async def _get_embed_service(self):
        """获取嵌入服务"""
        if not self._embed_service:
            ai_factory = AIFactory.get_instance()
            self._embed_service = ai_factory.get_embedding(
                model_name="bge-m3",
                provider="ollama"
            )
        return self._embed_service

    def _validate_collection_name(self, name: str) -> None:
        """Validate collection name"""
        if not name or not isinstance(name, str):
            raise ValueError("Collection name must be a non-empty string")
        if len(name.strip()) == 0:
            raise ValueError("Collection name cannot be empty or whitespace")

    def _validate_vector(self, vector: List[float]) -> None:
        """Validate vector dimensions"""
        if not isinstance(vector, list):
            raise ValueError("Vector must be a list of float values")
        if len(vector) != self._vector_size:
            raise ValueError(f"Vector dimension mismatch. Expected {self._vector_size}, got {len(vector)}")

    @property
    def collection(self):
        """Lazy load collection"""
        if self._collection is None:
            vector_settings = self.config.get_vector_settings()
            self._collection = self.client.get_or_create_collection(
                name=vector_settings['collection_name'],
                metadata={
                    "hnsw:space": vector_settings['distance_func'],
                    "dimension": vector_settings['vector_size']
                }
            )
        return self._collection

    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            self._validate_collection_name(collection_name)
            collection = self.client.get_collection(name=collection_name)
            
            return {
                "count": collection.count(),
                "dimension": collection.metadata.get("dimension", self._vector_size),
                "distance": collection.metadata.get("hnsw:space", "cosine")
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                "count": 0,
                "dimension": self._vector_size,
                "distance": "cosine"
            }

    async def collection_exists(self, name: str) -> bool:
        """检查集合是否存在"""
        try:
            self._validate_collection_name(name)
            collections = self.client.list_collections()
            return name in collections
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False

    async def create_collection(self, name: str) -> Any:
        """创建集合"""
        self._validate_collection_name(name)
        
        try:
            # Check if collection exists first
            if await self.collection_exists(name):
                logger.info(f"Collection {name} already exists, returning existing collection")
                return self.client.get_collection(name=name)
                
            # Create new collection if it doesn't exist
            vector_settings = self.config.get_vector_settings()
            return self.client.create_collection(
                name=name,
                metadata={
                    "hnsw:space": vector_settings['distance_func'],
                    "dimension": vector_settings['vector_size']
                }
            )
        except Exception as e:
            logger.error(f"Error creating collection {name}: {e}")
            raise

    async def delete_collection(self, name: str) -> bool:
        """删除集合"""
        try:
            self._validate_collection_name(name)
            self.client.delete_collection(name=name)
            if name == self.config.settings.collection_name:
                self._collection = None
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            return False

    async def upsert_points(self, points: List[Dict[str, Any]]) -> bool:
        try:
            if not points:
                raise ValueError("Points list cannot be empty")
                
            embed_service = await self._get_embed_service()
            
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for point in points:
                if not isinstance(point, dict) or "text" not in point:
                    raise ValueError("Each point must be a dictionary containing 'text' field")
                
                # 创建嵌入向量
                vector = await embed_service.create_text_embedding(point["text"])
                self._validate_vector(vector)
                
                # 准备数据
                ids.append(str(point.get("id", uuid.uuid4())))
                embeddings.append(vector)
                documents.append(point["text"])
                metadatas.append(point.get("metadata", {}))
            
            # 批量插入
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            return True
            
        except Exception as e:
            logger.error(f"Error upserting points: {e}")
            return False

    async def search(self, query: List[float] = None, limit: int = 10, 
                    filters: Dict = None, collection_name: str = None,
                    query_embedding: List[float] = None,
                    score_threshold: float = None) -> List[Dict]:
        try:
            # Use query_embedding if provided, otherwise use query
            search_vector = query_embedding if query_embedding is not None else query
            
            # Validate input
            if search_vector is None:
                raise ValueError("Either query or query_embedding must be provided")
            self._validate_vector(search_vector)
            
            if limit < 1:
                raise ValueError("Limit must be a positive integer")
            
            # Get the correct collection
            if collection_name:
                collection = self.client.get_collection(name=collection_name)
            else:
                collection = self.collection
            
            # 执行搜索
            results = collection.query(
                query_embeddings=[search_vector],
                n_results=limit,
                where=filters
            )
            
            # 格式化结果
            formatted_results = []
            if results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    score = float(results['distances'][0][i])
                    # 如果设置了分数阈值，跳过低于阈值的结果
                    if score_threshold is not None and score < score_threshold:
                        continue
                    result = {
                        "id": results['ids'][0][i],
                        "score": score,
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i] or {}
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except ValueError as e:
            # Re-raise ValueError for validation errors
            raise e
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []

    async def close(self):
        """关闭连接和清理资源"""
        try:
            if self._embed_service:
                await self._embed_service.close()
            if hasattr(self.client, 'close'):
                await self.client.close()
        except Exception as e:
            logger.error(f"Error closing ChromaDB service: {e}") 