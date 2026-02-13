"""
Resource Service - Business logic layer for MCP resource management
"""

import logging
from typing import Dict, Any, Optional, List

from .resource_repository import ResourceRepository

logger = logging.getLogger(__name__)


class ResourceService:
    """Resource service - business logic layer"""

    def __init__(self, repository: Optional[ResourceRepository] = None):
        """Initialize resource service"""
        self.repository = repository or ResourceRepository()

    async def register_resource(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new resource"""
        if not resource_data.get("uri"):
            raise ValueError("Resource URI is required")

        if not resource_data.get("name"):
            raise ValueError("Resource name is required")

        existing = await self.repository.get_resource_by_uri(resource_data["uri"])
        if existing:
            raise ValueError(f"Resource '{resource_data['uri']}' already exists")

        resource = await self.repository.create_resource(resource_data)
        if not resource:
            raise RuntimeError("Failed to create resource")

        logger.info(f"Registered new resource: {resource['uri']}")
        return resource

    async def get_resource(self, resource_identifier: Any) -> Optional[Dict[str, Any]]:
        """Get resource by ID or URI"""
        if isinstance(resource_identifier, int):
            return await self.repository.get_resource_by_id(resource_identifier)
        elif isinstance(resource_identifier, str):
            return await self.repository.get_resource_by_uri(resource_identifier)
        else:
            raise ValueError("Resource identifier must be int (ID) or str (URI)")

    async def list_resources(
        self,
        resource_type: Optional[str] = None,
        active_only: bool = True,
        public_only: bool = False,
        owner_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List resources with filters"""
        return await self.repository.list_resources(
            resource_type=resource_type,
            is_active=active_only if active_only else None,
            is_public=public_only if public_only else None,
            owner_id=owner_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    async def update_resource(
        self, resource_identifier: Any, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update resource information"""
        resource = await self.get_resource(resource_identifier)
        if not resource:
            raise ValueError(f"Resource not found: {resource_identifier}")

        resource_id = resource["id"]

        if "uri" in updates and updates["uri"] != resource["uri"]:
            existing = await self.repository.get_resource_by_uri(updates["uri"])
            if existing:
                raise ValueError(f"Resource URI '{updates['uri']}' already exists")

        success = await self.repository.update_resource(resource_id, updates)
        if not success:
            raise RuntimeError("Failed to update resource")

        updated_resource = await self.repository.get_resource_by_id(resource_id)
        logger.debug(f"Updated resource: {resource['uri']}")
        return updated_resource

    async def delete_resource(self, resource_identifier: Any) -> bool:
        """Delete resource (soft delete)"""
        resource = await self.get_resource(resource_identifier)
        if not resource:
            raise ValueError(f"Resource not found: {resource_identifier}")

        success = await self.repository.delete_resource(resource["id"])
        if success:
            logger.info(f"Deleted resource: {resource['uri']}")
        return success

    async def record_resource_access(self, resource_identifier: Any) -> bool:
        """Record resource access"""
        resource = await self.get_resource(resource_identifier)
        if not resource:
            logger.warning(f"Cannot record access for unknown resource: {resource_identifier}")
            return False

        return await self.repository.increment_access_count(resource["id"])

    async def check_access(self, uri: str, user_id: str) -> bool:
        """Check if user has access to resource"""
        return await self.repository.check_user_access(uri, user_id)

    async def grant_access(self, resource_identifier: Any, user_id: str) -> bool:
        """Grant user access to resource"""
        resource = await self.get_resource(resource_identifier)
        if not resource:
            raise ValueError(f"Resource not found: {resource_identifier}")

        success = await self.repository.grant_access(resource["id"], user_id)
        if success:
            logger.info(f"Granted access to user {user_id} for resource {resource['uri']}")
        return success

    async def revoke_access(self, resource_identifier: Any, user_id: str) -> bool:
        """Revoke user access to resource"""
        resource = await self.get_resource(resource_identifier)
        if not resource:
            raise ValueError(f"Resource not found: {resource_identifier}")

        success = await self.repository.revoke_access(resource["id"], user_id)
        if success:
            logger.info(f"Revoked access from user {user_id} for resource {resource['uri']}")
        return success

    async def search_resources(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search resources"""
        return await self.repository.search_resources(query, limit)

    async def get_popular_resources(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular resources"""
        all_resources = await self.repository.list_resources(is_active=True, limit=1000)
        sorted_resources = sorted(
            all_resources, key=lambda r: r.get("access_count", 0), reverse=True
        )
        return sorted_resources[:limit]

    async def get_user_resources(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get resources owned by or accessible to user"""
        # Get owned resources
        owned = await self.repository.list_resources(owner_id=user_id, limit=limit)

        # Get public resources
        public = await self.repository.list_resources(is_public=True, limit=limit)

        # Get resources where user is in allowed_users
        all_resources = await self.repository.list_resources(limit=1000)
        allowed = [r for r in all_resources if user_id in r.get("allowed_users", [])]

        # Combine and deduplicate
        combined = {r["id"]: r for r in (owned + public + allowed)}
        return list(combined.values())[:limit]
