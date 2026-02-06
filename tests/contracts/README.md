# Test Contracts Architecture

**3-Contract Driven Development for isA MCP Server**

This directory contains the **Data Contracts** and **Logic Contracts** for all services. Together with the **System Contract** (`tests/TDD_CONTRACT.md`), these form the complete testing specification.

---

## The 3-Contract Architecture

### 1. **System Contract** (Shared) - `tests/TDD_CONTRACT.md`
**Defines HOW to test**
- Test layer structure (Component, Integration, API, Smoke)
- Directory conventions
- Pytest markers and fixtures
- Golden vs TDD workflow
- Infrastructure requirements

**Used by:** All services (shared contract)

---

### 2. **Data Contract** (Per Service) - `data_contract.py`
**Defines WHAT data structures to test**
- Request/Response Pydantic schemas
- Test data factories (builders)
- Valid/invalid data generators
- Field validation rules

**Location:** `tests/contracts/{service}/data_contract.py`

**Example:**
```python
from tests.contracts.skill.data_contract import (
    SkillTestDataFactory,
    SkillCategoryContract,
    ToolClassificationResponseContract,
)

# Use in tests
skill = SkillTestDataFactory.make_skill_category(
    id="calendar_management",
    name="Calendar Management",
)

# Validate response
response = ToolClassificationResponseContract(**api_response)
assert response.primary_skill_id is not None
```

---

### 3. **Logic Contract** (Per Service) - `logic_contract.md`
**Defines WHAT business rules to test**
- Business rules (BR-001, BR-002, ...)
- State machines and transitions
- Authorization matrix
- API contracts (status codes, error handling)
- Event contracts (published events)
- Performance SLAs

**Location:** `tests/contracts/{service}/logic_contract.md`

**Example:**
```markdown
### BR-001: Tool Classification
**Given**: Valid tool with name and description
**When**: Tool is synced to the system
**Then**:
- LLM classifies tool to 1-3 skills
- Each assignment has confidence >= 0.5
- Primary skill selected (highest confidence)
- Tool stored with skill_ids in vector DB

**Edge Cases**:
- No skill matches → Queue suggestion for review
- Confidence < threshold → Skip assignment
```

---

## Directory Structure

```
tests/
├── TDD_CONTRACT.md                    # System Contract (HOW to test)
│
├── contracts/                         # Data + Logic Contracts
│   ├── README.md                      # ← You are here
│   │
│   ├── skill/                         # Skill service contracts
│   │   ├── __init__.py
│   │   ├── data_contract.py           # Data Contract (WHAT data)
│   │   └── logic_contract.md          # Logic Contract (WHAT rules)
│   │
│   └── search/                        # Search service contracts (hierarchical)
│       ├── __init__.py
│       ├── data_contract.py
│       └── logic_contract.md
│
├── component/                         # Tests import from contracts/
│   └── services/
│       ├── skill/
│       │   └── test_skill_service_tdd.py
│       └── search/
│           └── test_hierarchical_search_service_tdd.py
│
├── integration/
│   └── services/
│       ├── skill/
│       │   └── test_skill_sync_integration.py
│       └── search/
│           └── test_search_integration.py
│
├── api/
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

## Services in This Project

### Skill Service (NEW - TDD from scratch)
**Purpose**: Manage skill categories and tool-skill assignments
- **Data Contract**: `tests/contracts/skill/data_contract.py`
- **Logic Contract**: `tests/contracts/skill/logic_contract.md`
- **Implementation**: `services/skill_service/`

### Search Service (EXISTING - Enhancement)
**Purpose**: Hierarchical semantic search for tools/prompts/resources
- **Data Contract**: `tests/contracts/search/data_contract.py`
- **Logic Contract**: `tests/contracts/search/logic_contract.md`
- **Implementation**: `services/search_service/` (enhanced)

---

## Workflow

### For NEW Service (Skill Service)
```bash
# Step 1: Define contracts FIRST (before implementation)
vim tests/contracts/skill/logic_contract.md    # Define business rules
vim tests/contracts/skill/data_contract.py      # Define schemas

# Step 2: Write TDD tests based on contracts
pytest tests/component/services/skill/test_skill_service_tdd.py -v

# Step 3: Implement service to satisfy contracts

# Step 4: Tests turn GREEN
```

### For EXISTING Service Enhancement (Search Service)
```bash
# Step 1: Write GOLDEN tests first to capture current behavior
pytest tests/component/golden/test_search_service_golden.py

# Step 2: Define new contracts for hierarchical search
vim tests/contracts/search/logic_contract.md
vim tests/contracts/search/data_contract.py

# Step 3: Write TDD tests for new behavior
pytest tests/component/services/search/test_hierarchical_search_service_tdd.py

# Step 4: Implement changes, tests turn GREEN
```

---

## Contract Checklist

### Data Contract Checklist
- [ ] All request schemas defined with Pydantic
- [ ] All response schemas defined with Pydantic
- [ ] Test data factories for valid data
- [ ] Test data factories for invalid data
- [ ] Builders for complex request construction
- [ ] Field validation rules documented

### Logic Contract Checklist
- [ ] All business rules documented (BR-XXX format)
- [ ] State machines defined with transitions
- [ ] Authorization matrix specified
- [ ] API contracts defined (status codes)
- [ ] Event contracts defined (if applicable)
- [ ] Performance SLAs specified
- [ ] Edge cases documented

---

## Reference

For the complete System Contract (HOW to test), see `tests/TDD_CONTRACT.md`
