from typing import Dict, Any, List, Optional
from datetime import datetime
from app.config.config_manager import config_manager
from app.services.db.graph.neo4j.service import Neo4jService
from app.services.db.graph.neo4j.queries.conv_queries import ConversationQueries
from app.services.db.vector.vector_factory import VectorFactory
from app.services.ai.models.ai_factory import AIFactory
from app.config.vector.chroma_config import ChromaConfig
import logging
import asyncio

logger = logging.getLogger(__name__)

class ConversationGraphManager:
    """Manages conversation knowledge graph in Neo4j and vector store"""
    
    def __init__(self):
        self.neo4j_service = None
        self.vector_service = None
        self.embed_service = None
        self.collection_name = "conv_reference"
        self.queries = ConversationQueries()
        self._initialized = False
        
    @property
    def gds_available(self) -> bool:
        """Check if GDS is available from Neo4j service"""
        return self.neo4j_service.gds_available if self.neo4j_service else False
        
    async def initialize(self):
        """Initialize services"""
        if self._initialized:
            return
            
        try:
            # Initialize Neo4j service
            neo4j_config = config_manager.get_config('neo4j')
            conn_params = neo4j_config.get_connection_params()
            
            self.neo4j_service = Neo4jService(
                uri=conn_params['uri'],
                user=conn_params['user'],
                password=conn_params['password']
            )
            await self.neo4j_service.initialize()
            
            # Initialize vector service with ChromaConfig
            vector_config = ChromaConfig()
            # Override settings for conversation vectors
            vector_config.settings.collection_name = self.collection_name
            vector_config.settings.vector_size = 1024  # bge-m3 model outputs 1024-dimensional vectors
            vector_config.settings.distance_type = "cosine"
            
            vector_factory = VectorFactory.get_instance()
            vector_factory.set_config(vector_config)
            self.vector_service = await vector_factory.get_vector("chroma")
            
            # Initialize embedding service
            ai_factory = AIFactory.get_instance()
            self.embed_service = ai_factory.get_embedding(
                model_name="bge-m3",
                provider="ollama"
            )
            
            # Validate services have required methods with detailed error messages
            for service_name, service in [
                ("Vector service", self.vector_service),
                ("Embedding service", self.embed_service)
            ]:
                if not hasattr(service, 'close'):
                    raise ValueError(f"{service_name} must implement close() method")
                if not callable(service.close):
                    raise ValueError(f"{service_name} close() method must be callable")
                if not asyncio.iscoroutinefunction(service.close):
                    raise ValueError(f"{service_name} close() method must be async")
            
            self._initialized = True
            logger.info("ConversationGraphManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise
            
    async def cleanup(self):
        """Cleanup resources"""
        cleanup_errors = []
        
        # Cleanup Neo4j service
        if self.neo4j_service:
            try:
                await self.neo4j_service.close()
            except Exception as e:
                cleanup_errors.append(f"Neo4j cleanup error: {str(e)}")
        
        # Cleanup vector service
        if self.vector_service:
            try:
                if hasattr(self.vector_service, 'close'):
                    if asyncio.iscoroutinefunction(self.vector_service.close):
                        await self.vector_service.close()
                    else:
                        logger.warning("Vector service close() method is not async, falling back to sync")
                        await asyncio.get_event_loop().run_in_executor(None, self.vector_service.close)
                else:
                    logger.warning("Vector service doesn't have close() method")
            except Exception as e:
                cleanup_errors.append(f"Vector service cleanup error: {str(e)}")
        
        # Cleanup embedding service
        if self.embed_service:
            try:
                if hasattr(self.embed_service, 'close'):
                    if asyncio.iscoroutinefunction(self.embed_service.close):
                        await self.embed_service.close()
                    else:
                        logger.warning("Embed service close() method is not async, falling back to sync")
                        await asyncio.get_event_loop().run_in_executor(None, self.embed_service.close)
                else:
                    logger.warning("Embed service doesn't have close() method")
            except Exception as e:
                cleanup_errors.append(f"Embedding service cleanup error: {str(e)}")
        
        if cleanup_errors:
            error_msg = "; ".join(cleanup_errors)
            logger.error(f"Errors during cleanup: {error_msg}")
            raise Exception(error_msg)
            
    async def sync_entity_vectors(self, entities: List[Dict]):
        """同步实体向量到图数据库"""
        try:
            for entity in entities:
                await self.neo4j_service.query(
                    self.queries.CREATE_ENTITY,
                    {
                        "entity_id": entity["id"],
                        "content": entity["content"],
                        "vector": entity["vector"]
                    }
                )
        except Exception as e:
            logger.error(f"Error syncing entity vectors: {e}")
            raise
            
    async def sync_fact_with_entities(self, fact: Dict, related_entities: List[str]):
        """同步事实及其关联实体，并计算置信度"""
        try:
            # Generate vector for fact if not provided
            if "vector" not in fact:
                fact_vector = await self.embed_service.create_text_embedding(fact["content"])
            else:
                fact_vector = fact["vector"]
                
            # 1. 先存储fact(初始置信度0.5)
            await self.neo4j_service.query(
                self.queries.CREATE_FACT,
                {
                    "fact_id": fact["id"],
                    "content": fact["content"],
                    "confidence": 0.5,  # 初始置信度为0.5
                    "timestamp": fact["timestamp"],
                    "vector": fact_vector
                }
            )
            
            # 2. 建立关系后计算新的置信度
            confidence = await self._calculate_fact_confidence(fact["id"])
            await self._update_fact_confidence(fact["id"], confidence)
            
        except Exception as e:
            logger.error(f"Error syncing fact: {e}")
            raise
            
    async def search_similar_entities(self, query_vector: List[float], min_similarity: float = 0.7):
        """基于向量相似度搜索实体"""
        try:
            results = await self.neo4j_service.query(
                self.queries.SEARCH_SIMILAR_ENTITIES,
                {
                    "query_vector": query_vector,
                    "min_similarity": min_similarity,
                    "limit": 5
                }
            )
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar entities: {e}")
            raise
            
    async def _calculate_fact_confidence(self, fact_id: str) -> float:
        """计算fact的置信度 - 基于相似facts数量和相似度"""
        try:
            # 1. 获取当前fact的向量
            fact = await self.neo4j_service.query(
                """
                MATCH (f:Fact {fact_id: $fact_id})
                RETURN f.vector as vector, f.content as content
                """,
                {"fact_id": fact_id}
            )
            
            if not fact or not fact[0].get("vector"):
                return 0.1  # 无向量时的低置信度
                
            # 2. 搜索相似facts (提高相似度阈值到0.85)
            if self.gds_available:
                similar_facts = await self.neo4j_service.query(
                    """
                    MATCH (f:Fact)
                    WHERE f.fact_id <> $fact_id AND f.vector IS NOT NULL
                    WITH f, gds.similarity.cosine($vector, f.vector) AS similarity
                    WHERE similarity > 0.85  
                    RETURN f.content as content, similarity
                    ORDER BY similarity DESC
                    LIMIT 5
                    """,
                    {
                        "fact_id": fact_id,
                        "vector": fact[0]["vector"]
                    }
                )
            else:
                similar_facts = await self.neo4j_service.query(
                    """
                    MATCH (f:Fact)
                    WHERE f.fact_id <> $fact_id AND f.vector IS NOT NULL
                    WITH f,
                         $vector as qvec,
                         [x IN f.vector | toFloat(x)] as fvec
                    WHERE size(fvec) = size(qvec)
                    WITH f,
                         reduce(dot = 0.0, i IN range(0, size(fvec)-1) | 
                             dot + fvec[i] * qvec[i]
                         ) / (
                             sqrt(reduce(norm1 = 0.0, i IN range(0, size(fvec)-1) | 
                                 norm1 + fvec[i] * fvec[i]
                             )) * 
                             sqrt(reduce(norm2 = 0.0, i IN range(0, size(qvec)-1) | 
                                 norm2 + qvec[i] * qvec[i]
                             ))
                         ) AS similarity
                    WHERE similarity > 0.85
                    RETURN f.content as content, similarity
                    ORDER BY similarity DESC
                    LIMIT 5
                    """,
                    {
                        "fact_id": fact_id,
                        "vector": fact[0]["vector"]
                    }
                )
            
            if not similar_facts:
                return 0.1  # 无相似节点时的低置信度
                
            # 3. 计算置信度
            # 3.1 基于相似节点数量: 0.05-0.2分 (降低数量分数)
            count_score = min(len(similar_facts) * 0.05, 0.2)
            
            # 3.2 基于相似度: 0-0.3分 (降低相似度分数)
            similarity_scores = [record["similarity"] for record in similar_facts]
            avg_similarity = sum(similarity_scores) / len(similarity_scores)
            similarity_score = avg_similarity * 0.3
            
            # 3.3 基于时间衰减: 0-0.2分 (新增时间因素)
            current_time = datetime.now()
            fact_time = datetime.fromisoformat(fact[0].get("timestamp", current_time.isoformat()))
            time_diff = (current_time - fact_time).days
            time_score = 0.2 * (1 - min(time_diff / 30, 1))  # 30天内逐渐增长
            
            # 3.4 最终置信度 = 初始置信度(0.2) + 数量分数 + 相似度分数 + 时间分数
            base_confidence = 0.2  # 提高初始置信度
            confidence = base_confidence + count_score + similarity_score + time_score
            
            # 3.5 应用上限
            return min(confidence, 0.85)  # 降低最高置信度
            
        except Exception as e:
            logger.error(f"Error calculating fact confidence: {e}")
            return 0.1
            
    async def _update_fact_confidence(self, fact_id: str, confidence: float):
        """更新fact的置信度"""
        try:
            await self.neo4j_service.query(
                self.queries.UPDATE_FACT_CONFIDENCE,
                {
                    "fact_id": fact_id,
                    "confidence": confidence,
                    "metadata": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error updating fact confidence: {e}")
            raise 

    def _generate_id(self, content: str) -> str:
        """生成唯一ID - 返回UUID格式"""
        import uuid
        import hashlib
        # 使用内容的hash作为UUID的namespace
        namespace = uuid.UUID(bytes=hashlib.md5(b'haley.ai').digest())
        # 生成基于内容的UUID5
        return str(uuid.uuid5(namespace, content))

    async def sync_conversation_knowledge(self, conversation_id: str, vectors: List[Dict]):
        """同步对话知识到图数据库和向量存储"""
        try:
            for conv_vec in vectors:
                # 1. 处理实体向量
                entity_ids = []
                for entity_vec in conv_vec.entity_vectors:
                    entity_id = self._generate_id(entity_vec.entity_text)
                    entity_ids.append(entity_id)
                    
                    # 同步实体向量到图数据库
                    await self.sync_entity_vectors([{
                        "id": entity_id,
                        "content": entity_vec.entity_text,
                        "vector": entity_vec.vector
                    }])
                
                # 2. 处理fact
                fact_id = self._generate_id(conv_vec.fact_vector.atomic_fact)
                fact = {
                    "id": fact_id,
                    "content": conv_vec.fact_vector.atomic_fact,
                    "timestamp": conv_vec.fact_vector.timestamp,
                    "vector": conv_vec.fact_vector.vector
                }
                
                # 3. 同步fact和entities的关系
                await self.sync_fact_with_entities(fact, entity_ids)
                
                # 4. 同步到Qdrant
                await self.vector_service.upsert_points_simple([{
                    "id": fact_id,  # 现在是UUID格式
                    "vector": conv_vec.fact_vector.vector,
                    "payload": {
                        "content": conv_vec.fact_vector.atomic_fact,
                        "timestamp": conv_vec.fact_vector.timestamp,
                        "entities": [e.entity_text for e in conv_vec.entity_vectors]
                    }
                }], self.collection_name)
                
        except Exception as e:
            logger.error(f"Error syncing conversation knowledge: {e}")
            raise

    async def search_similar_facts(
        self,
        query_vector: List[float],
        limit: int = 3,
        min_similarity: float = 0.7
    ) -> Dict[str, List[Dict]]:
        """在Neo4j和Qdrant中搜索相似事实"""
        try:
            # 1. Neo4j搜索 - Use appropriate query based on GDS availability
            query = self.queries.SEARCH_SIMILAR_FACTS if self.neo4j_service.gds_available else self.queries.SEARCH_SIMILAR_FACTS_FALLBACK
            neo4j_results = await self.neo4j_service.query(
                query,
                {
                    "query_vector": query_vector,
                    "min_similarity": min_similarity,
                    "limit": limit
                }
            )
            
            # 2. Qdrant搜索
            qdrant_results = await self.vector_service.search(
                collection_name=self.collection_name,
                query_embedding=query_vector,
                limit=limit,
                score_threshold=min_similarity
            )
            
            # 3. 统一格式化结果
            return {
                "neo4j_results": [{
                    "score": r["result"].get("score", 0.0),
                    "confidence": r["result"].get("payload", {}).get("confidence", 0.0),
                    "content": r["result"].get("payload", {}).get("content", ""),
                    "entities": r["result"].get("entities", []),
                    "id": r["result"].get("id", "")
                } for r in neo4j_results if r and "result" in r],
                
                "qdrant_results": [{
                    "score": hit["score"],
                    "content": hit["payload"].get("content", ""),
                    "entities": hit["payload"].get("entities", []),
                    "id": hit["id"],
                    "timestamp": hit["payload"].get("timestamp", "")
                } for hit in qdrant_results]
            }
            
        except Exception as e:
            logger.error(f"Error searching similar facts: {e}")
            raise

    async def get_graph_stats(self) -> Dict[str, int]:
        """获取图数据库统计信息"""
        stats = await self.neo4j_service.query(
            """
            MATCH (f:Fact) WITH count(f) as fact_count
            MATCH (e:Entity) WITH fact_count, count(e) as entity_count
            MATCH ()-[r:MENTIONS]->() WITH fact_count, entity_count, count(r) as relation_count
            RETURN {
                fact_count: fact_count,
                entity_count: entity_count,
                relation_count: relation_count
            } as stats
            """
        )
        return stats[0]["stats"] if stats else {"fact_count": 0, "entity_count": 0, "relation_count": 0}

    async def get_vector_stats(self) -> Dict[str, Any]:
        """获取向量存储统计信息"""
        try:
            collection_info = self.vector_service.client.get_collection(self.collection_name)
            
            return {
                "collection_name": self.collection_name,
                "point_count": collection_info.vectors_count,  
                "dimension": collection_info.config.params.vectors.size,
                "distance": collection_info.config.params.vectors.distance
            }
        except Exception as e:
            logger.error(f"Error getting vector stats: {e}")
            return {
                "collection_name": self.collection_name,
                "point_count": 0,
                "dimension": 0,
                "distance": None
            }