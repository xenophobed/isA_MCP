# Web Crawl Tool

## Description
Intelligently crawl and analyze web pages using a **hybrid approach**: traditional extraction (BeautifulSoup + CSS selectors) for simple pages, VLM+LLM analysis for complex pages. Supports both single URL analysis and multiple URL comparison.

### Hybrid Extraction Strategy
1. **First**: Try traditional extraction (fast, cost-effective) for static content sites
2. **Fallback**: Use VLM analysis (comprehensive) for dynamic/complex sites
3. **Smart Detection**: Automatically choose the best method based on page characteristics

## Input Parameters
- `url` (string, required): Target web page URL or JSON array of URLs for comparison
- `analysis_request` (string, optional): Analysis request description (default: "")

### URL Formats
- Single URL: `"https://example.com"`
- Multiple URLs: `'["https://site1.com", "https://site2.com"]'` (JSON array as string)

### Input Validation
- JSON arrays must contain only string URLs (numbers or other types rejected)
- Empty arrays `[]` are rejected
- JSON objects `{}` are rejected (only arrays supported for multiple URLs)
- Malformed JSON triggers validation errors

## Output Format

### Single URL Analysis
```json
{
  "status": "success|error",
  "action": "web_crawl",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "success": true,
    "result": {
      "method": "traditional_extraction|vlm_analysis",
      "success": true,
      "content": "Extracted content using chosen method...",
      "filtered_content": "Cleaned and processed content...",
      "extraction_info": {
        "strategy": "css_extraction|vlm_vision_analysis", 
        "processing_time": 1.23,
        "elements_found": 15
      }
    },
    "url": "https://example.com",
    "analysis_request": "extract main content",
    "extraction_method": "traditional_extraction",
    "extraction_time_ms": 1240,
    "page_info": {
      "title": "Page Title",
      "status_code": 200,
      "final_url": "https://example.com"
    }
  }
}
```

### Multiple URL Comparison
```json
{
  "status": "success|error", 
  "action": "web_crawl_compare",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "success": true,
    "comparison_report": "Detailed comparison analysis",
    "urls_count": 2,
    "analysis_request": "compare product features",
    "urls": ["https://site1.com", "https://site2.com"],
    "processing_time_ms": 8500
  }
}
```

### Result Object Structure

The `result` field contains extraction results based on the method used:

#### Traditional Extraction Result
- **`method`**: "traditional_extraction" 
- **`success`**: Boolean indicating extraction success
- **`content`**: Raw extracted content using BeautifulSoup + CSS selectors
- **`filtered_content`**: Cleaned content after pruning filter
- **`extraction_info`**: Metadata including:
  - `strategy`: "css_extraction" (method used)
  - `processing_time`: Time taken in seconds
  - `elements_found`: Number of HTML elements processed

#### VLM Analysis Result  
- **`method`**: "vlm_analysis"
- **`success`**: Boolean indicating analysis success
- **`content`**: Rich analysis results from image analyzer
- **`final_report`**: Synthesized analysis summary
- **`extraction_info`**: Metadata including:
  - `strategy`: "vlm_vision_analysis" 
  - `processing_time`: Time taken in seconds
  - `screenshots_analyzed`: Number of screenshots processed

## Error Response
```json
{
  "status": "error",
  "action": "web_crawl",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {},
  "error": "Error description"
}
```

## Example Usage
```python
# Single URL analysis
result = await client.call_tool("web_crawl", {
    "url": "https://example.com/article",
    "analysis_request": "extract main content and key points"
})

# Multiple URL comparison
result = await client.call_tool("web_crawl", {
    "url": '["https://site1.com", "https://site2.com"]',
    "analysis_request": "compare product features and pricing"
})

# Simple crawl without specific analysis
result = await client.call_tool("web_crawl", {
    "url": "https://example.com"
})
```

## Hybrid Method Selection

### Traditional Extraction (BeautifulSoup + CSS)
**Used when:**
- Page has static HTML content
- Content-Type is text/html
- Page loads without heavy JavaScript dependency
- Simple structure with identifiable content patterns

**Benefits:**
- ⚡ **Fast**: 2-5x faster than VLM analysis
- 💰 **Cost-effective**: No AI model calls needed
- 🎯 **Accurate**: Precise content extraction with CSS selectors
- 📊 **Reliable**: Deterministic results

### VLM Analysis (Vision + LLM)
**Used when:**
- Page has complex dynamic content
- Heavy JavaScript rendering required
- Traditional extraction fails or produces insufficient content
- Content requires visual understanding

**Benefits:**
- 🧠 **Intelligent**: Understands visual content layout
- 🔄 **Flexible**: Handles any page type
- 📱 **Modern**: Works with SPA and dynamic sites
- 🎨 **Visual**: Can analyze images, charts, complex layouts

### Automatic Selection
The service automatically chooses the best method:

```python
# Internal logic (simplified)
if can_extract_traditionally(url):
    result = traditional_extraction(url)  # Fast BeautifulSoup
else:
    result = vlm_analysis(url)           # Comprehensive VLM
```