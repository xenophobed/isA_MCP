# Shared System Contract

**How to Test - isA MCP Server TDD Methodology**

This document defines HOW to test the isA MCP platform. It specifies test organization, markers, fixtures, and workflow for all services.

---

## Test Layers

### 1. Unit Tests (`tests/unit/`)
**Purpose**: Test pure logic in isolation
**Dependencies**: None (no mocks, no I/O)
**Speed**: < 1ms per test
**Markers**: `@pytest.mark.unit`

```python
@pytest.mark.unit
def test_validation_logic():
    """Test pure validation without dependencies."""
    assert validate_skill_id("calendar_management") is True
    assert validate_skill_id("123_invalid") is False
```

### 2. Component Tests (`tests/component/`)
**Purpose**: Test service classes with mocked dependencies
**Dependencies**: Mocked (MockQdrantClient, MockAsyncpgPool, MockModelClient)
**Speed**: < 100ms per test
**Markers**: `@pytest.mark.component`

```python
@pytest.mark.component
@pytest.mark.asyncio
async def test_skill_classification(mock_model_client, mock_qdrant_client):
    """Test skill classification with mocked LLM and vector DB."""
    service = SkillService(model_client=mock_model_client, qdrant=mock_qdrant_client)
    result = await service.classify_tool(tool)
    assert result.primary_skill_id is not None
```

### 3. Integration Tests (`tests/integration/`)
**Purpose**: Test service interactions with real or port-forwarded services
**Dependencies**: Real databases (via port-forward to K8s)
**Speed**: < 5s per test
**Markers**: `@pytest.mark.integration`

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_skill_sync_integration(db_pool, qdrant_client):
    """Test skill sync with real Qdrant and PostgreSQL."""
    # Requires: kubectl port-forward svc/qdrant 6333:6333
    result = await sync_tools_with_skills(db_pool, qdrant_client)
    assert result.synced_count > 0
```

### 4. API Tests (`tests/api/`)
**Purpose**: Test HTTP endpoints with real server
**Dependencies**: Running MCP server
**Speed**: < 1s per test
**Markers**: `@pytest.mark.api`

```python
@pytest.mark.api
@pytest.mark.asyncio
async def test_search_api(mcp_client):
    """Test hierarchical search API endpoint."""
    response = await mcp_client.post("/api/v1/search", json={"query": "schedule meeting"})
    assert response.status_code == 200
```

### 5. Smoke Tests (`tests/smoke/`)
**Purpose**: Quick sanity checks for deployment validation
**Dependencies**: Full production-like environment
**Speed**: < 30s total
**Markers**: `@pytest.mark.smoke`

---

## Directory Structure

```
tests/
├── conftest.py                     # Global fixtures
├── pytest.ini                      # Pytest configuration
│
├── contracts/                      # Data + Logic contracts
│   ├── README.md
│   ├── shared_system_contract.md   # This file
│   ├── skill/
│   │   ├── __init__.py
│   │   ├── data_contract.py
│   │   └── logic_contract.md
│   └── search/
│       ├── __init__.py
│       ├── data_contract.py
│       └── logic_contract.md
│
├── fixtures/                       # Shared test data
│   ├── __init__.py
│   ├── factories.py
│   ├── generators.py
│   └── sample_requests.py
│
├── unit/
│   ├── conftest.py
│   └── golden/                     # Characterization tests
│
├── component/
│   ├── conftest.py
│   ├── mocks/                      # Mock implementations
│   │   ├── __init__.py
│   │   ├── db_mock.py
│   │   ├── qdrant_mock.py
│   │   └── model_client_mock.py
│   ├── golden/                     # Characterization tests
│   └── services/                   # TDD tests
│       ├── skill/
│       │   └── test_skill_service_tdd.py
│       └── search/
│           └── test_hierarchical_search_tdd.py
│
├── integration/
│   ├── conftest.py
│   └── services/
│       ├── skill/
│       │   └── test_skill_sync_integration.py
│       └── search/
│           └── test_search_integration.py
│
├── api/
│   ├── conftest.py
│   └── services/
│       ├── skill/
│       │   └── test_skill_api.py
│       └── search/
│           └── test_search_api.py
│
└── smoke/
    └── api/
        └── skill_search_test.sh
```

---

## Test Naming Conventions

### Golden Tests (Characterization)
```
test_{component}_{behavior}_golden.py
test_search_service_golden.py
```

### TDD Tests (New Features)
```
test_{component}_{feature}_tdd.py
test_skill_service_tdd.py
test_hierarchical_search_tdd.py
```

### Test Function Names
```python
def test_BR001_skill_category_creation():
    """Map to Business Rule BR-001"""

def test_EC001_concurrent_classification():
    """Map to Edge Case EC-001"""

def test_happy_path_search():
    """Standard happy path test"""
```

---

## Pytest Markers

Configure in `pytest.ini`:

```ini
[pytest]
markers =
    unit: Unit tests (no dependencies)
    component: Component tests (mocked dependencies)
    integration: Integration tests (real services)
    api: API endpoint tests
    smoke: Smoke tests for deployment
    golden: Characterization/golden tests (do not modify)
    tdd: Test-driven development tests
    slow: Tests taking > 1 second
    skill: Skill service tests
    search: Search service tests
```

---

## Running Tests

### By Layer
```bash
# All tests
pytest tests/ -v

# By layer
pytest tests/unit/ -v
pytest tests/component/ -v
pytest tests/integration/ -v
pytest tests/api/ -v

# By marker
pytest -m unit
pytest -m component
pytest -m integration
pytest -m api
pytest -m smoke
```

### By Type
```bash
# Golden tests only (characterization)
pytest -m golden

# TDD tests only (new features)
pytest -m tdd

# Skip slow tests
pytest -m "not slow"
```

### By Service
```bash
# Skill service tests
pytest tests/*/services/skill/ -v
pytest -m skill

# Search service tests
pytest tests/*/services/search/ -v
pytest -m search
```

### With Coverage
```bash
pytest --cov=services --cov-report=html tests/
```

---

## Fixtures

### Mock Fixtures (component tests)
```python
@pytest.fixture
def mock_db_pool():
    """Mock asyncpg pool."""
    return MockAsyncpgPool()

@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client."""
    return MockQdrantClient()

@pytest.fixture
def mock_model_client():
    """Mock model client for embeddings/LLM."""
    return MockModelClient()
```

### Real Fixtures (integration tests)
```python
@pytest.fixture
async def db_pool():
    """Real PostgreSQL pool (requires port-forward)."""
    pool = await asyncpg.create_pool(os.getenv("TEST_DATABASE_URL"))
    yield pool
    await pool.close()

@pytest.fixture
async def qdrant_client():
    """Real Qdrant client (requires port-forward)."""
    client = QdrantClient(url=os.getenv("TEST_QDRANT_URL"))
    yield client
    client.close()
```

### Contract Fixtures
```python
@pytest.fixture
def skill_factory():
    """Skill test data factory from contract."""
    from tests.contracts.skill.data_contract import SkillTestDataFactory
    return SkillTestDataFactory()

@pytest.fixture
def search_factory():
    """Search test data factory from contract."""
    from tests.contracts.search.data_contract import SearchTestDataFactory
    return SearchTestDataFactory()
```

---

## TDD Workflow

### For New Features

1. **Read Logic Contract** - Understand business rules
2. **Read Data Contract** - Understand data structures
3. **Write Failing Test** (RED)
   ```python
   @pytest.mark.tdd
   @pytest.mark.component
   async def test_BR001_skill_classification():
       """
       BR-001: Tool Classification
       Given: Valid tool with name and description
       When: Classification is requested
       Then: Tool assigned to 1-3 skills with confidence >= 0.5
       """
       # Use factory from data contract
       request = SkillTestDataFactory.make_classification_request(
           tool_name="create_calendar_event",
           tool_description="Create a new calendar event"
       )

       result = await service.classify_tool(request)

       # Assert business rule
       assert len(result.assignments) >= 1
       assert len(result.assignments) <= 3
       assert all(a.confidence >= 0.5 for a in result.assignments)
       assert result.primary_skill_id is not None
   ```
4. **Implement Feature** to make test pass
5. **Refactor** if needed
6. **Test Passes** (GREEN)

### For Bug Fixes

1. **Write Golden Test** capturing current (buggy) behavior
2. **Write TDD Test** defining expected (correct) behavior
3. **Fix Implementation**
4. **TDD Test Passes**, Golden test updated

---

## Contract Usage in Tests

### Import Contracts
```python
from tests.contracts.skill.data_contract import (
    SkillTestDataFactory,
    SkillCategoryCreateRequestContract,
    ToolClassificationResponseContract,
    SkillCategoryBuilder,
)
```

### Use Factory Methods
```python
# Simple factory
skill = SkillTestDataFactory.make_skill_category(
    id="calendar_management",
    name="Calendar Management"
)

# Builder pattern for complex data
request = (
    SkillCategoryBuilder()
    .with_id("calendar_management")
    .with_keywords(["calendar", "event", "schedule"])
    .with_examples(["create_event", "list_events"])
    .build()
)
```

### Validate Responses Against Contract
```python
# Response must conform to contract schema
response_data = await service.classify_tool(request)
validated = ToolClassificationResponseContract(**response_data)

assert validated.primary_skill_id is not None
assert len(validated.assignments) >= 1
```

### Use Invalid Data for Negative Tests
```python
@pytest.mark.tdd
def test_invalid_skill_id_rejected():
    """Test that invalid skill ID format is rejected."""
    invalid_data = SkillTestDataFactory.make_invalid_skill_invalid_id_format()

    with pytest.raises(ValidationError):
        SkillCategoryCreateRequestContract(**invalid_data)
```

---

## Environment Setup

### For Component Tests
No external services required - all dependencies are mocked.

```bash
# Run component tests
pytest tests/component/ -v
```

### For Integration Tests
Requires port-forwarded K8s services:

```bash
# Port forward services
kubectl port-forward svc/postgresql 5432:5432 -n mcp &
kubectl port-forward svc/qdrant 6333:6333 -n mcp &
kubectl port-forward svc/model-service 8082:8082 -n mcp &

# Set environment variables
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/mcp"
export TEST_QDRANT_URL="http://localhost:6333"
export TEST_MODEL_SERVICE_URL="http://localhost:8082"

# Run integration tests
pytest tests/integration/ -v -m integration
```

### For API Tests
Requires running MCP server:

```bash
# Start MCP server
python main.py &

# Set environment
export TEST_MCP_URL="http://localhost:8081"

# Run API tests
pytest tests/api/ -v -m api
```

---

## Performance Requirements

| Test Layer | Target p95 | Max Acceptable |
|------------|-----------|----------------|
| Unit | < 1ms | < 10ms |
| Component | < 100ms | < 500ms |
| Integration | < 5s | < 30s |
| API | < 1s | < 5s |

---

## Coverage Requirements

| Area | Minimum Coverage |
|------|-----------------|
| Business Rules (BR-XXX) | 100% |
| Edge Cases (EC-XXX) | 100% |
| Validation Rules | 100% |
| Happy Paths | 100% |
| Error Handling | 90% |

---

**Version**: 1.0.0
**Last Updated**: 2025-12-11
**Owner**: ISA MCP Team
