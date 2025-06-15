from typing import List, Dict, Any, Optional
import weaviate
import logging
import uuid
from ..base_vector_service import BaseVectorService
from app.config.vector.weaviate_config import WeaviateConfig
from app.config.vector.base_vector_config import DistanceMetric, AlgorithmType
from app.services.ai.models.ai_factory import AIFactory

logger = logging.getLogger(__name__)

class WeaviateService(BaseVectorService):
    """Weaviate vector database service implementation"""
    
    def __init__(self, client: weaviate.Client, config: WeaviateConfig):
        """Initialize Weaviate service
        
        Args:
            client: Weaviate client instance
            config: Weaviate configuration
        """
        super().__init__(config)
        self.client = client
        self.config = config
        self._embed_service = None
        
    async def create_collection(self, collection_name: str) -> bool:
        """Create a new collection
        
        Args:
            collection_name: Name of the collection to create
            
        Returns:
            bool: True if collection was created successfully
        """
        try:
            # Define collection schema
            schema = {
                "class": collection_name,
                "vectorizer": "none",  # We'll provide vectors directly
                "vectorIndexConfig": {
                    "distance": self.config.settings.distance_metric.value,
                    "algorithm": self.config.settings.algorithm.value
                },
                "properties": [
                    {
                        "name": "text",
                        "dataType": ["text"],
                        "description": "Document text"
                    },
                    {
                        "name": "metadata",
                        "dataType": ["object"],
                        "description": "Document metadata"
                    }
                ]
            }
            
            # Create collection
            self.client.schema.create_class(schema)
            logger.info(f"Created collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {str(e)}")
            return False
            
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            bool: True if collection was deleted successfully
        """
        try:
            self.client.schema.delete_class(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {str(e)}")
            return False
            
    async def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists
        
        Args:
            collection_name: Name of the collection to check
            
        Returns:
            bool: True if collection exists
        """
        try:
            return self.client.schema.exists(collection_name)
        except Exception as e:
            logger.error(f"Failed to check collection existence: {str(e)}")
            return False
            
    async def upsert_points(self, points: List[Dict[str, Any]]) -> bool:
        """Upsert points into the collection
        
        Args:
            points: List of points to upsert. Each point should be a dictionary
                   containing 'text' and 'metadata' fields
                   
        Returns:
            bool: True if points were upserted successfully
        """
        if not points:
            raise ValueError("Points list cannot be empty")
            
        try:
            # Get embedding service
            embed_service = await self._get_embed_service()
            
            # Process points in batches
            for i in range(0, len(points), self.config.batch_size):
                batch = points[i:i + self.config.batch_size]
                
                # Create embeddings for batch
                texts = [p["text"] for p in batch]
                embeddings = await embed_service.create_text_embeddings(texts)
                
                # Prepare objects for batch upload
                objects = []
                for point, embedding in zip(batch, embeddings):
                    if not isinstance(point, dict) or "text" not in point:
                        raise ValueError("Each point must be a dictionary containing 'text' field")
                        
                    objects.append({
                        "class": self.config.settings.collection_name,
                        "vector": embedding,
                        "properties": {
                            "text": point["text"],
                            "metadata": point.get("metadata", {})
                        }
                    })
                
                # Upload batch
                self.client.batch.configure(
                    batch_size=self.config.batch_size,
                    timeout_retries=3,
                    callback=None
                )
                
                with self.client.batch as batch:
                    for obj in objects:
                        batch.add_data_object(
                            data_object=obj["properties"],
                            class_name=obj["class"],
                            vector=obj["vector"]
                        )
                        
            logger.info(f"Successfully upserted {len(points)} points")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert points: {str(e)}")
            return False
            
    async def search(
        self,
        query: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors
        
        Args:
            query: Query vector
            limit: Maximum number of results to return
            filters: Optional filters to apply
            
        Returns:
            List of dictionaries containing search results
        """
        if len(query) != self.config.settings.vector_size:
            raise ValueError("Vector dimension mismatch")
            
        try:
            # Build query
            query_builder = (
                self.client.query
                .get(self.config.settings.collection_name, ["text", "metadata"])
                .with_near_vector({
                    "vector": query,
                    "certainty": 0.7
                })
                .with_limit(limit)
            )
            
            # Add filters if provided
            if filters:
                where_filter = {
                    "operator": "And",
                    "operands": [
                        {
                            "path": [key],
                            "operator": "Equal",
                            "valueString": value
                        }
                        for key, value in filters.items()
                    ]
                }
                query_builder = query_builder.with_where(where_filter)
            
            # Execute query
            result = query_builder.do()
            
            # Process results
            if "data" in result and "Get" in result["data"]:
                items = result["data"]["Get"][self.config.settings.collection_name]
                return [
                    {
                        "id": item.get("_additional", {}).get("id"),
                        "score": item.get("_additional", {}).get("certainty", 0),
                        "document": {
                            "text": item.get("text", ""),
                            "metadata": item.get("metadata", {})
                        }
                    }
                    for item in items
                ]
            return []
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
            
    async def close(self):
        """Close the Weaviate client connection"""
        try:
            self.client.close()
            logger.info("Closed Weaviate client connection")
        except Exception as e:
            logger.error(f"Error closing Weaviate client: {str(e)}")
            
    async def _get_embed_service(self):
        """Get or create embedding service"""
        if self._embed_service is None:
            from app.services.embedding.embedding_factory import get_embedding_service
            self._embed_service = await get_embedding_service()
        return self._embed_service 