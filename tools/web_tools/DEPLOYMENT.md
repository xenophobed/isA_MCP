# Web Tools 部署指南

## ✅ 实现完成

### 工具列表 (7个)

#### 🔍 搜索工具 (3个)
1. **web_search** - 基础网页搜索
   - Security Level: LOW
   - 支持过滤条件（freshness, result_filter, goggle_type）

2. **deep_web_search** - 深度搜索
   - Security Level: MEDIUM
   - 多策略智能搜索 + RAG模式

3. **web_search_with_summary** - 带摘要搜索
   - Security Level: MEDIUM
   - AI生成摘要 + 引用

#### 🕷️ 爬取工具 (1个)
4. **web_crawl** - 网页内容爬取
   - Security Level: MEDIUM
   - 提取title, content, links, images
   - 支持VLM视觉分析

#### 🤖 自动化工具 (2个)
5. **web_automation_execute** - 网页自动化执行
   - Security Level: HIGH
   - AI驱动的网页操作（点击、填表、提取数据）
   - 支持DOM-first/VLM-first/Hybrid策略

6. **web_automation_search** - 自动化搜索
   - Security Level: MEDIUM
   - 自动化搜索引擎操作 + 后续任务

#### ⚙️ 实用工具 (1个)
7. **web_service_health_check** - 健康检查
   - Security Level: LOW
   - 验证web service可用性

---

## 📦 已完成的工作

### 1. 文件结构
```
tools/web_tools/
├── __init__.py                 ✅ 模块导出
├── web_client.py               ✅ HTTP客户端 + SSE处理
├── web_tools.py                ✅ 7个MCP工具定义
├── README.md                   ✅ 完整文档
├── DEPLOYMENT.md               ✅ 本文件
└── tests/
    └── test_web_tools.sh       ✅ 测试脚本（更新为7个工具）
```

### 2. 配置更新
- ✅ `deployment/k8s/mcp-configmap.yaml` - 添加了WEB_SERVICE配置

### 3. 旧实现备份
- ✅ `tools/services/web_services.backup_20251117_095329/` - 旧实现已备份

### 4. 验证测试
- ✅ 所有7个工具成功注册
- ✅ SSE进度追踪正常
- ✅ API调用正常
- ✅ Consul可选导入（不可用时自动降级）

---

## 🚀 部署步骤

### 方式1: 自动发现（推荐）

根据 `core/auto_discovery.py`，系统会自动发现并注册 `web_tools`：

**自动发现逻辑**：
1. 扫描 `tools/` 目录下的所有 `*_tools.py` 文件
2. 查找 `register_{module_name}` 函数
3. 调用该函数注册工具

**我们的实现**：
- 文件：`tools/web_tools/web_tools.py`
- 函数：`register_web_tools(mcp)` ✅
- 符合命名规范 ✅

**重启 MCP Pod 即可自动发现**：
```bash
# 重启 MCP pod
kubectl rollout restart deployment mcp -n isa-cloud-staging

# 验证工具注册
kubectl logs -n isa-cloud-staging -l app=mcp --tail=100 | grep "web_tools"

# 应该看到类似：
# ✅ Registered tools from web_tools
# 🔧 Tools discovered: ... (包含7个web工具)
```

### 方式2: 手动验证

在重启前可以本地验证：

```bash
# 运行测试
cd /Users/xenodennis/Documents/Fun/isA_MCP
./tools/web_tools/tests/test_web_tools.sh

# 预期输出：
# ✅ All 7 tools registered as MCP tools
# ✅ Tool discovery working correctly
```

---

## 📊 工具同步到 Tool Service

根据 `services/sync_service/sync_service.py`，工具会自动同步到 PostgreSQL：

### 同步流程
```
Auto Discovery → MCP Tools → Tool Service → PostgreSQL
                                  ↓
                            Tool Repository
                         (tools表 + metadata)
```

### 验证同步
```bash
# 查看工具服务日志
kubectl logs -n isa-cloud-staging -l app=tool-service --tail=50

# 或查询数据库
kubectl exec -it postgres-0 -n isa-cloud-staging -- psql -U postgres -d isa_cloud

SELECT name, category, enabled FROM tools WHERE name LIKE 'web_%';
```

预期结果：
```
          name           |   category   | enabled
-------------------------+--------------+---------
 web_search              | search       | t
 deep_web_search         | search       | t
 web_search_with_summary | search       | t
 web_crawl               | crawl        | t
 web_automation_execute  | automation   | t
 web_automation_search   | automation   | t
 web_service_health_check| utility      | t
```

---

## 🔧 配置验证

### 确认环境变量

```bash
kubectl get configmap mcp-config -n isa-cloud-staging -o yaml | grep WEB_
```

应该看到：
```yaml
WEB_SERVICE_NAME: "web_service"
WEB_SERVICE_URL: "http://web.isa-cloud-staging.svc.cluster.local:8083"
WEB_FALLBACK_HOST: "web.isa-cloud-staging.svc.cluster.local"
WEB_FALLBACK_PORT: "8083"
```

### 确认 Web Service 运行

```bash
kubectl get svc web -n isa-cloud-staging
kubectl get pods -l app=web -n isa-cloud-staging
```

---

## 🧪 测试计划

### 1. 基础功能测试

```bash
# 在 MCP pod 中测试
kubectl exec -it mcp-xxx -n isa-cloud-staging -- python3 << 'EOF'
from tools.web_tools import register_web_tools
from mcp.server.fastmcp import FastMCP
from core.security import initialize_security

initialize_security()
mcp = FastMCP("test")
register_web_tools(mcp)

tools = list(mcp._tool_manager._tools.keys())
print(f"Registered tools: {len(tools)}")
for tool in sorted([t for t in tools if 'web' in t]):
    print(f"  ✓ {tool}")
EOF
```

### 2. API集成测试

```bash
# 测试搜索
curl -X POST http://mcp-service:8000/api/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "web_search",
    "parameters": {
      "query": "Python programming",
      "count": 3
    }
  }'

# 测试爬取
curl -X POST http://mcp-service:8000/api/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "web_crawl",
    "parameters": {
      "url": "https://example.com"
    }
  }'
```

### 3. Claude Desktop 测试

在 Claude Desktop 中测试：
```
User: Search for recent AI news using web_search
User: Crawl https://example.com and extract the content
User: Use web_automation to search for Python tutorials on Google
```

---

## 📝 关键差异：新 vs 旧

### 旧实现 (`tools/services/web_services/`)
- ❌ 使用 ProgressManager 管理进度
- ❌ 需要客户端轮询 `/progress/{id}/stream`
- ❌ 复杂的 progress context 管理
- ❌ 在 `services` 目录下（可能不会被自动发现）

### 新实现 (`tools/web_tools/`)
- ✅ Web service 直接返回 SSE
- ✅ Client 自动处理 SSE 流
- ✅ 简单直接的实现
- ✅ 在 `tools` 根目录（符合自动发现规范）
- ✅ 完整的7个工具（search + crawl + automation）

---

## ⚠️ 注意事项

### 1. Security Levels
- LOW: web_search, web_service_health_check
- MEDIUM: deep_web_search, web_search_with_summary, web_crawl, web_automation_search
- HIGH: web_automation_execute

确保调用者有相应权限。

### 2. Consul 依赖
- Consul 是**可选的**
- 没有 consul 时自动使用 fallback URL
- 不影响功能

### 3. 超时设置
- 默认 120 秒（适合 web 操作）
- Deep search 可能需要更长时间
- 可通过 `WebServiceConfig.api_timeout` 调整

### 4. Rate Limiting
- Web service 可能有 rate limit
- 注意避免频繁调用
- 监控 `execution_time` 指标

---

## 🐛 故障排查

### 工具未注册
```bash
# 1. 检查文件命名
ls -la tools/web_tools/web_tools.py
# 应该存在

# 2. 检查 register 函数
grep -n "def register_web_tools" tools/web_tools/web_tools.py
# 应该找到函数定义

# 3. 查看发现日志
kubectl logs -l app=mcp -n isa-cloud-staging | grep "web_tools"
```

### SSE 流处理失败
```bash
# 测试 web service SSE
curl -N http://localhost/api/v1/web/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "count": 1}'

# 应该看到 SSE 消息流
```

### 工具执行超时
```python
# 增加超时
from tools.web_tools.web_client import WebServiceConfig, WebServiceClient

config = WebServiceConfig(api_timeout=300)  # 5分钟
client = WebServiceClient(config)
```

---

## 📈 监控指标

关注以下指标：
- 工具调用频率
- SSE 连接数
- 执行时间分布
- 错误率
- Web service 健康状态

```bash
# 查看工具调用统计
kubectl exec -it postgres-0 -n isa-cloud-staging -- psql -U postgres -d isa_cloud

SELECT
    name,
    execution_count,
    avg_execution_time,
    last_executed_at
FROM tools
WHERE name LIKE 'web_%'
ORDER BY execution_count DESC;
```

---

## ✅ 部署清单

- [x] 备份旧的 web_services
- [x] 实现 web_client.py (SSE 支持)
- [x] 实现 web_tools.py (7个工具)
- [x] 更新 mcp-configmap.yaml
- [x] 创建测试脚本
- [x] 验证工具注册
- [ ] **重启 MCP Pod**
- [ ] 验证自动发现
- [ ] 验证工具同步到数据库
- [ ] Claude Desktop 集成测试

---

## 🎯 下一步

1. **重启 MCP Pod**:
   ```bash
   kubectl rollout restart deployment mcp -n isa-cloud-staging
   ```

2. **验证部署**:
   ```bash
   # 查看日志
   kubectl logs -f -l app=mcp -n isa-cloud-staging

   # 等待看到：
   # ✅ Registered tools from web_tools
   # 🔧 Tools discovered: ...
   ```

3. **测试工具**:
   ```bash
   ./tools/web_tools/tests/test_web_tools.sh
   ```

4. **Claude Desktop 测试**:
   - 打开 Claude Desktop
   - 连接到 MCP server
   - 测试各个 web 工具

---

**部署完成后，您将拥有完整的 Web 工具套件！** 🚀
