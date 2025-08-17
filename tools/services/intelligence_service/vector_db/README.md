# Enhanced RAG Vector Database System

## 概述

这个增强的 RAG 系统提供了先进的混合搜索能力，结合了语义搜索和词汇搜索，支持多种向量数据库后端，并包含先进的重排算法。

## 架构图

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Application   │───▶│ Embedding        │───▶│ Hybrid Search   │
│     Layer       │    │ Generator        │    │ Service         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ ISA Client       │    │ Vector DB       │
                       │ (Fallback)       │    │ Factory         │
                       └──────────────────┘    └─────────────────┘
                                                        │
                                ┌───────────────────────┼─────────────────────┐
                                ▼                       ▼                     ▼
                       ┌─────────────────┐    ┌─────────────────┐   ┌─────────────────┐
                       │ Supabase        │    │ Qdrant          │   │ Future:         │
                       │ Vector DB       │    │ Vector DB       │   │ Weaviate, etc.  │
                       │ (pgvector+FTS)  │    │ (High Perf)     │   │                 │
                       └─────────────────┘    └─────────────────┘   └─────────────────┘
```

## 主要功能

### 1. 混合搜索 (Hybrid Search)
- **语义搜索**: 使用 pgvector 的 IVFFLAT 索引进行高效的向量相似性搜索
- **词汇搜索**: 使用 PostgreSQL 的全文搜索 (tsvector/tsquery) 进行 BM25 风格搜索
- **结果融合**: 支持 Reciprocal Rank Fusion (RRF)、加权平均等融合算法

### 2. 向量数据库抽象层
- **统一接口**: 通过 `BaseVectorDB` 抽象类提供统一的 API
- **多后端支持**: 支持 Supabase (pgvector)、Qdrant、Weaviate 等
- **透明切换**: 通过工厂模式和环境变量轻松切换数据库

### 3. 高级重排算法
- **Max Marginal Relevance (MMR)**: 平衡相关性和多样性，减少结果冗余
- **多重排策略**: 支持 ISA Jina 重排器、MMR、集成重排
- **自定义多样性函数**: 支持基于语义、词汇、元数据的多样性计算

### 4. 增量更新机制
- **变更跟踪**: 自动记录数据变更并进行批量处理
- **索引刷新**: 智能的索引维护和优化策略
- **新鲜度监控**: 实时监控知识库的新鲜度状态

## 使用方法

### 基础搜索

```python
from tools.services.intelligence_service.language.embedding_generator import (
    hybrid_search_local, enhanced_search
)

# 混合搜索
results = await hybrid_search_local(
    query_text="Python 编程最佳实践",
    user_id="user123",
    top_k=5,
    search_mode="hybrid",      # "semantic", "lexical", "hybrid"
    ranking_method="rrf"       # "rrf", "weighted", "mmr"
)

# 智能路由搜索
results = await enhanced_search(
    query_text="机器学习算法比较",
    user_id="user123",
    search_mode="hybrid",
    use_local_db=True
)
```

### 存储知识

```python
from tools.services.intelligence_service.language.embedding_generator import store_knowledge_local

result = await store_knowledge_local(
    user_id="user123",
    text="深度学习是机器学习的一个子领域...",
    metadata={
        "source": "深度学习教程",
        "category": "AI",
        "difficulty": "intermediate"
    }
)
```

### 高级重排

```python
from tools.services.intelligence_service.language.embedding_generator import (
    mmr_rerank, advanced_rerank
)

# MMR 重排（平衡相关性和多样性）
mmr_results = await mmr_rerank(
    query="机器学习算法",
    documents=documents,
    lambda_param=0.7,  # 0.7 相关性 + 0.3 多样性
    top_k=5
)

# 多策略重排
advanced_results = await advanced_rerank(
    query="深度学习框架比较",
    documents=documents,
    method="combined",  # "mmr", "isa", "combined"
    top_k=5
)
```

### 向量数据库配置

```python
# 环境变量配置
VECTOR_DB_TYPE=supabase  # supabase, qdrant, weaviate
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_key

# 程序化配置
from tools.services.intelligence_service.vector_db import get_vector_db, VectorDBType

# 获取默认数据库
vector_db = get_vector_db()

# 指定数据库类型
qdrant_db = get_vector_db(
    db_type=VectorDBType.QDRANT,
    config={
        'host': 'localhost',
        'port': 6333,
        'collection_name': 'knowledge_base'
    }
)
```

## 数据库迁移

### 1. 运行向量索引迁移

```bash
# 应用向量索引和全文搜索索引
supabase db reset --local
# 或
psql -d your_db -f config/supabase/migrations/20250815000001_add_user_knowledge_vector_index.sql
psql -d your_db -f config/supabase/migrations/20250815000002_add_sql_execution_function.sql
```

### 2. 验证索引

```sql
-- 检查向量索引
SELECT schemaname, tablename, indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'user_knowledge' 
  AND indexdef LIKE '%vector%';

-- 检查全文搜索索引
SELECT schemaname, tablename, indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'user_knowledge' 
  AND indexdef LIKE '%gin%';
```

## 性能优化建议

### 1. 索引优化
- **IVFFLAT 参数**: 根据数据量调整 `lists` 参数 (推荐: √(行数))
- **全文搜索**: 定期运行 `VACUUM ANALYZE` 更新统计信息
- **复合索引**: 为常用查询模式创建复合索引

### 2. 搜索优化
- **批量处理**: 对于大量查询，使用批量 API
- **缓存策略**: 缓存常用查询的结果
- **分页查询**: 对于大结果集使用分页

### 3. 重排优化
- **MMR λ 参数**: 根据应用场景调整相关性/多样性平衡
- **批处理重排**: 对多个查询批量重排以提高效率
- **预计算**: 对于常用查询预计算重排结果

## 监控和维护

### 1. 新鲜度监控

```python
from tools.services.intelligence_service.vector_db.incremental_update_service import (
    get_knowledge_freshness, refresh_knowledge_base
)

# 检查新鲜度
status = await get_knowledge_freshness(user_id="user123")
print(f"数据新鲜度: {status['staleness_hours']:.1f} 小时")

# 强制刷新
result = await refresh_knowledge_base(user_id="user123")
```

### 2. 性能监控

```python
from tools.services.intelligence_service.vector_db.hybrid_search_service import hybrid_search_service

# 获取服务统计
stats = await hybrid_search_service.get_stats()
print(f"本地数据库可用: {stats['local_db_available']}")
```

### 3. 索引维护

```sql
-- 定期维护 (建议每周)
VACUUM ANALYZE dev.user_knowledge;

-- 重建向量索引 (如果性能下降)
REINDEX INDEX dev.idx_user_knowledge_embedding_vector;

-- 检查索引使用情况
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE tablename = 'user_knowledge';
```

## 配置参数

### 搜索配置

```python
from tools.services.intelligence_service.vector_db.base_vector_db import VectorSearchConfig

config = VectorSearchConfig(
    top_k=10,                           # 返回结果数量
    search_mode=SearchMode.HYBRID,      # 搜索模式
    ranking_method=RankingMethod.RRF,   # 排序方法
    semantic_weight=0.7,                # 语义权重
    lexical_weight=0.3,                 # 词汇权重
    mmr_lambda=0.5,                     # MMR 多样性参数
    include_embeddings=False            # 是否返回向量
)
```

### 更新策略配置

```python
from tools.services.intelligence_service.vector_db.incremental_update_service import UpdatePolicy

policy = UpdatePolicy(
    strategy=UpdateStrategy.BATCH,      # 更新策略
    batch_size=100,                     # 批处理大小
    batch_interval_minutes=5,           # 批处理间隔
    max_staleness_hours=24,             # 最大陈旧时间
    enable_auto_reindex=True,           # 自动重建索引
    reindex_threshold_changes=1000      # 重建索引阈值
)
```

## 故障排除

### 常见问题

1. **向量搜索慢**
   - 检查 IVFFLAT 索引是否创建
   - 调整 `lists` 参数
   - 考虑增加内存设置

2. **全文搜索无结果**
   - 检查 `text_search_vector` 列是否填充
   - 验证触发器是否正常工作
   - 检查查询语法

3. **混合搜索结果不理想**
   - 调整语义/词汇权重
   - 尝试不同的融合算法
   - 检查数据质量

### 调试工具

```python
# 启用详细日志
import logging
logging.getLogger('tools.services.intelligence_service.vector_db').setLevel(logging.DEBUG)

# 检查搜索详情
search_result = await hybrid_search_local(query, user_id, top_k=5)
print(f"搜索方法: {search_result[0]['method']}")
print(f"语义分数: {search_result[0]['semantic_score']}")
print(f"词汇分数: {search_result[0]['lexical_score']}")
```

## 未来扩展

### 1. 新增向量数据库
- 在 `vector_db/` 目录下创建新的实现类
- 继承 `BaseVectorDB` 抽象类
- 在工厂类中注册新的数据库类型

### 2. 自定义重排算法
- 实现自定义多样性函数
- 扩展 MMR 算法参数
- 集成外部重排服务

### 3. 高级功能
- 多模态搜索 (文本+图像)
- 实时流式更新
- 分布式搜索集群
- A/B 测试框架

---

这个增强的 RAG 系统为您提供了生产级的搜索能力，支持从简单的语义搜索到复杂的混合搜索和多样性优化，可以根据您的具体需求进行灵活配置和扩展。