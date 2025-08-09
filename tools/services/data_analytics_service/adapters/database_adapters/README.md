# 数据库适配器扩展指南

## 概述

数据分析系统现已支持多种数据库类型，包括传统数据库、NoSQL数据库、数据仓库和数据湖。所有适配器都基于统一的 `DatabaseAdapter` 接口，提供一致的使用体验。

## 支持的数据库类型

### 传统关系数据库
- **PostgreSQL** - 开源关系数据库
- **MySQL** - 流行的开源数据库  
- **Oracle** - 企业级关系数据库
- **SQLite** - 轻量级文件数据库
- **SQL Server** - 微软企业数据库

### NoSQL数据库
- **MongoDB** - 文档数据库
- **Redis** - 内存键值存储
- **Elasticsearch** - 搜索和分析引擎

### 数据仓库
- **Snowflake** - 云原生数据仓库
- **Google BigQuery** - 无服务器数据仓库
- **ClickHouse** - 列式分析数据库

### 数据湖
- **Delta Lake** - 开源存储层
- **S3/MinIO** - 对象存储

## 使用方法

### 1. 基本配置

每种数据库类型都有其特定的配置参数：

#### PostgreSQL
```python
from tools.services.data_analytics_service.adapters.database_adapters import PostgreSQLAdapter

adapter = PostgreSQLAdapter()
config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'mydb',
    'username': 'user',
    'password': 'password'
}
await adapter.initialize(config)
```

#### Oracle
```python
from tools.services.data_analytics_service.adapters.database_adapters import OracleAdapter

adapter = OracleAdapter()
config = {
    'host': 'localhost',
    'port': 1521,
    'service_name': 'ORCLPDB1',  # 或使用 'database' 字段
    'username': 'user',
    'password': 'password'
}
await adapter.initialize(config)
```

#### MongoDB
```python
from tools.services.data_analytics_service.adapters.database_adapters import MongoDBAdapter

adapter = MongoDBAdapter()
config = {
    'host': 'localhost',
    'port': 27017,
    'database': 'mydb',
    'username': 'user',  # 可选
    'password': 'password'  # 可选
}
# 或者使用连接字符串
config = {
    'connection_string': 'mongodb://user:password@localhost:27017/mydb',
    'database': 'mydb'
}
await adapter.initialize(config)
```

#### Redis
```python
from tools.services.data_analytics_service.adapters.database_adapters import RedisAdapter

adapter = RedisAdapter()
config = {
    'host': 'localhost',
    'port': 6379,
    'database': 0,  # Redis数据库编号
    'password': 'password'  # 可选
}
await adapter.initialize(config)
```

#### Elasticsearch
```python
from tools.services.data_analytics_service.adapters.database_adapters import ElasticsearchAdapter

adapter = ElasticsearchAdapter()
config = {
    'host': 'localhost',
    'port': 9200,
    'username': 'elastic',  # 可选
    'password': 'password',  # 可选
    'use_ssl': False,  # 可选
    'verify_certs': True  # 可选
}
await adapter.initialize(config)
```

#### Snowflake
```python
from tools.services.data_analytics_service.adapters.database_adapters import SnowflakeAdapter

adapter = SnowflakeAdapter()
config = {
    'username': 'user',
    'password': 'password',
    'account': 'account_identifier',
    'warehouse': 'COMPUTE_WH',
    'database': 'MYDB',
    'schema': 'PUBLIC'
}
await adapter.initialize(config)
```

#### BigQuery
```python
from tools.services.data_analytics_service.adapters.database_adapters import BigQueryAdapter

adapter = BigQueryAdapter()
config = {
    'project_id': 'my-gcp-project',
    'service_account_path': '/path/to/service-account.json',  # 可选
    'dataset': 'my_dataset'  # 可选默认数据集
}
await adapter.initialize(config)
```

#### ClickHouse
```python
from tools.services.data_analytics_service.adapters.database_adapters import ClickHouseAdapter

adapter = ClickHouseAdapter()
config = {
    'host': 'localhost',
    'port': 9000,
    'database': 'default',
    'username': 'default',
    'password': '',
    'secure': False  # 可选，启用SSL
}
await adapter.initialize(config)
```

#### Delta Lake
```python
from tools.services.data_analytics_service.adapters.database_adapters import DeltaLakeAdapter

adapter = DeltaLakeAdapter()
config = {
    'path': '/path/to/delta/tables',  # 本地路径
    # 或者云存储
    # 'path': 's3://my-bucket/delta-tables',
    'storage_options': {  # 可选，用于云存储
        'AWS_ACCESS_KEY_ID': 'your-key',
        'AWS_SECRET_ACCESS_KEY': 'your-secret'
    }
}
await adapter.initialize(config)
```

#### S3/MinIO
```python
from tools.services.data_analytics_service.adapters.database_adapters import S3Adapter

adapter = S3Adapter()
config = {
    'access_key_id': 'your-access-key',
    'secret_access_key': 'your-secret-key',
    'bucket_name': 'my-data-bucket',
    'region': 'us-east-1',
    'prefix': 'data/',  # 可选前缀
    # 'endpoint_url': 'http://localhost:9000'  # 用于MinIO
}
await adapter.initialize(config)
```

### 2. 通用操作

所有适配器都支持以下通用操作：

```python
# 获取表列表
tables = adapter.get_tables()
for table in tables:
    print(f"表: {table.table_name}, 记录数: {table.record_count}")

# 获取表结构
columns = adapter.get_columns('table_name')
for column in columns:
    print(f"字段: {column.column_name}, 类型: {column.data_type}")

# 获取关系信息
relationships = adapter.get_relationships()

# 获取索引信息
indexes = adapter.get_indexes()

# 分析数据分布
distribution = adapter.analyze_data_distribution('table_name', 'column_name')

# 获取样本数据
sample_data = adapter.get_sample_data('table_name', limit=10)
```

### 3. 执行查询

```python
# 传统SQL数据库
results = adapter._execute_query("SELECT * FROM users LIMIT 10")

# MongoDB
results = adapter._execute_query("db.users.find({}).limit(10)")

# Redis
results = adapter._execute_query("KEYS user:*")

# Elasticsearch
results = adapter._execute_query('{"query": {"match_all": {}}}')
```

### 4. 特殊功能

#### Delta Lake时间旅行
```python
# 查询特定版本的数据
historical_data = adapter.time_travel_query('sales_table', version=5)

# 优化表
result = adapter.optimize_table('sales_table')

# 清理旧文件
result = adapter.vacuum_table('sales_table', retention_hours=168)
```

#### BigQuery干运行
```python
# 估算查询成本
cost_estimate = adapter.execute_dry_run("SELECT * FROM dataset.large_table")
print(f"预估成本: ${cost_estimate['estimated_cost_usd']:.4f}")
```

#### S3文件操作
```python
# 上传文件
result = adapter.upload_file('/local/file.csv', 'data/file.csv')

# 下载文件
result = adapter.download_file('data/file.csv', '/local/downloaded.csv')

# 获取桶信息
bucket_info = adapter.get_bucket_info()
```

## 依赖安装

每种适配器都有其特定的Python依赖包：

```bash
# PostgreSQL
pip install psycopg2-binary asyncpg

# MySQL
pip install mysql-connector-python aiomysql

# Oracle
pip install cx_Oracle
# 或者使用新版本
pip install oracledb

# MongoDB
pip install pymongo

# Redis
pip install redis

# Elasticsearch
pip install elasticsearch

# Snowflake
pip install snowflake-connector-python

# BigQuery
pip install google-cloud-bigquery

# ClickHouse
pip install clickhouse-driver

# Delta Lake
pip install deltalake pyarrow pandas

# S3
pip install boto3 pandas pyarrow

# SQLite (内置)
pip install aiosqlite
```

## 错误处理

所有适配器都包含完善的错误处理机制：

```python
try:
    await adapter.initialize(config)
    tables = adapter.get_tables()
except ImportError as e:
    print(f"缺少依赖包: {e}")
except ConnectionError as e:
    print(f"连接失败: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

## 扩展新适配器

要添加新的数据库类型支持，请按以下步骤：

1. 创建新的适配器类，继承 `DatabaseAdapter`
2. 实现所有抽象方法
3. 在 `__init__.py` 中导出新适配器
4. 在 `database_adapter.py` 中添加初始化方法
5. 更新类型映射

## 性能优化建议

1. **连接池**: 大多数适配器支持连接池，合理配置可提高性能
2. **批量操作**: 使用批量插入而非单条插入
3. **索引利用**: 确保查询能够利用现有索引
4. **采样分析**: 对大表使用采样进行数据分析
5. **缓存**: 缓存元数据信息避免重复查询

## 安全考虑

1. **凭证管理**: 使用环境变量或密钥管理服务存储数据库凭证
2. **网络安全**: 在生产环境中启用SSL/TLS加密
3. **权限控制**: 使用最小权限原则配置数据库用户
4. **审计日志**: 启用数据库访问日志记录

## 监控和诊断

1. **健康检查**: 定期执行 `health_check()` 监控连接状态
2. **性能指标**: 监控查询执行时间和资源使用情况
3. **错误日志**: 记录和分析连接失败和查询错误
4. **资源监控**: 监控数据库服务器的CPU、内存和存储使用情况