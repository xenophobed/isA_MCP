from typing import List, Dict, Any, Optional
from app.services.db.graph.neo4j.queries.db_capabilities import DBCapabilitiesQueries
from app.services.db.graph.neo4j.service import Neo4jService
from app.services.db.vector.vector_factory import VectorFactory
from app.services.ai.models.ai_factory import AIFactory
from app.config.config_manager import config_manager
from app.services.agent.capabilities.contextual.capability.source.db_meta_extractor import DatabaseMetadata
import json

logger = config_manager.get_logger(__name__)

class DBGraphManager:
    def __init__(self, uri=None, user=None, password=None):
        # Get Neo4j config from config manager if not provided
        if not (uri and user and password):
            neo4j_config = config_manager.get_config('neo4j')
            conn_params = neo4j_config.get_connection_params()
            uri = conn_params['uri']
            user = conn_params['user']
            password = conn_params['password']
            
        self.graph_db = Neo4jService(uri=uri, user=user, password=password)
        self.queries = DBCapabilitiesQueries()
        self.vector_service = None
        self.embed_service = None
        
    @classmethod
    async def create(cls, uri=None, user=None, password=None):
        """Factory method to create and initialize the manager"""
        manager = cls(uri=uri, user=user, password=password)
        await manager.initialize()
        return manager

    async def store_table_metadata(self, metadata: DatabaseMetadata, vectors: Dict[str, Any]):
        """Store table metadata and vectors in Neo4j"""
        try:
            await self.initialize()
            
            # Ensure vectors are lists
            semantic_vector = vectors["semantic_vector"].tolist() if hasattr(vectors["semantic_vector"], "tolist") else vectors["semantic_vector"]
            functional_vector = vectors["functional_vector"].tolist() if hasattr(vectors["functional_vector"], "tolist") else vectors["functional_vector"]
            contextual_vector = vectors["contextual_vector"].tolist() if hasattr(vectors["contextual_vector"], "tolist") else vectors["contextual_vector"]
            
            # Add log to check vector data
            logger.debug(f"Storing vectors - semantic: {len(semantic_vector)}, functional: {len(functional_vector)}, contextual: {len(contextual_vector)}")
            
            # Use MERGE instead of CREATE to prevent duplicates
            await self.graph_db.query(
                """
                MERGE (t:Table {table_id: $table_id})
                SET t = {
                    table_id: $table_id,
                    semantic_vector: $semantic_vector,
                    functional_vector: $functional_vector,
                    contextual_vector: $contextual_vector,
                    metadata: $metadata
                }
                """,
                {
                    "table_id": metadata.table_id,
                    "semantic_vector": semantic_vector,
                    "functional_vector": functional_vector,
                    "contextual_vector": contextual_vector,
                    "metadata": json.dumps({
                        "semantic": {
                            "core_concepts": metadata.semantic_vector.core_concepts,
                            "domain": metadata.semantic_vector.domain,
                            "business_entity": metadata.semantic_vector.business_entity
                        },
                        "functional": {
                            "common_operations": metadata.functional_vector.common_operations,
                            "query_patterns": metadata.functional_vector.query_patterns,
                            "sample_queries": metadata.functional_vector.sample_queries
                        },
                        "contextual": {
                            "usage_scenarios": metadata.contextual_vector.usage_scenarios,
                            "data_sensitivity": metadata.contextual_vector.data_sensitivity,
                            "update_frequency": metadata.contextual_vector.update_frequency
                        }
                    })
                }
            )
            
            logger.info(f"Stored table metadata for {metadata.table_id}")
            
        except Exception as e:
            logger.error(f"Error storing table metadata: {e}")
            raise

    async def search_tables(self, query_text: str, weights: Dict[str, float] = None, threshold: float = 0.3) -> List[Dict]:
        """Search for tables in Neo4j graph"""
        if weights is None:
            weights = {"semantic": 0.3, "functional": 0.4, "contextual": 0.3}
            
        try:
            # Generate query vector
            query_vector = await self.embed_service.create_text_embedding(query_text)
            if hasattr(query_vector, 'tolist'):
                query_vector = query_vector.tolist()
            
            logger.debug(f"Query vector length: {len(query_vector)}")
            
            # Verify vectors in database
            check_result = await self.graph_db.query(
                """
                MATCH (t:Table)
                WITH t LIMIT 1
                RETURN size(t.semantic_vector) as sem_size,
                       size(t.functional_vector) as func_size,
                       size(t.contextual_vector) as ctx_size
                """
            )
            if check_result:
                logger.debug(f"Database vector sizes: {check_result[0]}")
            
            results = await self.graph_db.query(
                self.queries.SEARCH_TABLE['query'],
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
                    "table_id": result["table_id"],
                    "metadata": metadata
                })
                
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching tables: {e}")
            raise

    async def initialize(self):
        """Initialize required services"""
        # Initialize Neo4j connection
        await self.graph_db.initialize()
        
        if not self.embed_service:
            self.embed_service = AIFactory.get_instance().get_embed_service(
                model_name="bge-m3",
                provider="ollama"
            )
