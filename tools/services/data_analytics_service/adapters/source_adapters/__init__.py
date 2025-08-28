#!/usr/bin/env python3
"""
Database adapters for different database types
"""

from .base_adapter import DatabaseAdapter
# Temporarily comment out specific adapters due to import issues
# from .postgresql_adapter import PostgreSQLAdapter
# from .mysql_adapter import MySQLAdapter
# from .sqlserver_adapter import SQLServerAdapter

# Common databases - commented out
# from .oracle_adapter import OracleAdapter
# from .mongodb_adapter import MongoDBAdapter
# from .redis_adapter import RedisAdapter
# from .elasticsearch_adapter import ElasticsearchAdapter

# Data warehouses - commented out
# from .snowflake_adapter import SnowflakeAdapter
# from .bigquery_adapter import BigQueryAdapter
# from .clickhouse_adapter import ClickHouseAdapter

# Data lakes - commented out
# from .deltalake_adapter import DeltaLakeAdapter
# from .s3_adapter import S3Adapter

# Create minimal stub classes for compatibility
class PostgreSQLAdapter(DatabaseAdapter):
    pass

class MySQLAdapter(DatabaseAdapter):
    pass

class SQLServerAdapter(DatabaseAdapter):
    pass

__all__ = [
    # Base and traditional databases
    "DatabaseAdapter",
    "PostgreSQLAdapter",
    "MySQLAdapter", 
    "SQLServerAdapter",
    
    # Common databases - commented out
    # "OracleAdapter",
    # "MongoDBAdapter", 
    # "RedisAdapter",
    # "ElasticsearchAdapter",
    
    # Data warehouses - commented out
    # "SnowflakeAdapter",
    # "BigQueryAdapter",
    # "ClickHouseAdapter",
    
    # Data lakes - commented out
    # "DeltaLakeAdapter",
    # "S3Adapter"
]