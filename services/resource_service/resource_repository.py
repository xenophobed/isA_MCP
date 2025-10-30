"""
Resource Repository - Data access layer for MCP resources
Handles database operations for resource registry
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from isa_common.postgres_client import PostgresClient

logger = logging.getLogger(__name__)


class ResourceRepository:
    """Resource repository - data access layer"""

    def __init__(self, host='isa-postgres-grpc', port=50061):
        """Initialize resource repository"""
        self.db = PostgresClient(host=host, port=port, user_id='mcp-resource-service')
        self.schema = "mcp"
        self.table = "resources"

    async def get_resource_by_id(self, resource_id: int) -> Optional[Dict[str, Any]]:
        """Get resource by ID"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE id = $1",
                    [resource_id],
                    schema=self.schema
                )
                return result
        except Exception as e:
            logger.error(f"Failed to get resource by ID {resource_id}: {e}")
            return None

    async def get_resource_by_uri(self, uri: str) -> Optional[Dict[str, Any]]:
        """Get resource by URI"""
        try:
            with self.db:
                result = self.db.query_row(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE uri = $1",
                    [uri],
                    schema=self.schema
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
            with self.db:
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

                results = self.db.query(sql, params, schema=self.schema)
                return results or []
        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            return []

    async def create_resource(self, resource_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new resource"""
        try:
            with self.db:
                record = {
                    'uri': resource_data['uri'],
                    'name': resource_data['name'],
                    'description': resource_data.get('description'),
                    'resource_type': resource_data.get('resource_type'),
                    'mime_type': resource_data.get('mime_type'),
                    'size_bytes': resource_data.get('size_bytes', 0),
                    'metadata': resource_data.get('metadata', {}),
                    'tags': resource_data.get('tags', []),
                    'is_public': resource_data.get('is_public', False),
                    'owner_id': resource_data.get('owner_id'),
                    'allowed_users': resource_data.get('allowed_users', []),
                    'is_active': resource_data.get('is_active', True)
                }

                count = self.db.insert_into(self.table, [record], schema=self.schema)

                if count and count > 0:
                    return await self.get_resource_by_uri(resource_data['uri'])
                return None
        except Exception as e:
            logger.error(f"Failed to create resource: {e}")
            return None

    async def update_resource(self, resource_id: int, updates: Dict[str, Any]) -> bool:
        """Update resource"""
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

                params.append(resource_id)

                sql = f"""
                    UPDATE {self.schema}.{self.table}
                    SET {', '.join(set_parts)}
                    WHERE id = ${param_idx}
                """

                self.db.execute(sql, params, schema=self.schema)
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
            with self.db:
                sql = f"""
                    UPDATE {self.schema}.{self.table}
                    SET
                        access_count = access_count + 1,
                        last_accessed_at = NOW()
                    WHERE id = $1
                """

                self.db.execute(sql, [resource_id], schema=self.schema)
                return True
        except Exception as e:
            logger.error(f"Failed to increment access count for resource {resource_id}: {e}")
            return False

    async def check_user_access(self, uri: str, user_id: str) -> bool:
        """Check if user has access to resource"""
        try:
            with self.db:
                sql = f"SELECT {self.schema}.user_has_resource_access($1, $2) as has_access"
                result = self.db.query_row(sql, [uri, user_id], schema=self.schema)
                return result.get('has_access', False) if result else False
        except Exception as e:
            logger.error(f"Failed to check user access: {e}")
            return False

    async def grant_access(self, resource_id: int, user_id: str) -> bool:
        """Grant user access to resource"""
        try:
            with self.db:
                sql = f"""
                    UPDATE {self.schema}.{self.table}
                    SET allowed_users = array_append(allowed_users, $1)
                    WHERE id = $2 AND NOT ($1 = ANY(allowed_users))
                """
                self.db.execute(sql, [user_id, resource_id], schema=self.schema)
                return True
        except Exception as e:
            logger.error(f"Failed to grant access: {e}")
            return False

    async def revoke_access(self, resource_id: int, user_id: str) -> bool:
        """Revoke user access to resource"""
        try:
            with self.db:
                sql = f"""
                    UPDATE {self.schema}.{self.table}
                    SET allowed_users = array_remove(allowed_users, $1)
                    WHERE id = $2
                """
                self.db.execute(sql, [user_id, resource_id], schema=self.schema)
                return True
        except Exception as e:
            logger.error(f"Failed to revoke access: {e}")
            return False

    async def search_resources(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search resources by URI, name, or description"""
        try:
            with self.db:
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
                results = self.db.query(sql, [query_pattern], schema=self.schema)
                return results or []
        except Exception as e:
            logger.error(f"Failed to search resources: {e}")
            return []
