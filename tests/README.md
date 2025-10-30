# MCP Test Suite

## Search vs Discover 的区别

经过检查代码，发现：

- **`/discover`** - 唯一的自定义AI搜索endpoint，使用 `search_service` 进行语义搜索
- **`/search`** - **不存在**（之前文档中可能有误）

所以实际上只有一个AI搜索endpoint：`POST /discover`

## 可用的 Endpoints

### 1. 标准 MCP Endpoints (JSON-RPC 2.0)

**Base URL**: `POST /mcp`

**必需Headers**:
- `Content-Type: application/json`
- `Accept: application/json, text/event-stream`

**可用方法**:

1. **tools/list** - 列出所有工具
2. **tools/call** - 调用工具
3. **prompts/list** - 列出所有prompts
4. **prompts/get** - 获取prompt
5. **resources/list** - 列出所有resources
6. **resources/read** - 读取resource

### 2. 自定义 REST Endpoints

1. **`GET /health`** - 健康检查
2. **`POST /discover`** - AI智能搜索（语义搜索tools/prompts/resources）

## 快速测试

### 测试 Health
```bash
curl http://localhost:8081/health
```

### 测试 Tools List
```bash
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

### 测试 AI Discover
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "weather"}'
```

### 测试 Call Tool
```bash
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 1,
    "params": {
      "name": "get_weather",
      "arguments": {"city": "San Francisco"}
    }
  }'
```

## 运行完整测试

```bash
cd /Users/xenodennis/Documents/Fun/isA_MCP
./tests/mcp_client_test.sh

# 详细输出
VERBOSE=true ./tests/mcp_client_test.sh

# 指定不同的服务器
MCP_URL=http://other-server:8081 ./tests/mcp_client_test.sh
```

## 当前注册的能力

- **48 Tools** - 各种工具（weather, image, data, memory等）
- **46 Prompts** - 各种prompt模板
- **9 Resources** - 各种资源

