"""
Tool Aggregator - Discovery and indexing of tools from external MCP servers.

Handles tool discovery, namespacing, embedding generation, and skill classification.
"""

from typing import Any, Dict, List, Optional
import logging

from tests.contracts.aggregator.data_contract import (
    ServerStatus,
)

logger = logging.getLogger(__name__)


class ToolAggregator:
    """
    Discovers and aggregates tools from external MCP servers.

    Responsibilities:
    - Discover tools from connected servers
    - Apply namespacing to avoid collisions
    - Index tools in PostgreSQL and Qdrant
    - Queue tools for skill classification
    """

    def __init__(
        self,
        session_manager=None,
        server_registry=None,
        tool_repository=None,
        vector_repository=None,
        skill_classifier=None,
        model_client=None,
    ):
        """
        Initialize ToolAggregator.

        Args:
            session_manager: SessionManager for MCP communication
            server_registry: ServerRegistry for server lookups
            tool_repository: Repository for tool storage
            vector_repository: Repository for vector indexing
            skill_classifier: SkillClassifier for tool classification
            model_client: Model client for embeddings
        """
        self._session_manager = session_manager
        self._server_registry = server_registry
        self._tool_repo = tool_repository
        self._vector_repo = vector_repository
        self._skill_classifier = skill_classifier
        self._model_client = model_client
        self._classification_batch_size = 10
        self._classification_concurrency = 5

    async def discover_tools(self, server_id: str) -> List[Dict[str, Any]]:
        """
        Discover and index all tools from an external server.

        Args:
            server_id: Server UUID to discover from

        Returns:
            List of discovered and indexed tools
        """
        # Get server info
        server = await self._server_registry.get(server_id)
        if not server:
            raise ValueError(f"Server not found: {server_id}")

        # Get session
        session = await self._session_manager.get_session(server_id)
        if not session:
            raise RuntimeError(f"No active session for server: {server_id}")

        logger.info(f"Discovering tools from server: {server['name']}")

        # Call tools/list on external server
        try:
            result = await session.list_tools()
            # ListToolsResult is a Pydantic model, access .tools attribute
            external_tools = result.tools if hasattr(result, "tools") else result.get("tools", [])
        except Exception as e:
            logger.error(f"Failed to discover tools from {server['name']}: {e}")
            raise

        logger.info(f"Found {len(external_tools)} tools from {server['name']}")

        # Process each tool
        aggregated_tools = []
        for ext_tool in external_tools:
            try:
                # Convert Tool Pydantic model to dict if needed
                tool_data = (
                    ext_tool
                    if isinstance(ext_tool, dict)
                    else {
                        "name": ext_tool.name,
                        "description": ext_tool.description or "",
                        "inputSchema": (
                            ext_tool.inputSchema if hasattr(ext_tool, "inputSchema") else {}
                        ),
                    }
                )
                tool = await self._aggregate_tool(server, tool_data)
                aggregated_tools.append(tool)
            except Exception as e:
                tool_name = (
                    ext_tool.get("name")
                    if isinstance(ext_tool, dict)
                    else getattr(ext_tool, "name", "unknown")
                )
                logger.error(f"Failed to aggregate tool {tool_name}: {e}")
                continue

        # Update server tool count
        if self._server_registry:
            await self._server_registry.update_tool_count(server_id, len(aggregated_tools))

        # Batch classify all discovered tools (same pattern as sync_service)
        if aggregated_tools and self._skill_classifier:
            await self._batch_classify_tools(aggregated_tools)

        logger.info(f"Aggregated {len(aggregated_tools)} tools from {server['name']}")
        return aggregated_tools

    async def _aggregate_tool(
        self, server: Dict[str, Any], tool_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single tool from external server.

        Applies namespacing, stores in DB, generates embedding, and queues classification.
        """
        original_name = tool_data["name"]
        namespaced_name = self.namespace_tool(original_name, server["name"])

        description = tool_data.get("description", "")
        input_schema = tool_data.get("inputSchema", {})

        # Propagate org_id from server to tool (org-scoped servers → org-scoped tools)
        server_org_id = server.get("org_id")
        is_global = server.get("is_global", True)

        # Store in PostgreSQL (if repo available)
        tool_id = None
        if self._tool_repo:
            tool_id = await self._tool_repo.create_external_tool(
                name=namespaced_name,
                description=description,
                input_schema=input_schema,
                source_server_id=server["id"],
                original_name=original_name,
                org_id=server_org_id,
                is_global=is_global,
            )
        else:
            # No storage - use hash as pseudo-ID for in-memory operation
            tool_id = hash(namespaced_name) % 1_000_000

        # Generate embedding
        embedding_text = f"{namespaced_name}: {description}"
        embedding = await self._generate_embedding(embedding_text)

        # Index in Qdrant
        if self._vector_repo:
            await self._vector_repo.upsert_tool(
                tool_id=tool_id,
                name=namespaced_name,
                description=description,
                embedding=embedding,
                metadata={
                    "source_server_id": str(server["id"]),
                    "source_server_name": server["name"],
                    "original_name": original_name,
                    "is_external": True,
                    "is_classified": False,
                    "org_id": server_org_id,
                    "is_global": is_global,
                },
            )

        # Note: Classification is done in batch after all tools are aggregated
        # See discover_tools() -> _batch_classify_tools()

        return {
            "id": tool_id,
            "name": namespaced_name,
            "original_name": original_name,
            "description": description,
            "input_schema": input_schema,
            "source_server_id": server["id"],
            "source_server_name": server["name"],
            "is_external": True,
            "is_classified": False,
            "org_id": server_org_id,
            "is_global": is_global,
        }

    def namespace_tool(self, tool_name: str, server_name: str) -> str:
        """
        Create namespaced tool name.

        Format: {server_name}.{tool_name}

        Args:
            tool_name: Original tool name from server
            server_name: Registered server name (lowercase)

        Returns:
            Namespaced name
        """
        return f"{server_name}.{tool_name}"

    def parse_namespaced_name(self, namespaced: str) -> tuple:
        """
        Parse namespaced name into server and tool.

        Only first dot separates server from tool name (tool names can contain dots).

        Args:
            namespaced: Full namespaced name

        Returns:
            Tuple of (server_name, original_tool_name)

        Raises:
            ValueError: If not a valid namespaced name
        """
        if "." not in namespaced:
            raise ValueError(f"Not a namespaced name: {namespaced}")

        parts = namespaced.split(".", 1)
        return parts[0], parts[1]

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for tool text."""
        if self._model_client:
            try:
                # Use OpenAI-compatible embeddings API (same as sync_service)
                response = await self._model_client.embeddings.create(
                    input=text, model="text-embedding-3-small"
                )
                return response.data[0].embedding
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}, using mock embedding")
                return [0.1] * 1536

        # Return mock embedding if no model client
        return [0.1] * 1536

    async def _batch_classify_tools(self, tools: List[Dict[str, Any]]) -> None:
        """
        Batch classify tools using skill classifier.

        Same pattern as sync_service.classify_tools_batch() for consistency.

        Args:
            tools: List of aggregated tool dicts with id, name, description
        """
        if not self._skill_classifier:
            logger.warning("No skill classifier available, skipping classification")
            return

        # Prepare batch format (same as sync_service)
        tools_for_batch = [
            {"tool_id": tool["id"], "tool_name": tool["name"], "description": tool["description"]}
            for tool in tools
        ]

        logger.info(f"🏷️  Batch classifying {len(tools_for_batch)} external tools...")

        try:
            # Use the same batch classification as sync_service
            batch_results = await self._skill_classifier.classify_tools_batch(tools_for_batch)

            classified = sum(1 for r in batch_results if r.get("primary_skill_id"))
            logger.info(f"✅ Classified {classified}/{len(tools_for_batch)} external tools")

            # Log individual results
            for result in batch_results:
                if result.get("primary_skill_id"):
                    logger.debug(f"  ✅ {result['tool_name']} -> {result['primary_skill_id']}")

        except Exception as e:
            logger.warning(f"Batch classification failed for external tools: {e}")
            # Tools remain searchable but unclassified

    async def aggregate_tools(self) -> List[Dict[str, Any]]:
        """
        Aggregate tools from all connected servers.

        Returns:
            List of all aggregated tools
        """
        all_tools = []

        # Get all connected servers
        servers = await self._server_registry.list(status=ServerStatus.CONNECTED)

        for server in servers:
            try:
                tools = await self.discover_tools(server["id"])
                all_tools.extend(tools)
            except Exception as e:
                logger.error(f"Failed to aggregate tools from {server['name']}: {e}")
                continue

        return all_tools

    async def search_tools(
        self, query: str, server_filter: List[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search across all aggregated tools.

        Args:
            query: Search query
            server_filter: Optional list of server names to filter
            limit: Maximum results

        Returns:
            List of matching tools with scores
        """
        # Generate query embedding
        query_embedding = await self._generate_embedding(query)

        # Build filter conditions
        filter_conditions = {"must": [{"field": "is_external", "match": {"value": True}}]}

        if server_filter:
            filter_conditions["should"] = [
                {"field": "source_server_name", "match": {"keyword": name}}
                for name in server_filter
            ]

        # Search in Qdrant
        if self._vector_repo:
            results = await self._vector_repo.search(
                query_vector=query_embedding, filter_conditions=filter_conditions, limit=limit
            )
            return results

        return []

    async def get_tool(self, namespaced_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a tool by its namespaced name.

        Args:
            namespaced_name: Full namespaced tool name

        Returns:
            Tool data or None if not found
        """
        if self._tool_repo:
            return await self._tool_repo.get_tool_by_name(namespaced_name)
        return None

    async def remove_server_tools(self, server_id: str) -> int:
        """
        Remove all tools from a server.

        Args:
            server_id: Server UUID

        Returns:
            Number of tools removed
        """
        if not self._tool_repo:
            return 0

        # Get tool IDs for Qdrant cleanup
        tool_ids = await self._tool_repo.get_tool_ids_by_server(server_id)

        # Remove from Qdrant
        if self._vector_repo:
            for tool_id in tool_ids:
                await self._vector_repo.delete_tool(tool_id)

        # Remove from PostgreSQL
        count = await self._tool_repo.delete_tools_by_server(server_id)

        logger.info(f"Removed {count} tools from server {server_id}")
        return count
