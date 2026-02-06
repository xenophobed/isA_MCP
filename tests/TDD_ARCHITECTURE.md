# TDD Architecture for isA_MCP

## Top-Down TDD Approach with Golden/Characterization Tests

This architecture combines **TDD (Test-Driven Development)** for new features with **Characterization Testing** to protect existing behavior.

```
tests/
├── conftest.py                      # Global fixtures
├── pytest.ini                       # Markers config
│
│ ══════════════════════════════════════════════════════════════
│  LAYER 4: UNIT (Pure logic, no I/O)
│ ══════════════════════════════════════════════════════════════
├── unit/
│   ├── conftest.py
│   │
│   ├── golden/                      # 🔒 CHARACTERIZATION (don't modify)
│   │   ├── test_llm_golden.py           # Captures current LLM behavior
│   │   ├── test_embedding_golden.py     # Captures current embedding behavior
│   │   ├── test_vision_golden.py        # Captures current vision behavior
│   │   └── test_audio_golden.py         # Captures current audio behavior
│   │
│   ├── services/                    # 🆕 TDD (new features)
│   │   ├── llm/
│   │   │   ├── test_openai.py
│   │   │   ├── test_cerebras.py
│   │   │   └── test_yyds.py
│   │   ├── embedding/
│   │   │   └── test_embedding_generator.py
│   │   ├── vision/
│   │   │   └── test_vision_analyzer.py
│   │   └── audio/
│   │       └── test_audio_processor.py
│   │
│   ├── logic/                       # Pure business logic
│   │   ├── test_pricing.py
│   │   ├── test_model_selection.py
│   │   ├── test_token_counting.py
│   │   └── test_schema_validation.py
│   │
│   └── models/                      # Types, enums, schemas
│       ├── test_tool_models.py
│       ├── test_prompt_models.py
│       └── test_config_models.py
│
│ ══════════════════════════════════════════════════════════════
│  LAYER 3: COMPONENT (Mocked external APIs)
│ ══════════════════════════════════════════════════════════════
├── component/
│   ├── conftest.py
│   ├── mocks/                       # Mock implementations
│   │   ├── __init__.py
│   │   ├── db_mock.py
│   │   ├── qdrant_mock.py
│   │   ├── minio_mock.py
│   │   ├── model_client_mock.py
│   │   ├── redis_mock.py
│   │   └── http_mock.py
│   │
│   ├── golden/                      # 🔒 CHARACTERIZATION
│   │   ├── test_llm_invoke_golden.py        # Current invoke behavior
│   │   ├── test_llm_stream_golden.py        # Current stream behavior
│   │   ├── test_embedding_golden.py
│   │   ├── test_tool_service_golden.py
│   │   └── test_search_service_golden.py
│   │
│   └── services/                    # 🆕 TDD (new features)
│       ├── llm/
│       │   ├── test_invoke.py
│       │   ├── test_stream.py
│       │   └── test_tool_calling.py
│       ├── embedding/
│       │   └── test_embedding_service.py
│       ├── vision/
│       │   └── test_vision_service.py
│       ├── audio/
│       │   └── test_audio_service.py
│       ├── tools/
│       │   ├── test_tool_service.py
│       │   └── test_tool_repository.py
│       ├── prompts/
│       │   └── test_prompt_service.py
│       ├── search/
│       │   └── test_search_service.py
│       └── sync/
│           └── test_sync_service.py
│
│ ══════════════════════════════════════════════════════════════
│  LAYER 2: INTEGRATION (Real DB, mocked external APIs)
│ ══════════════════════════════════════════════════════════════
├── integration/
│   ├── conftest.py
│   │
│   ├── golden/                      # 🔒 CHARACTERIZATION
│   │   ├── test_usage_tracking_golden.py
│   │   ├── test_discovery_golden.py
│   │   └── test_sync_golden.py
│   │
│   ├── events/                      # 🆕 TDD
│   │   ├── test_usage_events.py
│   │   └── test_tool_events.py
│   │
│   └── flows/                       # Business flow tests
│       ├── test_inference_flow.py
│       ├── test_tool_lifecycle.py
│       ├── test_discovery_flow.py
│       └── test_sync_flow.py
│
│ ══════════════════════════════════════════════════════════════
│  LAYER 1: API (HTTP contract tests)
│ ══════════════════════════════════════════════════════════════
├── api/
│   ├── conftest.py
│   │
│   ├── golden/                      # 🔒 CHARACTERIZATION (response snapshots)
│   │   ├── test_tools_api_golden.py
│   │   ├── test_prompts_api_golden.py
│   │   └── snapshots/                   # JSON response snapshots
│   │       ├── tools_list_success.json
│   │       ├── tools_call_success.json
│   │       ├── tools_call_error.json
│   │       ├── prompts_list_success.json
│   │       └── search_results.json
│   │
│   ├── tools/                       # 🆕 TDD
│   │   ├── test_tool_list_api.py
│   │   ├── test_tool_call_api.py
│   │   └── test_tool_search_api.py
│   ├── prompts/
│   │   ├── test_prompt_list_api.py
│   │   └── test_prompt_get_api.py
│   ├── resources/
│   │   └── test_resource_api.py
│   ├── auth/
│   │   └── test_auth_api.py
│   └── health/
│       └── test_health_api.py
│
│ ══════════════════════════════════════════════════════════════
│  E2E & EVAL (Special purpose)
│ ══════════════════════════════════════════════════════════════
├── e2e/                             # Shell scripts for manual/CI testing
│   ├── README.md
│   ├── api/
│   │   ├── test_mcp_protocol.sh
│   │   └── test_tool_calls.sh
│   ├── cache/
│   │   └── test_redis_cache.sh
│   ├── tool_calling/
│   │   └── test_llm_tools.sh
│   └── voice/
│       └── test_audio_pipeline.sh
│
├── eval/                            # DeepEval LLM quality tests
│   ├── conftest.py
│   ├── inference/
│   │   ├── test_text_generation.py
│   │   ├── test_summarization.py
│   │   └── test_extraction.py
│   ├── retrieval/
│   │   ├── test_semantic_search.py
│   │   └── test_tool_ranking.py
│   └── compliance/
│       ├── test_content_safety.py
│       └── test_pii_detection.py
│
│ ══════════════════════════════════════════════════════════════
│  SHARED
│ ══════════════════════════════════════════════════════════════
└── fixtures/
    ├── __init__.py
    ├── factories.py                 # Object factories
    ├── generators.py                # Random data generators
    ├── responses.py                 # Mock API responses
    └── data/                        # Test data files
        ├── audio/                   # Sample audio files
        │   └── sample.mp3
        ├── images/                  # Sample images
        │   └── sample.jpg
        ├── documents/               # PDFs, etc.
        │   └── sample.pdf
        └── golden/                  # Expected outputs for golden tests
            ├── llm_responses.json
            ├── embeddings.json
            └── vision_outputs.json
```

---

## Key Principles

| Folder | Purpose | Rule |
|--------|---------|------|
| `golden/` | Characterization tests | 🔒 **NEVER modify** - captures existing behavior |
| `services/`, `flows/`, etc. | TDD tests | 🆕 **Add new tests here** - define new behavior |
| `snapshots/` | Response snapshots | 🔒 **Update only intentionally** when API changes |

---

## Golden vs TDD Tests

### Golden Tests (Characterization)

**Purpose**: Capture and protect existing behavior. These tests detect unintended regressions.

```python
# tests/unit/golden/test_llm_golden.py
"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY
These tests capture the current behavior of the LLM service.
If these tests fail, it means behavior has changed unexpectedly.
"""
import pytest

@pytest.mark.golden
class TestLLMGolden:
    """Golden tests for LLM behavior - DO NOT MODIFY."""

    def test_token_counting_behavior(self):
        """Captures current token counting behavior."""
        from tools.services.intelligence_service.language.text_generator import count_tokens

        # These values represent CURRENT behavior
        # If they change, investigate before updating
        assert count_tokens("Hello, world!") == 4
        assert count_tokens("") == 0
        assert count_tokens("A" * 100) == 100

    def test_model_selection_defaults(self):
        """Captures current model selection defaults."""
        from core.config import get_default_model

        # Current default behavior
        assert get_default_model("text") == "gpt-4"
        assert get_default_model("embedding") == "text-embedding-3-small"
        assert get_default_model("vision") == "gpt-4-vision-preview"


# tests/component/golden/test_tool_service_golden.py
"""
🔒 CHARACTERIZATION TESTS - DO NOT MODIFY
"""
@pytest.mark.golden
class TestToolServiceGolden:
    """Golden tests for tool service - DO NOT MODIFY."""

    async def test_tool_registration_behavior(self, mock_db_pool):
        """Captures current tool registration behavior."""
        from services.tool_service import ToolService

        service = ToolService(db_pool=mock_db_pool)

        # Current behavior: returns tool ID on success
        result = await service.register_tool({
            "name": "test_tool",
            "description": "Test"
        })

        assert "id" in result
        assert result["status"] == "registered"
```

### TDD Tests (New Features)

**Purpose**: Define behavior for new features BEFORE implementation.

```python
# tests/unit/services/llm/test_openai.py
"""
🆕 TDD TESTS - Define new feature behavior
Write these tests BEFORE implementing the feature.
"""
import pytest

@pytest.mark.unit
class TestOpenAIService:
    """TDD tests for OpenAI service - add new tests here."""

    async def test_streaming_with_tool_calls(self, mock_openai_client):
        """RED: Define expected streaming + tool call behavior."""
        # Given: A request with tools
        request = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "What's the weather?"}],
            "tools": [{"type": "function", "function": {"name": "get_weather"}}],
            "stream": True
        }

        # When: Streaming response with tool call
        chunks = []
        async for chunk in openai_service.stream(request):
            chunks.append(chunk)

        # Then: Should receive tool call in stream
        tool_calls = [c for c in chunks if c.get("type") == "tool_call"]
        assert len(tool_calls) > 0
        assert tool_calls[0]["function"]["name"] == "get_weather"

    async def test_retry_on_rate_limit(self, mock_openai_client):
        """RED: Define retry behavior on rate limit."""
        mock_openai_client.set_response_sequence([
            {"error": "rate_limit", "retry_after": 1},
            {"content": "Success after retry"}
        ])

        result = await openai_service.generate("Test prompt")

        assert result == "Success after retry"
        assert mock_openai_client.call_count == 2
```

---

## Snapshot Testing for APIs

```python
# tests/api/golden/test_tools_api_golden.py
"""
🔒 API SNAPSHOT TESTS - DO NOT MODIFY
"""
import pytest
import json
from pathlib import Path

SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"

@pytest.mark.golden
@pytest.mark.api
class TestToolsAPIGolden:
    """Golden snapshot tests for tools API."""

    async def test_tools_list_response_snapshot(self, mcp_client):
        """Verify tools/list response matches snapshot."""
        response = await mcp_client.post("/", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        })

        actual = response.json()

        # Load expected snapshot
        snapshot_path = SNAPSHOTS_DIR / "tools_list_success.json"
        if snapshot_path.exists():
            with open(snapshot_path) as f:
                expected = json.load(f)

            # Compare structure (not exact values for dynamic fields)
            assert actual["jsonrpc"] == expected["jsonrpc"]
            assert "result" in actual
            assert "tools" in actual["result"]

            # Verify tool structure matches
            if actual["result"]["tools"]:
                actual_tool = actual["result"]["tools"][0]
                expected_tool = expected["result"]["tools"][0]
                assert set(actual_tool.keys()) == set(expected_tool.keys())

    async def test_tools_call_error_snapshot(self, mcp_client):
        """Verify error response matches snapshot."""
        response = await mcp_client.post("/", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}}
        })

        actual = response.json()

        snapshot_path = SNAPSHOTS_DIR / "tools_call_error.json"
        if snapshot_path.exists():
            with open(snapshot_path) as f:
                expected = json.load(f)

            assert "error" in actual
            assert actual["error"]["code"] == expected["error"]["code"]
```

---

## TDD Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    TDD: RED → GREEN → REFACTOR                  │
│                                                                 │
│   1. Write failing test in services/ folder                     │
│   2. Implement minimal code to pass                             │
│   3. Refactor while keeping tests green                         │
│   4. Run golden/ tests to ensure no regressions                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              CHARACTERIZATION: Protect Existing                 │
│                                                                 │
│   1. Golden tests capture CURRENT behavior                      │
│   2. If golden tests fail → investigate before updating         │
│   3. Only update golden tests when behavior change is           │
│      INTENTIONAL and approved                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Step-by-Step TDD Flow

```bash
# 1. Write failing tests (RED)
pytest tests/unit/services/llm/test_openai.py -v
# → FAILED (not implemented yet)

# 2. Implement the feature (GREEN)
# ... write code ...
pytest tests/unit/services/llm/test_openai.py -v
# → PASSED

# 3. Run golden tests to check for regressions
pytest tests/unit/golden -v
pytest tests/component/golden -v
# → All should still pass

# 4. Refactor if needed, keep all tests green
pytest tests/unit tests/component -v
```

---

## Test Markers & Configuration

```ini
# tests/pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

markers =
    # Test Layers
    api: API contract tests (Layer 1)
    integration: Service integration tests (Layer 2)
    component: Component tests (Layer 3)
    unit: Unit tests (Layer 4)
    e2e: End-to-end tests
    eval: DeepEval LLM quality tests

    # Test Types
    golden: Characterization tests - DO NOT MODIFY
    tdd: TDD tests for new features
    snapshot: Snapshot-based tests

    # Performance
    slow: Tests > 10 seconds

    # Infrastructure
    requires_db: Requires PostgreSQL
    requires_qdrant: Requires Qdrant
    requires_redis: Requires Redis
    requires_ai: Requires AI model access

addopts =
    --strict-markers
    -ra
    --tb=short
    -v

filterwarnings =
    ignore::DeprecationWarning
```

---

## Running Tests

```bash
# ═══════════════════════════════════════════════════════════════
# TDD Development (write tests first)
# ═══════════════════════════════════════════════════════════════

# Run TDD tests only (new features)
pytest tests/unit/services tests/component/services -v

# Run specific service tests
pytest tests/unit/services/llm -v
pytest tests/component/services/embedding -v


# ═══════════════════════════════════════════════════════════════
# Golden/Characterization Tests (regression detection)
# ═══════════════════════════════════════════════════════════════

# Run ALL golden tests
pytest -m golden -v

# Run golden tests by layer
pytest tests/unit/golden -v
pytest tests/component/golden -v
pytest tests/integration/golden -v
pytest tests/api/golden -v


# ═══════════════════════════════════════════════════════════════
# Full Test Pyramid
# ═══════════════════════════════════════════════════════════════

# Fast local development (unit + component)
pytest tests/unit tests/component -v --tb=short

# Pre-commit check (includes golden)
pytest tests/unit tests/component -v

# CI pipeline (all except eval)
pytest tests/ --ignore=tests/eval --ignore=tests/e2e -v

# Full suite with coverage
pytest --cov=core --cov=services --cov=tools \
       --cov-report=html --cov-fail-under=80


# ═══════════════════════════════════════════════════════════════
# Special Purpose
# ═══════════════════════════════════════════════════════════════

# DeepEval quality tests (nightly)
deepeval test run tests/eval/

# E2E shell scripts
./tests/e2e/api/test_mcp_protocol.sh
./tests/e2e/tool_calling/test_llm_tools.sh
```

---

## Layer Responsibilities

| Layer | Tests What | Mocks | Speed | Golden? |
|-------|-----------|-------|-------|---------|
| **Unit** | Pure functions, models | Everything | Very fast | ✅ Yes |
| **Component** | Service methods | DB, APIs | Fast | ✅ Yes |
| **Integration** | Service flows | External APIs | Medium | ✅ Yes |
| **API** | HTTP contracts | None | Slow | ✅ Yes |
| **E2E** | Full system | None | Very slow | ❌ No |
| **Eval** | LLM quality | None | Slow | ❌ No |

---

## When to Update Golden Tests

```
┌─────────────────────────────────────────────────────────────────┐
│                   GOLDEN TEST FAILURE                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Was this change │
                    │  intentional?   │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
        ┌─────────┐                   ┌─────────┐
        │   NO    │                   │   YES   │
        └────┬────┘                   └────┬────┘
             │                             │
             ▼                             ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ You have a bug! │          │ Get approval,   │
    │ Fix your code,  │          │ then update     │
    │ not the test.   │          │ golden test.    │
    └─────────────────┘          └─────────────────┘
```

### Approval Process for Golden Updates

1. **Document the change**: Why is behavior changing?
2. **Get review**: Another team member verifies the change is correct
3. **Update snapshot**: Commit with clear message: `chore(tests): update golden for X feature change`

---

## Mock Examples

```python
# tests/component/mocks/model_client_mock.py
class MockModelClient:
    """Mock for AI model service."""

    def __init__(self):
        self._responses = {}
        self._calls = []

    async def generate(self, prompt: str, **kwargs) -> str:
        self._calls.append(("generate", prompt, kwargs))
        return self._responses.get("generate", "Mock response")

    async def stream(self, prompt: str, **kwargs):
        self._calls.append(("stream", prompt, kwargs))
        for chunk in self._responses.get("stream", ["Mock ", "stream"]):
            yield chunk

    async def embed(self, text: str) -> list:
        self._calls.append(("embed", text))
        return self._responses.get("embed", [0.1] * 1536)

    def set_response(self, method: str, response):
        self._responses[method] = response

    def set_response_sequence(self, method: str, responses: list):
        """For testing retry logic."""
        self._response_sequences[method] = list(responses)
```

---

## Factory Pattern

```python
# tests/fixtures/factories.py
class ToolFactory:
    @staticmethod
    def build(**overrides):
        default = {
            "name": f"tool_{uuid.uuid4().hex[:8]}",
            "description": "A test tool",
            "category": "utility",
            "input_schema": {"type": "object", "properties": {}},
        }
        default.update(overrides)
        return default

    @staticmethod
    def build_intelligence(**overrides):
        """Convenience method for intelligence tools."""
        return ToolFactory.build(
            category="intelligence",
            description="An AI-powered tool",
            **overrides
        )
```

---

## Quick Start

```bash
# 1. Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock \
            deepeval faker factory-boy httpx

# 2. Directory structure is ready - start writing tests!

# 3. TDD workflow:
#    a. Add test to services/ folder (RED)
#    b. Implement feature (GREEN)
#    c. Run golden tests (ensure no regression)
#    d. Refactor if needed

# 4. Verify the pyramid
pytest tests/unit -v              # Fastest, most tests
pytest tests/component -v         # Fast
pytest tests/integration -v       # Medium
pytest tests/api -v               # Slow
pytest -m golden -v               # All characterization tests
```

---

## Coverage Goals

| Component | Target | Golden Coverage |
|-----------|--------|-----------------|
| core/ | 90% | 100% of existing APIs |
| services/ | 85% | 100% of public methods |
| tools/ | 80% | Key tools only |
| **Overall** | **80%** | - |
