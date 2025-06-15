from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, PayloadSchemaType
from typing import List, Dict, Any, Optional, Union
from app.config.config_manager import config_manager
from qdrant_client.models import PointStruct, Distance, FieldCondition, Range, Filter
from app.services.ai.models.ai_factory import AIFactory
from ..base_vector_service import BaseVectorService
import uuid
from datetime import datetime
import numpy as np
import time
import asyncio

logger = config_manager.get_logger(__name__)

class QdrantService(BaseVectorService):
    """Qdrant vector database service wrapper"""
    
    def __init__(self, client: QdrantClient, config: Dict[str, Any]):
        self.client = client
        self.collection_name = config.get('collection_name', 'default')
        self.vector_size = config.get('vector_size', 1536)
        self.distance = config.get('distance', Distance.COSINE)
        self.write_consistency = config.get('write_consistency', 1)
        self.on_disk_payload = config.get('on_disk_payload', True)
        self._meta_extractor = None  
        self.default_indexed_fields = {
            'text': PayloadSchemaType.TEXT,
            'timestamp': PayloadSchemaType.INTEGER,
            'source': PayloadSchemaType.KEYWORD,
            'topics': PayloadSchemaType.KEYWORD,
            'doc_type': PayloadSchemaType.KEYWORD,
            'language': PayloadSchemaType.KEYWORD,
            'entities': PayloadSchemaType.KEYWORD,
        }

    async def search(
        self,
        query: Union[str, List[float], None] = None,
        collection_name: str = None,
        limit: int = 10,
        score_threshold: float = 0.7,
        filters: Optional[Dict] = None,
        query_vector: Optional[List[float]] = None,  # For backward compatibility
        query_embedding: Optional[List[float]] = None  # For backward compatibility
    ):
        """
        Enhanced search with metadata filtering and scoring
        
        Args:
            query: Query text or vector to search for (new style)
            collection_name: Target collection name (optional)
            limit: Maximum number of results
            score_threshold: Minimum similarity score threshold
            filters: Optional filters to apply to search
            query_vector: Vector to search for (legacy support)
            query_embedding: Vector to search for (legacy support)
        """
        try:
            collection_name = collection_name or self.collection_name
            
            # Handle different input methods for the query vector
            if query is not None:
                if isinstance(query, str):
                    # Get embedding service
                    embed_service = await AIFactory.get_instance().get_embed_service(
                        model_name="bge-m3",
                        provider="ollama"
                    )
                    query_embedding = await embed_service.create_text_embedding(query)
                else:
                    query_embedding = query
            elif query_vector is not None:
                query_embedding = query_vector
            elif query_embedding is not None:
                pass  # query_embedding is already set
            else:
                raise ValueError("No query provided. Please provide either 'query', 'query_vector', or 'query_embedding'")

            # Convert to list if it's numpy array
            if hasattr(query_embedding, 'tolist'):
                query_embedding = query_embedding.tolist()
            
            # Ensure we're working with a single vector
            if isinstance(query_embedding, list) and isinstance(query_embedding[0], list):
                query_embedding = query_embedding[0]
            
            # Build search parameters
            search_params = {
                "collection_name": collection_name,
                "query_vector": query_embedding,
                "limit": limit,
                "score_threshold": score_threshold
            }
            
            # Add filter if provided
            if filters:
                search_params["filter"] = self._build_filter(filters)
            
            # Log search parameters for debugging
            logger.debug(f"Search params: {search_params}")
            
            # Perform the search
            results = self.client.search(**search_params)
            
            # Enrich results with metadata
            enriched_results = []
            for result in results:
                enriched_result = {
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload,
                    "vector": result.vector if hasattr(result, 'vector') else None
                }
                enriched_results.append(enriched_result)
            
            logger.info(f"Found {len(enriched_results)} results")
            return enriched_results
            
        except Exception as e:
            logger.error(f"Error during vector search: {e}")
            return []

    def _build_filter(self, filters: Union[Dict, Filter]) -> Optional[Filter]:
        """Build advanced Qdrant filter from dict or Filter object"""
        # If it's already a Filter object, return it directly
        if isinstance(filters, Filter):
            return filters
        
        # Otherwise, build the filter from dict
        must_conditions = []
        
        for key, value in filters.items():
            if isinstance(value, (list, tuple)):
                # Handle array values (OR condition)
                should_conditions = [
                    FieldCondition(key=key, match={'value': v}) 
                    for v in value
                ]
                must_conditions.append({"should": should_conditions})
            elif isinstance(value, dict):
                # Handle range conditions
                range_params = {}
                if 'gt' in value:
                    range_params['gt'] = value['gt']
                if 'gte' in value:
                    range_params['gte'] = value['gte']
                if 'lt' in value:
                    range_params['lt'] = value['lt']
                if 'lte' in value:
                    range_params['lte'] = value['lte']
                if range_params:
                    must_conditions.append(
                        FieldCondition(key=key, range=Range(**range_params))
                    )
            else:
                # Handle simple match condition
                must_conditions.append(
                    FieldCondition(key=key, match={'value': value})
                )
        
        return Filter(must=must_conditions) if must_conditions else None

    def get_collections(self):
        """Get list of collections"""
        return self.client.get_collections()

    def get_collection(self, collection_name: str = None):
        """Get collection info"""
        if collection_name is None:
            collection_name = self.collection_name
        return self.client.get_collection(collection_name=collection_name)

    def collection_exists(self, collection_name: str = None) -> bool:
        """Check if collection exists"""
        if collection_name is None:
            collection_name = self.collection_name
        try:
            self.client.get_collection(collection_name)
            return True
        except Exception:
            return False

    def create_collection(self, collection_name: str = None, vectors_config: Dict[str, Any] = None):
        """Create a new collection"""
        if collection_name is None:
            collection_name = self.collection_name
            
        if vectors_config is None:
            vectors_config = {
                "size": self.vector_size,
                "distance": self.distance
            }
            
        return self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vectors_config["size"],
                distance=vectors_config["distance"]
            ),
            write_consistency_factor=self.write_consistency,
            on_disk_payload=self.on_disk_payload
        )

    def delete_collection(self, collection_name: str = None):
        """Delete a collection"""
        if collection_name is None:
            collection_name = self.collection_name
        return self.client.delete_collection(collection_name=collection_name)

    async def upsert_points(self, points: List[Dict], collection_name: str = None, 
                           create_indexes: bool = True) -> bool:
        """
        Upsert points into collection with enhanced metadata handling
        
        Args:
            points: List of point dictionaries containing id, vector, and payload
            collection_name: Optional target collection name
            create_indexes: Whether to create payload indexes automatically
        """
        try:
            collection_name = collection_name or self.collection_name
            points_to_upsert = []
            
            # Get metadata extractor instance
            meta_extractor = await self._get_metadata_extractor()
            
            for point in points:
                # Extract metadata using the instance
                metadata = await meta_extractor.extract_metadata(point["text"])
                metadata_dict = metadata["extracted"].dict()
                
                # Combine example queries and summary with the original text
                enriched_text = f"""Summary: {metadata_dict.get('summary', '')}
                Example Questions: {' '.join(metadata_dict.get('example_queries', []))}
                Content: {point["text"]}"""
                
                # Create embedding for the enriched text
                embed_service = await AIFactory.get_instance().get_embed_service(
                    model_name="bge-m3",
                    provider="ollama"
                )
                vector = await embed_service.create_text_embedding(enriched_text)
                
                # Ensure vector is a flat list of floats
                vector = vector.tolist() if hasattr(vector, "tolist") else vector
                if not isinstance(vector[0], (int, float)):
                    vector = [float(x) for x in vector[0]]
                else:
                    vector = [float(x) for x in vector]
                
                point_id = str(uuid.uuid4())
                points_to_upsert.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,  # Use the new vector from enriched text
                        payload={
                            "text": enriched_text,
                            **metadata_dict,  # Spread metadata at top level
                            "timestamp": int(datetime.now().timestamp()),
                            "source": point.get("source", "unknown")
                        }
                    )
                )
            
            # Upsert points
            self.client.upsert(
                collection_name=collection_name,
                points=points_to_upsert,
                wait=True
            )
            
            # Create indexes if requested
            if create_indexes:
                await self._ensure_indexes(collection_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Error upserting points: {e}")
            raise

    async def create_payload_index(self, field_name: str, field_schema: PayloadSchemaType, collection_name: str = None):
        """Create a payload index for faster filtering"""
        try:
            collection_name = collection_name or self.collection_name
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_schema
            )
            logger.info(f"Created payload index for field: {field_name}")
        except Exception as e:
            logger.error(f"Error creating payload index: {e}")
            raise

    async def _ensure_indexes(self, collection_name: str):
        """Ensure all necessary payload indexes exist"""
        try:
            # Get existing indexes
            collection_info = self.client.get_collection(collection_name)
            existing_indexes = set()
            
            # Check if payload_schema exists and get field names
            if hasattr(collection_info, 'payload_schema'):
                existing_indexes = set(collection_info.payload_schema.keys())
            
            # Create missing indexes
            for field, schema_type in self.default_indexed_fields.items():
                if field not in existing_indexes:
                    await self.create_payload_index(
                        field_name=field,
                        field_schema=schema_type,
                        collection_name=collection_name
                    )
                    logger.info(f"Created index for field: {field}")
                    
        except Exception as e:
            logger.error(f"Error ensuring indexes: {e}")
            raise

    def close(self):
        """Synchronous close method"""
        self.client.close()

    async def close(self):
        """Asynchronous cleanup resources"""
        try:
            # Qdrant client 的 close 是同步的，我们用 asyncio 包装它
            await asyncio.get_event_loop().run_in_executor(None, self.client.close)
        except Exception as e:
            logger.warning(f"Error closing Qdrant client: {e}")

    async def upsert_points_simple(self, points: List[Dict], collection_name: str = None):
        """
        Simple upsert points without metadata extraction
        
        Args:
            points: List of dictionaries containing:
                - id (optional): Point ID, will generate UUID if not provided
                - vector: Vector data
                - payload: Optional payload data
            collection_name: Target collection name
        """
        try:
            collection_name = collection_name or self.collection_name
            points_to_upsert = []
            
            for point in points:
                # 确保向量格式正确
                vector = point["vector"]
                if hasattr(vector, "tolist"):
                    vector = vector.tolist()
                
                # 创建 PointStruct
                from qdrant_client.http.models import PointStruct
                points_to_upsert.append(
                    PointStruct(
                        id=point.get("id", str(uuid.uuid4())),
                        vector=vector,
                        payload=point.get("payload", {})
                    )
                )
            
            # 执行 upsert
            self.client.upsert(
                collection_name=collection_name,
                points=points_to_upsert,
                wait=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error upserting points: {e}")
            raise


    def search_sync(
        self,
        query: List[float],
        collection_name: Optional[str] = None,
        limit: int = 5,
        offset: int = 0,
        score_threshold: Optional[float] = None,
        filters: Optional[Filter] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors synchronously"""
        try:
            collection = collection_name or self.collection_name
            
            # Perform search
            results = self.client.search(
                collection_name=collection,
                query_vector=query,
                limit=limit,
                offset=offset,
                score_threshold=score_threshold,
                query_filter=filters
            )
            
            # Format results
            formatted_results = []
            for hit in results:
                result = {
                    'id': hit.id,
                    'score': hit.score,
                    'payload': hit.payload
                }
                formatted_results.append(result)
                
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            raise

    def upsert_points_sync(
        self,
        points: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
        batch_size: int = 100
    ) -> bool:
        """Upsert points with metadata extraction synchronously"""
        try:
            collection = collection_name or self.collection_name
            meta_extractor = self._get_metadata_extractor_sync()
            
            # Process in batches
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                point_objects = []
                
                for point in batch:
                    # Extract metadata
                    metadata = meta_extractor.extract_metadata_sync(point['text'])
                    
                    # Create point object
                    point_obj = PointStruct(
                        id=str(uuid.uuid4()),
                        vector=point.get('vector', []),
                        payload={
                            **point,
                            **metadata,
                            'timestamp': int(datetime.now().timestamp())
                        }
                    )
                    point_objects.append(point_obj)
                
                # Upsert batch
                self.client.upsert(
                    collection_name=collection,
                    points=point_objects,
                    wait=True
                )
                
                # Add delay between batches
                if i + batch_size < len(points):
                    time.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error upserting points: {str(e)}")
            raise

