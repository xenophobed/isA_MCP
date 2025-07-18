# Web Services Documentation

This document describes the three core web services available in the system: WebSearchService, WebCrawlService, and WebAutomationService.

## Overview

The web services provide different levels of web interaction capabilities:

1. **WebSearchService** - Basic web search functionality
2. **WebCrawlService** - Intelligent content extraction and analysis  
3. **WebAutomationService** - Browser automation for interactive tasks

---

## 1. WebSearchService

### Purpose
Basic web search functionality that returns search results with titles, URLs, and snippets.

### Input
```python
async def search(query: str, count: int = 10) -> Dict[str, Any]
```

**Parameters:**
- `query` (str): Search query string
- `count` (int, optional): Number of results to return (default: 10)

### Output
```json
{
    "success": true,
    "query": "python tutorial",
    "total": 10,
    "results": [
        {
            "title": "Python Tutorial - Learn Python",
            "url": "https://example.com/python-tutorial",
            "snippet": "Complete Python tutorial for beginners...",
            "score": 0.95
        }
    ],
    "urls": ["https://example.com/python-tutorial", ...]
}
```

### Usage Example
```python
service = WebSearchService()
result = await service.search("python tutorial", count=5)
urls = result["urls"]  # Extract URLs for further processing
await service.close()
```

### Use Cases
- Find relevant websites for a topic
- Get URLs for subsequent crawling
- Basic search functionality in applications

---

## 2. WebCrawlService

### Purpose
Intelligent web content extraction and analysis using an 8-step VLM+LLM process for high-quality content understanding and structured analysis.

### Input
```python
async def crawl_and_analyze(url: str, analysis_request: Optional[str] = None) -> Dict[str, Any]
```

**Parameters:**
- `url` (str): Target webpage URL
- `analysis_request` (str, optional): Specific analysis request (e.g., "aspect based sentiment analysis", "product feature comparison")

### Output
```json
{
    "success": true,
    "url": "https://example.com/product",
    "analysis_request": "aspect based sentiment analysis",
    "result": {
        "process_type": "content_analysis",
        "step1_screenshots": 5,
        "step2_page_analyses": {
            "best_screenshots": [...],
            "page_type": "product_reviews"
        },
        "step6_content_analysis": {
            "analysis_results": [...],
            "screenshots_analyzed": 3
        },
        "step8_markdown_content": "# Analysis Report\n\n## Product Reviews Analysis..."
    },
    "timestamp": "1234567890.123"
}
```

### Multi-URL Comparison
```python
async def crawl_and_compare_multiple(urls: List[str], analysis_request: str) -> Dict[str, Any]
```

**Parameters:**
- `urls` (List[str]): List of URLs to compare
- `analysis_request` (str): Comparison analysis request (e.g., "compare these three products")

### 8-Step Process
1. **Full Screenshot** - Scroll and capture entire page
2. **Page Understanding** - Analyze screenshots for relevance to analysis request
3. **UI Elements Detection** - Identify interactive elements (skipped for content analysis)
4. **Content Coordinates** - Determine target content areas (skipped for content analysis)
5. **Content Screenshot** - Capture specific regions (skipped for content analysis)
6. **Content Analysis** - VLM analysis of relevant screenshots
7. **Content Structuring** - LLM structuring of extracted content (merged with step 8)
8. **Markdown Generation** - Generate final analysis report

### Usage Example
```python
service = WebCrawlService()

# Single URL analysis
result = await service.crawl_and_analyze(
    "https://amazon.com/product", 
    "aspect based sentiment analysis"
)
report = result["result"]["step8_markdown_content"]

# Multi-URL comparison
comparison = await service.crawl_and_compare_multiple(
    ["https://url1.com", "https://url2.com", "https://url3.com"],
    "compare these three products"
)
comparison_report = comparison["comparison_report"]

await service.close()
```

### Use Cases
- Product review analysis and sentiment extraction
- Competitive product comparison
- Content extraction from complex web pages
- Market research and analysis
- Academic research content gathering

---

## 3. WebAutomationService

### Purpose
Generic browser automation service that can interact with web pages to perform tasks like searching, clicking, and form filling using a 4-step VLM-guided process.

### Input
```python
async def execute_task(url: str, task: str) -> Dict[str, Any]
```

**Parameters:**
- `url` (str): Target webpage URL
- `task` (str): Task description (e.g., "search airpod", "click login button", "fill contact form")

### Output
```json
{
    "success": true,
    "initial_url": "https://amazon.com",
    "final_url": "https://amazon.com/s?k=airpod",
    "task": "search airpod",
    "operations": [
        {
            "action": "type",
            "target": "search_input",
            "content": "airpod",
            "coordinates": [945, 29]
        },
        {
            "action": "click", 
            "target": "search_submit",
            "coordinates": [1469, 29]
        }
    ],
    "result_description": " Search completed successfully! Found Apple AirPods Pro 2, AirPods 4..."
}
```

### 4-Step Process
1. **Understand Page** - VLM analyzes page to identify required UI elements for the task
2. **Locate Elements** - OmniParser detects UI elements + VLM matches requirements with elements using annotated screenshots
3. **Execute Operations** - Playwright performs mouse clicks, keyboard input, and navigation
4. **Analyze Results** - VLM analyzes the final page to verify task completion

### Usage Example
```python
service = WebAutomationService()

# Search automation
result = await service.execute_task(
    "https://amazon.com", 
    "search airpod"
)

if result["success"]:
    print(f"Task completed! Final URL: {result['final_url']}")
    print(f"Operations performed: {len(result['operations'])}")
    print(f"Result: {result['result_description']}")
else:
    print(f"Task failed: {result['error']}")

await service.close()
```

### Supported Task Types
- **Search tasks**: "search [query]", "find [item]", "look for [product]"
- **Navigation**: "click [element]", "go to [section]"
- **Form filling**: "fill [field] with [value]", "enter [data]"
- **General interactions**: Any task that can be described in natural language

### Use Cases
- Automated testing of web applications
- Data collection through form interactions
- E-commerce product searches
- Social media automation
- Research data gathering
- Competitive analysis automation

---

## Service Comparison

| Feature | WebSearchService | WebCrawlService | WebAutomationService |
|---------|------------------|-----------------|---------------------|
| **Complexity** | Simple | High | Medium |
| **AI/VLM Usage** | None | Extensive | Moderate |
| **Browser Required** | No | Yes | Yes |
| **Input Type** | Search queries | URLs + analysis requests | URLs + task descriptions |
| **Output Type** | Search results | Analysis reports | Task execution results |
| **Use Case** | Find URLs | Analyze content | Interact with pages |
| **Processing Time** | Fast (seconds) | Slow (minutes) | Medium (30-60 seconds) |

## Integration Patterns

### Sequential Usage
```python
# 1. Search for relevant URLs
search_service = WebSearchService()
urls = await search_service.get_urls("python tutorials", 5)

# 2. Analyze each URL's content  
crawl_service = WebCrawlService()
for url in urls:
    analysis = await crawl_service.crawl_and_analyze(url, "tutorial quality analysis")
    
# 3. Automate interactions on best URLs
automation_service = WebAutomationService()
best_url = urls[0]
await automation_service.execute_task(best_url, "download tutorial PDF")
```

### Service Selection Guide

**Use WebSearchService when:**
- You need to find relevant URLs
- Building search functionality
- Collecting web references
- Simple, fast operations required

**Use WebCrawlService when:**
- You need deep content analysis
- Performing sentiment analysis or reviews extraction
- Comparing multiple products/pages
- Research requiring structured reports
- Content quality and accuracy are critical

**Use WebAutomationService when:**
- You need to interact with web pages
- Automating repetitive tasks
- Testing web applications
- Filling forms or performing searches
- Navigating through multi-step processes

---

## Technical Requirements

### Dependencies
- **WebSearchService**: Brave Search API key (`BRAVE_TOKEN`)
- **WebCrawlService**: ISA client with VLM access, Playwright browser
- **WebAutomationService**: ISA client with VLM access, Playwright browser

### Performance Considerations
- **WebSearchService**: ~1-3 seconds per search
- **WebCrawlService**: ~2-5 minutes per URL (due to VLM processing)
- **WebAutomationService**: ~30-60 seconds per task

### Resource Usage
- **WebSearchService**: Low memory, API calls only
- **WebCrawlService**: High memory (browser + multiple screenshots), intensive VLM usage
- **WebAutomationService**: Medium memory (browser instance), moderate VLM usage

All services include proper resource cleanup and error handling for production use.