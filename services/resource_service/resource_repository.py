"""
Resource Repository - Data access layer for MCP resources
Handles database operations for resource registry
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from isa_common import AsyncPostgresClient
from core.config import get_settings

logger = logging.getLogger(__name__)


class ResourceRepository:
    """Resource repository - data access layer"""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Initialize resource repository

        Args:
            host: PostgreSQL gRPC server host (defaults to config)
            port: PostgreSQL gRPC server port (defaults to config)
        """
        settings = get_settings()
        host = host or settings.infrastructure.postgres_grpc_host
        port = port or settings.infrastructure.postgres_grpc_port

        self.db = AsyncPostgresClient(host=host, port=port, user_id='mcp-resource-service')
        self.schema = "mcp"
        self.table = "resources"

    async def get_resource_by_id(self, resource_id: int) -> Optional[Dict[str, Any]]:
        """Get resource by ID"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE id = $1",
                    params=[resource_id]
                )
            return result
        except Exception as e:
            logger.error(f"Failed to get resource by ID {resource_id}: {e}")
            return None

    async def get_resource_by_uri(self, uri: str) -> Optional[Dict[str, Any]]:
        """Get resource by URI"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE uri = $1",
                    params=[uri]
                )
            return result
        except Exception as e:
            logger.error(f"Failed to get resource by URI {uri}: {e}")
            return None

    async def list_resources(
        self,
        resource_type: Optional[str] = None,
        is_active: Optional[bool] = True,
        is_public: Optional[bool] = None,
        owner_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List resources with filters"""
        try:
            where_clauses = []
            params = []
            param_idx = 1

            if resource_type is not None:
                where_clauses.append(f"resource_type = ${param_idx}")
                params.append(resource_type)
                param_idx += 1

            if is_active is not None:
                where_clauses.append(f"is_active = ${param_idx}")
                params.append(is_active)
                param_idx += 1

            if is_public is not None:
                where_clauses.append(f"is_public = ${param_idx}")
                params.append(is_public)
                param_idx += 1

            if owner_id is not None:
                where_clauses.append(f"owner_id = ${param_idx}")
                params.append(owner_id)
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
            logger.error(f"Failed to list resources: {e}")
            return []

    async def create_resource(self, resource_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new resource (internal or external)"""
        try:
            # Serialize metadata dict to JSON string for PostgreSQL jsonb
            metadata = resource_data.get('metadata', {})
            metadata_json = json.dumps(metadata) if isinstance(metadata, dict) else metadata

            # Handle skill_ids - ensure it's a list
            skill_ids = resource_data.get('skill_ids', [])
            if not isinstance(skill_ids, list):
                skill_ids = []

            record = {
                'uri': resource_data['uri'],
                'name': resource_data['name'],
                'description': resource_data.get('description'),
                'resource_type': resource_data.get('resource_type'),
                'mime_type': resource_data.get('mime_type'),
                'size_bytes': resource_data.get('size_bytes', 0),
                'metadata': metadata_json,
                'tags': resource_data.get('tags', []),
                'is_public': resource_data.get('is_public', False),
                'owner_id': resource_data.get('owner_id'),
                'allowed_users': resource_data.get('allowed_users', []),
                'is_active': resource_data.get('is_active', True),
                # External resource fields
                'source_server_id': resource_data.get('source_server_id'),
                'original_name': resource_data.get('original_name'),
                'original_uri': resource_data.get('original_uri'),
                'is_external': resource_data.get('is_external', False),
                # Skill classification fields (hierarchical search)
                'skill_ids': skill_ids,
                'primary_skill_id': resource_data.get('primary_skill_id'),
                'is_classified': resource_data.get('is_classified', False),
            }

            async with self.db:
                count = await self.db.insert_into(self.table, [record], schema=self.schema)

            if count and count > 0:
                return await self.get_resource_by_uri(resource_data['uri'])
            return None
        except Exception as e:
            logger.error(f"Failed to create resource: {e}")
            return None

    async def create_external_resource(
        self,
        uri: str,
        name: str,
        description: str,
        source_server_id: str,
        original_name: str,
        original_uri: str,
        mime_type: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> Optional[int]:
        """
        Create an external resource from an MCP server.

        Args:
            uri: Namespaced URI (server://resource_uri)
            name: Namespaced resource name (server.resource_name)
            description: Resource description
            source_server_id: UUID of the source external server
            original_name: Original resource name before namespacing
            original_uri: Original URI from the external server
            mime_type: Resource MIME type
            resource_type: Resource type

        Returns:
            Resource ID if created, None on failure
        """
        resource_data = {
            'uri': uri,
            'name': name,
            'description': description,
            'source_server_id': source_server_id,
            'original_name': original_name,
            'original_uri': original_uri,
            'mime_type': mime_type,
            'resource_type': resource_type,
            'is_external': True,
            'is_active': True,
            'is_public': True,  # External resources are typically public
        }
        result = await self.create_resource(resource_data)
        return result.get('id') if result else None

    async def update_resource(self, resource_id: int, updates: Dict[str, Any]) -> bool:
        """Update resource"""
        try:
            set_parts = []
            params = []
            param_idx = 1

            for key, value in updates.items():
                if key not in ['id', 'created_at', 'updated_at']:
                    # Serialize dict/list to JSON for jsonb columns
                    if key == 'metadata' and isinstance(value, dict):
                        value = json.dumps(value)
                    set_parts.append(f"{key} = ${param_idx}")
                    params.append(value)
                    param_idx += 1

            if not set_parts:
                return False

            params.append(resource_id)

            sql = f"""
                UPDATE {self.schema}.{self.table}
                SET {', '.join(set_parts)}
                WHERE id = ${param_idx}
            """

            async with self.db:
                await self.db.execute(sql, params=params)
            return True
        except Exception as e:
            logger.error(f"Failed to update resource {resource_id}: {e}")
            return False

    async def delete_resource(self, resource_id: int) -> bool:
        """Delete resource (soft delete)"""
        try:
            return await self.update_resource(resource_id, {'is_active': False})
        except Exception as e:
            logger.error(f"Failed to delete resource {resource_id}: {e}")
            return False

    async def increment_access_count(self, resource_id: int) -> bool:
        """Increment resource access statistics"""
        try:
            sql = f"""
                UPDATE {self.schema}.{self.table}
                SET
                    access_count = access_count + 1,
                    last_accessed_at = NOW()
                WHERE id = $1
            """

            async with self.db:
                await self.db.execute(sql, params=[resource_id])
            return True
        except Exception as e:
            logger.error(f"Failed to increment access count for resource {resource_id}: {e}")
            return False

    async def check_user_access(self, uri: str, user_id: str) -> bool:
        """Check if user has access to resource"""
        try:
            sql = f"SELECT {self.schema}.user_has_resource_access($1, $2) as has_access"
            async with self.db:
                result = await self.db.query_row(sql, params=[uri, user_id])
            return result.get('has_access', False) if result else False
        except Exception as e:
            logger.error(f"Failed to check user access: {e}")
            return False

    async def grant_access(self, resource_id: int, user_id: str) -> bool:
        """Grant user access to resource"""
        try:
            sql = f"""
                UPDATE {self.schema}.{self.table}
                SET allowed_users = array_append(allowed_users, $1)
                WHERE id = $2 AND NOT ($1 = ANY(allowed_users))
            """
            async with self.db:
                await self.db.execute(sql, params=[user_id, resource_id])
            return True
        except Exception as e:
            logger.error(f"Failed to grant access: {e}")
            return False

    async def revoke_access(self, resource_id: int, user_id: str) -> bool:
        """Revoke user access to resource"""
        try:
            sql = f"""
                UPDATE {self.schema}.{self.table}
                SET allowed_users = array_remove(allowed_users, $1)
                WHERE id = $2
            """
            async with self.db:
                await self.db.execute(sql, params=[user_id, resource_id])
            return True
        except Exception as e:
            logger.error(f"Failed to revoke access: {e}")
            return False

    async def search_resources(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search resources by URI, name, or description"""
        try:
            sql = f"""
                SELECT * FROM {self.schema}.{self.table}
                WHERE
                    (uri ILIKE $1 OR name ILIKE $1 OR description ILIKE $1)
                    AND is_active = TRUE
                ORDER BY
                    CASE
                        WHEN uri ILIKE $1 THEN 1
                        WHEN name ILIKE $1 THEN 2
                        ELSE 3
                    END,
                    access_count DESC
                LIMIT {limit}
            """

            query_pattern = f"%{query}%"
            async with self.db:
                results = await self.db.query(sql, params=[query_pattern])
            return results or []
        except Exception as e:
            logger.error(f"Failed to search resources: {e}")
            return []

    # =========================================================================
    # External Resource Methods
    # =========================================================================

    async def list_external_resources(
        self,
        server_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List external resources with optional filters.

        Args:
            server_id: Filter by source server UUID
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of external resources
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
            logger.error(f"Failed to list external resources: {e}")
            return []

    async def get_resource_ids_by_server(self, server_id: str) -> List[int]:
        """
        Get all resource IDs from a specific external server.

        Used for cleanup when removing a server.

        Args:
            server_id: External server UUID

        Returns:
            List of resource IDs
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
            logger.error(f"Failed to get resource IDs for server {server_id}: {e}")
            return []

    async def delete_resources_by_server(self, server_id: str) -> int:
        """
        Delete all resources from a specific external server.

        Args:
            server_id: External server UUID

        Returns:
            Number of resources deleted
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

                # Delete the resources
                delete_sql = f"""
                    DELETE FROM {self.schema}.{self.table}
                    WHERE source_server_id = $1
                """
                await self.db.execute(delete_sql, params=[server_id])

            logger.info(f"Deleted {count} resources from server {server_id}")
            return count
        except Exception as e:
            logger.error(f"Failed to delete resources for server {server_id}: {e}")
            return 0

    async def get_resource_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get resource by name"""
        try:
            async with self.db:
                result = await self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE name = $1",
                    params=[name]
                )
            return result
        except Exception as e:
            logger.error(f"Failed to get resource by name {name}: {e}")
            return None

    # =========================================================================
    # Skill Classification Methods (Hierarchical Search Support)
    # =========================================================================

    async def update_resource_skills(
        self,
        resource_id: int,
        skill_ids: List[str],
        primary_skill_id: Optional[str] = None
    ) -> bool:
        """
        Update skill classification for a resource.

        Args:
            resource_id: Resource ID
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
                    resource_id
                ])
            return True
        except Exception as e:
            logger.error(f"Failed to update resource skills for {resource_id}: {e}")
            return False

    async def get_resources_by_skill(
        self,
        skill_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get resources belonging to a skill category.

        Args:
            skill_id: Skill category ID
            limit: Maximum results

        Returns:
            List of resources in the skill category
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
            logger.error(f"Failed to get resources by skill {skill_id}: {e}")
            return []

    async def get_unclassified_resources(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get resources that haven't been classified into skill categories.

        Args:
            limit: Maximum results

        Returns:
            List of unclassified resources
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
            logger.error(f"Failed to get unclassified resources: {e}")
            return []

    async def upsert_resource(self, resource_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Insert or update a resource by URI.

        Args:
            resource_data: Resource data with 'uri' field

        Returns:
            The created/updated resource record
        """
        uri = resource_data.get('uri')
        if not uri:
            logger.error("Cannot upsert resource without URI")
            return None

        existing = await self.get_resource_by_uri(uri)
        if existing:
            # Update existing resource
            await self.update_resource(existing['id'], resource_data)
            return await self.get_resource_by_uri(uri)
        else:
            # Create new resource
            return await self.create_resource(resource_data)
