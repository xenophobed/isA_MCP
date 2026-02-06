"""
Prompt Repository - Data access layer for MCP prompts
Handles database operations for prompt registry
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from isa_common import AsyncPostgresClient
from core.config import get_settings

logger = logging.getLogger(__name__)


class PromptRepository:
    """Prompt repository - data access layer"""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Initialize prompt repository

        Args:
            host: PostgreSQL gRPC server host (defaults to config)
            port: PostgreSQL gRPC server port (defaults to config)
        """
        settings = get_settings()
        host = host or settings.infrastructure.postgres_grpc_host
        port = port or settings.infrastructure.postgres_grpc_port

        self.db = AsyncPostgresClient(host=host, port=port, user_id='mcp-prompt-service')
        self.schema = "mcp"
        self.table = "prompts"

    async def get_prompt_by_id(self, prompt_id: int) -> Optional[Dict[str, Any]]:
        """Get prompt by ID"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE id = $1",
                    params=[prompt_id]
                )
            return result
        except Exception as e:
            logger.error(f"Failed to get prompt by ID {prompt_id}: {e}")
            return None

    async def get_prompt_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get prompt by name"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE name = $1",
                    params=[name]
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

            async with self.db:
                results = await self.db.query(sql, params=params)
            return results or []
        except Exception as e:
            logger.error(f"Failed to list prompts: {e}")
            return []

    async def create_prompt(self, prompt_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new prompt (internal or external)"""
        try:
            # Serialize complex types to JSON strings for gRPC compatibility
            arguments = prompt_data.get('arguments', [])
            metadata = prompt_data.get('metadata', {})
            tags = prompt_data.get('tags', [])

            # Handle skill_ids
            skill_ids = prompt_data.get('skill_ids', [])
            if not isinstance(skill_ids, list):
                skill_ids = []

            record = {
                'name': prompt_data['name'],
                'description': prompt_data.get('description'),
                'category': prompt_data.get('category'),
                'content': prompt_data['content'],
                'arguments': json.dumps(arguments) if isinstance(arguments, (list, dict)) else arguments,  # jsonb field
                'metadata': json.dumps(metadata) if isinstance(metadata, dict) else metadata,  # jsonb field
                'tags': tags if isinstance(tags, list) else [],  # array field - pass as list, not JSON string
                'version': prompt_data.get('version', '1.0.0'),
                'is_active': prompt_data.get('is_active', True),
                # External prompt fields
                'source_server_id': prompt_data.get('source_server_id'),
                'original_name': prompt_data.get('original_name'),
                'is_external': prompt_data.get('is_external', False),
                # Skill classification fields (hierarchical search)
                'skill_ids': skill_ids,
                'primary_skill_id': prompt_data.get('primary_skill_id'),
                'is_classified': prompt_data.get('is_classified', False),
            }

            async with self.db:
                count = await self.db.insert_into(self.table, [record], schema=self.schema)

            if count and count > 0:
                return await self.get_prompt_by_name(prompt_data['name'])
            return None
        except Exception as e:
            logger.error(f"Failed to create prompt: {e}")
            return None

    async def create_external_prompt(
        self,
        name: str,
        description: str,
        content: str,
        arguments: List[Dict[str, Any]],
        source_server_id: str,
        original_name: str
    ) -> Optional[int]:
        """
        Create an external prompt from an MCP server.

        Args:
            name: Namespaced prompt name (server.prompt_name)
            description: Prompt description
            content: Prompt content/template
            arguments: Prompt arguments schema
            source_server_id: UUID of the source external server
            original_name: Original prompt name before namespacing

        Returns:
            Prompt ID if created, None on failure
        """
        prompt_data = {
            'name': name,
            'description': description,
            'content': content,
            'arguments': arguments,
            'source_server_id': source_server_id,
            'original_name': original_name,
            'is_external': True,
            'is_active': True,
        }
        result = await self.create_prompt(prompt_data)
        return result.get('id') if result else None

    async def update_prompt(self, prompt_id: int, updates: Dict[str, Any]) -> bool:
        """Update prompt"""
        try:
            set_parts = []
            params = []
            param_idx = 1

            # Serialize complex types to JSON strings for gRPC compatibility
            for key, value in updates.items():
                if key not in ['id', 'created_at', 'updated_at']:
                    # Serialize complex types
                    if key in ['arguments', 'metadata']:  # jsonb fields
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value)
                    elif key == 'tags':  # array field - keep as list
                        if not isinstance(value, list):
                            value = []

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

            async with self.db:
                await self.db.execute(sql, params=params)
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

            async with self.db:
                await self.db.execute(sql, params=[generation_time_ms, prompt_id])
            return True
        except Exception as e:
            logger.error(f"Failed to increment usage count for prompt {prompt_id}: {e}")
            return False

    async def search_prompts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search prompts by name, description, or content"""
        try:
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
            async with self.db:
                results = await self.db.query(sql, params=[query_pattern])
            return results or []
        except Exception as e:
            logger.error(f"Failed to search prompts: {e}")
            return []

    async def search_by_tags(self, tags: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Search prompts by tags"""
        try:
            sql = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE tags && $1 AND is_active = TRUE
                ORDER BY usage_count DESC
                LIMIT {limit}
            """

            async with self.db:
                results = await self.db.query(sql, params=[tags])
            return results or []
        except Exception as e:
            logger.error(f"Failed to search prompts by tags: {e}")
            return []

    # =========================================================================
    # External Prompt Methods
    # =========================================================================

    async def list_external_prompts(
        self,
        server_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List external prompts with optional filters.

        Args:
            server_id: Filter by source server UUID
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of external prompts
        """
        try:
            where_clauses = ["is_external = TRUE", "is_active = TRUE"]
            params = []
            param_idx = 1

            if server_id is not None:
                where_clauses.append(f"source_server_id = ${param_idx}")
                params.append(server_id)
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
            logger.error(f"Failed to list external prompts: {e}")
            return []

    async def get_prompt_ids_by_server(self, server_id: str) -> List[int]:
        """
        Get all prompt IDs from a specific external server.

        Used for cleanup when removing a server.

        Args:
            server_id: External server UUID

        Returns:
            List of prompt IDs
        """
        try:
            sql = f"""
                SELECT id FROM {self.schema}.{self.table}
                WHERE source_server_id = $1
            """

            async with self.db:
                results = await self.db.query(sql, params=[server_id])

            return [row['id'] for row in results] if results else []
        except Exception as e:
            logger.error(f"Failed to get prompt IDs for server {server_id}: {e}")
            return []

    async def delete_prompts_by_server(self, server_id: str) -> int:
        """
        Delete all prompts from a specific external server.

        Args:
            server_id: External server UUID

        Returns:
            Number of prompts deleted
        """
        try:
            # Get count first
            count_sql = f"""
                SELECT COUNT(*) as count FROM {self.schema}.{self.table}
                WHERE source_server_id = $1
            """
            async with self.db:
                result = await self.db.query_row(count_sql, params=[server_id])
                count = result.get('count', 0) if result else 0

                # Delete the prompts
                delete_sql = f"""
                    DELETE FROM {self.schema}.{self.table}
                    WHERE source_server_id = $1
                """
                await self.db.execute(delete_sql, params=[server_id])

            logger.info(f"Deleted {count} prompts from server {server_id}")
            return count
        except Exception as e:
            logger.error(f"Failed to delete prompts for server {server_id}: {e}")
            return 0

    # =========================================================================
    # Skill Classification Methods (Hierarchical Search Support)
    # =========================================================================

    async def update_prompt_skills(
        self,
        prompt_id: int,
        skill_ids: List[str],
        primary_skill_id: Optional[str] = None
    ) -> bool:
        """
        Update skill classification for a prompt.

        Args:
            prompt_id: Prompt ID
            skill_ids: List of assigned skill IDs
            primary_skill_id: Primary skill assignment

        Returns:
            True if successful
        """
        try:
            sql = f"""
                UPDATE {self.schema}.{self.table}
                SET
                    skill_ids = $1,
                    primary_skill_id = $2,
                    is_classified = $3
                WHERE id = $4
            """
            async with self.db:
                await self.db.execute(sql, params=[
                    skill_ids,
                    primary_skill_id or (skill_ids[0] if skill_ids else None),
                    len(skill_ids) > 0,
                    prompt_id
                ])
            return True
        except Exception as e:
            logger.error(f"Failed to update prompt skills for {prompt_id}: {e}")
            return False

    async def get_prompts_by_skill(
        self,
        skill_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get prompts belonging to a skill category.

        Args:
            skill_id: Skill category ID
            limit: Maximum results

        Returns:
            List of prompts in the skill category
        """
        try:
            sql = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE $1 = ANY(skill_ids) AND is_active = TRUE
                ORDER BY
                    CASE WHEN primary_skill_id = $1 THEN 0 ELSE 1 END,
                    name
                LIMIT {limit}
            """
            async with self.db:
                results = await self.db.query(sql, params=[skill_id])
            return results or []
        except Exception as e:
            logger.error(f"Failed to get prompts by skill {skill_id}: {e}")
            return []

    async def get_unclassified_prompts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get prompts that haven't been classified into skill categories.

        Args:
            limit: Maximum results

        Returns:
            List of unclassified prompts
        """
        try:
            sql = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE is_classified = FALSE AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT {limit}
            """
            async with self.db:
                results = await self.db.query(sql, params=[])
            return results or []
        except Exception as e:
            logger.error(f"Failed to get unclassified prompts: {e}")
            return []
