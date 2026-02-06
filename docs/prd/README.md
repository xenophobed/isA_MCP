# ISA MCP - Product Requirements Document (PRD)

**Skill-Based Hierarchical Search System**

This document defines user stories, requirements, and acceptance criteria for the ISA MCP platform.

---

## Table of Contents

1. [Overview](#overview)
2. [Epic: Skill-Based Search](#epic-skill-based-search)
3. [User Stories](#user-stories)
4. [Non-Functional Requirements](#non-functional-requirements)
5. [Acceptance Criteria Summary](#acceptance-criteria-summary)

---

## Overview

### Problem Statement

As MCP tool registries grow to thousands of tools, the current flat search approach faces critical challenges:

1. **Context Bloat**: Loading all tool schemas consumes too many tokens
2. **Poor Relevance**: Simple similarity search returns irrelevant tools
3. **Slow Discovery**: Searching 1000s of tools is inefficient
4. **No Organization**: Tools lack logical grouping

### Solution

Implement a **Skill-Based Hierarchical Search System** that:

1. Groups tools into skill categories (human-managed schema)
2. Uses LLM to auto-classify tools into skills
3. Performs two-stage search: skills first, then tools
4. Loads schemas lazily for minimal context output

### Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Context tokens per search | ~50k | <5k |
| Search latency (p95) | ~200ms | <100ms |
| Relevant tool in top-3 | ~60% | >90% |
| Tools searched per query | 1000+ | 50-100 |

---

## Epic: Skill-Based Search

### Epic ID: SK

**Description**: Enable intelligent tool discovery through skill-based hierarchical search, reducing context overhead while improving relevance.

### Epic Scope

| In Scope | Out of Scope |
|----------|--------------|
| Skill category schema definition | 3+ level hierarchy |
| LLM-based tool classification | Manual tool-skill assignment UI |
| Two-stage hierarchical search | Real-time skill suggestions |
| Lazy schema loading | Cross-tenant skill sharing |
| Fallback to direct search | Skill-based access control |

---

## User Stories

### SK-US1: Skill-Based Tool Search

**Story ID**: SK-US1
**Priority**: P0 (Must Have)
**Status**: 🔄 In Progress

**As an** MCP Client (LLM Application)
**I want** to search for tools using skill-based hierarchical routing
**So that** I get the most relevant tools with minimal context consumption

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | Given a natural language query, the system returns a hierarchical search response with matched skills and tools | ⏳ |
| AC2 | Given skill matches (score >= threshold), tools are filtered by matched skill IDs | ⏳ |
| AC3 | Given no skill matches (all scores < threshold), the system falls back to direct tool search | ⏳ |
| AC4 | Given `include_schemas=true`, the response includes input_schema for returned tools | ⏳ |
| AC5 | Given `include_schemas=false`, the response excludes input_schema (metadata only) | ⏳ |
| AC6 | Response time (p95) is < 100ms for hierarchical search | ⏳ |
| AC7 | Context tokens in response are < 5000 for top-5 tools | ⏳ |

#### API Contract

**Request**:
```json
POST /api/v1/search
{
  "query": "schedule a meeting with John tomorrow",
  "item_type": "tool",
  "limit": 5,
  "skill_limit": 3,
  "skill_threshold": 0.4,
  "tool_threshold": 0.3,
  "include_schemas": true,
  "strategy": "hierarchical"
}
```

**Response**:
```json
{
  "query": "schedule a meeting with John tomorrow",
  "tools": [...],
  "matched_skills": [...],
  "metadata": {
    "strategy_used": "hierarchical",
    "skill_ids_used": ["calendar_management"],
    "total_time_ms": 85.2
  }
}
```

---

### SK-US2: Tool Classification on Sync

**Story ID**: SK-US2
**Priority**: P0 (Must Have)
**Status**: 🔄 In Progress

**As a** System Administrator
**I want** tools to be automatically classified into skills when synced
**So that** new tools are immediately discoverable via skill-based search

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | When a new tool is synced, LLM classifies it into 1-3 skill categories | ⏳ |
| AC2 | Classification includes confidence scores (0.0-1.0) for each skill assignment | ⏳ |
| AC3 | Primary skill is determined (highest confidence >= 0.5) | ⏳ |
| AC4 | If no valid skill matches (all confidence < 0.5), tool is assigned to "uncategorized" | ⏳ |
| AC5 | If LLM suggests new skill, suggestion is queued for human review | ⏳ |
| AC6 | Skill embeddings are updated in real-time after classification | ⏳ |
| AC7 | Classification completes within 2 seconds per tool | ⏳ |

#### Classification Flow

```
New Tool → LLM Classifier → Skill Assignments → Index Updates
              │                    │                  │
              ▼                    ▼                  ▼
         Prompt with          1-3 skills        - PostgreSQL
         skill schema         + confidence      - Qdrant (tools)
                              + primary         - Qdrant (skills)
```

---

### SK-US3: Skill Category Management

**Story ID**: SK-US3
**Priority**: P1 (Should Have)
**Status**: ⏳ Pending

**As a** Platform Administrator
**I want** to manage skill categories (CRUD operations)
**So that** I can control the skill schema that tools are classified into

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | Admin can create a new skill category with id, name, description, keywords, examples | ⏳ |
| AC2 | Admin can update an existing skill category | ⏳ |
| AC3 | Admin can deactivate a skill category (soft delete) | ⏳ |
| AC4 | Admin can list all skill categories with tool counts | ⏳ |
| AC5 | Skill ID must be unique and match pattern `^[a-z][a-z0-9_]*$` | ⏳ |
| AC6 | When skill is deactivated, existing tool assignments remain but skill is excluded from search | ⏳ |

#### API Contract

**Create Skill**:
```json
POST /api/v1/skills
{
  "id": "calendar_management",
  "name": "Calendar Management",
  "description": "Tools for managing calendars, events, and scheduling",
  "keywords": ["calendar", "event", "schedule", "meeting"],
  "examples": ["create_event", "list_events"]
}
```

---

### SK-US4: Skill Suggestion Review

**Story ID**: SK-US4
**Priority**: P2 (Nice to Have)
**Status**: ⏳ Pending

**As a** Platform Administrator
**I want** to review skill suggestions from LLM classification
**So that** I can approve or reject new skill categories

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | Admin can list pending skill suggestions | ⏳ |
| AC2 | Admin can approve suggestion (creates new skill category) | ⏳ |
| AC3 | Admin can reject suggestion with reason | ⏳ |
| AC4 | Approved skill triggers re-classification of source tool | ⏳ |
| AC5 | Suggestions include source tool information | ⏳ |

---

### SK-US5: Direct Search Strategy

**Story ID**: SK-US5
**Priority**: P1 (Should Have)
**Status**: ⏳ Pending

**As an** MCP Client
**I want** to bypass skill routing and search tools directly
**So that** I can perform quick searches without skill overhead

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | Given `strategy="direct"`, skill search is skipped | ⏳ |
| AC2 | Direct search returns tools from entire index (no skill filter) | ⏳ |
| AC3 | Response includes `matched_skills: []` and `skill_ids_used: null` | ⏳ |
| AC4 | Direct search latency < 80ms (p95) | ⏳ |

---

### SK-US6: Skill-Only Search

**Story ID**: SK-US6
**Priority**: P2 (Nice to Have)
**Status**: ⏳ Pending

**As an** MCP Client
**I want** to search only for matching skills (without tool search)
**So that** I can understand which skill categories match a query

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | GET /api/v1/search/skills returns matching skills only | ⏳ |
| AC2 | Response includes skill metadata and tool_count | ⏳ |
| AC3 | Supports threshold and limit parameters | ⏳ |
| AC4 | Skill search latency < 20ms (p95) | ⏳ |

---

### SK-US7: Batch Tool Classification

**Story ID**: SK-US7
**Priority**: P1 (Should Have)
**Status**: ⏳ Pending

**As a** System Administrator
**I want** to classify existing tools in batch
**So that** I can seed skill assignments for tools registered before skill system

#### Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | Admin can trigger batch classification for all unclassified tools | ⏳ |
| AC2 | Batch processes tools in parallel (configurable concurrency) | ⏳ |
| AC3 | Progress is reported (processed/total/errors) | ⏳ |
| AC4 | Failed classifications are logged and can be retried | ⏳ |
| AC5 | Batch completes within 5 minutes for 1000 tools | ⏳ |

---

## Non-Functional Requirements

### Performance Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| **NFR-P1**: Hierarchical search latency | < 100ms (p95) | End-to-end response time |
| **NFR-P2**: Direct search latency | < 80ms (p95) | End-to-end response time |
| **NFR-P3**: Skill search latency | < 20ms (p95) | Skill index query |
| **NFR-P4**: Tool classification latency | < 2s per tool | LLM call + processing |
| **NFR-P5**: Search throughput | > 100 req/s | Concurrent requests |

### Reliability Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| **NFR-R1**: Search availability | > 99.9% | Uptime |
| **NFR-R2**: Fallback success rate | 100% | When skills don't match |
| **NFR-R3**: Classification success rate | > 95% | Valid skill assignments |

### Scalability Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| **NFR-S1**: Tool capacity | 10,000+ tools | Index size |
| **NFR-S2**: Skill capacity | 100+ skills | Skill categories |
| **NFR-S3**: Concurrent searches | 500+ | Simultaneous requests |

### Context Optimization Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| **NFR-C1**: Context per search | < 5000 tokens | Top-5 tool response |
| **NFR-C2**: Context reduction | > 90% | vs. current approach |
| **NFR-C3**: Schema size | < 500 tokens/tool | input_schema average |

---

## Acceptance Criteria Summary

### Must Pass Before Release

| Story | Critical AC | Status |
|-------|-------------|--------|
| SK-US1 | AC1, AC2, AC3, AC6 | ⏳ |
| SK-US2 | AC1, AC2, AC3, AC6 | ⏳ |
| SK-US3 | AC1, AC4 | ⏳ |
| SK-US5 | AC1, AC2 | ⏳ |

### Quality Gates

| Gate | Criteria | Target |
|------|----------|--------|
| **Unit Tests** | Coverage on business logic | > 80% |
| **Component Tests** | Service-level integration | > 70% |
| **Integration Tests** | End-to-end flows | All happy paths |
| **Performance Tests** | Latency SLAs | All NFR-P* met |

---

## Related Documents

- [Domain - Business Context](../domain/README.md)
- [Design - Architecture](../design/README.md)
- [Environment - Configuration](../env/README.md)
- [Logic Contract - Skill Service](../../tests/contracts/skill/logic_contract.md)
- [Logic Contract - Search Service](../../tests/contracts/search/logic_contract.md)

---

**Version**: 1.0.0
**Last Updated**: 2025-12-11
**Owner**: ISA MCP Team
