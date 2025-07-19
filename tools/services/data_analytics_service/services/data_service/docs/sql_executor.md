# SQL Executor Service

## Overview
Step 6 of the data analytics pipeline: Executes SQL queries with intelligent fallback mechanisms, error handling, and performance optimization.

## Architecture
- Multi-database support (PostgreSQL, MySQL, SQLite, SQL Server)
- Intelligent fallback strategies for failed queries
- Performance monitoring and optimization suggestions
- Execution history tracking for continuous learning

## Key Functions

### `execute_sql_with_fallbacks(sql_generation_result, original_query)`

**Input:**
- `sql_generation_result` (SQLGenerationResult): Pre-generated SQL from SQL Generator
- `original_query` (str): Original natural language query (for logging)

**Output:**
- `execution_result` (ExecutionResult): Query execution results
- `fallback_attempts` (List[FallbackAttempt]): Details of any fallback attempts

**Example:**
```python
result, fallbacks = await executor.execute_sql_with_fallbacks(
    sql_generation_result, 
    "Show customers with high sales"
)

# result.success = True
# result.data = [{'customer_name': 'John Doe', 'total_sales': 1500.00}, ...]
# result.row_count = 25
# result.execution_time_ms = 45.2
# fallbacks = []  # No fallbacks needed
```

### `execute_sql_directly(sql)`

**Input:**
- `sql` (str): SQL query to execute directly

**Output:**
- `execution_result` (ExecutionResult): Query execution results

**Example:**
```python
result = await executor.execute_sql_directly("SELECT * FROM customers LIMIT 10")

# result.success = True
# result.data = [{'customer_id': 1, 'customer_name': 'John'}, ...]
# result.column_names = ['customer_id', 'customer_name']
```

### `validate_sql(sql, semantic_metadata)`

**Input:**
- `sql` (str): SQL query to validate
- `semantic_metadata` (SemanticMetadata): Available metadata for validation

**Output:**
- `validation_result` (Dict): Validation status and suggestions

**Example:**
```python
validation = await executor.validate_sql(
    "SELECT * FROM customers WHERE customer_id = 1",
    semantic_metadata
)

# validation['is_valid'] = True
# validation['errors'] = []
# validation['warnings'] = []
# validation['suggestions'] = ['Consider adding index on customer_id']
```

### `optimize_query(sql, semantic_metadata)`

**Input:**
- `sql` (str): SQL query to optimize
- `semantic_metadata` (SemanticMetadata): Available metadata

**Output:**
- `optimization_result` (Dict): Optimized SQL and suggestions

**Example:**
```python
optimization = await executor.optimize_query(
    "SELECT * FROM customers WHERE status = 'active'",
    semantic_metadata
)

# optimization['optimized_sql'] = "SELECT * FROM customers WHERE status = 'active' LIMIT 1000"
# optimization['optimizations_applied'] = ['Added LIMIT clause']
# optimization['suggestions'] = ['Consider adding index on status']
```

## Database Support

### SQLite Helper
```python
# Create SQLite executor for testing
executor = SQLExecutor.create_sqlite_executor("customers.db", "user123")
```

### Multi-Database Configuration
```python
# PostgreSQL
config = {
    'type': 'postgresql',
    'host': 'localhost',
    'port': 5432,
    'database': 'mydb',
    'username': 'user',
    'password': 'pass'
}

# MySQL
config = {
    'type': 'mysql',
    'host': 'localhost',
    'port': 3306,
    'database': 'mydb',
    'username': 'user',
    'password': 'pass'
}

# SQLite
config = {
    'type': 'sqlite',
    'database': '/path/to/database.db'
}
```

## Fallback Strategies

The SQL Executor includes intelligent fallback mechanisms:

1. **Extended Timeout**: Retry with longer timeout
2. **Add Limit**: Add LIMIT clause to prevent large result sets
3. **Simplify Query**: Remove complex subqueries and functions
4. **Remove Joins**: Execute query on primary table only
5. **Alternative Tables**: Try alternative tables from metadata
6. **Alternative Columns**: Use available columns instead of missing ones
7. **Syntax Correction**: Attempt to fix common SQL syntax errors
8. **Basic Select**: Generate simple SELECT query as last resort

## Performance Features

### Execution Statistics
```python
stats = await executor.get_execution_statistics()

# stats['database_type'] = 'postgresql'
# stats['connection_status'] = 'connected'
# stats['database_info']['version'] = 'PostgreSQL 13.0'
```

### Query Plan Analysis
```python
plan = await executor.explain_query_plan(
    "SELECT * FROM customers WHERE customer_id = 1"
)

# plan['plan'] = [{'Node Type': 'Index Scan', 'Total Cost': 0.28, ...}]
```

## Usage
```python
from tools.services.data_analytics_service.services.data_service.sql_executor import SQLExecutor

# Initialize with database config
config = {
    'type': 'sqlite',
    'database': '/path/to/db.sqlite',
    'max_execution_time': 30,
    'max_rows': 10000
}
executor = SQLExecutor(config)

# Execute SQL with fallbacks
result, fallbacks = await executor.execute_sql_with_fallbacks(
    sql_generation_result,
    "Original user query"
)

# Handle results
if result.success:
    print(f"Found {result.row_count} rows")
    for row in result.data:
        print(row)
else:
    print(f"Query failed: {result.error_message}")
    print(f"Attempted {len(fallbacks)} fallback strategies")
```

## Error Handling

The service provides comprehensive error handling:
- Database connection failures
- SQL syntax errors
- Missing tables/columns
- Performance timeouts
- Large result set handling

All errors include detailed messages and suggested fixes through the fallback system.