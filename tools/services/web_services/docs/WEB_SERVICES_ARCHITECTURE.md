# Web Services Architecture Documentation

## 📁 Directory Structure

```
tools/services/web_services/
├── web_tools.py              # 🎯 MCP Tool Registration (Entry Point)
│
├── services/                  # 🎨 High-Level Service Layer
│   ├── web_search_service.py    # Web search functionality
│   ├── web_crawl_service.py     # Web crawling & content extraction
│   ├── web_automation_service.py # Browser automation
│   └── bs4_service.py           # BeautifulSoup extraction
│
├── engines/                   # ⚙️ Processing Engines
│   ├── search_engine.py         # Search strategies (Brave, etc.)
│   ├── extraction_engine.py     # Content extraction logic
│   └── detection_engine.py      # Element detection
│
├── core/                      # 🔧 Core Components
│   ├── browser_manager.py       # Playwright browser management
│   ├── session_manager.py       # Session handling
│   ├── extraction_service.py    # Extraction coordination
│   ├── action_executor.py       # Action execution
│   └── stealth_manager.py       # Anti-detection
│
├── strategies/                # 🎲 Strategy Implementations
│   ├── actions/                 # Action strategies (click, scroll, etc.)
│   ├── extraction/              # Extraction strategies
│   ├── filtering/               # Content filtering (BM25, etc.)
│   ├── detection/               # Element detection strategies
│   └── generation/              # Content generation
│
├── utils/                     # 🛠️ Utilities (NEW - MCP Enhancements)
│   ├── robots_checker.py        # ✨ NEW: Robots.txt compliance
│   ├── content_extractor.py     # ✨ NEW: Readability + Markdown
│   ├── user_agents.py           # ✨ NEW: User-Agent management
│   ├── rate_limiter.py          # Existing: Rate limiting
│   ├── proxy_manager.py         # Existing: Proxy handling
│   └── human_behavior.py        # Existing: Human-like behavior
│
├── models/                    # 📦 Data Models
│   └── (data structures)
│
├── configs/                   # ⚙️ Configuration
│   └── (config files)
│
├── docs/                      # 📚 Documentation
│   ├── web_tools.md
│   ├── web_search.md
│   ├── web_crawl.md
│   └── web_automation.md
│
└── tests/                     # 🧪 Tests
    └── (test files)
```

---

## 🔄 Data Flow Architecture

### **Layer 1: MCP Tools (Entry Point)**
```
web_tools.py
  ↓
  register_web_tools(mcp)
    ├── @mcp.tool() web_search()
    ├── @mcp.tool() web_crawl()
    ├── @mcp.tool() web_crawl_compare()
    └── @mcp.tool() web_automation()
```

### **Layer 2: Service Layer**
```
WebToolsService (web_tools.py)
  ├── WebSearchService (services/web_search_service.py)
  │     └── Uses: SearchEngine (engines/search_engine.py)
  │           └── Uses: BraveSearchStrategy
  │
  ├── WebCrawlService (services/web_crawl_service.py)
  │     ├── Uses: BS4Service (services/bs4_service.py)
  │     ├── Uses: ContentExtractor (utils/content_extractor.py) ✨ NEW
  │     └── Uses: RobotsChecker (utils/robots_checker.py) ✨ NEW
  │
  └── WebAutomationService (services/web_automation_service.py)
        ├── Uses: BrowserManager (core/browser_manager.py)
        ├── Uses: ActionExecutor (core/action_executor.py)
        └── Uses: ExtractionService (core/extraction_service.py)
```

### **Layer 3: Engines**
```
SearchEngine (engines/search_engine.py)
  └── Strategies: Brave, Google, Bing, etc.

ExtractionEngine (engines/extraction_engine.py)
  └── Coordinates extraction strategies

DetectionEngine (engines/detection_engine.py)
  └── Element detection logic
```

### **Layer 4: Core Components**
```
BrowserManager → Playwright browser lifecycle
SessionManager → Session persistence
ActionExecutor → Execute browser actions
StealthManager → Anti-detection measures
ExtractionService → Content extraction coordination
```

### **Layer 5: Strategies**
```
strategies/actions/ → Click, Scroll, Navigate, etc.
strategies/extraction/ → Various extraction methods
strategies/filtering/ → BM25, Pruning filters
strategies/detection/ → Element detection methods
```

### **Layer 6: Utilities**
```
✨ NEW:
  robots_checker.py → Robots.txt compliance
  content_extractor.py → Readability + Markdown
  user_agents.py → User-Agent management

Existing:
  rate_limiter.py → Rate limiting
  proxy_manager.py → Proxy rotation
  human_behavior.py → Human-like actions
```

---

## 🎯 Integration Points for MCP Enhancements

### **Where to Add New Features:**

#### **1. Robots.txt Checking**
**Location**: `utils/robots_checker.py` ✅ Created
**Used by**:
- `services/web_crawl_service.py` (check before crawling)
- `services/web_search_service.py` (check before following links)
- `services/web_automation_service.py` (check before automation)

**Integration**:
```python
# In web_crawl_service.py
from tools.services.web_services.utils.robots_checker import get_robots_checker

class WebCrawlService:
    def __init__(self, check_robots=True):
        self.robots_checker = get_robots_checker() if check_robots else None

    async def crawl_and_analyze(self, url, ...):
        # Check robots.txt
        if self.robots_checker:
            can_fetch, reason = await self.robots_checker.can_fetch(url)
            if not can_fetch:
                return {"error": "robots_txt_blocked", "reason": reason}

        # Proceed with crawl...
```

---

#### **2. Readability Extraction**
**Location**: `utils/content_extractor.py` ✅ Created
**Used by**:
- `services/web_crawl_service.py` (primary content extraction)
- `services/bs4_service.py` (enhanced extraction option)

**Integration**:
```python
# In web_crawl_service.py
from tools.services.web_services.utils.content_extractor import get_content_extractor

class WebCrawlService:
    def __init__(self):
        self.content_extractor = get_content_extractor()

    async def _extract_content(self, html, url):
        # Try readability first
        result = self.content_extractor.extract(html, url)

        if result['success'] and result['method'] == 'readability':
            return result  # Best quality

        # Fallback to BS4
        return await self._bs4_extraction(html)
```

---

#### **3. User-Agent Management**
**Location**: `utils/user_agents.py` ✅ Created
**Used by**:
- All services that make HTTP requests
- `core/browser_manager.py` (Playwright user-agent)
- `utils/rate_limiter.py` (request headers)

**Integration**:
```python
# In web_crawl_service.py
from tools.services.web_services.utils.user_agents import get_user_agent

class WebCrawlService:
    def __init__(self, autonomous=True):
        self.user_agent = get_user_agent(autonomous=autonomous)

    async def _fetch_html(self, url):
        response = requests.get(url, headers={"User-Agent": self.user_agent})
```

---

#### **4. Content Pagination**
**Location**: `utils/content_extractor.py` ✅ Implemented
**Used by**:
- `web_tools.py` (add max_length, start_index parameters)
- `services/web_crawl_service.py` (implement pagination)

**Integration**:
```python
# In web_tools.py
@mcp.tool()
async def web_crawl(
    url: str,
    analysis_request: str = "",
    max_length: int = 0,          # NEW: 0 = no pagination
    start_index: int = 0           # NEW: for pagination
) -> str:
    service = WebCrawlService()
    result = await service.crawl_and_analyze(
        url, analysis_request, max_length, start_index
    )
```

---

## 🔧 Recommended Enhancement Strategy

### **Phase 1: Non-Breaking Additions (Simple)**

**Step 1**: Add utility imports to existing services
```python
# In web_crawl_service.py (top of file)
try:
    from tools.services.web_services.utils.robots_checker import get_robots_checker
    from tools.services.web_services.utils.content_extractor import get_content_extractor
    from tools.services.web_services.utils.user_agents import get_user_agent
    HAS_ENHANCEMENTS = True
except ImportError:
    HAS_ENHANCEMENTS = False
```

**Step 2**: Add optional parameters to existing methods
```python
class WebCrawlService:
    def __init__(self, check_robots=False, autonomous=True):  # Default False = no breaking change
        if HAS_ENHANCEMENTS and check_robots:
            self.robots_checker = get_robots_checker()
            self.user_agent = get_user_agent(autonomous)
        else:
            self.robots_checker = None
            self.user_agent = "isA_MCP/1.0"
```

**Step 3**: Add enhanced extraction as fallback option
```python
async def _extract_content(self, html, url):
    if HAS_ENHANCEMENTS:
        # Try readability
        result = get_content_extractor().extract(html, url)
        if result['success']:
            return result

    # Existing BS4 fallback
    return await self._bs4_extraction(html)
```

---

### **Phase 2: New Optional Tools (No Breaking Changes)**

Add new MCP tools alongside existing ones:

```python
# In web_tools.py
@mcp.tool()
async def web_crawl_enhanced(  # NEW tool name
    url: str,
    analysis_request: str = "",
    check_robots: bool = True,   # NEW
    max_length: int = 0,          # NEW
    start_index: int = 0,         # NEW
    autonomous: bool = True       # NEW
) -> str:
    """Enhanced web crawling with robots.txt, readability, pagination"""
    service = EnhancedWebCrawlService(
        check_robots=check_robots,
        autonomous=autonomous
    )
    return await service.crawl_and_analyze(
        url, analysis_request, max_length, start_index
    )
```

**Benefits**:
- ✅ Original `web_crawl` unchanged
- ✅ New `web_crawl_enhanced` with new features
- ✅ Users can choose which to use
- ✅ Gradual migration path

---

## 💡 Simplest Integration Approach

### **Option A: Enhance Existing web_crawl_service.py (Minimal Changes)**

1. Add imports (with try/except for graceful degradation)
2. Add optional init parameters
3. Add robots check before crawl (optional)
4. Add readability extraction as primary method
5. Keep BS4 and VLM as fallbacks

**File to modify**: `services/web_crawl_service.py`
**Lines to add**: ~50 lines
**Breaking changes**: None (all optional)

---

### **Option B: Create Enhanced Wrapper (Zero Breaking Changes)**

1. Keep existing `web_crawl_service.py` untouched
2. Create `services/web_crawl_service_enhanced.py`
3. Wrapper uses existing service + new utilities
4. Register as new MCP tool

**Files to create**: 1 new file
**Files to modify**: `web_tools.py` (add new tool registration)
**Breaking changes**: Zero

---

## 🎯 Recommended Next Steps

Based on your complex architecture, I recommend **Option B** (Enhanced Wrapper):

1. ✅ **Already Created**:
   - `utils/robots_checker.py`
   - `utils/content_extractor.py`
   - `utils/user_agents.py`

2. **Next: Simple Integration** (2 steps):
   - Update `web_tools.py` to add new parameters to existing tools
   - OR create wrapper that uses existing services

**Which approach do you prefer?**
- **A**: Modify existing `web_crawl_service.py` (minimal, integrated)
- **B**: Create enhanced wrapper (safe, no breaking changes)
- **C**: Show me specific integration points and I'll decide

