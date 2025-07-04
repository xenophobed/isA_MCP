# Database Management System

This directory contains the centralized database management system for the MCP server, providing improved connection pooling, schema management, and repository patterns while maintaining backward compatibility.

## 🏗️ **Architecture Overview**

```
core/database/
├── __init__.py              # Main module exports
├── connection_manager.py    # Connection pooling & management
├── repositories.py          # Repository pattern implementations
├── schema_manager.py        # Schema validation & management
├── migration_manager.py     # Database migrations
├── compatibility.py         # Backward compatibility layer
├── migration_script.py      # Migration helper script
└── README.md               # This documentation
```

## 🚀 **Key Features**

### **1. Connection Pooling**
- **PostgreSQL Connection Pool**: Direct database access with asyncpg
- **Supabase Client Management**: Centralized Supabase client with singleton pattern
- **Health Monitoring**: Built-in health checks and connection monitoring
- **Fallback Strategy**: Graceful fallback to Supabase-only if PostgreSQL pool fails

### **2. Repository Pattern**
- **Domain-Specific Repositories**: Separate repositories for different data domains
- **Type Safety**: Full type annotations with Pydantic models
- **Error Handling**: Consistent error handling across all operations
- **Async/Await**: Full async support for all database operations

### **3. Schema Management**
- **Schema Validation**: Automatic validation against expected schema
- **Missing Table Detection**: Identifies missing tables and columns
- **Schema Backup**: Create backups before making changes
- **Migration Support**: Integrated with migration system

### **4. Migration System**
- **Version Control**: Track database schema versions
- **Automatic Migrations**: Apply pending migrations automatically
- **Rollback Support**: Rollback to previous versions (with rollback scripts)
- **Migration History**: Track all applied migrations with checksums

### **5. Backward Compatibility**
- **Zero Code Changes**: Existing code works without modifications
- **Drop-in Replacement**: New system replaces old `supabase_client` transparently
- **Gradual Migration**: Migrate to new patterns at your own pace

## 📊 **Database Tables**

The system manages the following tables:

### **Core Tables**
- `memories` - Memory storage and retrieval
- `users` - User management and profiles
- `user_sessions` - Session management
- `models` - Model registry
- `model_capabilities` - Model capabilities

### **Cache Tables**
- `weather_cache` - Weather data caching
- `prompt_embeddings` - Prompt embeddings cache
- `resource_embeddings` - Resource embeddings cache
- `tool_embeddings` - Tool embeddings cache

### **Analytics Tables**
- `rag_documents` - RAG document storage with vector embeddings
- `db_metadata_embedding` - Data analytics metadata embeddings
- `selection_history` - Usage history tracking

### **Security Tables**
- `audit_log` - Tool usage logging
- `authorization_requests` - Security authorization requests

### **System Tables**
- `migration_history` - Database migration tracking

## 🔧 **Usage Examples**

### **1. Minimal Change (Backward Compatible)**

```python
# Existing code works unchanged
from core.supabase_client import get_supabase_client

supabase = get_supabase_client()
await supabase.set_memory("key", "value")
```

### **2. Repository Pattern (Recommended)**

```python
from core.database import MemoryRepository

memory_repo = MemoryRepository()
await memory_repo.set_memory("key", "value", "category", 5)
```

### **3. Direct Database Access**

```python
from core.database import get_database_manager

db = await get_database_manager()

# Vector search
results = await db.execute_vector_search(
    table="rag_documents",
    embedding_column="embedding", 
    query_embedding=[0.1, 0.2, ...],
    limit=10,
    filters={"collection_name": "docs"}
)

# Raw SQL
results = await db.execute_query(
    "SELECT * FROM memories WHERE category = $1",
    "important"
)
```

### **4. Schema Management**

```python
from core.database import SchemaManager

schema_manager = SchemaManager()

# Validate schema
validation = await schema_manager.validate_schema()
if not validation['valid']:
    print(f"Missing tables: {validation['missing_tables']}")
    
# Create missing tables
await schema_manager.create_missing_tables(validation)
```

### **5. Migration Management**

```python
from core.database import MigrationManager

migration_manager = MigrationManager()

# Check current version
version = await migration_manager.get_current_version()

# Apply pending migrations
result = await migration_manager.apply_migrations()
print(f"Applied {result['applied_count']} migrations")
```

## 🔄 **Migration Guide**

### **Step 1: Test Current System**

```bash
cd core/database
python migration_script.py
```

### **Step 2: Update Dependencies**

```bash
pip install asyncpg  # For PostgreSQL direct access
```

### **Step 3: Environment Variables**

Ensure these are set in your `.env`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_PWD=your-database-password
```

### **Step 4: Gradual Migration**

1. **Phase 1**: Keep existing imports (zero changes)
2. **Phase 2**: Migrate to repository pattern for new code
3. **Phase 3**: Refactor existing code to use repositories
4. **Phase 4**: Use direct database access for advanced features

## 🔍 **Repository Interfaces**

### **MemoryRepository**
```python
class MemoryRepository:
    async def get_memory(self, key: str) -> Optional[Dict[str, Any]]
    async def set_memory(self, key: str, value: str, category: str = "general", 
                        importance: int = 1, user_id: str = "default") -> bool
    async def search_memories(self, query: str, category: Optional[str] = None, 
                             limit: int = 10) -> List[Dict[str, Any]]
    async def delete_memory(self, key: str) -> bool
```

### **EmbeddingRepository**
```python
class EmbeddingRepository:
    async def store_embeddings(self, table: str, embeddings_data: List[Dict]) -> bool
    async def search_embeddings(self, table: str, query_embedding: List[float], 
                              limit: int = 10, filters: Dict[str, Any] = None) -> List[Dict]
    async def get_embeddings_cache(self, table: str, key_column: str = None) -> Dict[str, List[float]]
```

## 🚀 **Performance Benefits**

### **Connection Pooling**
- **Reduced Latency**: Reuse existing connections
- **Better Throughput**: Handle more concurrent requests
- **Resource Management**: Automatic connection lifecycle management

### **Vector Operations**
- **Direct PostgreSQL Access**: Bypass Supabase API for vector operations
- **Optimized Queries**: Use native pgvector operators
- **Batch Operations**: Efficient bulk operations

### **Caching**
- **Embedding Cache**: Cache frequently used embeddings
- **Query Result Cache**: Cache expensive query results
- **Connection Reuse**: Minimize connection overhead

## 🔒 **Security Considerations**

### **Connection Security**
- **Service Role Keys**: Use Supabase service role for server operations
- **Connection Encryption**: All connections use TLS
- **Credential Management**: Environment variable based configuration

### **Query Safety**
- **Parameterized Queries**: All queries use parameter binding
- **Input Validation**: Repository layer validates all inputs
- **Error Handling**: Secure error messages without sensitive data

## 📈 **Monitoring & Health Checks**

### **Health Check Endpoint**
```python
from core.database import get_database_manager

db = await get_database_manager()
health = await db.health_check()

# Returns:
{
    'supabase_healthy': True,
    'postgresql_healthy': True, 
    'pool_size': 10,
    'pool_free': 8,
    'timestamp': '2024-01-01T12:00:00Z'
}
```

### **Performance Metrics**
- **Connection Pool Usage**: Monitor active/idle connections
- **Query Performance**: Track query execution times
- **Error Rates**: Monitor database operation failures
- **Schema Validation**: Regular schema health checks

## 🛠️ **Development Workflow**

### **1. Schema Changes**
```bash
# Create migration
python -c "
from core.database import MigrationManager
mgr = MigrationManager()
mgr.create_migration_file('add_new_table', '''
CREATE TABLE new_table (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);
''')
"

# Apply migration
python -c "
import asyncio
from core.database import MigrationManager
async def apply():
    mgr = MigrationManager()
    result = await mgr.apply_migrations()
    print(result)
asyncio.run(apply())
"
```

### **2. Testing**
```python
# Test database operations
from core.database import MemoryRepository

async def test_memory():
    repo = MemoryRepository()
    success = await repo.set_memory("test", "value")
    assert success
    
    memory = await repo.get_memory("test")
    assert memory['value'] == "value"
```

### **3. Backup & Recovery**
```python
# Backup schema
from core.database import SchemaManager

schema_manager = SchemaManager()
backup_file = await schema_manager.backup_schema()
print(f"Schema backed up to: {backup_file}")
```

## 🎯 **Best Practices**

### **1. Use Repository Pattern**
- Encapsulate database logic in repositories
- Keep business logic separate from data access
- Use type hints for better IDE support

### **2. Handle Errors Gracefully**
- Always handle database exceptions
- Log errors with appropriate detail levels
- Provide meaningful error messages to users

### **3. Optimize Vector Operations**
- Use direct PostgreSQL access for vector searches
- Batch embedding operations when possible
- Cache frequently accessed embeddings

### **4. Monitor Performance**
- Regular health checks
- Monitor connection pool usage
- Track query performance metrics

### **5. Schema Management**
- Use migrations for schema changes
- Validate schema regularly
- Backup before major changes

## 🔧 **Configuration**

### **Environment Variables**
```env
# Required
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# Optional (for direct PostgreSQL access)
SUPABASE_PWD=your-database-password

# Connection Pool Settings (optional)
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=10
DB_POOL_TIMEOUT=60
```

### **Feature Flags**
```python
# Disable PostgreSQL pool (fallback to Supabase only)
DISABLE_PG_POOL=true

# Enable verbose logging
DB_DEBUG_MODE=true

# Enable schema auto-migration
AUTO_MIGRATE_SCHEMA=true
```

This new database management system provides a robust, scalable foundation for your MCP server while maintaining full backward compatibility with existing code. 