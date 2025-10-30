# MCP Fetch Server Analysis & Enhancement Plan

## 📊 Comparison: MCP Fetch vs Current Web Services

### **Feature Matrix**

| Feature | MCP Fetch | Your web_services | Priority | Recommendation |
|---------|-----------|-------------------|----------|----------------|
| **Robots.txt Compliance** | ✅ Built-in | ❌ Missing | 🔴 HIGH | **Add** |
| **Readability Extraction** | ✅ readabilipy | ❌ BS4 only | 🟡 MEDIUM | **Enhance** |
| **Content Pagination** | ✅ Auto-chunking | ❌ No pagination | 🟡 MEDIUM | **Add** |
| **Proxy Support** | ✅ Yes | ❌ No | 🟢 LOW | **Add** |
| **User-Agent Strategy** | ✅ Dual mode | ⚠️ Generic | 🟡 MEDIUM | **Enhance** |
| **Content-Type Detection** | ✅ Smart | ⚠️ Basic | 🟢 LOW | **Enhance** |
| **VLM Vision Analysis** | ❌ No | ✅ Yes | N/A | **Keep** |
| **Deep Search** | ❌ No | ✅ Yes | N/A | **Keep** |
| **Web Automation** | ❌ No | ✅ Playwright | N/A | **Keep** |
| **Multi-URL Compare** | ❌ No | ✅ Yes | N/A | **Keep** |

---

## 🎯 Key Learnings from MCP Fetch

### 1. **Ethical Scraping with Robots.txt** ⭐⭐⭐

**What they do:**
```python
from protego import Protego

async def check_may_autonomously_fetch_url(url: str, user_agent: str):
    robot_txt_url = get_robots_txt_url(url)
    response = await client.get(robot_txt_url, ...)
    robot_parser = Protego.parse(response.text)

    if not robot_parser.can_fetch(str(url), user_agent):
        raise McpError(f"robots.txt disallows autonomous fetching")
```

**Why it matters:**
- ✅ Legal compliance
- ✅ Respectful scraping
- ✅ Avoids IP bans
- ✅ Clear error messages to users

**Implementation for your service:**
```python
# tools/services/web_services/utils/robots_checker.py
class RobotsChecker:
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self.cache: Dict[str, Protego] = {}

    async def can_fetch(self, url: str, autonomous: bool = True) -> Tuple[bool, str]:
        """Check if URL can be fetched per robots.txt"""
        if not autonomous:
            return True, "Manual fetch bypasses robots.txt"

        domain = urlparse(url).netloc
        if domain not in self.cache:
            self.cache[domain] = await self._fetch_robots_txt(domain)

        can_fetch = self.cache[domain].can_fetch(url, self.user_agent)
        return can_fetch, "Allowed" if can_fetch else "Disallowed by robots.txt"
```

---

### 2. **Readability + Markdown Conversion** ⭐⭐⭐

**What they do:**
```python
import readabilipy.simple_json
import markdownify

def extract_content_from_html(html: str) -> str:
    # Step 1: Extract main content with readability algorithm
    ret = readabilipy.simple_json.simple_json_from_html_string(
        html, use_readability=True
    )

    # Step 2: Convert to clean markdown
    content = markdownify.markdownify(
        ret["content"],
        heading_style=markdownify.ATX,  # Use # headers
    )
    return content
```

**Why it matters:**
- ✅ Removes ads, navigation, footers automatically
- ✅ Preserves structure (headings, lists, links)
- ✅ LLM-friendly markdown format
- ✅ Much cleaner than raw BS4 text

**Comparison:**

| Method | Output Quality | Speed | Best For |
|--------|---------------|----ings|----------|
| **BS4 text** | ⚠️ Includes noise | ⚡ Fast | Simple pages |
| **Readability + MD** | ✅ Clean content | ⚡ Fast | Articles, blogs |
| **VLM Vision** | ✅✅ Most accurate | 🐌 Slow | Complex layouts |

**Implementation:**
```python
# Enhanced extraction pipeline
class ContentExtractor:
    async def extract(self, html: str, url: str) -> Dict:
        # Try readability first (fast, clean)
        readable = readabilipy.simple_json.simple_json_from_html_string(html)
        if readable['content']:
            return {
                "method": "readability",
                "content": markdownify.markdownify(readable['content']),
                "title": readable.get('title'),
                "byline": readable.get('byline'),
                "excerpt": readable.get('excerpt')
            }

        # Fallback to BS4
        return {
            "method": "bs4",
            "content": bs4_extract(html)
        }
```

---

### 3. **Smart Content Pagination** ⭐⭐

**What they do:**
```python
class Fetch(BaseModel):
    max_length: int = 5000    # Chunk size
    start_index: int = 0      # Offset for pagination

# Auto-generate continuation prompt
if actual_content_length == args.max_length and remaining_content > 0:
    next_start = args.start_index + actual_content_length
    content += (
        f"\n\n<error>Content truncated. "
        f"Call the fetch tool with a start_index of {next_start} "
        f"to get more content.</error>"
    )
```

**Why it matters:**
- ✅ Handles large articles gracefully
- ✅ LLM context window management
- ✅ Clear user guidance for continuation
- ✅ Stateless pagination (no server-side cursor)

**Implementation:**
```python
# Add to web_crawl parameters
async def web_crawl(
    self,
    url: str,
    analysis_request: str = "",
    max_length: int = 5000,      # NEW
    start_index: int = 0          # NEW
) -> str:
    result = await service.crawl_and_analyze(url, analysis_request)
    content = result['content']

    # Paginate if needed
    if start_index >= len(content):
        return {"error": "No more content available"}

    chunk = content[start_index:start_index + max_length]

    if len(chunk) == max_length and start_index + max_length < len(content):
        chunk += f"\n\n💡 Content continues. Use start_index={start_index + max_length} for more."

    return {"content": chunk, "total_length": len(content), ...}
```

---

### 4. **Dual User-Agent Strategy** ⭐⭐

**What they do:**
```python
# Different UAs for different contexts
DEFAULT_USER_AGENT_AUTONOMOUS = "ModelContextProtocol/1.0 (Autonomous; +github.com/...)"
DEFAULT_USER_AGENT_MANUAL = "ModelContextProtocol/1.0 (User-Specified; +github.com/...)"

# Tool calls (autonomous) - check robots.txt
await check_may_autonomously_fetch_url(url, user_agent_autonomous)

# Prompt calls (manual) - skip robots.txt
await fetch_url(url, user_agent_manual)  # No robots check
```

**Why it matters:**
- ✅ Transparency - sites know it's AI scraping
- ✅ Accountability - contact URL in UA
- ✅ User control - manual fetch bypasses restrictions
- ✅ Compliance - respects robots.txt for autonomous

**Implementation:**
```python
# tools/services/web_services/config.py
USER_AGENT_AUTONOMOUS = (
    "isA_MCP/1.0 (Autonomous; AI Agent; "
    "+https://github.com/yourusername/isA_MCP)"
)

USER_AGENT_MANUAL = (
    "isA_MCP/1.0 (User-Directed; "
    "+https://github.com/yourusername/isA_MCP)"
)

# Use in requests
class WebCrawlService:
    async def crawl(self, url: str, autonomous: bool = True):
        ua = USER_AGENT_AUTONOMOUS if autonomous else USER_AGENT_MANUAL

        if autonomous:
            # Check robots.txt first
            can_fetch, reason = await self.robots_checker.can_fetch(url)
            if not can_fetch:
                raise ValueError(f"Robots.txt blocks autonomous access: {reason}")

        # Proceed with fetch
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"User-Agent": ua})
```

---

### 5. **Proxy Support** ⭐

**What they do:**
```python
async def serve(proxy_url: str | None = None):
    # Pass proxy to all requests
    async with AsyncClient(proxies=proxy_url) as client:
        response = await client.get(url, ...)
```

**Why it matters:**
- ✅ Corporate firewall support
- ✅ Geographic restrictions bypass
- ✅ Rate limit distribution
- ✅ Privacy/anonymity

**Implementation:**
```python
# Add to WebCrawlService init
class WebCrawlService:
    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url or os.getenv("WEB_PROXY_URL")

    async def _fetch(self, url: str):
        async with httpx.AsyncClient(proxies=self.proxy_url) as client:
            return await client.get(url, ...)
```

---

### 6. **Content-Type Smart Detection** ⭐

**What they do:**
```python
content_type = response.headers.get("content-type", "")
is_page_html = (
    "<html" in page_raw[:100] or      # Check content
    "text/html" in content_type or    # Check header
    not content_type                   # Default to HTML
)

if is_page_html and not force_raw:
    return extract_content_from_html(page_raw), ""
else:
    return (
        page_raw,
        f"Content type {content_type} cannot be simplified to markdown"
    )
```

**Why it matters:**
- ✅ Handles PDFs, JSON, XML appropriately
- ✅ Avoids errors on non-HTML content
- ✅ Clear messaging to users
- ✅ Optional raw access

**Implementation:**
```python
async def _determine_extraction_method(self, url: str, html: str, headers: dict):
    content_type = headers.get('content-type', '').lower()

    # HTML content
    if 'text/html' in content_type or '<html' in html[:100]:
        return 'readability'  # or 'vlm' for complex pages

    # JSON content
    elif 'application/json' in content_type:
        return 'json_parser'

    # PDF content
    elif 'application/pdf' in content_type:
        return 'pdf_extractor'

    # Markdown already
    elif 'text/markdown' in content_type:
        return 'raw'

    # Unknown - return raw
    else:
        return 'raw'
```

---

## 🚀 Recommended Implementation Plan

### Phase 1: High Priority (1-2 days)

1. **Add Robots.txt Checker**
   - Install: `pip install protego`
   - Create: `tools/services/web_services/utils/robots_checker.py`
   - Integrate into `WebCrawlService`

2. **Add Readability Extraction**
   - Install: `pip install readabilipy markdownify`
   - Create: `tools/services/web_services/utils/content_extractor.py`
   - Update extraction pipeline: Readability → BS4 → VLM

3. **Update User-Agent**
   - Define transparent UA strings
   - Add to configuration
   - Use in all HTTP requests

---

### Phase 2: Medium Priority (2-3 days)

4. **Add Content Pagination**
   - Add `max_length` and `start_index` parameters
   - Implement chunking logic
   - Add continuation prompts

5. **Add Proxy Support**
   - Add `proxy_url` parameter/env var
   - Pass to httpx/playwright

6. **Enhance Content-Type Detection**
   - Smart detection logic
   - Handler routing based on type
   - Clear error messages

---

### Phase 3: Polish (1 day)

7. **Testing & Documentation**
   - Unit tests for new features
   - Update tool docstrings
   - Usage examples

---

## 📝 File Structure

```
tools/services/web_services/
├── utils/
│   ├── robots_checker.py        # NEW: Robots.txt compliance
│   ├── content_extractor.py     # NEW: Readability + MD conversion
│   └── user_agents.py           # NEW: UA configuration
├── services/
│   ├── web_crawl_service.py     # ENHANCE: Add new features
│   └── web_search_service.py    # ENHANCE: Add robots check
└── config.py                     # NEW: Configuration constants
```

---

## 🔧 Dependencies to Add

```bash
pip install protego readabilipy markdownify
```

Or in `requirements.txt`:
```
protego>=0.3.0          # Robots.txt parsing
readabilipy>=0.2.0      # Content extraction
markdownify>=0.11.0     # HTML to Markdown
```

---

## ✅ Benefits Summary

### Immediate Benefits
1. ✅ **Legal Compliance** - Robots.txt respect
2. ✅ **Better Content** - Readability extraction
3. ✅ **Large Pages** - Pagination support
4. ✅ **Transparency** - Clear User-Agent
5. ✅ **Flexibility** - Proxy support

### Long-term Benefits
1. ✅ **Avoid IP Bans** - Respectful scraping
2. ✅ **Cleaner Data** - Better LLM inputs
3. ✅ **User Trust** - Ethical practices
4. ✅ **Debugging** - Clear error messages
5. ✅ **Maintainability** - Standard patterns

---

## 🎯 Next Steps

1. Review this analysis
2. Prioritize enhancements
3. Start with Phase 1 (high priority)
4. Test incrementally
5. Update documentation

**Ready to implement? Let me know which enhancements to start with!** 🚀

---

**Created**: 2025-10-18
**Based on**: MCP Fetch Server Analysis
**Status**: 📋 Recommendations Ready
