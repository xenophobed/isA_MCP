#!/usr/bin/env python
"""
Search Engine for Web Services
Unified interface for multiple search providers (Brave, Google, etc.)
Based on strategy pattern for extensibility
"""
import asyncio
import json
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
from enum import Enum
import httpx

from core.logging import get_logger

logger = get_logger(__name__)

class SearchProvider(Enum):
    """Supported search providers"""
    BRAVE = "brave"
    GOOGLE = "google"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"

class SearchResult:
    """Standardized search result"""
    def __init__(self, title: str, url: str, snippet: str, **kwargs):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.score = kwargs.get('score', 0.0)
        self.provider = kwargs.get('provider', 'unknown')
        self.metadata = kwargs.get('metadata', {})
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'url': self.url,
            'snippet': self.snippet,
            'score': self.score,
            'provider': self.provider,
            'metadata': self.metadata
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
    """Brave Search API implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.client = httpx.AsyncClient()
    
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search using Brave API"""
        logger.info(f"🔍 Brave search: {query}")
        
        params = {
            'q': query,
            'count': min(kwargs.get('count', 10), 20),  # Brave API max count is 20
            'offset': kwargs.get('offset', 0),
            'mkt': kwargs.get('market', 'en-US'),
            'safesearch': kwargs.get('safesearch', 'moderate'),
            'freshness': kwargs.get('freshness', None),
            'text_decorations': str(kwargs.get('text_decorations', True)).lower(),
            'spellcheck': str(kwargs.get('spellcheck', True)).lower()
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Subscription-Token': self.api_key
        }
        
        try:
            response = await self.client.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Parse web results
            web_results = data.get('web', {}).get('results', [])
            for i, result in enumerate(web_results):
                search_result = SearchResult(
                    title=result.get('title', ''),
                    url=result.get('url', ''),
                    snippet=result.get('description', ''),
                    score=1.0 - (i * 0.1),  # Simple ranking score
                    provider='brave',
                    metadata={
                        'age': result.get('age', ''),
                        'language': result.get('language', ''),
                        'family_friendly': result.get('family_friendly', True),
                        'type': result.get('type', 'web'),
                        'subtype': result.get('subtype', ''),
                        'deep_results': result.get('deep_results', [])
                    }
                )
                results.append(search_result)
            
            logger.info(f"✅ Brave search completed: {len(results)} results")
            return results
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Brave API error {e.response.status_code}: {e.response.text}")
            logger.error(f"❌ Request URL: {e.request.url}")
            logger.error(f"❌ Request params: {params}")
            logger.error(f"❌ Request headers: {headers}")
            raise Exception(f"Brave search failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"❌ Brave search error: {e}")
            raise Exception(f"Brave search failed: {str(e)}")
    
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