# 🏗️ isA_MCP 项目结构

## 📁 目录结构

```
isA_MCP/
├── 🚀 server.py                    # 主MCP服务器 (多端口部署)
├── 📋 pyproject.toml               # 项目配置和依赖
├── 📋 requirements.txt             # Python依赖
├── 🐳 docker-compose.yml           # Docker部署配置
├── 🔧 nginx.conf                   # 负载均衡器配置
├── 📋 config.yaml                  # 应用配置
│
├── 📁 core/                        # 核心模块
│   ├── 🔧 config.py               # 配置管理
│   ├── 🔒 security.py             # 安全管理
│   ├── 📊 monitoring.py           # 监控管理
│   ├── 📝 logging.py              # 日志管理
│   ├── ⚠️ exception.py            # 异常处理
│   └── 🛠️ utils.py                # 工具函数
│
├── 📁 tools/                       # MCP工具集
│   ├── 🧠 memory_tools.py         # 记忆管理工具
│   ├── 🌤️ weather_tools.py        # 天气工具
│   ├── 👑 admin_tools.py          # 管理员工具
│   ├── 💬 client_interaction_tools.py # 客户端交互工具
│   ├── 🔄 event_sourcing_tools.py # 事件溯源工具
│   ├── 🖼️ image_gen_tools.py      # 图像生成工具
│   ├── 📱 twillo_tools.py         # Twilio短信工具
│   ├── 🕷️ web_scrape_tools.py     # 网页抓取工具
│   │
│   ├── 📁 services/               # 业务服务层
│   │   └── 🔄 event_sourcing_services.py # 事件溯源服务
│   │
│   └── 📁 apps/                   # 第三方应用集成
│       └── 📁 shopify/            # Shopify集成
│           ├── 🛒 shopify_client.py
│           └── 🛒 shopify_tools.py
│
├── 📁 resources/                   # MCP资源
│   ├── 🧠 memory_resources.py     # 记忆资源
│   ├── 📊 monitoring_resources.py # 监控资源
│   ├── 🔄 event_sourcing_resources.py # 事件溯源资源
│   └── 🗄️ database_init.py        # 数据库初始化
│
├── 📁 prompts/                     # MCP提示词
│   └── 💭 system_prompts.py       # 系统提示词
│
├── 📁 servers/                     # MCP服务器实现
│   ├── 🔄 event_sourcing_server.py # 事件溯源服务器
│   ├── 📡 event_feedback_server.py # 事件回调服务器
│   ├── 🌐 v1.1_mcp_server.py      # MCP服务器v1.1
│   └── 🏗️ dynamic_mcp_server.py   # 动态MCP服务器
│
├── 📁 client/                      # MCP客户端
│   ├── 🌐 mcp_http_client.py      # HTTP客户端
│   ├── 🔄 v1.3_mcp_client.py      # 事件驱动客户端
│   └── 🚀 dynamic_mcp_client.py   # 动态客户端
│
├── 📁 tests/                       # 测试和演示
│   ├── 🧪 test_event_sourcing.py  # 事件溯源测试
│   └── 📁 demos/                  # 演示脚本
│       ├── 🎬 demo_event_sourcing.py
│       └── 🚀 start_event_sourcing_demo.py
│
├── 📁 docs/                        # 文档
│   ├── 📖 EVENT_SOURCING_README.md # 事件溯源文档
│   └── 🚀 DEPLOYMENT_GUIDE.md     # 部署指南
│
├── 📁 logs/                        # 日志文件
├── 📁 tmp/                         # 临时文件
├── 📁 bin/                         # 可执行脚本
├── 📁 k8s/                         # Kubernetes配置
└── 📁 ssl/                         # SSL证书
```

## 🎯 核心组件说明

### 1. 主服务器 (`server.py`)
- **作用**: 统一的MCP服务器入口点
- **功能**: 
  - 集成所有工具、资源、提示词
  - 支持多端口部署
  - 负载均衡支持
  - 安全和监控集成

### 2. Event Sourcing 系统
- **工具层**: `tools/event_sourcing_tools.py` - MCP工具接口
- **服务层**: `tools/services/event_sourcing_services.py` - 核心业务逻辑
- **资源层**: `resources/event_sourcing_resources.py` - 数据资源
- **回调服务**: `servers/event_feedback_server.py` - 事件回调处理

### 3. 架构模式

```
用户/Agent → MCP工具 → 事件服务 → 后台监控
     ↑                              ↓
事件回调服务 ←─────────────────────────┘
     ↓
LangGraph Agent → LLM处理 → MCP工具调用(Twilio等)
```

## 🔧 使用方式

### 启动主服务器
```bash
# 单端口
python server.py --port 8001

# 多端口部署 (配合nginx)
python server.py --port 8001 &
python server.py --port 8002 &
python server.py --port 8003 &
```

### 启动事件回调服务
```bash
python servers/event_feedback_server.py
```

### 启动负载均衡器
```bash
docker-compose up nginx
```

## 📊 MCP资源说明

### Event Sourcing资源
- `event://tasks` - 所有后台任务
- `event://status` - 服务状态
- `event://tasks/active` - 活跃任务
- `event://tasks/by-type/{type}` - 按类型筛选任务
- `event://config/examples` - 配置示例

### 使用示例
```python
# 客户端读取资源
tasks = await client.read_resource("event://tasks")
status = await client.read_resource("event://status")
```

## 🛠️ 开发规范

1. **工具开发**: 在 `tools/` 下创建，使用 `register_xxx_tools(mcp)` 模式
2. **服务开发**: 在 `tools/services/` 下创建业务逻辑
3. **资源开发**: 在 `resources/` 下创建，使用 `@mcp.resource()` 装饰器
4. **提示词**: 在 `prompts/` 下创建，使用 `@mcp.prompt()` 装饰器

## 🔒 安全特性

- 分级授权 (LOW, MEDIUM, HIGH)
- 速率限制
- 审计日志
- 用户权限管理

## 📈 监控功能

- 性能指标收集
- 健康检查端点
- 实时日志记录
- 事件追踪 