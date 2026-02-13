"""
Global pytest configuration and shared fixtures for isA_MCP tests.

This file provides:
- Event loop configuration for async tests
- Mock fixtures for database, Qdrant, and model clients
- Real client fixtures for integration tests
- Configuration loading via core/config
- Golden test utilities
- Common utilities and helpers

Test Structure:
- golden/    -> Characterization tests (DO NOT MODIFY)
- services/  -> TDD tests (new features)

Configuration:
- Uses core/config for centralized configuration
- Set ENV=test to load deployment/test/config/.env.test
- For integration tests, ensure port-forwarded K8s services are available
"""

import pytest
import asyncio
import sys
import os
from typing import AsyncGenerator, Generator
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set test environment BEFORE importing core/config
# This ensures the correct .env file is loaded
os.environ.setdefault("ENV", "test")

# Load configuration via core/config (centralized config system)
try:
    from core.config import get_settings, reload_settings, MCPConfig

    # Reload to ensure test config is loaded
    _settings = reload_settings()
    CONFIG_AVAILABLE = True
except ImportError as e:
    CONFIG_AVAILABLE = False
    _settings = None
    print(f"Warning: Could not load core/config: {e}")

# Import mocks (created in component/mocks/)
try:
    from tests.component.mocks.db_mock import MockAsyncpgPool
    from tests.component.mocks.qdrant_mock import MockQdrantClient
    from tests.component.mocks.model_client_mock import MockModelClient
    from tests.component.mocks.minio_mock import MockMinioClient
    from tests.component.mocks.redis_mock import MockRedisClient
except ImportError:
    # Mocks not yet created, will be available after setup
    MockAsyncpgPool = None
    MockQdrantClient = None
    MockModelClient = None
    MockMinioClient = None
    MockRedisClient = None


# ═══════════════════════════════════════════════════════════════
# Event Loop Configuration
# ═══════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ═══════════════════════════════════════════════════════════════
# Mock Fixtures (for unit and component tests)
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def mock_db_pool():
    """Provide mock database pool for testing."""
    if MockAsyncpgPool is None:
        pytest.skip("MockAsyncpgPool not available")
    return MockAsyncpgPool()


@pytest.fixture
def mock_qdrant_client():
    """Provide mock Qdrant client for testing."""
    if MockQdrantClient is None:
        pytest.skip("MockQdrantClient not available")
    return MockQdrantClient()


@pytest.fixture
def mock_model_client():
    """Provide mock model client for testing."""
    if MockModelClient is None:
        pytest.skip("MockModelClient not available")
    return MockModelClient()


@pytest.fixture
def mock_minio_client():
    """Provide mock MinIO client for testing."""
    if MockMinioClient is None:
        pytest.skip("MockMinioClient not available")
    return MockMinioClient()


@pytest.fixture
def mock_redis_client():
    """Provide mock Redis client for testing."""
    if MockRedisClient is None:
        pytest.skip("MockRedisClient not available")
    return MockRedisClient()


# ═══════════════════════════════════════════════════════════════
# Real Client Fixtures (for integration tests)
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
async def db_pool() -> AsyncGenerator:
    """
    Real database pool for integration tests.

    Requires:
        - PostgreSQL running
        - TEST_DATABASE_URL environment variable set
    """
    import asyncpg

    database_url = os.getenv(
        "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/isa_mcp_test"
    )

    try:
        pool = await asyncpg.create_pool(database_url)
        yield pool
        await pool.close()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.fixture
async def qdrant_client() -> AsyncGenerator:
    """
    Real Qdrant client for integration tests.

    Requires:
        - Qdrant running
        - TEST_QDRANT_URL environment variable set
    """
    try:
        from qdrant_client import QdrantClient

        qdrant_url = os.getenv("TEST_QDRANT_URL", "http://localhost:6333")
        client = QdrantClient(url=qdrant_url)
        yield client
        client.close()
    except Exception as e:
        pytest.skip(f"Qdrant not available: {e}")


@pytest.fixture
async def mcp_client() -> AsyncGenerator:
    """
    MCP client for API tests.

    Requires:
        - MCP server running
        - TEST_MCP_URL environment variable set
    """
    try:
        import httpx

        mcp_url = os.getenv("TEST_MCP_URL", "http://localhost:8000")
        async with httpx.AsyncClient(base_url=mcp_url) as client:
            yield client
    except Exception as e:
        pytest.skip(f"MCP server not available: {e}")


# ═══════════════════════════════════════════════════════════════
# Environment & Configuration Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def mcp_settings() -> MCPConfig:
    """
    Provide MCPConfig from core/config for integration tests.

    This fixture loads the centralized configuration from:
    - deployment/test/config/.env.test (when ENV=test)

    Usage:
        def test_something(mcp_settings):
            assert mcp_settings.isa_service_url == "http://localhost:8082"
    """
    if not CONFIG_AVAILABLE:
        pytest.skip("core/config not available")
    return get_settings()


@pytest.fixture
def test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MCP_API_KEY", "test_api_key_12345")
    return {"ENV": "test", "LOG_LEVEL": "DEBUG", "MCP_API_KEY": "test_api_key_12345"}


@pytest.fixture
def test_config(mcp_settings):
    """
    Provide test configuration dict from MCPConfig.

    This is a convenience fixture that extracts commonly used
    config values into a simple dict format.
    """
    if not CONFIG_AVAILABLE:
        # Fallback for when core/config is not available
        return {
            "database_url": "postgresql://test:test@localhost:5432/test",
            "qdrant_url": "http://localhost:6333",
            "minio_url": "http://localhost:9000",
            "redis_url": "redis://localhost:6379",
            "model_service_url": "http://localhost:8082",
            "mcp_url": "http://localhost:8081",
        }

    return {
        "database_url": os.getenv(
            "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        ),
        "qdrant_url": mcp_settings.infrastructure.qdrant_url or "http://localhost:6333",
        "qdrant_grpc_host": mcp_settings.infrastructure.qdrant_grpc_host,
        "qdrant_grpc_port": mcp_settings.infrastructure.qdrant_grpc_port,
        "postgres_grpc_host": mcp_settings.infrastructure.postgres_grpc_host,
        "postgres_grpc_port": mcp_settings.infrastructure.postgres_grpc_port,
        "minio_endpoint": mcp_settings.infrastructure.minio_endpoint or "localhost:9000",
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "model_service_url": mcp_settings.isa_service_url,
        "mcp_url": f"http://localhost:{mcp_settings.port}",
        "db_schema": mcp_settings.db_schema,
    }


@pytest.fixture
def legacy_test_config():
    """Provide legacy test configuration (deprecated, use test_config instead)."""
    return {
        "database_url": "postgresql://test:test@localhost:5432/test",
        "qdrant_url": "http://localhost:6333",
        "minio_url": "http://localhost:9000",
        "redis_url": "redis://localhost:6379",
        "model_service_url": "http://localhost:8001",
    }


# ═══════════════════════════════════════════════════════════════
# Temporary File/Directory Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def temp_tools_dir(tmp_path) -> Path:
    """Create temporary directory for tool files."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    return tools_dir


@pytest.fixture
def temp_prompts_dir(tmp_path) -> Path:
    """Create temporary directory for prompt files."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    return prompts_dir


@pytest.fixture
def temp_resources_dir(tmp_path) -> Path:
    """Create temporary directory for resource files."""
    resources_dir = tmp_path / "resources"
    resources_dir.mkdir()
    return resources_dir


# ═══════════════════════════════════════════════════════════════
# Sample Data Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def sample_tool_source():
    """Provide sample tool source code."""
    return '''
from mcp import mcp

@mcp.tool()
async def sample_tool(input_text: str, max_length: int = 100) -> str:
    """
    A sample tool for testing.

    Args:
        input_text: The input text to process
        max_length: Maximum length of output

    Returns:
        Processed text output
    """
    return input_text[:max_length]
'''


@pytest.fixture
def sample_prompt_source():
    """Provide sample prompt source code."""
    return '''
from mcp import mcp

@mcp.prompt()
def sample_prompt(topic: str, style: str = "professional") -> str:
    """
    A sample prompt for testing.

    Args:
        topic: The topic to write about
        style: The writing style
    """
    return f"Write a {style} article about {topic}."
'''


@pytest.fixture
def sample_resource_source():
    """Provide sample resource source code."""
    return '''
from mcp import mcp

@mcp.resource("resource://sample/{id}")
async def sample_resource(id: str) -> dict:
    """
    A sample resource for testing.

    Args:
        id: The resource identifier
    """
    return {"id": id, "content": "Sample content"}
'''


# ═══════════════════════════════════════════════════════════════
# Utility Functions
# ═══════════════════════════════════════════════════════════════


def assert_valid_tool_schema(schema: dict):
    """Assert that a tool schema is valid."""
    assert "type" in schema
    assert schema["type"] == "object"
    assert "properties" in schema


def assert_valid_mcp_response(response: dict):
    """Assert that an MCP response is valid JSON-RPC 2.0."""
    assert "jsonrpc" in response
    assert response["jsonrpc"] == "2.0"
    assert "result" in response or "error" in response


def create_test_tool_file(path: Path, name: str, description: str = "Test tool"):
    """Create a test tool file."""
    content = f'''
from mcp import mcp

@mcp.tool()
async def {name}(input: str) -> str:
    """{description}"""
    return f"Processed: {{input}}"
'''
    file_path = path / f"{name}.py"
    file_path.write_text(content)
    return file_path
