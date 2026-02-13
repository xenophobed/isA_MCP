"""
Mock for Redis client.

Provides a mock implementation of Redis client
for testing cache operations without a real Redis instance.
"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
import time


@dataclass
class MockRedisValue:
    """Represents a cached value with optional TTL."""

    value: Any
    expire_at: Optional[float] = None

    def is_expired(self) -> bool:
        """Check if value is expired."""
        if self.expire_at is None:
            return False
        return time.time() > self.expire_at


class MockRedisClient:
    """
    Mock for Redis client.

    Provides in-memory cache for testing.

    Example usage:
        client = MockRedisClient()
        await client.set("key", "value", ex=60)
        value = await client.get("key")
        assert value == "value"
    """

    def __init__(self):
        self._data: Dict[str, MockRedisValue] = {}
        self._sets: Dict[str, Set[str]] = {}
        self._lists: Dict[str, List[str]] = {}
        self._hashes: Dict[str, Dict[str, str]] = {}
        self._closed = False

    # ═══════════════════════════════════════════════════════════════
    # String Operations
    # ═══════════════════════════════════════════════════════════════

    async def get(self, key: str) -> Optional[str]:
        """Get a string value."""
        self._cleanup_expired()

        if key not in self._data:
            return None

        item = self._data[key]
        if item.is_expired():
            del self._data[key]
            return None

        return item.value

    async def set(
        self,
        key: str,
        value: str,
        ex: int = None,
        px: int = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """Set a string value."""
        # Handle nx (only set if not exists)
        if nx and key in self._data and not self._data[key].is_expired():
            return False

        # Handle xx (only set if exists)
        if xx and (key not in self._data or self._data[key].is_expired()):
            return False

        expire_at = None
        if ex:
            expire_at = time.time() + ex
        elif px:
            expire_at = time.time() + (px / 1000)

        self._data[key] = MockRedisValue(value=value, expire_at=expire_at)
        return True

    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set with expiration in seconds."""
        return await self.set(key, value, ex=seconds)

    async def setnx(self, key: str, value: str) -> bool:
        """Set if not exists."""
        return await self.set(key, value, nx=True)

    async def mget(self, *keys: str) -> List[Optional[str]]:
        """Get multiple values."""
        return [await self.get(key) for key in keys]

    async def mset(self, mapping: Dict[str, str]) -> bool:
        """Set multiple values."""
        for key, value in mapping.items():
            await self.set(key, value)
        return True

    async def incr(self, key: str) -> int:
        """Increment integer value."""
        current = await self.get(key)
        new_value = int(current or 0) + 1
        await self.set(key, str(new_value))
        return new_value

    async def decr(self, key: str) -> int:
        """Decrement integer value."""
        current = await self.get(key)
        new_value = int(current or 0) - 1
        await self.set(key, str(new_value))
        return new_value

    # ═══════════════════════════════════════════════════════════════
    # Key Operations
    # ═══════════════════════════════════════════════════════════════

    async def delete(self, *keys: str) -> int:
        """Delete keys."""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
            if key in self._sets:
                del self._sets[key]
                count += 1
            if key in self._lists:
                del self._lists[key]
                count += 1
            if key in self._hashes:
                del self._hashes[key]
                count += 1
        return count

    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        self._cleanup_expired()
        count = 0
        for key in keys:
            if key in self._data and not self._data[key].is_expired():
                count += 1
        return count

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        if key not in self._data:
            return False
        self._data[key].expire_at = time.time() + seconds
        return True

    async def ttl(self, key: str) -> int:
        """Get time to live in seconds."""
        if key not in self._data:
            return -2

        item = self._data[key]
        if item.expire_at is None:
            return -1

        remaining = int(item.expire_at - time.time())
        return max(remaining, 0)

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        self._cleanup_expired()
        import fnmatch

        return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]

    # ═══════════════════════════════════════════════════════════════
    # Hash Operations
    # ═══════════════════════════════════════════════════════════════

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field."""
        if name not in self._hashes:
            return None
        return self._hashes[name].get(key)

    async def hset(
        self, name: str, key: str = None, value: str = None, mapping: Dict = None
    ) -> int:
        """Set hash field(s)."""
        if name not in self._hashes:
            self._hashes[name] = {}

        count = 0
        if key and value:
            self._hashes[name][key] = value
            count = 1
        if mapping:
            for k, v in mapping.items():
                self._hashes[name][k] = v
                count += 1
        return count

    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields."""
        return self._hashes.get(name, {}).copy()

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        if name not in self._hashes:
            return 0
        count = 0
        for key in keys:
            if key in self._hashes[name]:
                del self._hashes[name][key]
                count += 1
        return count

    async def hexists(self, name: str, key: str) -> bool:
        """Check if hash field exists."""
        return name in self._hashes and key in self._hashes[name]

    # ═══════════════════════════════════════════════════════════════
    # Set Operations
    # ═══════════════════════════════════════════════════════════════

    async def sadd(self, name: str, *values: str) -> int:
        """Add members to set."""
        if name not in self._sets:
            self._sets[name] = set()
        before = len(self._sets[name])
        self._sets[name].update(values)
        return len(self._sets[name]) - before

    async def srem(self, name: str, *values: str) -> int:
        """Remove members from set."""
        if name not in self._sets:
            return 0
        before = len(self._sets[name])
        self._sets[name] -= set(values)
        return before - len(self._sets[name])

    async def smembers(self, name: str) -> Set[str]:
        """Get all set members."""
        return self._sets.get(name, set()).copy()

    async def sismember(self, name: str, value: str) -> bool:
        """Check if value is in set."""
        return value in self._sets.get(name, set())

    # ═══════════════════════════════════════════════════════════════
    # List Operations
    # ═══════════════════════════════════════════════════════════════

    async def lpush(self, name: str, *values: str) -> int:
        """Push to left of list."""
        if name not in self._lists:
            self._lists[name] = []
        for value in values:
            self._lists[name].insert(0, value)
        return len(self._lists[name])

    async def rpush(self, name: str, *values: str) -> int:
        """Push to right of list."""
        if name not in self._lists:
            self._lists[name] = []
        self._lists[name].extend(values)
        return len(self._lists[name])

    async def lpop(self, name: str) -> Optional[str]:
        """Pop from left of list."""
        if name not in self._lists or not self._lists[name]:
            return None
        return self._lists[name].pop(0)

    async def rpop(self, name: str) -> Optional[str]:
        """Pop from right of list."""
        if name not in self._lists or not self._lists[name]:
            return None
        return self._lists[name].pop()

    async def lrange(self, name: str, start: int, end: int) -> List[str]:
        """Get range from list."""
        if name not in self._lists:
            return []
        if end == -1:
            return self._lists[name][start:]
        return self._lists[name][start : end + 1]

    async def llen(self, name: str) -> int:
        """Get list length."""
        return len(self._lists.get(name, []))

    # ═══════════════════════════════════════════════════════════════
    # Utility Methods
    # ═══════════════════════════════════════════════════════════════

    def _cleanup_expired(self) -> None:
        """Remove expired keys."""
        expired = [k for k, v in self._data.items() if v.is_expired()]
        for key in expired:
            del self._data[key]

    async def flushdb(self) -> bool:
        """Clear all data."""
        self._data.clear()
        self._sets.clear()
        self._lists.clear()
        self._hashes.clear()
        return True

    async def ping(self) -> str:
        """Ping the server."""
        return "PONG"

    async def close(self) -> None:
        """Close connection."""
        self._closed = True

    def is_closed(self) -> bool:
        """Check if closed."""
        return self._closed
