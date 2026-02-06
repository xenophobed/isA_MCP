# Data Stack Architecture - 正确版本

## 🎯 核心原则
**模块化设计 - 只需替换对应组件**

---

## 📦 数据技术栈

### 1. **数据存储** - MinIO (Parquet)
```
用途: 所有数据的主存储
格式: Parquet (列式存储，高压缩)
位置: core/clients/minio_client.py
状态: ✅ 已集成
```

### 2. **快速查询** - DuckDB
```
用途: 高频数据查询缓存
特点:
  - 内存分析数据库
  - 原生 Parquet 支持
  - 与 Polars 零拷贝集成 (Arrow)
位置: core/clients/duckdb_client.py
状态: ✅ 已集成 (via isa-common)
```

### 3. **数据分析** - Polars
```
用途: 数据处理和转换
特点:
  - Rust 实现，性能 5-10x Pandas
  - 懒加载 (Lazy evaluation)
  - 与 DuckDB 零拷贝集成
状态: ⏳ 需要替换 Pandas
```

### 4. **向量存储** - Qdrant
```
用途: Embeddings 向量数据库
特点:
  - 高性能向量搜索
  - gRPC 接口
  - 多租户隔离
位置: core/clients/qdrant_client.py
状态: ✅ 刚创建
```

---

## 🔄 数据流

### 数据摄取流程
```
CSV/Excel
  ↓ (读取)
Polars DataFrame
  ↓ (写入)
MinIO (Parquet) ← 主存储
  ↓ (高频加载)
DuckDB ← 查询缓存
```

### 数据查询流程
```
MinIO (Parquet)
  ↓ (DuckDB 读取)
DuckDB Query Engine
  ↓ (Arrow format - 零拷贝)
Polars DataFrame
  ↓ (分析/转换)
Result
```

### 向量搜索流程
```
Text
  ↓ (ISA Model)
Embeddings (1536-dim)
  ↓ (存储)
Qdrant Vector DB
  ↓ (相似度搜索)
Top-K Results
```

---

## 🔧 需要改动的地方

### 1. **Adapters 层** - Pandas → Polars
```python
# 文件位置
tools/services/data_analytics_service/adapters/sink_adapters/
  - parquet_adapter.py (Line 7: import pandas)
  - duckdb_adapter.py (Line 7: import pandas)
  - csv_adapter.py (可能也有 pandas)

# 改动示例
- import pandas as pd
+ import polars as pl

- df = pd.DataFrame(data)
+ df = pl.DataFrame(data)

- df.to_parquet(path)
+ df.write_parquet(path)
```

### 2. **Preprocessor 层** - Pandas → Polars
```python
# 文件位置
tools/services/data_analytics_service/services/data_service/preprocessor/

# 改动: DataFrame 操作全部改成 Polars API
```

### 3. **Metadata Embedding 层** - Supabase → Qdrant
```python
# 文件位置
tools/services/data_analytics_service/services/data_service/management/metadata/metadata_embedding.py

# 改动
- from core.database.supabase_client import get_supabase_client
+ from core.clients.qdrant_client import get_qdrant_client

- self.supabase = get_supabase_client()
- result = self.supabase.client.schema('dev').table('db_meta_embedding').upsert()
+ self.qdrant = get_qdrant_client(collection_name='metadata_embeddings')
+ self.qdrant.upsert(collection_name='metadata_embeddings', points=[...])

# 向量搜索
- result = self.supabase.rpc('match_metadata_embeddings', {...})
+ results = self.qdrant.search(
+     collection_name='metadata_embeddings',
+     query_vector=embedding,
+     limit=limit,
+     query_filter={"user_id": user_id}
+ )
```

### 4. **Data Query 层** - 确保 DuckDB + Polars
```python
# 文件位置
tools/services/data_analytics_service/tools/data_tools.py - data_query()

# 确保使用
from core.clients.duckdb_client import DuckDBClient
from core.clients.minio_client import get_minio_client
import polars as pl

# 查询流程
# 1. MinIO 下载 Parquet
# 2. DuckDB 执行 SQL
# 3. Polars 处理结果
```

---

## ✅ 已完成

1. ✅ `core/clients/qdrant_client.py` - 创建完成
2. ✅ `core/clients/postgres_client.py` - 创建完成 (备用)
3. ✅ `core/clients/duckdb_client.py` - 已存在
4. ✅ `core/clients/minio_client.py` - 已存在

---

## ⏳ 待完成

### 优先级 1 - 向量存储迁移 🔴
- [ ] 更新 `metadata_embedding.py` 使用 Qdrant

### 优先级 2 - 数据处理迁移 🟡
- [ ] 更新 `parquet_adapter.py` 使用 Polars
- [ ] 更新 `duckdb_adapter.py` 使用 Polars
- [ ] 更新 `preprocessor_service.py` 使用 Polars

### 优先级 3 - 查询层验证 🟢
- [ ] 验证 `data_query` 使用 DuckDB + Polars
- [ ] 运行 `test_async_data.py` 全流程测试

---

## 📊 技术栈对比

| 组件 | 旧方案 | 新方案 | 提升 |
|-----|--------|--------|------|
| 数据库 | Supabase (?) | Qdrant | 专业向量DB |
| 数据处理 | Pandas | Polars | 5-10x 性能 |
| 查询引擎 | 手动SQL | DuckDB | SQL接口 + 零拷贝 |
| 存储 | ✅ MinIO | ✅ MinIO | 无变化 |
| 格式 | ✅ Parquet | ✅ Parquet | 无变化 |

---

## 🎯 下一步

**按优先级顺序执行**:

1. 更新 `metadata_embedding.py` → Qdrant
2. 更新所有 Adapters → Polars
3. 测试完整流程

**改动规模**: 小 - 只是替换 API 调用，架构本身已经模块化 ✅

---

**文档版本**: v1.0
**最后更新**: 2025-11-03
