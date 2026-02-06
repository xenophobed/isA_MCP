"""
Component layer test configuration and fixtures.

Layer 3: Component Tests
- Tests individual service/repository methods
- Uses mocked dependencies (DB, Qdrant, external APIs)
- Fast execution with controlled inputs
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ═══════════════════════════════════════════════════════════════
# Service Mocks
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_tool_service():
    """Mock tool service."""
    service = AsyncMock()
    service.get_tool = AsyncMock(return_value=None)
    service.get_all_tools = AsyncMock(return_value=[])
    service.search_tools = AsyncMock(return_value=[])
    service.execute_tool = AsyncMock(return_value={"result": "success"})
    service.register_tool = AsyncMock()
    return service


@pytest.fixture
def mock_prompt_service():
    """Mock prompt service."""
    service = AsyncMock()
    service.get_prompt = AsyncMock(return_value=None)
    service.get_all_prompts = AsyncMock(return_value=[])
    service.render_prompt = AsyncMock(return_value="Rendered prompt")
    service.register_prompt = AsyncMock()
    return service


@pytest.fixture
def mock_resource_service():
    """Mock resource service."""
    service = AsyncMock()
    service.get_resource = AsyncMock(return_value=None)
    service.get_all_resources = AsyncMock(return_value=[])
    service.read_resource = AsyncMock(return_value={"content": "data"})
    service.register_resource = AsyncMock()
    return service


@pytest.fixture
def mock_search_service():
    """Mock search service."""
    service = AsyncMock()
    service.search_tools = AsyncMock(return_value=[])
    service.search_prompts = AsyncMock(return_value=[])
    service.search_resources = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_sync_service():
    """Mock sync service."""
    service = AsyncMock()
    service.sync_tools = AsyncMock()
    service.sync_prompts = AsyncMock()
    service.sync_resources = AsyncMock()
    service.sync_all = AsyncMock()
    service.check_needs_sync = AsyncMock(return_value=False)
    return service


@pytest.fixture
def mock_progress_manager():
    """Mock progress manager."""
    manager = AsyncMock()
    manager.start = AsyncMock(return_value="progress_123")
    manager.update = AsyncMock()
    manager.complete = AsyncMock()
    manager.fail = AsyncMock()
    manager.get_status = AsyncMock(return_value={"status": "running"})
    return manager


# ═══════════════════════════════════════════════════════════════
# Repository Mocks
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_tool_repo(mock_db_pool):
    """Mock tool repository."""
    repo = AsyncMock()
    repo.db_pool = mock_db_pool
    repo.get_by_name = AsyncMock(return_value=None)
    repo.get_all = AsyncMock(return_value=[])
    repo.upsert = AsyncMock()
    repo.delete = AsyncMock()
    repo.check_needs_sync = AsyncMock(return_value=False)
    return repo


@pytest.fixture
def mock_prompt_repo(mock_db_pool):
    """Mock prompt repository."""
    repo = AsyncMock()
    repo.db_pool = mock_db_pool
    repo.get_by_name = AsyncMock(return_value=None)
    repo.get_all = AsyncMock(return_value=[])
    repo.upsert = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_resource_repo(mock_db_pool):
    """Mock resource repository."""
    repo = AsyncMock()
    repo.db_pool = mock_db_pool
    repo.get_by_uri = AsyncMock(return_value=None)
    repo.get_all = AsyncMock(return_value=[])
    repo.upsert = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_vector_repo(mock_qdrant_client):
    """Mock vector repository."""
    repo = AsyncMock()
    repo.qdrant = mock_qdrant_client
    repo.upsert_embedding = AsyncMock()
    repo.search = AsyncMock(return_value=[])
    repo.delete = AsyncMock()
    return repo


# ═══════════════════════════════════════════════════════════════
# Client Mocks
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_postgres_client(mock_db_pool):
    """Mock PostgreSQL client."""
    client = MagicMock()
    client.pool = mock_db_pool
    client.execute = AsyncMock()
    client.fetch = AsyncMock(return_value=[])
    client.fetchrow = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_qdrant_manager(mock_qdrant_client):
    """Mock Qdrant manager."""
    manager = MagicMock()
    manager.client = mock_qdrant_client
    manager.search = AsyncMock(return_value=[])
    manager.upsert = AsyncMock()
    manager.create_collection = AsyncMock()
    return manager


# ═══════════════════════════════════════════════════════════════
# Auth Mocks
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_auth_service():
    """Mock authentication service."""
    service = AsyncMock()
    service.validate_token = AsyncMock(return_value=True)
    service.get_user_from_token = AsyncMock(return_value={
        "user_id": "test_user",
        "email": "test@example.com",
        "roles": ["user"]
    })
    service.validate_api_key = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_auth_middleware(mock_auth_service):
    """Mock authentication middleware."""
    middleware = MagicMock()
    middleware.auth_service = mock_auth_service
    middleware.authenticate = AsyncMock(return_value={
        "authenticated": True,
        "user_id": "test_user"
    })
    return middleware


@pytest.fixture
def mock_authorization_client():
    """Mock authorization client."""
    client = AsyncMock()
    client.check_permission = AsyncMock(return_value=True)
    client.get_user_permissions = AsyncMock(return_value=["read", "write"])
    client.authorize_tool_access = AsyncMock(return_value=True)
    return client


# ═══════════════════════════════════════════════════════════════
# Intelligence Service Mocks
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_text_generator():
    """Mock text generator."""
    generator = AsyncMock()
    generator.generate = AsyncMock(return_value="Generated text content")
    generator.generate_with_context = AsyncMock(return_value="Context-aware text")
    return generator


@pytest.fixture
def mock_embedding_generator():
    """Mock embedding generator."""
    generator = AsyncMock()
    generator.generate = AsyncMock(return_value=[0.1] * 1536)
    generator.generate_batch = AsyncMock(return_value=[[0.1] * 1536])
    return generator


@pytest.fixture
def mock_vision_analyzer():
    """Mock vision analyzer."""
    analyzer = AsyncMock()
    analyzer.analyze = AsyncMock(return_value={
        "description": "Image description",
        "objects": ["object1", "object2"],
        "text": []
    })
    analyzer.ocr = AsyncMock(return_value={"text": "Extracted text"})
    return analyzer


@pytest.fixture
def mock_audio_analyzer():
    """Mock audio analyzer."""
    analyzer = AsyncMock()
    analyzer.transcribe = AsyncMock(return_value={"text": "Transcribed audio"})
    analyzer.analyze = AsyncMock(return_value={"duration": 10, "language": "en"})
    return analyzer


# ═══════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════

def create_mock_tool(name: str = "test_tool", **kwargs):
    """Create a mock tool object."""
    default = {
        "name": name,
        "description": f"Description for {name}",
        "category": "utility",
        "input_schema": {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            },
            "required": ["input"]
        },
        "is_active": True
    }
    default.update(kwargs)
    return default


def create_mock_prompt(name: str = "test_prompt", **kwargs):
    """Create a mock prompt object."""
    default = {
        "name": name,
        "description": f"Description for {name}",
        "template": "This is a template for {input}",
        "arguments": [
            {"name": "input", "description": "Input argument", "required": True}
        ]
    }
    default.update(kwargs)
    return default


def create_mock_resource(uri: str = "resource://test/1", **kwargs):
    """Create a mock resource object."""
    default = {
        "uri": uri,
        "name": "test_resource",
        "description": "A test resource",
        "mime_type": "application/json"
    }
    default.update(kwargs)
    return default


@pytest.fixture
def mock_creators():
    """Provide mock object creators."""
    return {
        "tool": create_mock_tool,
        "prompt": create_mock_prompt,
        "resource": create_mock_resource
    }
