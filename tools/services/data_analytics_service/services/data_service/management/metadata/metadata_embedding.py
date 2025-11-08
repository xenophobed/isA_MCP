#!/usr/bin/env python3
"""
AI-Powered Metadata Embedding Service - Step 3: Generate embeddings and store in Qdrant
Uses ISA Model for unified embedding generation + Qdrant for vector storage
"""

import json
import asyncio
import hashlib
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from datetime import datetime

from core.clients.qdrant_client import get_qdrant_client
from core.clients.model_client import get_model_client
from tools.base_service import BaseService
from .semantic_enricher import SemanticMetadata

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingRecord:
    """Record for storing embeddings"""
    id: str
    entity_type: str  # 'table', 'column', 'relationship', 'business_rule', 'semantic_tag'
    entity_name: str
    entity_full_name: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    semantic_tags: List[str]
    confidence_score: float
    created_at: datetime
    updated_at: datetime

@dataclass
class SearchResult:
    """Search result from embedding similarity search"""
    entity_name: str
    entity_type: str
    similarity_score: float
    content: str
    metadata: Dict[str, Any]
    semantic_tags: List[str]

class AIMetadataEmbeddingService(BaseService):
    """Step 3: AI-powered metadata embedding generation and storage in Qdrant (ISA Model)"""

    def __init__(self, database_source: str = "customs_trade_db"):
        super().__init__("AIMetadataEmbeddingService")
        self.database_source = database_source

        # Collection name: user_data (per user requirement)
        self.collection_name = 'user_data'
        self.vector_dimension = 1536  # text-embedding-3-small
        self.distance_metric = 'Cosine'

        # Qdrant client will be initialized asynchronously
        self.qdrant = None

        # ISA Model client will be initialized asynchronously
        self.model_client = None
        self.embedding_cache = {}

        logger.info(f"AI Metadata Embedding Service initialized for database: {database_source} (using ISA Model + Qdrant)")
        
    async def initialize(self):
        """Initialize the embedding storage service, Qdrant client, and ISA Model client"""
        try:
            # Initialize ISA Model client
            if not self.model_client:
                self.model_client = await get_model_client()
                logger.info("ISA Model client initialized successfully")

            # Initialize Qdrant client
            if not self.qdrant:
                from isa_common.qdrant_client import QdrantClient
                self.qdrant = QdrantClient(
                    host='isa-qdrant-grpc',
                    port=50062,
                    user_id=f'metadata-{self.database_source}'
                )
                logger.info(f"Qdrant client initialized successfully")

            # Ensure collection exists
            await self._ensure_collection()
            logger.info("Embedding storage service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embedding storage: {e}")
            raise

    async def _ensure_collection(self):
        """Ensure the Qdrant collection exists"""
        try:
            # Check if collection exists
            collections = self.qdrant.list_collections()

            if self.collection_name not in collections:
                # Create collection
                self.qdrant.create_collection(
                    self.collection_name,
                    self.vector_dimension,
                    distance=self.distance_metric
                )
                logger.info(f"Created Qdrant collection '{self.collection_name}'")

                # Create field indexes for filtering
                await self._create_indexes()
            else:
                logger.info(f"Qdrant collection '{self.collection_name}' already exists")

        except Exception as e:
            logger.warning(f"Failed to ensure collection: {e}")
            # Don't raise - collection might already exist

    async def _create_indexes(self):
        """Create field indexes for filtering"""
        try:
            # Index for database_source filtering
            self.qdrant.create_field_index(
                self.collection_name,
                'database_source',
                'keyword'
            )

            # Index for entity_type filtering
            self.qdrant.create_field_index(
                self.collection_name,
                'entity_type',
                'keyword'
            )

            logger.info("Created field indexes for filtering")

        except Exception as e:
            logger.warning(f"Index creation failed (may already exist): {e}")
    
    async def store_semantic_metadata(
        self, 
        semantic_metadata: SemanticMetadata,
        storage_path: str = None,
        dataset_name: str = None
    ) -> Dict[str, Any]:
        """
        Store semantic metadata with embeddings in pgvector
        
        Args:
            semantic_metadata: Enriched semantic metadata from step 2
            storage_path: Optional MinIO Parquet path for query execution
            dataset_name: Optional dataset name
            
        Returns:
            Storage results with statistics and billing information
        """
        results = {
            'stored_embeddings': 0,
            'failed_embeddings': 0,
            'storage_time': datetime.now().isoformat(),
            'errors': []
        }
        
        # Store storage path info for query execution
        self._storage_path = storage_path
        self._dataset_name = dataset_name
        
        try:
            # Store business entities with storage path
            entity_results = await self._store_business_entities(
                semantic_metadata.business_entities,
                storage_path=storage_path,
                dataset_name=dataset_name
            )
            results['stored_embeddings'] += entity_results['stored']
            results['failed_embeddings'] += entity_results['failed']
            results['errors'].extend(entity_results['errors'])
            
            # Store semantic tags
            tags_results = await self._store_semantic_tags(semantic_metadata.semantic_tags)
            results['stored_embeddings'] += tags_results['stored']
            results['failed_embeddings'] += tags_results['failed']
            results['errors'].extend(tags_results['errors'])
            
            # Store business rules
            rules_results = await self._store_business_rules(semantic_metadata.business_rules)
            results['stored_embeddings'] += rules_results['stored']
            results['failed_embeddings'] += rules_results['failed']
            results['errors'].extend(rules_results['errors'])
            
            # Store data patterns
            patterns_results = await self._store_data_patterns(semantic_metadata.data_patterns)
            results['stored_embeddings'] += patterns_results['stored']
            results['failed_embeddings'] += patterns_results['failed']
            results['errors'].extend(patterns_results['errors'])
            
            # Add billing information to results
            results['billing_info'] = self.get_billing_summary()
            
            logger.info(f"Stored {results['stored_embeddings']} embeddings, {results['failed_embeddings']} failed")
            
        except Exception as e:
            logger.error(f"Failed to store semantic metadata: {e}")
            results['errors'].append(str(e))
        
        return results
    
    async def search_similar_entities(self, query: str, entity_type: Optional[str] = None,
                                    limit: int = 10, similarity_threshold: float = 0.7) -> List[SearchResult]:
        """
        Search for similar entities using embedding similarity

        Args:
            query: Search query text
            entity_type: Optional filter by entity type
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score

        Returns:
            List of search results
        """
        try:
            # Generate embedding for query
            query_embedding = await self._generate_embedding(query)

            if not query_embedding:
                return []

            # Build filter conditions for Qdrant
            filter_conditions = {
                'must': [
                    {'field': 'database_source', 'match': {'keyword': self.database_source}}
                ]
            }

            # Add entity type filter if specified
            if entity_type:
                filter_conditions['must'].append(
                    {'field': 'entity_type', 'match': {'keyword': entity_type}}
                )

            # Search in Qdrant
            with self.qdrant:
                results = self.qdrant.search_with_filter(
                    self.collection_name,
                    query_embedding,
                    filter_conditions=filter_conditions,
                    limit=limit,
                    with_payload=True,
                    with_vectors=False
                )

            # Filter by similarity threshold and format results
            search_results = []
            if results:
                for result in results:
                    score = result.get('score', 0.0)
                    if score >= similarity_threshold:
                        payload = result.get('payload', {})
                        search_result = SearchResult(
                            entity_name=payload.get('entity_name', 'unknown'),
                            entity_type=payload.get('entity_type', 'unknown'),
                            similarity_score=score,
                            content=payload.get('content', ''),
                            metadata=payload.get('metadata', {}),
                            semantic_tags=payload.get('semantic_tags', [])
                        )
                        search_results.append(search_result)

            return search_results

        except Exception as e:
            logger.error(f"Failed to search similar entities: {e}")
            return []
    
    async def search_with_reranking(self, query: str, entity_type: Optional[str] = None, 
                                  limit: int = 10, similarity_threshold: float = 0.7,
                                  use_reranking: bool = True) -> List[SearchResult]:
        """
        Enhanced search with AI-powered reranking for better relevance
        
        Args:
            query: Search query text
            entity_type: Optional filter by entity type
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            use_reranking: Whether to use AI reranking for better results
            
        Returns:
            List of search results, potentially reranked by AI
        """
        try:
            # First get similarity search results
            initial_results = await self.search_similar_entities(
                query, entity_type, limit * 2, similarity_threshold  # Get more for reranking
            )
            
            if not initial_results or not use_reranking:
                return initial_results[:limit]

            # Note: ISA Model does not currently support reranking
            # Returning top similarity results instead
            logger.info(f"Reranking not available in ISA Model, using top {limit} similarity results")
            return initial_results[:limit]
            
        except Exception as e:
            logger.error(f"Enhanced search failed: {e}")
            return []
    
    async def _store_business_entities(
        self, 
        business_entities: List[Dict[str, Any]],
        storage_path: str = None,
        dataset_name: str = None
    ) -> Dict[str, Any]:
        """
        Store business entities as embeddings with storage path
        
        Args:
            business_entities: List of business entity dictionaries
            storage_path: Optional MinIO Parquet path
            dataset_name: Optional dataset name
        """
        results = {'stored': 0, 'failed': 0, 'errors': []}
        
        for entity in business_entities:
            try:
                entity_name = entity['entity_name']
                entity_type = entity['entity_type']
                confidence = entity.get('confidence', 0.0)
                
                # Create content description
                content = f"Table: {entity_name}, Type: {entity_type}, "
                content += f"Importance: {entity.get('business_importance', 'unknown')}, "
                content += f"Records: {entity.get('record_count', 0)}, "
                content += f"Key attributes: {', '.join(entity.get('key_attributes', []))}"
                
                # Generate embedding
                embedding = await self._generate_embedding(content)
                if not embedding:
                    results['failed'] += 1
                    continue
                
                # Store in database with storage path info
                # Build metadata with storage information
                metadata_dict = {
                    'business_importance': entity.get('business_importance', 'unknown'),
                    'record_count': entity.get('record_count', 0),
                    'key_attributes': entity.get('key_attributes', []),
                    'relationships': entity.get('relationships', [])
                }
                
                # Add storage path for query execution
                if storage_path:
                    metadata_dict['storage_path'] = storage_path
                if dataset_name:
                    metadata_dict['dataset_name'] = dataset_name
                
                # Generate unique integer ID for Qdrant
                point_id_str = f"entity_{entity_name}_{self.database_source}"
                point_id = abs(hash(point_id_str)) % (10 ** 15)  # Ensure positive 15-digit int

                # Build Qdrant payload
                payload = {
                    'entity_type': 'table',
                    'entity_name': entity_name,
                    'entity_full_name': f"table:{entity_name}",
                    'content': content,
                    'metadata': metadata_dict,
                    'semantic_tags': [],
                    'confidence_score': confidence,
                    'source_step': 3,
                    'database_source': self.database_source,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }

                # Upsert to Qdrant
                points = [{
                    'id': point_id,
                    'vector': embedding,
                    'payload': payload
                }]

                with self.qdrant:
                    operation_id = self.qdrant.upsert_points(self.collection_name, points)

                if operation_id:
                    results['stored'] += 1
                    logger.info(f"Stored entity embedding: {entity_name}")
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Failed to store entity {entity.get('entity_name', 'unknown')}: {e}")
                logger.error(f"Failed to store entity embedding: {e}")
        
        return results
    
    async def _store_semantic_tags(self, semantic_tags: Dict[str, List[str]]) -> Dict[str, Any]:
        """Store semantic tags as embeddings"""
        results = {'stored': 0, 'failed': 0, 'errors': []}
        
        for entity_key, tags in semantic_tags.items():
            if not tags:  # Skip empty tags
                continue
                
            try:
                # Parse entity key (e.g., "table:companies" or "column:companies.company_code")
                if ':' not in entity_key:
                    continue
                    
                entity_type_prefix, entity_path = entity_key.split(':', 1)
                
                # Create content description
                content = f"{entity_type_prefix.title()}: {entity_path} has semantic tags: {', '.join(tags)}"
                
                # Generate embedding
                embedding = await self._generate_embedding(content)
                if not embedding:
                    results['failed'] += 1
                    continue
                
                # Generate unique integer ID for Qdrant
                point_id_str = f"tags_{entity_key.replace(':', '_').replace('.', '_')}_{self.database_source}"
                point_id = abs(hash(point_id_str)) % (10 ** 15)

                # Build Qdrant payload
                payload = {
                    'entity_type': 'semantic_tags',
                    'entity_name': entity_path,
                    'entity_full_name': entity_key,
                    'content': content,
                    'metadata': {'entity_type_prefix': entity_type_prefix},
                    'semantic_tags': tags,
                    'confidence_score': 0.9,
                    'source_step': 3,
                    'database_source': self.database_source,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }

                # Upsert to Qdrant
                points = [{
                    'id': point_id,
                    'vector': embedding,
                    'payload': payload
                }]

                with self.qdrant:
                    operation_id = self.qdrant.upsert_points(self.collection_name, points)

                if operation_id:
                    results['stored'] += 1
                    logger.info(f"Stored semantic tags: {entity_key}")
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Failed to store tags for {entity_key}: {e}")
                logger.error(f"Failed to store semantic tags: {e}")
        
        return results
    
    async def _store_business_rules(self, business_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store business rules as embeddings"""
        results = {'stored': 0, 'failed': 0, 'errors': []}
        
        for rule in business_rules:
            try:
                rule_type = rule.get('rule_type', 'unknown')
                description = rule.get('description', '')
                confidence = rule.get('confidence', 0.0)
                
                # Create content description
                content = f"Business rule ({rule_type}): {description}"
                
                # Generate embedding
                embedding = await self._generate_embedding(content)
                if not embedding:
                    results['failed'] += 1
                    continue
                
                # Generate unique ID
                rule_id = hashlib.md5(description.encode()).hexdigest()[:16]

                # Generate unique integer ID for Qdrant
                point_id_str = f"rule_{rule_id}_{self.database_source}"
                point_id = abs(hash(point_id_str)) % (10 ** 15)

                # Build Qdrant payload
                payload = {
                    'entity_type': 'business_rule',
                    'entity_name': rule_type,
                    'entity_full_name': f"rule:{rule_type}",
                    'content': content,
                    'metadata': {
                        'tables_involved': rule.get('tables_involved', []),
                        'sql_constraint': rule.get('sql_constraint', '')
                    },
                    'semantic_tags': [f"rule:{rule_type}"],
                    'confidence_score': confidence,
                    'source_step': 3,
                    'database_source': self.database_source,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }

                # Upsert to Qdrant
                points = [{
                    'id': point_id,
                    'vector': embedding,
                    'payload': payload
                }]

                with self.qdrant:
                    operation_id = self.qdrant.upsert_points(self.collection_name, points)

                if operation_id:
                    results['stored'] += 1
                    logger.info(f"Stored business rule: {rule_type}")
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Failed to store rule {rule.get('rule_type', 'unknown')}: {e}")
                logger.error(f"Failed to store business rule: {e}")
        
        return results
    
    async def _store_data_patterns(self, data_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store data patterns as embeddings"""
        results = {'stored': 0, 'failed': 0, 'errors': []}
        
        for pattern in data_patterns:
            try:
                pattern_type = pattern.get('pattern_type', 'unknown')
                description = pattern.get('description', '')
                confidence = pattern.get('confidence', 0.0)
                
                # Create content description
                content = f"Data pattern ({pattern_type}): {description}"
                if 'tables_involved' in pattern:
                    content += f" - Tables: {', '.join(pattern['tables_involved'])}"
                if 'columns_involved' in pattern:
                    content += f" - Columns: {', '.join(pattern['columns_involved'])}"
                
                # Generate embedding
                embedding = await self._generate_embedding(content)
                if not embedding:
                    results['failed'] += 1
                    continue
                
                # Generate unique ID
                pattern_id = hashlib.md5(description.encode()).hexdigest()[:16]

                # Generate unique integer ID for Qdrant
                point_id_str = f"pattern_{pattern_id}_{self.database_source}"
                point_id = abs(hash(point_id_str)) % (10 ** 15)

                # Build Qdrant payload
                payload = {
                    'entity_type': 'data_pattern',
                    'entity_name': pattern_type,
                    'entity_full_name': f"pattern:{pattern_type}",
                    'content': content,
                    'metadata': {
                        'tables_involved': pattern.get('tables_involved', []),
                        'columns_involved': pattern.get('columns_involved', [])
                    },
                    'semantic_tags': [f"pattern:{pattern_type}"],
                    'confidence_score': confidence,
                    'source_step': 3,
                    'database_source': self.database_source,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }

                # Upsert to Qdrant
                points = [{
                    'id': point_id,
                    'vector': embedding,
                    'payload': payload
                }]

                with self.qdrant:
                    operation_id = self.qdrant.upsert_points(self.collection_name, points)

                if operation_id:
                    results['stored'] += 1
                    logger.info(f"Stored data pattern: {pattern_type}")
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Failed to store pattern {pattern.get('pattern_type', 'unknown')}: {e}")
                logger.error(f"Failed to store data pattern: {e}")
        
        return results
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using ISA Model"""
        try:
            # Check cache first
            text_hash = hashlib.md5(text.encode()).hexdigest()
            if text_hash in self.embedding_cache:
                return self.embedding_cache[text_hash]

            # Initialize client if needed
            if not self.model_client:
                self.model_client = await get_model_client()

            # Use ISA Model for embedding generation
            response = await self.model_client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )

            embedding = response.data[0].embedding

            # Cache the result
            self.embedding_cache[text_hash] = embedding
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def _generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts efficiently using ISA Model"""
        try:
            # Initialize client if needed
            if not self.model_client:
                self.model_client = await get_model_client()

            # Use ISA Model for batch embedding generation
            response = await self.model_client.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )

            embeddings = [item.embedding for item in response.data]

            # Cache results
            for text, embedding in zip(texts, embeddings):
                text_hash = hashlib.md5(text.encode()).hexdigest()
                self.embedding_cache[text_hash] = embedding

            return embeddings

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}, falling back to individual processing")
            # Fallback: process individually
            embeddings = []
            for text in texts:
                embedding = await self._generate_embedding(text)
                embeddings.append(embedding)
            return embeddings
    
    async def _fallback_similarity_search(self, query: str, entity_type: Optional[str] = None,
                                        limit: int = 10, similarity_threshold: float = 0.7) -> List[SearchResult]:
        """
        Fallback similarity search - deprecated, kept for backward compatibility
        Now just calls the main search_similar_entities which uses Qdrant
        """
        logger.warning("_fallback_similarity_search is deprecated, using main search instead")
        return await self.search_similar_entities(query, entity_type, limit, similarity_threshold)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import math
            
            # Convert to same length if needed
            if len(vec1) != len(vec2):
                min_len = min(len(vec1), len(vec2))
                vec1 = vec1[:min_len]
                vec2 = vec2[:min_len]
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            # Avoid division by zero
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = dot_product / (magnitude1 * magnitude2)
            
            # Ensure result is between 0 and 1
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"Cosine similarity calculation failed: {e}")
            return 0.0
    
    async def get_metadata_stats(self) -> Dict[str, Any]:
        """Get statistics about stored metadata embeddings"""
        try:
            # Get collection info from Qdrant
            with self.qdrant:
                collection_info = self.qdrant.get_collection_info(self.collection_name)

            if not collection_info:
                return {'success': False, 'error': 'Failed to get collection info'}

            # Count by entity types using scroll
            entity_type_counts = {}
            filter_conditions = {
                'must': [
                    {'field': 'database_source', 'match': {'keyword': self.database_source}}
                ]
            }

            # Get all points for this database_source to count by type
            offset_id = None
            total_points = 0
            while True:
                with self.qdrant:
                    result = self.qdrant.scroll(
                        collection_name=self.collection_name,
                        filter_conditions=filter_conditions,
                        limit=1000,
                        offset_id=offset_id,
                        with_payload=True,
                        with_vectors=False
                    )

                if not result or 'points' not in result:
                    break

                points = result['points']
                if not points:
                    break

                # Count by entity type
                for point in points:
                    entity_type = point['payload'].get('entity_type', 'unknown')
                    entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1
                    total_points += 1

                offset_id = result.get('next_offset')
                if not offset_id:
                    break

            return {
                'success': True,
                'stats': {
                    'total_points': total_points,
                    'entity_type_counts': entity_type_counts,
                    'collection_total': collection_info.get('points_count', 0)
                },
                'database_source': self.database_source
            }

        except Exception as e:
            logger.error(f"Failed to get metadata stats: {e}")
            return {'success': False, 'error': str(e)}
    
    async def cleanup_old_embeddings(self, days_old: int = 30) -> Dict[str, Any]:
        """Clean up old embeddings"""
        try:
            from datetime import datetime, timedelta

            # Calculate cutoff date
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

            # Find old points by scrolling
            filter_conditions = {
                'must': [
                    {'field': 'database_source', 'match': {'keyword': self.database_source}}
                ]
            }

            old_point_ids = []
            offset_id = None

            while True:
                with self.qdrant:
                    result = self.qdrant.scroll(
                        collection_name=self.collection_name,
                        filter_conditions=filter_conditions,
                        limit=1000,
                        offset_id=offset_id,
                        with_payload=True,
                        with_vectors=False
                    )

                if not result or 'points' not in result:
                    break

                points = result['points']
                if not points:
                    break

                # Filter by created_at date
                for point in points:
                    created_at = point['payload'].get('created_at', '')
                    if created_at and created_at < cutoff_date:
                        old_point_ids.append(point['id'])

                offset_id = result.get('next_offset')
                if not offset_id:
                    break

            # Delete old points
            deleted_count = 0
            if old_point_ids:
                with self.qdrant:
                    operation_id = self.qdrant.delete_points(self.collection_name, old_point_ids)
                    if operation_id:
                        deleted_count = len(old_point_ids)
                        logger.info(f"Deleted {deleted_count} old embeddings (older than {days_old} days)")

            return {
                'success': True,
                'deleted_count': deleted_count,
                'database_source': self.database_source
            }

        except Exception as e:
            logger.error(f"Failed to cleanup embeddings: {e}")
            return {'success': False, 'error': str(e)}

# Global instance cache - store per database_source
_embedding_services = {}

async def get_embedding_service(database_source: str = "customs_trade_db") -> AIMetadataEmbeddingService:
    """Get AI metadata embedding service instance - cached per database_source with auto-initialization"""
    global _embedding_services
    if database_source not in _embedding_services:
        service = AIMetadataEmbeddingService(database_source)
        # Initialize Qdrant and Model clients
        await service.initialize()
        _embedding_services[database_source] = service
    return _embedding_services[database_source]

# Backward compatibility
def get_embedding_storage(database_source: str = "customs_trade_db") -> AIMetadataEmbeddingService:
    """Backward compatibility - use get_embedding_service instead"""
    logger.warning("get_embedding_storage is deprecated, use get_embedding_service")
    return get_embedding_service(database_source)