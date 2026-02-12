# Contributing to isA_MCP

Thank you for your interest in contributing to isA_MCP. This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Code Style Requirements](#code-style-requirements)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

---

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please be respectful, inclusive, and constructive in all interactions.

### Our Standards

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the project and community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, trolling, or personal attacks
- Publishing others' private information
- Other conduct that could reasonably be considered inappropriate

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.11 or higher
- Docker and Docker Compose
- Git
- Access to required infrastructure (PostgreSQL, Qdrant, Redis)

### Understanding the Project

isA_MCP is an intelligent MCP (Model Context Protocol) server with:

- **Auto-Discovery System**: Automatically registers tools, prompts, and resources
- **Skill-Based Search**: Hierarchical semantic search using Qdrant
- **Microservices Architecture**: Connects to external services via HTTP clients
- **Contract-Driven Development**: All services follow CDD/TDD methodology

Key directories:
```
isA_MCP/
├── main.py              # MCP server entry point
├── services/            # Core services (skill, search, sync, discovery)
├── tools/               # MCP tool implementations
├── prompts/             # MCP prompt templates
├── resources/           # MCP resources
├── tests/               # Test suite (unit, component, integration, api)
├── deployment/          # Docker and Kubernetes configurations
└── docs/                # Documentation
```

---

## Development Environment Setup

### 1. Clone the Repository

```bash
git clone <repository_url>
cd isA_MCP
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### 4. Configure Environment

```bash
# Copy environment template
cp deployment/.env.template .env

# Edit .env with your local settings
# Required variables:
# - DATABASE_URL: PostgreSQL connection string
# - QDRANT_HOST: Qdrant server host
# - REDIS_URL: Redis connection string
```

### 5. Start Infrastructure

```bash
# Start required services
docker-compose -f deployment/dev/docker-compose.yml up -d postgres qdrant redis
```

### 6. Verify Setup

```bash
# Run the server
python main.py

# In another terminal, verify health
curl http://localhost:8081/health
```

### 7. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

---

## Code Style Requirements

### Python Style Guide

We follow PEP 8 with the following specifications:

- **Line length**: Maximum 100 characters
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Grouped and sorted (stdlib, third-party, local)
- **Docstrings**: Google style docstrings for all public functions

### Type Hints

All functions must include type hints:

```python
def search_tools(
    query: str,
    skill_filter: Optional[str] = None,
    limit: int = 10
) -> List[ToolResult]:
    """Search for tools matching the query.

    Args:
        query: The search query string.
        skill_filter: Optional skill to filter results.
        limit: Maximum number of results to return.

    Returns:
        List of matching ToolResult objects.

    Raises:
        SearchError: If the search operation fails.
    """
    ...
```

### Docstrings

All modules, classes, and public functions require docstrings:

```python
"""Module for skill service operations.

This module provides the SkillService class for managing
tool categorization and skill-based filtering.
"""

class SkillService:
    """Service for managing skills and tool categorization.

    The SkillService handles registration, retrieval, and
    search operations for skills within the MCP system.

    Attributes:
        db: Database connection for skill storage.
        vector_store: Qdrant client for semantic search.
    """

    def __init__(self, db: Database, vector_store: QdrantClient) -> None:
        """Initialize the SkillService.

        Args:
            db: Database connection instance.
            vector_store: Qdrant client for vector operations.
        """
        ...
```

### Code Formatting

Use the following tools for consistent formatting:

```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Check types with mypy
mypy .

# Lint with flake8
flake8 .
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Modules | snake_case | `skill_service.py` |
| Classes | PascalCase | `SkillService` |
| Functions | snake_case | `get_skill_by_id` |
| Variables | snake_case | `tool_count` |
| Constants | UPPER_SNAKE | `MAX_BATCH_SIZE` |
| Private | leading underscore | `_internal_helper` |

---

## Testing Requirements

### Test Structure

Tests are organized in layers following CDD/TDD:

```
tests/
├── contracts/      # Service contracts (schemas, interfaces)
├── unit/           # Unit tests (isolated, mocked dependencies)
├── component/      # Component tests (service integration)
├── integration/    # Integration tests (real infrastructure)
└── api/            # API endpoint tests
```

### Writing Tests

#### Unit Tests

```python
# tests/unit/test_skill_service.py
import pytest
from unittest.mock import Mock, patch
from services.skill_service import SkillService

class TestSkillService:
    """Unit tests for SkillService."""

    def test_get_skill_by_id_returns_skill(self):
        """Test that get_skill_by_id returns the correct skill."""
        # Arrange
        mock_db = Mock()
        mock_db.fetch_one.return_value = {"id": "1", "name": "web_research"}
        service = SkillService(db=mock_db, vector_store=Mock())

        # Act
        result = service.get_skill_by_id("1")

        # Assert
        assert result.name == "web_research"
        mock_db.fetch_one.assert_called_once_with("1")

    def test_get_skill_by_id_raises_for_missing(self):
        """Test that get_skill_by_id raises NotFoundError for missing skill."""
        mock_db = Mock()
        mock_db.fetch_one.return_value = None
        service = SkillService(db=mock_db, vector_store=Mock())

        with pytest.raises(NotFoundError):
            service.get_skill_by_id("nonexistent")
```

#### Component Tests

```python
# tests/component/test_search_integration.py
import pytest
from services.search_service import SearchService
from services.skill_service import SkillService

class TestSearchWithSkillService:
    """Component tests for search-skill integration."""

    @pytest.fixture
    def services(self, mock_db, mock_qdrant):
        skill_service = SkillService(mock_db, mock_qdrant)
        search_service = SearchService(skill_service, mock_qdrant)
        return search_service, skill_service

    def test_hierarchical_search_uses_skill_filter(self, services):
        """Test that search correctly filters by skill."""
        search_service, skill_service = services

        # Arrange
        skill_service.register_skill("web_research", ["web_search", "scraper"])

        # Act
        results = search_service.search("find articles", skill_filter="web_research")

        # Assert
        assert all(r.skill == "web_research" for r in results)
```

### Test Coverage Requirements

- **Minimum coverage**: 95% for new code
- **Critical paths**: 100% coverage for core services
- **Edge cases**: Test error conditions and boundary cases

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/unit/test_skill_service.py -v

# Run tests by marker
python -m pytest -m tdd -v
python -m pytest -m skill -v

# Run with coverage
python -m pytest tests/ --cov=services --cov-report=html

# Run specific test class
python -m pytest tests/unit/test_skill_service.py::TestSkillService -v

# Run specific test method
python -m pytest tests/unit/test_skill_service.py::TestSkillService::test_get_skill_by_id -v
```

---

## Pull Request Process

### Before Creating a PR

1. **Create a feature branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/my-feature
   ```

2. **Write tests first** (TDD):
   - Create tests that define expected behavior
   - Run tests to confirm they fail
   - Implement the feature
   - Run tests to confirm they pass

3. **Follow commit conventions**:
   ```bash
   git commit -m "feat(tools): add new vision analyzer"
   git commit -m "test(tools): add unit tests for vision analyzer"
   git commit -m "docs(tools): document vision analyzer usage"
   ```

4. **Update documentation** if needed

5. **Run the full test suite**:
   ```bash
   python -m pytest tests/ -v
   ```

6. **Lint and format code**:
   ```bash
   black .
   isort .
   flake8 .
   mypy .
   ```

### Creating the PR

1. **Push your branch**:
   ```bash
   git push -u origin feature/my-feature
   ```

2. **Create PR via GitHub CLI or web**:
   ```bash
   gh pr create --base develop --title "feat(tools): add vision analyzer" --body "..."
   ```

3. **Fill out PR template** with:
   - Summary of changes
   - Testing performed
   - Related issues
   - Checklist items

### PR Review Process

1. **Automated checks** must pass:
   - All tests pass
   - Code coverage maintained
   - Linting passes
   - Type checking passes

2. **Code review** by maintainers:
   - At least one approval required
   - Address all review comments
   - Request re-review after changes

3. **Final checks**:
   - Branch is up to date with develop
   - No merge conflicts
   - All conversations resolved

### After PR is Merged

1. **Delete your feature branch**:
   ```bash
   git checkout develop
   git pull origin develop
   git branch -d feature/my-feature
   ```

2. **Celebrate your contribution!**

---

## Issue Reporting

### Bug Reports

When reporting a bug, include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Minimal steps to reproduce
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: Python version, OS, relevant versions
6. **Logs**: Relevant error messages or logs

Example:
```markdown
## Bug Description
The hierarchical search returns duplicate tools when multiple skills match.

## Steps to Reproduce
1. Register tool "web_search" with skills ["web_research", "data_collection"]
2. Search with query "find web articles"
3. Observe duplicate "web_search" in results

## Expected Behavior
Each tool should appear only once in results.

## Actual Behavior
"web_search" appears twice when both skills match.

## Environment
- Python 3.11.5
- isA_MCP v0.1.0
- macOS 14.0

## Logs
```
[2025-02-11 10:30:45] DEBUG: Found 2 matching skills: web_research, data_collection
[2025-02-11 10:30:45] DEBUG: Returning 5 tools (with duplicates)
```
```

### Feature Requests

When requesting a feature, include:

1. **Description**: What you want to add
2. **Use Case**: Why this would be valuable
3. **Proposed Solution**: How you envision it working
4. **Alternatives**: Other approaches you've considered

---

## Additional Resources

- [Git Workflow Guide](docs/guidance/git-workflow.md)
- [Release Process](docs/guidance/release-process.md)
- [Git Commands Reference](docs/guidance/git-commands.md)
- [Project README](README.md)

---

## Questions?

If you have questions not covered here:

1. Check existing documentation
2. Search existing issues
3. Open a new issue with the "question" label

Thank you for contributing to isA_MCP!
