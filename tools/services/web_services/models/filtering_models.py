#!/usr/bin/env python
"""
Filtering Models
Data structures for content filtering operations
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
import json


class FilterType(Enum):
    """Types of content filters"""
    SEMANTIC = "semantic"
    BM25 = "bm25"
    PRUNING = "pruning"
    AI_RELEVANCE = "ai_relevance"
    AI_QUALITY = "ai_quality"
    AI_TOPIC = "ai_topic"
    AI_SENTIMENT = "ai_sentiment"
    AI_LANGUAGE = "ai_language"
    AI_COMPOSITE = "ai_composite"
    CUSTOM = "custom"


@dataclass
class FilterMetadata:
    """Metadata for filtering operation"""
    timestamp: datetime
    filter_type: FilterType
    filter_name: str
    processing_time: Optional[float] = None
    tokens_used: Optional[int] = None
    confidence_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'filter_type': self.filter_type.value,
            'filter_name': self.filter_name,
            'processing_time': self.processing_time,
            'tokens_used': self.tokens_used,
            'confidence_score': self.confidence_score
        }


@dataclass
class FilterCriteria:
    """Criteria for content filtering"""
    filter_type: FilterType
    config: Dict[str, Any]
    enabled: bool = True
    priority: int = 0  # Higher priority filters run first
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'filter_type': self.filter_type.value,
            'config': self.config,
            'enabled': self.enabled,
            'priority': self.priority
        }
    
    @classmethod
    def semantic_filter(cls, user_query: str, similarity_threshold: float = 0.6) -> 'FilterCriteria':
        """Create semantic filter criteria"""
        return cls(
            filter_type=FilterType.SEMANTIC,
            config={
                'user_query': user_query,
                'similarity_threshold': similarity_threshold,
                'min_chunk_length': 100,
                'max_chunks': 20
            }
        )
    
    @classmethod
    def bm25_filter(cls, user_query: str, bm25_threshold: float = 1.0) -> 'FilterCriteria':
        """Create BM25 filter criteria"""
        return cls(
            filter_type=FilterType.BM25,
            config={
                'user_query': user_query,
                'bm25_threshold': bm25_threshold,
                'k1': 1.5,
                'b': 0.75,
                'min_words': 5
            }
        )
    
    @classmethod
    def pruning_filter(cls, threshold: float = 0.5, threshold_type: str = "fixed") -> 'FilterCriteria':
        """Create pruning filter criteria"""
        return cls(
            filter_type=FilterType.PRUNING,
            config={
                'threshold': threshold,
                'threshold_type': threshold_type,
                'min_word_threshold': 10
            }
        )
    
    @classmethod
    def ai_relevance_filter(cls, user_query: str, relevance_threshold: float = 0.6) -> 'FilterCriteria':
        """Create AI relevance filter criteria"""
        return cls(
            filter_type=FilterType.AI_RELEVANCE,
            config={
                'user_query': user_query,
                'relevance_threshold': relevance_threshold,
                'llm_config': {'temperature': 0.1, 'max_tokens': 200}
            }
        )
    
    @classmethod
    def ai_quality_filter(cls, min_quality: str = 'medium') -> 'FilterCriteria':
        """Create AI quality filter criteria"""
        return cls(
            filter_type=FilterType.AI_QUALITY,
            config={
                'min_quality': min_quality,
                'llm_config': {'temperature': 0.1, 'max_tokens': 150}
            }
        )
    
    @classmethod
    def ai_topic_filter(cls, target_categories: List[str] = None) -> 'FilterCriteria':
        """Create AI topic classification filter criteria"""
        return cls(
            filter_type=FilterType.AI_TOPIC,
            config={
                'target_categories': target_categories or ['news', 'technical', 'educational'],
                'llm_config': {'temperature': 0.1, 'max_tokens': 100}
            }
        )
    
    @classmethod
    def ai_sentiment_filter(cls, target_sentiments: List[str] = None) -> 'FilterCriteria':
        """Create AI sentiment filter criteria"""
        return cls(
            filter_type=FilterType.AI_SENTIMENT,
            config={
                'target_sentiments': target_sentiments or ['positive', 'neutral'],
                'llm_config': {'temperature': 0.1, 'max_tokens': 50}
            }
        )
    
    @classmethod
    def ai_language_filter(cls, target_languages: List[str] = None) -> 'FilterCriteria':
        """Create AI language filter criteria"""
        return cls(
            filter_type=FilterType.AI_LANGUAGE,
            config={
                'target_languages': target_languages or ['english', 'chinese'],
                'llm_config': {'temperature': 0.1, 'max_tokens': 30}
            }
        )


@dataclass
class FilterResult:
    """Result from content filtering operation"""
    original_content: str
    filtered_content: str
    filters_applied: List[FilterMetadata]
    reduction_percentage: float
    success: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_content': self.original_content,
            'filtered_content': self.filtered_content,
            'filters_applied': [f.to_dict() for f in self.filters_applied],
            'reduction_percentage': self.reduction_percentage,
            'success': self.success,
            'error': self.error
        }
    
    def get_filter_count(self) -> int:
        """Get number of filters applied"""
        return len(self.filters_applied)
    
    def get_processing_time(self) -> float:
        """Get total processing time for all filters"""
        return sum(f.processing_time for f in self.filters_applied if f.processing_time)
    
    def get_total_tokens(self) -> int:
        """Get total tokens used by all filters"""
        return sum(f.tokens_used for f in self.filters_applied if f.tokens_used)
    
    def has_filter_type(self, filter_type: FilterType) -> bool:
        """Check if a specific filter type was applied"""
        return any(f.filter_type == filter_type for f in self.filters_applied)
    
    def get_filter_by_type(self, filter_type: FilterType) -> Optional[FilterMetadata]:
        """Get filter metadata by type"""
        for f in self.filters_applied:
            if f.filter_type == filter_type:
                return f
        return None
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


@dataclass
class FilterPipeline:
    """Pipeline for multiple content filters"""
    filters: List[FilterCriteria]
    name: str = "default"
    description: Optional[str] = None
    
    def __post_init__(self):
        # Sort filters by priority (higher priority first)
        self.filters.sort(key=lambda x: x.priority, reverse=True)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'filters': [f.to_dict() for f in self.filters]
        }
    
    def add_filter(self, filter_criteria: FilterCriteria):
        """Add a filter to the pipeline"""
        self.filters.append(filter_criteria)
        # Re-sort by priority
        self.filters.sort(key=lambda x: x.priority, reverse=True)
    
    def remove_filter(self, filter_type: FilterType):
        """Remove a filter from the pipeline"""
        self.filters = [f for f in self.filters if f.filter_type != filter_type]
    
    def get_enabled_filters(self) -> List[FilterCriteria]:
        """Get only enabled filters"""
        return [f for f in self.filters if f.enabled]
    
    def enable_filter(self, filter_type: FilterType):
        """Enable a filter"""
        for f in self.filters:
            if f.filter_type == filter_type:
                f.enabled = True
    
    def disable_filter(self, filter_type: FilterType):
        """Disable a filter"""
        for f in self.filters:
            if f.filter_type == filter_type:
                f.enabled = False
    
    def has_filter_type(self, filter_type: FilterType) -> bool:
        """Check if pipeline has a specific filter type"""
        return any(f.filter_type == filter_type for f in self.filters)
    
    @classmethod
    def create_default_pipeline(cls) -> 'FilterPipeline':
        """Create a default filter pipeline"""
        return cls(
            name="default",
            description="Default content filtering pipeline",
            filters=[
                FilterCriteria.pruning_filter(threshold=0.5),
                FilterCriteria.ai_quality_filter(min_quality='medium')
            ]
        )
    
    @classmethod
    def create_semantic_pipeline(cls, user_query: str) -> 'FilterPipeline':
        """Create a semantic-focused filter pipeline"""
        return cls(
            name="semantic",
            description="Semantic relevance focused pipeline",
            filters=[
                FilterCriteria.semantic_filter(user_query, similarity_threshold=0.6),
                FilterCriteria.ai_relevance_filter(user_query, relevance_threshold=0.7),
                FilterCriteria.pruning_filter(threshold=0.3)
            ]
        )
    
    @classmethod
    def create_quality_pipeline(cls) -> 'FilterPipeline':
        """Create a quality-focused filter pipeline"""
        return cls(
            name="quality",
            description="Content quality focused pipeline",
            filters=[
                FilterCriteria.ai_quality_filter(min_quality='high'),
                FilterCriteria.ai_sentiment_filter(target_sentiments=['positive', 'neutral']),
                FilterCriteria.pruning_filter(threshold=0.6)
            ]
        )
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


# Predefined filter configurations
class PredefinedFilters:
    """Predefined filter configurations for common use cases"""
    
    @staticmethod
    def get_research_filters(query: str) -> List[FilterCriteria]:
        """Filters optimized for research content"""
        return [
            FilterCriteria.semantic_filter(query, similarity_threshold=0.7),
            FilterCriteria.ai_topic_filter(['research', 'technical', 'educational']),
            FilterCriteria.ai_quality_filter('high'),
            FilterCriteria.pruning_filter(threshold=0.6)
        ]
    
    @staticmethod
    def get_news_filters(query: str) -> List[FilterCriteria]:
        """Filters optimized for news content"""
        return [
            FilterCriteria.bm25_filter(query, bm25_threshold=1.2),
            FilterCriteria.ai_topic_filter(['news', 'current_events']),
            FilterCriteria.ai_quality_filter('medium'),
            FilterCriteria.pruning_filter(threshold=0.4)
        ]
    
    @staticmethod
    def get_product_filters(query: str) -> List[FilterCriteria]:
        """Filters optimized for product content"""
        return [
            FilterCriteria.semantic_filter(query, similarity_threshold=0.6),
            FilterCriteria.ai_topic_filter(['commercial', 'product']),
            FilterCriteria.ai_sentiment_filter(['positive', 'neutral']),
            FilterCriteria.pruning_filter(threshold=0.5)
        ]
    
    @staticmethod
    def get_minimal_filters() -> List[FilterCriteria]:
        """Minimal filtering for speed"""
        return [
            FilterCriteria.pruning_filter(threshold=0.3)
        ]
    
    @staticmethod
    def get_comprehensive_filters(query: str) -> List[FilterCriteria]:
        """Comprehensive filtering for quality"""
        return [
            FilterCriteria.semantic_filter(query, similarity_threshold=0.7),
            FilterCriteria.ai_relevance_filter(query, relevance_threshold=0.8),
            FilterCriteria.ai_quality_filter('high'),
            FilterCriteria.ai_sentiment_filter(['positive', 'neutral']),
            FilterCriteria.pruning_filter(threshold=0.6)
        ]