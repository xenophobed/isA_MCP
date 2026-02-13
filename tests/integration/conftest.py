"""
Integration layer test configuration and fixtures.

Layer 2: Service Integration Tests
- Tests service-to-service interactions
- Uses real database, mocked external APIs
- Tests event chains and business flows
"""

import pytest
from typing import AsyncGenerator
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# Database Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
async def clean_db(db_pool) -> AsyncGenerator:
    """
    Provide a clean database state for each test.

    Truncates test tables before and after each test.
    """
    # Clean before test
    async with db_pool.acquire() as conn:
        await conn.execute("""
            TRUNCATE TABLE mcp_tools, mcp_prompts, mcp_resources CASCADE;
        """)

    yield db_pool

    # Clean after test
    async with db_pool.acquire() as conn:
        await conn.execute("""
            TRUNCATE TABLE mcp_tools, mcp_prompts, mcp_resources CASCADE;
        """)


@pytest.fixture
async def seeded_db(clean_db) -> AsyncGenerator:
    """
    Database with seed data for testing.
    """
    async with clean_db.acquire() as conn:
        # Insert seed tools
        await conn.execute("""
            INSERT INTO mcp_tools (name, description, input_schema, category)
            VALUES
                ('test_tool_1', 'First test tool', '{}', 'utility'),
                ('test_tool_2', 'Second test tool', '{}', 'intelligence'),
                ('test_tool_3', 'Third test tool', '{}', 'web');
        """)

        # Insert seed prompts
        await conn.execute("""
            INSERT INTO mcp_prompts (name, description, template, arguments)
            VALUES
                ('test_prompt_1', 'First test prompt', 'Template 1', '[]'),
                ('test_prompt_2', 'Second test prompt', 'Template 2', '[]');
        """)

    yield clean_db


# ═══════════════════════════════════════════════════════════════
# Qdrant Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
async def clean_qdrant(qdrant_client) -> AsyncGenerator:
    """
    Provide a clean Qdrant state for each test.

    Recreates test collections before each test.
    """
    test_collections = ["mcp_tools_test", "mcp_prompts_test", "mcp_resources_test"]

    # Delete existing test collections
    for collection in test_collections:
        try:
            qdrant_client.delete_collection(collection)
        except Exception:
            pass  # Collection might not exist

    # Create fresh collections
    from qdrant_client.models import Distance, VectorParams

    for collection in test_collections:
        qdrant_client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )

    yield qdrant_client

    # Cleanup after test
    for collection in test_collections:
        try:
            qdrant_client.delete_collection(collection)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# Service Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
async def discovery_service(clean_db, temp_tools_dir):
    """Provide auto-discovery service for testing."""
    from core.auto_discovery import AutoDiscovery

    service = AutoDiscovery(tools_dir=temp_tools_dir, db_pool=clean_db)
    return service


@pytest.fixture
async def sync_service(clean_db, clean_qdrant):
    """Provide sync service for testing."""
    from services.sync_service import SyncService

    service = SyncService(db_pool=clean_db, qdrant_client=clean_qdrant)
    return service


@pytest.fixture
async def search_service(clean_db, clean_qdrant):
    """Provide search service for testing."""
    from services.search_service import SearchService

    service = SearchService(db_pool=clean_db, qdrant_client=clean_qdrant)
    return service


# ═══════════════════════════════════════════════════════════════
# Event/Flow Fixtures
# ═══════════════════════════════════════════════════════════════


class EventCollector:
    """Collect events for testing event-driven flows."""

    def __init__(self):
        self.events = []

    def record(self, event_type: str, data: dict):
        """Record an event."""
        self.events.append({"type": event_type, "data": data})

    def get_events(self, event_type: str = None) -> list:
        """Get recorded events, optionally filtered by type."""
        if event_type:
            return [e for e in self.events if e["type"] == event_type]
        return self.events

    def clear(self):
        """Clear recorded events."""
        self.events = []

    async def wait_for_event(self, event_type: str, timeout: float = 5.0):
        """Wait for a specific event type."""
        import asyncio

        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            events = self.get_events(event_type)
            if events:
                return events[0]
            await asyncio.sleep(0.1)
        return None


@pytest.fixture
def event_collector():
    """Provide event collector for flow testing."""
    return EventCollector()


# ═══════════════════════════════════════════════════════════════
# Test Tool Files
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def populated_tools_dir(temp_tools_dir) -> Path:
    """Create a tools directory with sample tool files."""

    # Create intelligence tool
    (temp_tools_dir / "text_tool.py").write_text('''
from mcp import mcp

@mcp.tool()
async def text_generator(prompt: str, max_tokens: int = 100) -> str:
    """Generate text based on a prompt.

    Args:
        prompt: The input prompt
        max_tokens: Maximum tokens to generate
    """
    return f"Generated: {prompt[:max_tokens]}"
''')

    # Create web tool
    (temp_tools_dir / "web_tool.py").write_text('''
from mcp import mcp

@mcp.tool()
async def web_fetch(url: str) -> dict:
    """Fetch content from a URL.

    Args:
        url: The URL to fetch
    """
    return {"url": url, "content": "Sample content"}
''')

    # Create utility tool
    (temp_tools_dir / "util_tool.py").write_text('''
from mcp import mcp

@mcp.tool()
async def calculator(expression: str) -> float:
    """Evaluate a mathematical expression.

    Args:
        expression: The math expression to evaluate
    """
    return eval(expression)
''')

    return temp_tools_dir


@pytest.fixture
def populated_prompts_dir(temp_prompts_dir) -> Path:
    """Create a prompts directory with sample prompt files."""

    (temp_prompts_dir / "assistant_prompt.py").write_text('''
from mcp import mcp

@mcp.prompt()
def assistant_prompt(task: str, context: str = "") -> str:
    """General assistant prompt.

    Args:
        task: The task to perform
        context: Additional context
    """
    return f"You are a helpful assistant. Task: {task}. Context: {context}"
''')

    (temp_prompts_dir / "coder_prompt.py").write_text('''
from mcp import mcp

@mcp.prompt()
def coder_prompt(language: str, task: str) -> str:
    """Coding assistant prompt.

    Args:
        language: Programming language
        task: Coding task
    """
    return f"You are an expert {language} developer. Task: {task}"
''')

    return temp_prompts_dir
