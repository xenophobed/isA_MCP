# Search and Discovery

Intelligent tool discovery with semantic and hierarchical search.

## Overview

ISA MCP provides two search strategies:

1. **Semantic Search** - Vector similarity matching
2. **Hierarchical Search** - Two-stage skill → tool routing

## Semantic Search

Find tools using natural language queries.

### Basic Search

```python
import aiohttp

async def search_tools(query: str, limit: int = 5):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8081/search",
            json={
                "query": query,
                "type": "tool",
                "limit": limit,
                "score_threshold": 0.3
            }
        ) as response:
            return await response.json()

# Example
results = await search_tools("weather information")

print(f"Found {results['count']} tools:")
for tool in results['results']:
    print(f"  - {tool['name']} (score: {tool['score']:.3f})")
    print(f"    {tool['description'][:60]}...")
```

**Output:**
```
Found 3 tools:
  - get_weather (score: 0.670)
    Get check query weather temperature forecast conditions...
  - stream_weather (score: 0.553)
    Stream continuous real-time weather updates live...
  - batch_weather (score: 0.423)
    Batch multiple cities weather query parallel...
```

### Search Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search query |
| `type` | string | all | `tool`, `prompt`, `resource`, or omit for all |
| `limit` | int | 10 | Maximum results |
| `score_threshold` | float | 0.3 | Minimum similarity score |

### Search All Types

```python
results = await search_all("data analysis")
# Returns tools, prompts, and resources matching the query
```

## Hierarchical Search

Two-stage skill-based routing for better relevance.

### How It Works

```
User Query: "schedule a meeting with John tomorrow"
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 1: Skill Matching                                 │
│  Query → Embedding → Skills Index                        │
│  Result: ["calendar_management": 0.92, "communication": 0.65]
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 2: Tool Search (Filtered by Skills)              │
│  Query → Embedding → Tools Index (filter: calendar)     │
│  Result: ["create_event": 0.95, "send_invite": 0.82]    │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 3: Schema Loading                                 │
│  Load input_schema only for matched tools               │
│  Return minimal context for model consumption            │
└─────────────────────────────────────────────────────────┘
```

### Skill Categories

```
Skills (6 Categories)
├── Productivity
│   ├── calendar_management
│   ├── task_management
│   ├── note_taking
│   └── time_tracking
│
├── Communication
│   ├── email_operations
│   ├── messaging
│   ├── notifications
│   └── collaboration
│
├── Data
│   ├── data_query
│   ├── data_analysis
│   ├── data_visualization
│   └── data_export
│
├── File
│   ├── file_operations
│   ├── document_processing
│   ├── media_handling
│   └── cloud_storage
│
├── Integration
│   ├── api_integration
│   ├── webhook_management
│   ├── third_party_services
│   └── automation
│
└── System
    ├── configuration
    ├── monitoring
    ├── security
    └── administration
```

### Using Hierarchical Search

```python
# Via API
async with aiohttp.ClientSession() as session:
    async with session.post(
        "http://localhost:8081/api/v1/search",
        json={
            "query": "schedule a meeting",
            "strategy": "hierarchical",  # Use skill-based routing
            "limit": 5
        }
    ) as response:
        results = await response.json()

# Results include skill information
for tool in results['tools']:
    print(f"{tool['name']}")
    print(f"  Skills: {tool['skill_ids']}")
    print(f"  Primary: {tool['primary_skill_id']}")
```

## Fallback Behavior

When no skills match (score below threshold), the system falls back to direct search:

```
Query: "do something unusual and rare"
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 1: Skill Matching                                 │
│  Result: [] (no skills above threshold 0.4)             │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  FALLBACK: Direct Search                                 │
│  Skip skill filtering                                    │
│  Query → Embedding → All Tools Index                    │
│  Result: Best matching tools regardless of skill        │
└─────────────────────────────────────────────────────────┘
```

## Search Metadata

Search results include metadata for debugging:

```json
{
  "query": "schedule meeting",
  "tools": [...],
  "metadata": {
    "strategy": "hierarchical",
    "skills_matched": ["calendar_management"],
    "skill_scores": [0.92],
    "fallback_used": false,
    "search_time_ms": 45.2
  }
}
```

## Tool Classification

Tools are automatically classified into skills:

### Classification Process

1. **LLM Analysis** - Tool name and description analyzed
2. **Skill Assignment** - Assigned to 1-3 skill categories
3. **Confidence Scores** - Each assignment has a confidence (0.0-1.0)
4. **Primary Skill** - Highest confidence >= 0.5

### Classification Example

```
Tool: send_meeting_invite
Description: Send calendar invite to attendees

Classification:
  - calendar_management: 0.85 (primary)
  - communication: 0.72
  - collaboration: 0.45
```

## Performance

| Operation | Target Latency |
|-----------|----------------|
| Semantic search | < 100ms |
| Hierarchical search (Stage 1) | < 50ms |
| Hierarchical search (Stage 2) | < 100ms |
| Schema loading | < 50ms |

## Best Practices

### 1. Use Semantic Search for Discovery

```python
# Good: Natural language query
results = await search("weather information")

# Avoid: Listing all and filtering
all_tools = await list_tools()
filtered = [t for t in all_tools if 'weather' in t['name']]
```

### 2. Tune Score Threshold

```python
# Higher threshold = more relevant, fewer results
results = await search(query, score_threshold=0.5)

# Lower threshold = more results, less relevant
results = await search(query, score_threshold=0.2)
```

### 3. Use Type Filtering

```python
# Search only tools
tools = await search(query, type="tool")

# Search only prompts
prompts = await search(query, type="prompt")
```

## API Reference

### POST /search

```json
{
  "query": "string",
  "type": "tool|prompt|resource",
  "limit": 10,
  "score_threshold": 0.3
}
```

### POST /api/v1/search

```json
{
  "query": "string",
  "strategy": "semantic|hierarchical",
  "include_external": true,
  "server_filter": ["server1", "server2"],
  "limit": 10
}
```

## Next Steps

- [HIL Guide](./hil.md) - Human interaction patterns
- [Aggregator Guide](./aggregator.md) - External server tools
