#!/usr/bin/env python3
"""
AI-Powered Metadata Embedding Service - Step 3: Generate embeddings and store in pgvector
Uses intelligence_service embedding_generator for advanced embedding capabilities
"""

import json
import asyncio
import hashlib
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from datetime import datetime

from core.database.supabase_client import get_supabase_client
from tools.base_service import BaseService
from .semantic_enricher import SemanticMetadata

# Import AI-powered embedding service
try:
    from tools.services.intelligence_service.language.embedding_generator import embed, EmbeddingGenerator
except ImportError:
    # Fallback for testing/development
    embed = None
    EmbeddingGenerator = None
    logging.warning("Could not import intelligence_service embedding_generator - embedding features will be limited")

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
    """Step 3: AI-powered metadata embedding generation and storage in pgvector"""
    
    def __init__(self, database_source: str = "customs_trade_db"):
        super().__init__("AIMetadataEmbeddingService")
        self.database_source = database_source
        self.supabase = get_supabase_client()
        
        # Initialize AI embedding service
        if EmbeddingGenerator:
            self.embedding_generator = EmbeddingGenerator()
            logger.info("AI embedding generator initialized successfully")
        else:
            self.embedding_generator = None
            logger.warning("AI embedding generator not available - using fallback")
            
        self.embedding_cache = {}
        
        logger.info(f"AI Metadata Embedding Service initialized for database: {database_source}")
        
    async def initialize(self):
        """Initialize the embedding storage service"""
        try:
            # Test database connection by checking if table exists
            await self._ensure_table()
            logger.info("Embedding storage service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embedding storage: {e}")
            raise
    
    async def _ensure_table(self):
        """Ensure the db_meta_embedding table exists"""
        try:
            result = self.supabase.client.schema('dev').table('db_meta_embedding').select('*').limit(1).execute()
            logger.info("db_meta_embedding table verified")
        except Exception as e:
            logger.warning(f"db_meta_embedding table may not exist: {e}")
            logger.info("Please run setup_metadata_embedding.sql to create the table")
            raise
    
    async def store_semantic_metadata(self, semantic_metadata: SemanticMetadata) -> Dict[str, Any]:
        """
        Store semantic metadata with embeddings in pgvector
        
        Args:
            semantic_metadata: Enriched semantic metadata from step 2
            
        Returns:
            Storage results with statistics and billing information
        """
        results = {
            'stored_embeddings': 0,
            'failed_embeddings': 0,
            'storage_time': datetime.now().isoformat(),
            'errors': []
        }
        
        try:
            # Store business entities
            entity_results = await self._store_business_entities(semantic_metadata.business_entities)
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
            
            # Use the RPC function to search
            result = self.supabase.client.rpc(
                'match_metadata_embeddings',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': similarity_threshold,
                    'match_count': limit,
                    'entity_type_filter': entity_type,
                    'database_filter': self.database_source,
                    'min_confidence': 0.0
                }
            ).execute()
            
            search_results = []
            if result.data:
                for row in result.data:
                    search_result = SearchResult(
                        entity_name=row['entity_name'],
                        entity_type=row['entity_type'],
                        similarity_score=row['similarity'],
                        content=row['content'],
                        metadata=row['metadata'],
                        semantic_tags=row['semantic_tags']
                    )
                    search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search similar entities: {e}")
            # Fallback to intelligence service search when DB function is missing
            return await self._fallback_similarity_search(query, entity_type, limit, similarity_threshold)
    
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
            
            if not initial_results or not use_reranking or not self.embedding_generator:
                return initial_results[:limit]
            
            # Use AI reranking if available
            try:
                from tools.services.intelligence_service.language.embedding_generator import rerank
                
                # Extract texts for reranking
                documents = [result.content for result in initial_results]
                
                # Rerank using AI
                reranked = await rerank(query, documents, top_k=min(limit, len(documents)))
                
                # Map back to SearchResult objects
                content_to_result = {result.content: result for result in initial_results}
                reranked_results = []
                
                for item in reranked:
                    content = item["document"]
                    if content in content_to_result:
                        result = content_to_result[content]
                        # Update similarity score with reranking score
                        result.similarity_score = item["relevance_score"]
                        reranked_results.append(result)
                
                logger.info(f"Reranked {len(reranked_results)} results using AI")
                return reranked_results
                
            except Exception as e:
                logger.warning(f"AI reranking failed, using similarity search results: {e}")
                return initial_results[:limit]
            
        except Exception as e:
            logger.error(f"Enhanced search failed: {e}")
            return []
    
    async def _store_business_entities(self, business_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store business entities as embeddings"""
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
                
                # Store in database
                record_data = {
                    'id': f"entity_{entity_name}_{self.database_source}",
                    'entity_type': 'table',
                    'entity_name': entity_name,
                    'entity_full_name': f"table:{entity_name}",
                    'content': content,
                    'embedding': embedding,
                    'metadata': {
                        'business_importance': entity.get('business_importance', 'unknown'),
                        'record_count': entity.get('record_count', 0),
                        'key_attributes': entity.get('key_attributes', []),
                        'relationships': entity.get('relationships', [])
                    },
                    'semantic_tags': [],
                    'confidence_score': confidence,
                    'source_step': 3,
                    'database_source': self.database_source,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                result = self.supabase.client.schema('dev').table('db_meta_embedding').upsert(record_data).execute()
                
                if result.data:
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
                
                # Store in database
                record_data = {
                    'id': f"tags_{entity_key.replace(':', '_').replace('.', '_')}_{self.database_source}",
                    'entity_type': 'semantic_tags',
                    'entity_name': entity_path,
                    'entity_full_name': entity_key,
                    'content': content,
                    'embedding': embedding,
                    'metadata': {'entity_type_prefix': entity_type_prefix},
                    'semantic_tags': tags,
                    'confidence_score': 0.9,
                    'source_step': 3,
                    'database_source': self.database_source,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                result = self.supabase.client.schema('dev').table('db_meta_embedding').upsert(record_data).execute()
                
                if result.data:
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
                
                # Store in database
                record_data = {
                    'id': f"rule_{rule_id}_{self.database_source}",
                    'entity_type': 'business_rule',
                    'entity_name': rule_type,
                    'entity_full_name': f"rule:{rule_type}",
                    'content': content,
                    'embedding': embedding,
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
                
                result = self.supabase.client.schema('dev').table('db_meta_embedding').upsert(record_data).execute()
                
                if result.data:
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
                
                # Store in database
                record_data = {
                    'id': f"pattern_{pattern_id}_{self.database_source}",
                    'entity_type': 'data_pattern',
                    'entity_name': pattern_type,
                    'entity_full_name': f"pattern:{pattern_type}",
                    'content': content,
                    'embedding': embedding,
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
                
                result = self.supabase.client.schema('dev').table('db_meta_embedding').upsert(record_data).execute()
                
                if result.data:
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
        """Generate embedding for text using AI embedding service"""
        try:
            # Check cache first
            text_hash = hashlib.md5(text.encode()).hexdigest()
            if text_hash in self.embedding_cache:
                return self.embedding_cache[text_hash]
            
            # Use AI embedding generator if available
            if self.embedding_generator and embed:
                embedding = await embed(text, model="text-embedding-3-small")
                
                # Cache the result
                self.embedding_cache[text_hash] = embedding
                return embedding
            
            # Fallback: Try direct import if service not initialized
            else:
                try:
                    from tools.services.intelligence_service.language.embedding_generator import embed as direct_embed
                    logger.info("Using direct intelligence service embedding import")
                    embedding = await direct_embed(text, model="text-embedding-3-small")
                    
                    # Cache the result
                    self.embedding_cache[text_hash] = embedding
                    return embedding
                    
                except ImportError:
                    logger.error("Intelligence service embedding unavailable - cannot generate embeddings")
                    return None
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def _generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts efficiently"""
        try:
            if self.embedding_generator and embed:
                # Use AI batch embedding for efficiency
                embeddings = await embed(texts, model="text-embedding-3-small")
                
                # Cache results
                for text, embedding in zip(texts, embeddings):
                    text_hash = hashlib.md5(text.encode()).hexdigest()
                    self.embedding_cache[text_hash] = embedding
                
                return embeddings
            
            else:
                # Fallback: Try direct batch embedding
                try:
                    from tools.services.intelligence_service.language.embedding_generator import embed as direct_embed
                    embeddings = await direct_embed(texts, model="text-embedding-3-small")
                    
                    # Cache results
                    for text, embedding in zip(texts, embeddings):
                        text_hash = hashlib.md5(text.encode()).hexdigest()
                        self.embedding_cache[text_hash] = embedding
                    
                    return embeddings
                    
                except ImportError:
                    # Last resort: process individually
                    embeddings = []
                    for text in texts:
                        embedding = await self._generate_embedding(text)
                        embeddings.append(embedding)
                    return embeddings
                
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            return [None] * len(texts)
    
    async def _fallback_similarity_search(self, query: str, entity_type: Optional[str] = None,
                                        limit: int = 10, similarity_threshold: float = 0.7) -> List[SearchResult]:
        """
        Fallback similarity search using intelligence service search function
        Used when the database RPC function is not available
        """
        try:
            # Query all content from database
            db_query = self.supabase.client.schema('dev').table('db_meta_embedding').select('*')
            
            # Add filters
            if entity_type:
                db_query = db_query.eq('entity_type', entity_type)
            db_query = db_query.eq('database_source', self.database_source)
            
            result = db_query.execute()
            
            if not result.data:
                return []
            
            # Extract content texts for search
            candidates = []
            content_to_row = {}
            
            for row in result.data:
                content = row.get('content', '')
                if content:
                    candidates.append(content)
                    content_to_row[content] = row
            
            if not candidates:
                return []
            
            # Use intelligence service search function
            try:
                from tools.services.intelligence_service.language.embedding_generator import search
                
                # Use the actual query with intelligence service search
                search_results_raw = await search(query, candidates, top_k=limit)
                
                search_results = []
                for content, similarity_score in search_results_raw:
                    if similarity_score >= similarity_threshold and content in content_to_row:
                        row = content_to_row[content]
                        search_result = SearchResult(
                            entity_name=row['entity_name'],
                            entity_type=row['entity_type'],
                            similarity_score=similarity_score,
                            content=content,
                            metadata=row.get('metadata', {}),
                            semantic_tags=row.get('semantic_tags', [])
                        )
                        search_results.append(search_result)
                
                return search_results
                
            except ImportError:
                logger.warning("Intelligence service search not available")
                return []
            
        except Exception as e:
            logger.error(f"Fallback similarity search failed: {e}")
            return []
    
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
            result = self.supabase.client.rpc(
                'get_metadata_stats', 
                {'database_name': self.database_source}
            ).execute()
            
            if result.data:
                return {
                    'success': True,
                    'stats': result.data,
                    'database_source': self.database_source
                }
            else:
                return {'success': False, 'error': 'No stats available'}
                
        except Exception as e:
            logger.error(f"Failed to get metadata stats: {e}")
            return {'success': False, 'error': str(e)}
    
    async def cleanup_old_embeddings(self, days_old: int = 30) -> Dict[str, Any]:
        """Clean up old embeddings"""
        try:
            result = self.supabase.client.rpc(
                'cleanup_old_metadata_embeddings',
                {
                    'days_old': days_old,
                    'database_name': self.database_source
                }
            ).execute()
            
            deleted_count = result.data if result.data else 0
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'database_source': self.database_source
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup embeddings: {e}")
            return {'success': False, 'error': str(e)}

# Global instance
_embedding_service = None

def get_embedding_service(database_source: str = "customs_trade_db") -> AIMetadataEmbeddingService:
    """Get AI metadata embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = AIMetadataEmbeddingService(database_source)
    return _embedding_service

# Backward compatibility
def get_embedding_storage(database_source: str = "customs_trade_db") -> AIMetadataEmbeddingService:
    """Backward compatibility - use get_embedding_service instead"""
    logger.warning("get_embedding_storage is deprecated, use get_embedding_service")
    return get_embedding_service(database_source)