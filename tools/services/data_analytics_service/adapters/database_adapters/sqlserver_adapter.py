#!/usr/bin/env python3
"""
SQL Server database adapter
"""

from typing import Dict, List, Any, Optional
from .base_adapter import DatabaseAdapter
from ...core.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False

class SQLServerAdapter(DatabaseAdapter):
    """SQL Server database adapter"""
    
    def __init__(self):
        super().__init__()
        if not PYODBC_AVAILABLE:
            raise ImportError("pyodbc is required for SQL Server adapter. Install with: pip install pyodbc")
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create SQL Server connection"""
        driver = config.get('driver', 'ODBC Driver 17 for SQL Server')
        connection_string = f"""
        DRIVER={{{driver}}};
        SERVER={config['host']},{config.get('port', 1433)};
        DATABASE={config['database']};
        UID={config['username']};
        PWD={config['password']};
        TIMEOUT={config.get('timeout', 30)};
        """
        
        connection = pyodbc.connect(connection_string)
        self.cursor = connection.cursor()
        return connection
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute SQL Server query"""
        try:
            self.cursor.execute(query, params or ())
            
            # Handle queries that don't return results
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
                self.connection.commit()
                return []
            
            # Fetch results for SELECT queries
            columns = [column[0] for column in self.cursor.description]
            results = []
            
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            raise e
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get SQL Server table information"""
        schema_condition = ""
        if schema_filter:
            schema_list = "','".join(schema_filter)
            schema_condition = f"AND s.name IN ('{schema_list}')"
        
        query = f"""
        SELECT 
            t.name as table_name,
            s.name as schema_name,
            'BASE TABLE' as table_type,
            COALESCE(p.rows, 0) as record_count,
            COALESCE(CAST(ep.value AS NVARCHAR(MAX)), '') as table_comment,
            t.create_date,
            t.modify_date
        FROM sys.tables t
        INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        LEFT JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0,1)
        LEFT JOIN sys.extended_properties ep ON t.object_id = ep.major_id AND ep.minor_id = 0 AND ep.name = 'MS_Description'
        WHERE s.name NOT IN ('sys', 'information_schema', 'INFORMATION_SCHEMA')
        {schema_condition}
        ORDER BY s.name, t.name
        """
        
        results = self._execute_query(query)
        
        tables = []
        for row in results:
            tables.append(TableInfo(
                table_name=row['table_name'],
                schema_name=row['schema_name'],
                table_type=row['table_type'],
                record_count=row['record_count'] or 0,
                table_comment=row['table_comment'] or '',
                created_date=str(row['create_date']) if row['create_date'] else '',
                last_modified=str(row['modify_date']) if row['modify_date'] else ''
            ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get SQL Server column information"""
        table_condition = ""
        if table_name:
            table_condition = f"AND t.name = '{table_name}'"
        
        query = f"""
        SELECT 
            t.name as table_name,
            c.name as column_name,
            typ.name as data_type,
            CASE 
                WHEN typ.name IN ('varchar', 'nvarchar', 'char', 'nchar') THEN c.max_length
                WHEN typ.name IN ('decimal', 'numeric') THEN c.precision
                ELSE 0
            END as max_length,
            c.is_nullable,
            COALESCE(CAST(dc.definition AS NVARCHAR(MAX)), '') as default_value,
            COALESCE(CAST(ep.value AS NVARCHAR(MAX)), '') as column_comment,
            c.column_id as ordinal_position
        FROM sys.tables t
        INNER JOIN sys.columns c ON t.object_id = c.object_id
        INNER JOIN sys.types typ ON c.user_type_id = typ.user_type_id
        INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        LEFT JOIN sys.default_constraints dc ON c.default_object_id = dc.object_id
        LEFT JOIN sys.extended_properties ep ON t.object_id = ep.major_id AND c.column_id = ep.minor_id AND ep.name = 'MS_Description'
        WHERE s.name NOT IN ('sys', 'information_schema', 'INFORMATION_SCHEMA')
        {table_condition}
        ORDER BY t.name, c.column_id
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
        """Get SQL Server foreign key relationships"""
        query = """
        SELECT
            fk.name as constraint_name,
            OBJECT_NAME(fk.parent_object_id) as from_table,
            COL_NAME(fkc.parent_object_id, fkc.parent_column_id) as from_column,
            OBJECT_NAME(fk.referenced_object_id) as to_table,
            COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) as to_column,
            'FOREIGN KEY' as constraint_type
        FROM sys.foreign_keys fk
        INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
        INNER JOIN sys.schemas s ON fk.schema_id = s.schema_id
        WHERE s.name NOT IN ('sys', 'information_schema', 'INFORMATION_SCHEMA')
        ORDER BY from_table, fk.name
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
        """Get SQL Server index information"""
        table_condition = ""
        if table_name:
            table_condition = f"AND t.name = '{table_name}'"
        
        query = f"""
        SELECT
            i.name as index_name,
            t.name as table_name,
            STRING_AGG(c.name, ',') WITHIN GROUP (ORDER BY ic.key_ordinal) as column_names,
            i.is_unique,
            i.type_desc as index_type,
            i.is_primary_key as is_primary
        FROM sys.indexes i
        INNER JOIN sys.tables t ON i.object_id = t.object_id
        INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE s.name NOT IN ('sys', 'information_schema', 'INFORMATION_SCHEMA')
        AND i.name IS NOT NULL
        {table_condition}
        GROUP BY i.name, t.name, i.is_unique, i.type_desc, i.is_primary_key
        ORDER BY t.name, i.name
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
        """Analyze SQL Server data distribution"""
        try:
            # Basic statistics query
            stats_query = f"""
            SELECT 
                COUNT(*) as total_count,
                COUNT(DISTINCT [{column_name}]) as unique_count,
                COUNT([{column_name}]) as non_null_count,
                COUNT(*) - COUNT([{column_name}]) as null_count
            FROM [{table_name}]
            """
            
            stats_result = self._execute_query(stats_query)
            if not stats_result:
                return {"error": "No data found"}
            
            stats = stats_result[0]
            
            # Sample data query
            sample_query = f"""
            SELECT TOP {min(sample_size, 100)} [{column_name}] 
            FROM [{table_name}] 
            WHERE [{column_name}] IS NOT NULL 
            ORDER BY NEWID()
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
        """Get sample data from SQL Server table"""
        try:
            query = f"SELECT TOP {limit} * FROM [{table_name}]"
            return self._execute_query(query)
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_table_size(self, table_name: str) -> Dict[str, Any]:
        """Get SQL Server table size information"""
        try:
            query = f"""
            SELECT 
                CAST(ROUND(((SUM(a.total_pages) * 8) / 1024.00), 2) AS NUMERIC(36, 2)) AS total_size_mb,
                CAST(ROUND(((SUM(a.used_pages) * 8) / 1024.00), 2) AS NUMERIC(36, 2)) AS used_size_mb,
                CAST(ROUND(((SUM(a.data_pages) * 8) / 1024.00), 2) AS NUMERIC(36, 2)) AS data_size_mb
            FROM [{table_name}] t
            INNER JOIN sys.indexes i ON t.object_id = i.object_id
            INNER JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
            INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
            LEFT OUTER JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE t.name = '{table_name}'
            AND i.object_id > 255
            """
            
            result = self._execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            return {"error": str(e)}
    
    def get_database_version(self) -> str:
        """Get SQL Server version"""
        try:
            result = self._execute_query("SELECT @@VERSION as version")
            return result[0]['version'] if result else "Unknown"
        except Exception:
            return "Unknown"