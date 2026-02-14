# Reliability & Infrastructure

Infrastructure reliability features and best practices for ISA MCP platform.

## Overview

The platform implements multiple reliability features:
- **Retry Logic** - Exponential backoff for transient failures
- **Overflow Protection** - Vector ID capacity monitoring
- **Atomic Operations** - Race-condition-free database operations
- **Migration Safety** - Transactional migrations with rollback support
- **Cache Versioning** - Schema-aware cache invalidation

## Vector Database Reliability

### Point ID Overflow Detection

**Problem:** Vector embeddings use type-based ID offsets (tools: 0-999K, prompts: 1M-2M, resources: 2M-3M). Exceeding 1M items per type causes ID collisions.

**Solution:** Automatic overflow detection with warnings and errors.

```python
# services/vector_service/vector_repository.py

# Configuration
_MAX_ITEMS_PER_TYPE = 1_000_000
_OVERFLOW_WARNING_THRESHOLD = 900_000  # Warn at 90%

def _compute_point_id(self, item_type: str, db_id: int) -> int:
    """Compute unique Qdrant point ID with overflow protection."""
    offset = self.TYPE_OFFSETS.get(item_type, 0)

    # Error at capacity
    if db_id >= _MAX_ITEMS_PER_TYPE:
        raise ValueError(
            f"Point ID overflow: {item_type} db_id={db_id} exceeds "
            f"max {_MAX_ITEMS_PER_TYPE - 1}. IDs would collide."
        )

    # Warn approaching capacity
    if db_id >= _OVERFLOW_WARNING_THRESHOLD:
        logger.warning(
            f"Point ID approaching limit: {item_type} db_id={db_id} "
            f"({db_id / _MAX_ITEMS_PER_TYPE:.0%} of capacity)"
        )

    return offset + db_id
```

**Capacity Planning:**
- Monitor warning logs for items approaching 900K
- Plan migration to new offset ranges before hitting 1M
- Consider sharding or collection partitioning for large datasets

### Qdrant Retry Logic

**Problem:** Transient Qdrant failures (network issues, temporary overload) cause operation failures without automatic recovery.

**Solution:** Exponential backoff retry with configurable attempts.

```python
# Configuration
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 0.5  # seconds

async def _retry_qdrant(coro_factory, operation_name: str):
    """Retry Qdrant operation with exponential backoff."""
    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            return await coro_factory()
        except Exception as e:
            last_exc = e
            if attempt < _MAX_RETRIES - 1:
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    f"Qdrant {operation_name} failed (attempt {attempt + 1}/{_MAX_RETRIES}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
    raise last_exc

# Usage
await _retry_qdrant(
    lambda: self.client.upsert_points(collection, points),
    operation_name=f"upsert point {point_id}"
)
```

**Retry Schedule:**
- Attempt 1: Immediate
- Attempt 2: 0.5s delay
- Attempt 3: 1.0s delay
- Attempt 4: Fail with exception

**Applied to:**
- `upsert_vector()` - Embedding storage
- `delete_vector()` - Embedding deletion

**Consistency Note:** Retry helps with transient failures but doesn't solve Qdrant/PostgreSQL consistency. For full consistency, consider implementing two-phase delete pattern (mark deleted in PostgreSQL → delete from Qdrant → hard delete from PostgreSQL).

## Database Reliability

### Atomic Delete Operations

**Problem:** Separate COUNT + DELETE queries have race condition window where data could change between queries.

```python
# Before (vulnerable to race condition)
count_sql = "SELECT COUNT(*) FROM mcp.tools WHERE source_server_id = $1"
result = await self.db.query_row(count_sql, params=[server_id])
count = result.get("count", 0)

delete_sql = "DELETE FROM mcp.tools WHERE source_server_id = $1"
await self.db.execute(delete_sql, params=[server_id])
# Data could have been inserted/deleted between COUNT and DELETE
```

**Solution:** CTE-based atomic operation.

```python
# After (atomic)
delete_sql = """
    WITH deleted AS (
        DELETE FROM mcp.tools
        WHERE source_server_id = $1
        RETURNING 1
    )
    SELECT COUNT(*) as count FROM deleted
"""
result = await self.db.query_row(delete_sql, params=[server_id])
count = result.get("count", 0)
# Count and delete are atomic - single database operation
```

**Applied to:**
- `tool_repository.delete_tools_by_server()`
- `prompt_repository.delete_prompts_by_server()`
- `resource_repository.delete_resources_by_server()`

**Benefits:**
- No race conditions
- Accurate count of deleted rows
- Single database round-trip (performance)

### Migration Safety

**Problem:** Schema migrations can cause data loss if not properly wrapped in transactions.

**Solution:** Transactional migrations with backups and rollback instructions.

```sql
-- Migration: 003_refined_skill_categories.sql
BEGIN;

-- 1. Create backup before destructive operations
CREATE TABLE IF NOT EXISTS mcp.tool_skill_assignments_backup_003 AS
SELECT * FROM mcp.tool_skill_assignments;

-- 2. Perform migration changes
DELETE FROM mcp.tool_skill_assignments
WHERE skill_id NOT IN (SELECT id FROM mcp.skill_categories);

UPDATE mcp.skill_categories SET ...;

-- 3. Commit transaction
COMMIT;

-- 4. Rollback instructions (commented for reference)
-- BEGIN;
-- DROP TABLE IF EXISTS mcp.skill_categories_new;
-- RESTORE FROM mcp.tool_skill_assignments_backup_003;
-- COMMIT;
```

**Migration Checklist:**
- ✅ Wrapped in BEGIN/COMMIT
- ✅ Backup tables created before destructive operations
- ✅ Rollback SQL provided in comments
- ✅ Uses IF NOT EXISTS / IF EXISTS for idempotency
- ✅ Tested on staging database before production

**Migrations with Multi-Tenant Fields:**
All multi-tenant migrations include safe defaults and backfill:

```sql
BEGIN;

-- Add columns with safe defaults
ALTER TABLE mcp.tools
ADD COLUMN IF NOT EXISTS org_id UUID,
ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;

-- Backfill existing data as global
UPDATE mcp.tools
SET is_global = TRUE
WHERE is_global IS NULL;

-- Add scoped unique constraints
CREATE UNIQUE INDEX IF NOT EXISTS idx_tools_name_global
ON mcp.tools(name)
WHERE is_global = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tools_name_org
ON mcp.tools(name, org_id)
WHERE is_global = FALSE;

COMMIT;
```

## Cache Reliability

### Cache Versioning

**Problem:** Schema migrations may change data format, but cached data remains in old format until TTL expires.

**Solution:** Version-prefixed cache keys that auto-invalidate on schema changes.

```python
# core/cache/redis_cache.py

# Increment this when schema migrations change cached data format
CACHE_VERSION = 1

# Cache keys automatically include version
CACHE_PREFIX = f"mcp:cache:v{CACHE_VERSION}:"

# Example keys
"mcp:cache:v1:tool:id:123"
"mcp:cache:v1:tool_list:category:system"
```

**Invalidation Flow:**
1. Schema migration deployed (changes tool data structure)
2. Increment `CACHE_VERSION` to 2
3. New cache prefix: `mcp:cache:v2:`
4. All reads miss cache (old v1 keys not found)
5. Cache repopulated with new data format
6. Old v1 keys expire naturally (TTL)

**Cache Cleanup:**
```python
# Optional: Manual cleanup of old cache keys
async def cleanup_old_cache_versions(redis_client, current_version: int):
    """Delete cache keys from previous versions."""
    for old_version in range(1, current_version):
        pattern = f"mcp:cache:v{old_version}:*"
        deleted = await redis_client.delete_pattern(pattern)
        logger.info(f"Deleted {deleted} keys from cache v{old_version}")
```

### Batched Pattern Invalidation

**Problem:** Single-shot SCAN with limit=10000 may miss keys if total keys exceed limit.

**Solution:** Loop batched SCAN until exhausted.

```python
async def invalidate_pattern(self, pattern: str) -> int:
    """Invalidate all keys matching pattern (batched for large key sets)."""
    total_deleted = 0
    batch_size = 10000

    async with self._client:
        while True:
            keys = await self._client.list_keys(full_pattern, limit=batch_size)
            if not keys:
                break

            await self._client.delete_multiple(keys)
            total_deleted += len(keys)

            # If batch < limit, we've exhausted all matches
            if len(keys) < batch_size:
                break

    return total_deleted
```

**Use Cases:**
- Tool list cache invalidation after tool update
- Search cache invalidation after embedding update
- Batch cleanup during migrations

## Error Handling

### Async Task Error Callbacks

**Problem:** Fire-and-forget asyncio tasks silently fail without logging errors.

```python
# Before (silent failures)
async def register_tools(mcp):
    # If this fails, error is lost
    ...

asyncio.create_task(register_tools(mcp))  # No error handling
```

**Solution:** Add error callback to log failures.

```python
# After (errors logged)
task = asyncio.create_task(register_func(mcp))
task.add_done_callback(
    lambda t, name=module_name: (
        logger.error(f"Async registration failed for {name}: {t.exception()}")
        if t.exception() else None
    )
)
```

**Applied to:**
- `core/auto_discovery.py` - Tool/prompt/resource registration

### Resource Leak Prevention

**Problem:** Context managers not properly cleaned up on initialization failure.

```python
# Before (resource leak)
session_cm = session_type(...)
await session_cm.__aenter__()
await asyncio.wait_for(session.initialize(), timeout=self._connection_timeout)
# If initialize() fails, __aexit__() never called → LEAK
```

**Solution:** Proper exception handling with cleanup.

```python
# After (no leak)
session_cm = session_type(...)
await session_cm.__aenter__()
try:
    await asyncio.wait_for(session.initialize(), timeout=self._connection_timeout)
except Exception:
    await session_cm.__aexit__(*sys.exc_info())  # Cleanup
    raise
```

**Applied to:**
- `services/aggregator_service/session_manager.py` - SSE and HTTP session creation

### Exception Handling

**Problem:** Bare `except:` blocks catch `SystemExit` and `KeyboardInterrupt`, preventing graceful shutdown.

```python
# Before (dangerous)
try:
    risky_operation()
except:  # Catches SystemExit, KeyboardInterrupt
    pass
```

**Solution:** Specific exception types.

```python
# After (safe)
try:
    risky_operation()
except OSError:  # File operations
    pass
except (json.JSONDecodeError, ValueError):  # Parsing
    pass
except Exception:  # Generic fallback (still allows SystemExit)
    pass
```

**Replaced 22 bare excepts across:**
- File operations → `OSError`
- JSON parsing → `json.JSONDecodeError, ValueError, TypeError`
- Font loading → `OSError, IOError`
- Process operations → `ProcessLookupError`
- Generic cleanup → `Exception`

## Monitoring & Alerting

### Key Metrics to Monitor

**Vector Database:**
- Point ID usage per type (warn at 900K, alert at 1M)
- Qdrant operation retry rate
- Failed operations after retry exhaustion

**Cache:**
- Cache hit/miss ratios per namespace
- Cache invalidation frequency
- Old version cache key count (after version bump)

**Database:**
- Long-running transactions (migration safety)
- DELETE operation counts (atomic deletes)
- Multi-tenant query performance (index usage)

### Log Patterns

```python
# Overflow warning
logger.warning("Point ID approaching limit: tool db_id=920000 (92% of capacity)")

# Retry attempts
logger.warning("Qdrant upsert point 42 failed (attempt 1/3): ConnectionError. Retrying in 0.5s...")

# Successful recovery
logger.info("Deleted vector: 42")  # After retry

# Cache invalidation
logger.debug("Cache INVALIDATE: mcp:cache:v1:tool:* (25000 keys)")

# Async task failure
logger.error("Async registration failed for my_custom_tools: ValueError: Invalid config")
```

## Best Practices

1. **Idempotent Operations**
   - Migrations use IF (NOT) EXISTS
   - Retry logic safe for duplicate operations
   - CTE deletes don't double-count

2. **Graceful Degradation**
   - Cache failures logged, not raised
   - Retry exhaustion returns error (doesn't crash)
   - Overflow warning allows continued operation (error only at limit)

3. **Observability**
   - Log all retry attempts
   - Track overflow warnings
   - Monitor cache version transitions

4. **Capacity Planning**
   - Set alerts at 80% capacity (800K items)
   - Plan migration before 90% (900K items)
   - Test overflow behavior in staging

5. **Testing Reliability**
   - Test retry logic with mock failures
   - Test overflow at exact boundaries
   - Test cache versioning across migrations

## Next Steps

- [Configuration](./configuration) - Infrastructure setup
- [Security](./security) - Security reliability
- [Multi-Tenant](./multi-tenant) - Tenant data reliability
