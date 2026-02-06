# Skill-Based Hierarchical Search System Design

**Technical Architecture for ISA MCP Hierarchical Search**

This document outlines the technical design for a hierarchical skill-based search system that enables efficient tool discovery at scale (1000s of tools).

---

## Related Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Domain | [docs/domain/README.md](../domain/README.md) | Business context, taxonomy |
| PRD | [docs/prd/README.md](../prd/README.md) | User stories, requirements |
| Environment | [docs/env/README.md](../env/README.md) | Configuration contract |
| Skill Data Contract | [tests/contracts/skill/data_contract.py](../../tests/contracts/skill/data_contract.py) | Pydantic schemas |
| Skill Logic Contract | [tests/contracts/skill/logic_contract.md](../../tests/contracts/skill/logic_contract.md) | Business rules |
| Search Data Contract | [tests/contracts/search/data_contract.py](../../tests/contracts/search/data_contract.py) | Pydantic schemas |
| Search Logic Contract | [tests/contracts/search/logic_contract.md](../../tests/contracts/search/logic_contract.md) | Business rules |

---

## Overview

### Design Decisions (Based on Requirements)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Skill Origin | Auto-discovered within predefined schema | LLM clusters tools, but constrained to valid skill categories |
| Hierarchy | 2-Level (Skill → Tools) | Simple, fast, easy to debug |
| Tool Membership | Multiple Skills | A tool can belong to multiple skills for flexible retrieval |
| Retrieval Strategy | Sequential (Skill → Tools) | First find skills, then search tools within matched skills |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SYNC PHASE (Write Path)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────┐   │
│  │  New Tool    │───▶│  LLM Classifier  │───▶│  Skill Assignment   │   │
│  │  (from MCP)  │    │  (categorize to  │    │  (multi-skill OK)   │   │
│  │              │    │   skill schema)  │    │                     │   │
│  └──────────────┘    └──────────────────┘    └──────────┬──────────┘   │
│                                                          │              │
│                              ┌───────────────────────────┼───────────┐  │
│                              ▼                           ▼           │  │
│                    ┌─────────────────┐         ┌─────────────────┐   │  │
│                    │  Skills Index   │         │  Tools Index    │   │  │
│                    │  (Qdrant)       │         │  (Qdrant)       │   │  │
│                    │                 │         │                 │   │  │
│                    │  - skill_id     │         │  - tool_id      │   │  │
│                    │  - name         │         │  - name         │   │  │
│                    │  - description  │         │  - description  │   │  │
│                    │  - embedding    │         │  - skill_ids[]  │   │  │
│                    │  - tool_count   │         │  - embedding    │   │  │
│                    │  - metadata     │         │  - metadata     │   │  │
│                    └─────────────────┘         └─────────────────┘   │  │
│                                                                      │  │
│                    ┌─────────────────┐                               │  │
│                    │  Skills Table   │  (PostgreSQL - Source of Truth) │
│                    │  (predefined    │                               │  │
│                    │   schema)       │                               │  │
│                    └─────────────────┘                               │  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         SEARCH PHASE (Read Path)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  User Query: "schedule a meeting with John tomorrow"                     │
│                              │                                           │
│                              ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Stage 1: Skill Retrieval                                          │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  Query embedding → Search Skills Index → Top K skills       │  │  │
│  │  │  Result: ["calendar_management", "communication"] (score>τ) │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              │                                           │
│                              ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Stage 2: Tool Retrieval (Filtered)                                │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  Query embedding → Search Tools Index                       │  │  │
│  │  │  Filter: skill_ids CONTAINS ANY ["calendar_management",     │  │  │
│  │  │          "communication"]                                   │  │  │
│  │  │  Result: ["create_calendar_event", "send_meeting_invite"]   │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              │                                           │
│                              ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Stage 3: Schema Enrichment (Lazy Load)                            │  │
│  │  Only fetch full inputSchema for top N tools from PostgreSQL      │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              │                                           │
│                              ▼                                           │
│         Return: 3-5 tools with minimal context for model consumption     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### 1. Skill Schema (Predefined Categories)

The skill schema defines the valid categories that LLM can assign tools to. This is **human-controlled** and stored in PostgreSQL.

```python
@dataclass
class SkillCategory:
    """Predefined skill category schema - human managed"""
    id: str                          # e.g., "calendar_management"
    name: str                        # e.g., "Calendar Management"
    description: str                 # What this skill category covers
    parent_domain: Optional[str]     # Optional grouping (for future 3-level)
    keywords: List[str]              # Hint keywords for LLM classification
    examples: List[str]              # Example tool names that belong here
    is_active: bool
    created_at: datetime
    updated_at: datetime

# Example predefined skills:
SKILL_SCHEMA = [
    SkillCategory(
        id="calendar_management",
        name="Calendar Management",
        description="Tools for managing calendars, events, scheduling, and appointments",
        keywords=["calendar", "event", "schedule", "meeting", "appointment", "reminder"],
        examples=["create_event", "list_events", "delete_event", "update_event"]
    ),
    SkillCategory(
        id="data_query",
        name="Data Query & Analysis",
        description="Tools for querying databases, searching data, and analysis",
        keywords=["query", "sql", "database", "search", "filter", "aggregate"],
        examples=["query_database", "search_records", "get_statistics"]
    ),
    SkillCategory(
        id="file_operations",
        name="File Operations",
        description="Tools for reading, writing, and managing files",
        keywords=["file", "read", "write", "upload", "download", "delete"],
        examples=["read_file", "write_file", "list_files", "upload_file"]
    ),
    # ... more categories
]
```

### 2. Skill Instance (Auto-Generated)

When LLM assigns tools to skills, it creates/updates skill instances with aggregated embeddings.

```python
@dataclass
class SkillInstance:
    """Auto-generated skill instance in vector DB"""
    id: str                          # Same as SkillCategory.id
    name: str
    description: str                 # LLM-enhanced description based on tools
    embedding: List[float]           # Aggregated embedding of skill
    tool_count: int                  # Number of tools in this skill
    tool_ids: List[int]              # Reference to tools (for stats)
    metadata: Dict[str, Any]         # Additional info
    updated_at: datetime
```

### 3. Tool with Skill Assignment

```python
@dataclass
class ToolWithSkills:
    """Tool with multi-skill assignment"""
    id: int
    name: str
    description: str
    embedding: List[float]
    skill_ids: List[str]             # Can belong to multiple skills
    primary_skill_id: str            # Main skill (highest confidence)
    skill_confidence: Dict[str, float]  # Confidence scores per skill
    input_schema: Dict[str, Any]
    metadata: Dict[str, Any]
```

---

## Sync Phase: Intelligent Tool Classification

### LLM Classification Prompt

```python
CLASSIFICATION_PROMPT = """
You are a tool classifier. Given a tool's name and description, assign it to one or more skill categories.

## Available Skill Categories:
{skill_categories_json}

## Tool to Classify:
Name: {tool_name}
Description: {tool_description}
Input Schema: {input_schema_summary}

## Instructions:
1. Analyze the tool's purpose and functionality
2. Assign to 1-3 most relevant skill categories (prefer fewer, more accurate assignments)
3. Provide confidence score (0.0-1.0) for each assignment
4. If no category fits well (confidence < 0.5), suggest a new category name

## Output Format (JSON):
{
    "assignments": [
        {"skill_id": "calendar_management", "confidence": 0.95, "reasoning": "..."},
        {"skill_id": "communication", "confidence": 0.6, "reasoning": "..."}
    ],
    "primary_skill_id": "calendar_management",
    "suggested_new_skill": null  // or {"name": "...", "description": "..."} if needed
}
"""
```

### Classification Flow

```python
class ToolClassifier:
    """LLM-based tool classifier"""

    async def classify_tool(
        self,
        tool: ToolData,
        skill_schema: List[SkillCategory]
    ) -> ToolClassification:
        """
        Classify a tool into skill categories using LLM

        Returns:
            ToolClassification with skill assignments and confidences
        """
        # 1. Build prompt with skill schema
        prompt = self._build_classification_prompt(tool, skill_schema)

        # 2. Call LLM
        response = await self.llm_client.chat(prompt)

        # 3. Parse and validate response
        classification = self._parse_classification(response)

        # 4. Filter by confidence threshold
        valid_assignments = [
            a for a in classification.assignments
            if a.confidence >= self.min_confidence
        ]

        # 5. Handle suggested new skills (queue for human review)
        if classification.suggested_new_skill:
            await self._queue_skill_suggestion(classification.suggested_new_skill)

        return ToolClassification(
            tool_id=tool.id,
            skill_ids=[a.skill_id for a in valid_assignments],
            primary_skill_id=classification.primary_skill_id,
            confidence_scores={a.skill_id: a.confidence for a in valid_assignments}
        )
```

### Skill Embedding Strategy

For skill embeddings, we have several options:

#### Option A: Aggregated Tool Embeddings (Recommended)
```python
async def update_skill_embedding(self, skill_id: str):
    """Update skill embedding by aggregating its tools' embeddings"""
    # Get all tools in this skill
    tools = await self.get_tools_by_skill(skill_id)

    if not tools:
        return

    # Weighted average of tool embeddings (weight by confidence)
    embeddings = []
    weights = []
    for tool in tools:
        embeddings.append(tool.embedding)
        weights.append(tool.skill_confidence.get(skill_id, 1.0))

    # Compute weighted centroid
    skill_embedding = np.average(embeddings, axis=0, weights=weights)
    skill_embedding = skill_embedding / np.linalg.norm(skill_embedding)  # Normalize

    await self.skill_repo.update_embedding(skill_id, skill_embedding.tolist())
```

#### Option B: LLM-Generated Skill Description Embedding
```python
async def generate_skill_embedding(self, skill_id: str):
    """Generate skill embedding from LLM-enhanced description"""
    skill = await self.skill_repo.get(skill_id)
    tools = await self.get_tools_by_skill(skill_id)

    # Ask LLM to generate comprehensive skill description
    enhanced_description = await self.llm_client.chat(f"""
        Based on these tools: {[t.name for t in tools]}
        Enhance this skill description for semantic search:
        Original: {skill.description}

        Output a 2-3 sentence description that captures what this skill enables.
    """)

    # Generate embedding from enhanced description
    embedding = await self.embedding_service.embed(enhanced_description)
    await self.skill_repo.update_embedding(skill_id, embedding)
```

**Recommendation**: Use Option A (aggregated embeddings) for consistency and lower LLM costs. Option B can be used for initial skill creation.

---

## Search Phase: Sequential Hierarchical Retrieval

### Search Algorithm

```python
class HierarchicalSearchService:
    """Two-stage hierarchical search: Skills → Tools"""

    async def search(
        self,
        query: str,
        item_type: Optional[str] = None,  # tool/prompt/resource
        limit: int = 5,
        skill_limit: int = 3,
        skill_threshold: float = 0.4,
        tool_threshold: float = 0.3,
    ) -> SearchResult:
        """
        Hierarchical search with skill routing

        Args:
            query: User's natural language query
            item_type: Filter by type
            limit: Max tools to return
            skill_limit: Max skills to match in stage 1
            skill_threshold: Min similarity for skill matching
            tool_threshold: Min similarity for tool matching

        Returns:
            SearchResult with matched tools and metadata
        """
        # Generate query embedding once (reused for both stages)
        query_embedding = await self.embedding_service.embed(query)

        # ============ Stage 1: Skill Retrieval ============
        matched_skills = await self.skill_repo.search(
            query_embedding=query_embedding,
            limit=skill_limit,
            score_threshold=skill_threshold
        )

        # Log skill matches for debugging
        logger.info(f"Stage 1 - Matched skills: {[(s.id, s.score) for s in matched_skills]}")

        # If no skills match, fall back to unfiltered search
        if not matched_skills:
            logger.warning("No skills matched, falling back to unfiltered search")
            skill_ids = None
        else:
            skill_ids = [s.id for s in matched_skills]

        # ============ Stage 2: Tool Retrieval (Filtered) ============
        matched_tools = await self.tool_repo.search(
            query_embedding=query_embedding,
            skill_ids=skill_ids,  # Filter by matched skills
            item_type=item_type,
            limit=limit,
            score_threshold=tool_threshold
        )

        logger.info(f"Stage 2 - Matched tools: {[(t.name, t.score) for t in matched_tools]}")

        # ============ Stage 3: Lazy Schema Loading ============
        # Only load full schemas for top results (minimize context)
        enriched_tools = await self._enrich_top_tools(matched_tools, limit=limit)

        return SearchResult(
            tools=enriched_tools,
            matched_skills=matched_skills,
            query=query,
            search_metadata={
                "skill_ids_used": skill_ids,
                "stage1_count": len(matched_skills),
                "stage2_count": len(matched_tools),
            }
        )

    async def _enrich_top_tools(
        self,
        tools: List[ToolMatch],
        limit: int
    ) -> List[EnrichedTool]:
        """Load full schemas only for top N tools"""
        enriched = []
        for tool in tools[:limit]:
            full_data = await self.tool_service.get_tool_by_id(tool.db_id)
            enriched.append(EnrichedTool(
                id=tool.id,
                name=tool.name,
                description=tool.description,
                score=tool.score,
                skill_ids=tool.skill_ids,
                input_schema=full_data.get('input_schema') if full_data else None,
            ))
        return enriched
```

---

## Database Schema

### PostgreSQL Tables

```sql
-- Predefined skill categories (human-managed)
CREATE TABLE mcp.skill_categories (
    id VARCHAR(64) PRIMARY KEY,           -- e.g., "calendar_management"
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_domain VARCHAR(64),            -- For future 3-level hierarchy
    keywords TEXT[],                       -- Hint keywords for LLM
    examples TEXT[],                       -- Example tool names
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tool-to-skill assignments (auto-generated)
CREATE TABLE mcp.tool_skill_assignments (
    id SERIAL PRIMARY KEY,
    tool_id INTEGER REFERENCES mcp.tools(id) ON DELETE CASCADE,
    skill_id VARCHAR(64) REFERENCES mcp.skill_categories(id),
    confidence FLOAT NOT NULL,            -- LLM confidence score
    is_primary BOOLEAN DEFAULT FALSE,     -- Primary skill flag
    assigned_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(tool_id, skill_id)
);

-- Index for efficient lookups
CREATE INDEX idx_tool_skill_tool ON mcp.tool_skill_assignments(tool_id);
CREATE INDEX idx_tool_skill_skill ON mcp.tool_skill_assignments(skill_id);

-- Skill suggestions queue (for human review)
CREATE TABLE mcp.skill_suggestions (
    id SERIAL PRIMARY KEY,
    suggested_name VARCHAR(255) NOT NULL,
    suggested_description TEXT,
    source_tool_id INTEGER REFERENCES mcp.tools(id),
    status VARCHAR(32) DEFAULT 'pending', -- pending/approved/rejected
    reviewed_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Qdrant Collections

```python
# Collection 1: Skills Index
SKILLS_COLLECTION = {
    "name": "mcp_skills",
    "vector_size": 1536,
    "distance": "Cosine",
    "payload_schema": {
        "id": "keyword",           # skill_id
        "name": "text",
        "description": "text",
        "tool_count": "integer",
        "is_active": "bool",
    }
}

# Collection 2: Tools Index (modified)
TOOLS_COLLECTION = {
    "name": "mcp_unified_search",  # Existing collection
    "vector_size": 1536,
    "distance": "Cosine",
    "payload_schema": {
        "type": "keyword",         # tool/prompt/resource
        "name": "text",
        "description": "text",
        "db_id": "integer",
        "skill_ids": "keyword[]",  # NEW: array of skill IDs
        "primary_skill_id": "keyword",  # NEW: primary skill
        "is_active": "bool",
    }
}
```

---

## Implementation Plan

### Phase 1: Foundation (Database & Models)
1. Create PostgreSQL tables for skill_categories and tool_skill_assignments
2. Define data models (SkillCategory, ToolSkillAssignment, etc.)
3. Create SkillRepository for PostgreSQL operations
4. Add skill_ids field to existing vector payload

### Phase 2: Sync Intelligence (LLM Classification)
1. Implement ToolClassifier with LLM integration
2. Implement skill embedding generation (aggregated approach)
3. Modify SyncService to classify tools during sync
4. Create SkillSyncService for skill index management

### Phase 3: Hierarchical Search
1. Create new Qdrant collection for skills
2. Implement HierarchicalSearchService with 2-stage retrieval
3. Add fallback logic for unmatched skills
4. Implement lazy schema loading

### Phase 4: API & Integration
1. Update search endpoints to use hierarchical search
2. Add skill management endpoints (CRUD for skill categories)
3. Add skill suggestion review workflow
4. Performance testing and tuning

---

## Performance Considerations

### Expected Latencies
| Operation | Latency |
|-----------|---------|
| Query embedding generation | ~50ms |
| Stage 1: Skill search (10-50 skills) | ~5ms |
| Stage 2: Tool search (filtered) | ~20ms |
| Schema enrichment (top 5) | ~10ms |
| **Total** | **~85ms** |

### Optimization Strategies
1. **Embedding caching**: Cache query embeddings for repeated searches
2. **Skill index in memory**: For <100 skills, keep in-memory copy
3. **Batch schema loading**: Load schemas in parallel
4. **Skill warmup**: Pre-compute skill embeddings on startup

### Context Output Reduction
| Scenario | Tools Searched | Tools Returned | Context Tokens |
|----------|---------------|----------------|----------------|
| Current (no skills) | 1000 | 10 | ~50k tokens |
| With skills (filtered) | 50-100 | 5 | ~5k tokens |
| **Reduction** | - | - | **~90%** |

---

## Resolved Design Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Skill embedding update frequency | **Real-time** | Update immediately when tools change for accuracy |
| Initial skill categories | **Seed from existing tools** | Analyze current tools, propose categories |
| LLM for classification | **ISA Model** | Use existing infrastructure |
| Confidence threshold | Start with **0.5**, tune based on metrics | Conservative default |

---

## TDD Development Plan

### Contract-Driven Development

This feature follows CDD methodology. See [docs/cdd_guide.md](../cdd_guide.md) for the full approach.

### Test Contracts

| Service | Data Contract | Logic Contract |
|---------|---------------|----------------|
| Skill Service | [data_contract.py](../../tests/contracts/skill/data_contract.py) | [logic_contract.md](../../tests/contracts/skill/logic_contract.md) |
| Search Service | [data_contract.py](../../tests/contracts/search/data_contract.py) | [logic_contract.md](../../tests/contracts/search/logic_contract.md) |

### Test Layers

```
tests/
├── unit/           # Pure logic tests
├── component/      # Service-level tests (mocked dependencies)
├── integration/    # Real database tests
└── api/            # HTTP endpoint tests
```

---

**Version**: 1.0.0
**Last Updated**: 2025-12-11
**Owner**: ISA MCP Team
