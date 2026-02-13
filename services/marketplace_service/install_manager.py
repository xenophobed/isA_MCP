"""
Install Manager - Handles package installation with aggregator integration.

Coordinates:
- MCP server configuration preparation
- Aggregator service registration
- Tool discovery and skill classification
- Installation record management
- Integration with existing tool infrastructure (mcp.tools)
"""

import re
from typing import Any, Dict, List, Optional
import logging

from tests.contracts.marketplace import InstallStatus, InstallResult

logger = logging.getLogger(__name__)


class InstallManager:
    """
    Manages package installation workflow.

    Integrates with:
    - AggregatorService for MCP server management
    - SkillService for tool classification
    - PackageRepository for installation records
    - ToolRepository for unified tool storage (mcp.tools)
    - VectorRepository for semantic search embeddings
    """

    def __init__(
        self,
        repository,
        aggregator=None,
        skill_service=None,
        tool_repository=None,
        vector_repository=None,
    ):
        """
        Initialize InstallManager.

        Args:
            repository: PackageRepository for database operations
            aggregator: AggregatorService for MCP server management
            skill_service: SkillService for tool classification
            tool_repository: ToolRepository for unified tool storage
            vector_repository: VectorRepository for embedding storage
        """
        self._repo = repository
        self._aggregator = aggregator
        self._skill_service = skill_service
        self._tool_repo = tool_repository
        self._vector_repo = vector_repository

    async def install(
        self,
        package: Dict[str, Any],
        version: Dict[str, Any],
        user_config: Dict[str, Any],
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        auto_connect: bool = True,
    ) -> InstallResult:
        """
        Install a package.

        Args:
            package: Package record
            version: Version record
            user_config: User-provided configuration (API keys, etc.)
            user_id: User ID for personal installation
            org_id: Organization ID for enterprise installation
            auto_connect: Whether to connect immediately

        Returns:
            Installation result
        """
        logger.info(f"Installing {package['name']}@{version['version']}")

        try:
            # Step 1: Prepare MCP configuration
            mcp_config = await self.prepare_config(
                version.get("mcp_config", {}),
                user_config,
            )

            # Step 2: Register with aggregator
            server_id = None
            if self._aggregator:
                server_config = {
                    "name": self._get_server_name(package["name"]),
                    "description": package.get("description", ""),
                    "transport_type": mcp_config.get("transport", "stdio"),
                    "connection_config": mcp_config,
                    "auto_connect": auto_connect,
                }

                try:
                    server = await self._aggregator.register_server(server_config)
                    server_id = server["id"]
                    logger.info(f"Registered server: {server['name']} ({server_id})")
                except Exception as e:
                    logger.error(f"Failed to register server: {e}")
                    # Continue without aggregator - can be connected later

            # Step 3: Create installation record
            installation = await self._repo.create_installation(
                package_id=package["id"],
                version_id=version["id"],
                server_id=server_id,
                user_id=user_id,
                org_id=org_id,
                install_config=user_config,
            )

            # Step 4: Discover, classify, and sync tools
            tools_discovered = 0
            skills_assigned = []

            if server_id and self._aggregator:
                try:
                    # Discover tools from the connected server
                    tools = await self._aggregator.discover_tools(server_id)
                    tools_discovered = len(tools)

                    # Step 4a: Create tools in unified mcp.tools table
                    # This ensures marketplace tools are searchable via hierarchical search
                    tool_ids = await self._sync_tools_to_unified_table(
                        tools=tools,
                        server_id=server_id,
                        package_name=package["name"],
                    )

                    # Update tools with their IDs for mapping
                    for i, tool in enumerate(tools):
                        if i < len(tool_ids) and tool_ids[i]:
                            tool["id"] = tool_ids[i]

                    # Step 4b: Create marketplace-specific tool mappings
                    await self._repo.create_tool_mappings(
                        installed_package_id=installation["id"],
                        tools=tools,
                        package_name=package["name"],
                    )

                    # Step 4c: Create vector embeddings for semantic search
                    await self._sync_tool_embeddings(tools)

                    # Collect assigned skills
                    skill_ids = set()
                    for tool in tools:
                        if tool.get("skill_ids"):
                            skill_ids.update(tool["skill_ids"])
                    skills_assigned = list(skill_ids)

                    logger.info(
                        f"Discovered {tools_discovered} tools, "
                        f"synced to unified table, "
                        f"assigned to {len(skills_assigned)} skills"
                    )

                except Exception as e:
                    logger.warning(f"Tool discovery failed: {e}")
                    # Installation still succeeds, tools can be discovered later

            return InstallResult(
                success=True,
                package_id=package["id"],
                package_name=package["name"],
                version=version["version"],
                server_id=server_id,
                tools_discovered=tools_discovered,
                skills_assigned=skills_assigned,
            )

        except Exception as e:
            logger.error(f"Installation failed: {e}")
            return InstallResult(
                success=False,
                package_id=package.get("id", ""),
                package_name=package["name"],
                version=version.get("version", ""),
                error=str(e),
            )

    async def uninstall(self, installation: Dict[str, Any]) -> bool:
        """
        Uninstall a package.

        Cleans up:
        - Aggregator server registration
        - Marketplace tool mappings
        - Unified tools table (mcp.tools)
        - Vector embeddings

        Args:
            installation: Installation record

        Returns:
            True if uninstalled successfully
        """
        installation_id = installation["id"]
        server_id = installation.get("server_id")

        logger.info(f"Uninstalling package: {installation.get('package_name', installation_id)}")

        # Update status
        await self._repo.update_installation_status(
            installation_id,
            InstallStatus.UNINSTALLING,
        )

        try:
            # Step 1: Delete tools from unified mcp.tools table
            if server_id and self._tool_repo:
                try:
                    deleted_count = await self._tool_repo.delete_tools_by_server(server_id)
                    logger.info(f"Deleted {deleted_count} tools from unified table")
                except Exception as e:
                    logger.warning(f"Failed to delete unified tools: {e}")

            # Step 2: Remove from aggregator
            if server_id and self._aggregator:
                try:
                    await self._aggregator.remove_server(server_id)
                    logger.info(f"Removed server: {server_id}")
                except Exception as e:
                    logger.warning(f"Failed to remove server: {e}")

            # Step 3: Delete marketplace tool mappings
            await self._repo.delete_tool_mappings(installation_id)

            # Step 4: Delete installation record
            await self._repo.delete_installation(installation_id)

            logger.info("Uninstallation complete")
            return True

        except Exception as e:
            logger.error(f"Uninstallation failed: {e}")
            await self._repo.update_installation_status(
                installation_id,
                InstallStatus.ERROR,
                error_message=str(e),
            )
            raise

    async def prepare_config(
        self,
        mcp_config: Dict[str, Any],
        user_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Prepare MCP configuration with user values.

        Resolves placeholders like {{API_KEY}} with user-provided values.

        Args:
            mcp_config: Base MCP configuration from package
            user_config: User-provided configuration values

        Returns:
            Prepared configuration
        """
        config = dict(mcp_config)

        # Resolve environment variable placeholders
        if "env" in config:
            resolved_env = {}
            placeholder_pattern = re.compile(r"\{\{(\w+)\}\}")

            for key, value in config["env"].items():
                if isinstance(value, str):
                    matches = placeholder_pattern.findall(value)
                    resolved_value = value

                    for match in matches:
                        if match in user_config:
                            resolved_value = resolved_value.replace(
                                f"{{{{{match}}}}}", user_config[match]
                            )

                    resolved_env[key] = resolved_value
                else:
                    resolved_env[key] = value

            config["env"] = resolved_env

        # Add any extra user config
        for key, value in user_config.items():
            if key not in ("env",) and key not in config:
                if "env" not in config:
                    config["env"] = {}
                config["env"][key] = value

        return config

    def _get_server_name(self, package_name: str) -> str:
        """Convert package name to valid server name."""
        # "@pencil/ui-design" -> "pencil-ui-design"
        name = package_name.lstrip("@").replace("/", "-").replace("_", "-")
        return name.lower()

    async def reconnect(self, installation: Dict[str, Any]) -> bool:
        """
        Reconnect a disconnected package.

        Args:
            installation: Installation record

        Returns:
            True if reconnected successfully
        """
        server_id = installation.get("server_id")
        if not server_id or not self._aggregator:
            return False

        try:
            await self._aggregator.connect_server(server_id)
            await self._repo.update_installation_status(
                installation["id"],
                InstallStatus.INSTALLED,
            )
            return True
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            await self._repo.update_installation_status(
                installation["id"],
                InstallStatus.ERROR,
                error_message=str(e),
            )
            return False

    async def refresh_tools(self, installation: Dict[str, Any]) -> int:
        """
        Refresh tool discovery for an installation.

        Returns:
            Number of tools discovered
        """
        server_id = installation.get("server_id")
        if not server_id or not self._aggregator:
            return 0

        try:
            # Re-discover tools
            tools = await self._aggregator.discover_tools(server_id)

            # Sync to unified table
            tool_ids = await self._sync_tools_to_unified_table(
                tools=tools,
                server_id=server_id,
                package_name=installation.get("package_name", "unknown"),
            )

            # Update tools with their IDs
            for i, tool in enumerate(tools):
                if i < len(tool_ids) and tool_ids[i]:
                    tool["id"] = tool_ids[i]

            # Update mappings
            await self._repo.delete_tool_mappings(installation["id"])
            await self._repo.create_tool_mappings(
                installed_package_id=installation["id"],
                tools=tools,
                package_name=installation.get("package_name", "unknown"),
            )

            # Sync embeddings
            await self._sync_tool_embeddings(tools)

            return len(tools)

        except Exception as e:
            logger.error(f"Tool refresh failed: {e}")
            return 0

    # =========================================================================
    # Unified Tool Infrastructure Integration
    # =========================================================================

    async def _sync_tools_to_unified_table(
        self,
        tools: List[Dict[str, Any]],
        server_id: str,
        package_name: str,
    ) -> List[Optional[int]]:
        """
        Sync discovered tools to the unified mcp.tools table.

        This ensures marketplace tools are:
        - Searchable via hierarchical skills search
        - Visible in tool listings
        - Properly classified by SkillService

        Args:
            tools: List of discovered tools from aggregator
            server_id: Aggregator server ID
            package_name: Package name for namespacing

        Returns:
            List of tool IDs (None for failed upserts)
        """
        if not self._tool_repo:
            logger.warning("ToolRepository not available, skipping unified sync")
            return [None] * len(tools)

        tool_ids = []
        server_name = self._get_server_name(package_name)

        for tool in tools:
            try:
                # Create namespaced name: "pencil-ui-design.create_component"
                original_name = tool.get("name", "")
                namespaced_name = f"{server_name}.{original_name}"

                # Upsert to mcp.tools with is_external=True
                tool_id = await self._tool_repo.upsert_external_tool(
                    name=namespaced_name,
                    description=tool.get("description", ""),
                    input_schema=tool.get("input_schema", {}),
                    source_server_id=server_id,
                    original_name=original_name,
                )

                tool_ids.append(tool_id)

                # Classify tool if SkillService available
                if tool_id and self._skill_service:
                    try:
                        await self._skill_service.classify_tool(tool_id)
                    except Exception as e:
                        logger.debug(f"Tool classification deferred: {e}")

            except Exception as e:
                logger.error(f"Failed to sync tool {tool.get('name')}: {e}")
                tool_ids.append(None)

        logger.debug(f"Synced {len([t for t in tool_ids if t])} tools to unified table")
        return tool_ids

    async def _sync_tool_embeddings(self, tools: List[Dict[str, Any]]) -> None:
        """
        Create vector embeddings for tools to enable semantic search.

        Args:
            tools: List of tools with IDs
        """
        if not self._vector_repo:
            logger.debug("VectorRepository not available, skipping embeddings")
            return

        try:
            # Prepare tool data for embedding
            tool_data = []
            for tool in tools:
                if tool.get("id"):
                    tool_data.append(
                        {
                            "id": tool["id"],
                            "name": tool.get("name", ""),
                            "description": tool.get("description", ""),
                        }
                    )

            if not tool_data:
                return

            # Use VectorRepository's batch upsert for efficiency
            await self._vector_repo.batch_upsert_tools(tool_data)
            logger.debug(f"Created embeddings for {len(tool_data)} tools")

        except Exception as e:
            logger.warning(f"Failed to create tool embeddings: {e}")
