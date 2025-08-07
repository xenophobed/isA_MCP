"""
Professional DuckDB Service for MCP Resources
Enterprise-grade DuckDB service designed for MCP resource systems

Main Components:
- core.py: Core service classes and connection pool management
- mcp_resource.py: MCP resource interface implementation
- monitoring.py: Monitoring and metrics system
- config.py: Configuration management system
- tests.py: Comprehensive unit test suite

Key Features:
✅ Connection Pool Management
✅ Concurrency Control
✅ Transaction Management
✅ Security & Access Control
✅ Performance Monitoring
✅ Polars/Pandas Integration
✅ MCP Resource Interface
✅ Configuration Management
✅ Comprehensive Test Coverage

Usage:
```python
from resources.dbs.duckdb import (
    DuckDBService, initialize_duckdb_service,
    DuckDBResourceProvider, get_duckdb_resource_provider,
    load_config, Environment
)

# Load configuration
config = load_config(Environment.DEVELOPMENT)

# Initialize service
service = await initialize_duckdb_service(
    config.database, config.pool, config.security
)

# Initialize MCP resource provider
provider = get_duckdb_resource_provider(service)

# Execute queries
result = service.execute_query("SELECT 1 as test")
df = service.execute_query_df("SELECT * FROM my_table")

# Use transactions
with service.transaction() as conn:
    conn.execute("INSERT INTO table VALUES (?)", [value])
```

Architecture:
```
DuckDBService (core.py)
├── ConnectionPool - Connection pool management
├── ManagedConnection - Managed connections
├── SecurityConfig - Security configuration
├── DataFrameAdapter - DataFrame adapters
└── Transaction Management - Transaction management

DuckDBResourceProvider (mcp_resource.py)
├── MCP Resource Interface - MCP resource interface
├── Query Caching - Query caching
├── Multiple Export Formats - Multiple export formats
└── Error Handling - Error handling

DuckDBMonitor (monitoring.py)
├── QueryMonitor - Query monitoring
├── HealthChecker - Health checking
├── AlertManager - Alert management
└── Metrics Collection - Metrics collection

ConfigManager (config.py)
├── Multi-Environment Support - Multi-environment support
├── Configuration Validation - Configuration validation
├── Environment Variables - Environment variables
└── Encryption Support - Encryption support
```

Performance Features:
- Connection pooling with configurable min/max connections
- Query result caching with TTL
- Concurrent query execution support
- Health monitoring and automatic recovery
- Resource usage tracking and alerts

Security Features:
- SQL injection prevention
- Function blacklisting/whitelisting
- Access level control (READ_ONLY, READ_WRITE, ADMIN)
- Audit logging
- Configuration encryption
"""

from .core import (
    DuckDBService,
    ConnectionConfig,
    PoolConfig, 
    SecurityConfig,
    AccessLevel,
    TransactionIsolation,
    get_duckdb_service,
    initialize_duckdb_service
)

from .mcp_resource import (
    DuckDBResourceProvider,
    get_duckdb_resource_provider
)

from .monitoring import (
    DuckDBMonitor,
    get_duckdb_monitor,
    AlertLevel,
    MetricType
)

from .config import (
    DuckDBServiceConfig,
    DatabaseConfig,
    ConfigManager,
    Environment,
    LogLevel,
    load_config,
    get_config_manager,
    get_current_config
)

__version__ = "1.0.0"
__author__ = "DuckDB MCP Service Team"

__all__ = [
    # Core service
    "DuckDBService",
    "ConnectionConfig", 
    "PoolConfig",
    "SecurityConfig",
    "AccessLevel",
    "TransactionIsolation",
    "get_duckdb_service",
    "initialize_duckdb_service",
    
    # MCP resource interface
    "DuckDBResourceProvider",
    "get_duckdb_resource_provider",
    
    # Monitoring
    "DuckDBMonitor", 
    "get_duckdb_monitor",
    "AlertLevel",
    "MetricType",
    
    # Configuration
    "DuckDBServiceConfig",
    "DatabaseConfig",
    "ConfigManager",
    "Environment",
    "LogLevel", 
    "load_config",
    "get_config_manager",
    "get_current_config",
]