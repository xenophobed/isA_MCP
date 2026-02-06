# Skill Service Logic Contract

**Business Rules and Specifications for Skill Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for skill service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Classification Algorithm](#classification-algorithm)
4. [Embedding Strategy](#embedding-strategy)
5. [API Contracts](#api-contracts)
6. [Performance SLAs](#performance-slas)
7. [Edge Cases](#edge-cases)

---

## Business Rules

### BR-001: Skill Category Creation
**Given**: Valid skill category request from admin
**When**: Admin creates a new skill category
**Then**:
- Skill ID validated (lowercase, starts with letter, underscores allowed)
- Skill record created in `mcp.skill_categories` table
- Initial embedding generated from description
- Skill upserted to Qdrant `mcp_skills` collection
- `tool_count` initialized to 0

**Validation Rules**:
- `id`: Required, format `^[a-z][a-z0-9_]*$`, max 64 chars
- `name`: Required, max 255 chars
- `description`: Required, min 10 chars, max 1000 chars
- `keywords`: Optional, array of lowercase strings
- `examples`: Optional, array of tool name examples

**Edge Cases**:
- Duplicate ID → **409 Conflict** `{"detail": "Skill already exists: {id}"}`
- Invalid ID format → **422 Validation Error**
- Description too short → **422 Validation Error**

---

### BR-002: Tool Classification (LLM)
**Given**: Tool to be classified with name and description
**When**: SyncService processes a new/updated tool
**Then**:
- LLM receives tool info + available skill categories
- LLM returns 1-3 skill assignments with confidence scores
- Assignments with confidence >= 0.5 are saved
- Primary skill = highest confidence assignment
- Tool updated in Qdrant with `skill_ids[]` payload
- Affected skill embeddings updated (real-time)

**LLM Classification Rules**:
- Maximum 3 skill assignments per tool
- Each assignment requires confidence score 0.0-1.0
- Only assignments with confidence >= MIN_CONFIDENCE (0.5) are saved
- If no skill matches with sufficient confidence → suggest new skill
- Suggestions queued in `mcp.skill_suggestions` for human review

**Input to LLM**:
```json
{
  "tool_name": "create_calendar_event",
  "tool_description": "Create a new event on the calendar",
  "input_schema_summary": "title: string, start_time: datetime",
  "available_skills": [
    {"id": "calendar_management", "name": "Calendar Management", "description": "...", "keywords": [...]}
  ]
}
```

**Expected LLM Output**:
```json
{
  "assignments": [
    {"skill_id": "calendar_management", "confidence": 0.95, "reasoning": "Creates calendar events"},
    {"skill_id": "communication", "confidence": 0.4, "reasoning": "May send invites"}
  ],
  "primary_skill_id": "calendar_management",
  "suggested_new_skill": null
}
```

**Edge Cases**:
- LLM timeout → Retry once, then skip (log error)
- LLM returns invalid JSON → Log error, skip classification
- All confidences < threshold → Queue suggestion, no assignment
- Tool already classified + no changes → Skip (optimization)

---

### BR-003: Skill Assignment Storage
**Given**: Classification result with skill assignments
**When**: Assignments are stored
**Then**:
- Old assignments for tool deleted (if re-classifying)
- New assignments created in `mcp.tool_skill_assignments` table
- Each assignment stores: `tool_id`, `skill_id`, `confidence`, `is_primary`, `source`
- Tool vector payload updated with `skill_ids[]` array
- `primary_skill_id` stored separately for quick access

**Storage Rules**:
- A tool can belong to multiple skills (many-to-many)
- Each tool has exactly one primary skill (highest confidence)
- Assignments are atomic (all-or-nothing transaction)
- Re-classification replaces all existing assignments

**Database Schema**:
```sql
CREATE TABLE mcp.tool_skill_assignments (
    id SERIAL PRIMARY KEY,
    tool_id INTEGER NOT NULL,
    skill_id VARCHAR(64) NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    is_primary BOOLEAN DEFAULT FALSE,
    source VARCHAR(32) DEFAULT 'llm_auto',
    assigned_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tool_id, skill_id)
);
```

---

### BR-004: Skill Embedding Generation (Aggregated)
**Given**: Skill with assigned tools
**When**: Skill embedding is updated
**Then**:
- Fetch all tools assigned to this skill
- Get embeddings of all tools from Qdrant
- Compute weighted average (weight = confidence score)
- Normalize resulting vector (L2 norm = 1)
- Upsert to Qdrant `mcp_skills` collection
- Update `tool_count` in payload

**Aggregation Formula**:
```python
# Weighted average of tool embeddings
skill_embedding = sum(tool.embedding * tool.confidence for tool in tools) / sum(tool.confidence for tool in tools)

# Normalize
skill_embedding = skill_embedding / norm(skill_embedding)
```

**Update Triggers** (Real-time):
- Tool assigned to skill → Update skill embedding
- Tool removed from skill → Update skill embedding
- Tool embedding changed → Update affected skill embeddings
- Skill description changed → Regenerate base embedding

**Edge Cases**:
- Skill has 0 tools → Use description embedding only
- Skill has 1 tool → Use tool embedding directly (still normalize)
- Tool embedding missing → Skip that tool in aggregation

---

### BR-005: Skill Suggestion Workflow
**Given**: LLM suggests new skill (no match found)
**When**: Suggestion is created
**Then**:
- Suggestion stored in `mcp.skill_suggestions` table
- Status = `pending`
- Admin notified (if notification enabled)
- Tool remains unclassified until suggestion resolved

**Suggestion Lifecycle**:
```
PENDING → APPROVED (creates new skill, assigns tool)
PENDING → REJECTED (discarded)
PENDING → MERGED (merged into existing skill)
```

**Auto-Approval Rules** (Optional):
- If same skill suggested by LLM N times → auto-create (configurable)
- Default: N = 3

---

### BR-006: Manual Assignment Override
**Given**: Admin manually assigns tool to skills
**When**: Manual assignment is created
**Then**:
- Source = `human_manual` or `human_override`
- Overwrites any LLM assignments
- Prevents re-classification on next sync (until force_reclassify)
- Skill embeddings updated

**Override Rules**:
- Human assignments take precedence over LLM
- Human can assign to skills LLM didn't suggest
- Human can set confidence = 1.0 for manual assignments
- Force reclassify flag ignores human overrides

---

### BR-007: Skill Listing and Filtering
**Given**: Request to list skill categories
**When**: User queries skills
**Then**:
- Returns all skills matching filter criteria
- Supports filtering by: `is_active`, `parent_domain`
- Supports pagination: `limit`, `offset`
- Returns `tool_count` for each skill
- Sorted by `name` ASC by default

**Default Values**:
- `is_active`: True (only active skills)
- `limit`: 100
- `offset`: 0

---

### BR-008: Get Tools by Skill
**Given**: Valid skill_id
**When**: User requests tools for a skill
**Then**:
- Returns all tools assigned to the skill
- Includes assignment metadata (confidence, is_primary)
- Sorted by confidence DESC
- Supports pagination

**Edge Cases**:
- Skill not found → **404 Not Found**
- Skill has no tools → Empty array `[]`

---

## State Machines

### Skill Category State Machine

```
┌─────────┐
│ ACTIVE  │ ← Default state
└────┬────┘
     │
     ├────► INACTIVE  (admin deactivates)
     │
     └────► DELETED   (soft delete)

INACTIVE → ACTIVE (admin reactivates)
```

**Valid Transitions**:
- `ACTIVE` → `INACTIVE` (deactivate)
- `INACTIVE` → `ACTIVE` (reactivate)
- `ACTIVE` → `DELETED` (soft delete)
- `INACTIVE` → `DELETED` (soft delete)

**Behavior by State**:
- `ACTIVE`: Included in classification, searchable
- `INACTIVE`: Excluded from classification, not searchable, existing assignments preserved
- `DELETED`: Removed from all queries, assignments orphaned

---

### Skill Suggestion State Machine

```
┌─────────┐
│ PENDING │ ← Initial state
└────┬────┘
     │
     ├────► APPROVED  (admin approves → creates skill)
     │
     ├────► REJECTED  (admin rejects → discarded)
     │
     └────► MERGED    (admin merges into existing skill)
```

---

## Classification Algorithm

### LLM Prompt Template

```
You are a tool classifier. Given a tool's name and description, assign it to one or more skill categories.

## Available Skill Categories:
{skill_categories_json}

## Tool to Classify:
Name: {tool_name}
Description: {tool_description}
Input Schema: {input_schema_summary}

## Instructions:
1. Analyze the tool's purpose and functionality
2. Assign to 1-3 most relevant skill categories
3. Provide confidence score (0.0-1.0) for each assignment
4. If no category fits well (all confidences < 0.5), suggest a new category

## Output Format (JSON only, no markdown):
{
    "assignments": [
        {"skill_id": "...", "confidence": 0.0-1.0, "reasoning": "..."}
    ],
    "primary_skill_id": "..." or null,
    "suggested_new_skill": null or {"name": "...", "description": "..."}
}
```

### Classification Confidence Thresholds

| Confidence Range | Action |
|-----------------|--------|
| 0.8 - 1.0 | Strong match, always assign |
| 0.5 - 0.79 | Moderate match, assign |
| 0.3 - 0.49 | Weak match, skip but log |
| 0.0 - 0.29 | No match, ignore |

### Multi-Skill Assignment Rules

| Scenario | Expected Behavior |
|----------|------------------|
| Tool clearly belongs to 1 skill | 1 assignment, confidence > 0.8 |
| Tool spans 2 skills (e.g., export_calendar_csv) | 2 assignments, primary = highest |
| Generic utility tool | 1-2 assignments, lower confidence |
| No clear match | 0 assignments + suggestion |

---

## Embedding Strategy

### Skill Embedding Sources

1. **Description Embedding** (Initial)
   - Generated when skill created
   - Used when skill has 0 tools

2. **Aggregated Tool Embedding** (Runtime)
   - Weighted average of assigned tool embeddings
   - Weight = assignment confidence
   - Normalized to unit vector

3. **Hybrid Embedding** (Optional enhancement)
   - 70% aggregated tools + 30% description
   - More stable, less prone to drift

### Embedding Update Schedule

| Event | Update Strategy |
|-------|----------------|
| Tool assigned | Immediate (real-time) |
| Tool removed | Immediate (real-time) |
| Tool embedding changed | Immediate (real-time) |
| Skill description changed | Immediate (regenerate) |
| Batch sync | Update all affected skills |

---

## API Contracts

### POST /api/v1/skills
**Create Skill Category**

**Request**: `application/json`
```json
{
  "id": "calendar_management",
  "name": "Calendar Management",
  "description": "Tools for managing calendars and events...",
  "keywords": ["calendar", "event", "schedule"],
  "examples": ["create_event", "list_events"],
  "parent_domain": "productivity"
}
```

**Success Response**: `201 Created`
```json
{
  "id": "calendar_management",
  "name": "Calendar Management",
  "description": "Tools for managing calendars and events...",
  "keywords": ["calendar", "event", "schedule"],
  "examples": ["create_event", "list_events"],
  "parent_domain": "productivity",
  "tool_count": 0,
  "is_active": true,
  "created_at": "2025-12-11T10:00:00Z",
  "updated_at": "2025-12-11T10:00:00Z"
}
```

**Error Responses**:
- `409 Conflict`: Skill ID already exists
- `422 Validation Error`: Invalid request data

---

### GET /api/v1/skills
**List Skill Categories**

**Query Parameters**:
- `is_active`: Boolean (optional, default: true)
- `parent_domain`: String (optional)
- `limit`: Integer (optional, default: 100)
- `offset`: Integer (optional, default: 0)

**Success Response**: `200 OK`
```json
[
  {
    "id": "calendar_management",
    "name": "Calendar Management",
    "tool_count": 15,
    ...
  }
]
```

---

### GET /api/v1/skills/{skill_id}
**Get Skill Category**

**Success Response**: `200 OK`
```json
{
  "id": "calendar_management",
  "name": "Calendar Management",
  "description": "...",
  "keywords": [...],
  "examples": [...],
  "parent_domain": "productivity",
  "tool_count": 15,
  "is_active": true,
  "created_at": "...",
  "updated_at": "..."
}
```

**Error Responses**:
- `404 Not Found`: Skill not found

---

### GET /api/v1/skills/{skill_id}/tools
**Get Tools in Skill**

**Query Parameters**:
- `limit`: Integer (optional, default: 100)
- `offset`: Integer (optional, default: 0)

**Success Response**: `200 OK`
```json
[
  {
    "tool_id": 1,
    "tool_name": "create_event",
    "confidence": 0.95,
    "is_primary": true,
    "assigned_at": "2025-12-11T10:00:00Z"
  }
]
```

---

### POST /api/v1/skills/classify
**Classify Tool (Manual Trigger)**

**Request**: `application/json`
```json
{
  "tool_id": 1,
  "tool_name": "create_event",
  "tool_description": "Create calendar event",
  "force_reclassify": false
}
```

**Success Response**: `200 OK`
```json
{
  "tool_id": 1,
  "tool_name": "create_event",
  "assignments": [
    {"skill_id": "calendar_management", "confidence": 0.95, "reasoning": "..."}
  ],
  "primary_skill_id": "calendar_management",
  "suggested_new_skill": null,
  "classification_timestamp": "2025-12-11T10:00:00Z"
}
```

---

### GET /api/v1/skills/suggestions
**List Pending Suggestions**

**Success Response**: `200 OK`
```json
[
  {
    "id": 1,
    "suggested_name": "communication",
    "suggested_description": "Tools for email and messaging",
    "source_tool_id": 42,
    "source_tool_name": "send_email",
    "reasoning": "No existing skill covers email operations",
    "status": "pending",
    "created_at": "2025-12-11T10:00:00Z"
  }
]
```

---

### POST /api/v1/skills/suggestions/{id}/approve
**Approve Suggestion**

Creates new skill from suggestion and assigns source tool.

**Success Response**: `200 OK`
```json
{
  "skill": { ... },
  "assignment": { ... },
  "message": "Skill created and tool assigned"
}
```

---

## Performance SLAs

### Response Time Targets (p95)

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| Create Skill | < 100ms | < 500ms |
| List Skills | < 50ms | < 200ms |
| Get Skill | < 20ms | < 100ms |
| Get Skill Tools | < 100ms | < 500ms |
| Classify Tool (LLM) | < 3s | < 10s |
| Update Skill Embedding | < 200ms | < 1s |

### Throughput Targets

- Skill CRUD operations: 100 req/s
- Classification requests: 10 req/s (LLM limited)
- Embedding updates: 50 req/s

### Resource Limits

- Max skills: 1000
- Max tools per skill: 10000
- Max skills per tool: 5
- Max keywords per skill: 20
- Max examples per skill: 10

---

## Edge Cases

### EC-001: Concurrent Classification
**Scenario**: Same tool classified by multiple sync processes
**Expected**: Last write wins, no duplicates
**Solution**: Use `ON CONFLICT` upsert

---

### EC-002: Skill Deleted During Classification
**Scenario**: Admin deletes skill while LLM is classifying
**Expected**: Assignment fails gracefully
**Solution**: FK constraint check, skip deleted skills

---

### EC-003: LLM Hallucination
**Scenario**: LLM returns non-existent skill_id
**Expected**: Assignment rejected
**Solution**: Validate skill_id exists before saving

---

### EC-004: Circular Embedding Update
**Scenario**: Skill embedding update triggers another update
**Expected**: No infinite loop
**Solution**: Track update timestamp, skip if recently updated

---

### EC-005: Empty Skill After All Tools Removed
**Scenario**: All tools unassigned from skill
**Expected**: Skill uses description embedding
**Solution**: Fall back to description embedding when tool_count = 0

---

### EC-006: Very Long Tool Description
**Scenario**: Tool description > 10000 chars
**Expected**: Classification works with truncated description
**Solution**: Truncate to 2000 chars for LLM context

---

## Test Coverage Requirements

All tests MUST cover:

- ✅ Happy path (BR-XXX success scenarios)
- ✅ Validation errors (400, 422)
- ✅ Not found errors (404)
- ✅ Conflict errors (409)
- ✅ State transitions (valid and invalid)
- ✅ LLM classification scenarios
- ✅ Embedding generation and updates
- ✅ Edge cases (EC-XXX scenarios)
- ✅ Performance within SLAs

---

**Version**: 1.0.0
**Last Updated**: 2025-12-11
**Owner**: MCP Search Team
