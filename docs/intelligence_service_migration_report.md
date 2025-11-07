# Intelligence Service → ISA Model 迁移评估报告

**生成时间**: 2025-01-XX  
**状态**: 部分迁移中

---

## 📊 总体概览

### 迁移进度
- ✅ **已迁移**: 7 个文件
- ⚠️ **仍在使用**: 28 个非测试/文档文件
- 📝 **测试/文档**: 多个文件（暂不迁移）

### ISA Model 架构
ISA Model 通过统一客户端 `AsyncISAModel` 提供 OpenAI 兼容 API：
- `client.chat.completions.create()` - 文本生成
- `client.embeddings.create()` - 向量嵌入
- `client.vision.completions.create()` - 视觉分析
- `client.images.generate()` - 图像生成

**入口**: `core/clients/model_client.py` → `get_model_client()` 或 `get_isa_client()`

---

## ✅ 已迁移到 ISA Model 的文件

### 1. 核心基础设施
- ✅ **`core/clients/model_client.py`**
  - 提供统一的 `AsyncISAModel` 客户端
  - 支持单例模式和配置管理

### 2. Data Analytics Service（RAG 服务）
- ✅ **`tools/services/data_analytics_service/services/digital_service/base/base_rag_service.py`**
  - Base RAG 服务已迁移，使用 `AsyncISAModel` 初始化
  - 所有子类继承此基础架构
  
根据文档已迁移的 RAG 模式：
- ✅ Simple RAG
- ✅ CRAG (Corrective RAG)
- ✅ Self-RAG
- ✅ RAG Fusion
- ✅ HyDE RAG
- ✅ RAPTOR RAG
- ✅ Graph RAG

### 3. Web Services
- ✅ **`tools/services/web_services/services/web_automation_service.py`**
  - 使用 ISA Model 进行图像分析
  
- ✅ **`tools/services/web_services/services/web_search_service.py`**
  - 已迁移到 ISA Model
  
- ✅ **`tools/services/web_services/strategies/detection/vision_analyzer.py`**
  - 视觉检测已迁移

---

## ⚠️ 仍在使用 `intelligence_service` 的文件

### 完整文件清单（28 个非测试文件）

1. `services/sync_service/sync_service.py`
2. `services/search_service/search_service.py`
3. `tools/plan_tools/plan_tools.py`
4. `tools/services/data_analytics_service/processors/file_processors/ai_enhanced_processor.py`
5. `tools/services/data_analytics_service/processors/file_processors/video_processor.py`
6. `tools/services/data_analytics_service/services/data_service/analytics/data_eda.py`
7. `tools/services/data_analytics_service/services/data_service/management/metadata/metadata_embedding.py`
8. `tools/services/data_analytics_service/services/data_service/management/metadata/semantic_enricher.py`
9. `tools/services/data_analytics_service/services/data_service/search/sql_generator.py`
10. `tools/services/data_analytics_service/services/data_service/transformation/lang_extractor.py`
11. `tools/services/data_analytics_service/services/digital_service/enhanced_digital_service.py`
12. `tools/services/data_analytics_service/services/digital_service/evaluation/diagnostic_service.py`
13. `tools/services/data_analytics_service/services/digital_service/evaluation/metrics_service.py`
14. `tools/services/data_analytics_service/services/digital_service/patterns/custom_rag_service.py`
15. `tools/services/data_analytics_service/services/digital_service/patterns/graph_rag/attribute_extractor.py`
16. `tools/services/data_analytics_service/services/digital_service/patterns/graph_rag/core/strategies.py`
17. `tools/services/data_analytics_service/services/digital_service/patterns/graph_rag/entity_extractor.py`
18. `tools/services/data_analytics_service/services/digital_service/patterns/graph_rag/graph_constructor.py`
19. `tools/services/data_analytics_service/services/digital_service/patterns/graph_rag/knowledge_retriever.py`
20. `tools/services/data_analytics_service/services/digital_service/patterns/graph_rag/neo4j_store.py`
21. `tools/services/data_analytics_service/services/digital_service/patterns/graph_rag/relation_extractor.py`
22. `tools/services/data_analytics_service/services/digital_service/patterns/self_rag_service.py`
23. `tools/services/data_analytics_service/services/digital_service/pdf_extract_service.py`
24. `tools/services/data_analytics_service/services/digital_service/rag_service.py`
25. `tools/services/web_services/services/web_crawl_service.py`

---

### A. Core Services（2 个文件）

#### 1. **`services/sync_service/sync_service.py`** ⭐ 高优先级
```python
# 第 40 行
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator

# 使用位置：第 47 行
self.embedding_gen = EmbeddingGenerator()
```
**用途**: MCP 工具/提示词/资源同步到向量库  
**迁移建议**: 
- 替换为 `await get_model_client()` → `client.embeddings.create()`
- 或使用 `BaseRAGService` 中已有的 embedding 方法

#### 2. **`services/search_service/search_service.py`** ⭐ 高优先级
```python
# 第 46 行
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator

# 使用位置：第 52 行
self.embedding_gen = EmbeddingGenerator()
```
**用途**: 语义搜索工具/提示词/资源  
**迁移建议**: 同上

---

### B. Data Analytics Service（9 个文件）

#### 3. **`tools/services/data_analytics_service/services/digital_service/patterns/custom_rag_service.py`** ⭐⭐ 中优先级
```python
# 第 32 行
from tools.services.intelligence_service.vision.image_analyzer import analyze as vlm_analyze

# 第 39-41 行
from tools.services.intelligence_service.vector_db.chunking_service import (
    ChunkingService, ChunkingStrategy, ChunkConfig
)
```
**用途**: 
- VLM 分析 PDF 图片
- 多模态 PDF 分块
**迁移建议**:
- Vision: `client.vision.completions.create()`
- Chunking: 考虑迁移到 `isa_common` 或保留（如果已优化）

#### 4. **`tools/services/data_analytics_service/services/digital_service/patterns/graph_rag/neo4j_store.py`**
```python
# 第 17 行
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator
```
**用途**: Graph RAG 实体嵌入  
**迁移建议**: 使用 `client.embeddings.create()`

#### 5. **`tools/services/data_analytics_service/services/digital_service/patterns/self_rag_service.py`**
```python
# 第 280 行（条件导入）
from tools.services.intelligence_service.language.embedding_generator import search
```
**用途**: Self-RAG 检索  
**迁移建议**: 使用 BaseRAGService 的方法或直接调用向量库

#### 6. **`tools/services/data_analytics_service/services/data_service/analytics/data_eda.py`**
```python
# 第 32 行 / 第 36 行（条件导入）
from tools.services.intelligence_service.language.text_generator import TextGenerator
```
**用途**: EDA 洞察生成  
**迁移建议**: `client.chat.completions.create()`

#### 7. **`tools/services/data_analytics_service/services/data_service/search/sql_generator.py`** ⚠️ 注意
```python
# 第 17 行（条件导入）
from tools.services.intelligence_service.language.text_generator import generate
```
**用途**: 自然语言到 SQL 转换  
**状态**: 有 fallback，已部分迁移但保留旧导入  
**迁移建议**: 完全迁移到 ISA Model

#### 8. **`tools/services/data_analytics_service/services/data_service/management/metadata/semantic_enricher.py`**
```python
# 第 16 行 / 第 25 行（条件导入）
from tools.services.intelligence_service.language.text_extractor import TextExtractor
```
**用途**: 元数据语义增强（实体提取、分类）  
**迁移建议**: `client.chat.completions.create()` + 结构化输出

#### 9. **`tools/services/data_analytics_service/services/data_service/management/metadata/metadata_embedding.py`**
```python
# 第 22 行
from tools.services.intelligence_service.language.embedding_generator import embed, EmbeddingGenerator
```
**用途**: 元数据嵌入（5 次使用）  
**迁移建议**: `client.embeddings.create()`

#### 10. **`tools/services/data_analytics_service/services/data_service/transformation/lang_extractor.py`**
```python
# 使用 TextExtractor, TextSummarizer, EmbeddingGenerator, TextGenerator
```
**用途**: 语言提取和转换  
**迁移建议**: 全面迁移到 ISA Model API

#### 11. **`tools/services/data_analytics_service/services/digital_service/enhanced_digital_service.py`**
根据之前的报告，使用了多个 intelligence_service 组件  
**迁移建议**: 逐个替换为 ISA Model API

---

### C. Web Services（1 个文件）

#### 12. **`tools/services/web_services/services/web_crawl_service.py`** ⭐ 高优先级
```python
# 第 21-22 行
from tools.services.intelligence_service.vision.image_analyzer import analyze as image_analyze
from tools.services.intelligence_service.language.text_generator import generate

# 第 228 行（条件导入）
from tools.services.intelligence_service.language.text_generator import generate
```
**用途**: 
- 网页截图分析
- 网页内容智能合成
**迁移建议**:
- Vision: `client.vision.completions.create()`
- Text: `client.chat.completions.create()`

---

### D. Plan Tools（1 个文件）

#### 13. **`tools/plan_tools/plan_tools.py`** ⭐ 高优先级
```python
# 第 21 行
from tools.services.intelligence_service.language.text_generator import generate

# 使用位置：第 188 行, 第 680 行
result_data = await generate(prompt, temperature=0.1)
```
**用途**: 执行计划生成和重规划  
**迁移建议**: 
```python
from core.clients.model_client import get_model_client

client = await get_model_client()
response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.1
)
result_data = response.choices[0].message.content
```

---

### E. Intelligence Service 内部（交叉引用）

以下文件属于 `intelligence_service` 内部模块，暂时保留：
- `tools/services/intelligence_service/language/embedding_generator.py` - 内部使用 chunking, vector_db
- `tools/services/intelligence_service/vector_db/hybrid_search_service.py` - 使用 embedding_generator
- `tools/services/intelligence_service/vector_db/chunking_service.py` - 条件使用 EmbeddingGenerator
- `tools/services/intelligence_service/tools/vision_tools.py` - 使用 image_analyzer, text_generator

**建议**: 
- 如果 `intelligence_service` 保留作为工具封装层，内部引用合理
- 如果完全迁移，需要重构内部依赖

---

## 📋 迁移优先级建议

### 🔴 高优先级（核心服务）
1. **`services/sync_service/sync_service.py`** - MCP 同步核心
2. **`services/search_service/search_service.py`** - 搜索核心
3. **`tools/plan_tools/plan_tools.py`** - 计划工具核心
4. **`tools/services/web_services/services/web_crawl_service.py`** - Web 爬取核心

### 🟡 中优先级（功能增强）
5. `tools/services/data_analytics_service/services/digital_service/patterns/custom_rag_service.py`
6. `tools/services/data_analytics_service/services/data_service/search/sql_generator.py`
7. `tools/services/data_analytics_service/services/data_service/analytics/data_eda.py`

### 🟢 低优先级（内部/工具）
8. `tools/services/data_analytics_service/services/digital_service/patterns/graph_rag/neo4j_store.py`
9. `tools/services/data_analytics_service/services/digital_service/patterns/self_rag_service.py`
10. 其他 metadata/transformation 服务

---

## 🔄 迁移模式示例

### 模式 1: Embedding Generator → ISA Model

**旧代码** (`services/sync_service/sync_service.py`):
```python
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator

self.embedding_gen = EmbeddingGenerator()

# 使用
embedding = await self.embedding_gen.embed(text)
```

**新代码**:
```python
from core.clients.model_client import get_model_client

# 在 __init__ 或方法中
client = await get_model_client()

# 使用
response = await client.embeddings.create(
    input=text,
    model="text-embedding-3-small"
)
embedding = response.data[0].embedding
```

### 模式 2: Text Generator → ISA Model

**旧代码** (`tools/plan_tools/plan_tools.py`):
```python
from tools.services.intelligence_service.language.text_generator import generate

result_data = await generate(prompt, temperature=0.1)
```

**新代码**:
```python
from core.clients.model_client import get_model_client

client = await get_model_client()
response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.1
)
result_data = response.choices[0].message.content
```

### 模式 3: Vision Analyzer → ISA Model

**旧代码** (`tools/services/web_services/services/web_crawl_service.py`):
```python
from tools.services.intelligence_service.vision.image_analyzer import analyze as image_analyze

result = await image_analyze(image_path, prompt)
```

**新代码**:
```python
from core.clients.model_client import get_model_client

client = await get_model_client()
response = await client.vision.completions.create(
    image=image_path,
    prompt=prompt,
    model="gpt-4o-mini"
)
result = response.choices[0].message.content
```

---

## 📝 迁移检查清单

### 对于每个文件：
- [ ] 替换 `intelligence_service` 导入为 `core.clients.model_client`
- [ ] 更新函数调用为 ISA Model API
- [ ] 处理错误和异常情况
- [ ] 更新类型注解
- [ ] 添加适当的日志记录
- [ ] 运行单元测试验证功能
- [ ] 更新相关文档

---

## 🎯 下一步行动

1. **立即迁移**（高优先级）：
   - `services/sync_service/sync_service.py`
   - `services/search_service/search_service.py`
   - `tools/plan_tools/plan_tools.py`
   - `tools/services/web_services/services/web_crawl_service.py`

2. **逐步迁移**（中优先级）：
   - Data Analytics 服务中的剩余文件

3. **评估保留**：
   - `intelligence_service` 内部模块是否作为工具封装层保留
   - VectorDB/Chunking 服务是否需要迁移到 `isa_common`

4. **文档更新**：
   - 更新所有相关文档
   - 添加迁移指南
   - 标记已废弃的 `intelligence_service` API

---

## 📊 统计摘要

| 类别 | 数量 | 状态 |
|------|------|------|
| 已迁移文件 | 7 | ✅ |
| 待迁移文件（高优先级） | 4 | 🔴 |
| 待迁移文件（中优先级） | 3 | 🟡 |
| 待迁移文件（低优先级） | 21 | 🟢 |
| 测试/文档文件 | 多个 | 📝 |
| **总计** | **35+** | - |

---

## 🔗 相关资源

- **ISA Model 客户端**: `core/clients/model_client.py`
- **Base RAG 服务**: `tools/services/data_analytics_service/services/digital_service/base/base_rag_service.py`
- **迁移状态文档**: `tools/services/data_analytics_service/services/digital_service/docs/rag_status.md`

---

**报告结束**

