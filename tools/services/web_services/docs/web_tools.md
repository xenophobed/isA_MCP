# Web Tools Documentation

## Overview

The Web Tools service provides three core web-related capabilities through the MCP (Model Context Protocol) interface:

1. **Web Search** - Search the web for information
2. **Web Crawl** - Intelligently crawl and analyze web pages
3. **Web Automation** - Automate web browser interactions

All tools return standardized JSON responses with consistent error handling and detailed metadata.

---

## = Web Search Tool

### Description
Search the web for information using advanced search capabilities.

### Function Signature
```python
async def web_search(query: str, count: int = 10) -> str
```

### Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query string |
| `count` | integer | No | 10 | Number of results to return (1-100) |

### Input Example
```json
{
  "query": "artificial intelligence machine learning",
  "count": 5
}
```

### Output Format

#### Success Response
```json
{
  "status": "success",
  "action": "web_search",
  "data": {
    "success": true,
    "query": "artificial intelligence machine learning",
    "results": [
      {
        "title": "Introduction to Machine Learning and AI",
        "url": "https://example.com/ai-ml-intro",
        "description": "Comprehensive guide to artificial intelligence and machine learning concepts...",
        "source": "example.com",
        "rank": 1
      }
    ],
    "total_results": 5,
    "search_time": 1.23,
    "metadata": {
      "provider": "web_search_service",
      "timestamp": "2024-01-20T10:30:00Z"
    }
  }
}
```

#### Error Response
```json
{
  "status": "error",
  "action": "web_search",
  "data": {},
  "error_message": "Search query cannot be empty"
}
```

### Use Cases
- Research topics and gather information
- Find relevant websites and resources
- Collect multiple perspectives on a subject
- Discover trending content and news

---

## =w Web Crawl Tool

### Description
Intelligently crawl and analyze web pages using a simplified hybrid approach: BS4 (default) + VLM (fallback) + LLM (analysis). Supports both single URL analysis and multiple URL comparison.

### Function Signature
```python
async def web_crawl(url: str, analysis_request: str = "") -> str
```

### Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | Target web page URL or JSON array of URLs for comparison |
| `analysis_request` | string | No | "" | Analysis request (e.g., 'analyze product reviews', 'compare features') |

### Input Examples

#### Single URL Analysis
```json
{
  "url": "https://example.com/product-page",
  "analysis_request": "extract product specifications and pricing"
}
```

#### Multiple URL Comparison
```json
{
  "url": "[\"https://site1.com/product\", \"https://site2.com/product\"]",
  "analysis_request": "compare product features and prices"
}
```

### Output Format

#### Single URL Success Response
```json
{
  "status": "success",
  "action": "web_crawl",
  "data": {
    "success": true,
    "url": "https://example.com/product-page",
    "extraction_method": "bs4",
    "content": {
      "title": "Amazing Product - Best Price Online",
      "headings": ["Product Overview", "Specifications", "Reviews"],
      "paragraphs": ["Product description text...", "Technical details..."],
      "links": [
        {"text": "Buy Now", "url": "https://example.com/buy"},
        {"text": "Reviews", "url": "https://example.com/reviews"}
      ],
      "word_count": 1250
    },
    "analysis": {
      "summary": "This page showcases a tech product with detailed specifications...",
      "key_points": ["High-quality materials", "Competitive pricing", "Positive reviews"],
      "structured_data": {
        "price": "$299.99",
        "rating": "4.5/5",
        "availability": "In Stock"
      }
    },
    "metadata": {
      "processing_time": 2.1,
      "content_length": 15000,
      "images_found": 8,
      "links_found": 23,
      "timestamp": "2024-01-20T10:30:00Z"
    }
  }
}
```

#### Multiple URL Comparison Response
```json
{
  "status": "success",
  "action": "web_crawl_compare",
  "data": {
    "success": true,
    "urls": ["https://site1.com/product", "https://site2.com/product"],
    "comparison_analysis": {
      "summary": "Comparison of two product pages reveals different pricing strategies...",
      "key_differences": [
        "Site 1 offers better warranty",
        "Site 2 has lower price",
        "Site 1 has more detailed specifications"
      ],
      "recommendations": "Site 1 for quality assurance, Site 2 for budget-conscious buyers"
    },
    "individual_results": [
      {
        "url": "https://site1.com/product",
        "extraction_method": "bs4",
        "content": { /* ... content data ... */ },
        "analysis": { /* ... analysis data ... */ }
      },
      {
        "url": "https://site2.com/product", 
        "extraction_method": "vlm",
        "content": { /* ... content data ... */ },
        "analysis": { /* ... analysis data ... */ }
      }
    ],
    "metadata": {
      "total_processing_time": 8.7,
      "pages_analyzed": 2,
      "timestamp": "2024-01-20T10:30:00Z"
    }
  }
}
```

#### Error Response
```json
{
  "status": "error",
  "action": "web_crawl",
  "data": {},
  "error_message": "Invalid URL format: URL must be a valid HTTP/HTTPS address"
}
```

### Extraction Methods

1. **BS4 (BeautifulSoup)** - Default method for standard HTML pages
   - Fast processing (1-3 seconds)
   - Clean text extraction
   - Structured data parsing

2. **VLM (Vision Language Model)** - Fallback for complex pages
   - Handles JavaScript-heavy content
   - Visual understanding of layouts
   - Slower but more comprehensive (5-15 seconds)

### Use Cases
- Extract product information from e-commerce sites
- Analyze article content and structure
- Compare multiple websites or products
- Research competitor analysis
- Content aggregation and synthesis

---

## > Web Automation Tool

### Description
Automate web browser interactions using a 5-step atomic workflow: Screenshot ’ Analysis ’ UI Detection ’ Action Generation ’ Execution.

### Function Signature
```python
async def web_automation(url: str, task: str) -> str
```

### Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | Target web page URL |
| `task` | string | Yes | - | Task description (e.g., 'search for airpods', 'fill contact form') |

### Input Example
```json
{
  "url": "https://google.com",
  "task": "search for laptop deals"
}
```

### Output Format

#### Success Response
```json
{
  "status": "success",
  "action": "web_automation",
  "data": {
    "success": true,
    "task": "search for laptop deals",
    "initial_url": "https://google.com",
    "final_url": "https://www.google.com/search?q=laptop+deals",
    "workflow_results": {
      "step1_screenshot": "/tmp/automation_screenshot_1.png",
      "step2_analysis": {
        "page_type": "search_page",
        "required_elements": [
          {
            "element_name": "search_input",
            "element_purpose": "search query input field",
            "visual_description": "text input box in center",
            "interaction_type": "click_and_type"
          }
        ],
        "interaction_strategy": "Click search input, type query, press Enter",
        "confidence": 0.95
      },
      "step3_ui_detection": 1,
      "step4_actions": [
        {
          "action": "click",
          "element": "search_input", 
          "x": 400,
          "y": 300
        },
        {
          "action": "type",
          "element": "search_input",
          "x": 400,
          "y": 300,
          "text": "laptop deals"
        },
        {
          "action": "press",
          "key": "Enter"
        }
      ],
      "step5_execution": {
        "actions_executed": 3,
        "execution_time": 4.2,
        "task_completed": true,
        "summary": "Successfully searched for 'laptop deals'",
        "final_screenshot": "/tmp/automation_screenshot_final.png"
      }
    },
    "result_description": "Successfully automated Google search for 'laptop deals'. Found search results page with multiple relevant listings.",
    "metadata": {
      "total_time": 15.7,
      "browser_used": "chromium",
      "timestamp": "2024-01-20T10:30:00Z"
    }
  }
}
```

#### Error Response
```json
{
  "status": "error", 
  "action": "web_automation",
  "data": {},
  "error_message": "Failed to load page: Connection timeout after 30 seconds"
}
```

### Workflow Steps

1. **Step 1: Screenshot** - Capture initial page state
2. **Step 2: Analysis** - Understand page content and requirements using image_analyzer
3. **Step 3: UI Detection** - Detect interactive elements and coordinates using ui_detector  
4. **Step 4: Action Generation** - Generate Playwright actions using text_generator
5. **Step 5: Execution** - Execute actions and analyze results

### Performance
- **Typical execution time**: 15-30 seconds
- **Step 2 (Analysis)**: ~1.7 seconds (optimized with gpt-4.1-nano)
- **Step 3 (UI Detection)**: ~16-20 seconds (quality-focused)
- **Step 4 (Action Generation)**: ~2.2 seconds
- **Step 5 (Execution)**: ~6.8 seconds

### Use Cases
- Automate form filling and submissions
- Perform searches on websites
- Navigate complex web applications
- Collect data through interactions
- Test user workflows

---

## =à Error Handling

All tools implement consistent error handling with detailed error messages:

### Common Error Types

1. **Validation Errors**
   - Invalid URL format
   - Empty required parameters
   - Parameter value out of range

2. **Network Errors**
   - Connection timeout
   - DNS resolution failure
   - HTTP error codes (404, 500, etc.)

3. **Processing Errors**
   - Content parsing failures
   - Service unavailable
   - Rate limiting

4. **Browser Errors** (Web Automation)
   - Page load failures
   - Element not found
   - Interaction failures

### Error Response Format
```json
{
  "status": "error",
  "action": "tool_name",
  "data": {},
  "error_message": "Detailed error description"
}
```

---

## =€ Performance Characteristics

| Tool | Typical Response Time | Factors Affecting Performance |
|------|----------------------|-------------------------------|
| Web Search | 1-3 seconds | Query complexity, result count |
| Web Crawl (BS4) | 1-3 seconds | Page size, content complexity |
| Web Crawl (VLM) | 5-15 seconds | Image processing, analysis depth |
| Web Automation | 15-30 seconds | Page complexity, task complexity |

---

## =Ë Usage Examples

### Research Workflow
```bash
# 1. Search for information
web_search("artificial intelligence trends 2024", 10)

# 2. Crawl detailed articles
web_crawl("https://example.com/ai-trends-article", "summarize key trends")

# 3. Compare multiple sources
web_crawl('["https://site1.com/ai", "https://site2.com/ai"]', "compare perspectives")
```

### E-commerce Analysis
```bash
# 1. Search for products
web_search("gaming laptop under 1500", 5)

# 2. Analyze product pages
web_crawl("https://store.com/laptop", "extract specifications and pricing")

# 3. Automate price checking
web_automation("https://competitor.com", "search for same laptop model")
```

### Content Collection
```bash
# 1. Automate navigation
web_automation("https://news-site.com", "navigate to technology section")

# 2. Crawl articles
web_crawl("https://news-site.com/tech", "extract recent technology news")

# 3. Search for related topics
web_search("technology news analysis", 15)
```

---

## = Security & Best Practices

### Rate Limiting
- Built-in request throttling
- Respectful crawling delays
- Automatic retry mechanisms

### Data Privacy
- No persistent storage of crawled content
- Temporary files automatically cleaned
- No user data retention

### Browser Security (Web Automation)
- Sandboxed browser environments
- No credential storage
- Safe interaction patterns

### Usage Guidelines
1. Respect website robots.txt files
2. Avoid overwhelming servers with requests
3. Use appropriate delays between operations
4. Handle sensitive data appropriately
5. Monitor for IP blocking or rate limiting

---

## =Ê Monitoring & Debugging

### Logging
All tools provide detailed logging including:
- Request/response timing
- Extraction method used
- Error details and stack traces
- Performance metrics

### Performance Metrics
- Processing time per step
- Content extraction success rates
- Browser automation success rates
- Error frequency and types

### Troubleshooting
Common issues and solutions:
- **Slow performance**: Check network connectivity, reduce complexity
- **Extraction failures**: Verify URL accessibility, check for CAPTCHA
- **Automation failures**: Ensure page loads completely, check for dynamic content