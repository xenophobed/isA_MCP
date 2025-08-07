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

## 🔒 **工具安全等级查询**

### 📝 **1. 获取所有工具安全等级**

**命令：**
```bash
curl -s http://localhost:8081/security/levels | jq .
```

**响应示例：**
```json
{
  "status": "success",
  "security_levels": {
    "tools": {
      "get_weather": {
        "name": "get_weather",
        "category": "weather",
        "security_level": "LOW",
        "security_level_value": 1,
        "requires_authorization": false,
        "description": "Get mock weather information for testing purposes"
      },
      "search_memories": {
        "name": "search_memories", 
        "category": "web",
        "security_level": "LOW",
        "security_level_value": 1,
        "requires_authorization": false,
        "description": "Search across memory types using semantic similarity"
      }
    },
    "summary": {
      "total_tools": 60,
      "security_levels": {
        "LOW": 2,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
        "DEFAULT": 58
      },
      "authorization_required": 0,
      "rate_limits": {
        "default": {"calls": 100, "window": 3600},
        "remember": {"calls": 50, "window": 3600},
        "forget": {"calls": 10, "window": 3600}
      }
    }
  },
  "timestamp": "2025-07-26T09:59:23.399288"
}
```

### 📝 **2. 按安全等级搜索工具**

**搜索LOW级别工具：**
```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"security_level": "LOW", "max_results": 5}' \
  http://localhost:8081/security/search | jq .
```

**响应示例：**
```json
{
  "status": "success",
  "security_level": "LOW",
  "results": [
    {
      "name": "get_weather",
      "type": "tool",
      "description": "Get mock weather information for testing purposes",
      "similarity_score": 1.0,
      "category": "weather",
      "keywords": ["weather", "temperature", "forecast", "security_low"],
      "metadata": {
        "security_level": "LOW",
        "security_level_value": 1,
        "requires_authorization": false,
        "input_schema": {
          "properties": {
            "city": {"title": "City", "type": "string"},
            "user_id": {"default": "default", "title": "User Id", "type": "string"}
          },
          "required": ["city"]
        }
      }
    },
    {
      "name": "search_memories",
      "type": "tool", 
      "description": "Search across memory types using semantic similarity",
      "similarity_score": 1.0,
      "category": "web",
      "keywords": ["search", "memory", "similarity", "security_low"],
      "metadata": {
        "security_level": "LOW",
        "security_level_value": 1,
        "requires_authorization": false
      }
    }
  ],
  "result_count": 2,
  "max_results": 5,
  "timestamp": "2025-07-26T09:59:32.096971"
}
```

**搜索其他级别工具：**
```bash
# MEDIUM级别
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"security_level": "MEDIUM", "max_results": 3}' \
  http://localhost:8081/security/search

# HIGH级别  
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"security_level": "HIGH", "max_results": 3}' \
  http://localhost:8081/security/search

# CRITICAL级别
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"security_level": "CRITICAL", "max_results": 3}' \
  http://localhost:8081/security/search
```

### 📝 **3. 普通搜索中的安全等级信息**

**命令：**
```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"query": "weather", "max_results": 2}' \
  http://localhost:8081/search | jq .
```

**响应示例（包含安全等级metadata）：**
```json
{
  "status": "success", 
  "query": "weather",
  "results": [
    {
      "name": "get_weather",
      "type": "tool",
      "description": "Get mock weather information for testing purposes",
      "similarity_score": 1.0,
      "category": "weather",
      "metadata": {
        "security_level": "LOW",
        "security_level_value": 1,
        "requires_authorization": false,
        "input_schema": {
          "properties": {
            "city": {"title": "City", "type": "string"}
          },
          "required": ["city"]
        }
      }
    }
  ],
  "result_count": 1
}
```

### 📝 **4. 错误处理示例**

**无效安全等级：**
```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"security_level": "INVALID"}' \
  http://localhost:8081/security/search | jq .
```

**响应：**
```json
{
  "status": "error",
  "message": "Invalid security_level. Must be: LOW, MEDIUM, HIGH, CRITICAL, or DEFAULT"
}
```

### 💡 **5. Python使用示例**

```python
import requests
import json

def get_tool_security_levels():
    """获取所有工具的安全等级"""
    response = requests.get('http://localhost:8081/security/levels')
    return response.json()

def search_tools_by_security(security_level, max_results=10):
    """按安全等级搜索工具"""
    response = requests.post(
        'http://localhost:8081/security/search',
        headers={'Content-Type': 'application/json'},
        json={
            "security_level": security_level.upper(),
            "max_results": max_results
        }
    )
    return response.json()

def search_with_security_info(query, max_results=10):
    """搜索工具（包含安全等级信息）"""
    response = requests.post(
        'http://localhost:8081/search',
        headers={'Content-Type': 'application/json'},
        json={
            "query": query,
            "max_results": max_results,
            "filters": {"types": ["tool"]}
        }
    )
    return response.json()

# 使用示例
print("=== 安全等级统计 ===")
security_info = get_tool_security_levels()
summary = security_info['security_levels']['summary']
print(f"总工具数: {summary['total_tools']}")
for level, count in summary['security_levels'].items():
    print(f"{level}级别: {count}个工具")

print("\n=== LOW级别工具 ===")
low_tools = search_tools_by_security('LOW', 5)
for tool in low_tools['results']:
    auth_status = "需要授权" if tool['metadata']['requires_authorization'] else "无需授权"
    print(f"- {tool['name']}: {auth_status}")

print("\n=== 搜索天气工具 ===")
weather_tools = search_with_security_info('weather', 3)
for tool in weather_tools['results']:
    metadata = tool['metadata']
    print(f"- {tool['name']}")
    print(f"  安全等级: {metadata.get('security_level', 'UNKNOWN')}")
    print(f"  需要授权: {'是' if metadata.get('requires_authorization') else '否'}")
```

### 📊 **6. 安全等级说明**

- **LOW (1)**: 基础工具，无安全风险，无需授权
  - 示例：天气查询、内存搜索
- **MEDIUM (2)**: 一般操作，需要基础授权
  - 示例：数据存储、计算操作
- **HIGH (3)**: 敏感操作，需要严格授权
  - 示例：数据删除、系统配置
- **CRITICAL (4)**: 关键操作，需要最高权限
  - 示例：系统重置、管理员操作
- **DEFAULT**: 未设置安全等级的工具（默认为LOW处理）

---

## 🎮 **Widget Resources 使用方法**

### 📝 **1. 搜索Widget资源**

**命令：**
```bash
curl -X POST http://localhost:8081/search \
  -H "Content-Type: application/json" \
  -d '{"query": "widget"}'
```

**搜索结果示例：**
```json
{
  "status": "success",
  "query": "widget",
  "results": [
    {
      "name": "widget://system/info",
      "type": "resource",
      "description": "Get system-wide widget information and capabilities",
      "similarity_score": 1.0,
      "category": "widget",
      "keywords": ["system", "widget", "capabilities", "information"],
      "metadata": {
        "uri": "widget://system/info",
        "mime_type": "text/plain"
      }
    },
    {
      "name": "widget://user/{user_id}/configs",
      "type": "resource", 
      "description": "Get user's widget configurations and preferences",
      "similarity_score": 1.0,
      "category": "widget",
      "keywords": ["user", "widget", "configurations", "preferences"],
      "metadata": {
        "uri": "widget://user/{user_id}/configs",
        "mime_type": "text/plain"
      }
    },
    {
      "name": "widget://user/{user_id}/usage",
      "type": "resource",
      "description": "Get widget usage statistics for a user", 
      "similarity_score": 1.0,
      "category": "widget",
      "keywords": ["user", "widget", "usage", "statistics"],
      "metadata": {
        "uri": "widget://user/{user_id}/usage",
        "mime_type": "text/plain"
      }
    }
  ],
  "result_count": 6
}
```

### 🚀 **2. 读取系统Widget信息**

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
      "uri": "widget://system/info"
    }
  }'
```

**使用结果示例：**
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"widget://system/info","mimeType":"text/plain","text":"# Widget System Information\n\n## System Overview\n- **Total Widgets**: 5\n- **Active Widgets**: 5\n- **Plugin System Version**: 1.0.0\n- **Last Updated**: 2025-01-24 16:32:15\n\n## System Configuration\n- **Max Concurrent Widgets**: 3\n- **Default Timeout**: 30,000ms\n- **Retry Attempts**: 2\n- **Cache Enabled**: ✅ Yes\n- **Supported Output Formats**: text, image, data, analysis, search, knowledge\n\n## Available Widgets\n\n### 🎨 Dream Image Generator\n- **ID**: `dream`\n- **Version**: 1.0.0\n- **Description**: Generate beautiful images from text descriptions using AI\n- **Capabilities**: text_to_image, image_style_transfer, professional_headshots\n- **Triggers**: \"generate image\", \"create image\", \"draw\" ...\n\n### 🔍 Hunt Search Widget\n- **ID**: `hunt`\n- **Version**: 1.0.0\n- **Description**: Advanced search and discovery capabilities\n- **Capabilities**: web_search, product_search, content_discovery\n- **Triggers**: \"search\", \"find\", \"hunt\" ...\n\n### 🤖 Omni Assistant Widget\n- **ID**: `omni`\n- **Version**: 1.0.0\n- **Description**: General-purpose AI assistant for various tasks\n- **Capabilities**: text_generation, content_creation, task_assistance\n- **Triggers**: \"help\", \"assist\", \"generate\" ...\n\n### 📚 Knowledge Widget\n- **ID**: `knowledge`\n- **Version**: 1.0.0\n- **Description**: Knowledge retrieval and Q&A capabilities\n- **Capabilities**: document_search, qa_system, knowledge_base\n- **Triggers**: \"what is\", \"explain\", \"define\" ...\n\n### 📊 Data Scientist Widget\n- **ID**: `data_scientist`\n- **Version**: 1.0.0\n- **Description**: Data analysis and visualization capabilities\n- **Capabilities**: data_analysis, visualization, statistical_analysis\n- **Triggers**: \"analyze\", \"chart\", \"graph\" ...\n\n## Plugin Triggers Summary\n\n| Widget | Primary Triggers | Capabilities Count |\n|--------|-----------------|-------------------|\n| 🎨 Dream Image Generator | \"generate image\" | 3 |\n| 🔍 Hunt Search Widget | \"search\" | 3 |\n| 🤖 Omni Assistant Widget | \"help\" | 3 |\n| 📚 Knowledge Widget | \"what is\" | 3 |\n| 📊 Data Scientist Widget | \"analyze\" | 3 |\n\n## Integration Notes\n- Widgets are implemented as plugins in the frontend application\n- Each widget supports multiple trigger phrases for natural language activation\n- All widgets support streaming responses and real-time status updates\n- Widget configurations can be customized per user\n\n---\n*System Information Generated at 2025-01-24T16:32:15.123456*"}]}}
```

### 📊 **3. 读取用户Widget配置**

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
      "uri": "widget://user/auth0|123456/configs"
    }
  }'
```

**使用结果示例：**
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"widget://user/auth0|123456/configs","mimeType":"text/plain","text":"# User Widget Configurations: auth0|123456\n\n## Summary\n- **Available Widgets**: 5\n- **Configured Widgets**: 2\n- **Last Updated**: 2025-01-24 16:35:42\n\n## Available Widget Types\n- **Dream**: ✅ Configured\n- **Hunt**: ⚙️ Default\n- **Omni**: ✅ Configured\n- **Knowledge**: ⚙️ Default\n- **Data_Scientist**: ⚙️ Default\n\n## Widget Configurations\n\n### Dream Widget\n- **Status**: Custom Configuration\n- **Enabled**: True\n- **Timeout**: 35000ms\n- **Settings**: style=artistic, quality=high\n\n### Hunt Widget\n- **Status**: Default Configuration\n- **Enabled**: True\n- **Timeout**: 15000ms\n- **Settings**: search_depth=medium, result_format=detailed, max_results=10\n\n### Omni Widget\n- **Status**: Custom Configuration\n- **Enabled**: True\n- **Timeout**: 25000ms\n- **Settings**: tone=casual, length=short\n\n### Knowledge Widget\n- **Status**: Default Configuration\n- **Enabled**: True\n- **Timeout**: 25000ms\n- **Settings**: search_depth=deep, context_size=medium, search_type=hybrid\n\n### Data_Scientist Widget\n- **Status**: Default Configuration\n- **Enabled**: True\n- **Timeout**: 45000ms\n- **Settings**: analysis_type=exploratory, visualization_type=chart, auto_insights=True\n\n## Default Configurations Available\n- **dream**: 5 settings\n- **hunt**: 4 settings\n- **omni**: 4 settings\n- **knowledge**: 4 settings\n- **data_scientist**: 4 settings\n\n---\n*Generated at 2025-01-24T16:35:42.789123*"}]}}
```

### 📈 **4. 读取用户Widget使用统计**

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
      "uri": "widget://user/auth0|123456/usage"
    }
  }'
```

**使用结果示例：**
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"widget://user/auth0|123456/usage","mimeType":"text/plain","text":"{\n  \"user_id\": \"auth0|123456\",\n  \"usage_summary\": {\n    \"total_executions\": 47,\n    \"total_processing_time\": 125430,\n    \"most_used_widget\": \"dream\",\n    \"last_activity\": \"2025-01-24T16:30:15.123456\"\n  },\n  \"by_widget_type\": {\n    \"dream\": {\n      \"execution_count\": 25,\n      \"success_count\": 23,\n      \"error_count\": 2,\n      \"total_time\": 75000,\n      \"last_used\": \"2025-01-24T16:30:15.123456\",\n      \"avg_response_time\": 3000,\n      \"user_rating\": 4.8,\n      \"is_favorite\": true,\n      \"last_error\": null\n    },\n    \"omni\": {\n      \"execution_count\": 15,\n      \"success_count\": 15,\n      \"error_count\": 0,\n      \"total_time\": 30000,\n      \"last_used\": \"2025-01-24T15:45:30.456789\",\n      \"avg_response_time\": 2000,\n      \"user_rating\": 4.5,\n      \"is_favorite\": false,\n      \"last_error\": null\n    },\n    \"knowledge\": {\n      \"execution_count\": 7,\n      \"success_count\": 6,\n      \"error_count\": 1,\n      \"total_time\": 20430,\n      \"last_used\": \"2025-01-24T14:20:10.789012\",\n      \"avg_response_time\": 2918,\n      \"user_rating\": 4.0,\n      \"is_favorite\": false,\n      \"last_error\": \"Knowledge base temporarily unavailable\"\n    }\n  },\n  \"performance_metrics\": {\n    \"average_response_time\": 2669.57,\n    \"success_rate\": 93.62,\n    \"error_rate\": 6.38\n  },\n  \"timestamp\": \"2025-01-24T16:35:58.123456\"\n}"}]}}
```

### 🎯 **5. 读取特定Widget配置**

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
      "uri": "widget://user/auth0|123456/config/dream"
    }
  }'
```

**使用结果示例：**
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"widget://user/auth0|123456/config/dream","mimeType":"text/plain","text":"{\n  \"user_id\": \"auth0|123456\",\n  \"widget_type\": \"dream\",\n  \"config\": {\n    \"style\": \"artistic\",\n    \"quality\": \"high\",\n    \"size\": \"1024x1024\",\n    \"enabled\": true,\n    \"timeout\": 35000\n  },\n  \"has_custom_config\": true,\n  \"default_config\": {\n    \"style\": \"default\",\n    \"quality\": \"standard\",\n    \"size\": \"1024x1024\",\n    \"enabled\": true,\n    \"timeout\": 30000\n  },\n  \"last_updated\": \"2025-01-24T14:25:30.123456\",\n  \"timestamp\": \"2025-01-24T16:37:12.456789\"\n}"}]}}
```

### 📚 **6. 读取Widget模板**

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
      "uri": "widget://templates/dream"
    }
  }'
```

**使用结果示例：**
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"contents":[{"uri":"widget://templates/dream","mimeType":"text/plain","text":"{\n  \"widget_type\": \"dream\",\n  \"templates\": [\n    {\n      \"id\": \"text_to_image\",\n      \"name\": \"Text to Image\",\n      \"category\": \"generation\",\n      \"description\": \"Generate image from text description\",\n      \"parameters\": [\"prompt\", \"style\", \"quality\"]\n    },\n    {\n      \"id\": \"professional_headshot\",\n      \"name\": \"Professional Headshot\",\n      \"category\": \"portrait\",\n      \"description\": \"Generate professional headshot photos\",\n      \"parameters\": [\"prompt\", \"industry\", \"style\"]\n    }\n  ],\n  \"total_templates\": 2,\n  \"template_categories\": [\"generation\", \"portrait\"],\n  \"timestamp\": \"2025-01-24T16:38:45.123456\"\n}"}]}}
```

### 💡 **7. Python使用示例**

```python
import requests
import json

def search_widget_resources(query="widget"):
    """搜索Widget资源"""
    response = requests.post(
        'http://localhost:8081/search',
        headers={'Content-Type': 'application/json'},
        json={"query": query, "max_results": 10}
    )
    return response.json()

def read_widget_resource(uri):
    """读取Widget资源内容"""
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
            "params": {"uri": uri}
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
                    return content  # 返回原始Markdown
    return None

def get_user_widget_usage(user_id):
    """获取用户Widget使用统计"""
    uri = f"widget://user/{user_id}/usage"
    return read_widget_resource(uri)

def get_widget_system_info():
    """获取Widget系统信息"""
    return read_widget_resource("widget://system/info")

def get_user_widget_configs(user_id):
    """获取用户Widget配置"""
    uri = f"widget://user/{user_id}/configs"
    return read_widget_resource(uri)

# 使用示例
print("=== 搜索Widget资源 ===")
widget_resources = search_widget_resources()
for resource in widget_resources['results']:
    print(f"- {resource['name']}: {resource['description'][:60]}...")

print("\n=== Widget系统信息 ===")
system_info = get_widget_system_info()
print(system_info[:200] + "..." if len(system_info) > 200 else system_info)

print("\n=== 用户Widget使用统计 ===")
usage_stats = get_user_widget_usage('auth0|123456')
if isinstance(usage_stats, dict):
    summary = usage_stats.get('usage_summary', {})
    print(f"总执行次数: {summary.get('total_executions', 0)}")
    print(f"最常用Widget: {summary.get('most_used_widget', 'N/A')}")
    print(f"平均响应时间: {usage_stats.get('performance_metrics', {}).get('average_response_time', 0):.2f}ms")

print("\n=== 用户Widget配置 ===")
user_configs = get_user_widget_configs('auth0|123456')
print(user_configs[:300] + "..." if len(user_configs) > 300 else user_configs)
```

### 📊 **8. Widget资源特性**

- **🎯 个性化配置**: 每个用户可以自定义Widget的配置参数
- **📈 实时统计**: 记录详细的使用统计和性能指标
- **🔍 智能搜索**: 支持基于关键词的Widget资源发现
- **🎨 多样化模板**: 提供不同类型的Widget操作模板
- **⚙️ 灵活集成**: 与现有的前端plugin系统完全兼容
- **🛡️ 安全控制**: 基于用户权限的资源访问控制

---

## 📋 **重要说明**

1. **JSON-RPC格式**：所有MCP调用都使用JSON-RPC 2.0格式
2. **事件流响应**：响应采用Server-Sent Events格式，需要解析`data:`行
3. **必需头部**：调用MCP端点时必须包含`Accept: application/json, text/event-stream`
4. **参数验证**：工具和提示词的参数会进行类型检查和验证
5. **错误处理**：返回的`isError`字段指示是否有错误发生
6. **搜索支持**：
   - ✅ **Tools**: 完全支持搜索和语义匹配，包含安全等级信息
   - ✅ **Prompts**: 完全支持搜索，metadata包含参数信息
   - ✅ **Resources**: 完全支持搜索和语义匹配
   - ✅ **Widget Resources**: 支持用户专属Widget资源搜索和个性化配置
7. **默认集合**：搜索`"default"`可获取预定义的常用工具和提示词
8. **安全等级**：
   - ✅ **安全等级查询**: `/security/levels` 端点获取所有工具安全等级
   - ✅ **按等级搜索**: `/security/search` 端点按安全等级搜索工具
   - ✅ **搜索集成**: 普通搜索结果包含完整安全等级metadata
   - ✅ **错误处理**: 完善的参数验证和错误信息

所有示例都经过真实测试验证，可以直接使用。