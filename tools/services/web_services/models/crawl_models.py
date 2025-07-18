#!/usr/bin/env python
"""
Crawl Models
Data structures for web crawling operations
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
import json


class CrawlMode(Enum):
    """Web crawling modes"""
    BROWSER_FULL = "browser_full"        # Full browser with all features
    BROWSER_LIGHT = "browser_light"      # Lightweight browser mode
    HTTP_ONLY = "http_only"             # Fast HTTP-only mode


class CrawlStrategy(Enum):
    """Multi-URL crawling strategies"""
    SEQUENTIAL = "sequential"            # Process URLs one by one
    CONCURRENT = "concurrent"           # Process URLs concurrently
    BATCH = "batch"                     # Process URLs in batches
    ADAPTIVE = "adaptive"               # Adaptive strategy based on performance


@dataclass
class ResourcePoolConfig:
    """Configuration for resource pool management"""
    pool_size: int = 10
    max_sessions: int = 20
    session_timeout: int = 300000  # 5 minutes in ms
    cleanup_interval: int = 60     # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionSchema:
    """Schema for content extraction configuration"""
    name: str
    schema_type: str  # 'predefined' or 'custom'
    schema_data: Dict[str, Any]
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_predefined(cls, schema_name: str) -> 'ExtractionSchema':
        """Create schema from predefined schemas"""
        predefined_schemas = {
            'article': {
                'name': 'article',
                'description': 'Extract article content',
                'fields': ['title', 'content', 'author', 'date', 'tags']
            },
            'product': {
                'name': 'product',
                'description': 'Extract product information',
                'fields': ['name', 'price', 'description', 'images', 'rating']
            },
            'contact': {
                'name': 'contact',
                'description': 'Extract contact information',
                'fields': ['name', 'email', 'phone', 'address', 'role']
            },
            'event': {
                'name': 'event',
                'description': 'Extract event information',
                'fields': ['title', 'date', 'location', 'description', 'organizer']
            },
            'research': {
                'name': 'research',
                'description': 'Extract research content',
                'fields': ['title', 'abstract', 'authors', 'keywords', 'content']
            }
        }
        
        if schema_name not in predefined_schemas:
            raise ValueError(f"Unknown predefined schema: {schema_name}")
        
        return cls(
            name=schema_name,
            schema_type='predefined',
            schema_data=predefined_schemas[schema_name]
        )
    
    @classmethod
    def from_custom(cls, name: str, schema_data: Dict[str, Any]) -> 'ExtractionSchema':
        """Create schema from custom data"""
        return cls(
            name=name,
            schema_type='custom',
            schema_data=schema_data
        )


@dataclass
class FilterConfig:
    """Configuration for content filtering"""
    filter_type: str
    enabled: bool = True
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CrawlConfig:
    """Configuration for crawl operations"""
    mode: CrawlMode = CrawlMode.BROWSER_FULL
    strategy: CrawlStrategy = CrawlStrategy.CONCURRENT
    max_concurrent: int = 5
    batch_size: int = 3
    timeout: int = 30000
    retry_attempts: int = 3
    retry_delay: float = 1.0
    use_stealth: bool = True
    use_human_behavior: bool = True
    use_rate_limiting: bool = True
    session_reuse: bool = True
    
    # Enhanced anti-detection settings
    stealth_level: str = "high"  # low, medium, high, extreme
    use_rotating_user_agents: bool = True
    random_delay_range: tuple = (1.0, 3.0)  # Random delay between actions
    viewport_randomization: bool = True
    timezone_spoofing: bool = True
    language_spoofing: bool = True
    
    # Resource management
    resource_pool: ResourcePoolConfig = None
    
    # Extraction configuration
    extraction_schema: ExtractionSchema = None
    
    # Filtering configuration
    filters: List[FilterConfig] = None
    
    def __post_init__(self):
        if self.resource_pool is None:
            self.resource_pool = ResourcePoolConfig()
        if self.extraction_schema is None:
            self.extraction_schema = ExtractionSchema.from_predefined('article')
        if self.filters is None:
            self.filters = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'mode': self.mode.value,
            'strategy': self.strategy.value,
            'max_concurrent': self.max_concurrent,
            'batch_size': self.batch_size,
            'timeout': self.timeout,
            'retry_attempts': self.retry_attempts,
            'retry_delay': self.retry_delay,
            'use_stealth': self.use_stealth,
            'use_human_behavior': self.use_human_behavior,
            'use_rate_limiting': self.use_rate_limiting,
            'session_reuse': self.session_reuse,
            'resource_pool': self.resource_pool.to_dict(),
            'extraction_schema': self.extraction_schema.to_dict(),
            'filters': [f.to_dict() for f in self.filters]
        }
    
    def add_filter(self, filter_type: str, config: Dict[str, Any] = None):
        """Add a filter to the configuration"""
        self.filters.append(FilterConfig(
            filter_type=filter_type,
            config=config or {}
        ))
    
    def enable_semantic_filter(self, query: str, threshold: float = 0.6):
        """Enable semantic filtering"""
        self.add_filter('semantic', {
            'user_query': query,
            'similarity_threshold': threshold
        })
    
    def enable_bm25_filter(self, query: str, threshold: float = 1.0):
        """Enable BM25 filtering"""
        self.add_filter('bm25', {
            'user_query': query,
            'bm25_threshold': threshold
        })
    
    def enable_pruning_filter(self, threshold: float = 0.5):
        """Enable pruning filtering"""
        self.add_filter('pruning', {
            'threshold': threshold
        })
    
    def enable_ai_quality_filter(self, min_quality: str = 'medium'):
        """Enable AI quality filtering"""
        self.add_filter('ai_quality', {
            'min_quality': min_quality
        })


@dataclass
class CrawlResult:
    """Result from crawling a single URL"""
    url: str
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    response_time: Optional[float] = None
    retry_count: int = 0
    extraction_schema: Optional[str] = None
    filters_applied: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.filters_applied is None:
            self.filters_applied = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to the result"""
        self.metadata[key] = value
    
    def get_item_count(self) -> int:
        """Get number of extracted items"""
        return len(self.data) if self.data else 0


@dataclass
class CrawlJobResult:
    """Result from crawling multiple URLs"""
    job_id: str
    urls: List[str]
    config: CrawlConfig
    results: List[CrawlResult]
    stats: Dict[str, Any]
    synthesis: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'job_id': self.job_id,
            'urls': self.urls,
            'config': self.config.to_dict(),
            'results': [result.to_dict() for result in self.results],
            'stats': self.stats,
            'synthesis': self.synthesis,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }
    
    def get_successful_results(self) -> List[CrawlResult]:
        """Get only successful crawl results"""
        return [r for r in self.results if r.success]
    
    def get_failed_results(self) -> List[CrawlResult]:
        """Get only failed crawl results"""
        return [r for r in self.results if not r.success]
    
    def get_total_items(self) -> int:
        """Get total number of extracted items"""
        return sum(r.get_item_count() for r in self.results)
    
    def get_success_rate(self) -> float:
        """Get success rate as percentage"""
        if not self.results:
            return 0.0
        return (len(self.get_successful_results()) / len(self.results)) * 100
    
    def get_duration(self) -> float:
        """Get job duration in seconds"""
        if not self.start_time or not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)