from typing import List, Dict, Any
from app.services.ai.models.ai_factory import AIFactory
from app.config.config_manager import config_manager
from .tool_extractor import ToolVectorMetadata
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ToolVectorEmbedder:
    """Generates vector embeddings for tool metadata"""
    
    def __init__(self):
        self.embed_service = None
        
    async def initialize(self):
        """Initialize embedding service"""
        self.embed_service = AIFactory.get_instance().get_embedding(
            model_name="bge-m3",
            provider="ollama"
        )
        
    async def generate_vectors(self, metadata: ToolVectorMetadata) -> Dict[str, Any]:
        """Generate vector embeddings for tool metadata"""
        try:
            if not self.embed_service:
                await self.initialize()
                
            # Generate semantic vector (what it is)
            semantic_text = (
                f"concept:{metadata.semantic_vector.core_concept} "
                f"domain:{metadata.semantic_vector.domain} "
                f"type:{metadata.semantic_vector.service_type}"
            )
            semantic_vector = await self.embed_service.create_text_embedding(semantic_text)
            
            # Generate functional vector (how it works)
            input_specs = " ".join(
                f"input:{name}:{type_}" 
                for name, type_ in metadata.functional_vector.input_spec.items()
            )
            output_spec = f"output:{metadata.functional_vector.output_spec['type']}"
            
            functional_text = (
                f"operation:{metadata.functional_vector.operation} "
                f"{input_specs} {output_spec}"
            )
            functional_vector = await self.embed_service.create_text_embedding(functional_text)
            
            # Generate contextual vector (when/where to use)
            prereqs = " ".join(f"prereq:{p}" for p in metadata.contextual_vector.prerequisites)
            constraints = " ".join(f"constraint:{c}" for c in metadata.contextual_vector.constraints)
            
            contextual_text = (
                f"usage:{metadata.contextual_vector.usage_context} "
                f"{prereqs} {constraints}"
            )
            contextual_vector = await self.embed_service.create_text_embedding(contextual_text)
            
            return {
                "semantic_vector": semantic_vector,
                "functional_vector": functional_vector,
                "contextual_vector": contextual_vector,
                "metadata": {
                    "semantic_text": semantic_text,
                    "functional_text": functional_text,
                    "contextual_text": contextual_text
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating vector embeddings: {str(e)}")
            raise
