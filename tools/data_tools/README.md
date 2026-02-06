# Data Tools

数据分析工具包 - 通过 HTTP API 连接外部数据分析服务

## 概述

`data_tools` 包提供了一组 MCP 工具，用于与外部数据分析微服务进行交互。这些工具通过 HTTP API 调用远程服务，支持 SSE（Server-Sent Events）进行实时进度跟踪。

目前包含：
- **Digital Analytics Tools**: 基于 RAG 的知识管理，支持文本、PDF 和图像内容

## 架构

```
tools/data_tools/
├── __init__.py              # 包导出
├── digital_client.py        # Digital Analytics Service HTTP 客户端
├── digital_tools.py         # Digital Analytics MCP 工具包装
├── README.md               # 本文档
└── tests/
    └── test_digital_tools.sh # 测试脚本
```

## Digital Analytics Tools

### 功能特性

Digital Analytics Service 提供强大的 RAG（Retrieval-Augmented Generation）能力：

1. **多模态内容处理**
   - ✅ 文本内容存储和检索
   - ✅ PDF 文档自动解析和提取
   - ✅ 图像视觉分析和描述生成

2. **七种 RAG 模式**
   - `simple`: 基础向量检索（最快）
   - `crag`: 纠错检索增强（高准确度）
   - `self_rag`: 自我反思检索（复杂推理）
   - `hyde`: 假设文档嵌入（模糊查询）
   - `raptor`: 递归摘要树（长文档）
   - `graph_rag`: 图结构检索（关系型知识）
   - `rag_fusion`: 多查询融合（高召回率）

### 可用工具

#### 1. digital_store_text
存储文本内容到知识库

```python
digital_store_text(
    user_id="alice",
    content="Docker is a containerization platform...",
    mode="simple",
    collection_name="tech_docs",
    metadata={"category": "devops"}
)
```

#### 2. digital_store_pdf
存储 PDF 文档并自动提取文本

```python
digital_store_pdf(
    user_id="researcher",
    pdf_url="https://arxiv.org/pdf/1706.03762.pdf",
    mode="raptor",
    collection_name="papers",
    metadata={"title": "Attention Is All You Need"}
)
```

#### 3. digital_store_image
存储图像并进行视觉分析

```python
digital_store_image(
    user_id="designer",
    image_url="https://example.com/photo.jpg",
    mode="simple",
    collection_name="inspiration"
)
```

#### 4. digital_search
在知识库中搜索相关内容

```python
digital_search(
    user_id="alice",
    query="What is Docker?",
    mode="rag_fusion",
    collection_name="tech_docs",
    top_k=5
)
```

#### 5. digital_response
基于知识库生成 AI 回答

```python
digital_response(
    user_id="alice",
    query="Explain the differences between Docker and Kubernetes",
    mode="simple",
    collection_name="tech_docs",
    use_citations=True
)
```

#### 6. digital_service_health_check
检查服务健康状态

```python
digital_service_health_check()
```

### 配置

#### 环境变量

Digital Analytics Service 客户端支持以下环境变量配置：

```bash
# 服务名称（用于 Consul 服务发现）
DATA_SERVICE_NAME=data_service

# Consul 配置
CONSUL_HOST=localhost
CONSUL_PORT=8500

# 服务连接配置
DATA_FALLBACK_HOST=localhost    # 后备主机
DATA_FALLBACK_PORT=8083         # 后备端口
DATA_API_TIMEOUT=300            # API 超时（秒）
DATA_MAX_RETRIES=3              # 最大重试次数
```

#### 配置优先级

1. **Consul 服务发现**: 首先尝试通过 Consul 发现服务
2. **环境变量**: 使用环境变量配置的后备地址
3. **默认值**: 使用内置默认配置

### 使用示例

#### 完整工作流程

```python
# 1. 存储文档
await digital_store_pdf(
    user_id="alice",
    pdf_url="https://arxiv.org/pdf/1706.03762.pdf",
    mode="raptor",
    collection_name="ml_papers"
)

# 2. 搜索相关内容
results = await digital_search(
    user_id="alice",
    query="transformer architecture",
    mode="simple",
    collection_name="ml_papers",
    top_k=3
)

# 3. 生成回答
response = await digital_response(
    user_id="alice",
    query="Explain the self-attention mechanism",
    mode="simple",
    collection_name="ml_papers",
    use_citations=True
)
```

#### 批量存储

```python
# 存储多个文档到同一个集合
documents = [
    "Docker documentation content...",
    "Kubernetes guide content...",
    "CI/CD best practices..."
]

for doc in documents:
    await digital_store_text(
        user_id="alice",
        content=doc,
        mode="simple",
        collection_name="devops_docs"
    )
```

## 客户端使用

### 直接使用客户端

如果需要直接使用 HTTP 客户端（不通过 MCP 工具）：

```python
from tools.data_tools import get_digital_client

# 获取客户端实例
client = get_digital_client()

# 存储内容（SSE 流式响应）
async for message in client.store(
    user_id="alice",
    content="Some content",
    content_type="text",
    mode="simple"
):
    if message.get('type') == 'progress':
        print(f"Progress: {message.get('message')}")
    elif message.get('type') == 'result':
        print(f"Result: {message.get('data')}")

# 搜索内容
result = await client.search(
    user_id="alice",
    query="search query",
    mode="simple",
    top_k=5
)

# 生成响应（SSE 流式响应）
async for message in client.generate_response(
    user_id="alice",
    query="question",
    mode="simple",
    options={"use_citations": True}
):
    if message.get('type') == 'progress':
        print(f"Progress: {message.get('message')}")
    elif message.get('type') == 'result':
        print(f"Response: {message.get('data')}")
```

### 自定义配置

```python
from tools.data_tools import DigitalServiceClient, DigitalServiceConfig

# 创建自定义配置
config = DigitalServiceConfig(
    service_name="my_data_service",
    fallback_host="data-service.example.com",
    fallback_port=9000,
    api_timeout=600
)

# 使用自定义配置创建客户端
client = DigitalServiceClient(config)
```

## 自动注册

工具会被自动发现系统自动注册：

1. 系统扫描 `tools/data_tools/` 目录
2. 查找 `digital_tools.py` 文件
3. 导入并调用 `register_digital_tools(mcp)` 函数
4. 所有工具自动注册到 MCP 服务器

无需手动注册，只需确保：
- `digital_tools.py` 存在于正确位置
- `register_digital_tools()` 函数已定义
- `__init__.py` 正确导出函数

## 最佳实践

### 1. 选择合适的 RAG 模式

| 场景 | 推荐模式 | 原因 |
|------|----------|------|
| 快速问答 | `simple` | 响应速度快 |
| 需要高准确度 | `crag` | 有纠错机制 |
| 模糊查询 | `hyde` | 生成假设文档提升匹配 |
| 提升召回率 | `rag_fusion` | 多查询融合 |
| 长文档理解 | `raptor` | 递归摘要 |
| 关系型知识 | `graph_rag` | 图结构检索 |

### 2. Collection 管理

建议按内容类型和用途组织 collection：

```
tech_docs/          # 技术文档
  - docker_guides
  - kubernetes_docs
  - api_references

research_papers/    # 研究论文
  - ml_papers
  - nlp_papers

visual_library/     # 图像库
  - product_photos
  - inspiration
```

### 3. 性能优化

- **批量存储**: 使用相同的 collection_name 批量存储相关内容
- **top_k 设置**: 根据需求调整，通常 3-5 个结果即可
- **异步处理**: API 支持 SSE 流式响应，实时展示进度

### 4. 错误处理

所有工具返回标准格式的 JSON 响应：

```json
{
  "status": "success|error",
  "action": "digital_store_text",
  "data": {
    "user_id": "alice",
    "success": true,
    "message": "Stored 5 chunks",
    "progress_history": [...]
  },
  "error_message": null
}
```

## 测试

运行测试脚本验证工具注册：

```bash
./tools/data_tools/tests/test_digital_tools.sh
```

测试内容包括：
- 文件存在性检查
- 模块导入验证
- 工具注册验证
- 文档字符串检查
- 客户端配置验证

## 故障排除

### 服务连接失败

如果工具无法连接到服务：

1. 检查服务是否运行
2. 验证环境变量配置
3. 确认 Consul 服务发现是否可用
4. 检查网络连接和防火墙设置

### 导入错误

如果遇到导入错误：

```python
# 确保项目根目录在 Python path 中
import sys
sys.path.insert(0, '/path/to/isA_MCP')

from tools.data_tools import register_digital_tools
```

### 安全管理器未初始化

工具需要在完整的 MCP 服务器环境中运行。如果直接导入测试，需要先初始化安全管理器：

```python
from core.security import initialize_security
initialize_security()
```

## 依赖服务

Digital Analytics Service 依赖以下服务：

- **ISA Model Service**: LLM 和 Embedding 生成
- **Qdrant**: 向量数据库
- **Neo4j**: 图数据库（Graph RAG）
- **MCP Tools**: PDF 和图像处理工具

确保这些服务正在运行并可访问。

## 相关资源

- 源代码: `/Users/xenodennis/Documents/Fun/isA_Data`
- API 文档: 参考 `/Users/xenodennis/Documents/Fun/isA_Data/docs/how_to_digital.md`
- 服务端点: `http://localhost:8083/api/v1/digital`

## 未来计划

- [ ] 添加更多数据分析工具（data_tools）
- [ ] 支持流式内容上传
- [ ] 批量操作 API
- [ ] 增强的元数据管理
- [ ] 内容版本控制
