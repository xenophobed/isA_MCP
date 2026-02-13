#!/usr/bin/env python3
"""
Max Marginal Relevance (MMR) Reranker

Advanced reranking algorithms for diversity-aware search result optimization.
Combines relevance with diversity to reduce redundancy in search results.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
import math
from dataclasses import dataclass

from .base_vector_db import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class MMRConfig:
    """Configuration for MMR reranking"""

    lambda_param: float = 0.5  # Balance between relevance and diversity (0-1)
    diversity_threshold: float = 0.7  # Similarity threshold for diversity filtering
    max_iterations: int = 100  # Maximum iterations to prevent infinite loops
    min_diversity_score: float = 0.1  # Minimum diversity score to consider
    use_semantic_diversity: bool = True  # Use embedding-based diversity
    use_lexical_diversity: bool = True  # Use text-based diversity


class MMRReranker:
    """
    Max Marginal Relevance reranker for diversity-aware result selection.

    MMR Formula:
    score = λ * relevance - (1-λ) * max_similarity_to_selected

    Features:
    - Embedding-based semantic diversity
    - Text-based lexical diversity
    - Configurable relevance/diversity balance
    - Multiple similarity metrics
    """

    def __init__(self, config: Optional[MMRConfig] = None):
        """
        Initialize MMR reranker.

        Args:
            config: MMR configuration
        """
        self.config = config or MMRConfig()
        self.logger = logger

    def rerank_results(
        self,
        search_results: List[SearchResult],
        target_count: Optional[int] = None,
        lambda_param: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        Rerank search results using MMR for diversity.

        Args:
            search_results: Original search results
            target_count: Target number of results (default: same as input)
            lambda_param: Override lambda parameter

        Returns:
            Reranked results with diversity optimization
        """
        try:
            if not search_results:
                return []

            if len(search_results) <= 1:
                return search_results

            target_count = target_count or len(search_results)
            lambda_param = lambda_param or self.config.lambda_param

            # Initialize result containers
            selected_results = []
            remaining_results = search_results.copy()

            # Select the first result (highest relevance)
            if remaining_results:
                best_result = max(remaining_results, key=lambda x: x.score)
                selected_results.append(best_result)
                remaining_results.remove(best_result)

            # Iteratively select results using MMR
            iteration = 0
            while (
                remaining_results
                and len(selected_results) < target_count
                and iteration < self.config.max_iterations
            ):
                best_mmr_score = -float("inf")
                best_candidate = None
                best_index = -1

                for i, candidate in enumerate(remaining_results):
                    # Calculate MMR score for this candidate
                    mmr_score = self._calculate_mmr_score(candidate, selected_results, lambda_param)

                    if mmr_score > best_mmr_score:
                        best_mmr_score = mmr_score
                        best_candidate = candidate
                        best_index = i

                # Add the best candidate
                if best_candidate and best_mmr_score > self.config.min_diversity_score:
                    selected_results.append(best_candidate)
                    remaining_results.pop(best_index)
                else:
                    # No more suitable candidates
                    break

                iteration += 1

            self.logger.debug(
                f"MMR reranking: {len(search_results)} → {len(selected_results)} results, "
                f"λ={lambda_param:.2f}, iterations={iteration}"
            )

            return selected_results

        except Exception as e:
            self.logger.error(f"MMR reranking failed: {e}")
            # Return original results if reranking fails
            return search_results[:target_count] if target_count else search_results

    def _calculate_mmr_score(
        self, candidate: SearchResult, selected_results: List[SearchResult], lambda_param: float
    ) -> float:
        """
        Calculate MMR score for a candidate result.

        Args:
            candidate: Candidate search result
            selected_results: Already selected results
            lambda_param: Relevance vs diversity balance

        Returns:
            MMR score
        """
        try:
            # Relevance component (normalized)
            relevance = candidate.score

            # Diversity component (max similarity to selected results)
            max_similarity = 0.0

            if selected_results:
                similarities = []

                for selected in selected_results:
                    similarity = self._calculate_similarity(candidate, selected)
                    similarities.append(similarity)

                max_similarity = max(similarities) if similarities else 0.0

            # MMR formula
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity

            return mmr_score

        except Exception as e:
            self.logger.error(f"MMR score calculation failed: {e}")
            return candidate.score  # Fallback to original relevance

    def _calculate_similarity(self, result1: SearchResult, result2: SearchResult) -> float:
        """
        Calculate similarity between two search results.

        Uses multiple similarity metrics and combines them.
        """
        try:
            similarities = []

            # Semantic similarity (embedding-based)
            if self.config.use_semantic_diversity and result1.embedding and result2.embedding:
                semantic_sim = self._cosine_similarity(result1.embedding, result2.embedding)
                similarities.append(semantic_sim)

            # Lexical similarity (text-based)
            if self.config.use_lexical_diversity:
                lexical_sim = self._text_similarity(result1.text, result2.text)
                similarities.append(lexical_sim)

            # Metadata similarity
            metadata_sim = self._metadata_similarity(result1.metadata or {}, result2.metadata or {})
            similarities.append(metadata_sim)

            # Average the similarities
            if similarities:
                return sum(similarities) / len(similarities)
            else:
                return 0.0

        except Exception as e:
            self.logger.error(f"Similarity calculation failed: {e}")
            return 0.0

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
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

    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate lexical similarity between two texts.

        Uses Jaccard similarity of word sets.
        """
        try:
            # Simple word-based Jaccard similarity
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())

            if not words1 and not words2:
                return 1.0

            intersection = len(words1 & words2)
            union = len(words1 | words2)

            return intersection / union if union > 0 else 0.0

        except Exception:
            return 0.0

    def _metadata_similarity(self, meta1: Dict[str, Any], meta2: Dict[str, Any]) -> float:
        """
        Calculate similarity between metadata dictionaries.

        Uses Jaccard similarity of key-value pairs.
        """
        try:
            if not meta1 and not meta2:
                return 1.0

            # Convert to sets of (key, value) tuples
            items1 = set(meta1.items())
            items2 = set(meta2.items())

            intersection = len(items1 & items2)
            union = len(items1 | items2)

            return intersection / union if union > 0 else 0.0

        except Exception:
            return 0.0

    def rerank_with_custom_diversity(
        self,
        search_results: List[SearchResult],
        diversity_function: callable,
        target_count: Optional[int] = None,
        lambda_param: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        Rerank with custom diversity function.

        Args:
            search_results: Original search results
            diversity_function: Custom function to calculate diversity
            target_count: Target number of results
            lambda_param: Relevance vs diversity balance

        Returns:
            Reranked results
        """
        try:
            if not search_results:
                return []

            target_count = target_count or len(search_results)
            lambda_param = lambda_param or self.config.lambda_param

            selected_results = []
            remaining_results = search_results.copy()

            # Select first result
            if remaining_results:
                best_result = max(remaining_results, key=lambda x: x.score)
                selected_results.append(best_result)
                remaining_results.remove(best_result)

            # Custom MMR selection
            while remaining_results and len(selected_results) < target_count:
                best_score = -float("inf")
                best_candidate = None
                best_index = -1

                for i, candidate in enumerate(remaining_results):
                    # Use custom diversity function
                    max_similarity = max(
                        [diversity_function(candidate, selected) for selected in selected_results],
                        default=0.0,
                    )

                    # MMR score with custom diversity
                    mmr_score = lambda_param * candidate.score - (1 - lambda_param) * max_similarity

                    if mmr_score > best_score:
                        best_score = mmr_score
                        best_candidate = candidate
                        best_index = i

                if best_candidate:
                    selected_results.append(best_candidate)
                    remaining_results.pop(best_index)
                else:
                    break

            return selected_results

        except Exception as e:
            self.logger.error(f"Custom MMR reranking failed: {e}")
            return search_results[:target_count] if target_count else search_results


# Global instance
mmr_reranker = MMRReranker()


# Convenience functions
def rerank_with_mmr(
    search_results: List[SearchResult],
    lambda_param: float = 0.5,
    target_count: Optional[int] = None,
) -> List[SearchResult]:
    """Convenience function for MMR reranking."""
    return mmr_reranker.rerank_results(
        search_results, target_count=target_count, lambda_param=lambda_param
    )


def create_diversity_function(metric: str = "combined") -> callable:
    """
    Create a diversity function for custom reranking.

    Args:
        metric: "semantic", "lexical", "metadata", or "combined"

    Returns:
        Diversity function
    """

    def semantic_diversity(result1: SearchResult, result2: SearchResult) -> float:
        if result1.embedding and result2.embedding:
            return mmr_reranker._cosine_similarity(result1.embedding, result2.embedding)
        return 0.0

    def lexical_diversity(result1: SearchResult, result2: SearchResult) -> float:
        return mmr_reranker._text_similarity(result1.text, result2.text)

    def metadata_diversity(result1: SearchResult, result2: SearchResult) -> float:
        return mmr_reranker._metadata_similarity(result1.metadata or {}, result2.metadata or {})

    def combined_diversity(result1: SearchResult, result2: SearchResult) -> float:
        return mmr_reranker._calculate_similarity(result1, result2)

    return {
        "semantic": semantic_diversity,
        "lexical": lexical_diversity,
        "metadata": metadata_diversity,
        "combined": combined_diversity,
    }.get(metric, combined_diversity)
