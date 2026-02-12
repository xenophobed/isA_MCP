# Core Concepts

## Project Overview

**isA_MCP** is an enterprise-grade, intelligent MCP (Model Context Protocol) server developed following **Contract-Driven (CDD)** and **Test-Driven (TDD)** methodologies. It integrates core features like **Auto-Discovery**, **Hierarchical Semantic Search**, and **Skill Management** within a microservices architecture. By providing intelligent tool selection and real-time progress tracking, it offers a powerful and extensible infrastructure for AI applications.

For a full list of features and capabilities, see the [Platform Overview](./guidance/index.md).

## System Architecture

### Overall Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        C1[Desktop Client]
        C2[IDE Extension]
        C3[Custom Client]
    end

    subgraph "MCP Server (This Project)"
        MS[Smart MCP Server<br/>main.py]
        subgraph "New Services"
            SkillSvc[Skill Service]
            SearchSvc[Hierarchical Search]
        end
        AD[Auto Discovery]
        Sync[Sync Service]
    end

    subgraph "Tool Layer"
        GT[General Tools]
        IT[Intelligence Tools]
        WT[Web Tools<br/>(HTTP Client)]
        DT[Data Tools<br/>(HTTP Client)]
    end

    subgraph "External Microservices"
        WS[Web Service<br/>:8083]
        DS[Data Analytics<br/>:8083]
        IM[Model Service<br/>(LLM/Embeddings)]
    end

    subgraph "Infrastructure"
        PG[(PostgreSQL<br/>Metadata)]
        QD[(Qdrant<br/>Vector Search)]
        CS[Consul<br/>Service Discovery]
        RD[(Redis<br/>Cache)]
    end

    C1 --> MS
    C2 --> MS
    C3 --> MS

    MS --> AD
    AD --> Sync
    MS --> SkillSvc
    MS --> SearchSvc

    SearchSvc --> SkillSvc
    SearchSvc --> QD
    SkillSvc --> PG
    SkillSvc --> QD

    MS --> GT
    MS --> IT
    MS --> WT
    MS --> DT

    WT --> WS
    DT --> DS
    IT --> IM

    Sync --> PG
    Sync --> QD

    WT --> CS
    DT --> CS

    PG -.-> RD
```

### Core Service Flows

#### 1. Startup and Auto-Discovery
```
Start main.py
  ↓
Auto-Discovery scans the `tools/` directory
  ↓
Parses Python files, extracts `@mcp.tool()` decorators
  ↓
Registers 88+ tools with FastMCP
  ↓
Sync Service synchronizes tools with PostgreSQL
  ↓
Generates embeddings via the Model Service
  ↓
Stores vectors and metadata in Qdrant
  ↓
Service Ready ✅
```

#### 2. Hierarchical Semantic Search Flow
```
User Query: "Find web articles about AI"
  ↓
Stage 1: Skill Search
  Hierarchical Search Service converts query to a vector
  ↓
  Searches Qdrant's `mcp_skills` collection to find relevant skills (e.g., "web_research")
  ↓
Stage 2: Tool Search
  Uses the matched skill(s) to filter the `tools` collection in Qdrant
  ↓
  Returns Top-K tools (e.g., `web_search`) with similarity scores
  ↓
Fetches full tool schema from PostgreSQL
  ↓
Returns structured, enriched results
```

#### 3. Microservice Call Flow
```
User calls: web_search(query="AI news")
  ↓
web_tools.py (MCP Tool Layer)
  ↓
web_client.py (HTTP Client)
  ↓
Consul Service Discovery (optional) or Fallback URL
  ↓
HTTP POST → Web Service (External Microservice)
  ↓
SSE stream response (real-time progress)
  ↓
Collects progress history + final result
  ↓
Returns to the user
```

## See Also

- [Platform Overview](./guidance/index.md) -- Features and API endpoints
- [Search & Discovery](./guidance/search.md) -- Hierarchical search details
- [Human-in-the-Loop](./guidance/hil.md) -- HIL interaction patterns
- [Design Documents](./design/) -- Technical architecture deep dives
