#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Query Analyzer - Intelligent query profiling for deep search
Analyzes queries to determine complexity, domain, and optimal search strategies
"""

import re
from typing import List, Optional
from core.logging import get_logger

from .models import (
    QueryProfile,
    QueryComplexity,
    QueryDomain,
    QueryType,
    RAGMode,
    SearchStrategy
)

logger = get_logger(__name__)


class QueryAnalyzer:
    """
    Analyzes queries to create comprehensive profiles for search optimization

    Uses pattern matching, keyword analysis, and heuristics to:
    - Determine query complexity (simple → expert)
    - Classify domain (technical, academic, business, etc.)
    - Identify query type (factual, procedural, research, etc.)
    - Recommend optimal RAG mode
    - Suggest search strategies
    """

    def __init__(self):
        """Initialize query analyzer with pattern dictionaries"""

        # Domain keywords
        self.domain_patterns = {
            QueryDomain.TECHNICAL: [
                r'\b(api|code|programming|algorithm|software|function|class|method)\b',
                r'\b(docker|kubernetes|database|server|framework|library)\b',
                r'\b(python|javascript|java|rust|go|typescript)\b'
            ],
            QueryDomain.ACADEMIC: [
                r'\b(research|study|paper|journal|academic|theory|analysis)\b',
                r'\b(university|professor|scholar|publication|peer.?review)\b',
                r'\b(hypothesis|methodology|empirical|statistical)\b'
            ],
            QueryDomain.MEDICAL: [
                r'\b(medical|health|disease|treatment|symptom|diagnosis|clinical)\b',
                r'\b(doctor|patient|medicine|drug|therapy|hospital)\b',
                r'\b(cancer|diabetes|infection|syndrome|disorder)\b'
            ],
            QueryDomain.LEGAL: [
                r'\b(law|legal|court|attorney|judge|lawsuit|regulation)\b',
                r'\b(contract|rights|statute|precedent|jurisdiction)\b',
                r'\b(compliance|liability|litigation|plaintiff|defendant)\b'
            ],
            QueryDomain.BUSINESS: [
                r'\b(business|market|company|revenue|profit|customer)\b',
                r'\b(strategy|management|sales|marketing|investment)\b',
                r'\b(startup|enterprise|b2b|roi|kpi)\b'
            ],
            QueryDomain.NEWS: [
                r'\b(news|latest|breaking|today|yesterday|current)\b',
                r'\b(update|announcement|report|happened|recent)\b',
                r'\b(2024|2025|this week|last month)\b'
            ]
        }

        # Query type patterns
        self.type_patterns = {
            QueryType.FACTUAL: [
                r'^(what|who|when|where|which)\b',
                r'\bdefin(e|ition)\b',
                r'\bmean(s|ing)?\b'
            ],
            QueryType.PROCEDURAL: [
                r'^how to\b',
                r'\b(steps?|guide|tutorial|instructions?)\b',
                r'\binstall\b|\bsetup\b|\bconfigure\b'
            ],
            QueryType.COMPARISON: [
                r'\b(vs|versus|compared? to|difference|better)\b',
                r'\b(pros? and cons?|advantages?|disadvantages?)\b',
                r'\b(alternative|instead of)\b'
            ],
            QueryType.RESEARCH: [
                r'\b(research|investigate|explore|analyze|study)\b',
                r'\b(comprehensive|deep|detailed|thorough)\b',
                r'\b(landscape|overview|survey|review)\b'
            ],
            QueryType.OPINION: [
                r'\b(best|top|recommend|should|opinion)\b',
                r'\b(favorite|prefer|choice|rating)\b',
                r'\b(review|testimonial|feedback)\b'
            ],
            QueryType.CURRENT_EVENTS: [
                r'\b(latest|recent|new|current|today|yesterday)\b',
                r'\b(update|news|happening|trend)\b',
                r'\b(2024|2025|this (week|month|year))\b'
            ]
        }

        # Complexity indicators
        self.complexity_indicators = {
            'simple': [r'^what is\b', r'^who is\b', r'^define\b'],
            'medium': [r'\bcompare\b', r'\bhow (does|do)\b', r'\bexplain\b'],
            'high': [r'\banalyz[ei]\b', r'\bresearch\b', r'\bcomprehensive\b'],
            'expert': [r'\bmulti.?faceted\b', r'\blandscape\b', r'\becosystem\b', r'\btradeoffs?\b']
        }

    def analyze(self, query: str) -> QueryProfile:
        """
        Analyze query and create comprehensive profile

        Args:
            query: Search query string

        Returns:
            QueryProfile with recommendations
        """
        query_lower = query.lower()

        # Determine domain
        domain = self._classify_domain(query_lower)

        # Determine query type
        query_type = self._classify_type(query_lower)

        # Determine complexity
        complexity = self._assess_complexity(query_lower)

        # Check special characteristics
        requires_fact_checking = self._needs_fact_checking(query_lower, query_type)
        is_multi_faceted = self._is_multi_faceted(query_lower)
        needs_recent_data = self._needs_recent_data(query_lower)

        # Recommend RAG mode
        recommended_rag = self._recommend_rag_mode(
            complexity, query_type, requires_fact_checking, is_multi_faceted
        )

        # Recommend search strategies
        search_strategies = self._recommend_strategies(
            domain, query_type, needs_recent_data
        )

        # Estimate depth
        estimated_depth = self._estimate_depth(complexity, is_multi_faceted)

        # Calculate confidence
        confidence_score = self._calculate_confidence(query_lower)

        profile = QueryProfile(
            query=query,
            complexity=complexity,
            domain=domain,
            query_type=query_type,
            estimated_depth=estimated_depth,
            recommended_rag=recommended_rag,
            search_strategies=search_strategies,
            requires_fact_checking=requires_fact_checking,
            is_multi_faceted=is_multi_faceted,
            needs_recent_data=needs_recent_data,
            confidence_score=confidence_score
        )

        logger.info(
            f"Query analyzed: complexity={complexity}, domain={domain}, "
            f"type={query_type}, rag={recommended_rag}, strategies={len(search_strategies)}"
        )

        return profile

    def _classify_domain(self, query: str) -> QueryDomain:
        """Classify query domain using pattern matching"""
        scores = {}

        for domain, patterns in self.domain_patterns.items():
            score = sum(
                1 for pattern in patterns
                if re.search(pattern, query, re.IGNORECASE)
            )
            scores[domain] = score

        # Return domain with highest score, or GENERAL if none match
        if not scores or max(scores.values()) == 0:
            return QueryDomain.GENERAL

        return max(scores.items(), key=lambda x: x[1])[0]

    def _classify_type(self, query: str) -> QueryType:
        """Classify query type using pattern matching"""
        for query_type, patterns in self.type_patterns.items():
            if any(re.search(pattern, query, re.IGNORECASE) for pattern in patterns):
                return query_type

        return QueryType.FACTUAL  # Default

    def _assess_complexity(self, query: str) -> QueryComplexity:
        """Assess query complexity using multiple heuristics"""

        # Check complexity indicators
        for level in ['expert', 'high', 'medium', 'simple']:
            if any(re.search(pattern, query, re.IGNORECASE)
                   for pattern in self.complexity_indicators[level]):
                return QueryComplexity(level)

        # Heuristic: word count
        word_count = len(query.split())
        if word_count > 15:
            return QueryComplexity.HIGH
        elif word_count > 10:
            return QueryComplexity.MEDIUM
        elif word_count > 5:
            return QueryComplexity.MEDIUM
        else:
            return QueryComplexity.SIMPLE

    def _needs_fact_checking(self, query: str, query_type: QueryType) -> bool:
        """Determine if query needs fact-checking"""
        fact_check_patterns = [
            r'\b(true|false|fact|myth|verify|check|accurate)\b',
            r'\b(claim|statement|alleged|reportedly)\b'
        ]

        return (
            query_type == QueryType.RESEARCH or
            any(re.search(pattern, query, re.IGNORECASE)
                for pattern in fact_check_patterns)
        )

    def _is_multi_faceted(self, query: str) -> bool:
        """Determine if query is multi-faceted"""
        multi_faceted_patterns = [
            r'\b(and|or|versus|compared?|multiple|various|different)\b',
            r'\b(aspects?|factors?|dimensions?|perspectives?)\b',
            r'\b(pros? and cons?|advantages? and disadvantages?)\b'
        ]

        return any(re.search(pattern, query, re.IGNORECASE)
                   for pattern in multi_faceted_patterns)

    def _needs_recent_data(self, query: str) -> bool:
        """Determine if query needs recent data"""
        recency_patterns = [
            r'\b(latest|recent|new|current|today|yesterday)\b',
            r'\b(2024|2025|this (week|month|year))\b',
            r'\b(update|news|trend|happening)\b'
        ]

        return any(re.search(pattern, query, re.IGNORECASE)
                   for pattern in recency_patterns)

    def _recommend_rag_mode(
        self,
        complexity: QueryComplexity,
        query_type: QueryType,
        requires_fact_checking: bool,
        is_multi_faceted: bool
    ) -> RAGMode:
        """Recommend optimal RAG mode based on query characteristics"""

        # Fact-checking queries use CRAG
        if requires_fact_checking:
            return RAGMode.CRAG

        # Multi-faceted queries use Plan-RAG
        if is_multi_faceted:
            return RAGMode.PLAN_RAG

        # Research queries with high complexity use Plan-RAG
        if query_type == QueryType.RESEARCH and complexity in [QueryComplexity.HIGH, QueryComplexity.EXPERT]:
            return RAGMode.PLAN_RAG

        # Medium-high complexity uses Self-RAG
        if complexity in [QueryComplexity.MEDIUM, QueryComplexity.HIGH]:
            return RAGMode.SELF_RAG

        # Simple queries use simple RAG
        return RAGMode.SIMPLE

    def _recommend_strategies(
        self,
        domain: QueryDomain,
        query_type: QueryType,
        needs_recent_data: bool
    ) -> List[SearchStrategy]:
        """Recommend search strategies based on query characteristics"""
        strategies = []

        # Always include fresh web for recent data
        if needs_recent_data:
            strategies.append(SearchStrategy.FRESH_WEB)
            strategies.append(SearchStrategy.NEWS)

        # Domain-specific strategies
        if domain == QueryDomain.TECHNICAL:
            strategies.extend([
                SearchStrategy.TECHNICAL_DOCS,
                SearchStrategy.DISCUSSIONS,
                SearchStrategy.FRESH_WEB
            ])
        elif domain == QueryDomain.ACADEMIC:
            strategies.extend([
                SearchStrategy.ACADEMIC,
                SearchStrategy.FRESH_WEB
            ])
        elif domain == QueryDomain.NEWS:
            strategies.extend([
                SearchStrategy.NEWS,
                SearchStrategy.FRESH_WEB
            ])
        else:
            # General queries
            strategies.extend([
                SearchStrategy.FRESH_WEB,
                SearchStrategy.DISCUSSIONS
            ])

        # Query type specific
        if query_type == QueryType.PROCEDURAL:
            if SearchStrategy.VIDEOS not in strategies:
                strategies.append(SearchStrategy.VIDEOS)

        # Remove duplicates while preserving order
        seen = set()
        strategies = [s for s in strategies if not (s in seen or seen.add(s))]

        # Limit to 3 strategies for performance
        return strategies[:3]

    def _estimate_depth(self, complexity: QueryComplexity, is_multi_faceted: bool) -> int:
        """Estimate recommended search depth"""
        base_depth = {
            QueryComplexity.SIMPLE: 1,
            QueryComplexity.MEDIUM: 2,
            QueryComplexity.HIGH: 2,
            QueryComplexity.EXPERT: 3
        }

        depth = base_depth.get(complexity, 2)

        # Multi-faceted queries benefit from extra depth
        if is_multi_faceted and depth < 3:
            depth += 1

        return min(depth, 3)  # Cap at 3

    def _calculate_confidence(self, query: str) -> float:
        """Calculate confidence score for analysis"""
        score = 0.5  # Base confidence

        # Increase confidence for clear patterns
        word_count = len(query.split())
        if 5 <= word_count <= 20:
            score += 0.2

        # Increase confidence if multiple patterns match
        pattern_count = sum(
            1 for patterns in self.domain_patterns.values()
            if any(re.search(p, query, re.IGNORECASE) for p in patterns)
        )
        score += min(pattern_count * 0.1, 0.3)

        return min(score, 1.0)
