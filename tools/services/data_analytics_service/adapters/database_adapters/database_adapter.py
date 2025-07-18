#!/usr/bin/env python3
"""
Database Adapter for Data Analytics Service

Provides unified interface for database connections and operations.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from .base_adapter import BaseAdapter
from ..models.interfaces import IDataSource, IDataTarget
from ..models.data_models import (
    DataSource, DataTarget, DataSchema, DataRecord, 
    QueryRequest, QueryResult, DataSourceType, QueryType
)

logger = logging.getLogger(__name__)

class DatabaseAdapter(BaseAdapter, IDataSource, IDataTarget):
    """
    Database adapter for various database systems
    
    Supports PostgreSQL, MySQL, SQLite, and other SQL databases
    through a unified interface.
    """
    
    def __init__(self, db_type: str = "postgresql"):
        super().__init__(f"database_{db_type}", "database")
        self.db_type = db_type
        self.connection_pool = None
        self.schema_cache: Dict[str, DataSchema] = {}
        
    async def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate database configuration"""
        required_keys = ['host', 'database', 'username']
        
        # Check required keys
        for key in required_keys:
            if key not in config:
                self.logger.error(f"Missing required configuration key: {key}")
                return False
        
        # Validate port if provided
        if 'port' in config:
            try:
                port = int(config['port'])
                if not (1 <= port <= 65535):
                    self.logger.error(f"Invalid port number: {port}")
                    return False
            except ValueError:
                self.logger.error(f"Port must be a number: {config['port']}")
                return False
        
        return True
    
    async def _initialize_adapter(self) -> None:
        """Initialize database connection"""
        try:
            # Create connection pool based on database type
            if self.db_type == "postgresql":
                await self._initialize_postgresql()
            elif self.db_type == "mysql":
                await self._initialize_mysql()
            elif self.db_type == "sqlite":
                await self._initialize_sqlite()
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
                
            self.logger.info(f"Database connection pool initialized for {self.db_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    async def _initialize_postgresql(self) -> None:
        """Initialize PostgreSQL connection pool"""
        try:
            import asyncpg
            
            # Build connection string
            connection_string = (
                f"postgresql://{self.config['username']}:{self.config.get('password', '')}"
                f"@{self.config['host']}:{self.config.get('port', 5432)}"
                f"/{self.config['database']}"
            )
            
            # Create connection pool
            self.connection_pool = await asyncpg.create_pool(
                connection_string,
                min_size=1,
                max_size=10,
                command_timeout=30
            )
            
        except ImportError:
            raise ImportError("asyncpg is required for PostgreSQL support")
        except Exception as e:
            raise RuntimeError(f"Failed to create PostgreSQL connection pool: {e}")
    
    async def _initialize_mysql(self) -> None:
        """Initialize MySQL connection pool"""
        try:
            import aiomysql
            
            # Create connection pool
            self.connection_pool = await aiomysql.create_pool(
                host=self.config['host'],
                port=self.config.get('port', 3306),
                user=self.config['username'],
                password=self.config.get('password', ''),
                db=self.config['database'],
                minsize=1,
                maxsize=10,
                autocommit=True
            )
            
        except ImportError:
            raise ImportError("aiomysql is required for MySQL support")
        except Exception as e:
            raise RuntimeError(f"Failed to create MySQL connection pool: {e}")
    
    async def _initialize_sqlite(self) -> None:
        """Initialize SQLite connection"""
        try:
            import aiosqlite
            
            # For SQLite, we'll create connections on demand
            # Test the connection
            async with aiosqlite.connect(self.config['database']) as conn:
                await conn.execute("SELECT 1")
                
        except ImportError:
            raise ImportError("aiosqlite is required for SQLite support")
        except Exception as e:
            raise RuntimeError(f"Failed to test SQLite connection: {e}")
    
    async def _perform_health_check(self) -> bool:
        """Perform database health check"""
        try:
            if self.db_type == "sqlite":
                import aiosqlite
                async with aiosqlite.connect(self.config['database']) as conn:
                    await conn.execute("SELECT 1")
                    return True
            else:
                # For pooled connections
                if not self.connection_pool:
                    return False
                
                async with self.connection_pool.acquire() as conn:
                    if self.db_type == "postgresql":
                        await conn.fetchval("SELECT 1")
                    elif self.db_type == "mysql":
                        async with conn.cursor() as cursor:
                            await cursor.execute("SELECT 1")
                            await cursor.fetchone()
                    return True
                    
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False
    
    def _get_specific_capabilities(self) -> Dict[str, Any]:
        """Get database-specific capabilities"""
        return {
            'database_type': self.db_type,
            'supports_transactions': True,
            'supports_schemas': self.db_type in ['postgresql', 'mysql'],
            'supports_json': self.db_type in ['postgresql', 'mysql'],
            'max_connections': 10,
            'query_timeout': 30,
            'cached_schemas': list(self.schema_cache.keys())
        }
    
    # IDataSource implementation
    
    async def connect(self) -> bool:
        """Establish connection to database"""
        if not self.is_initialized:
            return await self.initialize(self.config)
        return True
    
    async def disconnect(self) -> bool:
        """Close database connection"""
        try:
            if self.connection_pool:
                self.connection_pool.close()
                await self.connection_pool.wait_closed()
                self.connection_pool = None
            
            self.is_initialized = False
            return True
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from database: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test database connection"""
        return await self.health_check()
    
    async def get_schema(self) -> DataSchema:
        """Get database schema"""
        return await self._execute_with_stats(
            "get_schema",
            self._extract_schema
        )
    
    async def _extract_schema(self) -> DataSchema:
        """Extract database schema"""
        try:
            self._ensure_initialized()
            
            # Check cache first
            cache_key = f"{self.db_type}_{self.config['database']}"
            if cache_key in self.schema_cache:
                return self.schema_cache[cache_key]
            
            # Extract schema based on database type
            if self.db_type == "postgresql":
                schema = await self._extract_postgresql_schema()
            elif self.db_type == "mysql":
                schema = await self._extract_mysql_schema()
            elif self.db_type == "sqlite":
                schema = await self._extract_sqlite_schema()
            else:
                raise ValueError(f"Schema extraction not supported for {self.db_type}")
            
            # Cache the schema
            self.schema_cache[cache_key] = schema
            return schema
            
        except Exception as e:
            self.logger.error(f"Failed to extract schema: {e}")
            raise
    
    async def _extract_postgresql_schema(self) -> DataSchema:
        """Extract PostgreSQL schema"""
        async with self.connection_pool.acquire() as conn:
            # Get tables and columns
            tables_query = """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """
            
            rows = await conn.fetch(tables_query)
            
            # Process results
            tables = {}
            for row in rows:
                table_name = row['table_name']
                if table_name not in tables:
                    tables[table_name] = []
                
                tables[table_name].append({
                    'name': row['column_name'],
                    'type': row['data_type'],
                    'nullable': row['is_nullable'] == 'YES'
                })
            
            # Convert to schema format
            fields = []
            for table_name, columns in tables.items():
                for column in columns:
                    fields.append({
                        'name': f"{table_name}.{column['name']}",
                        'type': column['type'],
                        'table': table_name,
                        'nullable': column['nullable']
                    })
            
            return DataSchema(
                name=self.config['database'],
                fields=fields,
                metadata={
                    'database_type': self.db_type,
                    'tables': list(tables.keys()),
                    'extracted_at': datetime.now().isoformat()
                }
            )
    
    async def _extract_mysql_schema(self) -> DataSchema:
        """Extract MySQL schema"""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Get tables and columns
                await cursor.execute("""
                    SELECT table_name, column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = %s
                    ORDER BY table_name, ordinal_position
                """, (self.config['database'],))
                
                rows = await cursor.fetchall()
                
                # Process results (similar to PostgreSQL)
                tables = {}
                for row in rows:
                    table_name = row[0]
                    if table_name not in tables:
                        tables[table_name] = []
                    
                    tables[table_name].append({
                        'name': row[1],
                        'type': row[2],
                        'nullable': row[3] == 'YES'
                    })
                
                # Convert to schema format
                fields = []
                for table_name, columns in tables.items():
                    for column in columns:
                        fields.append({
                            'name': f"{table_name}.{column['name']}",
                            'type': column['type'],
                            'table': table_name,
                            'nullable': column['nullable']
                        })
                
                return DataSchema(
                    name=self.config['database'],
                    fields=fields,
                    metadata={
                        'database_type': self.db_type,
                        'tables': list(tables.keys()),
                        'extracted_at': datetime.now().isoformat()
                    }
                )
    
    async def _extract_sqlite_schema(self) -> DataSchema:
        """Extract SQLite schema"""
        import aiosqlite
        
        async with aiosqlite.connect(self.config['database']) as conn:
            # Get table names
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = await cursor.fetchall()
            
            fields = []
            table_names = []
            
            for (table_name,) in tables:
                table_names.append(table_name)
                
                # Get column info for each table
                cursor = await conn.execute(f"PRAGMA table_info({table_name})")
                columns = await cursor.fetchall()
                
                for column in columns:
                    fields.append({
                        'name': f"{table_name}.{column[1]}",
                        'type': column[2],
                        'table': table_name,
                        'nullable': column[3] == 0
                    })
            
            return DataSchema(
                name=self.config['database'],
                fields=fields,
                metadata={
                    'database_type': self.db_type,
                    'tables': table_names,
                    'extracted_at': datetime.now().isoformat()
                }
            )
    
    async def execute_query(self, query: QueryRequest) -> QueryResult:
        """Execute query against database"""
        return await self._execute_with_stats(
            "execute_query",
            self._execute_sql_query,
            query
        )
    
    async def _execute_sql_query(self, query: QueryRequest) -> QueryResult:
        """Execute SQL query"""
        try:
            self._ensure_initialized()
            
            if query.query_type != QueryType.SQL:
                raise ValueError(f"Database adapter only supports SQL queries, got {query.query_type}")
            
            # Execute query based on database type
            if self.db_type == "postgresql":
                return await self._execute_postgresql_query(query)
            elif self.db_type == "mysql":
                return await self._execute_mysql_query(query)
            elif self.db_type == "sqlite":
                return await self._execute_sqlite_query(query)
            else:
                raise ValueError(f"Query execution not supported for {self.db_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to execute query: {e}")
            return QueryResult(
                request_id=query.request_id,
                success=False,
                data=[],
                error=str(e)
            )
    
    async def _execute_postgresql_query(self, query: QueryRequest) -> QueryResult:
        """Execute PostgreSQL query"""
        async with self.connection_pool.acquire() as conn:
            try:
                # Apply limit and offset
                sql = query.query
                if query.limit:
                    sql += f" LIMIT {query.limit}"
                if query.offset:
                    sql += f" OFFSET {query.offset}"
                
                rows = await conn.fetch(sql)
                
                # Convert to list of dictionaries
                data = [dict(row) for row in rows]
                
                return QueryResult(
                    request_id=query.request_id,
                    success=True,
                    data=data,
                    total_count=len(data),
                    metadata={
                        'database_type': self.db_type,
                        'query_type': query.query_type.value,
                        'executed_at': datetime.now().isoformat()
                    }
                )
                
            except Exception as e:
                raise RuntimeError(f"PostgreSQL query failed: {e}")
    
    async def _execute_mysql_query(self, query: QueryRequest) -> QueryResult:
        """Execute MySQL query"""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    # Apply limit and offset
                    sql = query.query
                    if query.limit:
                        sql += f" LIMIT {query.limit}"
                    if query.offset:
                        sql += f" OFFSET {query.offset}"
                    
                    await cursor.execute(sql)
                    rows = await cursor.fetchall()
                    
                    # Get column names
                    columns = [desc[0] for desc in cursor.description]
                    
                    # Convert to list of dictionaries
                    data = [dict(zip(columns, row)) for row in rows]
                    
                    return QueryResult(
                        request_id=query.request_id,
                        success=True,
                        data=data,
                        total_count=len(data),
                        metadata={
                            'database_type': self.db_type,
                            'query_type': query.query_type.value,
                            'executed_at': datetime.now().isoformat()
                        }
                    )
                    
                except Exception as e:
                    raise RuntimeError(f"MySQL query failed: {e}")
    
    async def _execute_sqlite_query(self, query: QueryRequest) -> QueryResult:
        """Execute SQLite query"""
        import aiosqlite
        
        async with aiosqlite.connect(self.config['database']) as conn:
            try:
                # Apply limit and offset
                sql = query.query
                if query.limit:
                    sql += f" LIMIT {query.limit}"
                if query.offset:
                    sql += f" OFFSET {query.offset}"
                
                cursor = await conn.execute(sql)
                rows = await cursor.fetchall()
                
                # Get column names
                columns = [desc[0] for desc in cursor.description]
                
                # Convert to list of dictionaries
                data = [dict(zip(columns, row)) for row in rows]
                
                return QueryResult(
                    request_id=query.request_id,
                    success=True,
                    data=data,
                    total_count=len(data),
                    metadata={
                        'database_type': self.db_type,
                        'query_type': query.query_type.value,
                        'executed_at': datetime.now().isoformat()
                    }
                )
                
            except Exception as e:
                raise RuntimeError(f"SQLite query failed: {e}")
    
    # IDataTarget implementation
    
    async def write_data(self, data: List[DataRecord]) -> bool:
        """Write data to database"""
        return await self._execute_with_stats(
            "write_data",
            self._write_data_to_db,
            data
        )
    
    async def _write_data_to_db(self, data: List[DataRecord]) -> bool:
        """Write data records to database"""
        try:
            self._ensure_initialized()
            
            if not data:
                return True
            
            # Group data by schema/table
            tables = {}
            for record in data:
                table_name = record.schema_name or 'default_table'
                if table_name not in tables:
                    tables[table_name] = []
                tables[table_name].append(record)
            
            # Write data for each table
            for table_name, records in tables.items():
                await self._write_table_data(table_name, records)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write data: {e}")
            return False
    
    async def _write_table_data(self, table_name: str, records: List[DataRecord]) -> None:
        """Write records to specific table"""
        if not records:
            return
        
        # Get column names from first record
        columns = list(records[0].data.keys())
        
        if self.db_type == "postgresql":
            await self._write_postgresql_data(table_name, columns, records)
        elif self.db_type == "mysql":
            await self._write_mysql_data(table_name, columns, records)
        elif self.db_type == "sqlite":
            await self._write_sqlite_data(table_name, columns, records)
    
    async def _write_postgresql_data(self, table_name: str, columns: List[str], records: List[DataRecord]) -> None:
        """Write data to PostgreSQL"""
        async with self.connection_pool.acquire() as conn:
            # Prepare values
            values = []
            for record in records:
                values.append([record.data.get(col) for col in columns])
            
            # Build INSERT query
            placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            # Execute batch insert
            await conn.executemany(query, values)
    
    async def _write_mysql_data(self, table_name: str, columns: List[str], records: List[DataRecord]) -> None:
        """Write data to MySQL"""
        async with self.connection_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Prepare values
                values = []
                for record in records:
                    values.append([record.data.get(col) for col in columns])
                
                # Build INSERT query
                placeholders = ', '.join(['%s'] * len(columns))
                query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                
                # Execute batch insert
                await cursor.executemany(query, values)
    
    async def _write_sqlite_data(self, table_name: str, columns: List[str], records: List[DataRecord]) -> None:
        """Write data to SQLite"""
        import aiosqlite
        
        async with aiosqlite.connect(self.config['database']) as conn:
            # Prepare values
            values = []
            for record in records:
                values.append([record.data.get(col) for col in columns])
            
            # Build INSERT query
            placeholders = ', '.join(['?'] * len(columns))
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            # Execute batch insert
            await conn.executemany(query, values)
            await conn.commit()
    
    async def create_schema(self, schema: DataSchema) -> bool:
        """Create database schema"""
        return await self._execute_with_stats(
            "create_schema",
            self._create_db_schema,
            schema
        )
    
    async def _create_db_schema(self, schema: DataSchema) -> bool:
        """Create database schema"""
        try:
            self._ensure_initialized()
            
            # Group fields by table
            tables = {}
            for field in schema.fields:
                table_name = field.get('table', 'default_table')
                if table_name not in tables:
                    tables[table_name] = []
                tables[table_name].append(field)
            
            # Create tables
            for table_name, fields in tables.items():
                await self._create_table(table_name, fields)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create schema: {e}")
            return False
    
    async def _create_table(self, table_name: str, fields: List[Dict[str, Any]]) -> None:
        """Create database table"""
        # Build CREATE TABLE query
        column_definitions = []
        for field in fields:
            column_name = field['name'].split('.')[-1]  # Remove table prefix
            column_type = self._map_type_to_db(field['type'])
            nullable = "NULL" if field.get('nullable', True) else "NOT NULL"
            column_definitions.append(f"{column_name} {column_type} {nullable}")
        
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_definitions)})"
        
        # Execute based on database type
        if self.db_type == "postgresql":
            async with self.connection_pool.acquire() as conn:
                await conn.execute(query)
        elif self.db_type == "mysql":
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query)
        elif self.db_type == "sqlite":
            import aiosqlite
            async with aiosqlite.connect(self.config['database']) as conn:
                await conn.execute(query)
                await conn.commit()
    
    def _map_type_to_db(self, field_type: str) -> str:
        """Map generic type to database-specific type"""
        type_mapping = {
            'postgresql': {
                'string': 'TEXT',
                'integer': 'INTEGER',
                'float': 'REAL',
                'boolean': 'BOOLEAN',
                'date': 'DATE',
                'datetime': 'TIMESTAMP',
                'json': 'JSONB'
            },
            'mysql': {
                'string': 'TEXT',
                'integer': 'INT',
                'float': 'FLOAT',
                'boolean': 'BOOLEAN',
                'date': 'DATE',
                'datetime': 'DATETIME',
                'json': 'JSON'
            },
            'sqlite': {
                'string': 'TEXT',
                'integer': 'INTEGER',
                'float': 'REAL',
                'boolean': 'INTEGER',
                'date': 'TEXT',
                'datetime': 'TEXT',
                'json': 'TEXT'
            }
        }
        
        return type_mapping.get(self.db_type, {}).get(field_type.lower(), 'TEXT') 