# ISA MCP - Domain Documentation

**Model Context Protocol (MCP) Server Platform**

This document provides the domain knowledge foundation for the ISA MCP platform, covering taxonomy, business scenarios, and domain concepts.

---

## Table of Contents

1. [Platform Overview](#platform-overview)
2. [Domain Taxonomy](#domain-taxonomy)
3. [Component Lifecycle](#component-lifecycle)
4. [Business Scenarios](#business-scenarios)
5. [Skill-Based Architecture](#skill-based-architecture)
6. [Glossary](#glossary)

---

## Platform Overview

### What is ISA MCP?

ISA MCP is an enterprise-grade **Model Context Protocol (MCP) Server** that provides:

- **Unified Tool Interface**: Single API for registering, discovering, and invoking MCP tools
- **Intelligent Discovery**: Skill-based hierarchical search for optimal tool matching
- **Multi-Provider Support**: Connect to multiple MCP servers and aggregate tools
- **Resilient Infrastructure**: Automatic sync, caching, and fallback mechanisms
- **Full Lifecycle Management**: From tool registration to invocation to monitoring

### Core Value Propositions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ISA MCP VALUE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  UNIFIED     │  │ INTELLIGENT  │  │   CONTEXT    │  │    FULL      │    │
│  │   REGISTRY   │  │  DISCOVERY   │  │ OPTIMIZATION │  │  LIFECYCLE   │    │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤  ├──────────────┤    │
│  │ One API for  │  │ Skill-based  │  │ Minimal      │  │ Register →   │    │
│  │ all tools    │  │ routing      │  │ context      │  │ Discover →   │    │
│  │ Multi-server │  │ Semantic     │  │ output       │  │ Invoke →     │    │
│  │ aggregation  │  │ search       │  │ Lazy loading │  │ Monitor      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Domain Taxonomy

### 1. MCP Component Types

```
MCP Components
├── Tools
│   ├── User Tools (User-facing operations)
│   │   ├── Calendar Tools (events, scheduling)
│   │   ├── Communication Tools (email, messaging)
│   │   ├── Data Tools (query, analysis)
│   │   └── File Tools (read, write, manage)
│   │
│   └── Service Tools (Internal operations)
│       ├── Sync Tools (data synchronization)
│       ├── Admin Tools (configuration)
│       └── Utility Tools (helpers)
│
├── Prompts
│   ├── System Prompts (instructions)
│   ├── Template Prompts (reusable patterns)
│   └── Dynamic Prompts (context-aware)
│
└── Resources
    ├── Static Resources (files, configs)
    ├── Dynamic Resources (APIs, databases)
    └── Computed Resources (derived data)
```

### 2. Skill Categories (Predefined Schema)

```
Skills (Hierarchical Organization)
├── Productivity Skills
│   ├── calendar_management
│   ├── task_management
│   ├── note_taking
│   └── time_tracking
│
├── Communication Skills
│   ├── email_operations
│   ├── messaging
│   ├── notifications
│   └── collaboration
│
├── Data Skills
│   ├── data_query
│   ├── data_analysis
│   ├── data_visualization
│   └── data_export
│
├── File Skills
│   ├── file_operations
│   ├── document_processing
│   ├── media_handling
│   └── cloud_storage
│
├── Integration Skills
│   ├── api_integration
│   ├── webhook_management
│   ├── third_party_services
│   └── automation
│
└── System Skills
    ├── configuration
    ├── monitoring
    ├── security
    └── administration
```

### 3. Service Types

| Service Type | Description | Primary Responsibility |
|-------------|-------------|------------------------|
| **ToolService** | Tool management | CRUD operations for tools |
| **PromptService** | Prompt management | Template and dynamic prompts |
| **ResourceService** | Resource management | Static and dynamic resources |
| **SearchService** | Tool discovery | Hierarchical search, skill routing |
| **SkillService** | Skill management | Classification, assignment, embedding |
| **SyncService** | Data synchronization | MCP server sync, index updates |

### 4. Provider Categories

```
MCP Providers
├── Internal Providers
│   ├── ISA Tools (built-in tools)
│   ├── ISA Prompts (system prompts)
│   └── ISA Resources (platform resources)
│
├── External Providers
│   ├── GitHub (repository tools)
│   ├── Slack (communication tools)
│   ├── Google (calendar, drive tools)
│   └── Custom MCP Servers
│
└── Aggregated Providers
    ├── Multi-server aggregation
    └── Federated discovery
```

---

## Component Lifecycle

### Lifecycle Stages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMPONENT LIFECYCLE                                   │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
    │ REGISTER│────▶│ CLASSIFY│────▶│  INDEX  │────▶│ DISCOVER│
    └─────────┘     └─────────┘     └─────────┘     └─────────┘
         │               │               │               │
         ▼               ▼               ▼               ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
    │ Tool    │     │ LLM     │     │ Vector  │     │ Search  │
    │ metadata│     │ assigns │     │ embed + │     │ + Match │
    │ + schema│     │ skills  │     │ store   │     │ + Rank  │
    └─────────┘     └─────────┘     └─────────┘     └─────────┘
         │               │               │               │
         └───────────────┴───────────────┴───────────────┘
                                │
                                ▼
                        ┌─────────────┐
                        │   INVOKE    │
                        │  (Execute)  │
                        └─────────────┘
```

### Stage Details

#### 1. Register
- Tool/prompt/resource metadata captured
- Input/output schemas defined
- Provider association established
- Version control

#### 2. Classify (NEW - Skill Assignment)
- LLM analyzes tool description
- Assigns to 1-3 skill categories
- Confidence scores calculated
- Primary skill determined

#### 3. Index
- Generate vector embedding
- Store in Qdrant (tools + skills)
- Update PostgreSQL references
- Real-time sync

#### 4. Discover
- User query processed
- Stage 1: Skill matching
- Stage 2: Tool search (filtered)
- Results ranked by relevance

#### 5. Invoke
- Tool execution
- Input validation
- Response handling
- Logging and monitoring

---

## Business Scenarios

### Scenario 1: Intelligent Meeting Scheduling

**Description**: User wants to schedule a meeting using natural language

```
User Query: "schedule a meeting with John tomorrow at 2pm"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: Skill Matching                                         │
│  Query → Embedding → Skills Index                                │
│  Result: ["calendar_management": 0.92, "communication": 0.65]   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 2: Tool Search (Filtered)                                 │
│  Embedding → Tools Index (filter: calendar_management)           │
│  Result: ["create_event": 0.95, "send_invite": 0.82]            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 3: Schema Loading                                         │
│  Load input_schema for create_event                              │
│  Return minimal context for model consumption                    │
└─────────────────────────────────────────────────────────────────┘
```

**Features Used**:
- Skill-based hierarchical search
- Semantic similarity matching
- Lazy schema loading
- Minimal context output

---

### Scenario 2: Multi-Tool Data Pipeline

**Description**: User wants to query data and export results

```
User Query: "get sales data for Q4 and export to CSV"
                              │
                              ▼
             ┌────────────────┴────────────────┐
             │                                  │
             ▼                                  ▼
    ┌─────────────────┐              ┌─────────────────┐
    │ Skill: data_query│             │ Skill: data_export│
    │ Tool: query_db   │             │ Tool: export_csv  │
    └─────────────────┘              └─────────────────┘
             │                                  │
             └────────────────┬────────────────┘
                              │
                              ▼
                    Combined Tool Set
                    (Minimal Schemas)
```

**Features Used**:
- Multi-skill matching
- Tool chaining support
- Cross-skill discovery

---

### Scenario 3: New Tool Onboarding

**Description**: New MCP server registered with tools

```
New MCP Server ──▶ SyncService ──▶ Tool Extraction ──▶ Classification
       │                │                │                    │
       │                ▼                ▼                    ▼
       │          Discover         For each tool:       LLM assigns:
       │          all tools        - Extract metadata   - skill_ids[]
       │                           - Generate embedding - confidence
       │                                                - primary_skill
       │                                                      │
       └──────────────────────────────────────────────────────┘
                                   │
                                   ▼
                            Skill Embeddings
                            Updated (Real-time)
```

**Features Used**:
- Automatic tool discovery
- LLM-based classification
- Real-time embedding updates
- Skill index maintenance

---

### Scenario 4: Fallback Search (No Skill Match)

**Description**: Query doesn't match any skills

```
User Query: "do something unusual and rare"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: Skill Matching                                         │
│  Query → Embedding → Skills Index                                │
│  Result: [] (no skills above threshold 0.4)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  FALLBACK: Direct Search                                         │
│  Skip skill filtering                                            │
│  Query → Embedding → Tools Index (all tools)                    │
│  Result: Best matching tools regardless of skill                │
└─────────────────────────────────────────────────────────────────┘
```

**Features Used**:
- Graceful fallback
- Direct search mode
- Threshold-based routing

---

## Skill-Based Architecture

### Why Skills?

The MCP protocol faces a **scaling problem**: as tools grow to thousands, loading all tool schemas into context becomes impractical. Skills solve this by:

1. **Reducing Search Space**: Match skills first (~50) instead of tools (~1000s)
2. **Improving Relevance**: Filter tools by matched skills
3. **Minimizing Context**: Only load schemas for returned tools
4. **Enabling Organization**: Human-understandable skill categories

### Skill Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SKILL HIERARCHY                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User Query                                                                 │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         SKILLS LAYER                                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ calendar │  │   data   │  │   file   │  │  comms   │  ...       │   │
│  │  │   (15)   │  │   (25)   │  │   (10)   │  │   (8)    │            │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │   │
│  └───────┼─────────────┼─────────────┼─────────────┼──────────────────┘   │
│          │             │             │             │                       │
│          ▼             ▼             ▼             ▼                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         TOOLS LAYER                                  │   │
│  │  [create_event, list_events, ...] [query_db, analyze, ...]          │   │
│  │  [read_file, write_file, ...]     [send_email, notify, ...]         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tool-Skill Relationships

| Relationship | Description | Example |
|-------------|-------------|---------|
| **One-to-Many** | Tool belongs to multiple skills | `send_invite` → calendar, communication |
| **Primary Skill** | Highest confidence assignment | `send_invite` primary: calendar (0.8) |
| **Confidence Score** | LLM classification confidence | 0.0 - 1.0 per assignment |

---

## Glossary

### Core Terms

| Term | Definition |
|------|------------|
| **MCP** | Model Context Protocol - Standard for tool/resource sharing |
| **Tool** | Executable function exposed via MCP |
| **Prompt** | Reusable text template or instruction |
| **Resource** | Data source accessible via MCP |
| **Skill** | Logical grouping of related tools |
| **Provider** | MCP server that hosts tools |

### Technical Terms

| Term | Definition |
|------|------------|
| **Embedding** | Vector representation of text |
| **Hierarchical Search** | Two-stage skill → tool search |
| **Skill Threshold** | Minimum similarity for skill match |
| **Tool Threshold** | Minimum similarity for tool match |
| **Fallback** | Direct search when no skills match |
| **Lazy Loading** | Load schemas only when needed |

### Platform Terms

| Term | Definition |
|------|------------|
| **SkillService** | Service for skill classification and management |
| **SearchService** | Service for hierarchical tool discovery |
| **SyncService** | Service for MCP server synchronization |
| **ToolClassifier** | LLM-based tool categorization |
| **SkillIndex** | Qdrant collection for skill embeddings |

---

## Related Documents

- [PRD - User Stories & Requirements](../prd/README.md)
- [Design - Architecture & Data Flow](../design/README.md)
- [Environment - Configuration Contract](../env/README.md)
- [Test Contracts](../../tests/contracts/README.md)

---

**Version**: 1.0.0
**Last Updated**: 2025-12-11
**Owner**: ISA MCP Team
