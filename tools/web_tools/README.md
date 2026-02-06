# Web Tools for MCP Server

MCP工具包，用于通过web微服务进行网页搜索和自动化操作，支持SSE实时进度追踪。

## 特性

- ✅ **SSE流式进度追踪** - Web service直接返回Server-Sent Events，实时显示搜索进度
- ✅ **基于微服务架构** - 通过专门的web service API进行搜索，而不是直接调用第三方API
- ✅ **Consul服务发现** - 支持通过Consul自动发现web service（可选）
- ✅ **优雅降级** - Consul不可用时自动使用fallback URL
- ✅ **继承BaseTool** - 统一的响应格式和错误处理
- ✅ **安全机制** - 集成SecurityManager，支持多级别安全检查

## 架构设计

```
┌─────────────────┐
│   MCP Client    │
│   (Claude等)     │
└────────┬────────┘
         │ MCP协议
         ▼
┌─────────────────┐
│   web_tools     │  ← 本模块
│  (MCP Tools)    │
└────────┬────────┘
         │ HTTP + SSE
         ▼
┌─────────────────┐
│  web_client     │  ← HTTP客户端 + SSE处理
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
    ▼          ▼
┌────────┐ ┌────────────┐
│ Consul │ │ Web Service│
│(可选)   │ │  (port 80) │
└────────┘ └──────┬─────┘
                  │
                  ▼
           ┌──────────────┐
           │ Brave Search │
           │  APISIX等    │
           └──────────────┘
```

## 与旧实现的区别

### 旧方式 (tools/services/web_services/tools/)

- 使用 `ProgressManager` 来追踪进度
- 需要客户端轮询 `/progress/{operation_id}/stream`
- 复杂的进度上下文管理（search_progress_context.py）

### 新方式 (tools/web_tools/)

- **Web service直接返回SSE** - 不需要ProgressManager
- **web_client处理SSE流** - 自动收集进度更新
- **web_tools返回完整结果** - 包括进度历史和最终结果
- **更简单的实现** - 无需复杂的progress context

## 文件结构

```
tools/web_tools/
├── __init__.py              # 模块导出
├── web_client.py            # HTTP客户端 + SSE处理
├── web_tools.py             # MCP工具定义
├── README.md                # 本文档
└── tests/
    └── test_web_tools.sh    # 集成测试脚本
```

## 工具列表

### 搜索工具 (3个)

1. **web_search** - 基础网页搜索
   - 支持过滤条件（freshness, result_filter, goggle_type）
   - 实时SSE进度追踪
   - 返回搜索结果 + 进度历史

2. **deep_web_search** - 深度搜索
   - 多策略智能搜索
   - 查询优化和迭代
   - 可选RAG模式

3. **web_search_with_summary** - 带摘要的搜索
   - AI生成摘要
   - 来源引用
   - 可定制摘要数量

### 实用工具 (1个)

4. **web_service_health_check** - 健康检查
   - 验证web service可用性
   - 返回服务状态和响应时间

## 配置

### 环境变量

通过 `mcp-configmap.yaml` 配置：

```yaml
# Web Service配置
WEB_SERVICE_NAME: "web_service"
WEB_SERVICE_URL: "http://web.isa-cloud-staging.svc.cluster.local:8083"
WEB_FALLBACK_HOST: "web.isa-cloud-staging.svc.cluster.local"
WEB_FALLBACK_PORT: "8083"

# Consul配置（可选）
CONSUL_HOST: "consul-agent.isa-cloud-staging.svc.cluster.local"
CONSUL_PORT: "8500"
```

### WebServiceConfig

```python
@dataclass
class WebServiceConfig:
    service_name: str = "web_service"
    consul_host: str = "localhost"
    consul_port: int = 8500
    api_timeout: int = 120  # 网页操作超时较长
    max_retries: int = 3
    fallback_host: str = "localhost"
    fallback_port: int = 8083
```

## 使用示例

### 1. 基础搜索

```python
from tools.web_tools import register_web_tools
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my_app")
register_web_tools(mcp)

# 调用工具
result = await mcp.tools['web_search'](
    query="Python programming",
    count=10
)
```

### 2. 带过滤的搜索

```python
result = await mcp.tools['web_search'](
    query="AI news",
    count=5,
    freshness="day",      # 最近一天
    result_filter="news"  # 只返回新闻
)
```

### 3. 深度搜索

```python
result = await mcp.tools['deep_web_search'](
    query="machine learning trends",
    user_id="user123",
    depth=2,           # 搜索深度
    rag_mode=True     # 启用RAG处理
)
```

### 4. 带摘要的搜索

```python
result = await mcp.tools['web_search_with_summary'](
    query="climate change solutions",
    user_id="user123",
    count=10,
    summarize_count=5,
    include_citations=True
)
```

## 响应格式

所有工具返回统一的JSON格式：

```json
{
  "status": "success",
  "action": "web_search",
  "data": {
    "query": "Python programming",
    "results": [
      {
        "title": "Welcome to Python.org",
        "url": "https://www.python.org/",
        "description": "The official home of the Python Programming Language",
        "score": 1.0,
        "source": "brave"
      }
    ],
    "total_results": 5,
    "execution_time": 1.23,
    "provider": "brave",
    "progress_history": [
      {"progress": 0.1, "message": "Starting search..."},
      {"progress": 0.5, "message": "Executing search..."},
      {"progress": 0.9, "message": "Search completed"},
      {"progress": 1.0, "message": "Done"}
    ]
  }
}
```

## SSE进度追踪

Web service通过SSE返回实时进度：

```
data: {"message": "Starting search...", "progress": 0.1}
data: {"message": "Using brave provider...", "progress": 0.2}
data: {"message": "Executing search...", "progress": 0.5}
data: {"message": "Search completed", "progress": 0.9}
data: {"message": "Done", "progress": 1.0, "result": {...}, "completed": true}
```

web_client自动处理这些SSE消息：
1. 收集所有进度更新
2. 提取最终结果
3. 返回完整数据（结果 + 进度历史）

## 测试

### 运行测试脚本

```bash
# 基础测试（快速）
cd /Users/xenodennis/Documents/Fun/isA_MCP
./tools/web_tools/tests/test_web_tools.sh

# 包含深度搜索和摘要测试
RUN_DEEP_TESTS=yes RUN_SUMMARY_TESTS=yes ./tools/web_tools/tests/test_web_tools.sh
```

### 测试内容

- ✅ 工具注册和发现
- ✅ 服务健康检查
- ✅ 基础搜索功能
- ✅ 搜索过滤条件
- ✅ SSE进度追踪
- ✅ 深度搜索（可选）
- ✅ 带摘要搜索（可选）

## 依赖项

### 必需
- `aiohttp` - HTTP客户端和SSE处理
- `mcp` - MCP协议支持
- Core模块（security, logging, base_tool）

### 可选
- `python-consul` - Consul服务发现（无此依赖时自动使用fallback URL）

## 故障排查

### Consul不可用

**症状**: `ModuleNotFoundError: No module named 'consul'`

**解决**: 自动使用fallback URL，无需安装consul。如需consul支持：
```bash
pip install python-consul
```

### Web service不可达

**症状**: `Connection refused` 或超时

**检查**:
```bash
# 1. 验证服务运行
kubectl get svc web -n isa-cloud-staging

# 2. 测试连通性
curl http://localhost/api/v1/web/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "count": 1}'

# 3. 检查环境变量
echo $WEB_FALLBACK_HOST
echo $WEB_FALLBACK_PORT
```

### SSE流处理失败

**症状**: 进度更新收集失败

**原因**:
- 网络中断
- 超时设置过短
- JSON解析错误

**解决**:
```python
# 增加超时
config = WebServiceConfig(api_timeout=180)
client = WebServiceClient(config)
```

## 性能优化

### 超时设置

```python
# 快速搜索
config = WebServiceConfig(api_timeout=30)

# 深度搜索
config = WebServiceConfig(api_timeout=180)
```

### 重试策略

```python
# 更多重试
config = WebServiceConfig(max_retries=5)
```

### Session管理

客户端自动管理aiohttp session：
- 每次请求后自动关闭
- 避免unclosed session警告
- 支持连接池复用

## 安全性

### SecurityLevel

- `LOW` - web_search, web_service_health_check
- `MEDIUM` - deep_web_search, web_search_with_summary

### 安全检查

所有工具都经过：
1. `@security_manager.security_check` - 基础安全验证
2. `@security_manager.require_authorization` - 权限级别检查

## 开发指南

### 添加新工具

1. 在 `web_client.py` 添加新的API方法
2. 在 `web_tools.py` 注册新的MCP工具
3. 添加安全装饰器
4. 更新测试脚本

### 处理SSE流

```python
async def search(self, query: str) -> AsyncGenerator:
    async for message in self._request_sse("POST", "/api/v1/web/search", json={"query": query}):
        # message 是解析后的dict
        yield message

        # 检查完成
        if message.get('completed'):
            break
```

## 相关文档

- [Consul服务发现](https://code.claude.com/docs/en/claude_code_docs_map.md)
- [BaseTool文档](/Users/xenodennis/Documents/Fun/isA_MCP/tools/base_tool.py)
- [Web Service API](/Users/xenodennis/Documents/Fun/isA_OS/web_services/)

## 更新日志

### v1.0.0 (2025-11-17)

- ✅ 初始实现
- ✅ SSE流式进度追踪
- ✅ 3个搜索工具 + 1个健康检查工具
- ✅ Consul服务发现支持（可选）
- ✅ 完整的测试套件
- ✅ 优雅降级机制

## 许可证

ISA Cloud Platform - Internal Use Only
