"""
Tool Service - Business logic layer for MCP tool management
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, Any, Optional, List

if TYPE_CHECKING:
    from .tool_repository import ToolRepository

logger = logging.getLogger(__name__)


class ToolService:
    """Tool service - business logic layer"""

    def __init__(self, repository: Optional[ToolRepository] = None):
        """
        Initialize tool service

        Args:
            repository: ToolRepository instance (optional, will create if not provided)
        """
        if repository is None:
            from .tool_repository import ToolRepository

            repository = ToolRepository()
        self.repository = repository

    async def register_tool(self, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new tool

        Args:
            tool_data: Tool information including name, description, category, input_schema

        Returns:
            Created tool data with id

        Raises:
            ValueError: If tool data is invalid or tool already exists
        """
        # Validate required fields
        if not tool_data.get("name"):
            raise ValueError("Tool name is required")

        # Check if tool already exists
        existing = await self.repository.get_tool_by_name(tool_data["name"])
        if existing:
            raise ValueError(f"Tool '{tool_data['name']}' already exists")

        # Create tool
        tool = await self.repository.create_tool(tool_data)
        if not tool:
            raise RuntimeError("Failed to create tool")

        logger.info(f"Registered new tool: {tool['name']}")
        return tool

    async def get_tool(self, tool_identifier: Any) -> Optional[Dict[str, Any]]:
        """
        Get tool by ID or name

        Args:
            tool_identifier: Tool ID (int) or name (str)

        Returns:
            Tool data or None if not found
        """
        if isinstance(tool_identifier, int):
            return await self.repository.get_tool_by_id(tool_identifier)
        elif isinstance(tool_identifier, str):
            return await self.repository.get_tool_by_name(tool_identifier)
        else:
            raise ValueError("Tool identifier must be int (ID) or str (name)")

    async def list_tools(
        self,
        category: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List tools with optional filters

        Args:
            category: Filter by category
            active_only: Only return active tools
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of tool data
        """
        return await self.repository.list_tools(
            category=category,
            is_active=active_only if active_only else None,
            limit=limit,
            offset=offset,
        )

    async def get_default_tools(self) -> List[Dict[str, Any]]:
        """
        Get default tools (meta-tools always available in agent context).

        Returns tools marked with is_default=True, typically:
        - discover, get_tool_schema, execute (gateway tools)
        - list_skills, list_prompts, get_prompt, list_resources, read_resource

        Returns:
            List of default tool data
        """
        return await self.repository.get_default_tools()

    async def update_tool(self, tool_identifier: Any, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update tool information

        Args:
            tool_identifier: Tool ID or name
            updates: Fields to update

        Returns:
            Updated tool data

        Raises:
            ValueError: If tool not found or updates are invalid
        """
        # Get tool ID
        tool = await self.get_tool(tool_identifier)
        if not tool:
            raise ValueError(f"Tool not found: {tool_identifier}")

        tool_id = tool["id"]

        # Validate updates
        if "name" in updates and updates["name"] != tool["name"]:
            # Check if new name already exists
            existing = await self.repository.get_tool_by_name(updates["name"])
            if existing:
                raise ValueError(f"Tool name '{updates['name']}' already exists")

        # Perform update
        success = await self.repository.update_tool(tool_id, updates)
        if not success:
            raise RuntimeError("Failed to update tool")

        # Return updated tool
        updated_tool = await self.repository.get_tool_by_id(tool_id)
        logger.debug(f"Updated tool: {tool['name']}")
        return updated_tool

    async def delete_tool(self, tool_identifier: Any) -> bool:
        """
        Delete tool (soft delete)

        Args:
            tool_identifier: Tool ID or name

        Returns:
            True if successful

        Raises:
            ValueError: If tool not found
        """
        tool = await self.get_tool(tool_identifier)
        if not tool:
            raise ValueError(f"Tool not found: {tool_identifier}")

        success = await self.repository.delete_tool(tool["id"])
        if success:
            logger.info(f"Deleted tool: {tool['name']}")
        return success

    async def deprecate_tool(
        self, tool_identifier: Any, message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark tool as deprecated

        Args:
            tool_identifier: Tool ID or name
            message: Deprecation message

        Returns:
            Updated tool data
        """
        updates = {
            "is_deprecated": True,
            "deprecation_message": message or "This tool has been deprecated",
        }
        return await self.update_tool(tool_identifier, updates)

    async def record_tool_call(
        self, tool_identifier: Any, success: bool, response_time_ms: int
    ) -> bool:
        """
        Record tool call statistics

        Args:
            tool_identifier: Tool ID or name
            success: Whether the call was successful
            response_time_ms: Response time in milliseconds

        Returns:
            True if successful
        """
        tool = await self.get_tool(tool_identifier)
        if not tool:
            logger.warning(f"Cannot record call for unknown tool: {tool_identifier}")
            return False

        return await self.repository.increment_call_count(tool["id"], success, response_time_ms)

    async def get_tool_statistics(self, tool_identifier: Any) -> Optional[Dict[str, Any]]:
        """
        Get tool usage statistics

        Args:
            tool_identifier: Tool ID or name

        Returns:
            Statistics data including call count, success rate, etc.
        """
        tool = await self.get_tool(tool_identifier)
        if not tool:
            return None

        return await self.repository.get_tool_statistics(tool["id"])

    async def search_tools(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search tools by name or description

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching tools
        """
        return await self.repository.search_tools(query, limit)

    async def get_popular_tools(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most popular tools by call count

        Args:
            limit: Maximum number of results

        Returns:
            List of popular tools
        """
        all_tools = await self.repository.list_tools(is_active=True, limit=1000)
        # Sort by call count
        sorted_tools = sorted(all_tools, key=lambda t: t.get("call_count", 0), reverse=True)
        return sorted_tools[:limit]
