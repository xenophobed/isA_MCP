#!/usr/bin/env python3
"""
Embedding Storage - Step 3: Generate embeddings and store in pgvector
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

class EmbeddingStorage(BaseService):
    """Step 3: Generate embeddings and store in pgvector"""
    
    def __init__(self, database_source: str = "customs_trade_db"):
        super().__init__("EmbeddingStorage")
        self.database_source = database_source
        self.supabase = get_supabase_client()
        # No separate embedding service needed, using isa_client from BaseService
        self.embedding_cache = {}
        
        logger.info(f"EmbeddingStorage initialized for database: {database_source}")
        
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
        """Ensure the db_metadata_embedding table exists"""
        try:
            result = self.supabase.client.table('db_metadata_embedding').select('*').limit(1).execute()
            logger.info("db_metadata_embedding table verified")
        except Exception as e:
            logger.warning(f"db_metadata_embedding table may not exist: {e}")
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
                        'business_importance': entity.get('business_importance'),
                        'record_count': entity.get('record_count'),
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
                
                result = self.supabase.client.table('db_metadata_embedding').upsert(record_data).execute()
                
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
                
                result = self.supabase.client.table('db_metadata_embedding').upsert(record_data).execute()
                
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
                
                result = self.supabase.client.table('db_metadata_embedding').upsert(record_data).execute()
                
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
                
                result = self.supabase.client.table('db_metadata_embedding').upsert(record_data).execute()
                
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
        """Generate embedding for text using the embedding service"""
        try:
            # Check cache first
            text_hash = hashlib.md5(text.encode()).hexdigest()
            if text_hash in self.embedding_cache:
                return self.embedding_cache[text_hash]
            
            # Generate embedding using ISA client with billing collection
            result_data, billing_info = await self.call_isa_with_billing(
                input_data=text,
                task="embed",
                service_type="embedding",
                operation_name="generate_embedding"
            )
            
            embedding = result_data
            
            # Cache the result
            self.embedding_cache[text_hash] = embedding
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
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
_embedding_storage = None

def get_embedding_storage(database_source: str = "customs_trade_db") -> EmbeddingStorage:
    """Get embedding storage instance"""
    global _embedding_storage
    if _embedding_storage is None:
        _embedding_storage = EmbeddingStorage(database_source)
    return _embedding_storage