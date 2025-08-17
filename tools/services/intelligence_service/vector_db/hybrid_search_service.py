#!/usr/bin/env python3
"""
Hybrid Search Service

High-level service that orchestrates hybrid search across multiple backends:
- ISA client (existing)
- Local vector database (Supabase/Qdrant)
- Result fusion and optimization
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import logging
import asyncio
from datetime import datetime

from .base_vector_db import BaseVectorDB, SearchResult, VectorSearchConfig, SearchMode, RankingMethod
from .vector_db_factory import create_vector_db
from tools.services.intelligence_service.language.embedding_generator import embedding_generator

logger = logging.getLogger(__name__)

class HybridSearchService:
    """
    Hybrid search service that combines multiple search backends.
    
    Features:
    - ISA client integration (existing functionality)
    - Local vector database search
    - Hybrid search with result fusion
    - Fallback mechanisms for reliability
    - Performance optimization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize hybrid search service.
        
        Args:
            config: Service configuration
        """
        self.config = config or {}
        self.vector_db: Optional[BaseVectorDB] = None
        self.use_local_db = self.config.get('use_local_db', True)
        self.use_isa_fallback = self.config.get('use_isa_fallback', True)
        self.logger = logger
        
        # Initialize vector database
        if self.use_local_db:
            try:
                self.vector_db = create_vector_db()
                self.logger.info("Initialized local vector database")
            except Exception as e:
                self.logger.warning(f"Failed to initialize local vector database: {e}")
                self.vector_db = None
    
    async def store_knowledge(
        self,
        id: str,
        text: str,
        embedding: List[float],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store knowledge in the vector database.
        
        Args:
            id: Unique identifier
            text: Text content
            embedding: Vector embedding
            user_id: User identifier
            metadata: Additional metadata
            
        Returns:
            Storage result
        """
        try:
            if self.vector_db:
                success = await self.vector_db.store_vector(
                    id=id,
                    text=text,
                    embedding=embedding,
                    user_id=user_id,
                    metadata=metadata
                )
                
                return {
                    'success': success,
                    'method': 'local_db',
                    'id': id,
                    'user_id': user_id
                }
            else:
                return {
                    'success': False,
                    'error': 'Local vector database not available',
                    'method': 'none'
                }
                
        except Exception as e:
            self.logger.error(f"Error storing knowledge: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'local_db'
            }
    
    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        user_id: str,
        search_config: Optional[VectorSearchConfig] = None
    ) -> Dict[str, Any]:
        """
        Perform hybrid search using multiple backends.
        
        Args:
            query_text: Query text
            query_embedding: Query embedding vector
            user_id: User identifier
            search_config: Search configuration
            
        Returns:
            Search results with metadata
        """
        search_config = search_config or VectorSearchConfig()
        
        try:
            # Strategy 1: Try local database hybrid search first
            if self.vector_db and search_config.search_mode == SearchMode.HYBRID:
                try:
                    local_results = await self.vector_db.hybrid_search(
                        query_text=query_text,
                        query_embedding=query_embedding,
                        user_id=user_id,
                        config=search_config
                    )
                    
                    if local_results:
                        self.logger.debug(f"Local hybrid search returned {len(local_results)} results")
                        return {
                            'success': True,
                            'results': local_results,
                            'method': 'local_hybrid',
                            'total_results': len(local_results),
                            'search_mode': search_config.search_mode.value,
                            'ranking_method': search_config.ranking_method.value
                        }
                    
                except Exception as e:
                    self.logger.warning(f"Local hybrid search failed: {e}")
            
            # Strategy 2: Use separate semantic and lexical searches
            semantic_results = []
            lexical_results = []
            
            # Parallel execution of different search methods
            tasks = []
            
            # Local vector search
            if self.vector_db and search_config.search_mode in [SearchMode.SEMANTIC, SearchMode.HYBRID]:
                tasks.append(self._local_semantic_search(query_embedding, user_id, search_config))
            
            # Local text search  
            if self.vector_db and search_config.search_mode in [SearchMode.LEXICAL, SearchMode.HYBRID]:
                tasks.append(self._local_text_search(query_text, user_id, search_config))
            
            # ISA fallback search
            if self.use_isa_fallback:
                tasks.append(self._isa_fallback_search(query_text, user_id, search_config))
            
            # Execute searches in parallel
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.warning(f"Search task {i} failed: {result}")
                        continue
                    
                    if result.get('method') == 'local_semantic':
                        semantic_results = result.get('results', [])
                    elif result.get('method') == 'local_text':
                        lexical_results = result.get('results', [])
                    elif result.get('method') == 'isa_fallback':
                        # Use ISA results as fallback if local searches failed
                        if not semantic_results and not lexical_results:
                            return result
            
            # Fuse results if we have both semantic and lexical
            if semantic_results or lexical_results:
                fused_results = self._fuse_search_results(
                    semantic_results, lexical_results, search_config
                )
                
                return {
                    'success': True,
                    'results': fused_results,
                    'method': 'local_fused',
                    'semantic_count': len(semantic_results),
                    'lexical_count': len(lexical_results),
                    'total_results': len(fused_results),
                    'search_mode': search_config.search_mode.value,
                    'ranking_method': search_config.ranking_method.value
                }
            
            # Strategy 3: ISA fallback if all else fails
            if self.use_isa_fallback:
                return await self._isa_fallback_search(query_text, user_id, search_config)
            
            # No results found
            return {
                'success': True,
                'results': [],
                'method': 'none',
                'total_results': 0,
                'message': 'No search backends available or returned results'
            }
            
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'error'
            }
    
    async def _local_semantic_search(
        self,
        query_embedding: List[float],
        user_id: str,
        config: VectorSearchConfig
    ) -> Dict[str, Any]:
        """Perform local semantic search."""
        try:
            if not self.vector_db:
                return {'method': 'local_semantic', 'results': []}
            
            results = await self.vector_db.search_vectors(
                query_embedding=query_embedding,
                user_id=user_id,
                config=config
            )
            
            return {
                'method': 'local_semantic',
                'results': results,
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"Local semantic search failed: {e}")
            return {'method': 'local_semantic', 'results': [], 'error': str(e)}
    
    async def _local_text_search(
        self,
        query_text: str,
        user_id: str,
        config: VectorSearchConfig
    ) -> Dict[str, Any]:
        """Perform local text search."""
        try:
            if not self.vector_db:
                return {'method': 'local_text', 'results': []}
            
            results = await self.vector_db.search_text(
                query_text=query_text,
                user_id=user_id,
                config=config
            )
            
            return {
                'method': 'local_text',
                'results': results,
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"Local text search failed: {e}")
            return {'method': 'local_text', 'results': [], 'error': str(e)}
    
    async def _isa_fallback_search(
        self,
        query_text: str,
        user_id: str,
        config: VectorSearchConfig
    ) -> Dict[str, Any]:
        """Perform ISA fallback search using existing embedding_generator."""
        try:
            # First, get user's knowledge base from local database
            if self.vector_db:
                # Get all user texts for ISA search
                all_vectors = await self.vector_db.list_vectors(
                    user_id=user_id,
                    limit=1000  # Reasonable limit for ISA processing
                )
                
                if all_vectors:
                    # Extract texts for ISA similarity search
                    candidate_texts = [v.text for v in all_vectors]
                    
                    # Use ISA similarity search
                    isa_results = await embedding_generator.find_most_similar(
                        query_text=query_text,
                        candidate_texts=candidate_texts,
                        top_k=config.top_k
                    )
                    
                    # Convert ISA results to SearchResult format
                    search_results = []
                    for text, similarity_score in isa_results:
                        # Find matching vector for additional metadata
                        matching_vector = next(
                            (v for v in all_vectors if v.text == text), None
                        )
                        
                        search_result = SearchResult(
                            id=matching_vector.id if matching_vector else f"isa_{hash(text)}",
                            text=text,
                            score=similarity_score,
                            semantic_score=similarity_score,
                            metadata=matching_vector.metadata if matching_vector else {}
                        )
                        search_results.append(search_result)
                    
                    return {
                        'method': 'isa_fallback',
                        'results': search_results,
                        'success': True,
                        'isa_candidate_count': len(candidate_texts)
                    }
            
            return {
                'method': 'isa_fallback',
                'results': [],
                'success': True,
                'message': 'No candidates for ISA search'
            }
            
        except Exception as e:
            self.logger.error(f"ISA fallback search failed: {e}")
            return {
                'method': 'isa_fallback',
                'results': [],
                'error': str(e)
            }
    
    def _fuse_search_results(
        self,
        semantic_results: List[SearchResult],
        lexical_results: List[SearchResult],
        config: VectorSearchConfig
    ) -> List[SearchResult]:
        """
        Fuse semantic and lexical search results.
        
        Uses the ranking method specified in config.
        """
        try:
            if not semantic_results and not lexical_results:
                return []
            
            if not semantic_results:
                return lexical_results[:config.top_k]
            
            if not lexical_results:
                return semantic_results[:config.top_k]
            
            # Use the base class fusion methods via a temporary vector_db instance
            if self.vector_db:
                if config.ranking_method == RankingMethod.RRF:
                    return self.vector_db._reciprocal_rank_fusion(
                        semantic_results, lexical_results, config
                    )
                elif config.ranking_method == RankingMethod.WEIGHTED:
                    return self.vector_db._weighted_fusion(
                        semantic_results, lexical_results, config
                    )
                elif config.ranking_method == RankingMethod.MMR:
                    return self.vector_db._max_marginal_relevance(
                        semantic_results, lexical_results, config
                    )
            
            # Simple fallback fusion
            return self._simple_fusion(semantic_results, lexical_results, config)
            
        except Exception as e:
            self.logger.error(f"Result fusion failed: {e}")
            # Return semantic results as fallback
            return semantic_results[:config.top_k]
    
    def _simple_fusion(
        self,
        semantic_results: List[SearchResult],
        lexical_results: List[SearchResult],
        config: VectorSearchConfig
    ) -> List[SearchResult]:
        """Simple fusion as fallback when advanced methods fail."""
        try:
            # Combine and deduplicate by ID
            combined_map = {}
            
            # Add semantic results
            for result in semantic_results:
                combined_map[result.id] = result
            
            # Add lexical results (may override or merge with semantic)
            for result in lexical_results:
                if result.id in combined_map:
                    # Average the scores
                    existing = combined_map[result.id]
                    existing.score = (existing.score + result.score) / 2
                    existing.lexical_score = result.score
                else:
                    combined_map[result.id] = result
            
            # Sort by score and return top_k
            fused_results = list(combined_map.values())
            fused_results.sort(key=lambda x: x.score, reverse=True)
            return fused_results[:config.top_k]
            
        except Exception as e:
            self.logger.error(f"Simple fusion failed: {e}")
            return semantic_results[:config.top_k]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        try:
            stats = {
                'service': 'HybridSearchService',
                'use_local_db': self.use_local_db,
                'use_isa_fallback': self.use_isa_fallback,
                'local_db_available': self.vector_db is not None
            }
            
            if self.vector_db:
                local_stats = await self.vector_db.get_stats()
                stats['local_db_stats'] = local_stats
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}

# Global instance
hybrid_search_service = HybridSearchService()