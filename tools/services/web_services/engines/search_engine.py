#!/usr/bin/env python
"""
Search Engine for Web Services
Unified interface for multiple search providers (Brave, Google, etc.)
Based on strategy pattern for extensibility
"""
import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timedelta
import httpx

from core.logging import get_logger

logger = get_logger(__name__)

class SearchProvider(Enum):
    """Supported search providers"""
    BRAVE = "brave"
    GOOGLE = "google"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"

class SearchFreshness(Enum):
    """Time-based freshness filters for Brave"""
    DAY = "pd"       # Last 24 hours
    WEEK = "pw"      # Last 7 days  
    MONTH = "pm"     # Last 31 days
    YEAR = "py"      # Last 365 days
    CUSTOM = "custom"  # Custom date range

class ResultFilter(Enum):
    """Available result type filters for Brave"""
    DISCUSSIONS = "discussions"
    FAQ = "faq"
    NEWS = "news"
    VIDEOS = "videos"
    INFOBOX = "infobox"
    LOCATIONS = "locations"

class SafeSearchLevel(Enum):
    """Safe search filtering levels"""
    OFF = "off"
    MODERATE = "moderate"
    STRICT = "strict"

class SearchResult:
    """Enhanced search result with additional metadata"""
    def __init__(self, title: str = '', url: str = '', snippet: str = '', **kwargs):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.extra_snippets = kwargs.get('extra_snippets', [])
        self.score = kwargs.get('score', 0.0)
        self.provider = kwargs.get('provider', 'unknown')
        self.metadata = kwargs.get('metadata', {})
        self.age = kwargs.get('age', '')
        self.language = kwargs.get('language', '')
        self.type = kwargs.get('type', 'web')
        self.thumbnail = kwargs.get('thumbnail', {})
        self.deep_results = kwargs.get('deep_results', [])
    
    def get_all_content(self) -> str:
        """Get all available content from the result"""
        content_parts = [self.title, self.snippet]
        content_parts.extend(self.extra_snippets)
        meta_desc = self.metadata.get('meta_description', '')
        if meta_desc and meta_desc != self.snippet:
            content_parts.append(meta_desc)
        return ' '.join(filter(bool, content_parts))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'url': self.url,
            'snippet': self.snippet,
            'extra_snippets': self.extra_snippets,
            'all_content': self.get_all_content(),
            'score': self.score,
            'provider': self.provider,
            'metadata': self.metadata,
            'age': self.age,
            'language': self.language,
            'type': self.type
        }

class SearchStrategy(ABC):
    """Abstract base class for search strategies"""
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Execute search and return standardized results"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name"""
        pass

class BraveSearchStrategy(SearchStrategy):
    """Enhanced Brave Search API implementation with advanced features"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.client = httpx.AsyncClient(timeout=60)  # Increased timeout
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
        
        # Default goggles for different use cases
        self.goggles = {
            'academic': """
                ! name: Academic Sources
                ! description: Prioritize academic and educational content
                ! public: true
                
                $boost=3,site=.edu
                $boost=3,site=scholar.google.com
                $boost=3,site=arxiv.org
                $boost=2,site=.org
                $boost=2,site=pubmed.ncbi.nlm.nih.gov
                $boost=2,site=sciencedirect.com
                $downrank=3,site=pinterest.com
                $downrank=3,site=facebook.com
                $downrank=2,site=twitter.com
            """,
            'technical': """
                ! name: Technical Documentation
                ! description: Focus on technical docs and code
                ! public: true
                
                $boost=3,site=github.com
                $boost=3,site=stackoverflow.com
                $boost=2,site=docs.
                $boost=2,site=dev.to
                $boost=2,site=medium.com
                $downrank=2,site=w3schools.com
            """,
            'news': """
                ! name: News Sources
                ! description: Prioritize news websites
                ! public: true
                
                $boost=3,site=reuters.com
                $boost=3,site=apnews.com
                $boost=2,site=bbc.com
                $boost=2,site=cnn.com
                $boost=2,site=nytimes.com
            """
        }
    
    async def search(
        self,
        query: str,
        count: int = 20,  # Use max by default
        offset: int = 0,
        freshness: Optional[Union[SearchFreshness, str]] = None,
        result_filter: Optional[ResultFilter] = None,
        extra_snippets: bool = True,  # Request cluster data from Brave API
        summary: bool = False,
        goggles: Optional[str] = None,
        goggle_type: Optional[str] = None,
        safe_search: Union[SafeSearchLevel, str] = SafeSearchLevel.MODERATE,
        market: str = 'en-US',
        **kwargs
    ) -> List[SearchResult]:
        """
        Enhanced search with all available parameters

        Args:
            query: Search query
            count: Number of results (max 20)
            offset: Pagination offset
            freshness: Time-based filter
            result_filter: Filter by result type
            extra_snippets: Request extra content (Brave returns 'cluster' field with related pages)
            summary: Generate AI summary
            goggles: Custom goggle definition or URL
            goggle_type: Predefined goggle type (academic, technical, news)
            safe_search: Content filtering level
            market: Market/language preference
        """
        
        # Rate limiting
        await self._enforce_rate_limit()
        
        # Build parameters
        params = {
            'q': query,
            'count': min(count, 20),
            'offset': offset,
            'mkt': market,
            'safesearch': safe_search.value if isinstance(safe_search, SafeSearchLevel) else safe_search,
            'extra_snippets': extra_snippets,
            'text_decorations': True,
            'spellcheck': True
        }
        
        # Add freshness filter
        if freshness:
            if isinstance(freshness, SearchFreshness):
                if freshness == SearchFreshness.CUSTOM:
                    # For custom, expect date range in kwargs
                    date_from = kwargs.get('date_from')
                    date_to = kwargs.get('date_to')
                    if date_from and date_to:
                        params['freshness'] = f"{date_from}to{date_to}"
                else:
                    params['freshness'] = freshness.value
            else:
                params['freshness'] = freshness
        
        # Add result filter
        if result_filter:
            params['result_filter'] = result_filter.value if isinstance(result_filter, ResultFilter) else result_filter
        
        # Add summary generation
        if summary:
            params['summary'] = True
        
        # Add goggles for custom ranking
        if goggle_type and goggle_type in self.goggles:
            params['goggles'] = self.goggles[goggle_type]
        elif goggles:
            if goggles.startswith('http'):
                params['goggles_id'] = goggles
            else:
                params['goggles'] = goggles
        
        # Make request
        try:
            logger.info(f"🔍 Enhanced Brave search: {query} (freshness={freshness}, filter={result_filter})")
            
            headers = {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip',
                'X-Subscription-Token': self.api_key
            }
            
            response = await self.client.get(
                self.base_url,
                params=params,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse all result types
            results = await self._parse_comprehensive_results(data, query)
            
            logger.info(f"✅ Enhanced search completed: {len(results)} results")
            return results
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limited, waiting before retry...")
                await asyncio.sleep(5)
                return await self.search(query, count=count, offset=offset, freshness=freshness,
                                       result_filter=result_filter, extra_snippets=extra_snippets,
                                       summary=summary, goggles=goggles, goggle_type=goggle_type,
                                       safe_search=safe_search, market=market, **kwargs)
            logger.error(f"❌ Brave API error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            raise
    
    async def _parse_comprehensive_results(
        self,
        data: Dict[str, Any],
        query: str
    ) -> List[SearchResult]:
        """Parse all types of results from API response"""

        results = []

        # Parse web results (primary)
        web_results = data.get('web', {}).get('results', [])
        for i, result in enumerate(web_results):
            # Extract extra content from cluster field (Brave API's way of providing extra snippets)
            extra_snippets = []
            if 'cluster' in result and result['cluster']:
                # Extract descriptions from cluster items (related pages from same domain)
                extra_snippets = [
                    item.get('description', '')
                    for item in result['cluster'][:5]  # Max 5 extra snippets
                    if item.get('description')
                ]

            # Get meta_description from meta_url or profile if available
            meta_description = ''
            if 'meta_url' in result and isinstance(result['meta_url'], dict):
                meta_description = result['meta_url'].get('description', '')

            search_result = SearchResult(
                title=result.get('title', ''),
                url=result.get('url', ''),
                snippet=result.get('description', ''),
                extra_snippets=extra_snippets,
                score=1.0 - (i * 0.05),  # Ranking score
                provider='brave',
                age=result.get('age', ''),
                language=result.get('language', ''),
                type='web',
                deep_results=result.get('deep_results', []),
                metadata={
                    'family_friendly': result.get('family_friendly', True),
                    'subtype': result.get('subtype', ''),
                    'meta_description': meta_description,
                    'cluster_type': result.get('cluster_type', '')
                }
            )
            results.append(search_result)
        
        # Add news results if available
        news_results = data.get('news', {}).get('results', [])
        for result in news_results[:5]:  # Top 5 news
            search_result = SearchResult(
                title=result.get('title', ''),
                url=result.get('url', ''),
                snippet=result.get('description', ''),
                age=result.get('age', ''),
                type='news',
                score=0.8,
                provider='brave'
            )
            results.append(search_result)
        
        # Add video results if available  
        video_results = data.get('videos', {}).get('results', [])
        for result in video_results[:3]:  # Top 3 videos
            search_result = SearchResult(
                title=result.get('title', ''),
                url=result.get('url', ''),
                snippet=result.get('description', ''),
                thumbnail=result.get('thumbnail', {}),
                type='video',
                score=0.7,
                provider='brave'
            )
            results.append(search_result)
        
        # Add infobox if present
        if 'infobox' in data:
            infobox = data['infobox']
            results.insert(0, SearchResult(
                title=infobox.get('title', query),
                url=infobox.get('url', ''),
                snippet=infobox.get('description', ''),
                type='infobox',
                score=1.5,  # Highest priority
                provider='brave'
            ))
        
        # Add summary if generated
        if 'summarizer' in data and data['summarizer'].get('summary'):
            summary = data['summarizer']['summary']
            results.insert(0, SearchResult(
                title=f"AI Summary for: {query}",
                url='',
                snippet=summary,
                type='summary',
                score=1.5,
                provider='brave'
            ))
        
        return results
    
    async def deep_search(
        self,
        query: str,
        depth: int = 2,
        max_results_per_level: int = 10
    ) -> List[SearchResult]:
        """
        Perform deep search with multiple queries and refinements
        
        Args:
            query: Initial search query
            depth: Number of search levels
            max_results_per_level: Results per search level
        """
        
        all_results = []
        seen_urls = set()
        
        # Level 1: Initial search with multiple strategies
        strategies = [
            {'extra_snippets': True},
            {'freshness': SearchFreshness.WEEK, 'extra_snippets': True},
            {'goggle_type': 'technical', 'extra_snippets': True},
            {'result_filter': ResultFilter.DISCUSSIONS}
        ]
        
        for strategy in strategies:
            try:
                results = await self.search(
                    query,
                    count=max_results_per_level,
                    **strategy
                )
                
                for result in results:
                    if result.url not in seen_urls:
                        seen_urls.add(result.url)
                        all_results.append(result)
                
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Strategy failed: {strategy}, error: {e}")
                continue
        
        # Level 2: Query expansion (if depth > 1)
        if depth > 1:
            # Simple query variations
            expanded_queries = [
                f"{query} tutorial",
                f"{query} explained",
                f"{query} best practices",
                f"how does {query} work"
            ]
            
            for expanded_query in expanded_queries[:depth-1]:
                try:
                    results = await self.search(
                        expanded_query,
                        count=5,
                        extra_snippets=True
                    )
                    
                    for result in results:
                        if result.url not in seen_urls:
                            seen_urls.add(result.url)
                            all_results.append(result)
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"Expanded query failed: {expanded_query}, error: {e}")
                    continue
        
        # Sort by score
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"✅ Deep search completed: {len(all_results)} unique results")
        return all_results
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def get_provider_name(self) -> str:
        return "brave"
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

class GoogleSearchStrategy(SearchStrategy):
    """Google Custom Search API implementation (placeholder)"""
    
    def __init__(self, api_key: str, search_engine_id: str):
        self.api_key = api_key
        self.search_engine_id = search_engine_id
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search using Google Custom Search API"""
        logger.warning("Google search not implemented yet")
        return []
    
    def get_provider_name(self) -> str:
        return "google"

class DuckDuckGoSearchStrategy(SearchStrategy):
    """DuckDuckGo search implementation (no API key required)"""
    
    def __init__(self):
        self.client = httpx.AsyncClient()
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search using DuckDuckGo instant answers"""
        logger.warning("DuckDuckGo search not implemented yet")
        return []
    
    def get_provider_name(self) -> str:
        return "duckduckgo"

class SearchEngine:
    """Main search engine with multiple provider support"""
    
    def __init__(self):
        self.strategies: Dict[str, SearchStrategy] = {}
        self.default_provider = None
    
    def register_strategy(self, provider: SearchProvider, strategy: SearchStrategy):
        """Register a search strategy"""
        self.strategies[provider.value] = strategy
        if self.default_provider is None:
            self.default_provider = provider.value
        logger.info(f"✅ Registered {provider.value} search strategy")
    
    async def search(
        self, 
        query: str, 
        provider: Optional[SearchProvider] = None,
        **kwargs
    ) -> List[SearchResult]:
        """Execute search using specified or default provider"""
        
        provider_name = provider.value if provider else self.default_provider
        if not provider_name or provider_name not in self.strategies:
            raise ValueError(f"No search strategy registered for provider: {provider_name}")
        
        strategy = self.strategies[provider_name]
        logger.info(f"🔍 Executing search with {provider_name} provider")
        
        return await strategy.search(query, **kwargs)
    
    async def multi_search(
        self,
        query: str,
        providers: List[SearchProvider],
        **kwargs
    ) -> Dict[str, List[SearchResult]]:
        """Search across multiple providers concurrently"""
        logger.info(f"🔍 Multi-provider search: {[p.value for p in providers]}")
        
        tasks = []
        for provider in providers:
            if provider.value in self.strategies:
                task = self.search(query, provider, **kwargs)
                tasks.append((provider.value, task))
        
        results = {}
        completed_tasks = await asyncio.gather(
            *[task for _, task in tasks], 
            return_exceptions=True
        )
        
        for (provider_name, _), result in zip(tasks, completed_tasks):
            if isinstance(result, Exception):
                logger.error(f"❌ {provider_name} search failed: {result}")
                results[provider_name] = []
            else:
                results[provider_name] = result
                logger.info(f"✅ {provider_name}: {len(result)} results")
        
        return results
    
    async def aggregate_results(
        self,
        multi_results: Dict[str, List[SearchResult]],
        deduplicate: bool = True
    ) -> List[SearchResult]:
        """Aggregate and optionally deduplicate results from multiple providers"""
        all_results = []
        
        for provider, results in multi_results.items():
            all_results.extend(results)
        
        if deduplicate:
            # Simple deduplication by URL
            seen_urls = set()
            deduplicated = []
            for result in all_results:
                if result.url not in seen_urls:
                    seen_urls.add(result.url)
                    deduplicated.append(result)
            all_results = deduplicated
            logger.info(f"🔄 Deduplicated results: {len(all_results)} unique URLs")
        
        # Sort by score (highest first)
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        return all_results
    
    async def close(self):
        """Close all strategy clients"""
        for strategy in self.strategies.values():
            if hasattr(strategy, 'close'):
                await strategy.close()
    
    def get_available_providers(self) -> List[str]:
        """Get list of registered providers"""
        return list(self.strategies.keys())