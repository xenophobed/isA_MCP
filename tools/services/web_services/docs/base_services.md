# Web Services 基础服务架构

## 🎯 基础服务分层设计

### Layer 1: 引擎层 (Engines)
```
engines/
├── browser_engine.py      # Playwright浏览器引擎
├── search_engine.py       # 搜索引擎 (Brave API等)
└── extraction_engine.py   # 内容提取引擎
```

### Layer 2: 策略层 (Strategies) 
```
strategies/
├── detection/             # 元素检测策略
│   ├── css_strategy.py    # CSS选择器策略
│   ├── ai_strategy.py     # AI视觉策略
│   └── hybrid_strategy.py # 混合策略
├── extraction/            # 内容提取策略
│   ├── css_extraction.py  # CSS提取
│   ├── llm_extraction.py  # LLM提取
│   └── regex_extraction.py # 正则提取
├── filtering/             # 内容过滤策略
│   ├── pruning_filter.py  # 修剪过滤
│   └── bm25_filter.py     # BM25过滤
└── generation/            # 内容生成策略
    └── markdown_generator.py # Markdown生成
```

### Layer 3: 核心服务层 (Core Services) - 现有保留
```
core/
├── browser_manager.py     # 浏览器管理
├── session_manager.py     # 会话管理
├── stealth_manager.py     # 反检测
└── ...
```

### Layer 4: 工具层 (Utils) - 现有保留
```
utils/
├── human_behavior.py      # 人类行为模拟
├── rate_limiter.py        # 速率限制
├── proxy_manager.py       # 代理管理
└── ...
```

## 🔧 基础服务接口设计

### 1. Web Automation Service
```python
class WebAutomationService:
    async def detect_elements(strategy, page, element_type)
    async def perform_action(action_type, element, data)
    async def verify_result(page, success_criteria)
```

### 2. Web Search Service  
```python
class WebSearchService:
    async def search(query, provider, filters)
    async def aggregate_results(results_list)
    async def deduplicate(results)
```

### 3. Web Crawling Service
```python
class WebCrawlingService:
    async def crawl(url, extraction_strategy, filter_strategy)
    async def generate_markdown(html, generator_strategy)
    async def chunk_content(content, strategy)
```

## 📋 实施步骤

1. **Step 1**: 创建engines层的基础引擎
2. **Step 2**: 实现strategies层的策略模式
3. **Step 3**: 重构现有代码到新架构
4. **Step 4**: 测试基础服务
5. **Step 5**: 封装为MCP能力