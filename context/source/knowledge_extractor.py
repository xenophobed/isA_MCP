from typing import List, Dict, Optional
from pydantic import BaseModel
from app.services.agent.agent_factory import AgentFactory
from app.services.ai.models.ai_factory import AIFactory
from app.config.config_manager import config_manager

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

class ChunkInfo(BaseModel):
    chunk_id: str
    text: str
    metadata: Dict

class KnowledgeMetadata(BaseModel):
    capability_id: str
    semantic_vector: SemanticMetadata
    functional_vector: FunctionalMetadata
    contextual_vector: ContextualMetadata
    chunks: Optional[List[ChunkInfo]] = None

class KnowledgeExtractor:
    """Extracts structured metadata from knowledge content"""
    
    def __init__(self):
        self.agent_factory = AgentFactory.get_instance()
        self.ai_factory = AIFactory.get_instance()
        self.llm_service = None
        self.embed_service = None
        self.strategy = None
        
    async def initialize(self):
        """Initialize required services"""
        if not self.llm_service:
            llm_config = config_manager.get_config('llm')
            self.llm_service = self.ai_factory.get_llm(
                model_name="llama3.1",
                provider="ollama",
                config=llm_config
            )
            self.embed_service = self.ai_factory.get_embedding(
                model_name="bge-m3",
                provider="ollama",
                config=llm_config
            )
        
        # Create structured output strategy for metadata extraction
        strategy_config = {
            "model": {
                "model_name": "llama3.1",
                "provider": "ollama",
                "config": llm_config
            },
            "prompt": {
                "template_path": "app/services/ai/prompt/templates/knowledge",
                "prompt_name": "metadata_extractor"
            },
            "strategy": {
                "output_model": KnowledgeMetadata
            }
        }
        
        self.strategy = await self.agent_factory.create_strategy(
            strategy_type="custom_structured",
            config=strategy_config
        )
        
    async def extract_from_content(self, content: str, chunk_size: Optional[int] = None) -> KnowledgeMetadata:
        """Extract metadata from content with chunking support"""
        await self.initialize()  # Ensure services are initialized
        try:
            if not content.strip():
                raise ValueError("Empty content provided")
            
            # 1. Create chunks using embed service
            # If chunk_size is provided, update the text splitter configuration
            if chunk_size:
                self.embed_service.text_splitter.chunk_size = chunk_size
                
            chunks = await self.embed_service.create_chunks(
                text=content,
                metadata={"source": "knowledge_extractor"}  
            )
            
            if not chunks:
                logger.warning("No chunks created from content")
                # Create a single chunk from the entire content
                chunks = [{
                    'content': content,
                    'metadata': {"source": "knowledge_extractor"}
                }]
            
            # 2. Extract metadata from representative chunks
            sample_content = self._create_sample_content(chunks)
            
            # 3. Extract metadata using structured output strategy
            metadata = await self.strategy.execute({
                "content": sample_content or content  # Fallback to original content if no sample
            })
            
            # 4. Add chunk information
            metadata.chunks = [
                ChunkInfo(
                    chunk_id=f"chunk_{idx}",
                    text=chunk["content"],
                    metadata=chunk["metadata"]
                )
                for idx, chunk in enumerate(chunks)
            ]
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            raise
            
    def _create_sample_content(self, chunks: List[Dict]) -> str:
        """Create representative content from chunks for metadata extraction"""
        if not chunks:
            logger.warning("No chunks available for sample content")
            return ""
        
        # For single chunk, return it directly
        if len(chunks) == 1:
            return chunks[0]['content']
        
        # For multiple chunks, use first, middle and last
        sample_chunks = [
            chunks[0],
            chunks[len(chunks)//2],
            chunks[-1]
        ]
        
        return "\n\n".join([
            f"Section {i+1}:\n{chunk['content']}"
            for i, chunk in enumerate(sample_chunks)
        ])
