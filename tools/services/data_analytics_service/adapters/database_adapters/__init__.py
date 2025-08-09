#!/usr/bin/env python3
"""
Database adapters for different database types
"""

from .base_adapter import DatabaseAdapter
from .postgresql_adapter import PostgreSQLAdapter
from .mysql_adapter import MySQLAdapter
from .sqlserver_adapter import SQLServerAdapter

# Common databases
from .oracle_adapter import OracleAdapter
from .mongodb_adapter import MongoDBAdapter
from .redis_adapter import RedisAdapter
from .elasticsearch_adapter import ElasticsearchAdapter

# Data warehouses
from .snowflake_adapter import SnowflakeAdapter
from .bigquery_adapter import BigQueryAdapter
from .clickhouse_adapter import ClickHouseAdapter

# Data lakes
from .deltalake_adapter import DeltaLakeAdapter
from .s3_adapter import S3Adapter

__all__ = [
    # Base and traditional databases
    "DatabaseAdapter",
    "PostgreSQLAdapter",
    "MySQLAdapter", 
    "SQLServerAdapter",
    
    # Common databases
    "OracleAdapter",
    "MongoDBAdapter", 
    "RedisAdapter",
    "ElasticsearchAdapter",
    
    # Data warehouses
    "SnowflakeAdapter",
    "BigQueryAdapter",
    "ClickHouseAdapter",
    
    # Data lakes
    "DeltaLakeAdapter",
    "S3Adapter"
]