"""
Redis Cache Layer for MCP Services

Provides caching for tools, prompts, and resources to reduce database load.
Uses the cache prefixes defined in mcp_config.py.
"""

import json
import logging
import hashlib
from typing import Any, Optional, List, Callable, TypeVar
from functools import wraps

from isa_common import AsyncRedisClient
from core.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Cache TTLs (in seconds)
CACHE_TTL = {
    "tool": 300,  # 5 minutes
    "tool_list": 60,  # 1 minute (lists change more frequently)
    "prompt": 300,  # 5 minutes
    "resource": 300,  # 5 minutes
    "search": 30,  # 30 seconds (search results are dynamic)
    "skill": 600,  # 10 minutes (skills are more static)
}

# Cache version — increment when schema migrations change cached data format.
# This ensures stale data from a previous schema is never served.
CACHE_VERSION = 1

# Cache key prefixes (from mcp_config.py)
CACHE_PREFIX = f"mcp:cache:v{CACHE_VERSION}:"


class RedisCache:
    """Redis cache wrapper for MCP services"""

    _instance: Optional["RedisCache"] = None

    def __init__(self):
        settings = get_settings()
        self._client = AsyncRedisClient(
            host=settings.infrastructure.redis_host,
            port=settings.infrastructure.redis_port,
            user_id="mcp-cache-service",
        )
        self._enabled = True

    @classmethod
    def get_instance(cls) -> "RedisCache":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = RedisCache()
        return cls._instance

    def _make_key(self, namespace: str, key: str) -> str:
        """Create cache key with prefix"""
        return f"{CACHE_PREFIX}{namespace}:{key}"

    def _hash_params(self, params: dict) -> str:
        """Create hash from parameters for cache key"""
        param_str = json.dumps(params, sort_keys=True, default=str)
        return hashlib.md5(param_str.encode()).hexdigest()[:12]

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._enabled:
            return None

        try:
            cache_key = self._make_key(namespace, key)
            async with self._client:
                value = await self._client.get(cache_key)

            if value:
                logger.debug(f"Cache HIT: {cache_key}")
                return json.loads(value)

            logger.debug(f"Cache MISS: {cache_key}")
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    async def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL"""
        if not self._enabled:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            ttl = ttl or CACHE_TTL.get(namespace, 300)

            async with self._client:
                await self._client.set(cache_key, json.dumps(value, default=str), ttl_seconds=ttl)

            logger.debug(f"Cache SET: {cache_key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    async def delete(self, namespace: str, key: str) -> bool:
        """Delete value from cache"""
        if not self._enabled:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            async with self._client:
                await self._client.delete(cache_key)

            logger.debug(f"Cache DELETE: {cache_key}")
            return True
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern.

        Uses batched SCAN to handle large key sets without missing keys.
        """
        if not self._enabled:
            return 0

        try:
            full_pattern = f"{CACHE_PREFIX}{pattern}*"
            total_deleted = 0
            batch_size = 10000

            async with self._client:
                while True:
                    keys = await self._client.list_keys(full_pattern, limit=batch_size)
                    if not keys:
                        break
                    await self._client.delete_multiple(keys)
                    total_deleted += len(keys)
                    # If we got fewer than batch_size, we've exhausted all matches
                    if len(keys) < batch_size:
                        break

            logger.debug(f"Cache INVALIDATE: {full_pattern} ({total_deleted} keys)")
            return total_deleted
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")
            return 0

    async def invalidate_tool(self, tool_id: Optional[int] = None, tool_name: Optional[str] = None):
        """Invalidate tool cache entries"""
        if tool_id:
            await self.delete("tool", f"id:{tool_id}")
        if tool_name:
            await self.delete("tool", f"name:{tool_name}")
        # Also invalidate tool lists
        await self.invalidate_pattern("tool_list:")
        await self.invalidate_pattern("search:")

    async def invalidate_prompt(
        self, prompt_id: Optional[int] = None, prompt_name: Optional[str] = None
    ):
        """Invalidate prompt cache entries"""
        if prompt_id:
            await self.delete("prompt", f"id:{prompt_id}")
        if prompt_name:
            await self.delete("prompt", f"name:{prompt_name}")
        await self.invalidate_pattern("prompt_list:")

    async def invalidate_resource(
        self, resource_id: Optional[int] = None, uri: Optional[str] = None
    ):
        """Invalidate resource cache entries"""
        if resource_id:
            await self.delete("resource", f"id:{resource_id}")
        if uri:
            await self.delete("resource", f"uri:{uri}")
        await self.invalidate_pattern("resource_list:")


# Global cache instance
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get global cache instance"""
    global _cache
    if _cache is None:
        _cache = RedisCache.get_instance()
    return _cache


def cached(
    namespace: str, key_func: Optional[Callable[..., str]] = None, ttl: Optional[int] = None
):
    """
    Decorator to cache async function results.

    Usage:
        @cached('tool', key_func=lambda tool_id: f"id:{tool_id}")
        async def get_tool_by_id(self, tool_id: int):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache = get_cache()

            # Generate cache key
            if key_func:
                # Skip 'self' argument if method
                cache_key = key_func(*args[1:], **kwargs) if args else key_func(**kwargs)
            else:
                # Auto-generate key from function name and args
                params = {"args": args[1:] if args else (), "kwargs": kwargs}
                cache_key = f"{func.__name__}:{cache._hash_params(params)}"

            # Try cache first
            cached_value = await cache.get(namespace, cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                await cache.set(namespace, cache_key, result, ttl)

            return result

        return wrapper

    return decorator
