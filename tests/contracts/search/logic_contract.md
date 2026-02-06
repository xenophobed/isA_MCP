# Search Service Logic Contract (Hierarchical Search)

**Business Rules and Specifications for Hierarchical Search Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for hierarchical search behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [Search Algorithm](#search-algorithm)
3. [Fallback Strategies](#fallback-strategies)
4. [API Contracts](#api-contracts)
5. [Performance SLAs](#performance-slas)
6. [Edge Cases](#edge-cases)

---

## Business Rules

### BR-001: Two-Stage Hierarchical Search
**Given**: User query for tool/prompt/resource search
**When**: Hierarchical search is executed
**Then**:
1. **Stage 1 (Skill Matching)**:
   - Generate query embedding (reused for both stages)
   - Search `mcp_skills` collection for matching skills
   - Return top `skill_limit` skills with score >= `skill_threshold`

2. **Stage 2 (Tool Search)**:
   - Search `mcp_unified_search` collection
   - Filter by `skill_ids` from Stage 1 (if any matched)
   - Return top `limit` tools with score >= `tool_threshold`

3. **Stage 3 (Enrichment)**:
   - Load full `input_schema` from PostgreSQL for top results
   - Only load schemas if `include_schemas=true`
   - Return enriched results sorted by score DESC

**Key Invariants**:
- Query embedding generated exactly once (reused)
- All returned tools must belong to at least one matched skill (unless fallback)
- Results always sorted by similarity score descending
- Schema loading is lazy (only for returned tools)

---

### BR-002: Skill Matching (Stage 1)
**Given**: Query embedding and skill index
**When**: Skill search is performed
**Then**:
- Search Qdrant `mcp_skills` collection
- Use cosine similarity for scoring
- Filter by `score >= skill_threshold`
- Return maximum `skill_limit` skills
- Include `tool_count` for each skill

**Skill Match Criteria**:
- Score >= 0.4 (default threshold, configurable)
- Only active skills included
- Higher `tool_count` is not a ranking factor (pure similarity)

**Output Per Skill**:
```json
{
  "id": "calendar_management",
  "name": "Calendar Management",
  "description": "Tools for calendars...",
  "score": 0.87,
  "tool_count": 15
}
```

---

### BR-003: Tool Search with Skill Filter (Stage 2)
**Given**: Query embedding and matched skill IDs
**When**: Tool search is performed
**Then**:
- Search Qdrant `mcp_unified_search` collection
- Apply filter: `skill_ids CONTAINS ANY matched_skill_ids`
- Use cosine similarity for scoring
- Filter by `score >= tool_threshold`
- Return maximum `limit` tools
- Include `skill_ids[]` and `primary_skill_id` in results

**Tool Match Criteria**:
- Score >= 0.3 (default threshold, configurable)
- Must belong to at least one matched skill
- `is_active = true`

**Filter Logic**:
```python
filter_conditions = {
    "must": [
        {"field": "skill_ids", "match": {"any": matched_skill_ids}},
        {"field": "is_active", "match": {"value": True}}
    ]
}
```

---

### BR-004: Schema Enrichment (Stage 3)
**Given**: Matched tools from Stage 2
**When**: `include_schemas=true`
**Then**:
- For each tool in results (limited to `limit`):
  - Fetch full record from PostgreSQL by `db_id`
  - Extract `input_schema`, `output_schema`, `annotations`
  - Attach to tool result
- Load in parallel for performance
- Handle missing schemas gracefully (null)

**Schema Loading Rules**:
- Only load for tools that will be returned (after filtering)
- Maximum schemas to load = `limit` parameter
- If PostgreSQL lookup fails → tool still returned with `input_schema=null`
- Cache schemas if same tool appears in multiple searches (optional optimization)

---

### BR-005: Item Type Filtering
**Given**: Search request with `item_type` parameter
**When**: Search is performed
**Then**:
- If `item_type=null` → Search all types (tool, prompt, resource)
- If `item_type="tool"` → Only return tools
- If `item_type="prompt"` → Only return prompts
- If `item_type="resource"` → Only return resources
- Filter applied in BOTH Stage 1 (if skill has type metadata) and Stage 2

**Filter Application**:
```python
# Stage 2 filter
if item_type:
    filter_conditions["must"].append({
        "field": "type",
        "match": {"value": item_type}
    })
```

---

### BR-006: Fallback to Unfiltered Search
**Given**: No skills matched in Stage 1 (all scores < threshold)
**When**: Stage 2 is executed
**Then**:
- Remove skill filter (search all tools)
- Log warning: "No skills matched, falling back to unfiltered search"
- Continue with tool search using same thresholds
- Set `metadata.skill_ids_used = null` in response

**Fallback Trigger**:
- All skill scores < `skill_threshold`
- No skills exist in index (empty skill collection)
- Skill search error (graceful degradation)

**Fallback Behavior**:
- Search becomes equivalent to current non-hierarchical search
- Performance may be slower (larger search space)
- Results may be less relevant (no skill pre-filtering)

---

### BR-007: Search Metadata Tracking
**Given**: Any search request
**When**: Search completes
**Then**:
- Record timing for each stage:
  - `query_embedding_time_ms`
  - `skill_search_time_ms`
  - `tool_search_time_ms`
  - `schema_load_time_ms`
  - `total_time_ms`
- Record counts:
  - `stage1_skill_count`: Skills matched
  - `stage2_candidate_count`: Tools found before limit
  - `final_count`: Tools returned
- Record strategy:
  - `strategy_used`: hierarchical/direct/hybrid
  - `skill_ids_used`: List of skill IDs or null

---

### BR-008: Direct Search Strategy (Bypass Skills)
**Given**: Search request with `strategy="direct"`
**When**: Search is performed
**Then**:
- Skip Stage 1 entirely
- Search tools directly without skill filter
- Still apply `item_type` filter if specified
- Set `matched_skills = []` in response
- Set `skill_ids_used = null` in metadata

**Use Cases**:
- Quick searches where skill routing adds latency
- Testing/debugging without skill layer
- Emergency fallback if skill index corrupted

---

### BR-009: Score Normalization
**Given**: Qdrant returns similarity scores
**When**: Results are returned
**Then**:
- All scores normalized to 0.0-1.0 range
- Cosine similarity already returns -1 to 1
- Transform: `normalized = (raw + 1) / 2` (if needed)
- Ensure no scores > 1.0 or < 0.0 in response

---

## Search Algorithm

### Hierarchical Search Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HIERARCHICAL SEARCH FLOW                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  User Query: "schedule a meeting with John tomorrow"                     │
│                              │                                           │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Step 0: Generate Query Embedding (~50ms)                           │ │
│  │ - Call embedding model once                                        │ │
│  │ - Reuse for both stages                                            │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                              │                                           │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Stage 1: Skill Search (~10ms)                                      │ │
│  │ - Query: mcp_skills collection                                     │ │
│  │ - Params: limit=skill_limit, threshold=skill_threshold             │ │
│  │ - Output: [("calendar_management", 0.87), ("communication", 0.62)] │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                              │                                           │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Stage 2: Tool Search with Filter (~25ms)                           │ │
│  │ - Query: mcp_unified_search collection                             │ │
│  │ - Filter: skill_ids IN ["calendar_management", "communication"]    │ │
│  │ - Params: limit=limit, threshold=tool_threshold                    │ │
│  │ - Output: [("create_event", 0.92), ("send_invite", 0.78), ...]    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                              │                                           │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Stage 3: Schema Enrichment (~15ms)                                 │ │
│  │ - Load input_schema from PostgreSQL for top N tools                │ │
│  │ - Parallel loading for performance                                 │ │
│  │ - Skip if include_schemas=false                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                              │                                           │
│                              ▼                                           │
│  Return: HierarchicalSearchResponse                                      │
│  - tools: [EnrichedTool, ...]                                           │
│  - matched_skills: [SkillMatch, ...]                                    │
│  - metadata: SearchMetadata                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### Threshold Tuning Guide

| Use Case | skill_threshold | tool_threshold | Notes |
|----------|----------------|----------------|-------|
| **High Precision** | 0.7 | 0.6 | Few but highly relevant results |
| **Balanced** (default) | 0.4 | 0.3 | Good trade-off |
| **High Recall** | 0.2 | 0.1 | More results, may include noise |
| **No Filtering** | 0.0 | 0.0 | Return everything (not recommended) |

---

## Fallback Strategies

### Fallback Priority

1. **Hierarchical** (default) → If skill search fails → **Direct**
2. **Direct** → No fallback (search all tools)
3. **Hybrid** → Run both in parallel, merge results

### Graceful Degradation

| Failure | Fallback Behavior |
|---------|-------------------|
| Skill search timeout | Fall back to direct search |
| Skill search error | Fall back to direct search |
| No skills match | Fall back to direct search |
| Tool search error | Return empty results |
| Schema load error | Return tool without schema |
| Embedding error | Return empty results |

---

## API Contracts

### POST /api/v1/search
**Hierarchical Search**

**Request**: `application/json`
```json
{
  "query": "schedule a meeting with John",
  "item_type": "tool",
  "limit": 5,
  "skill_limit": 3,
  "skill_threshold": 0.4,
  "tool_threshold": 0.3,
  "include_schemas": true,
  "strategy": "hierarchical"
}
```

**Success Response**: `200 OK`
```json
{
  "query": "schedule a meeting with John",
  "tools": [
    {
      "id": "1",
      "db_id": 1,
      "type": "tool",
      "name": "create_calendar_event",
      "description": "Create a new event...",
      "score": 0.92,
      "skill_ids": ["calendar_management"],
      "primary_skill_id": "calendar_management",
      "input_schema": {...}
    }
  ],
  "matched_skills": [
    {
      "id": "calendar_management",
      "name": "Calendar Management",
      "description": "Tools for calendars...",
      "score": 0.87,
      "tool_count": 15
    }
  ],
  "metadata": {
    "strategy_used": "hierarchical",
    "skill_ids_used": ["calendar_management"],
    "stage1_skill_count": 2,
    "stage2_candidate_count": 15,
    "final_count": 5,
    "query_embedding_time_ms": 48.5,
    "skill_search_time_ms": 8.2,
    "tool_search_time_ms": 22.1,
    "schema_load_time_ms": 12.3,
    "total_time_ms": 91.1
  }
}
```

**Error Responses**:
- `400 Bad Request`: Invalid query (empty, too long)
- `422 Validation Error`: Invalid parameters (threshold out of range)
- `500 Internal Server Error`: Embedding/search failure

---

### GET /api/v1/search/skills
**Search Skills Only (Stage 1)**

**Query Parameters**:
- `query`: String (required)
- `limit`: Integer (optional, default: 5)
- `threshold`: Float (optional, default: 0.4)

**Success Response**: `200 OK`
```json
[
  {
    "id": "calendar_management",
    "name": "Calendar Management",
    "description": "...",
    "score": 0.87,
    "tool_count": 15
  }
]
```

---

### GET /api/v1/search/tools
**Search Tools with Skill Filter (Stage 2)**

**Query Parameters**:
- `query`: String (required)
- `skill_ids`: String (optional, comma-separated)
- `item_type`: String (optional)
- `limit`: Integer (optional, default: 10)
- `threshold`: Float (optional, default: 0.3)

**Success Response**: `200 OK`
```json
[
  {
    "id": "1",
    "db_id": 1,
    "type": "tool",
    "name": "create_calendar_event",
    "description": "...",
    "score": 0.92,
    "skill_ids": ["calendar_management"],
    "primary_skill_id": "calendar_management"
  }
]
```

---

## Performance SLAs

### Response Time Targets (p95)

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| Full Hierarchical Search | < 100ms | < 200ms |
| Skill Search (Stage 1) | < 15ms | < 50ms |
| Tool Search (Stage 2) | < 30ms | < 100ms |
| Schema Enrichment (5 tools) | < 20ms | < 50ms |
| Query Embedding | < 60ms | < 100ms |

### Throughput Targets

- Hierarchical searches: 100 req/s
- Concurrent embedding requests: 50 req/s

### Latency Breakdown (Target 100ms)

| Stage | Target | Percentage |
|-------|--------|------------|
| Query Embedding | 50ms | 50% |
| Skill Search | 10ms | 10% |
| Tool Search | 25ms | 25% |
| Schema Load | 15ms | 15% |

---

## Edge Cases

### EC-001: No Skills in Index
**Scenario**: Skill collection is empty (no skills seeded)
**Expected**: Fall back to direct search
**Solution**: Check skill count, skip Stage 1 if 0

---

### EC-002: All Skills Match
**Scenario**: Query is very generic, matches all skills highly
**Expected**: Return top `skill_limit` skills by score
**Solution**: Limit always applied, highest scores win

---

### EC-003: Skill Matches But No Tools
**Scenario**: Matched skills have 0 assigned tools
**Expected**: Return empty results (correct behavior)
**Solution**: Empty array is valid response

---

### EC-004: Very Long Query
**Scenario**: Query > 1000 characters
**Expected**: Reject with 422 Validation Error
**Solution**: Validate query length before processing

---

### EC-005: Special Characters in Query
**Scenario**: Query contains SQL injection, XSS, etc.
**Expected**: Query treated as literal text for embedding
**Solution**: No query parsing, direct to embedding model

---

### EC-006: Concurrent Same Query
**Scenario**: Same query submitted multiple times simultaneously
**Expected**: All return consistent results
**Solution**: Each request independent, no shared state

---

### EC-007: Skill Index Stale
**Scenario**: Skill embeddings not updated after tool changes
**Expected**: Search still works, may be suboptimal
**Solution**: Real-time updates (BR-004 in skill contract)

---

### EC-008: Tool Belongs to Zero Skills
**Scenario**: Tool exists but has no skill assignments
**Expected**: Tool excluded from hierarchical search
**Solution**: Tool should only appear in direct search mode

---

### EC-009: High Latency Embedding Service
**Scenario**: Embedding generation takes > 100ms
**Expected**: Search completes (slower), within max timeout
**Solution**: 10s timeout, graceful error handling

---

## Test Coverage Requirements

All tests MUST cover:

- ✅ Happy path (BR-XXX success scenarios)
- ✅ Both search strategies (hierarchical, direct)
- ✅ Fallback scenarios (no skills match)
- ✅ Item type filtering (tool, prompt, resource)
- ✅ Threshold variations (high, low, edge)
- ✅ Schema loading (with/without)
- ✅ Validation errors (422)
- ✅ Edge cases (EC-XXX scenarios)
- ✅ Performance within SLAs

---

**Version**: 1.0.0
**Last Updated**: 2025-12-11
**Owner**: MCP Search Team
