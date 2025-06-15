from typing import Dict, Any, List
from app.services.ai.models.ai_factory import AIFactory
from app.services.db.vector.vector_factory import VectorFactory
from app.config.config_manager import config_manager
from app.config.vector.chroma_config import ChromaConfig
from .db_meta_extractor import DatabaseMetadata, SemanticVector, FunctionalVector, ContextualVector
import numpy as np

logger = config_manager.get_logger(__name__)

class DBMetaEmbedder:
    """Generates embeddings for database metadata"""
    
    def __init__(self):
        self.embed_service = None
        self.vector_service = None
        
    async def initialize(self):
        """Initialize services"""
        # Get configs
        llm_config = config_manager.get_config('llm')
        vector_config = ChromaConfig()
        vector_config.settings.vector_size = 1024  # Set vector size for BGE-M3 model
        
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
        
    async def generate_vectors(self, metadata: DatabaseMetadata) -> Dict[str, Any]:
        """Generate embeddings for metadata"""
        if not self.embed_service:
            await self.initialize()
            
        try:
            # 1. Generate single query vector for each type
            semantic_text = " ".join([
                " ".join(metadata.semantic_vector.core_concepts),
                " ".join(metadata.semantic_vector.domain),
                " ".join(metadata.semantic_vector.business_entity)
            ])
            functional_text = " ".join([
                " ".join(metadata.functional_vector.common_operations),
                " ".join(metadata.functional_vector.query_patterns)
            ])
            contextual_text = " ".join(metadata.contextual_vector.usage_scenarios)
            
            # 2. Generate embeddings
            semantic_vector = await self.embed_service.create_text_embedding(semantic_text)
            functional_vector = await self.embed_service.create_text_embedding(functional_text)
            contextual_vector = await self.embed_service.create_text_embedding(contextual_text)
            
            # 3. Convert to lists if needed
            result_vectors = {
                "semantic_vector": semantic_vector.tolist() if hasattr(semantic_vector, "tolist") else semantic_vector,
                "functional_vector": functional_vector.tolist() if hasattr(functional_vector, "tolist") else functional_vector,
                "contextual_vector": contextual_vector.tolist() if hasattr(contextual_vector, "tolist") else contextual_vector
            }
            
            logger.debug(f"Vector dimensions - semantic: {len(result_vectors['semantic_vector'])}, " +
                        f"functional: {len(result_vectors['functional_vector'])}, " +
                        f"contextual: {len(result_vectors['contextual_vector'])}")
            
            return result_vectors
            
        except Exception as e:
            logger.error(f"Error generating vectors: {str(e)}")
            raise
