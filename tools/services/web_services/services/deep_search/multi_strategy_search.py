#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Strategy Search Engine
Executes search across multiple strategies in parallel and fuses results
"""

import asyncio
from typing import List, Dict, Any, Optional
from core.logging import get_logger

from .models import (
    SearchStrategy,
    SearchStrategyConfig,
    FusedSearchResult
)
from .result_fusion import ResultFusionEngine
from tools.services.web_services.engines.search_engine import SearchEngine, SearchFreshness, ResultFilter

logger = get_logger(__name__)


class MultiStrategySearch:
    """
    Executes searches across multiple strategies and fuses results

    Strategies:
    - FRESH_WEB: Recent web results (freshness=week)
    - ACADEMIC: Academic/technical sources (goggle_type=academic)
    - DISCUSSIONS: Forums, Reddit, Stack Overflow (result_filter=discussions)
    - TECHNICAL_DOCS: Documentation sites (goggle_type=technical)
    - NEWS: News articles (result_filter=news)
    - VIDEOS: Video content (result_filter=videos)
    """

    def __init__(self, search_engine: SearchEngine):
        """
        Initialize multi-strategy search

        Args:
            search_engine: Configured search engine instance
        """
        self.search_engine = search_engine
        self.fusion_engine = ResultFusionEngine(k=60)

    async def search_multi_strategy(
        self,
        query: str,
        strategies: List[SearchStrategyConfig],
        max_results_per_strategy: int = 10,
        fusion_method: str = "reciprocal_rank_fusion",
        max_final_results: int = 20,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Execute search across multiple strategies and fuse results

        Args:
            query: Search query
            strategies: List of strategy configurations
            max_results_per_strategy: Max results per strategy
            fusion_method: Fusion algorithm to use
            max_final_results: Max results after fusion
            progress_callback: Optional async callback for progress

        Returns:
            Dict with fused results and metadata
        """
        try:
            logger.info(f"Starting multi-strategy search: {len(strategies)} strategies")

            # Execute all strategies in parallel
            tasks = []
            for config in strategies:
                task = self._execute_strategy(
                    query,
                    config,
                    max_results_per_strategy
                )
                tasks.append(task)

            # Report progress: executing strategies
            if progress_callback:
                await progress_callback("executing_strategies", 0.3)

            # Gather results from all strategies
            strategy_results_list = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out errors and build results dict
            strategy_results = {}
            for i, result in enumerate(strategy_results_list):
                if isinstance(result, Exception):
                    logger.warning(f"Strategy {strategies[i].strategy} failed: {result}")
                    continue

                if result and result.get('results'):
                    strategy_results[strategies[i].strategy] = result['results']

            if not strategy_results:
                logger.error("All strategies failed")
                return {
                    'success': False,
                    'error': 'All search strategies failed',
                    'results': []
                }

            # Report progress: fusing results
            if progress_callback:
                await progress_callback("fusing_results", 0.6)

            # Fuse results
            fused_results = self.fusion_engine.fuse_results(
                strategy_results,
                strategies,
                method=fusion_method,
                max_results=max_final_results
            )

            # Get fusion statistics
            fusion_stats = self.fusion_engine.get_fusion_stats(fused_results)

            logger.info(
                f"Multi-strategy search complete: {len(fused_results)} fused results "
                f"from {len(strategy_results)} strategies"
            )

            return {
                'success': True,
                'query': query,
                'total_results': len(fused_results),
                'fused_results': fused_results,
                'strategies_used': [s.value for s in strategy_results.keys()],
                'fusion_stats': fusion_stats,
                'fusion_method': fusion_method
            }

        except Exception as e:
            logger.error(f"Multi-strategy search failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'results': []
            }

    async def _execute_strategy(
        self,
        query: str,
        config: SearchStrategyConfig,
        max_results: int
    ) -> Dict[str, Any]:
        """
        Execute a single search strategy

        Args:
            query: Search query
            config: Strategy configuration
            max_results: Max results to return

        Returns:
            Dict with search results
        """
        strategy = config.strategy
        params = config.params or {}

        try:
            logger.info(f"Executing strategy: {strategy.value}")

            # Build search parameters based on strategy
            search_kwargs = self._build_search_params(strategy, params, max_results)

            # Execute search
            results = await self.search_engine.search(query, **search_kwargs)

            # Convert SearchResult objects to dicts
            result_dicts = [
                {
                    'url': r.url,
                    'title': r.title,
                    'snippet': r.snippet,
                    'score': r.score,
                    'type': r.type,
                    'all_content': r.get_all_content()[:500]
                }
                for r in results
            ]

            logger.info(f"Strategy {strategy.value}: {len(result_dicts)} results")

            return {
                'strategy': strategy,
                'results': result_dicts,
                'count': len(result_dicts)
            }

        except Exception as e:
            logger.error(f"Strategy {strategy.value} failed: {e}")
            raise

    def _build_search_params(
        self,
        strategy: SearchStrategy,
        custom_params: Dict[str, Any],
        max_results: int
    ) -> Dict[str, Any]:
        """
        Build search parameters for a specific strategy

        Args:
            strategy: Search strategy enum
            custom_params: Custom parameters from config
            max_results: Maximum results

        Returns:
            Dict of search parameters
        """
        # Base parameters
        params = {
            'count': max_results,
            'extra_snippets': True
        }

        # Strategy-specific parameters
        if strategy == SearchStrategy.FRESH_WEB:
            params['freshness'] = SearchFreshness.WEEK

        elif strategy == SearchStrategy.ACADEMIC:
            params['goggle_type'] = 'academic'

        elif strategy == SearchStrategy.DISCUSSIONS:
            params['result_filter'] = ResultFilter.DISCUSSIONS

        elif strategy == SearchStrategy.TECHNICAL_DOCS:
            params['goggle_type'] = 'technical'

        elif strategy == SearchStrategy.NEWS:
            params['result_filter'] = ResultFilter.NEWS
            params['freshness'] = SearchFreshness.MONTH

        elif strategy == SearchStrategy.VIDEOS:
            params['result_filter'] = ResultFilter.VIDEOS

        # Override with custom params
        params.update(custom_params)

        return params

    def create_default_strategies(
        self,
        strategy_types: List[SearchStrategy],
        equal_weight: bool = True
    ) -> List[SearchStrategyConfig]:
        """
        Create default strategy configurations

        Args:
            strategy_types: List of strategy types to use
            equal_weight: If True, all strategies have weight 1.0

        Returns:
            List of SearchStrategyConfig objects
        """
        configs = []
        weight = 1.0 if equal_weight else None

        for strategy_type in strategy_types:
            # Set default weights if not equal
            if not equal_weight:
                # Prioritize fresh web and technical docs
                if strategy_type in [SearchStrategy.FRESH_WEB, SearchStrategy.TECHNICAL_DOCS]:
                    weight = 1.2
                elif strategy_type == SearchStrategy.DISCUSSIONS:
                    weight = 1.0
                elif strategy_type in [SearchStrategy.NEWS, SearchStrategy.VIDEOS]:
                    weight = 0.8
                else:
                    weight = 1.0

            config = SearchStrategyConfig(
                strategy=strategy_type,
                params={},
                weight=weight
            )
            configs.append(config)

        return configs
