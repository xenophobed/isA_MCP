"""
Mock implementations for Aggregator Service testing.

Provides mock sessions, registries, and external server behavior for component tests.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid
import asyncio

from tests.contracts.aggregator.data_contract import (
    ServerStatus,
)


class MockMCPSession:
    """
    Mock for MCP ClientSession.

    Simulates MCP SDK ClientSession behavior for testing.
    """

    def __init__(self, server_id: str = None, tools: List[Dict] = None):
        self.server_id = server_id or str(uuid.uuid4())
        self._tools = tools or []
        self._connected = False
        self._calls: List[Dict[str, Any]] = []
        self._tool_responses: Dict[str, Any] = {}
        self._should_fail_connect = False
        self._should_fail_tools_list = False
        self._connection_delay = 0.0

    def _record_call(self, method: str, **kwargs):
        """Record a method call."""
        self._calls.append(
            {"method": method, "args": kwargs, "timestamp": datetime.now(timezone.utc)}
        )

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get recorded calls, optionally filtered by method."""
        if method:
            return [c for c in self._calls if c["method"] == method]
        return self._calls

    def set_tools(self, tools: List[Dict]):
        """Set the tools this session will return."""
        self._tools = tools

    def set_tool_response(self, tool_name: str, response: Any):
        """Set the response for a specific tool call."""
        self._tool_responses[tool_name] = response

    def set_should_fail_connect(self, should_fail: bool = True):
        """Configure session to fail on connect."""
        self._should_fail_connect = should_fail

    def set_should_fail_tools_list(self, should_fail: bool = True):
        """Configure session to fail on tools/list."""
        self._should_fail_tools_list = should_fail

    def set_connection_delay(self, delay: float):
        """Set delay for connection (simulates slow servers)."""
        self._connection_delay = delay

    async def connect(self) -> None:
        """Connect to the MCP server."""
        self._record_call("connect")

        if self._connection_delay > 0:
            await asyncio.sleep(self._connection_delay)

        if self._should_fail_connect:
            raise ConnectionError("Mock connection failure")

        self._connected = True

    async def close(self) -> None:
        """Close the session."""
        self._record_call("close")
        self._connected = False

    async def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP session."""
        self._record_call("initialize")
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": f"mock-server-{self.server_id[:8]}", "version": "1.0.0"},
        }

    async def list_tools(self) -> Dict[str, Any]:
        """List available tools."""
        self._record_call("list_tools")

        if self._should_fail_tools_list:
            raise RuntimeError("Mock tools/list failure")

        return {"tools": self._tools}

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the external server."""
        self._record_call("call_tool", name=name, arguments=arguments)

        if not self._connected:
            raise RuntimeError("Session not connected")

        if name in self._tool_responses:
            response = self._tool_responses[name]
            if callable(response):
                return response(arguments)
            return response

        # Default mock response
        return {"content": [{"type": "text", "text": f"Mock result for {name}"}], "isError": False}

    @property
    def is_connected(self) -> bool:
        """Check if session is connected."""
        return self._connected


class MockServerRegistry:
    """
    Mock for ServerRegistry.

    Stores server registrations in memory and tracks method calls.
    """

    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}
        self._calls: List[Dict[str, Any]] = []

    def _record_call(self, method: str, **kwargs):
        """Record a method call."""
        self._calls.append({"method": method, "args": kwargs})

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get recorded calls, optionally filtered by method."""
        if method:
            return [c for c in self._calls if c["method"] == method]
        return self._calls

    def clear(self):
        """Clear all stored data."""
        self.servers = {}
        self._calls = []

    async def add(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Add a server to the registry."""
        self._record_call("add", config=config)

        name = config["name"]

        # Check for duplicate
        for server in self.servers.values():
            if server["name"] == name:
                raise ValueError(f"Server already exists: {name}")

        server_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        server = {
            "id": server_id,
            "name": name,
            "description": config.get("description"),
            "transport_type": config["transport_type"],
            "connection_config": config["connection_config"],
            "health_check_url": config.get("health_check_url"),
            "status": ServerStatus.DISCONNECTED,
            "tool_count": 0,
            "error_message": None,
            "registered_at": now,
            "connected_at": None,
            "last_health_check": None,
        }

        self.servers[server_id] = server
        return server

    async def get(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get a server by ID."""
        self._record_call("get", server_id=server_id)
        return self.servers.get(server_id)

    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a server by name."""
        self._record_call("get_by_name", name=name)
        for server in self.servers.values():
            if server["name"] == name:
                return server
        return None

    async def update(self, server_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Update a server's attributes."""
        self._record_call("update", server_id=server_id, updates=updates)

        if server_id not in self.servers:
            return None

        server = self.servers[server_id]
        for key, value in updates.items():
            if key in server:
                server[key] = value

        return server

    async def remove(self, server_id: str) -> bool:
        """Remove a server from the registry."""
        self._record_call("remove", server_id=server_id)

        if server_id not in self.servers:
            return False

        del self.servers[server_id]
        return True

    async def list(self, status: ServerStatus = None) -> List[Dict[str, Any]]:
        """List all servers with optional status filter."""
        self._record_call("list", status=status)

        results = []
        for server in self.servers.values():
            if status is None or server["status"] == status:
                results.append(server)

        return results

    async def update_status(
        self, server_id: str, status: ServerStatus, error_message: Optional[str] = None
    ) -> bool:
        """Update server connection status."""
        self._record_call(
            "update_status", server_id=server_id, status=status, error_message=error_message
        )

        if server_id not in self.servers:
            return False

        self.servers[server_id]["status"] = status
        self.servers[server_id]["error_message"] = error_message

        if status == ServerStatus.CONNECTED:
            self.servers[server_id]["connected_at"] = datetime.now(timezone.utc)

        return True

    async def update_tool_count(self, server_id: str, count: int) -> bool:
        """Update server tool count."""
        self._record_call("update_tool_count", server_id=server_id, count=count)

        if server_id not in self.servers:
            return False

        self.servers[server_id]["tool_count"] = count
        return True

    async def update_last_health_check(self, server_id: str) -> bool:
        """Update last health check timestamp."""
        self._record_call("update_last_health_check", server_id=server_id)

        if server_id not in self.servers:
            return False

        self.servers[server_id]["last_health_check"] = datetime.now(timezone.utc)
        return True


class MockExternalServer:
    """
    Mock for external MCP server behavior.

    Simulates the behavior of an external MCP server for testing.
    """

    def __init__(self, name: str, tools: List[Dict] = None):
        self.name = name
        self.tools = tools or []
        self._is_healthy = True
        self._health_delay = 0.0
        self._tool_execution_delay = 0.0
        self._should_fail_execution: Dict[str, bool] = {}

    def add_tool(self, name: str, description: str, input_schema: Dict = None):
        """Add a tool to the server."""
        self.tools.append(
            {
                "name": name,
                "description": description,
                "inputSchema": input_schema or {"type": "object", "properties": {}},
            }
        )

    def set_healthy(self, is_healthy: bool):
        """Set server health status."""
        self._is_healthy = is_healthy

    def set_health_delay(self, delay: float):
        """Set delay for health checks."""
        self._health_delay = delay

    def set_tool_execution_delay(self, delay: float):
        """Set delay for tool execution."""
        self._tool_execution_delay = delay

    def set_tool_should_fail(self, tool_name: str, should_fail: bool = True):
        """Configure a tool to fail on execution."""
        self._should_fail_execution[tool_name] = should_fail

    async def health_check(self) -> bool:
        """Perform health check."""
        if self._health_delay > 0:
            await asyncio.sleep(self._health_delay)
        return self._is_healthy

    async def list_tools(self) -> List[Dict]:
        """List available tools."""
        return self.tools

    async def execute_tool(self, name: str, arguments: Dict) -> Dict:
        """Execute a tool."""
        if self._tool_execution_delay > 0:
            await asyncio.sleep(self._tool_execution_delay)

        if self._should_fail_execution.get(name, False):
            return {"content": [{"type": "text", "text": f"Tool {name} failed"}], "isError": True}

        return {
            "content": [{"type": "text", "text": f"Executed {name} with {arguments}"}],
            "isError": False,
        }

    def create_session(self) -> MockMCPSession:
        """Create a mock session for this server."""
        session = MockMCPSession(tools=self.tools)
        return session


class MockSkillClassifier:
    """
    Mock for SkillClassifier.

    Simulates skill classification for external tools.
    """

    def __init__(self):
        self._calls: List[Dict[str, Any]] = []
        self._classification_results: Dict[str, Dict] = {}
        self._default_skill_id = "general_utility"

    def _record_call(self, method: str, **kwargs):
        """Record a method call."""
        self._calls.append({"method": method, "args": kwargs})

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get recorded calls."""
        if method:
            return [c for c in self._calls if c["method"] == method]
        return self._calls

    def set_classification_result(self, tool_name: str, result: Dict):
        """Set classification result for a specific tool."""
        self._classification_results[tool_name] = result

    def set_default_skill(self, skill_id: str):
        """Set the default skill for unclassified tools."""
        self._default_skill_id = skill_id

    async def classify_tools_batch(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch classify tools."""
        self._record_call("classify_tools_batch", tools=tools)
        results = []
        for tool in tools:
            tool_name = tool.get("tool_name", "")
            if tool_name in self._classification_results:
                result = self._classification_results[tool_name]
            else:
                result = {
                    "tool_id": tool.get("tool_id"),
                    "tool_name": tool_name,
                    "assignments": [{"skill_id": self._default_skill_id, "confidence": 0.75}],
                    "primary_skill_id": self._default_skill_id,
                }
            results.append(result)
        return results

    async def classify_tool(
        self, tool_id: int, tool_name: str, tool_description: str, **kwargs
    ) -> Dict[str, Any]:
        """Classify a tool into skill categories."""
        self._record_call(
            "classify_tool", tool_id=tool_id, tool_name=tool_name, tool_description=tool_description
        )

        if tool_name in self._classification_results:
            return self._classification_results[tool_name]

        # Default classification
        return {
            "tool_id": tool_id,
            "tool_name": tool_name,
            "assignments": [
                {
                    "skill_id": self._default_skill_id,
                    "confidence": 0.75,
                    "reasoning": "Mock classification",
                }
            ],
            "primary_skill_id": self._default_skill_id,
            "suggested_new_skill": None,
        }


class MockSessionManager:
    """
    Mock for SessionManager.

    Manages mock MCP sessions for testing.
    """

    def __init__(self, server_registry=None):
        self._sessions: Dict[str, MockMCPSession] = {}
        self._calls: List[Dict[str, Any]] = []
        self._should_fail_connect: Dict[str, bool] = {}
        self._server_registry = server_registry

    def _record_call(self, method: str, **kwargs):
        """Record a method call."""
        self._calls.append({"method": method, "args": kwargs})

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get recorded calls."""
        if method:
            return [c for c in self._calls if c["method"] == method]
        return self._calls

    def set_should_fail_connect(self, server_id: str, should_fail: bool = True):
        """Configure connection to fail for a server."""
        self._should_fail_connect[server_id] = should_fail

    def add_session(self, server_id: str, session: MockMCPSession):
        """Add a pre-configured session."""
        self._sessions[server_id] = session

    async def connect(self, config: Dict[str, Any]) -> MockMCPSession:
        """Connect to an external server and return session."""
        server_id = config.get("id") or str(uuid.uuid4())
        self._record_call("connect", server_id=server_id, config=config)

        # Update status to CONNECTING
        if self._server_registry:
            await self._server_registry.update_status(server_id, ServerStatus.CONNECTING)

        if self._should_fail_connect.get(server_id, False):
            # Update status to ERROR
            if self._server_registry:
                await self._server_registry.update_status(
                    server_id, ServerStatus.ERROR, "Mock connection failure"
                )
            raise ConnectionError(f"Mock connection failure for {server_id}")

        session = MockMCPSession(server_id=server_id)
        await session.connect()
        self._sessions[server_id] = session

        # Update status to CONNECTED
        if self._server_registry:
            await self._server_registry.update_status(server_id, ServerStatus.CONNECTED)

        return session

    async def disconnect(self, server_id: str) -> bool:
        """Disconnect from an external server."""
        self._record_call("disconnect", server_id=server_id)

        if server_id not in self._sessions:
            return False

        session = self._sessions[server_id]
        await session.close()
        del self._sessions[server_id]
        return True

    async def get_session(self, server_id: str) -> Optional[MockMCPSession]:
        """Get an active session for a server."""
        self._record_call("get_session", server_id=server_id)
        return self._sessions.get(server_id)

    async def list_tools(self, server_id: str = None) -> List[Dict]:
        """List tools from connected servers."""
        self._record_call("list_tools", server_id=server_id)

        all_tools = []

        if server_id:
            session = self._sessions.get(server_id)
            if session:
                result = await session.list_tools()
                all_tools.extend(result.get("tools", []))
        else:
            for session in self._sessions.values():
                result = await session.list_tools()
                all_tools.extend(result.get("tools", []))

        return all_tools

    async def call_tool(
        self, server_id: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on an external server."""
        self._record_call(
            "call_tool", server_id=server_id, tool_name=tool_name, arguments=arguments
        )

        session = self._sessions.get(server_id)
        if not session:
            raise RuntimeError(f"No session for server: {server_id}")

        return await session.call_tool(tool_name, arguments)

    async def health_check(self, server_id: str) -> bool:
        """Check health of a server session."""
        self._record_call("health_check", server_id=server_id)

        session = self._sessions.get(server_id)
        if not session:
            return False

        try:
            await session.list_tools()
            return True
        except Exception:
            return False


class MockToolRepository:
    """
    Mock for ToolRepository used by aggregator.

    Stores tools in memory for testing.
    """

    def __init__(self):
        self.tools: Dict[int, Dict[str, Any]] = {}
        self._calls: List[Dict[str, Any]] = []
        self._next_id = 1

    def _record_call(self, method: str, **kwargs):
        """Record a method call."""
        self._calls.append({"method": method, "args": kwargs})

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get recorded calls."""
        if method:
            return [c for c in self._calls if c["method"] == method]
        return self._calls

    def clear(self):
        """Clear all stored data."""
        self.tools = {}
        self._calls = []
        self._next_id = 1

    async def create_external_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict,
        source_server_id: str,
        original_name: str,
        is_external: bool = True,
        org_id: str = None,
        is_global: bool = True,
    ) -> int:
        """Create an external tool record (delegates to create_tool)."""
        return await self.create_tool(
            name=name,
            description=description,
            input_schema=input_schema,
            source_server_id=source_server_id,
            original_name=original_name,
            is_external=is_external,
        )

    async def create_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict,
        source_server_id: str,
        original_name: str,
        is_external: bool = True,
    ) -> int:
        """Create a tool record."""
        self._record_call(
            "create_tool",
            name=name,
            description=description,
            source_server_id=source_server_id,
            original_name=original_name,
        )

        tool_id = self._next_id
        self._next_id += 1

        self.tools[tool_id] = {
            "id": tool_id,
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "source_server_id": source_server_id,
            "original_name": original_name,
            "is_external": is_external,
            "is_classified": False,
            "skill_ids": [],
            "primary_skill_id": None,
        }

        return tool_id

    async def get_tool(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """Get a tool by ID."""
        self._record_call("get_tool", tool_id=tool_id)
        return self.tools.get(tool_id)

    async def get_tool_by_name(
        self, name: str, source_server_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get a tool by name and optionally server."""
        self._record_call("get_tool_by_name", name=name, source_server_id=source_server_id)

        for tool in self.tools.values():
            if tool["name"] == name:
                if source_server_id is None or tool["source_server_id"] == source_server_id:
                    return tool
        return None

    async def get_tool_ids_by_server(self, server_id: str) -> List[int]:
        """Get all tool IDs for a server."""
        self._record_call("get_tool_ids_by_server", server_id=server_id)

        return [tool["id"] for tool in self.tools.values() if tool["source_server_id"] == server_id]

    async def update_tool(self, tool_id: int, **updates) -> Optional[Dict[str, Any]]:
        """Update a tool."""
        self._record_call("update_tool", tool_id=tool_id, updates=updates)

        if tool_id not in self.tools:
            return None

        tool = self.tools[tool_id]
        for key, value in updates.items():
            if key in tool:
                tool[key] = value

        return tool

    async def delete_tools_by_server(self, server_id: str) -> int:
        """Delete all tools from a server."""
        self._record_call("delete_tools_by_server", server_id=server_id)

        to_delete = [
            tool_id for tool_id, tool in self.tools.items() if tool["source_server_id"] == server_id
        ]

        for tool_id in to_delete:
            del self.tools[tool_id]

        return len(to_delete)

    async def list_tools(
        self, server_id: str = None, is_classified: bool = None
    ) -> List[Dict[str, Any]]:
        """List tools with optional filters."""
        self._record_call("list_tools", server_id=server_id, is_classified=is_classified)

        results = []
        for tool in self.tools.values():
            if server_id and tool["source_server_id"] != server_id:
                continue
            if is_classified is not None and tool["is_classified"] != is_classified:
                continue
            results.append(tool)

        return results


class MockVectorRepository:
    """
    Mock for VectorRepository used by aggregator.

    Stores embeddings in memory for testing.
    """

    def __init__(self):
        self.vectors: Dict[str, Dict[str, Any]] = {}
        self._calls: List[Dict[str, Any]] = []

    def _record_call(self, method: str, **kwargs):
        """Record a method call."""
        self._calls.append({"method": method, "args": kwargs})

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get recorded calls."""
        if method:
            return [c for c in self._calls if c["method"] == method]
        return self._calls

    def clear(self):
        """Clear all stored data."""
        self.vectors = {}
        self._calls = []

    async def upsert_tool(
        self,
        tool_id: int,
        name: str,
        description: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> bool:
        """Upsert a tool vector."""
        self._record_call("upsert_tool", tool_id=tool_id, name=name, metadata=metadata)

        self.vectors[str(tool_id)] = {
            "id": str(tool_id),
            "name": name,
            "description": description,
            "embedding": embedding,
            "metadata": metadata,
        }

        return True

    async def delete_tool(self, tool_id: int) -> bool:
        """Delete a tool vector."""
        self._record_call("delete_tool", tool_id=tool_id)

        key = str(tool_id)
        if key in self.vectors:
            del self.vectors[key]
            return True
        return False

    async def update_tool_skills(
        self, tool_id: int, skill_ids: List[str], primary_skill_id: str
    ) -> bool:
        """Update skill assignments for a tool vector."""
        self._record_call(
            "update_tool_skills",
            tool_id=tool_id,
            skill_ids=skill_ids,
            primary_skill_id=primary_skill_id,
        )

        key = str(tool_id)
        if key in self.vectors:
            self.vectors[key]["metadata"]["skill_ids"] = skill_ids
            self.vectors[key]["metadata"]["primary_skill_id"] = primary_skill_id
            self.vectors[key]["metadata"]["is_classified"] = True
            return True
        return False

    async def search(
        self, query_vector: List[float], filter_conditions: Dict = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for similar tools."""
        self._record_call("search", filter_conditions=filter_conditions, limit=limit)

        results = []
        for vector in self.vectors.values():
            # Simple mock scoring
            score = 0.7 + (hash(vector["id"]) % 30) / 100
            results.append({"id": vector["id"], "score": score, "payload": vector["metadata"]})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


class MockModelClient:
    """
    Mock for model client used for embeddings.
    """

    def __init__(self):
        self._calls: List[Dict[str, Any]] = []
        self._embedding_size = 1536

    def _record_call(self, method: str, **kwargs):
        """Record a method call."""
        self._calls.append({"method": method, "args": kwargs})

    def get_calls(self, method: str = None) -> List[Dict[str, Any]]:
        """Get recorded calls."""
        if method:
            return [c for c in self._calls if c["method"] == method]
        return self._calls

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding for text."""
        self._record_call("generate_embedding", text=text)
        return [0.1] * self._embedding_size


# Export all mocks
__all__ = [
    "MockMCPSession",
    "MockServerRegistry",
    "MockExternalServer",
    "MockSkillClassifier",
    "MockSessionManager",
    "MockToolRepository",
    "MockVectorRepository",
    "MockModelClient",
]
