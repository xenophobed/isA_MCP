"""
Tool Repository - Data access layer for MCP tools
Handles database operations for tool registry with Redis caching
"""

import json
import logging
from typing import Dict, Any, Optional, List

from isa_common import AsyncPostgresClient
from core.config import get_settings
from core.cache import get_cache

logger = logging.getLogger(__name__)


class ToolRepository:
    """Tool repository - data access layer"""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Initialize tool repository

        Args:
            host: PostgreSQL gRPC server host (defaults to config)
            port: PostgreSQL gRPC server port (defaults to config)
        """
        settings = get_settings()
        host = host or settings.infrastructure.postgres_grpc_host
        port = port or settings.infrastructure.postgres_grpc_port

        self.db = AsyncPostgresClient(host=host, port=port, user_id="mcp-tool-service")
        self.schema = "mcp"
        self.table = "tools"

    async def get_tool_by_id(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """Get tool by ID (cached)"""
        cache = get_cache()
        cache_key = f"id:{tool_id}"

        # Try cache first
        cached = await cache.get("tool", cache_key)
        if cached is not None:
            return cached

        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE id = $1", params=[tool_id]
                )

            # Cache result
            if result:
                await cache.set("tool", cache_key, result)

            return result
        except Exception as e:
            logger.error(f"Failed to get tool by ID {tool_id}: {e}")
            return None

    # Alias for compatibility with tool_aggregator
    async def get_tool(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """Alias for get_tool_by_id"""
        return await self.get_tool_by_id(tool_id)

    async def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool by name (cached)"""
        cache = get_cache()
        cache_key = f"name:{name}"

        # Try cache first
        cached = await cache.get("tool", cache_key)
        if cached is not None:
            return cached

        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE name = $1", params=[name]
                )

            # Cache result
            if result:
                await cache.set("tool", cache_key, result)

            return result
        except Exception as e:
            logger.error(f"Failed to get tool by name {name}: {e}")
            return None

    async def list_tools(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = True,
        limit: int = 100,
        offset: int = 0,
        org_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List tools with optional filters (cached)"""
        cache = get_cache()
        cache_key = f"list:{org_id}:{category}:{is_active}:{limit}:{offset}"

        # Try cache first
        cached = await cache.get("tool_list", cache_key)
        if cached is not None:
            return cached

        try:
            # Build query dynamically
            where_clauses = []
            params = []
            param_idx = 1

            # Tenant filter: show global + org's own; without org_id show global only
            if org_id:
                where_clauses.append(f"(is_global = TRUE OR org_id = ${param_idx})")
                params.append(org_id)
                param_idx += 1
            else:
                where_clauses.append("is_global = TRUE")

            if category is not None:
                where_clauses.append(f"category = ${param_idx}")
                params.append(category)
                param_idx += 1

            if is_active is not None:
                where_clauses.append(f"is_active = ${param_idx}")
                params.append(is_active)
                param_idx += 1

            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)

            sql = f"""
                SELECT * FROM {self.schema}.{self.table}
                {where_sql}
                ORDER BY name ASC
                LIMIT {limit} OFFSET {offset}
            """

            async with self.db:
                results = await self.db.query(sql, params=params)

            results = results or []

            # Cache result
            if results:
                await cache.set("tool_list", cache_key, results)

            return results
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []

    async def get_default_tools(self) -> List[Dict[str, Any]]:
        """
        Get default tools (meta-tools that are always available).

        These are tools marked with is_default=True, typically meta-tools
        like discover, execute, get_tool_schema, etc.
        """
        cache = get_cache()
        cache_key = "default_tools"

        # Try cache first
        cached = await cache.get("tool_list", cache_key)
        if cached is not None:
            return cached

        try:
            sql = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE is_default = TRUE AND is_active = TRUE
                ORDER BY name ASC
            """

            async with self.db:
                results = await self.db.query(sql)

            results = results or []

            # Cache result
            if results:
                await cache.set("tool_list", cache_key, results)

            logger.info(f"Loaded {len(results)} default tools")
            return results
        except Exception as e:
            logger.error(f"Failed to get default tools: {e}")
            return []

    async def create_tool(self, tool_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new tool (internal or external)"""
        try:
            # Serialize complex types to JSON strings for gRPC compatibility
            input_schema = tool_data.get("input_schema", {})
            metadata = tool_data.get("metadata", {})
            skill_ids = tool_data.get("skill_ids", [])

            # Prepare data (let database set created_at/updated_at)
            record = {
                "name": tool_data["name"],
                "description": tool_data.get("description"),
                "category": tool_data.get("category"),
                "input_schema": (
                    json.dumps(input_schema) if isinstance(input_schema, dict) else input_schema
                ),
                "metadata": json.dumps(metadata) if isinstance(metadata, dict) else metadata,
                "is_active": tool_data.get("is_active", True),
                "is_default": tool_data.get("is_default", False),
                # External tool fields
                "source_server_id": tool_data.get("source_server_id"),
                "original_name": tool_data.get("original_name"),
                "is_external": tool_data.get("is_external", False),
                "is_classified": tool_data.get("is_classified", False),
                "skill_ids": skill_ids if isinstance(skill_ids, list) else [],
                "primary_skill_id": tool_data.get("primary_skill_id"),
                # Multi-tenant fields
                "org_id": tool_data.get("org_id"),
                "is_global": tool_data.get("is_global", True),
            }

            async with self.db:
                count = await self.db.insert_into(self.table, [record], schema=self.schema)

            if count and count > 0:
                # Invalidate list caches
                cache = get_cache()
                await cache.invalidate_pattern("tool_list:")

                # Retrieve the created tool
                return await self.get_tool_by_name(tool_data["name"])
            return None
        except Exception as e:
            logger.error(f"Failed to create tool: {e}")
            return None

    async def create_external_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        source_server_id: str,
        original_name: str,
        org_id: Optional[str] = None,
        is_global: bool = True,
    ) -> Optional[int]:
        """
        Create an external tool from an MCP server.

        Args:
            name: Namespaced tool name (server.tool_name)
            description: Tool description
            input_schema: Tool input JSON schema
            source_server_id: UUID of the source external server
            original_name: Original tool name before namespacing
            org_id: Organization ID for org-scoped tools
            is_global: Whether this tool is globally visible

        Returns:
            Tool ID if created, None on failure
        """
        # Use upsert to handle reconnections where tools already exist
        return await self.upsert_external_tool(
            name=name,
            description=description,
            input_schema=input_schema,
            source_server_id=source_server_id,
            original_name=original_name,
            org_id=org_id,
            is_global=is_global,
        )

    async def upsert_external_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        source_server_id: str,
        original_name: str,
        org_id: Optional[str] = None,
        is_global: bool = True,
    ) -> Optional[int]:
        """
        Upsert an external tool - insert or update if exists.

        Uses ON CONFLICT to handle reconnections where tools already exist.

        Args:
            name: Namespaced tool name (server.tool_name)
            description: Tool description
            input_schema: Tool input JSON schema
            source_server_id: UUID of the source external server
            original_name: Original tool name before namespacing
            org_id: Organization ID for org-scoped tools
            is_global: Whether this tool is globally visible

        Returns:
            Tool ID if created/updated, None on failure
        """
        try:
            input_schema_json = (
                json.dumps(input_schema) if isinstance(input_schema, dict) else input_schema
            )

            sql = f"""
                INSERT INTO {self.schema}.{self.table}
                (name, description, input_schema, source_server_id, original_name, is_external, is_classified, is_active, org_id, is_global)
                VALUES ($1, $2, $3::jsonb, $4, $5, TRUE, FALSE, TRUE, $6, $7)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    input_schema = EXCLUDED.input_schema,
                    source_server_id = EXCLUDED.source_server_id,
                    original_name = EXCLUDED.original_name,
                    org_id = EXCLUDED.org_id,
                    is_global = EXCLUDED.is_global,
                    updated_at = NOW()
                RETURNING id
            """

            async with self.db:
                results = await self.db.query(
                    sql,
                    params=[
                        name,
                        description,
                        input_schema_json,
                        source_server_id,
                        original_name,
                        org_id,
                        is_global,
                    ],
                )

            if results and len(results) > 0:
                return results[0].get("id")
            return None
        except Exception as e:
            logger.error(f"Failed to upsert external tool {name}: {e}")
            return None

    async def update_tool(self, tool_id: int, updates: Dict[str, Any]) -> bool:
        """Update tool (invalidates cache)"""
        try:
            # Build SET clause
            set_parts = []
            params = []
            param_idx = 1

            # Serialize complex types to JSON strings for gRPC compatibility
            for key, value in updates.items():
                if key not in ["id", "created_at", "updated_at"]:  # Skip immutable fields
                    # Serialize complex types
                    if key in ["input_schema", "metadata"]:
                        if isinstance(value, dict):
                            value = json.dumps(value)

                    set_parts.append(f"{key} = ${param_idx}")
                    params.append(value)
                    param_idx += 1

            if not set_parts:
                return False

            # Add tool_id
            params.append(tool_id)

            sql = f"""
                UPDATE {self.schema}.{self.table}
                SET {', '.join(set_parts)}
                WHERE id = ${param_idx}
            """

            async with self.db:
                await self.db.execute(sql, params=params)

            # Invalidate cache
            cache = get_cache()
            await cache.invalidate_tool(tool_id=tool_id)

            return True
        except Exception as e:
            logger.error(f"Failed to update tool {tool_id}: {e}")
            return False

    async def delete_tool(self, tool_id: int) -> bool:
        """Delete tool (soft delete - set is_active to false)"""
        try:
            return await self.update_tool(tool_id, {"is_active": False})
        except Exception as e:
            logger.error(f"Failed to delete tool {tool_id}: {e}")
            return False

    async def increment_call_count(
        self, tool_id: int, success: bool, response_time_ms: int
    ) -> bool:
        """Increment tool call statistics"""
        try:
            success_field = "success_count" if success else "failure_count"

            sql = f"""
                UPDATE {self.schema}.{self.table}
                SET
                    call_count = call_count + 1,
                    {success_field} = {success_field} + 1,
                    avg_response_time_ms = (
                        (avg_response_time_ms * call_count + $1) / (call_count + 1)
                    ),
                    last_used_at = NOW()
                WHERE id = $2
            """

            async with self.db:
                await self.db.execute(sql, params=[response_time_ms, tool_id])
            return True
        except Exception as e:
            logger.error(f"Failed to increment call count for tool {tool_id}: {e}")
            return False

    async def get_tool_statistics(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """Get tool usage statistics"""
        try:
            sql = f"""
                SELECT
                    id,
                    name,
                    call_count,
                    success_count,
                    failure_count,
                    avg_response_time_ms,
                    last_used_at,
                    {self.schema}.tools_success_rate(id) as success_rate
                FROM {self.schema}.{self.table}
                WHERE id = $1
            """

            async with self.db:
                result = await self.db.query_row(sql, params=[tool_id])
            return result
        except Exception as e:
            logger.error(f"Failed to get tool statistics for {tool_id}: {e}")
            return None

    async def search_tools(
        self, query: str, limit: int = 10, org_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search tools by name or description (cached)"""
        cache = get_cache()
        cache_key = f"search:{org_id}:{query}:{limit}"

        # Try cache first (short TTL for search)
        cached = await cache.get("search", cache_key)
        if cached is not None:
            return cached

        try:
            params = []
            param_idx = 1

            # Tenant filter: show global + org's own; without org_id show global only
            if org_id:
                tenant_clause = f"AND (is_global = TRUE OR org_id = ${param_idx})"
                params.append(org_id)
                param_idx += 1
            else:
                tenant_clause = "AND is_global = TRUE"

            query_pattern = f"%{query}%"
            params.append(query_pattern)
            pattern_param = f"${param_idx}"

            sql = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE
                    (name ILIKE {pattern_param} OR description ILIKE {pattern_param})
                    AND is_active = TRUE
                    {tenant_clause}
                ORDER BY
                    CASE
                        WHEN name ILIKE {pattern_param} THEN 1
                        ELSE 2
                    END,
                    call_count DESC
                LIMIT {limit}
            """

            async with self.db:
                results = await self.db.query(sql, params=params)

            results = results or []

            # Cache result (30 second TTL for search)
            if results:
                await cache.set("search", cache_key, results, ttl=30)

            return results
        except Exception as e:
            logger.error(f"Failed to search tools: {e}")
            return []

    # =========================================================================
    # External Tool Methods
    # =========================================================================

    async def list_external_tools(
        self,
        server_id: Optional[str] = None,
        is_classified: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
        org_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List external tools with optional filters.

        Args:
            server_id: Filter by source server UUID
            is_classified: Filter by classification status
            limit: Maximum results
            offset: Pagination offset
            org_id: Organization ID for tenant filtering

        Returns:
            List of external tools
        """
        try:
            where_clauses = ["is_external = TRUE", "is_active = TRUE"]
            params = []
            param_idx = 1

            # Tenant filter: show global + org's own; without org_id show global only
            if org_id:
                where_clauses.append(f"(is_global = TRUE OR org_id = ${param_idx})")
                params.append(org_id)
                param_idx += 1
            else:
                where_clauses.append("is_global = TRUE")

            if server_id is not None:
                where_clauses.append(f"source_server_id = ${param_idx}")
                params.append(server_id)
                param_idx += 1

            if is_classified is not None:
                where_clauses.append(f"is_classified = ${param_idx}")
                params.append(is_classified)
                param_idx += 1

            where_sql = "WHERE " + " AND ".join(where_clauses)

            sql = f"""
                SELECT * FROM {self.schema}.{self.table}
                {where_sql}
                ORDER BY name ASC
                LIMIT {limit} OFFSET {offset}
            """

            async with self.db:
                results = await self.db.query(sql, params=params)
            return results or []
        except Exception as e:
            logger.error(f"Failed to list external tools: {e}")
            return []

    async def get_tool_ids_by_server(self, server_id: str) -> List[int]:
        """
        Get all tool IDs from a specific external server.

        Used for cleanup when removing a server.

        Args:
            server_id: External server UUID

        Returns:
            List of tool IDs
        """
        try:
            sql = f"""
                SELECT id FROM {self.schema}.{self.table}
                WHERE source_server_id = $1
            """

            async with self.db:
                results = await self.db.query(sql, params=[server_id])

            return [row["id"] for row in results] if results else []
        except Exception as e:
            logger.error(f"Failed to get tool IDs for server {server_id}: {e}")
            return []

    async def delete_tools_by_server(self, server_id: str) -> int:
        """
        Delete all tools from a specific external server.

        Args:
            server_id: External server UUID

        Returns:
            Number of tools deleted
        """
        try:
            # Atomic count-and-delete in a single statement
            delete_sql = f"""
                WITH deleted AS (
                    DELETE FROM {self.schema}.{self.table}
                    WHERE source_server_id = $1
                    RETURNING 1
                )
                SELECT COUNT(*) as count FROM deleted
            """
            async with self.db:
                result = await self.db.query_row(delete_sql, params=[server_id])
                count = result.get("count", 0) if result else 0

            logger.info(f"Deleted {count} tools from server {server_id}")
            return count
        except Exception as e:
            logger.error(f"Failed to delete tools for server {server_id}: {e}")
            return 0

    async def update_tool_classification(
        self, tool_id: int, skill_ids: List[str], primary_skill_id: Optional[str] = None
    ) -> bool:
        """
        Update tool skill classification.

        Args:
            tool_id: Tool ID
            skill_ids: List of assigned skill IDs
            primary_skill_id: Primary skill assignment

        Returns:
            True if updated successfully
        """
        try:
            updates = {
                "skill_ids": skill_ids,
                "primary_skill_id": primary_skill_id or (skill_ids[0] if skill_ids else None),
                "is_classified": len(skill_ids) > 0,
            }
            return await self.update_tool(tool_id, updates)
        except Exception as e:
            logger.error(f"Failed to update classification for tool {tool_id}: {e}")
            return False

    async def get_unclassified_tools(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get tools that haven't been classified yet.

        Returns:
            List of unclassified tools
        """
        try:
            sql = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE is_classified = FALSE AND is_active = TRUE
                ORDER BY created_at ASC
                LIMIT {limit}
            """

            async with self.db:
                results = await self.db.query(sql)
            return results or []
        except Exception as e:
            logger.error(f"Failed to get unclassified tools: {e}")
            return []

    async def get_tools_by_skill(self, skill_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get tools assigned to a specific skill.

        Args:
            skill_id: Skill ID to filter by
            limit: Maximum results

        Returns:
            List of tools with the given skill
        """
        try:
            sql = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE $1 = ANY(skill_ids) AND is_active = TRUE
                ORDER BY
                    CASE WHEN primary_skill_id = $1 THEN 0 ELSE 1 END,
                    name ASC
                LIMIT {limit}
            """

            async with self.db:
                results = await self.db.query(sql, params=[skill_id])
            return results or []
        except Exception as e:
            logger.error(f"Failed to get tools by skill {skill_id}: {e}")
            return []

    # =========================================================================
    # Atomic Multi-Step Operations (Transaction Boundaries)
    # =========================================================================

    async def delete_tools_by_server_atomic(self, server_id: str) -> int:
        """
        Atomically delete all tools from a specific external server.

        TRANSACTION BOUNDARY: Count + Delete (atomic)

        Uses a CTE to ensure the count and delete happen atomically,
        preventing race conditions where tools could be added between
        counting and deleting.

        Args:
            server_id: External server UUID

        Returns:
            Number of tools deleted
        """
        try:
            # Atomic count-and-delete in a single statement via CTE
            delete_sql = f"""
                WITH deleted AS (
                    DELETE FROM {self.schema}.{self.table}
                    WHERE source_server_id = $1
                    RETURNING id
                )
                SELECT COUNT(*) as count FROM deleted
            """
            async with self.db:
                result = await self.db.query_row(delete_sql, params=[server_id])
                count = result.get("count", 0) if result else 0

            # Invalidate caches
            if count > 0:
                cache = get_cache()
                await cache.invalidate_pattern("tool_list:")

            logger.info(f"Atomically deleted {count} tools from server {server_id}")
            return count
        except Exception as e:
            logger.error(f"Failed to delete tools for server {server_id}: {e}")
            return 0
