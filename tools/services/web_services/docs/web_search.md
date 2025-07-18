# Web Search Tool

## Description
Search the web for information using search engines.

## Input Parameters
- `query` (string, required): Search query text
- `count` (int, optional): Number of results to return (default: 10)

## Output Format
```json
{
  "status": "success|error",
  "action": "web_search", 
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "success": true,
    "results": [
      {
        "title": "Search result title",
        "url": "https://example.com",
        "snippet": "Brief description of the content"
      }
    ],
    "query": "original search query",
    "count": 10
  }
}
```

## Error Response
```json
{
  "status": "error",
  "action": "web_search",
  "timestamp": "2024-01-01T12:00:00Z", 
  "error_message": "Error description"
}
```

## Example Usage
```python
# Basic search
result = await client.call_tool("web_search", {
    "query": "python programming"
})

# Search with specific count
result = await client.call_tool("web_search", {
    "query": "machine learning tutorials",
    "count": 5
})
```