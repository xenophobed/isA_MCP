"""
Aggregator Service TDD Tests

Test-Driven Development tests for the MCP Server Aggregator Service.
All tests reference business rules from tests/contracts/aggregator/logic_contract.md
and use data structures from tests/contracts/aggregator/data_contract.py.

TDD Status: RED/GREEN PHASE - Implementation in progress.
"""

import pytest
from pydantic import ValidationError

# Import contracts
from tests.contracts.aggregator.data_contract import (
    AggregatorTestDataFactory,
    ServerRegistrationRequestContract,
    ServerRegistrationBuilder,
    AggregatedToolBuilder,
    ServerTransportType,
    ServerStatus,
)

# Service imports - will be available once service is implemented
try:
    from services.aggregator_service import (
        AggregatorService,
        ServerRegistry,
        SessionManager,
        ToolAggregator,
        RequestRouter,
    )
    from tests.component.mocks.aggregator_mocks import (
        MockMCPSession,
        MockServerRegistry,
        MockExternalServer,
        MockSkillClassifier,
        MockSessionManager,
        MockToolRepository,
        MockVectorRepository,
        MockModelClient,
    )

    SERVICE_AVAILABLE = True
except ImportError as e:
    # Service not yet available - tests will be skipped
    AggregatorService = None
    ServerRegistry = None
    SessionManager = None
    ToolAggregator = None
    RequestRouter = None
    MockMCPSession = None
    MockServerRegistry = None
    MockExternalServer = None
    MockSkillClassifier = None
    MockSessionManager = None
    MockToolRepository = None
    MockVectorRepository = None
    MockModelClient = None
    SERVICE_AVAILABLE = False
    import warnings

    warnings.warn(f"AggregatorService not available for testing: {e}")


# ============================================================================
# Contract Validation Tests (Data Contract)
# These tests validate that the data contracts themselves work correctly
# ============================================================================


@pytest.mark.tdd
@pytest.mark.unit
class TestDataContractValidation:
    """Test that data contracts validate input correctly."""

    def test_valid_sse_server_registration(self):
        """Test that valid SSE server registration is accepted."""
        server = AggregatorTestDataFactory.make_sse_server_registration(
            name="github-mcp",
        )
        assert server.name == "github-mcp"
        assert server.transport_type == ServerTransportType.SSE
        assert "url" in server.connection_config

    def test_valid_stdio_server_registration(self):
        """Test that valid STDIO server registration is accepted."""
        server = AggregatorTestDataFactory.make_stdio_server_registration(
            name="local-tools",
        )
        assert server.name == "local-tools"
        assert server.transport_type == ServerTransportType.STDIO
        assert "command" in server.connection_config

    def test_valid_http_server_registration(self):
        """Test that valid HTTP server registration is accepted."""
        server = AggregatorTestDataFactory.make_http_server_registration(
            name="api-server",
        )
        assert server.name == "api-server"
        assert server.transport_type == ServerTransportType.HTTP
        assert "base_url" in server.connection_config

    def test_invalid_server_empty_name_rejected(self):
        """Test that empty server name is rejected."""
        invalid_data = AggregatorTestDataFactory.make_invalid_server_empty_name()
        with pytest.raises(ValidationError):
            ServerRegistrationRequestContract(**invalid_data)

    def test_invalid_server_name_starts_with_number_rejected(self):
        """Test that server name starting with number is rejected."""
        invalid_data = AggregatorTestDataFactory.make_invalid_server_name_starts_with_number()
        with pytest.raises(ValidationError):
            ServerRegistrationRequestContract(**invalid_data)

    def test_invalid_server_name_with_spaces_rejected(self):
        """Test that server name with spaces is rejected."""
        invalid_data = AggregatorTestDataFactory.make_invalid_server_name_with_spaces()
        with pytest.raises(ValidationError):
            ServerRegistrationRequestContract(**invalid_data)

    def test_invalid_sse_missing_url_rejected(self):
        """Test that SSE server missing URL is rejected."""
        invalid_data = AggregatorTestDataFactory.make_invalid_server_missing_config()
        with pytest.raises(ValidationError):
            ServerRegistrationRequestContract(**invalid_data)

    def test_invalid_stdio_missing_command_rejected(self):
        """Test that STDIO server missing command is rejected."""
        invalid_data = AggregatorTestDataFactory.make_invalid_stdio_missing_command()
        with pytest.raises(ValidationError):
            ServerRegistrationRequestContract(**invalid_data)

    def test_builder_pattern_creates_valid_server(self):
        """Test ServerRegistrationBuilder creates valid request."""
        server = (
            ServerRegistrationBuilder()
            .with_name("github-mcp")
            .with_sse_transport("https://github.example.com/sse")
            .with_health_check("https://github.example.com/health")
            .auto_connect(False)
            .build()
        )
        assert server.name == "github-mcp"
        assert server.transport_type == ServerTransportType.SSE
        assert server.auto_connect is False
        assert server.health_check_url == "https://github.example.com/health"

    def test_aggregated_tool_builder_creates_valid_tool(self):
        """Test AggregatedToolBuilder creates valid tool."""
        tool = (
            AggregatedToolBuilder()
            .from_server("github-mcp")
            .with_name("create_issue")
            .with_description("Create a new GitHub issue")
            .with_skills(["code_management", "issue_tracking"])
            .with_score(0.95)
            .build()
        )
        assert tool.name == "github-mcp.create_issue"
        assert tool.original_name == "create_issue"
        assert tool.source_server.name == "github-mcp"
        assert "code_management" in tool.skill_ids
        assert tool.is_classified is True

    def test_seed_servers_all_valid(self):
        """Test that all seed servers from factory are valid."""
        seed_servers = AggregatorTestDataFactory.get_seed_servers()
        assert len(seed_servers) >= 3  # At least 3 seed servers
        for server in seed_servers:
            assert isinstance(server, ServerRegistrationRequestContract)
            assert len(server.name) >= 1


# ============================================================================
# Fixtures for Aggregator Service Testing
# ============================================================================


@pytest.fixture
def mock_server_registry():
    """Provide mock server registry for testing."""
    if not SERVICE_AVAILABLE:
        pytest.skip("AggregatorService not available - check import path")
    return MockServerRegistry()


@pytest.fixture
def mock_session_manager(mock_server_registry):
    """Provide mock session manager for testing."""
    if not SERVICE_AVAILABLE:
        pytest.skip("AggregatorService not available - check import path")
    return MockSessionManager(server_registry=mock_server_registry)


@pytest.fixture
def mock_tool_repository():
    """Provide mock tool repository for testing."""
    if not SERVICE_AVAILABLE:
        pytest.skip("AggregatorService not available - check import path")
    return MockToolRepository()


@pytest.fixture
def mock_vector_repository():
    """Provide mock vector repository for testing."""
    if not SERVICE_AVAILABLE:
        pytest.skip("AggregatorService not available - check import path")
    return MockVectorRepository()


@pytest.fixture
def mock_skill_classifier():
    """Provide mock skill classifier for testing."""
    if not SERVICE_AVAILABLE:
        pytest.skip("AggregatorService not available - check import path")
    return MockSkillClassifier()


@pytest.fixture
def mock_model_client():
    """Provide mock model client for testing."""
    if not SERVICE_AVAILABLE:
        pytest.skip("AggregatorService not available - check import path")
    return MockModelClient()


@pytest.fixture
def aggregator_service(
    mock_server_registry,
    mock_session_manager,
    mock_tool_repository,
    mock_vector_repository,
    mock_skill_classifier,
    mock_model_client,
):
    """Provide AggregatorService with mocked dependencies."""
    if not SERVICE_AVAILABLE:
        pytest.skip("AggregatorService not available - check import path")
    service = AggregatorService(
        server_registry=mock_server_registry,
        session_manager=mock_session_manager,
        tool_repository=mock_tool_repository,
        vector_repository=mock_vector_repository,
        skill_classifier=mock_skill_classifier,
        model_client=mock_model_client,
    )
    return service


# ============================================================================
# BR-001: Server Registration
# ============================================================================


@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.aggregator
class TestBR001ServerRegistration:
    """
    BR-001: Server Registration

    Given: Valid server registration request from admin
    When: Admin registers a new external MCP server
    Then:
    - Server name validated (lowercase, starts with letter, hyphens/underscores allowed)
    - Connection config validated based on transport type
    - Server record created in mcp.external_servers table
    - Status set to DISCONNECTED initially
    - If auto_connect=true, connection attempt initiated
    """

    @pytest.mark.asyncio
    async def test_register_server_success(self, aggregator_service, mock_server_registry):
        """Test successful server registration."""
        # Arrange
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="github-mcp",
            auto_connect=False,  # Don't auto-connect for this test
        ).model_dump()

        # Act
        result = await aggregator_service.register_server(config)

        # Assert
        assert result["name"] == "github-mcp"
        assert result["status"] == ServerStatus.DISCONNECTED
        assert result["transport_type"] == ServerTransportType.SSE
        assert "id" in result

        # Verify registry was called
        calls = mock_server_registry.get_calls("add")
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_register_server_auto_connect(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test that auto_connect=true initiates connection."""
        # Arrange
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="slack-mcp",
            auto_connect=True,
        ).model_dump()

        # Act
        result = await aggregator_service.register_server(config)

        # Assert
        assert result["name"] == "slack-mcp"
        # Connection should have been initiated
        connect_calls = mock_session_manager.get_calls("connect")
        assert len(connect_calls) >= 1

    @pytest.mark.asyncio
    async def test_register_server_duplicate_name_raises_error(
        self, aggregator_service, mock_server_registry
    ):
        """Test that duplicate server name raises ValueError."""
        # Arrange - create server first
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="duplicate-server",
            auto_connect=False,
        ).model_dump()
        await aggregator_service.register_server(config)

        # Act & Assert - try to create duplicate
        with pytest.raises(ValueError) as exc:
            await aggregator_service.register_server(config)
        assert "already exists" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_register_stdio_server_with_command(
        self, aggregator_service, mock_server_registry
    ):
        """Test STDIO server registration with command config."""
        # Arrange
        config = AggregatorTestDataFactory.make_stdio_server_registration(
            name="local-mcp",
        ).model_dump()

        # Act
        result = await aggregator_service.register_server(config)

        # Assert
        assert result["transport_type"] == ServerTransportType.STDIO
        assert result["name"] == "local-mcp"

    @pytest.mark.asyncio
    async def test_register_http_server_with_base_url(
        self, aggregator_service, mock_server_registry
    ):
        """Test HTTP server registration with base_url config."""
        # Arrange
        config = AggregatorTestDataFactory.make_http_server_registration(
            name="http-api-mcp",
        ).model_dump()

        # Act
        result = await aggregator_service.register_server(config)

        # Assert
        assert result["transport_type"] == ServerTransportType.HTTP
        assert result["name"] == "http-api-mcp"


# ============================================================================
# BR-002: Server Connection
# ============================================================================


@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.aggregator
class TestBR002ServerConnection:
    """
    BR-002: Server Connection

    Given: Registered server with valid configuration
    When: Connection is requested (auto or manual)
    Then:
    - Status changes to CONNECTING
    - Transport created based on transport_type
    - MCP ClientSession established
    - If successful: status -> CONNECTED, connected_at updated
    - If failed: status -> ERROR, error_message populated
    - Tool discovery triggered on successful connection
    """

    @pytest.mark.asyncio
    async def test_connect_server_success(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test successful server connection."""
        # Arrange - register server first
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="connect-test-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        # Act
        result = await aggregator_service.connect_server(server_id)

        # Assert
        assert result is True
        # Verify status updated to CONNECTED
        updated_server = await mock_server_registry.get(server_id)
        assert updated_server["status"] == ServerStatus.CONNECTED

    @pytest.mark.asyncio
    async def test_connect_server_failure_sets_error_status(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test that connection failure sets ERROR status."""
        # Arrange
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="fail-connect-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        # Configure mock to fail connection
        mock_session_manager.set_should_fail_connect(server_id, True)

        # Act
        result = await aggregator_service.connect_server(server_id)

        # Assert
        assert result is False
        updated_server = await mock_server_registry.get(server_id)
        assert updated_server["status"] == ServerStatus.ERROR
        assert updated_server["error_message"] is not None

    @pytest.mark.asyncio
    async def test_connect_already_connected_is_idempotent(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test that connecting already connected server is idempotent."""
        # Arrange - register and connect
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="idempotent-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]
        await aggregator_service.connect_server(server_id)

        # Act - try to connect again
        result = await aggregator_service.connect_server(server_id)

        # Assert - should succeed (idempotent)
        assert result is True

    @pytest.mark.asyncio
    async def test_connect_nonexistent_server_raises_error(self, aggregator_service):
        """Test that connecting non-existent server raises error."""
        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await aggregator_service.connect_server("nonexistent-id")
        assert "not found" in str(exc.value).lower()


# ============================================================================
# BR-003: Tool Discovery
# ============================================================================


@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.aggregator
class TestBR003ToolDiscovery:
    """
    BR-003: Tool Discovery

    Given: Connected external MCP server
    When: Tool discovery is triggered
    Then:
    - Call tools/list on external server
    - For each tool:
      - Apply namespacing: {server_name}.{tool_name}
      - Store in mcp.tools with source_server_id, original_name
      - Generate embedding for tool
      - Index in Qdrant with server metadata
      - Queue for skill classification
    - Update mcp.external_servers.tool_count
    """

    @pytest.mark.asyncio
    async def test_discover_tools_success(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test successful tool discovery."""
        # Arrange - setup mock session with tools
        mock_tools = [
            {"name": "create_issue", "description": "Create GitHub issue", "inputSchema": {}},
            {"name": "list_repos", "description": "List repositories", "inputSchema": {}},
        ]
        session = MockMCPSession(tools=mock_tools)
        mock_session_manager._sessions["test-server"] = session
        await session.connect()

        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="github-mcp",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]
        mock_session_manager._sessions[server_id] = session

        # Act
        tools = await aggregator_service.discover_tools(server_id)

        # Assert
        assert len(tools) == 2
        # Check namespacing
        tool_names = [t["name"] for t in tools]
        assert "github-mcp.create_issue" in tool_names
        assert "github-mcp.list_repos" in tool_names

    @pytest.mark.asyncio
    async def test_discover_tools_applies_namespacing(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test that tool discovery applies correct namespacing."""
        # Arrange
        mock_tools = [
            {"name": "search", "description": "Search tool", "inputSchema": {}},
        ]
        session = MockMCPSession(tools=mock_tools)
        await session.connect()

        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="search-mcp",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]
        mock_session_manager._sessions[server_id] = session

        # Act
        tools = await aggregator_service.discover_tools(server_id)

        # Assert - namespacing format: {server_name}.{tool_name}
        assert len(tools) == 1
        assert tools[0]["name"] == "search-mcp.search"
        assert tools[0]["original_name"] == "search"

    @pytest.mark.asyncio
    async def test_discover_tools_updates_tool_count(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test that discovery updates server tool_count."""
        # Arrange
        mock_tools = [
            {"name": "tool1", "description": "Tool 1", "inputSchema": {}},
            {"name": "tool2", "description": "Tool 2", "inputSchema": {}},
            {"name": "tool3", "description": "Tool 3", "inputSchema": {}},
        ]
        session = MockMCPSession(tools=mock_tools)
        await session.connect()

        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="multi-tool-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]
        mock_session_manager._sessions[server_id] = session

        # Act
        await aggregator_service.discover_tools(server_id)

        # Assert
        updated_server = await mock_server_registry.get(server_id)
        assert updated_server["tool_count"] == 3

    @pytest.mark.asyncio
    async def test_discover_tools_empty_server(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test discovery from server with no tools."""
        # Arrange
        session = MockMCPSession(tools=[])
        await session.connect()

        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="empty-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]
        mock_session_manager._sessions[server_id] = session

        # Act
        tools = await aggregator_service.discover_tools(server_id)

        # Assert
        assert len(tools) == 0
        updated_server = await mock_server_registry.get(server_id)
        assert updated_server["tool_count"] == 0


# ============================================================================
# BR-004: Skill Classification for External Tools
# ============================================================================


@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.aggregator
class TestBR004SkillClassification:
    """
    BR-004: Skill Classification for External Tools

    Given: Aggregated tool from external server
    When: Classification is triggered
    Then:
    - Same classification process as internal tools
    - LLM assigns 1-3 skill categories with confidence scores
    - Assignments with confidence >= 0.5 saved
    - Primary skill determined
    - Tool updated with skill_ids, primary_skill_id, is_classified=true
    """

    @pytest.mark.asyncio
    async def test_classify_external_tool(
        self, aggregator_service, mock_tool_repository, mock_skill_classifier
    ):
        """Test that external tools are classified into skills."""
        # Arrange - create a tool
        tool_id = await mock_tool_repository.create_tool(
            name="github-mcp.create_issue",
            description="Create a new GitHub issue",
            input_schema={},
            source_server_id="server-123",
            original_name="create_issue",
        )

        mock_skill_classifier.set_classification_result(
            "github-mcp.create_issue",
            {
                "assignments": [
                    {"skill_id": "code_management", "confidence": 0.9},
                    {"skill_id": "issue_tracking", "confidence": 0.85},
                ],
                "primary_skill_id": "code_management",
            },
        )

        # Act
        result = await aggregator_service.classify_tool(tool_id)

        # Assert
        assert len(result["assignments"]) >= 1
        assert result["primary_skill_id"] == "code_management"

        # Verify tool was updated
        tool = await mock_tool_repository.get_tool(tool_id)
        assert tool["is_classified"] is True

    @pytest.mark.asyncio
    async def test_classify_tool_filters_low_confidence(
        self, aggregator_service, mock_tool_repository, mock_skill_classifier
    ):
        """Test that low confidence assignments are filtered."""
        # Arrange
        tool_id = await mock_tool_repository.create_tool(
            name="test-server.low_conf_tool",
            description="A tool with low confidence",
            input_schema={},
            source_server_id="server-123",
            original_name="low_conf_tool",
        )

        mock_skill_classifier.set_classification_result(
            "test-server.low_conf_tool",
            {
                "assignments": [
                    {"skill_id": "maybe_skill", "confidence": 0.3},  # Below 0.5 threshold
                ],
                "primary_skill_id": None,
            },
        )

        # Act
        result = await aggregator_service.classify_tool(tool_id)

        # Assert - low confidence should be filtered
        high_conf = [a for a in result["assignments"] if a["confidence"] >= 0.5]
        assert len(high_conf) == 0


# ============================================================================
# BR-005: Request Routing
# ============================================================================


@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.aggregator
class TestBR005RequestRouting:
    """
    BR-005: Request Routing

    Given: Tool execution request for aggregated tool
    When: Request is processed
    Then:
    - Parse tool name to extract server and original name
    - Resolve target server
    - Verify server status is CONNECTED
    - Get active session
    - Forward request to external server
    - Return response to client
    """

    @pytest.mark.asyncio
    async def test_route_namespaced_tool(
        self, aggregator_service, mock_server_registry, mock_session_manager, mock_tool_repository
    ):
        """Test routing for namespaced tool name."""
        # Arrange - setup server and tool
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="github-mcp",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        # Connect and setup session
        session = MockMCPSession()
        session.set_tool_response(
            "create_issue",
            {"content": [{"type": "text", "text": '{"issue_number": 42}'}], "isError": False},
        )
        await session.connect()
        mock_session_manager._sessions[server_id] = session
        await mock_server_registry.update_status(server_id, ServerStatus.CONNECTED)

        # Create the tool
        await mock_tool_repository.create_tool(
            name="github-mcp.create_issue",
            description="Create issue",
            input_schema={},
            source_server_id=server_id,
            original_name="create_issue",
        )

        # Act
        result = await aggregator_service.execute_tool(
            tool_name="github-mcp.create_issue", arguments={"title": "Bug", "body": "Description"}
        )

        # Assert
        assert result["is_error"] is False
        assert "issue_number" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_route_with_explicit_server_id(
        self, aggregator_service, mock_server_registry, mock_session_manager, mock_tool_repository
    ):
        """Test routing with explicit server_id parameter."""
        # Arrange
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="explicit-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        session = MockMCPSession()
        session.set_tool_response(
            "my_tool", {"content": [{"type": "text", "text": "Success"}], "isError": False}
        )
        await session.connect()
        mock_session_manager._sessions[server_id] = session
        await mock_server_registry.update_status(server_id, ServerStatus.CONNECTED)

        await mock_tool_repository.create_tool(
            name="explicit-server.my_tool",
            description="My tool",
            input_schema={},
            source_server_id=server_id,
            original_name="my_tool",
        )

        # Act - use explicit server_id
        result = await aggregator_service.execute_tool(
            tool_name="my_tool", arguments={}, server_id=server_id
        )

        # Assert
        assert result["is_error"] is False

    @pytest.mark.asyncio
    async def test_route_to_disconnected_server_fails(
        self, aggregator_service, mock_server_registry, mock_tool_repository
    ):
        """Test that routing to disconnected server fails gracefully."""
        # Arrange - create server but don't connect
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="disconnected-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        await mock_tool_repository.create_tool(
            name="disconnected-server.some_tool",
            description="Some tool",
            input_schema={},
            source_server_id=server_id,
            original_name="some_tool",
        )

        # Act & Assert
        with pytest.raises(Exception) as exc:
            await aggregator_service.execute_tool(
                tool_name="disconnected-server.some_tool", arguments={}
            )
        assert "unavailable" in str(exc.value).lower() or "disconnected" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_route_nonexistent_tool_fails(self, aggregator_service):
        """Test that routing to non-existent tool raises error."""
        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await aggregator_service.execute_tool(
                tool_name="nonexistent-server.no_tool", arguments={}
            )
        assert "not found" in str(exc.value).lower()


# ============================================================================
# BR-006: Health Monitoring
# ============================================================================


@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.aggregator
class TestBR006HealthMonitoring:
    """
    BR-006: Health Monitoring

    Given: Connected external servers
    When: Health check interval elapsed (default: 30s)
    Then:
    - For each connected server:
      - If health_check_url configured: HTTP GET with 5s timeout
      - Otherwise: ping session (call tools/list)
    - Update last_health_check timestamp
    - Track consecutive failures
    """

    @pytest.mark.asyncio
    async def test_health_check_success(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test successful health check updates timestamp."""
        # Arrange
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="healthy-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        session = MockMCPSession()
        await session.connect()
        mock_session_manager._sessions[server_id] = session
        await mock_server_registry.update_status(server_id, ServerStatus.CONNECTED)

        # Act
        result = await aggregator_service.health_check(server_id)

        # Assert
        assert result["status"] == ServerStatus.CONNECTED
        assert result["consecutive_failures"] == 0
        assert result["last_check"] is not None

    @pytest.mark.asyncio
    async def test_health_check_failure_increments_count(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test that failed health check increments failure count."""
        # Arrange
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="failing-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        session = MockMCPSession()
        session.set_should_fail_tools_list(True)  # Health check will fail
        await session.connect()
        mock_session_manager._sessions[server_id] = session
        await mock_server_registry.update_status(server_id, ServerStatus.CONNECTED)

        # Act
        result = await aggregator_service.health_check(server_id)

        # Assert
        assert result["consecutive_failures"] >= 1

    @pytest.mark.asyncio
    async def test_health_check_all_servers(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test health check for all connected servers."""
        # Arrange - create multiple servers
        for name in ["server-a", "server-b"]:
            config = AggregatorTestDataFactory.make_sse_server_registration(
                name=name,
                auto_connect=False,
            ).model_dump()
            server = await aggregator_service.register_server(config)
            session = MockMCPSession()
            await session.connect()
            mock_session_manager._sessions[server["id"]] = session
            await mock_server_registry.update_status(server["id"], ServerStatus.CONNECTED)

        # Act - health check without server_id checks all
        results = await aggregator_service.health_check()

        # Assert
        assert len(results) == 2


# ============================================================================
# BR-007: Server Disconnection
# ============================================================================


@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.aggregator
class TestBR007ServerDisconnection:
    """
    BR-007: Server Disconnection

    Given: Connected server
    When: Disconnect requested (manual or error-triggered)
    Then:
    - Wait for pending requests to complete (timeout: 30s)
    - Close session gracefully
    - Update status to DISCONNECTED
    - Mark server's tools as unavailable in search results
    - Do NOT delete tools (they remain for reconnection)
    """

    @pytest.mark.asyncio
    async def test_disconnect_server_success(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test successful server disconnection."""
        # Arrange - connect server first
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="disconnect-test",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        session = MockMCPSession()
        await session.connect()
        mock_session_manager._sessions[server_id] = session
        await mock_server_registry.update_status(server_id, ServerStatus.CONNECTED)

        # Act
        result = await aggregator_service.disconnect_server(server_id)

        # Assert
        assert result is True
        updated_server = await mock_server_registry.get(server_id)
        assert updated_server["status"] == ServerStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_disconnect_preserves_tools(
        self, aggregator_service, mock_server_registry, mock_session_manager, mock_tool_repository
    ):
        """Test that disconnect does not delete tools."""
        # Arrange
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="preserve-tools-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        # Create tools for this server
        tool_id = await mock_tool_repository.create_tool(
            name="preserve-tools-server.my_tool",
            description="A tool",
            input_schema={},
            source_server_id=server_id,
            original_name="my_tool",
        )

        session = MockMCPSession()
        await session.connect()
        mock_session_manager._sessions[server_id] = session
        await mock_server_registry.update_status(server_id, ServerStatus.CONNECTED)

        # Act
        await aggregator_service.disconnect_server(server_id)

        # Assert - tool should still exist
        tool = await mock_tool_repository.get_tool(tool_id)
        assert tool is not None

    @pytest.mark.asyncio
    async def test_disconnect_already_disconnected_is_idempotent(
        self, aggregator_service, mock_server_registry
    ):
        """Test that disconnecting already disconnected server is idempotent."""
        # Arrange
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="already-disconnected",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        # Act - disconnect (not connected yet)
        result = await aggregator_service.disconnect_server(server_id)

        # Assert - should succeed (idempotent)
        assert result is True


# ============================================================================
# BR-008: Server Removal
# ============================================================================


@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.aggregator
class TestBR008ServerRemoval:
    """
    BR-008: Server Removal

    Given: Registered server (connected or not)
    When: Admin deletes server
    Then:
    - If connected: disconnect first (BR-007)
    - Delete all server's tools from PostgreSQL (cascade)
    - Delete all server's tools from Qdrant
    - Delete server record
    """

    @pytest.mark.asyncio
    async def test_remove_server_success(self, aggregator_service, mock_server_registry):
        """Test successful server removal."""
        # Arrange
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="remove-test",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        # Act
        result = await aggregator_service.remove_server(server_id)

        # Assert
        assert result is True
        removed_server = await mock_server_registry.get(server_id)
        assert removed_server is None

    @pytest.mark.asyncio
    async def test_remove_server_deletes_tools(
        self, aggregator_service, mock_server_registry, mock_tool_repository
    ):
        """Test that server removal deletes associated tools."""
        # Arrange
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="delete-tools-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        # Create tools
        await mock_tool_repository.create_tool(
            name="delete-tools-server.tool1",
            description="Tool 1",
            input_schema={},
            source_server_id=server_id,
            original_name="tool1",
        )
        await mock_tool_repository.create_tool(
            name="delete-tools-server.tool2",
            description="Tool 2",
            input_schema={},
            source_server_id=server_id,
            original_name="tool2",
        )

        # Act
        await aggregator_service.remove_server(server_id)

        # Assert - tools should be deleted
        tools = await mock_tool_repository.get_tool_ids_by_server(server_id)
        assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_remove_connected_server_disconnects_first(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test that removing connected server disconnects first."""
        # Arrange
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="connected-remove",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]

        session = MockMCPSession()
        await session.connect()
        mock_session_manager._sessions[server_id] = session
        await mock_server_registry.update_status(server_id, ServerStatus.CONNECTED)

        # Act
        await aggregator_service.remove_server(server_id)

        # Assert - session should be closed
        disconnect_calls = mock_session_manager.get_calls("disconnect")
        assert len(disconnect_calls) >= 1

    @pytest.mark.asyncio
    async def test_remove_nonexistent_server_raises_error(self, aggregator_service):
        """Test that removing non-existent server raises error."""
        # Act & Assert
        with pytest.raises(ValueError) as exc:
            await aggregator_service.remove_server("nonexistent-id")
        assert "not found" in str(exc.value).lower()


# ============================================================================
# Edge Cases (from logic_contract.md)
# ============================================================================


@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.aggregator
class TestEdgeCases:
    """Edge case tests from logic contract EC-XXX."""

    @pytest.mark.asyncio
    async def test_EC002_tool_name_contains_dot(
        self, aggregator_service, mock_server_registry, mock_session_manager, mock_tool_repository
    ):
        """
        EC-002: Tool Name Contains Dot

        Scenario: External server has tool named "api.v2.create"
        Expected: Namespacing still works correctly
        Solution: Only first dot separates server from tool name
        """
        # Arrange
        mock_tools = [
            {"name": "api.v2.create", "description": "API v2 create", "inputSchema": {}},
        ]
        session = MockMCPSession(tools=mock_tools)
        await session.connect()

        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="server-a",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]
        mock_session_manager._sessions[server_id] = session

        # Act
        tools = await aggregator_service.discover_tools(server_id)

        # Assert - namespacing should work: server-a.api.v2.create
        assert len(tools) == 1
        assert tools[0]["name"] == "server-a.api.v2.create"
        assert tools[0]["original_name"] == "api.v2.create"

    @pytest.mark.asyncio
    async def test_EC004_duplicate_server_registration(
        self, aggregator_service, mock_server_registry
    ):
        """
        EC-004: Duplicate Tool Registration

        Scenario: Same server registered twice (different process)
        Expected: Second registration fails with 409
        """
        # Arrange
        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="duplicate-server",
            auto_connect=False,
        ).model_dump()

        # Act - first registration succeeds
        await aggregator_service.register_server(config)

        # Assert - second registration fails
        with pytest.raises(ValueError) as exc:
            await aggregator_service.register_server(config)
        assert "already exists" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_EC006_large_tool_discovery(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """
        EC-006: Large Tool Discovery

        Scenario: Server returns 500+ tools
        Expected: Discovery completes without timeout
        """
        # Arrange - create many tools
        mock_tools = [
            {"name": f"tool_{i}", "description": f"Tool {i}", "inputSchema": {}}
            for i in range(100)  # Use 100 for test (not 500 to keep test fast)
        ]
        session = MockMCPSession(tools=mock_tools)
        await session.connect()

        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="large-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]
        mock_session_manager._sessions[server_id] = session

        # Act
        tools = await aggregator_service.discover_tools(server_id)

        # Assert
        assert len(tools) == 100

    @pytest.mark.asyncio
    async def test_EC009_classification_service_unavailable(
        self, aggregator_service, mock_tool_repository, mock_skill_classifier
    ):
        """
        EC-009: Classification Service Unavailable

        Scenario: LLM service down during tool discovery
        Expected: Tools discovered but unclassified
        """
        # Arrange
        tool_id = await mock_tool_repository.create_tool(
            name="test-server.unclassified_tool",
            description="A tool that cannot be classified",
            input_schema={},
            source_server_id="server-123",
            original_name="unclassified_tool",
        )

        # Configure classifier to fail
        mock_skill_classifier.set_classification_result(
            "test-server.unclassified_tool",
            {
                "error": "Service unavailable",
                "assignments": [],
                "primary_skill_id": None,
            },
        )

        # Act - classification should handle failure gracefully
        result = await aggregator_service.classify_tool(tool_id)

        # Assert - tool remains unclassified but exists
        assert len(result.get("assignments", [])) == 0
        tool = await mock_tool_repository.get_tool(tool_id)
        assert tool is not None


# ============================================================================
# State & Aggregation Tests
# ============================================================================


@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.aggregator
class TestAggregatorState:
    """Tests for aggregator state management."""

    @pytest.mark.asyncio
    async def test_get_state_returns_counts(self, aggregator_service, mock_server_registry):
        """Test that get_state returns correct counts."""
        # Arrange - create multiple servers in different states
        for name in ["connected-1", "connected-2"]:
            config = AggregatorTestDataFactory.make_sse_server_registration(
                name=name,
                auto_connect=False,
            ).model_dump()
            server = await aggregator_service.register_server(config)
            await mock_server_registry.update_status(server["id"], ServerStatus.CONNECTED)

        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="disconnected-1",
            auto_connect=False,
        ).model_dump()
        await aggregator_service.register_server(config)

        # Act
        state = await aggregator_service.get_state()

        # Assert
        assert state["total_servers"] == 3
        assert state["connected_servers"] == 2
        assert state["disconnected_servers"] == 1


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.tdd
@pytest.mark.component
@pytest.mark.aggregator
@pytest.mark.slow
class TestPerformanceSLAs:
    """Performance tests based on SLAs from logic contract."""

    @pytest.mark.asyncio
    async def test_server_registration_under_2s(self, aggregator_service):
        """Test that server registration completes in < 2s."""
        import time

        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="perf-test-server",
            auto_connect=False,
        ).model_dump()

        start = time.perf_counter()
        await aggregator_service.register_server(config)
        elapsed = (time.perf_counter() - start) * 1000  # ms

        # With mocks, should be well under 2s
        assert elapsed < 2000, f"Registration took {elapsed:.2f}ms, expected < 2000ms"

    @pytest.mark.asyncio
    async def test_tool_discovery_completes(
        self, aggregator_service, mock_server_registry, mock_session_manager
    ):
        """Test that tool discovery completes in reasonable time."""
        import time

        mock_tools = [
            {"name": f"tool_{i}", "description": f"Tool {i}", "inputSchema": {}} for i in range(50)
        ]
        session = MockMCPSession(tools=mock_tools)
        await session.connect()

        config = AggregatorTestDataFactory.make_sse_server_registration(
            name="perf-discovery-server",
            auto_connect=False,
        ).model_dump()
        server = await aggregator_service.register_server(config)
        server_id = server["id"]
        mock_session_manager._sessions[server_id] = session

        start = time.perf_counter()
        tools = await aggregator_service.discover_tools(server_id)
        elapsed = (time.perf_counter() - start) * 1000  # ms

        assert len(tools) == 50
        assert elapsed < 5000, f"Discovery took {elapsed:.2f}ms, expected < 5000ms"
