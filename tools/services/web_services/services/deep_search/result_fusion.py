#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Result Fusion Engine - Multi-strategy search result fusion
Implements Reciprocal Rank Fusion (RRF) and other merging algorithms
"""

from typing import List, Dict, Any
from collections import defaultdict
from core.logging import get_logger

from .models import (
    FusedSearchResult,
    SearchStrategy,
    SearchStrategyConfig
)

logger = get_logger(__name__)


class ResultFusionEngine:
    """
    Fuses results from multiple search strategies using advanced algorithms

    Implements:
    - Reciprocal Rank Fusion (RRF) - primary method
    - Weighted scoring
    - Duplicate detection and merging
    - Diversity optimization
    """

    def __init__(self, k: int = 60):
        """
        Initialize fusion engine

        Args:
            k: Constant for RRF algorithm (default: 60)
               Lower k = more emphasis on top results
               Higher k = more balanced across ranks
        """
        self.k = k

    def fuse_results(
        self,
        strategy_results: Dict[SearchStrategy, List[Dict[str, Any]]],
        strategy_configs: List[SearchStrategyConfig],
        method: str = "reciprocal_rank_fusion",
        max_results: int = 20
    ) -> List[FusedSearchResult]:
        """
        Fuse results from multiple strategies into unified ranked list

        Args:
            strategy_results: Dict mapping strategy to its search results
            strategy_configs: List of strategy configs with weights
            method: Fusion method - "reciprocal_rank_fusion" or "weighted"
            max_results: Maximum results to return

        Returns:
            List of fused results sorted by fusion score
        """
        if not strategy_results:
            logger.warning("No results to fuse")
            return []

        # Create weight map from configs
        weight_map = {
            config.strategy: config.weight
            for config in strategy_configs
        }

        if method == "reciprocal_rank_fusion":
            fused = self._reciprocal_rank_fusion(
                strategy_results, weight_map
            )
        elif method == "weighted":
            fused = self._weighted_fusion(
                strategy_results, weight_map
            )
        else:
            logger.warning(f"Unknown fusion method: {method}, using RRF")
            fused = self._reciprocal_rank_fusion(
                strategy_results, weight_map
            )

        # Sort by fusion score descending
        fused.sort(key=lambda x: x.fusion_score, reverse=True)

        # Apply diversity optimization
        fused = self._optimize_diversity(fused)

        # Limit results
        fused = fused[:max_results]

        logger.info(
            f"Fused {sum(len(r) for r in strategy_results.values())} results "
            f"from {len(strategy_results)} strategies into {len(fused)} unique results"
        )

        return fused

    def _reciprocal_rank_fusion(
        self,
        strategy_results: Dict[SearchStrategy, List[Dict[str, Any]]],
        weight_map: Dict[SearchStrategy, float]
    ) -> List[FusedSearchResult]:
        """
        Reciprocal Rank Fusion algorithm

        Formula: RRF_score = Σ (weight_i / (k + rank_i))

        Where:
        - weight_i = strategy weight (default: 1.0)
        - k = constant (typically 60)
        - rank_i = 1-based rank in strategy i

        Benefits:
        - Robust to outliers
        - No score normalization needed
        - Works well with different result set sizes
        """
        # Group results by URL
        url_to_result = defaultdict(lambda: {
            'strategy_scores': {},
            'strategy_ranks': {},
            'strategies': [],
            'data': None
        })

        # Process each strategy's results
        for strategy, results in strategy_results.items():
            weight = weight_map.get(strategy, 1.0)

            for rank, result in enumerate(results, start=1):
                url = result.get('url', '')
                if not url:
                    continue

                # RRF score contribution from this strategy
                rrf_contribution = weight / (self.k + rank)

                # Store metadata
                url_to_result[url]['strategy_scores'][strategy.value] = rrf_contribution
                url_to_result[url]['strategy_ranks'][strategy.value] = rank
                url_to_result[url]['strategies'].append(strategy)

                # Keep first occurrence data
                if url_to_result[url]['data'] is None:
                    url_to_result[url]['data'] = result

        # Create FusedSearchResult objects
        fused_results = []
        for url, meta in url_to_result.items():
            # Sum RRF scores from all strategies
            fusion_score = sum(meta['strategy_scores'].values())

            # Get original data
            data = meta['data']

            fused_result = FusedSearchResult(
                url=url,
                title=data.get('title', ''),
                snippet=data.get('snippet', ''),
                fusion_score=fusion_score,
                strategy_scores=meta['strategy_scores'],
                strategy_ranks=meta['strategy_ranks'],
                source_strategies=meta['strategies'],
                original_score=data.get('score', 0.0),
                result_type=data.get('type', 'web'),
                all_content=data.get('all_content', '')
            )

            fused_results.append(fused_result)

        return fused_results

    def _weighted_fusion(
        self,
        strategy_results: Dict[SearchStrategy, List[Dict[str, Any]]],
        weight_map: Dict[SearchStrategy, float]
    ) -> List[FusedSearchResult]:
        """
        Simple weighted score fusion

        Formula: weighted_score = Σ (weight_i × score_i)
        """
        url_to_result = defaultdict(lambda: {
            'strategy_scores': {},
            'strategy_ranks': {},
            'strategies': [],
            'data': None
        })

        for strategy, results in strategy_results.items():
            weight = weight_map.get(strategy, 1.0)

            for rank, result in enumerate(results, start=1):
                url = result.get('url', '')
                if not url:
                    continue

                score = result.get('score', 0.0)
                weighted_score = weight * score

                url_to_result[url]['strategy_scores'][strategy.value] = weighted_score
                url_to_result[url]['strategy_ranks'][strategy.value] = rank
                url_to_result[url]['strategies'].append(strategy)

                if url_to_result[url]['data'] is None:
                    url_to_result[url]['data'] = result

        fused_results = []
        for url, meta in url_to_result.items():
            fusion_score = sum(meta['strategy_scores'].values())
            data = meta['data']

            fused_result = FusedSearchResult(
                url=url,
                title=data.get('title', ''),
                snippet=data.get('snippet', ''),
                fusion_score=fusion_score,
                strategy_scores=meta['strategy_scores'],
                strategy_ranks=meta['strategy_ranks'],
                source_strategies=meta['strategies'],
                original_score=data.get('score', 0.0),
                result_type=data.get('type', 'web'),
                all_content=data.get('all_content', '')
            )

            fused_results.append(fused_result)

        return fused_results

    def _optimize_diversity(
        self,
        results: List[FusedSearchResult],
        diversity_threshold: float = 0.3
    ) -> List[FusedSearchResult]:
        """
        Optimize result diversity by penalizing very similar consecutive results

        Uses simple domain-level diversity check
        """
        if len(results) <= 1:
            return results

        optimized = [results[0]]  # Always include top result
        seen_domains = set([self._extract_domain(results[0].url)])

        for result in results[1:]:
            domain = self._extract_domain(result.url)

            # If domain already seen, apply small penalty to fusion score
            if domain in seen_domains:
                result.fusion_score *= (1.0 - diversity_threshold * 0.1)

            optimized.append(result)
            seen_domains.add(domain)

        # Re-sort after diversity adjustment
        optimized.sort(key=lambda x: x.fusion_score, reverse=True)

        return optimized

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for diversity checking"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return url

    def get_fusion_stats(
        self,
        fused_results: List[FusedSearchResult]
    ) -> Dict[str, Any]:
        """
        Calculate statistics about fusion results

        Returns metrics like:
        - Strategy contribution (% from each strategy)
        - Multi-strategy results (found by multiple strategies)
        - Average fusion score
        - Domain diversity
        """
        if not fused_results:
            return {}

        # Strategy contribution
        strategy_counts = defaultdict(int)
        for result in fused_results:
            for strategy in result.source_strategies:
                strategy_counts[strategy.value] += 1

        total_contributions = sum(strategy_counts.values())
        strategy_contribution = {
            strategy: (count / total_contributions) * 100
            for strategy, count in strategy_counts.items()
        }

        # Multi-strategy results
        multi_strategy_count = sum(
            1 for r in fused_results
            if len(r.source_strategies) > 1
        )

        # Average scores
        avg_fusion_score = sum(r.fusion_score for r in fused_results) / len(fused_results)

        # Domain diversity
        unique_domains = len(set(self._extract_domain(r.url) for r in fused_results))
        diversity_ratio = unique_domains / len(fused_results)

        return {
            'total_results': len(fused_results),
            'multi_strategy_results': multi_strategy_count,
            'multi_strategy_ratio': multi_strategy_count / len(fused_results),
            'strategy_contribution': strategy_contribution,
            'avg_fusion_score': avg_fusion_score,
            'unique_domains': unique_domains,
            'diversity_ratio': diversity_ratio
        }
