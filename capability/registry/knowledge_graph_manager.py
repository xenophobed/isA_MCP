from typing import List, Dict, Any, Optional
from app.services.db.graph.neo4j.service import Neo4jService
from app.services.db.graph.neo4j.queries.knowledge_capabilities import KnowledgeCapabilitiesQueries
from app.services.ai.models.ai_factory import AIFactory
from app.services.db.vector.vector_factory import VectorFactory
from app.config.config_manager import config_manager
from pydantic import BaseModel, validator
import json
from app.config.vector.qdrant_config import QdrantConfig

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

    class Config:
        # This allows conversion of dicts to models during validation
        from_attributes = True

    @validator('chunks', pre=True)
    def convert_chunks(cls, v):
        if not v:
            return v
        return [
            ChunkInfo(**chunk) if isinstance(chunk, dict) else chunk 
            for chunk in v
        ]

class KnowledgeGraphManager:
    def __init__(self, uri=None, user=None, password=None):
        # Get Neo4j config from config manager if not provided
        if not (uri and user and password):
            neo4j_config = config_manager.get_config('neo4j')
            conn_params = neo4j_config.get_connection_params()
            uri = conn_params['uri']
            user = conn_params['user']
            password = conn_params['password']
            
        self.graph_db = Neo4jService(uri=uri, user=user, password=password)
        self.queries = KnowledgeCapabilitiesQueries()
        self.vector_service = None
        self.embed_service = None
        
    @classmethod
    async def create(cls, uri=None, user=None, password=None):
        """Factory method to create and initialize the manager"""
        manager = cls(uri=uri, user=user, password=password)
        await manager.graph_db.initialize()  # Initialize Neo4j connection
        
        # Initialize services
        vector_factory = VectorFactory.get_instance()
        manager.vector_service = await vector_factory.get_vector()  # Use default type from factory
        
        manager.embed_service = AIFactory.get_instance().get_embed_service(
            model_name="bge-m3",
            provider="ollama"
        )
        
        return manager

    async def store_knowledge(self, metadata: KnowledgeMetadata, vectors: Dict[str, Any]):
        """Store knowledge metadata and vectors"""
        try:
            await self.initialize()
            
            # Ensure vectors are lists
            semantic_vector = vectors["semantic_vector"].tolist() if hasattr(vectors["semantic_vector"], "tolist") else vectors["semantic_vector"]
            functional_vector = vectors["functional_vector"].tolist() if hasattr(vectors["functional_vector"], "tolist") else vectors["functional_vector"]
            contextual_vector = vectors["contextual_vector"].tolist() if hasattr(vectors["contextual_vector"], "tolist") else vectors["contextual_vector"]
            
            # 1. Store in Neo4j
            await self.graph_db.query(
                self.queries.CREATE_KNOWLEDGE_CAPABILITY.query,
                {
                    "capability_id": metadata.capability_id,
                    "semantic_vector": semantic_vector,
                    "functional_vector": functional_vector,
                    "contextual_vector": contextual_vector,
                    "metadata": json.dumps({
                        "semantic": metadata.semantic_vector.dict(),
                        "functional": metadata.functional_vector.dict(),
                        "contextual": metadata.contextual_vector.dict(),
                        "capability_id": metadata.capability_id
                    })
                }
            )
            
            # 2. Store chunks in vector store if present
            if metadata.chunks:
                chunk_points = []
                for chunk in metadata.chunks:
                    chunk_id = f"{metadata.capability_id}_{chunk.chunk_id}"
                    
                    # Ensure vector is a list
                    chunk_vector = vectors["chunk_vectors"][chunk.chunk_id]
                    if hasattr(chunk_vector, "tolist"):
                        chunk_vector = chunk_vector.tolist()
                    
                    # Store chunk in Neo4j
                    await self.graph_db.query(
                        self.queries.CREATE_KNOWLEDGE_CHUNK.query,
                        {
                            "capability_id": metadata.capability_id,
                            "chunk_id": chunk_id,
                            "text": chunk.text,
                            "metadata": json.dumps(chunk.metadata),
                            "vector": chunk_vector
                        }
                    )
                    
                    # Prepare for vector store
                    chunk_points.append({
                        "id": chunk_id,
                        "text": chunk.text,
                        "vector": chunk_vector,
                        "metadata": {
                            "capability_id": metadata.capability_id,
                            "chunk_id": chunk.chunk_id,
                            "source_metadata": chunk.metadata
                        }
                    })
                
                # Store in vector store
                if chunk_points:
                    await self.vector_service.upsert_points(
                        points=chunk_points,
                        collection_name='knowledge_chunks'
                    )
                
        except Exception as e:
            logger.error(f"Error storing knowledge: {e}")
            raise
            
    async def search_capabilities(self, query_text: str, weights: Dict[str, float], threshold: float = 0.3) -> List[Dict]:
        """Search for capabilities in Neo4j knowledge graph"""
        query_vector = await self.embed_service.create_text_embedding(query_text)
        
        results = await self.graph_db.query(
            self.queries.SEARCH_KNOWLEDGE.query,
            {
                "query_vector": query_vector,
                "weights": weights,
                "threshold": threshold,
                "limit": 5
            }
        )
        
        # Format results
        formatted_results = []
        for result in results:
            metadata = json.loads(result["metadata"]) if isinstance(result["metadata"], str) else result["metadata"]
            formatted_results.append({
                "score": result["score"],
                "capability_id": result["capability_id"],
                "core_concepts": metadata["semantic"]["core_concepts"],
                "operations": metadata["functional"]["operations"]
            })
            
        return formatted_results

    async def search_chunks(self, query_text: str, threshold: float = 0.3) -> List[Dict]:
        """Search for content chunks in vector store"""
        query_vector = await self.embed_service.create_text_embedding(query_text)
        
        results = await self.vector_service.search(
            query=query_vector,
            limit=5,
            score_threshold=threshold,
            collection_name='knowledge_chunks'
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "score": result["score"],
                "text": result["payload"]["text"][:200] + "...",
                "summary": result["payload"].get("summary", "N/A")
            })
            
        return formatted_results

    async def comprehensive_search(self, query_text: str, weights: Dict[str, float] = None) -> Dict[str, List[Dict]]:
        """Perform both capability and chunk search with formatted results"""
        if weights is None:
            weights = {"semantic": 0.3, "functional": 0.4, "contextual": 0.3}
            
        # Perform both searches
        capability_results = await self.search_capabilities(query_text, weights)
        chunk_results = await self.search_chunks(query_text)
        
        return {
            "capabilities": capability_results,
            "chunks": chunk_results
        }

    async def initialize(self):
        """Initialize required services"""
        # Initialize Neo4j connection
        await self.graph_db.initialize()
        
        if not self.vector_service:
            # Create QdrantConfig instance
            vector_config = QdrantConfig()
            
            # Override the collection name in the config
            vector_config.COLLECTION_NAME = 'knowledge_chunks'
            
            # Create vector service with updated config
            self.vector_service = await VectorFactory.create_vector_service(
                "qdrant",
                vector_config
            )
            
            # Ensure collection exists with proper settings
            if not self.vector_service.collection_exists('knowledge_chunks'):
                vector_settings = vector_config.get_vector_settings()
                self.vector_service.create_collection(
                    collection_name='knowledge_chunks',
                    vectors_config={
                        "size": vector_settings['size'],
                        "distance": vector_settings['distance']
                    }
                )
                
        if not self.embed_service:
            embed_config = config_manager.get_config('llm')
            self.embed_service = AIFactory.get_instance().get_embed_service(
                model_name="bge-m3",
                provider="ollama"
            )

    def _combine_search_results(self, capability_results: List[Dict], chunk_results: List[Dict]) -> List[Dict]:
        """Combine and sort results from both capability and chunk searches"""
        combined_results = []
        
        # Add capability results
        for result in capability_results:
            try:
                metadata = json.loads(result["metadata"]) if isinstance(result["metadata"], str) else result["metadata"]
                combined_results.append({
                    "score": result["score"],
                    "capability_id": result["capability_id"],
                    "metadata": metadata,
                    "result_type": "capability"
                })
            except Exception as e:
                logger.warning(f"Error processing capability result: {e}")
                continue
        
        # Add chunk results
        for result in chunk_results:
            try:
                # Extract metadata from payload structure
                source_metadata = result["payload"].get("source_metadata", {})
                combined_results.append({
                    "score": result["score"],
                    "capability_id": result["payload"].get("metadata", {}).get("capability_id"),
                    "chunk_text": result["payload"]["text"],
                    "chunk_metadata": source_metadata,
                    "summary": result["payload"].get("summary", ""),
                    "example_queries": result["payload"].get("example_queries", []),
                    "result_type": "chunk"
                })
            except Exception as e:
                logger.warning(f"Error processing chunk result: {e}")
                continue
        
        # Sort by score in descending order
        combined_results.sort(key=lambda x: x["score"], reverse=True)
        
        return combined_results
