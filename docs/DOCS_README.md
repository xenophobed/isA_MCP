# isA_MCP Documentation

欢迎使用isA_MCP的GitBook风格文档系统！

## 📚 文档结构

本文档系统按照GitBook的最佳实践组织，提供完整的API参考、用户指南和开发者文档。

### 📁 目录结构
```
docs/
├── README.md                    # 文档主页
├── SUMMARY.md                   # GitBook目录结构
├── book.json                    # GitBook配置
├── build.sh                     # 构建脚本
│
├── 📁 getting-started/          # 入门指南
│   ├── README.md                # 快速开始
│   ├── installation.md          # 安装指南
│   ├── quick-start.md           # 快速上手
│   └── configuration.md         # 配置说明
│
├── 📁 architecture/             # 系统架构
│   ├── README.md                # 架构概览
│   ├── core-components.md       # 核心组件
│   ├── service-layer.md         # 服务层
│   ├── data-layer.md            # 数据层
│   └── security-model.md        # 安全模型
│
├── 📁 services/                 # 服务文档
│   ├── data-analytics/          # 数据分析服务
│   ├── graph-analytics/         # 图分析服务
│   ├── web-services/            # Web服务
│   ├── rag/                     # RAG文档服务
│   ├── ecommerce/               # 电商集成
│   ├── memory/                  # 内存系统
│   └── image-generation/        # 图像生成
│
├── 📁 user-guide/               # 用户指南
│   ├── README.md                # 用户指南概览
│   ├── basic-usage.md           # 基础用法
│   ├── advanced-features.md     # 高级功能
│   ├── best-practices.md        # 最佳实践
│   └── troubleshooting.md       # 故障排除
│
├── 📁 api/                      # API参考
│   ├── README.md                # API概览
│   ├── authentication.md        # 认证说明
│   ├── tools.md                 # 工具端点
│   ├── services.md              # 服务API
│   ├── configuration.md         # 配置参考
│   ├── environment.md           # 环境变量
│   └── error-handling.md        # 错误处理
│
├── 📁 deployment/               # 部署指南
│   ├── README.md                # 部署概览
│   ├── local.md                 # 本地部署
│   ├── docker.md                # Docker部署
│   ├── railway.md               # Railway云部署
│   ├── production.md            # 生产环境
│   ├── monitoring.md            # 监控维护
│   └── performance.md           # 性能优化
│
├── 📁 development/              # 开发者指南
│   ├── README.md                # 开发概览
│   ├── project-structure.md     # 项目结构
│   ├── code-standards.md        # 代码规范
│   ├── testing.md               # 测试策略
│   ├── contributing.md          # 贡献指南
│   ├── extensions.md            # 扩展开发
│   └── service-development.md   # 服务开发
│
└── 📁 resources/                # 资源文档
    ├── migration.md             # 迁移指南
    ├── faq.md                   # 常见问题
    ├── changelog.md             # 更新日志
    └── license.md               # 许可证
```

## 🚀 快速开始

### 1. 浏览在线文档
直接打开 `docs/README.md` 开始浏览文档。

### 2. 本地构建GitBook
```bash
# 安装GitBook CLI
npm install -g gitbook-cli

# 进入文档目录
cd docs/

# 安装插件
gitbook install

# 本地服务
gitbook serve

# 访问 http://localhost:4000
```

### 3. 使用构建脚本
```bash
# 运行构建脚本
./docs/build.sh

# 这会生成：
# - HTML文档：docs/_book/
# - PDF文档：docs/isA_MCP_Documentation.pdf
```

## 📖 文档特性

### ✨ 包含内容
- **📋 完整的API参考** - 所有35+工具的详细说明
- **🎯 用户指南** - 从基础到高级的使用教程
- **🏗️ 架构文档** - 系统设计和组件说明
- **🔧 开发者指南** - 扩展开发和贡献指南
- **🚀 部署指南** - 多种部署选项和最佳实践
- **🔍 故障排除** - 常见问题和解决方案

### 🎨 GitBook功能
- **📱 响应式设计** - 支持桌面和移动设备
- **🔍 全文搜索** - 快速查找内容
- **📊 代码高亮** - 支持多种编程语言
- **📈 Mermaid图表** - 架构图和流程图
- **🔗 交叉引用** - 文档间的智能链接
- **📑 目录导航** - 层级化的导航结构
- **💾 PDF导出** - 完整文档的PDF版本

## 🌟 主要亮点

### 🧠 AI驱动的智能系统
- **智能工具选择** - 自然语言自动选择合适的工具
- **5步数据分析流程** - 从元数据到SQL生成的完整流水线
- **图谱分析** - 实体提取、关系映射和Neo4j集成
- **高级网页抓取** - 反检测和JavaScript执行

### 🏢 企业级特性
- **多级安全认证** - LOW、MEDIUM、HIGH安全等级
- **成本追踪** - 详细的AI API调用计费信息
- **审计日志** - 完整的操作记录和合规性
- **负载均衡** - 生产级的Docker集群部署

### 📊 服务覆盖
- **数据分析** - PostgreSQL、MySQL、SQL Server集成
- **文档处理** - PDF、DOCX、PPT等格式的RAG问答
- **电商集成** - 完整的Shopify购物车和结账流程
- **图像生成** - AI驱动的图像创建和转换
- **内存管理** - 持久化信息存储和智能检索

## 🔧 文档维护

### 更新文档
1. 编辑对应的Markdown文件
2. 运行 `./build.sh` 重新构建
3. 提交更改到版本控制

### 添加新章节
1. 在对应目录创建新的.md文件
2. 更新 `SUMMARY.md` 添加新章节
3. 重新构建文档

### 配置调整
- 编辑 `book.json` 调整GitBook配置
- 修改 `SUMMARY.md` 调整目录结构
- 更新 `build.sh` 调整构建流程

## 📚 使用示例

### 新用户入门
1. 从 [入门指南](getting-started/README.md) 开始
2. 按照 [安装指南](getting-started/installation.md) 配置环境
3. 尝试 [快速上手](getting-started/quick-start.md) 的示例

### 开发者
1. 阅读 [系统架构](architecture/README.md) 了解设计
2. 查看 [项目结构](development/project-structure.md) 熟悉代码
3. 参考 [开发指南](development/README.md) 开始贡献

### API使用者
1. 查看 [API概览](api/README.md) 了解可用功能
2. 参考 [工具端点](api/tools.md) 了解具体调用方式
3. 配置 [认证授权](api/authentication.md) 确保安全访问

## 🤝 贡献文档

我们欢迎对文档的改进！请参考 [贡献指南](development/contributing.md) 了解如何：

- 📝 改进现有文档
- ➕ 添加新的章节
- 🐛 修复文档错误
- 🌐 翻译文档内容

## 📞 获取帮助

- **📚 文档问题** - 在GitHub Issues中提出
- **🔧 技术支持** - 参考 [故障排除](user-guide/troubleshooting.md)
- **💡 功能建议** - 在GitHub Discussions中讨论

---

**🎯 开始探索isA_MCP的强大功能！** 从 [README.md](README.md) 开始您的旅程。