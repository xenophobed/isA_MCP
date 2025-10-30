#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Search Data Models
Core data structures for deep search functionality
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


class QueryComplexity(str, Enum):
    """Query complexity levels"""
    SIMPLE = "simple"           # Factual, single-concept queries
    MEDIUM = "medium"           # Comparison, multi-concept queries
    HIGH = "high"              # Research, analysis queries
    EXPERT = "expert"          # Multi-faceted, deep research


class QueryDomain(str, Enum):
    """Query domain classification"""
    GENERAL = "general"
    TECHNICAL = "technical"
    ACADEMIC = "academic"
    BUSINESS = "business"
    MEDICAL = "medical"
    LEGAL = "legal"
    NEWS = "news"
    ENTERTAINMENT = "entertainment"


class QueryType(str, Enum):
    """Type of query intent"""
    FACTUAL = "factual"              # "What is X?"
    PROCEDURAL = "procedural"        # "How to do X?"
    COMPARISON = "comparison"        # "X vs Y"
    RESEARCH = "research"            # "Research on X"
    OPINION = "opinion"              # "Best X for Y"
    CURRENT_EVENTS = "current_events"  # "Latest X"


class RAGMode(str, Enum):
    """RAG reasoning modes with estimated execution time"""
    AUTO = "auto"              # Automatically select based on query
    SIMPLE = "simple"          # Fast, single-pass (~12s)
    SELF_RAG = "self_rag"     # Self-critique with verification (~20s)
    PLAN_RAG = "plan_rag"     # Multi-step planning (~40s)
    CRAG = "crag"             # Corrective RAG for fact-checking (~30s)
    GRAPH_RAG = "graph_rag"   # Knowledge graph relationships (~60s)


class SearchStrategy(str, Enum):
    """Search strategy types"""
    FRESH_WEB = "fresh_web"           # Recent web results
    ACADEMIC = "academic"             # Academic/technical sources
    DISCUSSIONS = "discussions"       # Forums, Reddit, Stack Overflow
    TECHNICAL_DOCS = "technical_docs" # Documentation sites
    NEWS = "news"                     # News articles
    VIDEOS = "videos"                 # Video content


@dataclass
class QueryProfile:
    """
    Query analysis profile
    Used by QueryAnalyzer to characterize queries and recommend strategies
    """
    query: str
    complexity: QueryComplexity
    domain: QueryDomain
    query_type: QueryType

    # Recommendations
    estimated_depth: int                      # Recommended search depth (1-3)
    recommended_rag: RAGMode                  # Recommended RAG mode
    search_strategies: List[SearchStrategy]   # Recommended search strategies

    # Analysis metadata
    requires_fact_checking: bool = False
    is_multi_faceted: bool = False
    needs_recent_data: bool = False
    confidence_score: float = 0.0             # 0.0-1.0


@dataclass
class SearchStrategyConfig:
    """Configuration for a single search strategy"""
    strategy: SearchStrategy
    params: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0  # Weight for result fusion (0.0-1.0)


@dataclass
class FusedSearchResult:
    """
    Search result after multi-strategy fusion
    Combines results from multiple strategies with unified scoring
    """
    url: str
    title: str
    snippet: str

    # Fusion metadata
    fusion_score: float                       # Final fused score (0.0-1.0)
    strategy_scores: Dict[str, float]         # Score from each strategy
    strategy_ranks: Dict[str, int]            # Rank in each strategy
    source_strategies: List[SearchStrategy]   # Strategies that found this result

    # Original data
    original_score: float = 0.0
    result_type: str = "web"
    all_content: str = ""


@dataclass
class DeepSearchConfig:
    """Configuration for deep search execution"""
    query: str
    user_id: str

    # Search parameters
    depth: int = 2                            # Number of iterations (1-3)
    max_results_per_level: int = 10          # Results per iteration

    # Strategy configuration
    strategies: List[SearchStrategyConfig] = field(default_factory=list)
    fusion_method: str = "reciprocal_rank_fusion"  # Result fusion algorithm

    # RAG parameters
    rag_mode: RAGMode = RAGMode.AUTO
    include_citations: bool = True
    citation_style: str = "inline"

    # Query refinement
    enable_query_expansion: bool = True
    enable_query_refinement: bool = True

    # Control parameters
    max_total_time: int = 120                # Maximum execution time (seconds)
    enable_early_stopping: bool = False      # Stop when sufficient results found
    quality_threshold: float = 0.7           # Minimum quality score

    # Progress reporting
    progress_callback: Optional[Any] = None  # Async callback for progress updates


@dataclass
class DeepSearchResult:
    """Complete deep search result with all metadata"""
    success: bool
    query: str

    # Search results
    results: List[FusedSearchResult]
    total_results: int

    # Summary and synthesis
    summary: Optional[Dict[str, Any]] = None

    # Execution metadata
    execution_time: float = 0.0
    depth_completed: int = 0
    strategies_used: List[SearchStrategy] = field(default_factory=list)
    rag_mode_used: RAGMode = RAGMode.SIMPLE
    query_profile: Optional[QueryProfile] = None

    # Iteration tracking
    iterations: List[Dict[str, Any]] = field(default_factory=list)

    # Error handling
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class IterationResult:
    """Result from a single search iteration"""
    iteration_number: int
    query_used: str
    strategies_executed: List[SearchStrategy]
    results: List[FusedSearchResult]
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# Helper functions for model conversion

def complexity_from_score(score: float) -> QueryComplexity:
    """Convert numeric complexity score to enum"""
    if score >= 0.8:
        return QueryComplexity.EXPERT
    elif score >= 0.6:
        return QueryComplexity.HIGH
    elif score >= 0.4:
        return QueryComplexity.MEDIUM
    else:
        return QueryComplexity.SIMPLE


def estimate_execution_time(rag_mode: RAGMode, depth: int) -> int:
    """Estimate execution time in seconds"""
    base_times = {
        RAGMode.SIMPLE: 12,
        RAGMode.SELF_RAG: 20,
        RAGMode.CRAG: 30,
        RAGMode.PLAN_RAG: 40,
        RAGMode.GRAPH_RAG: 60
    }

    base = base_times.get(rag_mode, 12)
    return base * depth
