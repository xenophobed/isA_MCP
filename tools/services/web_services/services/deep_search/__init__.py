#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Search Module
Advanced multi-strategy search with query analysis and result fusion
"""

from .models import (
    QueryComplexity,
    QueryDomain,
    QueryType,
    RAGMode,
    SearchStrategy,
    QueryProfile,
    SearchStrategyConfig,
    FusedSearchResult,
    DeepSearchConfig,
    DeepSearchResult,
    IterationResult,
    complexity_from_score,
    estimate_execution_time
)

from .query_analyzer import QueryAnalyzer
from .result_fusion import ResultFusionEngine
from .multi_strategy_search import MultiStrategySearch
from .orchestrator import DeepSearchOrchestrator

__all__ = [
    # Enums
    'QueryComplexity',
    'QueryDomain',
    'QueryType',
    'RAGMode',
    'SearchStrategy',

    # Data models
    'QueryProfile',
    'SearchStrategyConfig',
    'FusedSearchResult',
    'DeepSearchConfig',
    'DeepSearchResult',
    'IterationResult',

    # Components
    'QueryAnalyzer',
    'ResultFusionEngine',
    'MultiStrategySearch',
    'DeepSearchOrchestrator',

    # Utilities
    'complexity_from_score',
    'estimate_execution_time',
]

__version__ = '1.0.0'
