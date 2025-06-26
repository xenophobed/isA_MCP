# 🎯 Event Sourcing MCP System

## 概述

这是一个基于Model Context Protocol (MCP)的事件驱动系统，实现了ambient agent架构，可以进行后台任务监控和主动通知。

## 🏗️ 架构设计

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User/Agent    │───▶│  MCP Server      │───▶│ Event Sourcing  │
│                 │    │  (Tools)         │    │ Service         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         ▲                                               │
         │               ┌─────────────────┐             │
         └───────────────│ Event Feedback  │◀────────────┘
                         │ Server (HTTP)   │
                         └─────────────────┘
```

### 核心组件

1. **Event Sourcing MCP Server** (`servers/event_sourcing_server.py`)
   - 提供后台任务管理工具
   - 独立运行监控服务
   - 支持多种任务类型

2. **Event Feedback Server** (`event_feedback_server.py`)
   - 接收事件反馈的HTTP服务器
   - 处理不同类型的事件
   - 模拟通知发送

3. **Event-Driven Client** (`client/v13_mcp_client.py`)
   - 增强的MCP客户端
   - 支持事件反馈处理
   - 集成LangGraph Agent

4. **现有MCP服务器** (`servers/v1.1_mcp_server.py`)
   - 扩展了Event Sourcing功能
   - 保持向后兼容

## 🔧 支持的事件类型

### 1. Web监控 (web_monitor)
监控网站内容变化，检测关键词

**配置示例:**
```json
{
  "urls": ["https://techcrunch.com", "https://news.ycombinator.com"],
  "keywords": ["artificial intelligence", "AI", "machine learning"],
  "check_interval_minutes": 30,
  "notification": {
    "method": "send_sms",
    "phone_number": "+1234567890"
  }
}
```

### 2. 定时任务 (schedule)
按时间表执行任务

**配置示例:**
```json
{
  "type": "daily",
  "hour": 8,
  "minute": 0,
  "action": "news_digest",
  "notification": {
    "method": "send_sms",
    "phone_number": "+1234567890"
  }
}
```

### 3. 新闻摘要 (news_digest)
生成每日新闻摘要

**配置示例:**
```json
{
  "news_urls": ["https://techcrunch.com", "https://bbc.com/news"],
  "hour": 8,
  "categories": ["technology", "business"],
  "notification": {
    "method": "send_sms",
    "phone_number": "+1234567890"
  }
}
```

### 4. 阈值监控 (threshold_watch)
监控指标并在达到阈值时报警

**配置示例:**
```json
{
  "metric": "bitcoin_price",
  "threshold": 50000,
  "check_interval_minutes": 15,
  "notification": {
    "method": "send_sms",
    "phone_number": "+1234567890"
  }
}
```

## 🛠️ 可用工具

### 后台任务管理
- `create_background_task`: 创建后台监控任务
- `list_background_tasks`: 列出所有后台任务
- `pause_background_task`: 暂停后台任务
- `resume_background_task`: 恢复后台任务
- `delete_background_task`: 删除后台任务
- `get_event_sourcing_status`: 获取事件溯源服务状态

### 现有工具集成
- `remember/forget/search_memories`: 记忆管理
- `get_weather`: 天气信息
- `send_sms`: SMS通知
- `scrape_webpage`: 网页抓取
- 安全和监控工具

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install fastapi uvicorn aiohttp langchain-openai langgraph pydantic
```

### 2. 启动演示
```bash
python start_event_sourcing_demo.py
```

### 3. 手动启动各组件

#### 启动Event Feedback Server
```bash
python event_feedback_server.py
```

#### 启动MCP服务器 (如果未运行)
```bash
# 启动现有的MCP服务器集群
docker-compose up -d
```

#### 运行Event-Driven客户端
```bash
python client/v13_mcp_client.py
```

## 🎮 使用示例

### 创建Web监控任务
```python
# 在v1.3客户端中输入:
"Set up a background task to monitor TechCrunch for new articles about artificial intelligence. Check every 30 minutes and send me SMS notifications when new AI content is found. My phone number is +1234567890."
```

### 设置每日新闻摘要
```python
# 在v1.3客户端中输入:
"Create a daily news digest task that summarizes the latest technology news from TechCrunch and Hacker News. Send me the digest every morning at 8 AM via SMS to +1234567890."
```

### 创建定时提醒
```python
# 在v1.3客户端中输入:
"Set up a daily reminder to check my project status every day at 9 AM. Send the reminder via SMS to +1234567890."
```

## 📊 监控和调试

### Event Feedback Server端点
- **主页**: http://localhost:8000/
- **事件列表**: http://localhost:8000/events
- **健康检查**: http://localhost:8000/health
- **特定事件类型**: http://localhost:8000/events/{event_type}

### 日志文件
- `event_sourcing.log`: Event Sourcing服务日志
- `event_feedback.log`: Event Feedback服务日志
- `mcp_server.log`: MCP服务器日志

## 🔄 工作流程

### 1. 任务创建流程
```
用户请求 → LangGraph Agent → create_background_task → Event Sourcing Service → 开始监控
```

### 2. 事件触发流程
```
监控检测到事件 → 生成EventFeedback → HTTP回调 → Event Feedback Server → 处理通知
```

### 3. 反馈处理流程
```
Event Feedback → Agent分析 → 决定是否通知 → 发送通知 (SMS/Email)
```

## 🎯 核心特性

### ✅ 已实现
- [x] 后台任务管理 (创建、暂停、恢复、删除)
- [x] Web内容监控
- [x] 定时任务执行
- [x] 新闻摘要生成
- [x] HTTP事件反馈机制
- [x] 模拟通知系统
- [x] Event-Driven客户端
- [x] 负载均衡支持
- [x] 安全和授权机制

### 🔄 计划中
- [ ] 真实的SMS/Email通知集成
- [ ] 高级网页抓取 (JavaScript支持)
- [ ] 机器学习驱动的内容分析
- [ ] 数据库持久化
- [ ] 分布式任务调度
- [ ] WebSocket实时通知

## 🔧 配置

### 环境变量
```bash
# OpenAI API (用于LangGraph Agent)
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=https://api.openai.com/v1

# Twilio (用于SMS通知)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_phone

# Event Feedback Server
EVENT_FEEDBACK_URL=http://localhost:8000/process_background_feedback
```

### MCP服务器配置
```yaml
# docker-compose.yml
services:
  mcp-server-1:
    ports:
      - "8001:8000"
  mcp-server-2:
    ports:
      - "8002:8000"
  mcp-server-3:
    ports:
      - "8003:8000"
  nginx:
    ports:
      - "80:80"
```

## 🧪 测试

### 运行演示场景
```bash
# 在v1.3客户端中输入:
demo
```

### 模拟事件反馈
```bash
# 在v1.3客户端中输入:
simulate
```

### 查看后台任务
```bash
# 在v1.3客户端中输入:
tasks
```

## 🐛 故障排除

### 常见问题

1. **连接失败**
   - 确保MCP服务器正在运行
   - 检查端口是否被占用
   - 验证nginx配置

2. **事件反馈不工作**
   - 确保Event Feedback Server在端口8000运行
   - 检查回调URL配置
   - 查看日志文件

3. **工具未发现**
   - 确保Event Sourcing MCP Server正在运行
   - 检查MCP协议兼容性
   - 验证工具注册

### 调试命令
```bash
# 检查端口占用
lsof -i :8000
lsof -i :8001

# 查看日志
tail -f event_sourcing.log
tail -f event_feedback.log

# 测试HTTP端点
curl http://localhost:8000/health
curl http://localhost:8000/events
```

## 📚 技术栈

- **Python 3.11+**
- **FastAPI**: HTTP服务器
- **MCP Python SDK**: Model Context Protocol
- **LangGraph**: Agent工作流
- **LangChain**: LLM集成
- **aiohttp**: 异步HTTP客户端
- **Pydantic**: 数据验证
- **asyncio**: 异步编程

## 🤝 贡献

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 📄 许可证

MIT License - 详见LICENSE文件

## 🎯 下一步

1. **真实集成**: 集成真实的通知服务
2. **扩展监控**: 添加更多监控类型
3. **性能优化**: 优化大规模任务处理
4. **UI界面**: 创建Web管理界面
5. **API文档**: 完善API文档

---

**注意**: 这是一个演示系统，生产环境使用需要额外的安全性和可靠性配置。 