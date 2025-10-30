# Memory Tools Search Capabilities Summary

## Overview

This document clarifies the search capabilities available for each memory type in the Memory Tools MCP integration.

## Current Status (as of 2025-10-30)

### ✅ Fully Implemented Search

| Memory Type | Search Tool | Endpoint | Status |
|-------------|-------------|----------|--------|
| **Factual** | `search_facts_by_subject(user_id, subject, limit)` | `GET /memories/factual/search/subject` | ✅ Working |
| **Episodic** | `search_episodes_by_event_type(user_id, event_type, limit)` | `GET /memories/episodic/search/event_type` | ✅ Working |

### ⚠️ Placeholder Tools (Endpoints Not Implemented)

| Tool | Intended Endpoint | Status |
|------|-------------------|--------|
| `search_memories(...)` | `GET /memories/search` | ❌ Endpoint doesn't exist |
| `search_concepts_by_category(...)` | `GET /memories/semantic/search/category` | ❌ Endpoint doesn't exist |

### ✅ Alternative Retrieval Methods

| Memory Type | Retrieval Tool | Endpoint | Status |
|-------------|----------------|----------|--------|
| **Working** | `get_active_working_memories(user_id)` | `GET /memories/working/active` | ✅ Working |
| **Session** | `get_session_context(user_id, session_id, ...)` | `GET /memories/session/{session_id}` | ✅ Working |

### ❌ Not Yet Implemented

| Memory Type | Search Capability | Status |
|-------------|-------------------|--------|
| **Procedural** | No search endpoint | ❌ Not implemented |
| **Semantic** | Placeholder tool exists, endpoint missing | ⚠️ Partial |

---

## Changes Made

### 1. Added Missing Tool ✅
- **New Tool**: `search_episodes_by_event_type`
  - Location: `tools/memory_tools/memory_tools.py:354-384`
  - Client method: `tools/memory_tools/memory_client.py:316-327`
  - Uses existing endpoint: `GET /memories/episodic/search/event_type`

### 2. Documented Placeholder Tools ⚠️
- **Updated**: `search_memories` - Added note that endpoint doesn't exist
  - Location: `tools/memory_tools/memory_tools.py:273-322`
  - Recommends using type-specific search tools instead

- **Updated**: `search_concepts_by_category` - Added note that endpoint doesn't exist
  - Location: `tools/memory_tools/memory_tools.py:386-421`
  - Kept as placeholder for future implementation

### 3. Updated Documentation 📝
- **File**: `tools/memory_tools/docs/how_to_memory.md`
- **Changes**:
  - Updated tool count: 14 → 15 tools
  - Added "Search Capabilities by Memory Type" section
  - Added example for episodic search
  - Clarified which tools are working vs. placeholders
  - Added tool breakdown in summary

---

## Usage Examples

### Working Search Tools

#### 1. Search Factual Memories by Subject
```python
result = await mcp.call_tool(
    "search_facts_by_subject",
    user_id="user_123",
    subject="Python",
    limit=10
)
```

#### 2. Search Episodic Memories by Event Type
```python
result = await mcp.call_tool(
    "search_episodes_by_event_type",
    user_id="user_123",
    event_type="meeting",
    limit=10
)
```

#### 3. Get Active Working Memories
```python
result = await mcp.call_tool(
    "get_active_working_memories",
    user_id="user_123"
)
```

#### 4. Get Session Context
```python
result = await mcp.call_tool(
    "get_session_context",
    user_id="user_123",
    session_id="session_456",
    include_summaries=True,
    max_recent_messages=10
)
```

---

## Future Enhancements Needed

To provide complete search coverage, the memory microservice needs:

1. **Generic Semantic Search** (`POST /memories/search`)
   - Cross-type vector similarity search
   - Filter by memory types
   - Configurable similarity threshold

2. **Semantic Concept Search** (`GET /memories/semantic/search/category`)
   - Search by concept category
   - Return related concepts

3. **Procedural Search** (`GET /memories/procedural/search/...`)
   - Search by skill type
   - Search by domain
   - Search by difficulty level

---

## Tool Count Summary

**Total MCP Tools**: 15
- **Storage**: 6 (all working)
- **Search**: 4 (2 working, 2 placeholders)
- **Retrieval**: 3 (all working)
- **Utility**: 2 (all working)

**Working Tools**: 13/15 (87%)
**Placeholder Tools**: 2/15 (13%)

---

## Related Files

- Tool Implementation: `tools/memory_tools/memory_tools.py`
- HTTP Client: `tools/memory_tools/memory_client.py`
- Documentation: `tools/memory_tools/docs/how_to_memory.md`
- Test Suite: `tools/memory_tools/tests/test_memory_tools.sh`

