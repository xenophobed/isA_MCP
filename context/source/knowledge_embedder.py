from typing import Dict, Any, List
from app.services.ai.models.ai_factory import AIFactory
from app.services.db.vector.vector_factory import VectorFactory
from app.config.config_manager import config_manager
from app.config.vector.chroma_config import ChromaConfig
import numpy as np
from pydantic import BaseModel

logger = config_manager.get_logger(__name__)

class SemanticMetadata(BaseModel):
    core_concepts: List[str]
    domain_knowledge: List[str]
    content_type: List[str]

class FunctionalMetadata(BaseModel):
    operations: List[str]
    input_patterns: List[str]
    output_types: List[str]

class ContextualMetadata(BaseModel):
    user_situations: List[str]
    prerequisites: List[str]
    usage_conditions: List[str]

class KnowledgeMetadata(BaseModel):
    capability_id: str
    semantic_vector: SemanticMetadata
    functional_vector: FunctionalMetadata
    contextual_vector: ContextualMetadata

class KnowledgeVectorEmbedder:
    """Generates embeddings for knowledge metadata and chunks"""
    
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
        
    async def generate_vectors(self, metadata: KnowledgeMetadata) -> Dict[str, Any]:
        """Generate embeddings for metadata"""
        if not self.embed_service:
            await self.initialize()
            
        try:
            # Generate metadata vectors
            vectors = await self._generate_metadata_vectors(metadata)
            
            # Generate chunk vectors if present
            if metadata.chunks:
                chunk_vectors = {}
                for chunk in metadata.chunks:
                    # Ensure vector is properly formatted
                    chunk_vector = await self.embed_service.create_text_embedding(chunk.text)
                    if hasattr(chunk_vector, 'tolist'):
                        chunk_vector = chunk_vector.tolist()
                    chunk_vectors[chunk.chunk_id] = chunk_vector
                vectors["chunk_vectors"] = chunk_vectors
                
            logger.info(f"Generated vectors: {list(vectors.keys())}")
            return vectors
            
        except Exception as e:
            logger.error(f"Error generating vectors: {e}")
            raise
        
    async def _generate_metadata_vectors(self, metadata: KnowledgeMetadata) -> Dict[str, np.ndarray]:
        """Generate vectors for metadata components"""
        texts = {
            "semantic": self._create_semantic_text(metadata.semantic_vector),
            "functional": self._create_functional_text(metadata.functional_vector),
            "contextual": self._create_contextual_text(metadata.contextual_vector)
        }
        
        vectors = {}
        for key, text in texts.items():
            vectors[f"{key}_vector"] = await self.embed_service.create_text_embedding(text)
            
        return vectors
        
    async def _generate_chunk_vectors(self, chunks: List[Dict], batch_size: int = 5) -> List[Dict]:
        """Generate vectors for content chunks in batches"""
        try:
            vector_service = await self._get_vector_service()
            
            # Prepare points for vector service
            points = [{
                "text": chunk["text"],
                "metadata": {
                    "chunk_id": chunk["chunk_id"],
                    "capability_id": self.current_capability_id,
                    **chunk.get("metadata", {})
                }
            } for chunk in chunks]
            
            # Upsert to vector store
            await vector_service.upsert_points(points)
            
            # Return vectors for neo4j storage
            return [{
                "chunk_id": chunk["chunk_id"],
                "vector": await self.embed_service.create_text_embedding(chunk["text"])
            } for chunk in chunks]
            
        except Exception as e:
            logger.error(f"Error generating chunk vectors: {e}")
            raise
        
    def _create_semantic_text(self, semantic: SemanticMetadata) -> str:
        return (
            f"concepts: {' '.join(semantic.core_concepts)} "
            f"domain: {' '.join(semantic.domain_knowledge)} "
            f"type: {' '.join(semantic.content_type)}"
        )
        
    def _create_functional_text(self, functional: FunctionalMetadata) -> str:
        return (
            f"operations: {' '.join(functional.operations)} "
            f"inputs: {' '.join(functional.input_patterns)} "
            f"outputs: {' '.join(functional.output_types)}"
        )
        
    def _create_contextual_text(self, contextual: ContextualMetadata) -> str:
        return (
            f"situations: {' '.join(contextual.user_situations)} "
            f"prerequisites: {' '.join(contextual.prerequisites)} "
            f"conditions: {' '.join(contextual.usage_conditions)}"
        )
