#!/usr/bin/env python3
"""
PostgreSQL database adapter
"""

import json
from typing import Dict, List, Any, Optional
from .base_adapter import DatabaseAdapter
from ...core.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL database adapter"""
    
    def __init__(self):
        super().__init__()
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 is required for PostgreSQL adapter. Install with: pip install psycopg2-binary")
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create PostgreSQL connection"""
        connection = psycopg2.connect(
            host=config['host'],
            port=config.get('port', 5432),
            database=config['database'],
            user=config['username'],
            password=config['password'],
            connect_timeout=config.get('timeout', 30)
        )
        self.cursor = connection.cursor(cursor_factory=RealDictCursor)
        return connection
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute PostgreSQL query"""
        try:
            self.cursor.execute(query, params)
            
            # Handle queries that don't return results
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
                self.connection.commit()
                return []
            
            # Fetch results for SELECT queries
            results = self.cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            raise e
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get PostgreSQL table information"""
        schema_condition = ""
        if schema_filter:
            schema_list = "','".join(schema_filter)
            schema_condition = f"AND t.table_schema IN ('{schema_list}')"
        
        query = f"""
        SELECT 
            t.table_name,
            t.table_schema,
            t.table_type,
            COALESCE(c.reltuples::bigint, 0) as record_count,
            COALESCE(obj_description(c.oid), '') as table_comment,
            '' as created_date,
            '' as last_modified
        FROM information_schema.tables t
        LEFT JOIN pg_class c ON c.relname = t.table_name
        LEFT JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
        WHERE t.table_type = 'BASE TABLE'
        AND t.table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        {schema_condition}
        ORDER BY t.table_schema, t.table_name
        """
        
        results = self._execute_query(query)
        
        tables = []
        for row in results:
            tables.append(TableInfo(
                table_name=row['table_name'],
                schema_name=row['table_schema'],
                table_type=row['table_type'],
                record_count=row['record_count'] or 0,
                table_comment=row['table_comment'] or '',
                created_date=row['created_date'] or '',
                last_modified=row['last_modified'] or ''
            ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get PostgreSQL column information"""
        table_condition = ""
        if table_name:
            table_condition = f"AND c.table_name = '{table_name}'"
        
        query = f"""
        SELECT 
            c.table_name,
            c.column_name,
            c.data_type,
            COALESCE(c.character_maximum_length, c.numeric_precision, 0) as max_length,
            CASE WHEN c.is_nullable = 'YES' THEN true ELSE false END as is_nullable,
            COALESCE(c.column_default, '') as default_value,
            COALESCE(col_description(pgc.oid, c.ordinal_position), '') as column_comment,
            c.ordinal_position
        FROM information_schema.columns c
        LEFT JOIN pg_class pgc ON pgc.relname = c.table_name
        LEFT JOIN pg_namespace pgn ON pgn.oid = pgc.relnamespace AND pgn.nspname = c.table_schema
        WHERE c.table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        {table_condition}
        ORDER BY c.table_name, c.ordinal_position
        """
        
        results = self._execute_query(query)
        
        columns = []
        for row in results:
            columns.append(ColumnInfo(
                table_name=row['table_name'],
                column_name=row['column_name'],
                data_type=row['data_type'],
                max_length=row['max_length'],
                is_nullable=row['is_nullable'],
                default_value=row['default_value'],
                column_comment=row['column_comment'],
                ordinal_position=row['ordinal_position']
            ))
        
        return columns
    
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get PostgreSQL foreign key relationships"""
        query = """
        SELECT
            tc.constraint_name,
            tc.table_name as from_table,
            kcu.column_name as from_column,
            ccu.table_name as to_table,
            ccu.column_name as to_column,
            tc.constraint_type
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu 
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        ORDER BY tc.table_name, tc.constraint_name
        """
        
        results = self._execute_query(query)
        
        relationships = []
        for row in results:
            relationships.append(RelationshipInfo(
                constraint_name=row['constraint_name'],
                from_table=row['from_table'],
                from_column=row['from_column'],
                to_table=row['to_table'],
                to_column=row['to_column'],
                constraint_type=row['constraint_type']
            ))
        
        return relationships
    
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Get PostgreSQL index information"""
        table_condition = ""
        if table_name:
            table_condition = f"AND t.relname = '{table_name}'"
        
        query = f"""
        SELECT
            i.relname as index_name,
            t.relname as table_name,
            array_agg(a.attname ORDER BY c.ordinality) as column_names,
            ix.indisunique as is_unique,
            am.amname as index_type,
            ix.indisprimary as is_primary
        FROM pg_class t
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_am am ON i.relam = am.oid
        JOIN unnest(ix.indkey) WITH ORDINALITY AS c(attnum, ordinality) ON true
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = c.attnum
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
        {table_condition}
        GROUP BY i.relname, t.relname, ix.indisunique, am.amname, ix.indisprimary
        ORDER BY t.relname, i.relname
        """
        
        results = self._execute_query(query)
        
        indexes = []
        for row in results:
            indexes.append(IndexInfo(
                index_name=row['index_name'],
                table_name=row['table_name'],
                column_names=row['column_names'],
                is_unique=row['is_unique'],
                index_type=row['index_type'],
                is_primary=row['is_primary']
            ))
        
        return indexes
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze PostgreSQL data distribution"""
        try:
            # Basic statistics query
            stats_query = f"""
            SELECT 
                COUNT(*) as total_count,
                COUNT(DISTINCT "{column_name}") as unique_count,
                COUNT("{column_name}") as non_null_count,
                COUNT(*) - COUNT("{column_name}") as null_count
            FROM "{table_name}"
            """
            
            stats_result = self._execute_query(stats_query)
            if not stats_result:
                return {"error": "No data found"}
            
            stats = stats_result[0]
            
            # Sample data query with safety checks
            sample_query = f"""
            SELECT "{column_name}" 
            FROM "{table_name}" 
            WHERE "{column_name}" IS NOT NULL 
            ORDER BY RANDOM() 
            LIMIT {min(sample_size, 100)}
            """
            
            sample_results = self._execute_query(sample_query)
            sample_values = [row[column_name] for row in sample_results]
            
            # Calculate percentages
            total_count = stats['total_count']
            null_percentage = stats['null_count'] / total_count if total_count > 0 else 0
            unique_percentage = stats['unique_count'] / stats['non_null_count'] if stats['non_null_count'] > 0 else 0
            
            return {
                "total_count": total_count,
                "unique_count": stats['unique_count'],
                "null_count": stats['null_count'],
                "null_percentage": round(null_percentage, 4),
                "unique_percentage": round(unique_percentage, 4),
                "sample_values": sample_values[:10]  # Limit sample display
            }
        
        except Exception as e:
            return {"error": str(e), "analysis_failed": True}
    
    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from PostgreSQL table"""
        try:
            query = f'SELECT * FROM "{table_name}" LIMIT {limit}'
            return self._execute_query(query)
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_table_size(self, table_name: str) -> Dict[str, Any]:
        """Get PostgreSQL table size information"""
        try:
            query = f"""
            SELECT
                pg_size_pretty(pg_total_relation_size('"{table_name}"')) as total_size,
                pg_size_pretty(pg_relation_size('"{table_name}"')) as table_size,
                pg_size_pretty(pg_total_relation_size('"{table_name}"') - pg_relation_size('"{table_name}"')) as index_size
            """
            
            result = self._execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            return {"error": str(e)}
    
    def get_database_version(self) -> str:
        """Get PostgreSQL version"""
        try:
            result = self._execute_query("SELECT version()")
            return result[0]['version'] if result else "Unknown"
        except Exception:
            return "Unknown"