#!/usr/bin/env python3
"""
Unified Search Service - Generic search across tools, prompts, and resources
Uses the existing capabilities system instead of reinventing the wheel
"""

import asyncio
import hashlib
import json
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator
from core.database.supabase_client import get_supabase_client
from core.logging import get_logger
from core.search_monitoring import get_search_monitor
from core.security import SecurityPolicy

logger = get_logger(__name__)

@dataclass
class SearchResult:
    """Unified search result"""
    name: str
    type: str  # 'tool', 'prompt', 'resource'
    description: str
    similarity_score: float
    category: str
    keywords: List[str]
    metadata: Dict[str, Any]

@dataclass
class SearchFilter:
    """Search filters"""
    types: Optional[List[str]] = None  # ['tool', 'prompt', 'resource']
    categories: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    min_similarity: float = 0.25

class UnifiedSearchService:
    """Generic search service using existing MCP capabilities system"""
    
    def __init__(self, mcp_server=None):
        self.mcp_server = mcp_server
        self.embedding_generator = EmbeddingGenerator()
        self.supabase = get_supabase_client()
        
        # Security policy for tool security levels
        self.security_policy = SecurityPolicy()
        
        # Cache for capabilities data
        self.capabilities_cache = {
            'tools': {},
            'prompts': {},
            'resources': {}
        }
        self.embeddings_cache = {}
        self.last_updated = None
        
        # Performance caches
        self.search_results_cache = {}  # Cache search results
        self.query_embeddings_cache = {}  # Cache query embeddings
        self.max_cache_size = 1000
        self.cache_ttl_seconds = 300  # 5 minutes
        
        # Monitoring
        self.monitor = get_search_monitor()
        
    async def initialize(self, mcp_server=None, fallback_mode=True):
        """Initialize the search service with graceful fallback"""
        if mcp_server:
            self.mcp_server = mcp_server
            
        if not self.mcp_server:
            logger.error("MCP server not provided")
            if not fallback_mode:
                raise ValueError("MCP server required for initialization")
            return
            
        try:
            # Load capabilities from MCP server
            await self._refresh_capabilities()
            
            # Compute embeddings for search
            await self._compute_embeddings()
            
            logger.info("Unified search service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize search service: {e}")
            if fallback_mode:
                logger.warning("Continuing in degraded mode without embeddings")
                # Initialize with empty cache for basic functionality
                self.capabilities_cache = {'tools': {}, 'prompts': {}, 'resources': {}}
            else:
                raise
            
    async def _refresh_capabilities(self):
        """Refresh capabilities data from MCP server with error handling"""
        try:
            # Get all capabilities using existing MCP API with timeouts
            tools = await asyncio.wait_for(self.mcp_server.list_tools(), timeout=30.0)
            prompts = await asyncio.wait_for(self.mcp_server.list_prompts(), timeout=30.0)
            resources = await asyncio.wait_for(self.mcp_server.list_resources(), timeout=30.0)
            
            # Process tools
            self.capabilities_cache['tools'] = {}
            for tool in tools:
                # Get security level for the tool
                security_level = self.security_policy.tool_policies.get(tool.name, None)
                security_level_name = security_level.name if security_level else "DEFAULT"
                security_level_value = security_level.value if security_level else 1
                
                tool_info = {
                    'name': tool.name,
                    'description': tool.description or f"Tool: {tool.name}",
                    'type': 'tool',
                    'category': self._categorize_tool(tool.name),
                    'keywords': self._extract_keywords(tool.name, tool.description or ""),
                    'metadata': {
                        'input_schema': getattr(tool, 'inputSchema', None),
                        'security_level': security_level_name,
                        'security_level_value': security_level_value,
                        'requires_authorization': security_level_value > 1 if security_level else False
                    }
                }
                self.capabilities_cache['tools'][tool.name] = tool_info
                
            # Process prompts  
            self.capabilities_cache['prompts'] = {}
            for prompt in prompts:
                # Handle prompt arguments serialization
                arguments = getattr(prompt, 'arguments', None)
                serialized_arguments = None
                if arguments:
                    try:
                        # Convert PromptArgument objects to serializable format
                        serialized_arguments = []
                        for arg in arguments:
                            if hasattr(arg, 'name'):  # It's a PromptArgument object
                                arg_dict = {
                                    'name': arg.name,
                                    'required': getattr(arg, 'required', False),
                                    'description': getattr(arg, 'description', ''),
                                }
                                # Add type if available
                                if hasattr(arg, 'type'):
                                    arg_dict['type'] = str(arg.type) if arg.type else 'string'
                                serialized_arguments.append(arg_dict)
                            else:
                                # Fallback for other formats
                                serialized_arguments.append(str(arg))
                    except Exception as e:
                        logger.warning(f"Failed to serialize arguments for prompt {prompt.name}: {e}")
                        serialized_arguments = []
                
                prompt_info = {
                    'name': prompt.name,
                    'description': prompt.description or f"Prompt: {prompt.name}",
                    'type': 'prompt',
                    'category': self._categorize_prompt(prompt.name),
                    'keywords': self._extract_keywords(prompt.name, prompt.description or ""),
                    'metadata': {
                        'arguments': serialized_arguments
                    }
                }
                self.capabilities_cache['prompts'][prompt.name] = prompt_info
                
            # Process resources
            self.capabilities_cache['resources'] = {}
            for resource in resources:
                resource_uri = str(resource.uri)
                resource_info = {
                    'name': resource_uri,
                    'description': resource.description or f"Resource: {resource_uri}",
                    'type': 'resource',
                    'category': self._categorize_resource(resource_uri),
                    'keywords': self._extract_keywords(resource_uri, resource.description or ""),
                    'metadata': {
                        'uri': resource_uri,
                        'mime_type': getattr(resource, 'mimeType', None)
                    }
                }
                self.capabilities_cache['resources'][resource_uri] = resource_info
                
            logger.info(f"Refreshed capabilities: {len(tools)} tools, {len(prompts)} prompts, {len(resources)} resources")
            
        except asyncio.TimeoutError:
            logger.error("Timeout while refreshing capabilities from MCP server")
            raise
        except Exception as e:
            logger.error(f"Failed to refresh capabilities: {e}")
            raise
            
    def _extract_keywords(self, name: str, description: str) -> List[str]:
        """Extract keywords from name and description"""
        keywords = []
        if name:
            # Split on underscores and camelCase
            import re
            words = re.split(r'[_\s]+|(?=[A-Z])', name.lower())
            keywords.extend([w for w in words if len(w) > 2])
        if description:
            words = description.lower().split()
            keywords.extend([w for w in words if len(w) > 3])
        return list(set(keywords))[:15]
        
    def _categorize_tool(self, name: str) -> str:
        """Categorize tools based on name patterns"""
        name_lower = name.lower()
        if any(word in name_lower for word in ["memory", "recall", "remember", "store"]):
            return "memory"
        elif any(word in name_lower for word in ["image", "generate", "picture", "visual", "vision"]):
            return "vision"
        elif any(word in name_lower for word in ["audio", "speech", "sound", "voice"]):
            return "audio"
        elif any(word in name_lower for word in ["web", "browser", "automation", "crawl", "search"]):
            return "web"
        elif any(word in name_lower for word in ["data", "analytics", "analysis", "graph"]):
            return "analytics"
        elif any(word in name_lower for word in ["shopify", "ecommerce", "product", "order"]):
            return "ecommerce"
        elif any(word in name_lower for word in ["weather", "forecast", "temperature"]):
            return "weather"
        elif any(word in name_lower for word in ["admin", "system", "manage"]):
            return "admin"
        return "general"
        
    def _categorize_prompt(self, name: str) -> str:
        """Categorize prompts based on name patterns"""
        name_lower = name.lower()
        # Omni categories
        if any(word in name_lower for word in ["general", "content", "research_report"]):
            return "custom"
        elif any(word in name_lower for word in ["market", "business", "financial"]):
            return "business_commerce"
        elif any(word in name_lower for word in ["tutorial", "course", "education"]):
            return "education_learning"
        elif any(word in name_lower for word in ["tech", "implementation", "technology"]):
            return "technology_innovation"
        elif any(word in name_lower for word in ["campaign", "content_marketing", "marketing"]):
            return "marketing_media"
        elif any(word in name_lower for word in ["wellness", "health"]):
            return "health_wellness"
        elif any(word in name_lower for word in ["productivity", "lifestyle"]):
            return "lifestyle_personal"
        elif any(word in name_lower for word in ["career", "professional"]):
            return "professional_career"
        elif any(word in name_lower for word in ["news", "analysis"]):
            return "news_current_events"
        elif any(word in name_lower for word in ["storytelling", "creative"]):
            return "creative_artistic"
        elif any(word in name_lower for word in ["research_paper", "science"]):
            return "science_research"
        # Dream categories
        elif any(word in name_lower for word in ["text_to_image", "image_to_image", "style_transfer", "face_swap", "professional_headshot", "emoji_generation", "photo_inpainting", "photo_outpainting", "sticker_generation"]):
            return "dream"
        # Legacy categories
        elif any(word in name_lower for word in ["security", "audit"]):
            return "security"
        elif any(word in name_lower for word in ["memory", "organization"]):
            return "memory"
        elif any(word in name_lower for word in ["autonomous", "execution", "planning"]):
            return "autonomous"
        elif any(word in name_lower for word in ["shopify", "shopping", "product"]):
            return "shopping"
        elif any(word in name_lower for word in ["rag", "retrieval"]):
            return "rag"
        return "general"
        
    def _categorize_resource(self, uri: str) -> str:
        """Categorize resources based on URI patterns"""
        uri_lower = uri.lower()
        if uri_lower.startswith("memory://"):
            return "memory"
        elif uri_lower.startswith("shopify://"):
            return "shopify"
        elif uri_lower.startswith("event://"):
            return "event"
        elif uri_lower.startswith("monitoring://"):
            return "monitoring"
        elif uri_lower.startswith("weather://"):
            return "weather"
        elif uri_lower.startswith("guardrail://"):
            return "security"
        elif uri_lower.startswith("symbolic://"):
            return "reasoning"
        elif uri_lower.startswith("rag://"):
            return "rag"
        elif uri_lower.startswith("widget://"):
            return "widget"
        return "general"
        
    async def _compute_embeddings(self):
        """Compute embeddings for all capabilities"""
        try:
            # Load cached embeddings first
            if await self._load_cached_embeddings():
                logger.info("Loaded cached embeddings")
                return
                
            # Compute embeddings for all items
            all_items = {}
            for item_type, items in self.capabilities_cache.items():
                all_items.update(items)
                
            for item_name, item_info in all_items.items():
                combined_text = f"{item_info['description']} {' '.join(item_info['keywords'])}"
                embedding = await self.embedding_generator.embed_single(
                    combined_text,
                    model="text-embedding-3-small"
                )
                self.embeddings_cache[item_name] = embedding
                
            await self._save_embeddings_cache()
            logger.info(f"Computed embeddings for {len(self.embeddings_cache)} items")
            
        except Exception as e:
            logger.error(f"Failed to compute embeddings: {e}")
            
    async def _load_cached_embeddings(self) -> bool:
        """Load cached embeddings from Supabase with error handling"""
        try:
            if not self.supabase:
                logger.warning("Supabase client not available for cached embeddings")
                return False
                
            result = self.supabase.table('mcp_unified_search_embeddings').select('item_name, embedding').execute()
            
            total_items = sum(len(items) for items in self.capabilities_cache.values())
            if result.data and len(result.data) >= total_items * 0.8:
                for row in result.data:
                    item_name = row['item_name']
                    embedding = row['embedding']
                    
                    if embedding and isinstance(embedding, list):
                        self.embeddings_cache[item_name] = embedding
                        
                logger.info(f"Loaded cached embeddings for {len(result.data)} items")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to load cached embeddings: {e}")
            return False
            
    async def _save_embeddings_cache(self):
        """Save embeddings to Supabase with error handling"""
        try:
            if not self.supabase:
                logger.warning("Supabase client not available for caching embeddings")
                return
                
            # Clear existing embeddings
            self.supabase.table('mcp_unified_search_embeddings').delete().neq('id', 0).execute()
            
            # Insert new embeddings
            batch_data = []
            all_items = {}
            for item_type, items in self.capabilities_cache.items():
                all_items.update(items)
                
            for item_name, embedding in self.embeddings_cache.items():
                if item_name in all_items:
                    item_info = all_items[item_name]
                    # Ensure all data is JSON serializable
                    data = {
                        'item_name': str(item_name),
                        'item_type': str(item_info['type']),
                        'category': str(item_info['category']),
                        'description': str(item_info['description']),
                        'embedding': embedding
                    }
                    batch_data.append(data)
                    
            if batch_data:
                self.supabase.table('mcp_unified_search_embeddings').insert(batch_data).execute()
                logger.info(f"Saved {len(batch_data)} embeddings")
                
        except Exception as e:
            logger.error(f"Failed to save embeddings: {e}")
            
    async def search(self, query: str, filters: SearchFilter = None, max_results: int = 10, user_id: Optional[str] = None) -> List[SearchResult]:
        """Unified search across all capabilities with fallback"""
        import time
        start_time = time.time()
        
        try:
            if not filters:
                filters = SearchFilter()
                
            # Handle special "default" query to return predefined collections
            if query.strip().lower() == "default":
                logger.info("Processing default query for predefined collections")
                return await self._get_default_collections(filters, max_results, user_id)
                
            # If no embeddings available, fall back to keyword search
            if not self.embeddings_cache and query.strip():
                logger.info("No embeddings available, falling back to keyword search")
                return await self._fallback_search(query, filters, max_results)
                
            # Check cache first for repeated queries
            cache_key = self._get_search_cache_key(query, filters, max_results)
            cached_result = self._get_cached_search_result(cache_key)
            was_cached = cached_result is not None
            if cached_result:
                logger.info("Returning cached search result")
                # Record cached search metrics
                response_time_ms = int((time.time() - start_time) * 1000)
                self.monitor.record_search(
                    response_time_ms=response_time_ms,
                    results_count=len(cached_result),
                    success=True,
                    used_cache=True,
                    used_fallback=False
                )
                return cached_result
            
            # Compute query embedding with caching
            query_embedding = await self._get_cached_query_embedding(query)
            if not query_embedding:
                logger.error("Failed to get query embedding, falling back to keyword search")
                return await self._fallback_search(query, filters, max_results, user_id)
            
            # Get all items to search with user filtering
            all_items = {}
            for item_type, items in self.capabilities_cache.items():
                if not filters.types or item_type.rstrip('s') in filters.types:
                    # Apply user-specific filtering for resources
                    if user_id and item_type == 'resources':
                        user_filtered_items = await self._filter_resources_by_user(items, user_id)
                        all_items.update(user_filtered_items)
                    else:
                        all_items.update(items)
                    
            # Compute similarities
            similarities = {}
            for item_name, item_info in all_items.items():
                if item_name in self.embeddings_cache:
                    import numpy as np
                    item_embedding = self.embeddings_cache[item_name]
                    similarity = np.dot(query_embedding, item_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(item_embedding)
                    )
                    similarities[item_name] = float(similarity)
                    
            # Apply filters and sort
            results = []
            sorted_items = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            
            for item_name, score in sorted_items:
                if score >= filters.min_similarity and len(results) < max_results:
                    item_info = all_items[item_name]
                    
                    # Apply category filter
                    if filters.categories and item_info['category'] not in filters.categories:
                        continue
                        
                    # Apply keyword filter
                    if filters.keywords:
                        item_keywords = [k.lower() for k in item_info['keywords']]
                        filter_keywords = [k.lower() for k in filters.keywords]
                        if not any(fk in item_keywords for fk in filter_keywords):
                            continue
                            
                    result = SearchResult(
                        name=item_name,
                        type=item_info['type'],
                        description=item_info['description'],
                        similarity_score=score,
                        category=item_info['category'],
                        keywords=item_info['keywords'],
                        metadata=item_info['metadata']
                    )
                    results.append(result)
                    
            # Cache successful results
            self._cache_search_result(cache_key, results)
            
            # Record metrics and log search
            response_time_ms = int((time.time() - start_time) * 1000)
            used_fallback = False
            
            # Record monitoring metrics
            self.monitor.record_search(
                response_time_ms=response_time_ms,
                results_count=len(results),
                success=True,
                used_cache=False,  # This path means cache miss
                used_fallback=used_fallback
            )
            
            await self._log_search(query, filters, results, response_time_ms)
            
            logger.info(f"Search completed in {response_time_ms}ms with {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in unified search: {e}")
            # Try fallback search on error
            try:
                logger.info("Attempting fallback search due to error")
                fallback_results = await self._fallback_search(query, filters, max_results, user_id)
                
                # Record fallback search metrics
                response_time_ms = int((time.time() - start_time) * 1000)
                self.monitor.record_search(
                    response_time_ms=response_time_ms,
                    results_count=len(fallback_results),
                    success=True,
                    used_cache=False,
                    used_fallback=True
                )
                
                return fallback_results
            except Exception as fallback_error:
                logger.error(f"Fallback search also failed: {fallback_error}")
                
                # Record failed search
                response_time_ms = int((time.time() - start_time) * 1000)
                self.monitor.record_search(
                    response_time_ms=response_time_ms,
                    results_count=0,
                    success=False,
                    used_cache=False,
                    used_fallback=False
                )
                
                return []
                
    async def _fallback_search(self, query: str, filters: SearchFilter, max_results: int, user_id: Optional[str] = None) -> List[SearchResult]:
        """Fallback search using keyword matching when embeddings are unavailable"""
        try:
            query_words = set(query.lower().split())
            results = []
            
            # Get all items to search with user filtering
            all_items = {}
            for item_type, items in self.capabilities_cache.items():
                if not filters.types or item_type.rstrip('s') in filters.types:
                    # Apply user-specific filtering for resources
                    if user_id and item_type == 'resources':
                        user_filtered_items = await self._filter_resources_by_user(items, user_id)
                        all_items.update(user_filtered_items)
                    else:
                        all_items.update(items)
            
            # Score items based on keyword overlap
            scored_items = []
            for item_name, item_info in all_items.items():
                # Apply filters
                if filters.categories and item_info['category'] not in filters.categories:
                    continue
                    
                if filters.keywords:
                    item_keywords = [k.lower() for k in item_info['keywords']]
                    filter_keywords = [k.lower() for k in filters.keywords]
                    if not any(fk in item_keywords for fk in filter_keywords):
                        continue
                
                # Calculate keyword overlap score
                item_words = set()
                item_words.update(item_info['name'].lower().split())
                item_words.update(item_info['description'].lower().split())
                item_words.update([k.lower() for k in item_info['keywords']])
                
                overlap = len(query_words.intersection(item_words))
                if overlap > 0:
                    # Normalize score by query length
                    score = overlap / len(query_words)
                    scored_items.append((item_name, item_info, score))
            
            # Sort by score and create results
            scored_items.sort(key=lambda x: x[2], reverse=True)
            
            for item_name, item_info, score in scored_items[:max_results]:
                if score >= filters.min_similarity:
                    result = SearchResult(
                        name=item_name,
                        type=item_info['type'],
                        description=item_info['description'],
                        similarity_score=score,
                        category=item_info['category'],
                        keywords=item_info['keywords'],
                        metadata=item_info['metadata']
                    )
                    results.append(result)
            
            logger.info(f"Fallback search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in fallback search: {e}")
            return []
            
    async def _get_default_collections(self, filters: SearchFilter, max_results: int, user_id: Optional[str] = None) -> List[SearchResult]:
        """Get predefined default collections of tools, prompts, and resources"""
        try:
            default_results = []
            
            # Default tools (most commonly used)
            if not filters.types or 'tool' in filters.types:
                default_tools = [
                    'web_search', 'web_crawl', 'web_automation',
                    'create_execution_plan', 'replan_execution', 'get_autonomous_status'
                ]
                for tool_name in default_tools:
                    if tool_name in self.capabilities_cache.get('tools', {}):
                        tool_info = self.capabilities_cache['tools'][tool_name]
                        result = SearchResult(
                            name=tool_name,
                            type='tool',
                            description=tool_info['description'],
                            similarity_score=1.0,  # Perfect match for defaults
                            category=tool_info['category'],
                            keywords=tool_info['keywords'] + ['default'],
                            metadata=tool_info['metadata']
                        )
                        default_results.append(result)
            
            # Default prompts (most commonly used)
            if not filters.types or 'prompt' in filters.types:
                default_prompts = [
                    'default_reason_prompt', 'default_response_prompt', 'default_review_prompt'
                ]
                for prompt_name in default_prompts:
                    if prompt_name in self.capabilities_cache.get('prompts', {}):
                        prompt_info = self.capabilities_cache['prompts'][prompt_name]
                        result = SearchResult(
                            name=prompt_name,
                            type='prompt',
                            description=prompt_info['description'],
                            similarity_score=1.0,
                            category=prompt_info['category'],
                            keywords=prompt_info['keywords'] + ['default'],
                            metadata=prompt_info['metadata']
                        )
                        default_results.append(result)
            
            # Default resources (commonly accessed)
            if not filters.types or 'resource' in filters.types:
                # Get user-filtered resources if user_id provided
                resources = self.capabilities_cache.get('resources', {})
                if user_id:
                    resources = await self._filter_resources_by_user(resources, user_id)
                
                # Select default resources (first few available)
                default_resource_patterns = [
                    'memory://', 'monitoring://', 'weather://', 'rag://'
                ]
                
                for pattern in default_resource_patterns:
                    matching_resources = [uri for uri in resources.keys() if uri.startswith(pattern)]
                    for resource_uri in matching_resources[:2]:  # Limit to 2 per pattern
                        if resource_uri in resources:
                            resource_info = resources[resource_uri]
                            result = SearchResult(
                                name=resource_uri,
                                type='resource',
                                description=resource_info['description'],
                                similarity_score=1.0,
                                category=resource_info['category'],
                                keywords=resource_info['keywords'] + ['default'],
                                metadata=resource_info['metadata']
                            )
                            default_results.append(result)
                            
                            if len(default_results) >= max_results:
                                break
                    
                    if len(default_results) >= max_results:
                        break
            
            # Apply additional filters if specified
            filtered_results = []
            for result in default_results:
                # Apply category filter
                if filters.categories and result.category not in filters.categories:
                    continue
                    
                # Apply keyword filter
                if filters.keywords:
                    result_keywords = [k.lower() for k in result.keywords]
                    filter_keywords = [k.lower() for k in filters.keywords]
                    if not any(fk in result_keywords for fk in filter_keywords):
                        continue
                        
                filtered_results.append(result)
                
                if len(filtered_results) >= max_results:
                    break
            
            logger.info(f"Returned {len(filtered_results)} default collection items")
            return filtered_results[:max_results]
            
        except Exception as e:
            logger.error(f"Error getting default collections: {e}")
            return []
            
    async def _filter_resources_by_user(self, resources: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Filter resources based on user access permissions and custom configurations"""
        try:
            # Try to get user-specific resources from resource managers
            user_resources = {}
            
            # Check widget resources - get user-specific widget configurations
            try:
                from resources.user_widget_resources import UserWidgetResource
                widget_resource = UserWidgetResource()
                
                # Get user's widget configurations from database
                user_widget_configs = await widget_resource._fetch_user_widget_configs(user_id)
                
                # Filter widget resources to only include user's configured widgets
                widget_resources = {uri: info for uri, info in resources.items() 
                                 if info.get('category') == 'widget'}
                
                for uri, info in widget_resources.items():
                    # Extract widget name from URI (e.g., "widget://system/info" -> check for widget configs)
                    if uri.startswith('widget://'):
                        # For system info and template resources, always include
                        if '/info' in uri or '/templates/' in uri:
                            user_resources[uri] = info
                        # For user-specific resources, check if user has configurations
                        elif f'/user/{user_id}/' in uri:
                            user_resources[uri] = info
                        # For widget type resources, check if user has that widget configured
                        elif any(widget_name in uri for widget_name in user_widget_configs.keys()):
                            user_resources[uri] = info
                
                logger.info(f"Found {len(user_resources)} widget resources for user {user_id}")
                
            except Exception as e:
                logger.debug(f"Could not access widget resources: {e}")
            
            # Check graph knowledge resources
            try:
                from resources.graph_knowledge_resources import graph_knowledge_resources
                graph_result = await graph_knowledge_resources.get_user_resources(int(user_id))
                if graph_result.get('success'):
                    for resource in graph_result.get('resources', []):
                        resource_id = resource.get('resource_id')
                        if resource_id in resources:
                            user_resources[resource_id] = resources[resource_id]
            except Exception as e:
                logger.debug(f"Could not access graph knowledge resources: {e}")
            
            # Check digital knowledge resources  
            try:
                from resources.digital_resource import digital_knowledge_resources
                digital_result = await digital_knowledge_resources.get_user_resources(user_id)
                if digital_result.get('success'):
                    for resource in digital_result.get('resources', []):
                        resource_id = resource.get('resource_id')
                        if resource_id in resources:
                            user_resources[resource_id] = resources[resource_id]
            except Exception as e:
                logger.debug(f"Could not access digital knowledge resources: {e}")
            
            # If no user-specific filtering worked, return all resources
            if not user_resources:
                logger.debug(f"No user-specific resources found for user {user_id}, returning all resources")
                return resources
                
            logger.info(f"Filtered {len(resources)} resources to {len(user_resources)} for user {user_id}")
            return user_resources
            
        except Exception as e:
            logger.error(f"Error filtering resources by user: {e}")
            return resources  # Return all resources on error
            
    def _get_search_cache_key(self, query: str, filters: SearchFilter, max_results: int) -> str:
        """Generate cache key for search request"""
        cache_data = {
            'query': query,
            'types': filters.types,
            'categories': filters.categories,
            'keywords': filters.keywords,
            'min_similarity': filters.min_similarity,
            'max_results': max_results
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
        
    def _get_cached_search_result(self, cache_key: str) -> Optional[List[SearchResult]]:
        """Get cached search result if available and fresh"""
        import time
        if cache_key in self.search_results_cache:
            cached_data = self.search_results_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_ttl_seconds:
                return cached_data['results']
            else:
                # Remove expired cache entry
                del self.search_results_cache[cache_key]
        return None
        
    def _cache_search_result(self, cache_key: str, results: List[SearchResult]):
        """Cache search results with TTL"""
        import time
        
        # Limit cache size
        if len(self.search_results_cache) >= self.max_cache_size:
            # Remove oldest entries (simple LRU)
            oldest_key = min(self.search_results_cache.keys(), 
                           key=lambda k: self.search_results_cache[k]['timestamp'])
            del self.search_results_cache[oldest_key]
            
        self.search_results_cache[cache_key] = {
            'results': results,
            'timestamp': time.time()
        }
        
    async def _get_cached_query_embedding(self, query: str) -> Optional[List[float]]:
        """Get cached query embedding or compute new one"""
        import time
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        # Check cache first
        if query_hash in self.query_embeddings_cache:
            cached_data = self.query_embeddings_cache[query_hash]
            if time.time() - cached_data['timestamp'] < self.cache_ttl_seconds:
                return cached_data['embedding']
            else:
                del self.query_embeddings_cache[query_hash]
        
        # Compute new embedding with retries
        for attempt in range(3):
            try:
                embedding = await asyncio.wait_for(
                    self.embedding_generator.embed_single(query, model="text-embedding-3-small"),
                    timeout=10.0
                )
                
                # Cache the result
                if len(self.query_embeddings_cache) >= self.max_cache_size:
                    oldest_key = min(self.query_embeddings_cache.keys(),
                                   key=lambda k: self.query_embeddings_cache[k]['timestamp'])
                    del self.query_embeddings_cache[oldest_key]
                    
                self.query_embeddings_cache[query_hash] = {
                    'embedding': embedding,
                    'timestamp': time.time()
                }
                
                return embedding
                
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Embedding attempt {attempt + 1} failed: {e}")
                if attempt == 2:
                    logger.error("All embedding attempts failed")
                    return None
        
        return None
        
    def clear_caches(self):
        """Clear all performance caches"""
        self.search_results_cache.clear()
        self.query_embeddings_cache.clear()
        # Also clear capabilities cache to force refresh
        self.capabilities_cache = {'tools': {}, 'prompts': {}, 'resources': {}}
        self.embeddings_cache = {}
        logger.info("All caches cleared")
        
    async def force_refresh(self):
        """Force refresh of capabilities cache"""
        try:
            self.clear_caches()
            if self.mcp_server:
                await self._refresh_capabilities()
                await self._compute_embeddings()
                logger.info("Forced cache refresh completed")
        except Exception as e:
            logger.error(f"Error during forced refresh: {e}")
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        import time
        current_time = time.time()
        
        # Count fresh entries
        fresh_search_results = sum(1 for data in self.search_results_cache.values() 
                                 if current_time - data['timestamp'] < self.cache_ttl_seconds)
        fresh_query_embeddings = sum(1 for data in self.query_embeddings_cache.values()
                                   if current_time - data['timestamp'] < self.cache_ttl_seconds)
        
        return {
            'search_results_cache': {
                'total_entries': len(self.search_results_cache),
                'fresh_entries': fresh_search_results,
                'max_size': self.max_cache_size
            },
            'query_embeddings_cache': {
                'total_entries': len(self.query_embeddings_cache),
                'fresh_entries': fresh_query_embeddings,
                'max_size': self.max_cache_size
            },
            'cache_ttl_seconds': self.cache_ttl_seconds
        }
        
    def get_monitoring_metrics(self) -> Dict[str, Any]:
        """Get comprehensive monitoring metrics"""
        return self.monitor.get_diagnostic_info()
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status"""
        return self.monitor.check_health()
        
    def reset_monitoring_metrics(self):
        """Reset monitoring metrics"""
        self.monitor.reset_metrics()
            
    async def search_by_category(self, category: str, item_type: str = None) -> List[SearchResult]:
        """Search by category"""
        filters = SearchFilter(
            types=[item_type] if item_type else None,
            categories=[category],
            min_similarity=0.0  # No similarity requirement for category search
        )
        return await self.search("", filters, max_results=50)
        
    async def search_by_keywords(self, keywords: List[str], item_type: str = None) -> List[SearchResult]:
        """Search by keywords"""
        filters = SearchFilter(
            types=[item_type] if item_type else None,
            keywords=keywords,
            min_similarity=0.0  # No similarity requirement for keyword search
        )
        return await self.search(" ".join(keywords), filters)
        
    async def get_capabilities_summary(self) -> Dict[str, Any]:
        """Get summary of all capabilities"""
        try:
            summary = {}
            for item_type, items in self.capabilities_cache.items():
                categories = {}
                for item_info in items.values():
                    category = item_info['category']
                    if category not in categories:
                        categories[category] = 0
                    categories[category] += 1
                    
                summary[item_type] = {
                    'total': len(items),
                    'categories': categories
                }
                
            return summary
            
        except Exception as e:
            logger.error(f"Error getting capabilities summary: {e}")
            return {}
            
    async def get_capabilities(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all capabilities with optional user filtering"""
        try:
            capabilities = {}
            
            for item_type, items in self.capabilities_cache.items():
                # Apply user-specific filtering for resources
                if user_id and item_type == 'resources':
                    filtered_items = await self._filter_resources_by_user(items, user_id)
                    capabilities[item_type] = list(filtered_items.values())
                else:
                    capabilities[item_type] = list(items.values())
                    
            # Add metadata
            total_count = sum(len(items) for items in capabilities.values())
            capabilities['metadata'] = {
                'total_count': total_count,
                'last_updated': str(self.last_updated) if self.last_updated else None,
                'user_filtered': user_id is not None
            }
            
            # Ensure JSON serializable by converting to strings where needed
            import json
            try:
                json.dumps(capabilities)  # Test serialization
            except TypeError as e:
                logger.warning(f"Capabilities not JSON serializable: {e}")
                # Fallback: convert to string representation
                for key, value in capabilities.items():
                    if key != 'metadata':
                        capabilities[key] = str(value)
            
            return capabilities
            
        except Exception as e:
            logger.error(f"Error getting capabilities: {e}")
            return {'error': str(e)}
            
    async def get_capabilities_by_type(self, capability_type: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get capabilities filtered by type (tools, prompts, resources)"""
        try:
            if capability_type not in self.capabilities_cache:
                return {'error': f"Invalid capability type: {capability_type}"}
                
            items = self.capabilities_cache[capability_type]
            
            # Apply user-specific filtering for resources
            if user_id and capability_type == 'resources':
                filtered_items = await self._filter_resources_by_user(items, user_id)
                capabilities = list(filtered_items.values())
            else:
                capabilities = list(items.values())
                
            return {
                'type': capability_type,
                'capabilities': capabilities,
                'count': len(capabilities),
                'user_filtered': user_id is not None and capability_type == 'resources'
            }
            
        except Exception as e:
            logger.error(f"Error getting capabilities by type: {e}")
            return {'error': str(e)}
            
    async def get_tool_security_levels(self) -> Dict[str, Any]:
        """Get security levels for all tools"""
        try:
            security_info = {}
            
            # Get tools from cache
            tools = self.capabilities_cache.get('tools', {})
            
            for tool_name, tool_info in tools.items():
                metadata = tool_info.get('metadata', {})
                security_info[tool_name] = {
                    'name': tool_name,
                    'category': tool_info.get('category', 'general'),
                    'security_level': metadata.get('security_level', 'DEFAULT'),
                    'security_level_value': metadata.get('security_level_value', 1),
                    'requires_authorization': metadata.get('requires_authorization', False),
                    'description': tool_info.get('description', '')
                }
            
            # Add security policy information
            security_summary = {
                'total_tools': len(security_info),
                'security_levels': {
                    'LOW': len([t for t in security_info.values() if t['security_level_value'] == 1]),
                    'MEDIUM': len([t for t in security_info.values() if t['security_level_value'] == 2]),
                    'HIGH': len([t for t in security_info.values() if t['security_level_value'] == 3]),
                    'CRITICAL': len([t for t in security_info.values() if t['security_level_value'] == 4]),
                    'DEFAULT': len([t for t in security_info.values() if t['security_level'] == 'DEFAULT'])
                },
                'authorization_required': len([t for t in security_info.values() if t['requires_authorization']]),
                'rate_limits': self.security_policy.rate_limits
            }
            
            return {
                'tools': security_info,
                'summary': security_summary,
                'security_policy_version': '1.0'
            }
            
        except Exception as e:
            logger.error(f"Error getting tool security levels: {e}")
            return {'error': str(e)}
            
    async def search_by_security_level(self, security_level: str, max_results: int = 20) -> List[SearchResult]:
        """Search tools by security level"""
        try:
            results = []
            tools = self.capabilities_cache.get('tools', {})
            
            for tool_name, tool_info in tools.items():
                metadata = tool_info.get('metadata', {})
                tool_security_level = metadata.get('security_level', 'DEFAULT')
                
                if tool_security_level.upper() == security_level.upper():
                    result = SearchResult(
                        name=tool_name,
                        type='tool',
                        description=tool_info['description'],
                        similarity_score=1.0,  # Perfect match for security level
                        category=tool_info['category'],
                        keywords=tool_info['keywords'] + [f'security_{security_level.lower()}'],
                        metadata=tool_info['metadata']
                    )
                    results.append(result)
                    
                    if len(results) >= max_results:
                        break
            
            logger.info(f"Found {len(results)} tools with security level {security_level}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching by security level: {e}")
            return []
            
    async def _log_search(self, query: str, filters: SearchFilter, results: List[SearchResult], response_time_ms: int = None):
        """Log search for analytics with performance metrics"""
        try:
            if not self.supabase:
                return
                
            # Ensure all data is JSON serializable
            data = {
                'query': str(query),
                'filters': {
                    'types': filters.types if filters.types else [],
                    'categories': filters.categories if filters.categories else [],
                    'keywords': filters.keywords if filters.keywords else [],
                    'min_similarity': float(filters.min_similarity)
                },
                'results_count': len(results),
                'top_results': [str(r.name) for r in results[:5]],
                'result_types': [str(r.type) for r in results],
                'response_time_ms': response_time_ms
            }
            
            self.supabase.table('mcp_search_history').insert(data).execute()
            
        except Exception as e:
            logger.error(f"Failed to log search: {e}")

# Global instance
_search_service = None

async def get_search_service(mcp_server=None):
    """Get search service instance"""
    global _search_service
    if _search_service is None:
        _search_service = UnifiedSearchService(mcp_server)
        if mcp_server:
            await _search_service.initialize(mcp_server)
    return _search_service