# Smart MCP Server API Documentation

## Overview

The Smart MCP Server is an AI-powered Model Context Protocol (MCP) server with automatic capability discovery and intelligent routing. It provides both MCP-compliant endpoints and REST API endpoints.

**Base URL:** `http://localhost:8081`

**Current Capabilities:**
- **Tools:** 36 registered MCP tools
- **Prompts:** 11 registered MCP prompts  
- **Resources:** 14 registered MCP resources
- **AI Selectors:** 3/3 active (fully integrated with MCP server)

---

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

Returns server health status and configuration.

**Response:**
```json
{
  "status": "healthy",
  "service": "Smart MCP Server",
  "server_info": {
    "server_name": "Smart MCP Server",
    "ai_selectors": {
      "tool_selector": true,
      "prompt_selector": true,
      "resource_selector": true
    },
    "capabilities_count": {
      "tools": 36,
      "prompts": 11,
      "resources": 14
    },
    "features": [
      "AI-powered capability discovery",
      "Vector similarity matching",
      "Dynamic tool selection",
      "Smart prompt routing",
      "Intelligent resource discovery",
      "Security and monitoring integration"
    ]
  }
}
```

---

### 2. Capabilities Listing

**Endpoint:** `GET /capabilities`

Lists all available tools, prompts, and resources with their counts.

**Response:**
```json
{
  "status": "success",
  "capabilities": {
    "tools": {
      "count": 36,
      "available": [
        "get_weather", "remember", "automate_web_login", 
        "generate_image", "search_products", "..."
      ]
    },
    "prompts": {
      "count": 11,
      "available": [
        "security_analysis_prompt", "memory_organization_prompt",
        "user_assistance_prompt", "..."
      ]
    },
    "resources": {
      "count": 14,
      "available": [
        "memory://all", "weather://cache",
        "monitoring://metrics", "..."
      ]
    }
  }
}
```

---

### 3. AI-Powered Capability Discovery

**Endpoint:** `POST /discover`

Uses AI to discover relevant capabilities based on natural language requests.

**Request:**
```json
{
  "request": "Natural language description of what you want to do"
}
```

**Example - Weather Request:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "I need to check the weather in New York"}'
```

**Response:**
```json
{
  "status": "success",
  "user_request": "I need to check the weather in New York",
  "capabilities": {
    "tools": ["get_weather"],
    "prompts": ["monitoring_report_prompt"],
    "resources": ["weather://cache"]
  }
}
```

**Example - Memory Management:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Help me remember important information"}'
```

**Response:**
```json
{
  "status": "success",
  "user_request": "Help me remember important information",
  "capabilities": {
    "tools": ["remember", "search_memories", "forget", "update_memory"],
    "prompts": ["memory_organization_prompt", "user_assistance_prompt"],
    "resources": ["memory://all", "memory://category/{category}"]
  }
}
```

**Example - Web Automation:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "I want to automate website login and search"}'
```

**Response:**
```json
{
  "status": "success",
  "user_request": "I want to automate website login and search",
  "capabilities": {
    "tools": ["automate_web_login", "automate_web_search", "intelligent_web_crawl"],
    "prompts": ["scrape_and_analyze_prompt", "content_analysis_prompt"],
    "resources": ["shopify://preferences/user_profiles"]
  }
}
```

---

### 4. AI Selector Statistics

**Endpoint:** `GET /stats`

Returns detailed statistics about AI selectors including usage patterns.

**Response:**
```json
{
  "status": "success",
  "server_info": { "..." },
  "selector_stats": {
    "tools": {
      "total_selections": 50,
      "tool_usage": {
        "automate_web_login": 28,
        "get_weather": 15,
        "remember": 12
      },
      "available_tools": ["...", "36 tools"],
      "threshold": 0.25
    },
    "prompts": {
      "total_selections": 50,
      "prompt_usage": {
        "user_assistance_prompt": 31,
        "memory_organization_prompt": 16
      },
      "available_prompts": ["...", "11 prompts"],
      "threshold": 0.25
    },
    "resources": {
      "total_selections": 50,
      "resource_usage": {
        "memory://all": 22,
        "weather://cache": 15
      },
      "available_resources": ["...", "14 resources"],
      "threshold": 0.25
    }
  }
}
```

---

### 5. MCP Protocol Endpoint

**Endpoint:** `GET /mcp/`

Main MCP protocol endpoint for Model Context Protocol communication. Requires Server-Sent Events (SSE) support.

**Headers Required:**
- `Accept: text/event-stream`

**Error Response (without SSE headers):**
```json
{
  "jsonrpc": "2.0",
  "id": "server-error",
  "error": {
    "code": -32600,
    "message": "Not Acceptable: Client must accept text/event-stream"
  }
}
```

---

## Error Handling

**Standard Error Response:**
```json
{
  "status": "error",
  "message": "Error description"
}
```

**HTTP Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid request
- `404 Not Found` - Endpoint not found
- `406 Not Acceptable` - Invalid headers
- `500 Internal Server Error` - Server error

---

## Usage Examples

```bash
# Check server health
curl http://localhost:8081/health

# List all capabilities
curl http://localhost:8081/capabilities

# Discover capabilities for a task
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "I need help with data analysis"}'

# Get usage statistics
curl http://localhost:8081/stats
```

---

## Integration Notes

- **Content-Type:** Use `application/json` for POST requests
- **Response Format:** All responses return JSON with consistent structure
- **Error Handling:** Check `status` field in response
- **Authentication:** No authentication required
- **AI Similarity Threshold:** 0.25 (configurable)

---

*Last Updated: December 2024*
