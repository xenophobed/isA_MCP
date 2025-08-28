#!/usr/bin/env python3
"""
MySQL database adapter
"""

from typing import Dict, List, Any, Optional
from .base_adapter import DatabaseAdapter
from ...processors.data_processors.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

class MySQLAdapter(DatabaseAdapter):
    """MySQL database adapter"""
    
    def __init__(self):
        super().__init__()
        if not MYSQL_AVAILABLE:
            raise ImportError("mysql-connector-python is required for MySQL adapter. Install with: pip install mysql-connector-python")
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create MySQL connection"""
        connection = mysql.connector.connect(
            host=config['host'],
            port=config.get('port', 3306),
            database=config['database'],
            user=config['username'],
            password=config['password'],
            connection_timeout=config.get('timeout', 30),
            autocommit=True
        )
        self.cursor = connection.cursor(dictionary=True, buffered=True)
        return connection
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute MySQL query"""
        try:
            self.cursor.execute(query, params)
            
            # Handle queries that don't return results
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
                return []
            
            # Fetch results for SELECT queries
            results = self.cursor.fetchall()
            return results if results else []
        except Exception as e:
            raise e
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get MySQL table information"""
        schema_condition = ""
        if schema_filter:
            schema_list = "','".join(schema_filter)
            schema_condition = f"AND t.table_schema IN ('{schema_list}')"
        
        query = f"""
        SELECT 
            t.table_name,
            t.table_schema,
            t.table_type,
            COALESCE(t.table_rows, 0) as record_count,
            COALESCE(t.table_comment, '') as table_comment,
            COALESCE(t.create_time, '') as created_date,
            COALESCE(t.update_time, '') as last_modified
        FROM information_schema.tables t
        WHERE t.table_type = 'BASE TABLE'
        AND t.table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
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
                created_date=str(row['created_date']) if row['created_date'] else '',
                last_modified=str(row['last_modified']) if row['last_modified'] else ''
            ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get MySQL column information"""
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
            COALESCE(c.column_comment, '') as column_comment,
            c.ordinal_position
        FROM information_schema.columns c
        WHERE c.table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
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
        """Get MySQL foreign key relationships"""
        query = """
        SELECT
            kcu.constraint_name,
            kcu.table_name as from_table,
            kcu.column_name as from_column,
            kcu.referenced_table_name as to_table,
            kcu.referenced_column_name as to_column,
            'FOREIGN KEY' as constraint_type
        FROM information_schema.key_column_usage kcu
        WHERE kcu.referenced_table_name IS NOT NULL
        AND kcu.table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
        ORDER BY kcu.table_name, kcu.constraint_name
        """
        
        results = self._execute_query(query)
        
        relationships = []
        for row in results:
            if row['to_table']:  # Ensure we have a valid foreign key
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
        """Get MySQL index information"""
        table_condition = ""
        if table_name:
            table_condition = f"AND s.table_name = '{table_name}'"
        
        query = f"""
        SELECT
            s.index_name,
            s.table_name,
            GROUP_CONCAT(s.column_name ORDER BY s.seq_in_index) as column_names,
            CASE WHEN s.non_unique = 0 THEN true ELSE false END as is_unique,
            s.index_type,
            CASE WHEN s.index_name = 'PRIMARY' THEN true ELSE false END as is_primary
        FROM information_schema.statistics s
        WHERE s.table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
        {table_condition}
        GROUP BY s.table_name, s.index_name, s.non_unique, s.index_type
        ORDER BY s.table_name, s.index_name
        """
        
        results = self._execute_query(query)
        
        indexes = []
        for row in results:
            column_names = row['column_names'].split(',') if row['column_names'] else []
            indexes.append(IndexInfo(
                index_name=row['index_name'],
                table_name=row['table_name'],
                column_names=column_names,
                is_unique=row['is_unique'],
                index_type=row['index_type'],
                is_primary=row['is_primary']
            ))
        
        return indexes
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze MySQL data distribution"""
        try:
            # Basic statistics query
            stats_query = f"""
            SELECT 
                COUNT(*) as total_count,
                COUNT(DISTINCT `{column_name}`) as unique_count,
                COUNT(`{column_name}`) as non_null_count,
                COUNT(*) - COUNT(`{column_name}`) as null_count
            FROM `{table_name}`
            """
            
            stats_result = self._execute_query(stats_query)
            if not stats_result:
                return {"error": "No data found"}
            
            stats = stats_result[0]
            
            # Sample data query
            sample_query = f"""
            SELECT `{column_name}` 
            FROM `{table_name}` 
            WHERE `{column_name}` IS NOT NULL 
            ORDER BY RAND() 
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
                "sample_values": sample_values[:10]
            }
        
        except Exception as e:
            return {"error": str(e), "analysis_failed": True}
    
    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from MySQL table"""
        try:
            query = f"SELECT * FROM `{table_name}` LIMIT {limit}"
            return self._execute_query(query)
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_table_size(self, table_name: str) -> Dict[str, Any]:
        """Get MySQL table size information"""
        try:
            query = f"""
            SELECT
                ROUND(((data_length + index_length) / 1024 / 1024), 2) as 'total_size_mb',
                ROUND((data_length / 1024 / 1024), 2) as 'data_size_mb',
                ROUND((index_length / 1024 / 1024), 2) as 'index_size_mb',
                table_rows
            FROM information_schema.tables 
            WHERE table_name = '{table_name}'
            AND table_schema = DATABASE()
            """
            
            result = self._execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            return {"error": str(e)}
    
    def get_database_version(self) -> str:
        """Get MySQL version"""
        try:
            result = self._execute_query("SELECT VERSION() as version")
            return result[0]['version'] if result else "Unknown"
        except Exception:
            return "Unknown"