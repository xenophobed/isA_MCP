#!/usr/bin/env python3
"""
Base Vector Database Interface

Abstract base class for vector database implementations with hybrid search support.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SearchMode(Enum):
    """Search mode enumeration"""
    SEMANTIC = "semantic"      # Vector similarity search only
    LEXICAL = "lexical"        # BM25/full-text search only  
    HYBRID = "hybrid"          # Combined semantic + lexical search

class RankingMethod(Enum):
    """Ranking method for result fusion"""
    RRF = "rrf"                # Reciprocal Rank Fusion
    WEIGHTED = "weighted"      # Weighted average of scores
    MMR = "mmr"                # Max Marginal Relevance

@dataclass
class SearchResult:
    """Individual search result"""
    id: str
    text: str
    score: float
    semantic_score: Optional[float] = None
    lexical_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None

@dataclass 
class VectorSearchConfig:
    """Configuration for vector search operations"""
    top_k: int = 5
    search_mode: SearchMode = SearchMode.SEMANTIC
    ranking_method: RankingMethod = RankingMethod.RRF
    semantic_weight: float = 0.7
    lexical_weight: float = 0.3
    mmr_lambda: float = 0.5  # Diversity parameter for MMR
    include_embeddings: bool = False
    filter_metadata: Optional[Dict[str, Any]] = None

class BaseVectorDB(ABC):
    """
    Abstract base class for vector database implementations.
    
    Provides unified interface for:
    - Vector storage and retrieval
    - Semantic search via embeddings
    - Lexical search via BM25/full-text
    - Hybrid search with result fusion
    - User isolation and filtering
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize vector database.
        
        Args:
            config: Database-specific configuration
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def store_vector(
        self,
        id: str,
        text: str,
        embedding: List[float],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store a text with its embedding.
        
        Args:
            id: Unique identifier
            text: Original text content
            embedding: Vector embedding
            user_id: User identifier for isolation
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def search_vectors(
        self,
        query_embedding: List[float],
        user_id: str,
        config: VectorSearchConfig
    ) -> List[SearchResult]:
        """
        Search vectors using semantic similarity.
        
        Args:
            query_embedding: Query vector
            user_id: User identifier for filtering
            config: Search configuration
            
        Returns:
            List of search results
        """
        pass
    
    @abstractmethod
    async def search_text(
        self,
        query_text: str,
        user_id: str,
        config: VectorSearchConfig
    ) -> List[SearchResult]:
        """
        Search text using lexical/BM25 search.
        
        Args:
            query_text: Query text
            user_id: User identifier for filtering
            config: Search configuration
            
        Returns:
            List of search results
        """
        pass
    
    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        user_id: str,
        config: VectorSearchConfig
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining semantic and lexical results.
        
        Args:
            query_text: Query text for lexical search
            query_embedding: Query embedding for semantic search
            user_id: User identifier for filtering
            config: Search configuration
            
        Returns:
            Fused and ranked search results
        """
        try:
            # Execute both searches in parallel
            import asyncio
            
            semantic_task = self.search_vectors(query_embedding, user_id, config)
            lexical_task = self.search_text(query_text, user_id, config)
            
            semantic_results, lexical_results = await asyncio.gather(
                semantic_task, lexical_task, return_exceptions=True
            )
            
            # Handle potential exceptions
            if isinstance(semantic_results, Exception):
                self.logger.warning(f"Semantic search failed: {semantic_results}")
                semantic_results = []
            
            if isinstance(lexical_results, Exception):
                self.logger.warning(f"Lexical search failed: {lexical_results}")
                lexical_results = []
            
            # Fuse results using specified ranking method
            if config.ranking_method == RankingMethod.RRF:
                return self._reciprocal_rank_fusion(semantic_results, lexical_results, config)
            elif config.ranking_method == RankingMethod.WEIGHTED:
                return self._weighted_fusion(semantic_results, lexical_results, config)
            elif config.ranking_method == RankingMethod.MMR:
                return self._max_marginal_relevance(semantic_results, lexical_results, config)
            else:
                # Default to RRF
                return self._reciprocal_rank_fusion(semantic_results, lexical_results, config)
                
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            # Fallback to semantic search only
            return await self.search_vectors(query_embedding, user_id, config)
    
    def _reciprocal_rank_fusion(
        self,
        semantic_results: List[SearchResult],
        lexical_results: List[SearchResult],
        config: VectorSearchConfig,
        k: int = 60
    ) -> List[SearchResult]:
        """
        Fuse results using Reciprocal Rank Fusion (RRF).
        
        RRF Score = 1/(k + rank_semantic) + 1/(k + rank_lexical)
        """
        try:
            # Create lookup for efficient merging
            result_map = {}
            
            # Add semantic results
            for rank, result in enumerate(semantic_results):
                result_map[result.id] = {
                    'result': result,
                    'semantic_rank': rank + 1,
                    'lexical_rank': None
                }
            
            # Add lexical results
            for rank, result in enumerate(lexical_results):
                if result.id in result_map:
                    result_map[result.id]['lexical_rank'] = rank + 1
                else:
                    result_map[result.id] = {
                        'result': result,
                        'semantic_rank': None,
                        'lexical_rank': rank + 1
                    }
            
            # Calculate RRF scores
            fused_results = []
            for item_id, data in result_map.items():
                result = data['result']
                semantic_rank = data['semantic_rank'] or (len(semantic_results) + 1)
                lexical_rank = data['lexical_rank'] or (len(lexical_results) + 1)
                
                # RRF formula
                rrf_score = (1.0 / (k + semantic_rank)) + (1.0 / (k + lexical_rank))
                
                # Update result with RRF score and preserve original scores
                result.score = rrf_score
                if data['semantic_rank']:
                    result.semantic_score = semantic_results[data['semantic_rank'] - 1].score
                if data['lexical_rank']:
                    result.lexical_score = lexical_results[data['lexical_rank'] - 1].score
                
                fused_results.append(result)
            
            # Sort by RRF score descending and return top_k
            fused_results.sort(key=lambda x: x.score, reverse=True)
            return fused_results[:config.top_k]
            
        except Exception as e:
            self.logger.error(f"RRF fusion failed: {e}")
            # Fallback to semantic results
            return semantic_results[:config.top_k]
    
    def _weighted_fusion(
        self,
        semantic_results: List[SearchResult],
        lexical_results: List[SearchResult],
        config: VectorSearchConfig
    ) -> List[SearchResult]:
        """
        Fuse results using weighted average of normalized scores.
        """
        try:
            # Normalize scores to [0, 1] range
            def normalize_scores(results: List[SearchResult]) -> List[SearchResult]:
                if not results:
                    return results
                
                scores = [r.score for r in results]
                min_score, max_score = min(scores), max(scores)
                
                if max_score == min_score:
                    # All scores are the same
                    for result in results:
                        result.score = 1.0
                else:
                    for result in results:
                        result.score = (result.score - min_score) / (max_score - min_score)
                
                return results
            
            semantic_normalized = normalize_scores(semantic_results.copy())
            lexical_normalized = normalize_scores(lexical_results.copy())
            
            # Create result map
            result_map = {}
            
            # Add semantic results with weights
            for result in semantic_normalized:
                result_map[result.id] = {
                    'result': result,
                    'semantic_score': result.score,
                    'lexical_score': 0.0
                }
            
            # Add lexical results with weights
            for result in lexical_normalized:
                if result.id in result_map:
                    result_map[result.id]['lexical_score'] = result.score
                else:
                    result_map[result.id] = {
                        'result': result,
                        'semantic_score': 0.0,
                        'lexical_score': result.score
                    }
            
            # Calculate weighted scores
            fused_results = []
            for item_id, data in result_map.items():
                result = data['result']
                semantic_score = data['semantic_score']
                lexical_score = data['lexical_score']
                
                # Weighted combination
                weighted_score = (
                    config.semantic_weight * semantic_score +
                    config.lexical_weight * lexical_score
                )
                
                result.score = weighted_score
                result.semantic_score = semantic_score if semantic_score > 0 else None
                result.lexical_score = lexical_score if lexical_score > 0 else None
                
                fused_results.append(result)
            
            # Sort and return top_k
            fused_results.sort(key=lambda x: x.score, reverse=True)
            return fused_results[:config.top_k]
            
        except Exception as e:
            self.logger.error(f"Weighted fusion failed: {e}")
            return semantic_results[:config.top_k]
    
    def _max_marginal_relevance(
        self,
        semantic_results: List[SearchResult],
        lexical_results: List[SearchResult],
        config: VectorSearchConfig
    ) -> List[SearchResult]:
        """
        Apply Max Marginal Relevance for diversity-aware ranking.
        
        MMR = λ * Relevance(doc, query) - (1-λ) * max(Similarity(doc, selected_docs))
        """
        try:
            # First do regular fusion
            fused_results = self._reciprocal_rank_fusion(semantic_results, lexical_results, config)
            
            if len(fused_results) <= 1:
                return fused_results
            
            # Apply MMR for diversity
            mmr_results = []
            remaining_results = fused_results.copy()
            
            # Select first result (highest relevance)
            if remaining_results:
                best_result = remaining_results.pop(0)
                mmr_results.append(best_result)
            
            # Select remaining results using MMR
            while remaining_results and len(mmr_results) < config.top_k:
                best_mmr_score = -float('inf')
                best_result = None
                best_index = -1
                
                for i, candidate in enumerate(remaining_results):
                    # Calculate relevance (current score)
                    relevance = candidate.score
                    
                    # Calculate max similarity with already selected results
                    max_similarity = 0.0
                    if candidate.embedding:
                        for selected in mmr_results:
                            if selected.embedding:
                                similarity = self._cosine_similarity(
                                    candidate.embedding, selected.embedding
                                )
                                max_similarity = max(max_similarity, similarity)
                    
                    # MMR formula
                    mmr_score = (
                        config.mmr_lambda * relevance - 
                        (1 - config.mmr_lambda) * max_similarity
                    )
                    
                    if mmr_score > best_mmr_score:
                        best_mmr_score = mmr_score
                        best_result = candidate
                        best_index = i
                
                if best_result:
                    mmr_results.append(best_result)
                    remaining_results.pop(best_index)
                else:
                    break
            
            return mmr_results
            
        except Exception as e:
            self.logger.error(f"MMR ranking failed: {e}")
            return semantic_results[:config.top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            import math
            
            if len(vec1) != len(vec2):
                return 0.0
            
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            if magnitude1 == 0.0 or magnitude2 == 0.0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception:
            return 0.0
    
    @abstractmethod
    async def delete_vector(self, id: str, user_id: str) -> bool:
        """
        Delete a vector by ID.
        
        Args:
            id: Vector identifier
            user_id: User identifier for access control
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def get_vector(self, id: str, user_id: str) -> Optional[SearchResult]:
        """
        Get a specific vector by ID.
        
        Args:
            id: Vector identifier
            user_id: User identifier for access control
            
        Returns:
            Search result or None if not found
        """
        pass
    
    @abstractmethod
    async def list_vectors(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[SearchResult]:
        """
        List vectors for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum results to return
            offset: Results offset for pagination
            
        Returns:
            List of search results
        """
        pass
    
    @abstractmethod
    async def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Args:
            user_id: Optional user filter
            
        Returns:
            Statistics dictionary
        """
        pass