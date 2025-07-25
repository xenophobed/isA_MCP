# MCP完整使用指南

这是一个完整的MCP (Model Context Protocol) 使用指南，包含Prompts、Tools和Resources的搜索和使用方法。所有示例都经过真实测试。

---

## 🎯 **Prompts 使用方法**

### 📝 **1. 搜索提示词**

**命令：**
```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{"query": "default_reason_prompt"}'
```

**搜索结果示例：**
```json
{
  "status": "success",
  "query": "default_reason_prompt",
  "results": [
    {
      "name": "default_reason_prompt",
      "type": "prompt",
      "description": "Default reasoning prompt for intelligent assistant interactions. Provides structured approach to analyzing user requests and determining the best response strategy using available capabilities.",
      "similarity_score": 1.0,
      "category": "general",
      "keywords": ["reasoning", "analysis", "memory", "tools", "resources", "assistant"],
      "metadata": {
        "arguments": [
          {
            "name": "user_message",
            "required": true,
            "description": null
          },
          {
            "name": "memory",
            "required": false,
            "description": null
          },
          {
            "name": "tools",
            "required": false,
            "description": null
          },
          {
            "name": "resources",
            "required": false,
            "description": null
          }
        ]
      }
    }
  ],
  "result_count": 1
}
```

### 🚀 **2. 使用提示词（带参数）**

**端点：** `http://localhost:8081/mcp/prompts/get`

**命令：**
```bash
curl -X POST http://localhost:8081/mcp/prompts/get \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "prompts/get",
    "params": {
      "name": "default_reason_prompt",
      "arguments": {
        "user_message": "Help me create a marketing plan",
        "memory": "User is interested in AI products",
        "tools": "web_search, create_execution_plan",
        "resources": "marketing_knowledge"
      }
    }
  }'
```

**使用结果示例：**
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"messages":[{"role":"user","content":{"type":"text","text":"You are an intelligent assistant with memory, tools, and resources to help users.\n\n## Your Capabilities:\n- **Memory**: You can remember previous conversations and user preferences\n- **Tools**: You can use various tools to gather information or execute tasks  \n- **Resources**: You can access knowledge bases and documentation resources\n\n## User Request:\nHelp me create a marketing plan\n\n## Your Options:\n1. **Direct Answer** - If you already know the answer\n2. **Use Tools** - If you need to gather information or execute specific tasks\n3. **Create Plan** - If this is a complex multi-step task\n\nPlease analyze the user request and choose the most appropriate way to help the user.\n\nNote: Memory context: User is interested in AI products, Available tools: web_search, create_execution_plan, Available resources: marketing_knowledge"}}]}}
```

### 💡 **3. Python使用示例**
```python
import requests
import json

def use_prompt_with_args(prompt_name, **arguments):
    """使用MCP提示词并传递参数"""
    response = requests.post(
        'http://localhost:8081/mcp/prompts/get',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/get",
            "params": {
                "name": prompt_name,
                "arguments": arguments
            }
        }
    )
    
    # 解析事件流响应
    lines = response.text.strip().split('\n')
    for line in lines:
        if line.startswith('data: '):
            data = json.loads(line[6:])
            if 'result' in data:
                return data['result']['messages'][0]['content']['text']
    return None

# 使用示例
prompt_result = use_prompt_with_args(
    'default_reason_prompt',
    user_message="Help me create a marketing plan",
    memory="User is interested in AI products",
    tools="web_search, create_execution_plan",
    resources="marketing_knowledge"
)

print(prompt_result)
```

---

## 🔧 **Tools 使用方法**

### 📝 **1. 搜索工具**

**命令：**
```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{"query": "web_search"}'
```

**搜索结果示例：**
```json
{
  "status": "success",
  "query": "web_search",
  "results": [
    {
      "name": "web_search",
      "type": "tool",
      "description": "Search the web for information\n\nKeywords: search, web, internet, query, results\nCategory: web\n\nArgs:\n    query: Search query\n    count: Number of results to return (default: 10)",
      "similarity_score": 1.0,
      "category": "web",
      "keywords": ["search", "web", "internet", "query", "results"],
      "metadata": {
        "input_schema": {
          "properties": {
            "query": {
              "title": "Query",
              "type": "string"
            },
            "count": {
              "default": 10,
              "title": "Count",
              "type": "integer"
            }
          },
          "required": ["query"],
          "title": "web_searchArguments",
          "type": "object"
        }
      }
    }
  ],
  "result_count": 1
}
```

### 🚀 **2. 使用工具（带参数）**

**端点：** `http://localhost:8081/mcp/tools/call`

**命令：**
```bash
curl -X POST http://localhost:8081/mcp/tools/call \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "web_search",
      "arguments": {
        "query": "AI marketing trends 2024",
        "count": 3
      }
    }
  }'
```

**使用结果示例：**
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\"status\": \"success\", \"action\": \"web_search\", \"data\": {\"success\": true, \"query\": \"AI marketing trends 2024\", \"total\": 3, \"results\": [{\"title\": \"AI Will Shape the Future of Marketing - Professional & Executive Development | Harvard DCE\", \"url\": \"https://professional.dce.harvard.edu/blog/ai-will-shape-the-future-of-marketing/\", \"snippet\": \"AI platforms like HubSpot, Constant Contact, Mailchimp, and ActiveCampaign are already being used by marketers to automate tasks and optimize campaigns.\", \"score\": 1.0}, {\"title\": \"2025 AI Trends for Marketers\", \"url\": \"https://offers.hubspot.com/ai-marketing\", \"snippet\": \"Stay sharp, scalable, and ahead of the curve. Marketers are turning AI into measurable outcomes by boosting productivity, improving personalization, and accelerating performance across campaigns.\", \"score\": 0.9}, {\"title\": \"How AI Is Revolutionizing Marketing In 2024: Top 5 Trends\", \"url\": \"https://www.forbes.com/sites/shelleykohan/2024/05/19/how-ai-is-revolutionizing-marketing-in-2024-top-5-trends/\", \"snippet\": \"MarTech will continue to focus on artificial intelligence (AI) and generative AI (GenAI) to drive unprecedented levels of personalization and customer engagement.\", \"score\": 0.8}], \"urls\": [\"https://professional.dce.harvard.edu/blog/ai-will-shape-the-future-of-marketing/\", \"https://offers.hubspot.com/ai-marketing\", \"https://www.forbes.com/sites/shelleykohan/2024/05/19/how-ai-is-revolutionizing-marketing-in-2024-top-5-trends/\"]}, \"timestamp\": \"2025-07-24T16:45:04.310648\"}"}],"isError":false}}
```

### 💡 **3. Python使用示例**
```python
import requests
import json

def use_tool(tool_name, **arguments):
    """使用MCP工具并传递参数"""
    response = requests.post(
        'http://localhost:8081/mcp/tools/call',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
    )
    
    # 解析事件流响应
    lines = response.text.strip().split('\n')
    for line in lines:
        if line.startswith('data: '):
            data = json.loads(line[6:])
            if 'result' in data:
                return json.loads(data['result']['content'][0]['text'])
    return None

# 使用示例
result = use_tool(
    'web_search',
    query="AI marketing trends 2024",
    count=3
)

print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

## 📚 **Resources 使用方法**

### 📝 **1. 搜索资源**

**命令：**
```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{"query": "event", "filters": {"types": ["resource"]}}'
```

**搜索结果示例：**
```json
{
  "status": "success",
  "query": "event",
  "results": [
    {
      "name": "event://tasks",
      "type": "resource",
      "description": "Get all background tasks as a resource. This resource provides a comprehensive view of all background tasks in the event sourcing system.",
      "similarity_score": 1.0,
      "category": "event",
      "keywords": ["background", "tasks", "resource", "system", "event"],
      "metadata": {
        "uri": "event://tasks",
        "mime_type": "text/plain"
      }
    },
    {
      "name": "event://status",
      "type": "resource", 
      "description": "Get event sourcing service status as a resource. This resource provides the current operational status of the event sourcing service.",
      "similarity_score": 1.0,
      "category": "event",
      "keywords": ["status", "service", "resource", "event"],
      "metadata": {
        "uri": "event://status",
        "mime_type": "text/plain"
      }
    }
  ],
  "result_count": 2
}
```

### 📝 **1.2 获取所有资源列表**

**命令：**
```bash
curl -X GET http://localhost:8081/capabilities
```

**结果示例：**
```json
{
  "status": "success",
  "capabilities": {
    "resources": {
      "count": 19,
      "available": [
        "guardrail://config/pii",
        "event://tasks", 
        "event://status",
        "shopify://catalog/collections",
        "symbolic://entities/catalog"
      ]
    }
  }
}
```

### 🚀 **2. 使用资源（读取内容）**

**端点：** `http://localhost:8081/mcp/resources/read`

**命令：**
```bash
curl -X POST http://localhost:8081/mcp/resources/read \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "resources/read",
    "params": {
      "uri": "event://status"
    }
  }'
```

**使用结果示例：**
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"event://status","mimeType":"text/plain","text":"{\n  \"resource_type\": \"event_service_status\",\n  \"status\": {\n    \"service_running\": false,\n    \"total_tasks\": 0,\n    \"active_tasks\": 0,\n    \"paused_tasks\": 0,\n    \"running_monitors\": 0,\n    \"task_types\": {\n      \"web_monitor\": 0,\n      \"schedule\": 0,\n      \"news_digest\": 0,\n      \"threshold_watch\": 0\n    }\n  },\n  \"generated_at\": \"2025-07-24T16:49:51.887189\",\n  \"description\": \"Current status of the event sourcing service\"\n}"}]}}
```

### 💡 **3. Python使用示例**
```python
import requests
import json

def search_resources(query):
    """搜索MCP资源"""
    response = requests.post(
        'http://localhost:8081/search',
        headers={'Content-Type': 'application/json'},
        json={
            "query": query,
            "filters": {"types": ["resource"]},
            "max_results": 10
        }
    )
    return response.json()

def read_resource(uri):
    """读取MCP资源内容"""
    response = requests.post(
        'http://localhost:8081/mcp/resources/read',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        }
    )
    
    # 解析事件流响应
    lines = response.text.strip().split('\n')
    for line in lines:
        if line.startswith('data: '):
            data = json.loads(line[6:])
            if 'result' in data:
                content = data['result']['contents'][0]['text']
                try:
                    return json.loads(content)  # 尝试解析JSON
                except:
                    return content  # 返回原始文本
    return None

# 使用示例1: 搜索资源
resources = search_resources('event')
print("搜索到的资源:")
for resource in resources['results']:
    print(f"- {resource['name']}: {resource['description'][:50]}...")

# 使用示例2: 读取资源内容
resource_data = read_resource('event://status')
print(json.dumps(resource_data, indent=2, ensure_ascii=False))
```

---

## 🎯 **默认集合搜索**

### 📝 **搜索所有默认能力**

**命令：**
```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{"query": "default", "max_results": 15}'
```

**搜索结果示例：**
```json
{
  "status": "success",
  "query": "default",
  "results": [
    {
      "name": "create_execution_plan",
      "type": "tool",
      "similarity_score": 1.0,
      "category": "general"
    },
    {
      "name": "web_search",
      "type": "tool", 
      "similarity_score": 1.0,
      "category": "web"
    },
    {
      "name": "default_reason_prompt",
      "type": "prompt",
      "similarity_score": 1.0,
      "category": "general"
    },
    {
      "name": "default_response_prompt",
      "type": "prompt",
      "similarity_score": 1.0,
      "category": "general"
    },
    {
      "name": "default_review_prompt",
      "type": "prompt",
      "similarity_score": 1.0,
      "category": "general"
    }
  ],
  "result_count": 9
}
```

### 📝 **搜索默认工具**

**命令：**
```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{"query": "default", "filters": {"types": ["tool"]}}'
```

### 📝 **搜索默认提示词**

**命令：**
```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{"query": "default", "filters": {"types": ["prompt"]}}'
```

---

## 📋 **重要说明**

1. **JSON-RPC格式**：所有MCP调用都使用JSON-RPC 2.0格式
2. **事件流响应**：响应采用Server-Sent Events格式，需要解析`data:`行
3. **必需头部**：调用MCP端点时必须包含`Accept: application/json, text/event-stream`
4. **参数验证**：工具和提示词的参数会进行类型检查和验证
5. **错误处理**：返回的`isError`字段指示是否有错误发生
6. **搜索支持**：
   - ✅ **Tools**: 完全支持搜索和语义匹配
   - ✅ **Prompts**: 完全支持搜索，metadata包含参数信息
   - ✅ **Resources**: 完全支持搜索和语义匹配
7. **默认集合**：搜索`"default"`可获取预定义的常用工具和提示词

所有示例都经过真实测试验证，可以直接使用。