"""
Aggregator Service Data Contract

Defines canonical data structures for MCP Server Aggregator testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for aggregator service test data.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum

# ============================================================================
# Enums
# ============================================================================


class ServerTransportType(str, Enum):
    """Transport types for external MCP servers."""

    STDIO = "STDIO"  # Standard input/output (local process)
    SSE = "SSE"  # Server-Sent Events (HTTP streaming)
    HTTP = "HTTP"  # Standard HTTP request/response
    STREAMABLE_HTTP = "STREAMABLE_HTTP"  # MCP Streamable HTTP (bidirectional)


class ServerStatus(str, Enum):
    """Connection status of external MCP server."""

    CONNECTED = "CONNECTED"  # Server connected and healthy
    DISCONNECTED = "DISCONNECTED"  # Server intentionally disconnected
    ERROR = "ERROR"  # Server unreachable or failing
    CONNECTING = "CONNECTING"  # Connection in progress
    DEGRADED = "DEGRADED"  # Connected but elevated errors


class RoutingStrategy(str, Enum):
    """How routing decision was made."""

    NAMESPACE_RESOLVED = "namespace_resolved"  # Parsed from namespaced name
    EXPLICIT_SERVER = "explicit_server"  # Server ID provided
    FALLBACK = "fallback"  # Using fallback server


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================


class ServerRegistrationRequestContract(BaseModel):
    """
    Contract: External server registration request schema.

    Used for registering a new external MCP server.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z][a-z0-9_-]*$",
        description="Unique server identifier (lowercase, hyphens allowed)",
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Human-readable server description"
    )
    transport_type: ServerTransportType = Field(
        ..., description="Transport protocol for server connection"
    )
    connection_config: Dict[str, Any] = Field(
        ..., description="Transport-specific connection configuration"
    )
    health_check_url: Optional[str] = Field(
        None, description="Optional HTTP endpoint for health checks"
    )
    auto_connect: bool = Field(True, description="Connect immediately after registration")

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate server name format: lowercase, start with letter."""
        if not v[0].isalpha():
            raise ValueError("Server name must start with a letter")
        return v.lower()

    @model_validator(mode="after")
    def validate_connection_config(self) -> "ServerRegistrationRequestContract":
        """Validate connection config matches transport type."""
        config = self.connection_config
        transport = self.transport_type

        if transport == ServerTransportType.STDIO:
            if "command" not in config:
                raise ValueError("STDIO transport requires 'command' in connection_config")

        elif transport == ServerTransportType.SSE:
            if "url" not in config:
                raise ValueError("SSE transport requires 'url' in connection_config")

        elif transport == ServerTransportType.HTTP:
            if "base_url" not in config:
                raise ValueError("HTTP transport requires 'base_url' in connection_config")

        elif transport == ServerTransportType.STREAMABLE_HTTP:
            if "url" not in config:
                raise ValueError("STREAMABLE_HTTP transport requires 'url' in connection_config")

        return self

    class Config:
        json_schema_extra = {
            "example": {
                "name": "github-mcp",
                "description": "GitHub MCP Server for repository operations",
                "transport_type": "SSE",
                "connection_config": {
                    "url": "https://github-mcp.example.com/sse",
                    "headers": {"Authorization": "Bearer ${GITHUB_TOKEN}"},
                },
                "health_check_url": "https://github-mcp.example.com/health",
                "auto_connect": True,
            }
        }


class ServerConnectionRequestContract(BaseModel):
    """
    Contract: Server connect/disconnect request schema.
    """

    server_id: str = Field(..., description="Server UUID")
    action: str = Field(..., pattern="^(connect|disconnect)$", description="Action to perform")
    force: bool = Field(False, description="Force action even if pending requests")


class AggregatedSearchRequestContract(BaseModel):
    """
    Contract: Search request including external servers.
    """

    query: str = Field(
        ..., min_length=1, max_length=1000, description="Natural language search query"
    )
    include_external: bool = Field(True, description="Include tools from external servers")
    server_filter: Optional[List[str]] = Field(
        None, description="Limit to specific servers by name"
    )
    limit: int = Field(10, ge=1, le=50, description="Maximum results")
    skill_threshold: float = Field(0.4, ge=0.0, le=1.0, description="Skill match threshold")
    tool_threshold: float = Field(0.3, ge=0.0, le=1.0, description="Tool match threshold")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "create a GitHub issue",
                "include_external": True,
                "server_filter": ["github-mcp", "jira-mcp"],
                "limit": 10,
            }
        }


class ToolExecutionRequestContract(BaseModel):
    """
    Contract: Tool execution request for aggregated tools.
    """

    name: str = Field(..., min_length=1, description="Tool name (namespaced or original)")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    server_id: Optional[str] = Field(
        None, description="Explicit server ID (if not using namespaced name)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "github-mcp.create_issue",
                "arguments": {"repo": "owner/repo", "title": "Bug report", "body": "Description"},
            }
        }


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================


class ServerRecordContract(BaseModel):
    """
    Contract: External server record response schema.
    """

    id: str = Field(..., description="Server UUID")
    name: str = Field(..., description="Server name")
    description: Optional[str] = Field(None, description="Server description")
    transport_type: ServerTransportType = Field(..., description="Transport type")
    status: ServerStatus = Field(..., description="Current connection status")
    health_check_url: Optional[str] = Field(None, description="Health endpoint")
    last_health_check: Optional[datetime] = Field(None, description="Last health check time")
    tool_count: int = Field(0, ge=0, description="Number of tools from this server")
    error_message: Optional[str] = Field(None, description="Last error message")
    registered_at: datetime = Field(..., description="Registration timestamp")
    connected_at: Optional[datetime] = Field(None, description="Connection timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "uuid-1234",
                "name": "github-mcp",
                "description": "GitHub MCP Server",
                "transport_type": "SSE",
                "status": "CONNECTED",
                "tool_count": 15,
                "registered_at": "2025-01-08T10:00:00Z",
                "connected_at": "2025-01-08T10:00:05Z",
            }
        }


class SourceServerContract(BaseModel):
    """
    Contract: Source server info embedded in tool response.
    """

    id: str = Field(..., description="Server UUID")
    name: str = Field(..., description="Server name")
    status: ServerStatus = Field(..., description="Current status")


class AggregatedToolContract(BaseModel):
    """
    Contract: Aggregated tool response schema.
    """

    id: str = Field(..., description="Internal tool ID")
    name: str = Field(..., description="Namespaced tool name")
    original_name: str = Field(..., description="Original tool name from server")
    description: str = Field(..., description="Tool description")
    score: float = Field(..., ge=0.0, le=1.0, description="Search relevance score")
    source_server: SourceServerContract = Field(..., description="Source server info")
    skill_ids: List[str] = Field(default_factory=list, description="Assigned skill IDs")
    primary_skill_id: Optional[str] = Field(None, description="Primary skill ID")
    is_classified: bool = Field(False, description="Whether tool has been classified")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="Tool input schema")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "1",
                "name": "github-mcp.create_issue",
                "original_name": "create_issue",
                "description": "Create a new GitHub issue",
                "score": 0.95,
                "source_server": {"id": "uuid-1234", "name": "github-mcp", "status": "CONNECTED"},
                "skill_ids": ["code_management", "issue_tracking"],
                "primary_skill_id": "issue_tracking",
                "is_classified": True,
            }
        }


class RoutingContextContract(BaseModel):
    """
    Contract: Routing decision context.
    """

    tool_name: str = Field(..., description="Requested tool name")
    resolved_server_id: str = Field(..., description="Target server UUID")
    resolved_server_name: str = Field(..., description="Target server name")
    original_tool_name: str = Field(..., description="De-namespaced tool name")
    routing_strategy: RoutingStrategy = Field(..., description="How routing was determined")
    fallback_servers: List[str] = Field(default_factory=list, description="Fallback server IDs")


class ToolExecutionResponseContract(BaseModel):
    """
    Contract: Tool execution response from external server.
    """

    content: List[Dict[str, Any]] = Field(default_factory=list, description="Tool response content")
    is_error: bool = Field(False, description="Whether execution resulted in error")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "content": [{"type": "text", "text": '{"issue_number": 123}'}],
                "is_error": False,
                "metadata": {
                    "routed_to": "github-mcp",
                    "routing_time_ms": 12.5,
                    "execution_time_ms": 450.2,
                },
            }
        }


class ServerHealthContract(BaseModel):
    """
    Contract: Server health check response.
    """

    server_id: str = Field(..., description="Server UUID")
    server_name: str = Field(..., description="Server name")
    status: ServerStatus = Field(..., description="Health status")
    last_check: datetime = Field(..., description="Last health check time")
    response_time_ms: Optional[float] = Field(None, description="Health check response time")
    consecutive_failures: int = Field(0, ge=0, description="Consecutive failed checks")
    error_message: Optional[str] = Field(None, description="Last error if unhealthy")


class AggregatorStateContract(BaseModel):
    """
    Contract: Current state of the aggregator.
    """

    total_servers: int = Field(..., ge=0, description="Total registered servers")
    connected_servers: int = Field(..., ge=0, description="Currently connected servers")
    disconnected_servers: int = Field(..., ge=0, description="Disconnected servers")
    error_servers: int = Field(..., ge=0, description="Servers in error state")
    total_tools: int = Field(..., ge=0, description="Total aggregated tools")
    classified_tools: int = Field(..., ge=0, description="Tools with skill assignments")
    unclassified_tools: int = Field(..., ge=0, description="Tools pending classification")
    last_sync: Optional[datetime] = Field(None, description="Last full sync time")

    class Config:
        json_schema_extra = {
            "example": {
                "total_servers": 5,
                "connected_servers": 4,
                "disconnected_servers": 0,
                "error_servers": 1,
                "total_tools": 125,
                "classified_tools": 120,
                "unclassified_tools": 5,
                "last_sync": "2025-01-08T10:00:00Z",
            }
        }


# ============================================================================
# Test Data Factory
# ============================================================================


class AggregatorTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    """

    # ========================================================================
    # ID Generators
    # ========================================================================

    @staticmethod
    def make_server_id() -> str:
        """Generate unique test server ID (UUID)."""
        return str(uuid.uuid4())

    @staticmethod
    def make_server_name() -> str:
        """Generate unique test server name."""
        return f"test-server-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_tool_id() -> int:
        """Generate test tool ID."""
        return abs(hash(uuid.uuid4().hex)) % 1000000

    # ========================================================================
    # Valid Data Generators - Server Registration
    # ========================================================================

    @staticmethod
    def make_stdio_server_registration(**overrides) -> ServerRegistrationRequestContract:
        """
        Create valid STDIO server registration request.

        Args:
            **overrides: Override any default fields

        Returns:
            ServerRegistrationRequestContract for STDIO transport
        """
        name = overrides.pop("name", None) or AggregatorTestDataFactory.make_server_name()
        defaults = {
            "name": name,
            "description": f"Test STDIO MCP Server: {name}",
            "transport_type": ServerTransportType.STDIO,
            "connection_config": {
                "command": "python",
                "args": ["-m", "test_mcp_server"],
                "env": {"MCP_MODE": "test"},
            },
            "health_check_url": None,
            "auto_connect": True,
        }
        defaults.update(overrides)
        return ServerRegistrationRequestContract(**defaults)

    @staticmethod
    def make_sse_server_registration(**overrides) -> ServerRegistrationRequestContract:
        """
        Create valid SSE server registration request.

        Args:
            **overrides: Override any default fields

        Returns:
            ServerRegistrationRequestContract for SSE transport
        """
        name = overrides.pop("name", None) or AggregatorTestDataFactory.make_server_name()
        defaults = {
            "name": name,
            "description": f"Test SSE MCP Server: {name}",
            "transport_type": ServerTransportType.SSE,
            "connection_config": {
                "url": f"https://{name}.example.com/sse",
                "headers": {"Authorization": "Bearer test-token"},
            },
            "health_check_url": f"https://{name}.example.com/health",
            "auto_connect": True,
        }
        defaults.update(overrides)
        return ServerRegistrationRequestContract(**defaults)

    @staticmethod
    def make_http_server_registration(**overrides) -> ServerRegistrationRequestContract:
        """
        Create valid HTTP server registration request.

        Args:
            **overrides: Override any default fields

        Returns:
            ServerRegistrationRequestContract for HTTP transport
        """
        name = overrides.pop("name", None) or AggregatorTestDataFactory.make_server_name()
        defaults = {
            "name": name,
            "description": f"Test HTTP MCP Server: {name}",
            "transport_type": ServerTransportType.HTTP,
            "connection_config": {
                "base_url": f"https://{name}.example.com/api",
                "headers": {"X-API-Key": "test-key"},
            },
            "health_check_url": f"https://{name}.example.com/health",
            "auto_connect": True,
        }
        defaults.update(overrides)
        return ServerRegistrationRequestContract(**defaults)

    # ========================================================================
    # Valid Data Generators - Server Record
    # ========================================================================

    @staticmethod
    def make_server_record(**overrides) -> ServerRecordContract:
        """
        Create valid server record for assertions.

        Args:
            **overrides: Override any default fields

        Returns:
            ServerRecordContract with valid data
        """
        server_id = overrides.pop("id", None) or AggregatorTestDataFactory.make_server_id()
        name = overrides.pop("name", None) or "test-server"
        defaults = {
            "id": server_id,
            "name": name,
            "description": f"Test server: {name}",
            "transport_type": ServerTransportType.SSE,
            "status": ServerStatus.CONNECTED,
            "health_check_url": f"https://{name}.example.com/health",
            "last_health_check": datetime.now(timezone.utc),
            "tool_count": 10,
            "error_message": None,
            "registered_at": datetime.now(timezone.utc),
            "connected_at": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return ServerRecordContract(**defaults)

    # ========================================================================
    # Valid Data Generators - Aggregated Tool
    # ========================================================================

    @staticmethod
    def make_aggregated_tool(**overrides) -> AggregatedToolContract:
        """
        Create valid aggregated tool for assertions.

        Args:
            **overrides: Override any default fields

        Returns:
            AggregatedToolContract with valid data
        """
        tool_id = overrides.pop("id", None) or str(AggregatorTestDataFactory.make_tool_id())
        server_name = overrides.pop("server_name", "github-mcp")
        original_name = overrides.pop("original_name", "create_issue")

        defaults = {
            "id": tool_id,
            "name": f"{server_name}.{original_name}",
            "original_name": original_name,
            "description": f"Tool: {original_name} from {server_name}",
            "score": 0.85,
            "source_server": SourceServerContract(
                id=AggregatorTestDataFactory.make_server_id(),
                name=server_name,
                status=ServerStatus.CONNECTED,
            ),
            "skill_ids": ["code_management"],
            "primary_skill_id": "code_management",
            "is_classified": True,
            "input_schema": {"type": "object", "properties": {"param1": {"type": "string"}}},
        }
        defaults.update(overrides)
        return AggregatedToolContract(**defaults)

    # ========================================================================
    # Valid Data Generators - Search & Execution
    # ========================================================================

    @staticmethod
    def make_search_request(**overrides) -> AggregatedSearchRequestContract:
        """Create valid aggregated search request."""
        defaults = {
            "query": "create a GitHub issue",
            "include_external": True,
            "server_filter": None,
            "limit": 10,
            "skill_threshold": 0.4,
            "tool_threshold": 0.3,
        }
        defaults.update(overrides)
        return AggregatedSearchRequestContract(**defaults)

    @staticmethod
    def make_tool_execution_request(**overrides) -> ToolExecutionRequestContract:
        """Create valid tool execution request."""
        defaults = {
            "name": "github-mcp.create_issue",
            "arguments": {"repo": "owner/repo", "title": "Test issue", "body": "Test description"},
            "server_id": None,
        }
        defaults.update(overrides)
        return ToolExecutionRequestContract(**defaults)

    @staticmethod
    def make_tool_execution_response(**overrides) -> ToolExecutionResponseContract:
        """Create valid tool execution response."""
        defaults = {
            "content": [{"type": "text", "text": '{"issue_number": 123}'}],
            "is_error": False,
            "metadata": {
                "routed_to": "github-mcp",
                "routing_time_ms": 15.2,
                "execution_time_ms": 320.5,
            },
        }
        defaults.update(overrides)
        return ToolExecutionResponseContract(**defaults)

    # ========================================================================
    # Valid Data Generators - State & Health
    # ========================================================================

    @staticmethod
    def make_aggregator_state(**overrides) -> AggregatorStateContract:
        """Create valid aggregator state."""
        defaults = {
            "total_servers": 5,
            "connected_servers": 4,
            "disconnected_servers": 0,
            "error_servers": 1,
            "total_tools": 125,
            "classified_tools": 120,
            "unclassified_tools": 5,
            "last_sync": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return AggregatorStateContract(**defaults)

    @staticmethod
    def make_server_health(**overrides) -> ServerHealthContract:
        """Create valid server health record."""
        server_id = overrides.pop("server_id", None) or AggregatorTestDataFactory.make_server_id()
        defaults = {
            "server_id": server_id,
            "server_name": "test-server",
            "status": ServerStatus.CONNECTED,
            "last_check": datetime.now(timezone.utc),
            "response_time_ms": 45.5,
            "consecutive_failures": 0,
            "error_message": None,
        }
        defaults.update(overrides)
        return ServerHealthContract(**defaults)

    # ========================================================================
    # Predefined Test Servers (Seed Data)
    # ========================================================================

    @staticmethod
    def get_seed_servers() -> List[ServerRegistrationRequestContract]:
        """
        Get predefined external servers for seeding tests.

        Returns list of common external MCP server configurations.
        """
        return [
            ServerRegistrationRequestContract(
                name="github-mcp",
                description="GitHub MCP Server for repository operations",
                transport_type=ServerTransportType.SSE,
                connection_config={
                    "url": "https://github-mcp.example.com/sse",
                    "headers": {"Authorization": "Bearer ${GITHUB_TOKEN}"},
                },
                health_check_url="https://github-mcp.example.com/health",
            ),
            ServerRegistrationRequestContract(
                name="slack-mcp",
                description="Slack MCP Server for team communication",
                transport_type=ServerTransportType.SSE,
                connection_config={
                    "url": "https://slack-mcp.example.com/sse",
                    "headers": {"Authorization": "Bearer ${SLACK_TOKEN}"},
                },
                health_check_url="https://slack-mcp.example.com/health",
            ),
            ServerRegistrationRequestContract(
                name="local-tools",
                description="Local STDIO MCP Server",
                transport_type=ServerTransportType.STDIO,
                connection_config={
                    "command": "python",
                    "args": ["-m", "local_mcp_server"],
                    "env": {},
                },
            ),
        ]

    # ========================================================================
    # Invalid Data Generators (for negative testing)
    # ========================================================================

    @staticmethod
    def make_invalid_server_empty_name() -> dict:
        """Generate server request with empty name."""
        return {
            "name": "",
            "transport_type": "SSE",
            "connection_config": {"url": "https://example.com/sse"},
        }

    @staticmethod
    def make_invalid_server_name_starts_with_number() -> dict:
        """Generate server request with name starting with number."""
        return {
            "name": "123-invalid",
            "transport_type": "SSE",
            "connection_config": {"url": "https://example.com/sse"},
        }

    @staticmethod
    def make_invalid_server_name_with_spaces() -> dict:
        """Generate server request with spaces in name."""
        return {
            "name": "invalid server name",
            "transport_type": "SSE",
            "connection_config": {"url": "https://example.com/sse"},
        }

    @staticmethod
    def make_invalid_server_missing_config() -> dict:
        """Generate server request missing required config."""
        return {
            "name": "valid-name",
            "transport_type": "SSE",
            "connection_config": {},  # Missing 'url' for SSE
        }

    @staticmethod
    def make_invalid_stdio_missing_command() -> dict:
        """Generate STDIO server missing command."""
        return {
            "name": "stdio-server",
            "transport_type": "STDIO",
            "connection_config": {"args": ["-m", "test"]},  # Missing 'command'
        }

    @staticmethod
    def make_invalid_tool_execution_empty_name() -> dict:
        """Generate tool execution with empty name."""
        return {"name": "", "arguments": {}}

    @staticmethod
    def make_invalid_search_negative_threshold() -> dict:
        """Generate search with negative threshold."""
        return {"query": "test query", "skill_threshold": -0.5}


# ============================================================================
# Request Builders (for complex test scenarios)
# ============================================================================


class ServerRegistrationBuilder:
    """
    Builder pattern for creating complex server registration requests.

    Example:
        request = (
            ServerRegistrationBuilder()
            .with_name("github-mcp")
            .with_sse_transport("https://github.example.com/sse")
            .with_health_check("https://github.example.com/health")
            .auto_connect(False)
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "name": AggregatorTestDataFactory.make_server_name(),
            "description": "Test MCP Server",
            "transport_type": ServerTransportType.SSE,
            "connection_config": {"url": "https://test.example.com/sse"},
            "health_check_url": None,
            "auto_connect": True,
        }

    def with_name(self, name: str) -> "ServerRegistrationBuilder":
        """Set server name."""
        self._data["name"] = name
        self._data["description"] = f"MCP Server: {name}"
        return self

    def with_description(self, description: str) -> "ServerRegistrationBuilder":
        """Set description."""
        self._data["description"] = description
        return self

    def with_stdio_transport(
        self, command: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None
    ) -> "ServerRegistrationBuilder":
        """Configure STDIO transport."""
        self._data["transport_type"] = ServerTransportType.STDIO
        self._data["connection_config"] = {"command": command, "args": args or [], "env": env or {}}
        return self

    def with_sse_transport(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> "ServerRegistrationBuilder":
        """Configure SSE transport."""
        self._data["transport_type"] = ServerTransportType.SSE
        self._data["connection_config"] = {"url": url, "headers": headers or {}}
        return self

    def with_http_transport(
        self, base_url: str, headers: Optional[Dict[str, str]] = None
    ) -> "ServerRegistrationBuilder":
        """Configure HTTP transport."""
        self._data["transport_type"] = ServerTransportType.HTTP
        self._data["connection_config"] = {"base_url": base_url, "headers": headers or {}}
        return self

    def with_health_check(self, url: str) -> "ServerRegistrationBuilder":
        """Set health check URL."""
        self._data["health_check_url"] = url
        return self

    def auto_connect(self, enabled: bool = True) -> "ServerRegistrationBuilder":
        """Set auto-connect flag."""
        self._data["auto_connect"] = enabled
        return self

    def build(self) -> ServerRegistrationRequestContract:
        """Build the final request."""
        return ServerRegistrationRequestContract(**self._data)


class AggregatedToolBuilder:
    """
    Builder pattern for creating aggregated tool records.

    Example:
        tool = (
            AggregatedToolBuilder()
            .from_server("github-mcp")
            .with_name("create_issue")
            .with_skills(["code_management", "issue_tracking"])
            .with_score(0.95)
            .build()
        )
    """

    def __init__(self):
        self._server_name = "test-server"
        self._server_id = AggregatorTestDataFactory.make_server_id()
        self._data = {
            "id": str(AggregatorTestDataFactory.make_tool_id()),
            "original_name": "test_tool",
            "description": "Test tool description",
            "score": 0.8,
            "skill_ids": [],
            "primary_skill_id": None,
            "is_classified": False,
            "input_schema": None,
        }

    def from_server(
        self,
        name: str,
        server_id: Optional[str] = None,
        status: ServerStatus = ServerStatus.CONNECTED,
    ) -> "AggregatedToolBuilder":
        """Set source server."""
        self._server_name = name
        self._server_id = server_id or AggregatorTestDataFactory.make_server_id()
        self._server_status = status
        return self

    def with_name(self, name: str) -> "AggregatedToolBuilder":
        """Set tool name."""
        self._data["original_name"] = name
        return self

    def with_description(self, description: str) -> "AggregatedToolBuilder":
        """Set description."""
        self._data["description"] = description
        return self

    def with_skills(
        self, skill_ids: List[str], primary: Optional[str] = None
    ) -> "AggregatedToolBuilder":
        """Set skill assignments."""
        self._data["skill_ids"] = skill_ids
        self._data["primary_skill_id"] = primary or (skill_ids[0] if skill_ids else None)
        self._data["is_classified"] = len(skill_ids) > 0
        return self

    def with_score(self, score: float) -> "AggregatedToolBuilder":
        """Set relevance score."""
        self._data["score"] = score
        return self

    def with_schema(self, schema: Dict[str, Any]) -> "AggregatedToolBuilder":
        """Set input schema."""
        self._data["input_schema"] = schema
        return self

    def unclassified(self) -> "AggregatedToolBuilder":
        """Mark as unclassified."""
        self._data["skill_ids"] = []
        self._data["primary_skill_id"] = None
        self._data["is_classified"] = False
        return self

    def build(self) -> AggregatedToolContract:
        """Build the final tool."""
        return AggregatedToolContract(
            id=self._data["id"],
            name=f"{self._server_name}.{self._data['original_name']}",
            original_name=self._data["original_name"],
            description=self._data["description"],
            score=self._data["score"],
            source_server=SourceServerContract(
                id=self._server_id,
                name=self._server_name,
                status=getattr(self, "_server_status", ServerStatus.CONNECTED),
            ),
            skill_ids=self._data["skill_ids"],
            primary_skill_id=self._data["primary_skill_id"],
            is_classified=self._data["is_classified"],
            input_schema=self._data["input_schema"],
        )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "ServerTransportType",
    "ServerStatus",
    "RoutingStrategy",
    # Request Contracts
    "ServerRegistrationRequestContract",
    "ServerConnectionRequestContract",
    "AggregatedSearchRequestContract",
    "ToolExecutionRequestContract",
    # Response Contracts
    "ServerRecordContract",
    "SourceServerContract",
    "AggregatedToolContract",
    "RoutingContextContract",
    "AggregatorStateContract",
    "ToolExecutionResponseContract",
    "ServerHealthContract",
    # Factory
    "AggregatorTestDataFactory",
    # Builders
    "ServerRegistrationBuilder",
    "AggregatedToolBuilder",
]
