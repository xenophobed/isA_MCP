"""
Unit tests for Redis cache versioning and pattern invalidation.

Tests the cache improvements in PR #31:
- Cache version prefix
- Batched pattern invalidation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.cache.redis_cache import RedisCache, CACHE_VERSION, CACHE_PREFIX


class TestCacheVersioning:
    """Test cache versioning (#17)."""

    def test_cache_version_in_prefix(self):
        """Cache prefix should include version number."""
        assert f"v{CACHE_VERSION}" in CACHE_PREFIX
        assert CACHE_PREFIX == f"mcp:cache:v{CACHE_VERSION}:"

    def test_versioned_cache_keys(self):
        """Cache keys should be prefixed with version."""
        mock_client = AsyncMock()
        cache = RedisCache.__new__(RedisCache)
        cache._client = mock_client
        cache._enabled = True

        # Check that keys include version prefix
        key = cache._make_key("tool", "id:123")
        assert key == f"mcp:cache:v{CACHE_VERSION}:tool:id:123"

    @pytest.mark.asyncio
    async def test_version_change_invalidates_old_cache(self):
        """Changing CACHE_VERSION should make old keys inaccessible."""
        mock_client = AsyncMock()
        mock_client.get.return_value = None  # Old key not found

        cache = RedisCache.__new__(RedisCache)
        cache._client = mock_client
        cache._enabled = True

        # Try to get data from old cache (different version)
        result = await cache.get("tool", "id:123")

        # Should call get with versioned key
        call_args = mock_client.get.call_args[0][0]
        assert f"v{CACHE_VERSION}" in call_args
        assert result is None  # Old cache miss


class TestBatchedPatternInvalidation:
    """Test batched SCAN invalidation (#17)."""

    @pytest.mark.asyncio
    async def test_invalidate_pattern_single_batch(self):
        """Should handle <10k keys in single batch."""
        mock_client = AsyncMock()
        # Return 100 keys, then empty (all keys in first batch)
        mock_client.list_keys.side_effect = [
            [f"mcp:cache:v1:tool:id:{i}" for i in range(100)],
            [],
        ]
        mock_client.delete_multiple = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        cache = RedisCache.__new__(RedisCache)
        cache._client = mock_client
        cache._enabled = True

        deleted = await cache.invalidate_pattern("tool:")

        assert deleted == 100
        assert mock_client.list_keys.call_count == 1
        assert mock_client.delete_multiple.call_count == 1

    @pytest.mark.asyncio
    async def test_invalidate_pattern_multiple_batches(self):
        """Should handle >10k keys across multiple batches."""
        mock_client = AsyncMock()

        # Simulate 25k keys across 3 batches
        batch_1 = [f"key_{i}" for i in range(10000)]  # Full batch
        batch_2 = [f"key_{i}" for i in range(10000, 20000)]  # Full batch
        batch_3 = [f"key_{i}" for i in range(20000, 25000)]  # Partial (5k keys)

        mock_client.list_keys.side_effect = [batch_1, batch_2, batch_3]
        mock_client.delete_multiple = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        cache = RedisCache.__new__(RedisCache)
        cache._client = mock_client
        cache._enabled = True

        deleted = await cache.invalidate_pattern("tool:")

        assert deleted == 25000
        assert mock_client.list_keys.call_count == 3
        assert mock_client.delete_multiple.call_count == 3

        # Verify batch size parameter
        for call in mock_client.list_keys.call_args_list:
            assert call[1]["limit"] == 10000

    @pytest.mark.asyncio
    async def test_invalidate_pattern_stops_on_partial_batch(self):
        """Should stop when batch size < limit (exhausted results)."""
        mock_client = AsyncMock()

        # Return partial batch (< 10k) on first call
        mock_client.list_keys.return_value = [f"key_{i}" for i in range(500)]
        mock_client.delete_multiple = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        cache = RedisCache.__new__(RedisCache)
        cache._client = mock_client
        cache._enabled = True

        deleted = await cache.invalidate_pattern("tool:")

        assert deleted == 500
        # Should not call list_keys again after partial batch
        assert mock_client.list_keys.call_count == 1

    @pytest.mark.asyncio
    async def test_invalidate_pattern_handles_errors(self):
        """Should return 0 and log warning on errors."""
        mock_client = AsyncMock()
        mock_client.list_keys.side_effect = Exception("Redis connection error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        cache = RedisCache.__new__(RedisCache)
        cache._client = mock_client
        cache._enabled = True

        deleted = await cache.invalidate_pattern("tool:")

        assert deleted == 0  # Error returns 0

    @pytest.mark.asyncio
    async def test_invalidate_pattern_respects_version_prefix(self):
        """Pattern invalidation should use versioned prefix."""
        mock_client = AsyncMock()
        mock_client.list_keys.return_value = []
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        cache = RedisCache.__new__(RedisCache)
        cache._client = mock_client
        cache._enabled = True

        await cache.invalidate_pattern("tool:")

        # Verify the pattern includes version prefix
        call_args = mock_client.list_keys.call_args[0][0]
        assert call_args == f"mcp:cache:v{CACHE_VERSION}:tool:*"


class TestCacheInvalidationHelpers:
    """Test specific invalidation helper methods."""

    @pytest.mark.asyncio
    async def test_invalidate_tool(self):
        """Should invalidate specific tool and tool lists."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.delete = AsyncMock()
        mock_client.list_keys.return_value = []  # For pattern invalidation

        cache = RedisCache.__new__(RedisCache)
        cache._client = mock_client
        cache._enabled = True

        await cache.invalidate_tool(tool_id=123, tool_name="test_tool")

        # Should delete specific keys and invalidate patterns
        assert mock_client.delete.call_count == 2  # id and name keys
        assert mock_client.list_keys.call_count == 2  # tool_list and search patterns

    @pytest.mark.asyncio
    async def test_invalidate_prompt(self):
        """Should invalidate specific prompt and prompt lists."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.delete = AsyncMock()
        mock_client.list_keys.return_value = []

        cache = RedisCache.__new__(RedisCache)
        cache._client = mock_client
        cache._enabled = True

        await cache.invalidate_prompt(prompt_id=456)

        assert mock_client.delete.call_count == 1  # id key only
        assert mock_client.list_keys.call_count == 1  # prompt_list pattern
