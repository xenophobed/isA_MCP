# MCP Search API Documentation

## Overview

The MCP Search Service provides unified search capabilities across tools, prompts, and resources with user-specific access control. This API enables semantic similarity search, keyword filtering, and category-based discovery of MCP capabilities.

## Base URL

```
http://localhost:8081
```

## Authentication

Currently, the API uses user_id-based access control. Include the `user_id` parameter in your requests to filter resources based on user permissions.

---

## API Endpoints

### 1. Search Capabilities

**Endpoint:** `POST /search`

Perform unified search across tools, prompts, and resources with advanced filtering and user-specific access control.

### 2. Get All Capabilities

**Endpoint:** `GET /capabilities`

Retrieve all available capabilities (tools, prompts, resources) with optional user filtering.

**Query Parameters:**
- `user_id` (optional): Filter resources based on user permissions

**Response Format:**
```json
{
  "tools": [...],
  "prompts": [...], 
  "resources": [...],
  "metadata": {
    "total_count": 150,
    "last_updated": "2024-01-01T00:00:00Z",
    "user_filtered": true
  }
}
```

### 3. Get Capabilities by Type

**Endpoint:** `GET /capabilities/{type}`

Retrieve capabilities filtered by specific type: `tools`, `prompts`, or `resources`.

**Path Parameters:**
- `type`: Capability type (`tools`, `prompts`, `resources`)

**Query Parameters:**
- `user_id` (optional): Filter resources based on user permissions

**Response Format:**
```json
{
  "type": "prompts",
  "capabilities": [
    {
      "name": "text_to_image_prompt",
      "description": "Generate prompts for text-to-image generation...",
      "type": "prompt",
      "category": "dream",
      "keywords": ["text-to-image", "photography", "professional"],
      "metadata": {
        "arguments": [
          {"name": "prompt", "type": "string", "required": true},
          {"name": "style_preset", "type": "string", "default": "photorealistic"},
          {"name": "quality", "type": "string", "default": "high"}
        ]
      }
    }
  ],
  "count": 45,
  "user_filtered": false
}
```

#### Request Format

```json
{
  "query": "string (required)",
  "user_id": "string (optional)",
  "filters": {
    "types": ["tool", "prompt", "resource"] (optional),
    "categories": ["category1", "category2"] (optional),
    "keywords": ["keyword1", "keyword2"] (optional),
    "min_similarity": 0.25 (optional, default: 0.25)
  },
  "max_results": 10 (optional, default: 10)
}
```

#### Response Format

```json
{
  "status": "success|error",
  "query": "original search query",
  "user_id": "user identifier (if provided)",
  "filters": {
    "applied filters object"
  },
  "results": [
    {
      "name": "capability_name",
      "type": "tool|prompt|resource",
      "description": "detailed description",
      "similarity_score": 0.75,
      "category": "category_name",
      "keywords": ["keyword1", "keyword2"],
      "metadata": {
        "additional_info": "value"
      }
    }
  ],
  "result_count": 5,
  "max_results": 10
}
```

---

## Parameters

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Natural language search query |
| `user_id` | string | No | User identifier for access control |
| `max_results` | integer | No | Maximum results to return (1-100, default: 10) |

### Filter Parameters

| Filter | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `types` | array | Capability types to search | `["tool", "prompt", "resource"]` |
| `categories` | array | Categories to filter by | `["memory", "analytics", "web"]` |
| `keywords` | array | Keywords to match | `["user", "data", "analysis"]` |
| `min_similarity` | float | Minimum similarity score | `0.25` (range: 0.0-1.0) |

---

## Categories

### Tool Categories
- `memory` - Memory and storage tools
- `vision` - Image and visual processing
- `audio` - Audio processing tools
- `web` - Web automation and search
- `analytics` - Data analytics and graph tools
- `ecommerce` - E-commerce and Shopify tools
- `weather` - Weather and forecast tools
- `admin` - Administrative and system tools
- `general` - General purpose tools

### Prompt Categories
- `custom` - Custom content generation
- `business_commerce` - Business and commerce
- `education_learning` - Educational content
- `technology_innovation` - Technical implementation
- `marketing_media` - Marketing and media
- `health_wellness` - Health and wellness
- `lifestyle_personal` - Lifestyle and personal
- `professional_career` - Professional development
- `news_current_events` - News analysis
- `creative_artistic` - Creative content
- `science_research` - Scientific research
- `dream` - AI image generation and manipulation
- `security` - Security analysis
- `autonomous` - Autonomous execution
- `rag` - Retrieval augmented generation

### Resource Categories
- `memory` - Memory resources
- `security` - Security configurations
- `shopify` - E-commerce resources
- `reasoning` - Symbolic reasoning
- `event` - Event sourcing
- `rag` - Knowledge base resources
- `general` - General resources

---

## Usage Examples

### Basic Search

Search for memory-related capabilities:

```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "store user information and memories",
    "max_results": 5
  }'
```

### User-Specific Resource Search

Search for resources accessible to a specific user:

```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "knowledge graph user data",
    "user_id": "88888",
    "filters": {
      "types": ["resource"],
      "categories": ["rag"]
    },
    "max_results": 10
  }'
```

### Category-Filtered Search

Search only for business-related prompts:

```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "create marketing strategy",
    "filters": {
      "types": ["prompt"],
      "categories": ["business_commerce", "marketing_media"]
    }
  }'
```

### High-Precision Search

Search with higher similarity threshold:

```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "analyze data with machine learning",
    "filters": {
      "types": ["tool"],
      "min_similarity": 0.5
    },
    "max_results": 3
  }'
```

### Keyword-Based Search

Search using specific keywords:

```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "graph analytics",
    "filters": {
      "keywords": ["neo4j", "knowledge", "graph"],
      "categories": ["analytics"]
    }
  }'
```

### Get All Capabilities

Retrieve all available capabilities:

```bash
curl -X GET http://localhost:8081/capabilities
```

### Get User-Filtered Capabilities

Get capabilities with user-specific resource filtering:

```bash
curl -X GET "http://localhost:8081/capabilities?user_id=88888"
```

### Get Specific Capability Type

Get only prompts:

```bash
curl -X GET http://localhost:8081/capabilities/prompts
```

### Get Dream Prompts

Search for Dream category prompts specifically:

```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "image generation",
    "filters": {
      "types": ["prompt"],
      "categories": ["dream"]
    }
  }'
```

---

## Response Examples

### Successful Search Response

```json
{
  "status": "success",
  "query": "store user information",
  "user_id": "88888",
  "filters": {
    "types": ["tool"],
    "min_similarity": 0.25
  },
  "results": [
    {
      "name": "store_knowledge",
      "type": "tool",
      "description": "Store knowledge items in user's knowledge base with embeddings",
      "similarity_score": 0.82,
      "category": "memory",
      "keywords": ["knowledge", "store", "embeddings", "user", "database"],
      "metadata": {
        "input_schema": {
          "properties": {
            "user_id": {"type": "string"},
            "text": {"type": "string"},
            "metadata": {"type": "object"}
          },
          "required": ["user_id", "text"]
        }
      }
    },
    {
      "name": "list_user_knowledge",
      "type": "tool", 
      "description": "List all knowledge items for a specific user",
      "similarity_score": 0.76,
      "category": "memory",
      "keywords": ["list", "user", "knowledge", "items", "retrieve"],
      "metadata": {
        "input_schema": {
          "properties": {
            "user_id": {"type": "string"},
            "limit": {"type": "integer", "default": 50}
          },
          "required": ["user_id"]
        }
      }
    }
  ],
  "result_count": 2,
  "max_results": 10
}
```

### Error Response

```json
{
  "status": "error",
  "message": "Query is required"
}
```

---

## User Access Control

### Resource Filtering

When `user_id` is provided, the search service automatically filters resources based on user permissions:

1. **Graph Knowledge Resources** - Filters based on `@resources/graph_knowledge_resources.py` user mappings
2. **Digital Knowledge Resources** - Filters based on `@resources/digital_resource.py` user mappings
3. **General Resources** - No user filtering applied (globally accessible)

### Access Patterns

```bash
# Search user's personal knowledge resources
{
  "query": "my documents and analysis",
  "user_id": "user123",
  "filters": {"types": ["resource"]}
}

# Search user's graph knowledge specifically  
{
  "query": "knowledge graph data",
  "user_id": "88888",
  "filters": {
    "types": ["resource"],
    "categories": ["rag"]
  }
}

# Search without user filtering (all public resources)
{
  "query": "weather information",
  "filters": {"types": ["resource"]}
}
```

---

## Integration Examples

### Python Client

```python
import requests
import json

def search_mcp_capabilities(query, user_id=None, filters=None, max_results=10):
    """Search MCP capabilities with optional user filtering"""
    
    payload = {
        "query": query,
        "max_results": max_results
    }
    
    if user_id:
        payload["user_id"] = user_id
        
    if filters:
        payload["filters"] = filters
    
    response = requests.post(
        "http://localhost:8081/search",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )
    
    return response.json()

def get_all_capabilities(user_id=None):
    """Get all available capabilities"""
    params = {"user_id": user_id} if user_id else {}
    response = requests.get("http://localhost:8081/capabilities", params=params)
    return response.json()

def get_capabilities_by_type(capability_type, user_id=None):
    """Get capabilities filtered by type"""
    params = {"user_id": user_id} if user_id else {}
    response = requests.get(f"http://localhost:8081/capabilities/{capability_type}", params=params)
    return response.json()

# Example usage - Search
results = search_mcp_capabilities(
    query="analyze user data with graphs",
    user_id="88888",
    filters={
        "types": ["tool", "resource"],
        "categories": ["analytics", "rag"]
    },
    max_results=5
)

print(f"Found {results['result_count']} results:")
for result in results['results']:
    print(f"- {result['name']} ({result['type']}) - {result['similarity_score']:.3f}")

# Example usage - Get Dream prompts
dream_prompts = get_capabilities_by_type("prompts")
dream_category = [p for p in dream_prompts['capabilities'] if p['category'] == 'dream']
print(f"Found {len(dream_category)} Dream prompts:")
for prompt in dream_category:
    print(f"- {prompt['name']}: {prompt['description'][:100]}...")
```

### JavaScript Client

```javascript
async function searchMCPCapabilities(query, options = {}) {
    const payload = {
        query: query,
        max_results: options.maxResults || 10,
        ...options
    };
    
    try {
        const response = await fetch('http://localhost:8081/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        return await response.json();
    } catch (error) {
        console.error('Search failed:', error);
        return { status: 'error', message: error.message };
    }
}

// Example usage
const results = await searchMCPCapabilities(
    "knowledge graph user resources", 
    {
        userId: "88888",
        filters: {
            types: ["resource"],
            categories: ["rag"]
        },
        maxResults: 5
    }
);

console.log(`Found ${results.result_count} results`);
results.results.forEach(result => {
    console.log(`${result.name} (${result.type}) - ${result.similarity_score.toFixed(3)}`);
});
```

---

## Performance Notes

1. **Caching** - Query embeddings and search results are cached for 5 minutes
2. **Similarity Search** - Uses text-embedding-3-small for semantic similarity
3. **Fallback** - Keyword search is used when embeddings are unavailable
4. **User Filtering** - Applied only to resources, tools and prompts remain global
5. **Response Times** - Typical response times: 200-500ms for cached queries, 1-2s for new embeddings

---

## Monitoring

The search service includes built-in monitoring:

- Search performance metrics
- Cache hit rates
- User access patterns
- Error rates and health checks

Access monitoring data through the `/stats` endpoint.

---

## Support

For technical support or feature requests related to the MCP Search API, please refer to the main MCP server documentation or contact the development team.