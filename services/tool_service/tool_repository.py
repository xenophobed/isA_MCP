"""
Tool Repository - Data access layer for MCP tools
Handles database operations for tool registry
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from isa_common.postgres_client import PostgresClient

logger = logging.getLogger(__name__)


class ToolRepository:
    """Tool repository - data access layer"""

    def __init__(self, host='isa-postgres-grpc', port=50061):
        """
        Initialize tool repository

        Args:
            host: PostgreSQL gRPC server host
            port: PostgreSQL gRPC server port
        """
        self.db = PostgresClient(host=host, port=port, user_id='mcp-tool-service')
        self.schema = "mcp"
        self.table = "tools"

    async def get_tool_by_id(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """Get tool by ID"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE id = $1",
                    [tool_id],
                    schema=self.schema
                )
                return result
        except Exception as e:
            logger.error(f"Failed to get tool by ID {tool_id}: {e}")
            return None

    async def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool by name"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE name = $1",
                    [name],
                    schema=self.schema
                )
                return result
        except Exception as e:
            logger.error(f"Failed to get tool by name {name}: {e}")
            return None

    async def list_tools(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List tools with optional filters"""
        try:
            with self.db:
                # Build query dynamically
                where_clauses = []
                params = []
                param_idx = 1

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

                results = self.db.query(sql, params, schema=self.schema)
                return results or []
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []

    async def create_tool(self, tool_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new tool"""
        try:
            with self.db:
                # Serialize complex types to JSON strings for gRPC compatibility
                input_schema = tool_data.get('input_schema', {})
                metadata = tool_data.get('metadata', {})

                # Prepare data (let database set created_at/updated_at)
                record = {
                    'name': tool_data['name'],
                    'description': tool_data.get('description'),
                    'category': tool_data.get('category'),
                    'input_schema': json.dumps(input_schema) if isinstance(input_schema, dict) else input_schema,
                    'metadata': json.dumps(metadata) if isinstance(metadata, dict) else metadata,
                    'is_active': tool_data.get('is_active', True)
                }

                count = self.db.insert_into(self.table, [record], schema=self.schema)

                if count and count > 0:
                    # Retrieve the created tool
                    return await self.get_tool_by_name(tool_data['name'])
                return None
        except Exception as e:
            logger.error(f"Failed to create tool: {e}")
            return None

    async def update_tool(self, tool_id: int, updates: Dict[str, Any]) -> bool:
        """Update tool"""
        try:
            with self.db:
                # Build SET clause
                set_parts = []
                params = []
                param_idx = 1

                # Serialize complex types to JSON strings for gRPC compatibility
                for key, value in updates.items():
                    if key not in ['id', 'created_at', 'updated_at']:  # Skip immutable fields
                        # Serialize complex types
                        if key in ['input_schema', 'metadata']:
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

                self.db.execute(sql, params, schema=self.schema)
                return True
        except Exception as e:
            logger.error(f"Failed to update tool {tool_id}: {e}")
            return False

    async def delete_tool(self, tool_id: int) -> bool:
        """Delete tool (soft delete - set is_active to false)"""
        try:
            return await self.update_tool(tool_id, {'is_active': False})
        except Exception as e:
            logger.error(f"Failed to delete tool {tool_id}: {e}")
            return False

    async def increment_call_count(self, tool_id: int, success: bool, response_time_ms: int) -> bool:
        """Increment tool call statistics"""
        try:
            with self.db:
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

                self.db.execute(sql, [response_time_ms, tool_id], schema=self.schema)
                return True
        except Exception as e:
            logger.error(f"Failed to increment call count for tool {tool_id}: {e}")
            return False

    async def get_tool_statistics(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """Get tool usage statistics"""
        try:
            with self.db:
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

                result = self.db.query_row(sql, [tool_id], schema=self.schema)
                return result
        except Exception as e:
            logger.error(f"Failed to get tool statistics for {tool_id}: {e}")
            return None

    async def search_tools(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search tools by name or description"""
        try:
            with self.db:
                sql = f"""
                    SELECT * FROM {self.schema}.{self.table}
                    WHERE
                        (name ILIKE $1 OR description ILIKE $1)
                        AND is_active = TRUE
                    ORDER BY
                        CASE
                            WHEN name ILIKE $1 THEN 1
                            ELSE 2
                        END,
                        call_count DESC
                    LIMIT {limit}
                """

                query_pattern = f"%{query}%"
                results = self.db.query(sql, [query_pattern], schema=self.schema)
                return results or []
        except Exception as e:
            logger.error(f"Failed to search tools: {e}")
            return []
