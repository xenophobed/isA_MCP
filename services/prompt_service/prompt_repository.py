"""
Prompt Repository - Data access layer for MCP prompts
Handles database operations for prompt registry
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from isa_common.postgres_client import PostgresClient

logger = logging.getLogger(__name__)


class PromptRepository:
    """Prompt repository - data access layer"""

    def __init__(self, host='isa-postgres-grpc', port=50061):
        """
        Initialize prompt repository

        Args:
            host: PostgreSQL gRPC server host
            port: PostgreSQL gRPC server port
        """
        self.db = PostgresClient(host=host, port=port, user_id='mcp-prompt-service')
        self.schema = "mcp"
        self.table = "prompts"

    async def get_prompt_by_id(self, prompt_id: int) -> Optional[Dict[str, Any]]:
        """Get prompt by ID"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE id = $1",
                    [prompt_id],
                    schema=self.schema
                )
                return result
        except Exception as e:
            logger.error(f"Failed to get prompt by ID {prompt_id}: {e}")
            return None

    async def get_prompt_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get prompt by name"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE name = $1",
                    [name],
                    schema=self.schema
                )
                return result
        except Exception as e:
            logger.error(f"Failed to get prompt by name {name}: {e}")
            return None

    async def list_prompts(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = True,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List prompts with optional filters"""
        try:
            with self.db:
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

                if tags:
                    where_clauses.append(f"tags && ${param_idx}")
                    params.append(tags)
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
            logger.error(f"Failed to list prompts: {e}")
            return []

    async def create_prompt(self, prompt_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new prompt"""
        try:
            with self.db:
                record = {
                    'name': prompt_data['name'],
                    'description': prompt_data.get('description'),
                    'category': prompt_data.get('category'),
                    'content': prompt_data['content'],
                    'arguments': prompt_data.get('arguments', []),
                    'metadata': prompt_data.get('metadata', {}),
                    'tags': prompt_data.get('tags', []),
                    'version': prompt_data.get('version', '1.0.0'),
                    'is_active': prompt_data.get('is_active', True)
                }

                count = self.db.insert_into(self.table, [record], schema=self.schema)

                if count and count > 0:
                    return await self.get_prompt_by_name(prompt_data['name'])
                return None
        except Exception as e:
            logger.error(f"Failed to create prompt: {e}")
            return None

    async def update_prompt(self, prompt_id: int, updates: Dict[str, Any]) -> bool:
        """Update prompt"""
        try:
            with self.db:
                set_parts = []
                params = []
                param_idx = 1

                for key, value in updates.items():
                    if key not in ['id', 'created_at', 'updated_at']:
                        set_parts.append(f"{key} = ${param_idx}")
                        params.append(value)
                        param_idx += 1

                if not set_parts:
                    return False

                params.append(prompt_id)

                sql = f"""
                    UPDATE {self.schema}.{self.table}
                    SET {', '.join(set_parts)}
                    WHERE id = ${param_idx}
                """

                self.db.execute(sql, params, schema=self.schema)
                return True
        except Exception as e:
            logger.error(f"Failed to update prompt {prompt_id}: {e}")
            return False

    async def delete_prompt(self, prompt_id: int) -> bool:
        """Delete prompt (soft delete)"""
        try:
            return await self.update_prompt(prompt_id, {'is_active': False})
        except Exception as e:
            logger.error(f"Failed to delete prompt {prompt_id}: {e}")
            return False

    async def increment_usage_count(self, prompt_id: int, generation_time_ms: int) -> bool:
        """Increment prompt usage statistics"""
        try:
            with self.db:
                sql = f"""
                    UPDATE {self.schema}.{self.table}
                    SET
                        usage_count = usage_count + 1,
                        avg_generation_time_ms = (
                            (avg_generation_time_ms * usage_count + $1) / (usage_count + 1)
                        ),
                        last_used_at = NOW()
                    WHERE id = $2
                """

                self.db.execute(sql, [generation_time_ms, prompt_id], schema=self.schema)
                return True
        except Exception as e:
            logger.error(f"Failed to increment usage count for prompt {prompt_id}: {e}")
            return False

    async def search_prompts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search prompts by name, description, or content"""
        try:
            with self.db:
                sql = f"""
                    SELECT * FROM {self.schema}.{self.table}
                    WHERE
                        (name ILIKE $1 OR description ILIKE $1 OR content ILIKE $1)
                        AND is_active = TRUE
                    ORDER BY
                        CASE
                            WHEN name ILIKE $1 THEN 1
                            WHEN description ILIKE $1 THEN 2
                            ELSE 3
                        END,
                        usage_count DESC
                    LIMIT {limit}
                """

                query_pattern = f"%{query}%"
                results = self.db.query(sql, [query_pattern], schema=self.schema)
                return results or []
        except Exception as e:
            logger.error(f"Failed to search prompts: {e}")
            return []

    async def search_by_tags(self, tags: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Search prompts by tags"""
        try:
            with self.db:
                sql = f"""
                    SELECT * FROM {self.schema}.{self.table}
                    WHERE tags && $1 AND is_active = TRUE
                    ORDER BY usage_count DESC
                    LIMIT {limit}
                """

                results = self.db.query(sql, [tags], schema=self.schema)
                return results or []
        except Exception as e:
            logger.error(f"Failed to search prompts by tags: {e}")
            return []
