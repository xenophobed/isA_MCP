#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Search Orchestrator
Main component that coordinates query analysis, multi-strategy search, and iterative refinement
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from core.logging import get_logger

from .models import (
    DeepSearchConfig,
    DeepSearchResult,
    IterationResult,
    RAGMode,
    SearchStrategy,
    SearchStrategyConfig,
    FusedSearchResult,
    estimate_execution_time
)
from .query_analyzer import QueryAnalyzer
from .multi_strategy_search import MultiStrategySearch
from ..engines.search_engine import SearchEngine

logger = get_logger(__name__)


class DeepSearchOrchestrator:
    """
    Orchestrates deep search operations

    Flow:
    1. Analyze query (complexity, domain, recommended strategies)
    2. For each depth level:
       a. Execute multi-strategy search
       b. Fuse results
       c. Refine query if needed
    3. Generate final summary with RAG
    """

    def __init__(self, search_engine: SearchEngine):
        """
        Initialize orchestrator

        Args:
            search_engine: Configured search engine instance
        """
        self.search_engine = search_engine
        self.query_analyzer = QueryAnalyzer()
        self.multi_strategy_search = MultiStrategySearch(search_engine)

    async def execute_deep_search(
        self,
        config: DeepSearchConfig
    ) -> DeepSearchResult:
        """
        Execute deep search with query analysis and multi-strategy fusion

        Args:
            config: Deep search configuration

        Returns:
            DeepSearchResult with all metadata
        """
        start_time = time.time()

        try:
            logger.info(f"🚀 Starting deep search: '{config.query}' (depth={config.depth})")

            # Stage 1: Query Analysis
            if config.progress_callback:
                await config.progress_callback("analyzing_query", 0.1)

            query_profile = self.query_analyzer.analyze(config.query)

            logger.info(
                f"📊 Query analyzed: complexity={query_profile.complexity}, "
                f"domain={query_profile.domain}, type={query_profile.query_type}"
            )

            # Determine RAG mode (use config or auto-select)
            if config.rag_mode == RAGMode.AUTO:
                rag_mode = query_profile.recommended_rag
                logger.info(f"🤖 Auto-selected RAG mode: {rag_mode}")
            else:
                rag_mode = config.rag_mode

            # Determine strategies (use config or use analyzer recommendations)
            if not config.strategies:
                # Create default strategies from query profile
                strategies = self.multi_strategy_search.create_default_strategies(
                    query_profile.search_strategies,
                    equal_weight=True
                )
                logger.info(f"📋 Auto-selected strategies: {[s.strategy.value for s in strategies]}")
            else:
                strategies = config.strategies

            # Stage 2: Multi-Strategy Search (iterative)
            all_fused_results = []
            iterations = []
            current_query = config.query

            for iteration in range(1, config.depth + 1):
                logger.info(f"🔄 Iteration {iteration}/{config.depth}: searching '{current_query}'")

                if config.progress_callback:
                    progress = 0.1 + (0.6 * (iteration / config.depth))
                    await config.progress_callback(f"searching_iteration_{iteration}", progress)

                # Execute multi-strategy search
                search_result = await self.multi_strategy_search.search_multi_strategy(
                    query=current_query,
                    strategies=strategies,
                    max_results_per_strategy=config.max_results_per_level,
                    fusion_method=config.fusion_method,
                    max_final_results=config.max_results_per_level,
                    progress_callback=config.progress_callback
                )

                if not search_result.get('success'):
                    logger.warning(f"Iteration {iteration} failed: {search_result.get('error')}")
                    break

                # Get fused results
                iteration_results = search_result['fused_results']
                all_fused_results.extend(iteration_results)

                # Store iteration metadata
                iteration_data = IterationResult(
                    iteration_number=iteration,
                    query_used=current_query,
                    strategies_executed=[s.strategy for s in strategies],
                    results=iteration_results,
                    execution_time=time.time() - start_time,
                    metadata=search_result.get('fusion_stats', {})
                )
                iterations.append(iteration_data)

                logger.info(
                    f"✅ Iteration {iteration} complete: {len(iteration_results)} results, "
                    f"{search_result.get('fusion_stats', {}).get('unique_domains', 0)} unique domains"
                )

                # Query refinement for next iteration
                if iteration < config.depth and config.enable_query_refinement:
                    current_query = self._refine_query(
                        original_query=config.query,
                        iteration_results=iteration_results,
                        iteration_number=iteration
                    )
                    logger.info(f"🔍 Refined query for next iteration: '{current_query}'")

            # Stage 3: De-duplicate and re-rank all results
            if config.progress_callback:
                await config.progress_callback("finalizing_results", 0.8)

            final_results = self._deduplicate_results(all_fused_results)
            final_results = final_results[:config.max_results_per_level * config.depth]

            logger.info(f"📦 Final results: {len(final_results)} unique results")

            # Build result object
            execution_time = time.time() - start_time

            result = DeepSearchResult(
                success=True,
                query=config.query,
                results=final_results,
                total_results=len(final_results),
                execution_time=execution_time,
                depth_completed=len(iterations),
                strategies_used=query_profile.search_strategies,
                rag_mode_used=rag_mode,
                query_profile=query_profile,
                iterations=[{
                    'iteration': it.iteration_number,
                    'query': it.query_used,
                    'results': len(it.results),
                    'strategies': [s.value for s in it.strategies_executed],
                    'metadata': it.metadata
                } for it in iterations]
            )

            logger.info(
                f"✅ Deep search complete: {len(final_results)} results in {execution_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"❌ Deep search failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            execution_time = time.time() - start_time

            return DeepSearchResult(
                success=False,
                query=config.query,
                results=[],
                total_results=0,
                execution_time=execution_time,
                error=str(e)
            )

    def _refine_query(
        self,
        original_query: str,
        iteration_results: List[FusedSearchResult],
        iteration_number: int
    ) -> str:
        """
        Refine query for next iteration based on current results

        Simple heuristic refinement:
        - Iteration 1: Add "explained" or "guide"
        - Iteration 2: Add "advanced" or "detailed"

        Future: Use LLM for intelligent query expansion
        """
        if iteration_number == 1:
            # First refinement: add explanatory terms
            refinements = ["explained", "guide", "tutorial", "overview"]
            return f"{original_query} {refinements[iteration_number % len(refinements)]}"

        elif iteration_number == 2:
            # Second refinement: add depth terms
            refinements = ["advanced", "detailed", "comprehensive", "in-depth"]
            return f"{original_query} {refinements[iteration_number % len(refinements)]}"

        else:
            # Use original query
            return original_query

    def _deduplicate_results(
        self,
        results: List[FusedSearchResult]
    ) -> List[FusedSearchResult]:
        """
        Remove duplicate URLs and keep highest-scored version

        Args:
            results: List of fused results (possibly with duplicates)

        Returns:
            Deduplicated list sorted by fusion score
        """
        # Group by URL, keep highest score
        url_to_best_result = {}

        for result in results:
            url = result.url

            if url not in url_to_best_result:
                url_to_best_result[url] = result
            else:
                # Keep result with higher fusion score
                if result.fusion_score > url_to_best_result[url].fusion_score:
                    # Merge strategy information
                    existing = url_to_best_result[url]

                    # Combine strategies
                    combined_strategies = list(set(
                        existing.source_strategies + result.source_strategies
                    ))

                    # Merge scores
                    combined_scores = {**existing.strategy_scores, **result.strategy_scores}
                    combined_ranks = {**existing.strategy_ranks, **result.strategy_ranks}

                    # Update result
                    result.source_strategies = combined_strategies
                    result.strategy_scores = combined_scores
                    result.strategy_ranks = combined_ranks

                    url_to_best_result[url] = result

        # Convert back to list and sort
        deduped = list(url_to_best_result.values())
        deduped.sort(key=lambda x: x.fusion_score, reverse=True)

        return deduped

    def estimate_search_time(
        self,
        config: DeepSearchConfig,
        query_profile: Optional[Any] = None
    ) -> int:
        """
        Estimate deep search execution time

        Args:
            config: Deep search configuration
            query_profile: Optional query profile (will analyze if not provided)

        Returns:
            Estimated time in seconds
        """
        # Base time for multi-strategy search per iteration
        base_search_time = 5  # seconds per iteration

        # Strategy overhead
        strategy_count = len(config.strategies) if config.strategies else 3
        strategy_overhead = strategy_count * 2  # 2s per strategy

        # RAG mode time
        rag_time = estimate_execution_time(config.rag_mode, config.depth)

        # Total estimate
        total_time = (base_search_time + strategy_overhead) * config.depth + rag_time

        return min(total_time, config.max_total_time)
