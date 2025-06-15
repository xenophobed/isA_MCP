# app/services/processor.py
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import re
from app.config.config_manager import config_manager
from app.services.agent.capabilities.contextual.capability.registry.knowledge_graph_manager import KnowledgeGraphManager
from app.services.agent.capabilities.contextual.capability.source.knowledge_extractor import KnowledgeExtractor
from app.services.agent.capabilities.contextual.capability.source.knowledge_embedder import KnowledgeVectorEmbedder
from tenacity import retry, stop_after_attempt, wait_exponential

logger = config_manager.get_logger(__name__)

class ProcessorService:
    def __init__(self):
        self.knowledge_extractor = KnowledgeExtractor()
        self.knowledge_embedder = KnowledgeVectorEmbedder()
        self.graph_manager = KnowledgeGraphManager()
        
    async def _init_services(self):
        """Initialize all required services"""
        await self.knowledge_embedder.initialize()
        await self.graph_manager.initialize()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def process_content(
        self,
        content: str,
        metadata: Dict = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """Process content using knowledge graph approach"""
        await self._init_services()
        try:
            # 1. Preprocess text
            cleaned_text = self._preprocess_text(content)
            
            # 2. Extract metadata and generate vectors using knowledge graph approach
            kg_metadata = await self.knowledge_extractor.extract_from_content(cleaned_text)
            kg_vectors = await self.knowledge_embedder.generate_vectors(kg_metadata)
            
            # 3. Store in knowledge graph and get chunks
            await self.graph_manager.store_knowledge(kg_metadata, kg_vectors)
            
            # 4. Prepare chunks for index service format
            chunks = []
            for chunk in kg_metadata.chunks:
                chunk_vector = kg_vectors["chunk_vectors"][chunk.chunk_id]
                chunks.append({
                    "chunk_id": chunk.chunk_id,
                    "content": chunk.text,
                    "embedding": chunk_vector,
                    "metadata": {
                        **chunk.metadata,
                        "kg_capability_id": kg_metadata.capability_id,
                        "kg_core_concepts": kg_metadata.semantic_vector.core_concepts
                    }
                })
            
            # 5. Prepare document semantics
            doc_semantics = {
                "capability_id": kg_metadata.capability_id,
                "semantic": kg_metadata.semantic_vector.dict(),
                "functional": kg_metadata.functional_vector.dict(),
                "contextual": kg_metadata.contextual_vector.dict()
            }
            
            logger.info(f"Created {len(chunks)} chunks with proper format")
            return chunks, doc_semantics

        except Exception as e:
            logger.error(f"Failed to process content: {str(e)}")
            raise

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text content"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        return text.strip()

        
