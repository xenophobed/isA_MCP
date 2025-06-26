# 🏗️ isA_MCP Smart Server Architecture

## 📁 项目结构

```
isA_MCP/
├── 🚀 smart_server.py               # 智能MCP服务器 (AI工具选择)
├── 🌐 server.py                     # 传统MCP服务器
├── 📋 requirements.txt              # Python依赖
├── 📋 pyproject.toml                # 项目配置
├── 🐳 docker-compose.smart.yml      # 智能服务器Docker集群
├── 🐳 docker-compose.yml            # 传统服务器Docker配置
├── 🐳 Dockerfile.smart              # 智能服务器Docker镜像
├── 🧪 test_docker_cluster.py        # Docker集群测试套件
├── 🎬 start_smart_cluster.sh        # 智能集群启动脚本
│
├── 📁 deployment/                   # 部署配置
│   ├── 🔧 nginx.smart.conf         # 智能服务器负载均衡器
│   ├── 🔧 nginx.conf               # 传统服务器负载均衡器
│   ├── 📊 prometheus.yml           # 监控配置
│   └── 🔧 mcp_config.json          # MCP配置
│
├── 📁 core/                         # 核心模块
│   ├── 🔧 config.py                # 配置管理
│   ├── 🔒 security.py              # 安全管理
│   ├── 🔒 auth.py                  # 认证授权
│   ├── 📊 monitoring.py            # 监控管理
│   ├── 📝 logging.py               # 日志管理
│   ├── ⚠️ exception.py             # 异常处理
│   └── 🛠️ utils.py                 # 工具函数
│
├── 📁 tools/                        # MCP工具集
│   ├── 🧠 memory_tools.py          # 记忆管理工具
│   ├── 🌤️ weather_tools.py         # 天气工具
│   ├── 👑 admin_tools.py           # 管理员工具
│   ├── 💬 client_interaction_tools.py # 客户端交互工具
│   ├── 🔄 event_sourcing_tools.py  # 事件溯源工具
│   ├── 🖼️ image_gen_tools.py       # 图像生成工具
│   ├── 📱 twillo_tools.py          # Twilio通信工具
│   ├── 🕷️ web_scrape_tools.py      # 网页抓取工具 (新增)
│   ├── 🤖 smart_tools.py           # AI工具选择器
│   ├── 🎯 tool_selector.py         # 工具选择逻辑
│   │
│   ├── 📁 services/                # 业务服务层
│   │   ├── 🔄 event_sourcing_services.py # 事件溯源服务
│   │   └── 🛒 shopify_client.py    # Shopify客户端服务
│   │
│   └── 📁 apps/                    # 第三方应用集成
│       └── 📁 shopify/             # Shopify集成
│           ├── 🛒 shopify_client.py
│           └── 🛒 shopify_tools.py
│
├── 📁 resources/                    # MCP资源
│   ├── 🧠 memory_resources.py      # 记忆资源
│   ├── 📊 monitoring_resources.py  # 监控资源
│   ├── 🔄 event_sourcing_resources.py # 事件溯源资源
│   └── 🗄️ database_init.py         # 数据库初始化
│
├── 📁 prompts/                      # MCP提示词
│   └── 💭 system_prompts.py        # 系统提示词
│
├── 📁 client/                       # MCP客户端
│   ├── 🌐 mcp_http_client.py       # HTTP客户端
│   └── 🔄 v0.1_mcp_client.py       # 简化MCP客户端
│
├── 📁 tests/                        # 测试和演示
│   ├── 🧪 test_isa_model.py        # isa_model测试
│   └── 📁 mcp_test/                # MCP测试套件
│       ├── 🤖 simple_smart_tools.py
│       ├── 🎯 simple_tool_selector.py
│       ├── 🌐 simple_mcp_client.py
│       └── 🚀 autonomous_mcp_client.py
│
├── 📁 docs/                         # 文档
│   ├── 📖 PROJECT_STRUCTURE.md     # 项目结构 (本文档)
│   ├── 🚀 DEPLOYMENT_GUIDE.md      # 部署指南
│   ├── 🎯 EVENT_SOURCING_README.md # 事件溯源文档
│   ├── 🔄 REFACTORING_SUMMARY.md   # 重构总结
│   └── 🛒 SHOPIFY_INTEGRATION_STATUS.md # Shopify集成状态
│
├── 📁 logs/                         # 日志文件
├── 📁 scripts/                      # 管理脚本
│   ├── manage-mcp.sh
│   └── start-mcp-servers.sh
└── 📁 ssl/                          # SSL证书
```

## 🎯 核心组件说明

### 1. 智能MCP服务器 (`smart_server.py`)
- **作用**: AI驱动的智能工具选择MCP服务器
- **功能**: 
  - 🤖 基于用户请求智能推荐最相关的工具
  - 🔧 集成所有工具、资源、提示词
  - 📊 提供分析和统计端点
  - 🔍 支持嵌入向量相似度搜索
  - 📈 监控和性能指标

### 2. 传统MCP服务器 (`server.py`)
- **作用**: 标准MCP服务器实现
- **功能**: 
  - 📋 提供所有可用工具
  - 🔄 支持多端口部署
  - ⚖️ 负载均衡支持
  - 🔒 安全和监控集成

### 3. Docker集群架构

#### 智能服务器集群 (`docker-compose.smart.yml`)
```
┌─────────────────────────────────────────────────────────────┐
│                    Nginx Load Balancer                      │
│                    (Port 8081)                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   ┌────▼───┐    ┌────▼───┐    ┌────▼───┐
   │Smart-1 │    │Smart-2 │    │Smart-3 │
   │Port    │    │Port    │    │Port    │
   │4321    │    │4322    │    │4323    │
   └────────┘    └────────┘    └────────┘
```

#### 功能特性
- **AI工具选择**: 自动推荐最相关的工具
- **负载均衡**: 智能请求分发
- **健康检查**: 自动故障检测和恢复
- **实时监控**: 性能指标和统计
- **Web抓取**: 现代网页抓取支持

### 4. 工具生态系统

#### 🤖 AI驱动工具选择
```python
# 智能工具推荐示例
request = "scrape website for product information"
recommended_tools = [
    "scrape_webpage",      # 网页抓取
    "get_product_details", # Shopify产品详情
    "get_scraper_status"   # 抓取状态
]
```

#### 🛠️ 完整工具集
- **🕷️ Web抓取工具** (6个): 现代反检测网页抓取
- **🧠 记忆管理** (4个): 持久化信息存储
- **🖼️ 图像生成** (4个): AI图像创建和处理
- **🛒 Shopify集成** (8个): 电商功能完整支持
- **👑 管理工具** (4个): 系统管理和监控
- **💬 客户交互** (4个): 用户沟通和授权
- **🔄 事件溯源** (6个): 后台任务管理
- **🌤️ 天气服务** (1个): 全球天气数据

## 🚀 使用方式

### 启动智能服务器集群
```bash
# 一键启动完整集群
chmod +x start_smart_cluster.sh
./start_smart_cluster.sh

# 手动启动
docker-compose -f docker-compose.smart.yml up -d
```

### 测试集群功能
```bash
# 运行完整测试套件
python test_docker_cluster.py
```

### 访问端点
- **🌐 负载均衡器**: http://localhost:8081
- **🔍 智能分析**: http://localhost:8081/analyze
- **📊 服务器统计**: http://localhost:8081/stats
- **🏥 健康检查**: http://localhost:8081/health
- **📡 MCP协议**: http://localhost:8081/mcp/

### 直接访问服务器
- **服务器1**: http://localhost:4321
- **服务器2**: http://localhost:4322
- **服务器3**: http://localhost:4323

## 🎯 AI工具选择流程

```
用户请求 → 文本嵌入 → 相似度计算 → 工具排序 → 推荐返回
    ↓           ↓          ↓         ↓        ↓
"scrape web" → vector → similarity → rank → [scrape_webpage, ...]
```

## 📊 监控和统计

### 健康检查
每个服务器实例提供：
- ✅ 服务状态
- 🔧 已加载工具列表
- 🤖 AI选择器状态
- 📊 服务器模式

### 性能指标
- 📈 请求处理统计
- ⏱️ 响应时间指标
- 🔧 工具使用频率
- 🚦 错误率监控

## 🔒 安全特性

- **分级授权**: LOW, MEDIUM, HIGH安全级别
- **速率限制**: 防止滥用的请求限制
- **审计日志**: 完整的操作追踪
- **用户权限**: 基于角色的访问控制
- **SSL/TLS**: 加密通信支持

## 🐳 部署选项

### 开发环境
```bash
# 单服务器开发
python smart_server.py --port 4321

# 集群开发
./start_smart_cluster.sh
```

### 生产环境
```bash
# 使用Docker Compose
docker-compose -f docker-compose.smart.yml up -d

# 使用Kubernetes (计划中)
kubectl apply -f k8s/smart-mcp-cluster.yaml
```

## 🔄 与传统服务器对比

| 特性 | 智能服务器 | 传统服务器 |
|------|-----------|-----------|
| 工具选择 | 🤖 AI驱动智能推荐 | 📋 列出所有工具 |
| 部署端口 | 4321-4323 | 8001-8003 |
| 负载均衡器 | 8081 | 80 |
| Web抓取 | ✅ 完整支持 | ❌ 无 |
| 分析端点 | ✅ /analyze, /stats | ❌ 无 |
| Docker配置 | docker-compose.smart.yml | docker-compose.yml |

## 🛠️ 开发规范

1. **工具开发**: 在 `tools/` 下创建，添加Keywords和Category元数据
2. **服务开发**: 在 `tools/services/` 下创建业务逻辑
3. **资源开发**: 在 `resources/` 下创建，使用 `@mcp.resource()` 装饰器
4. **提示词**: 在 `prompts/` 下创建，使用 `@mcp.prompt()` 装饰器
5. **AI集成**: 为工具添加Keywords和Category以支持智能选择

## 📈 性能优化

- **工具缓存**: 智能工具选择结果缓存
- **向量缓存**: 嵌入向量计算缓存
- **连接池**: 数据库和API连接复用
- **负载均衡**: 请求智能分发
- **健康检查**: 自动故障恢复

---

**注意**: 这是新一代智能MCP服务器架构，结合了传统MCP协议的可靠性和AI驱动的智能化。适用于需要智能工具推荐和现代Web功能的应用场景。