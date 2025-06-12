from typing import List, Dict, Any
from app.services.ai.tools.tools_manager import tools_manager
from app.config.config_manager import config_manager
from app.services.db.vector.vector_factory import VectorFactory
from app.services.ai.models.ai_factory import AIFactory 
from app.config.vector.qdrant_config import QdrantConfig
import logging
import os

logger = logging.getLogger(__name__)

def rag_error_handler(state):
    """Handle RAG tool errors"""
    error = state.get("error")
    return {
        "messages": [{
            "content": f"Vector search error: {error}. Please try again later.",
            "type": "error"
        }]
    }

@tools_manager.register_tool(error_handler=rag_error_handler)
def vector_search(query: str, collection_name: str = "tp_product", limit: int = 5) -> List[Dict[str, Any]]:
    """Perform vector search in the database.
    
    @semantic:
        concept: vector-search
        domain: rag-service
        type: real-time
    
    @functional:
        operation: search
        input: query:string,collection:string,limit:integer
        output: search_results:list
    
    @context:
        usage: semantic-query
        prereq: vector_db_connection,embedding_service
        constraint: api_dependent,query_required
    """
    try:
        # Initialize services with proper config objects
        vector_config = QdrantConfig()
        vector_config.URL = os.getenv("QDRANT_URL")
        vector_config.API_KEY = os.getenv("QDRANT_API_KEY")
        
        # Create services synchronously
        vector_service = VectorFactory.create_vector_service_sync("qdrant", vector_config)
        embed_service = AIFactory.get_instance().get_embed_service(
            model_name="bge-m3",
            provider="ollama"
        )
        # Create query embedding
        query_vector = embed_service.create_text_embedding_sync(query)
        
        # Perform search
        results = vector_service.search_sync(
            query=query_vector,
            collection_name=collection_name,
            limit=limit,
            score_threshold=0.3
        )
        return results
        
    except Exception as e:
        logger.error(f"Error in vector search: {str(e)}")
        raise 