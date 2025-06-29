#!/usr/bin/env python3
"""
SQLite adapter for testing purposes
Implements the same interface as other database adapters
"""

import sqlite3
from typing import Dict, List, Any, Optional
from tools.services.data_analytics_service.adapters.database_adapters.base_adapter import DatabaseAdapter
from tools.services.data_analytics_service.core.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter for testing"""
    
    def __init__(self):
        super().__init__()
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create SQLite connection"""
        database_path = config['database']
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row  # Enable column access by name
        self.cursor = connection.cursor()
        return connection
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute SQLite query"""
        try:
            self.cursor.execute(query, params or ())
            
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
        """Get SQLite table information"""
        query = """
        SELECT 
            name as table_name,
            'main' as schema_name,
            'BASE TABLE' as table_type
        FROM sqlite_master 
        WHERE type = 'table' 
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
        
        results = self._execute_query(query)
        
        tables = []
        for row in results:
            table_name = row['table_name']
            
            # Get row count
            count_query = f"SELECT COUNT(*) as count FROM [{table_name}]"
            count_result = self._execute_query(count_query)
            record_count = count_result[0]['count'] if count_result else 0
            
            tables.append(TableInfo(
                table_name=table_name,
                schema_name=row['schema_name'],
                table_type=row['table_type'],
                record_count=record_count,
                table_comment='',
                created_date='',
                last_modified=''
            ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get SQLite column information"""
        columns = []
        
        # Get table names
        if table_name:
            table_names = [table_name]
        else:
            tables = self.get_tables()
            table_names = [t.table_name for t in tables]
        
        for table in table_names:
            # Get column info using PRAGMA
            pragma_query = f"PRAGMA table_info([{table}])"
            results = self._execute_query(pragma_query)
            
            for row in results:
                column_info = ColumnInfo(
                    table_name=table,
                    column_name=row['name'],
                    data_type=row['type'],
                    max_length=None,
                    is_nullable=not bool(row['notnull']),
                    default_value=row['dflt_value'] or '',
                    column_comment='',
                    ordinal_position=row['cid'] + 1
                )
                columns.append(column_info)
        
        return columns
    
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get SQLite foreign key relationships"""
        relationships = []
        
        # Get all tables
        tables = self.get_tables()
        
        for table in tables:
            # Get foreign keys using PRAGMA
            fk_query = f"PRAGMA foreign_key_list([{table.table_name}])"
            results = self._execute_query(fk_query)
            
            for row in results:
                relationship = RelationshipInfo(
                    constraint_name=f"fk_{table.table_name}_{row['from']}",
                    from_table=table.table_name,
                    from_column=row['from'],
                    to_table=row['table'],
                    to_column=row['to'],
                    constraint_type='FOREIGN KEY'
                )
                relationships.append(relationship)
        
        return relationships
    
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Get SQLite index information"""
        indexes = []
        
        # Get table names
        if table_name:
            table_names = [table_name]
        else:
            tables = self.get_tables()
            table_names = [t.table_name for t in tables]
        
        for table in table_names:
            # Get indexes using PRAGMA
            index_query = f"PRAGMA index_list([{table}])"
            results = self._execute_query(index_query)
            
            for row in results:
                index_name = row['name']
                
                # Get index columns
                index_info_query = f"PRAGMA index_info([{index_name}])"
                index_info_results = self._execute_query(index_info_query)
                
                column_names = [col['name'] for col in index_info_results]
                
                index_info = IndexInfo(
                    index_name=index_name,
                    table_name=table,
                    column_names=column_names,
                    is_unique=bool(row['unique']),
                    index_type='BTREE',  # SQLite default
                    is_primary=row['origin'] == 'pk'
                )
                indexes.append(index_info)
        
        return indexes
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze SQLite data distribution"""
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
            SELECT [{column_name}] 
            FROM [{table_name}] 
            WHERE [{column_name}] IS NOT NULL 
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
                "sample_values": sample_values[:10]
            }
        
        except Exception as e:
            return {"error": str(e), "analysis_failed": True}
    
    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from SQLite table"""
        try:
            query = f"SELECT * FROM [{table_name}] LIMIT {limit}"
            return self._execute_query(query)
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_database_version(self) -> str:
        """Get SQLite version"""
        try:
            result = self._execute_query("SELECT sqlite_version() as version")
            return f"SQLite {result[0]['version']}" if result else "Unknown"
        except Exception:
            return "Unknown"