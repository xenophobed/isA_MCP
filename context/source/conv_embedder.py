from typing import Dict, Any, List
from app.services.ai.models.ai_factory import AIFactory
from app.services.db.vector.vector_factory import VectorFactory
from app.config.config_manager import config_manager
from app.config.vector.chroma_config import ChromaConfig
from pydantic import BaseModel
import numpy as np

logger = config_manager.get_logger(__name__)

class EntityVector(BaseModel):
    """Entity vector with metadata"""
    entity_text: str
    vector: List[float] = []

class FactVector(BaseModel):
    """Atomic fact vector with metadata"""
    conversation_id: str
    atomic_fact: str
    timestamp: str
    vector: List[float] = []

class ConversationVectors(BaseModel):
    """Combined vectors for a conversation fact"""
    entity_vectors: List[EntityVector]
    fact_vector: FactVector

class ConversationEmbedder:
    """Generates embeddings for conversation facts and entities"""
    
    def __init__(self):
        self.embed_service = None
        self.vector_service = None
        self.collection_name = "conv_reference"
        
    async def initialize(self):
        """Initialize services"""
        # Get configs
        llm_config = config_manager.get_config('llm')
        vector_config = ChromaConfig()
        vector_config.settings.vector_size = 1024  # Set vector size for BGE-M3 model
        vector_config.settings.collection_name = self.collection_name
        
        # Initialize services using AIFactory
        ai_factory = AIFactory.get_instance()
        self.embed_service = ai_factory.get_embedding(
            model_name="bge-m3",
            provider="ollama",
            config=llm_config
        )
        
        # Initialize vector service
        vector_factory = VectorFactory.get_instance()
        vector_factory.set_config(vector_config)
        self.vector_service = await vector_factory.get_vector("chroma")
        
        # Create collection if not exists
        try:
            exists = await self.vector_service.collection_exists(self.collection_name)
            if not exists:
                await self.vector_service.create_collection(self.collection_name)
                logger.info(f"Created collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise
            
    async def embed_conversation_facts(self, conversation_id: str, facts: List[Dict]) -> List[ConversationVectors]:
        """Generate embeddings for conversation facts and entities"""
        if not self.embed_service:
            await self.initialize()
            
        try:
            conversation_vectors = []
            
            for fact in facts:
                # 1. 生成实体向量 - 把所有实体合并成一个字符串
                entities_text = " ".join(fact.entities)
                entity_vector = await self.embed_service.create_text_embedding(entities_text)
                
                entity_vectors = [EntityVector(
                    entity_text=entities_text,
                    vector=entity_vector.tolist() if hasattr(entity_vector, 'tolist') else entity_vector
                )]
                
                # 2. 生成事实向量
                fact_vector = await self.embed_service.create_text_embedding(fact.atomic_fact)
                
                fact_vec = FactVector(
                    conversation_id=conversation_id,
                    atomic_fact=fact.atomic_fact,
                    timestamp=fact.timestamp.strftime("%Y-%m-%d %H:%M:%S") if fact.timestamp else "",
                    vector=fact_vector.tolist() if hasattr(fact_vector, 'tolist') else fact_vector
                )
                
                # 组合向量
                conv_vectors = ConversationVectors(
                    entity_vectors=entity_vectors,
                    fact_vector=fact_vec
                )
                
                conversation_vectors.append(conv_vectors)
                
            return conversation_vectors
            
        except Exception as e:
            logger.error(f"Error embedding conversation facts: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources"""
        if self.embed_service and hasattr(self.embed_service, 'close'):
            try:
                await self.embed_service.close()
            except Exception as e:
                logger.error(f"Error cleaning up embedding service: {e}")
                raise
