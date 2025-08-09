#!/usr/bin/env python3
"""
ClickHouse database adapter
"""

from typing import Dict, List, Any, Optional
from .base_adapter import DatabaseAdapter
from ...processors.data_processors.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

try:
    from clickhouse_driver import Client
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False

class ClickHouseAdapter(DatabaseAdapter):
    """ClickHouse database adapter"""
    
    def __init__(self):
        super().__init__()
        if not CLICKHOUSE_AVAILABLE:
            raise ImportError("clickhouse-driver is required for ClickHouse adapter. Install with: pip install clickhouse-driver")
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create ClickHouse connection"""
        connection_params = {
            'host': config['host'],
            'port': config.get('port', 9000),
            'database': config.get('database', 'default'),
            'user': config.get('username', 'default'),
            'password': config.get('password', ''),
            'connect_timeout': config.get('timeout', 30),
            'send_receive_timeout': config.get('timeout', 30)
        }
        
        # Add SSL support
        if config.get('secure', False):
            connection_params['secure'] = True
        
        client = Client(**connection_params)
        
        # Test the connection
        client.execute('SELECT 1')
        
        self.client = client
        return client
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute ClickHouse query"""
        try:
            # Execute query with columnar result
            result = self.client.execute(query, params or (), with_column_types=True)
            
            if not result:
                return []
            
            data, columns_info = result
            
            # Convert to list of dictionaries
            rows = []
            column_names = [col[0] for col in columns_info]
            
            for row in data:
                row_dict = {}
                for i, value in enumerate(row):
                    # Convert ClickHouse specific types
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    elif hasattr(value, 'isoformat'):  # datetime objects
                        value = value.isoformat()
                    row_dict[column_names[i]] = value
                rows.append(row_dict)
            
            return rows
        except Exception as e:
            raise e
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get ClickHouse table information"""
        database_condition = ""
        if schema_filter:
            database_list = "','".join(schema_filter)
            database_condition = f"AND database IN ('{database_list}')"
        
        query = f"""
        SELECT 
            name as table_name,
            database as schema_name,
            engine as table_type,
            total_rows as record_count,
            comment as table_comment,
            '' as created_date,
            '' as last_modified
        FROM system.tables
        WHERE database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')
        {database_condition}
        ORDER BY database, name
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
                created_date=row['created_date'] or '',
                last_modified=row['last_modified'] or ''
            ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get ClickHouse column information"""
        table_condition = ""
        if table_name:
            table_condition = f"AND table = '{table_name}'"
        
        query = f"""
        SELECT 
            table as table_name,
            name as column_name,
            type as data_type,
            0 as max_length,
            1 as is_nullable,
            default_expression as default_value,
            comment as column_comment,
            position as ordinal_position
        FROM system.columns
        WHERE database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')
        {table_condition}
        ORDER BY table, position
        """
        
        results = self._execute_query(query)
        
        columns = []
        for row in results:
            # ClickHouse nullable detection
            is_nullable = 'Nullable' in row['data_type'] or row['data_type'].startswith('Array')
            
            columns.append(ColumnInfo(
                table_name=row['table_name'],
                column_name=row['column_name'],
                data_type=row['data_type'],
                max_length=row['max_length'],
                is_nullable=is_nullable,
                default_value=row['default_value'] or '',
                column_comment=row['column_comment'] or '',
                ordinal_position=row['ordinal_position']
            ))
        
        return columns
    
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get ClickHouse relationships (very limited)"""
        # ClickHouse doesn't have traditional foreign keys
        # But we can look for materialized views and dictionary relationships
        relationships = []
        
        try:
            # Look for dictionaries that reference tables
            dict_query = """
            SELECT 
                name as dict_name,
                source as source_info
            FROM system.dictionaries
            WHERE source LIKE '%table%'
            """
            
            dict_results = self._execute_query(dict_query)
            
            for dict_info in dict_results:
                # Parse source info to extract table references
                source_info = dict_info.get('source_info', '')
                if 'table' in source_info:
                    relationships.append(RelationshipInfo(
                        constraint_name=f"dict_{dict_info['dict_name']}",
                        from_table=dict_info['dict_name'],
                        from_column='key',
                        to_table='source_table',  # Would need parsing to get actual table
                        to_column='key',
                        constraint_type='DICTIONARY'
                    ))
        
        except Exception:
            pass  # Dictionary info might not be accessible
        
        return relationships
    
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Get ClickHouse indexes and sorting keys"""
        indexes = []
        
        try:
            table_condition = ""
            if table_name:
                table_condition = f"AND name = '{table_name}'"
            
            # Get sorting keys and primary keys
            query = f"""
            SELECT 
                name as table_name,
                sorting_key,
                primary_key,
                partition_key
            FROM system.tables
            WHERE database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')
            AND (sorting_key != '' OR primary_key != '' OR partition_key != '')
            {table_condition}
            ORDER BY name
            """
            
            results = self._execute_query(query)
            
            for row in results:
                table_name_val = row['table_name']
                
                # Primary key
                if row['primary_key']:
                    primary_columns = [col.strip() for col in row['primary_key'].split(',')]
                    indexes.append(IndexInfo(
                        index_name=f"PRIMARY_{table_name_val}",
                        table_name=table_name_val,
                        column_names=primary_columns,
                        is_unique=True,
                        index_type='PRIMARY',
                        is_primary=True
                    ))
                
                # Sorting key
                if row['sorting_key']:
                    sorting_columns = [col.strip() for col in row['sorting_key'].split(',')]
                    indexes.append(IndexInfo(
                        index_name=f"SORTING_{table_name_val}",
                        table_name=table_name_val,
                        column_names=sorting_columns,
                        is_unique=False,
                        index_type='SORTING',
                        is_primary=False
                    ))
                
                # Partition key
                if row['partition_key']:
                    partition_columns = [col.strip() for col in row['partition_key'].split(',')]
                    indexes.append(IndexInfo(
                        index_name=f"PARTITION_{table_name_val}",
                        table_name=table_name_val,
                        column_names=partition_columns,
                        is_unique=False,
                        index_type='PARTITION',
                        is_primary=False
                    ))
        
        except Exception:
            pass
        
        return indexes
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze ClickHouse data distribution"""
        try:
            # Basic statistics query
            stats_query = f"""
            SELECT 
                count() as total_count,
                uniq({column_name}) as unique_count,
                countIf({column_name} IS NOT NULL) as non_null_count,
                countIf({column_name} IS NULL) as null_count
            FROM {table_name}
            """
            
            stats_result = self._execute_query(stats_query)
            if not stats_result:
                return {"error": "No data found"}
            
            stats = stats_result[0]
            
            # Sample data query with SAMPLE
            sample_query = f"""
            SELECT {column_name} 
            FROM {table_name} SAMPLE 0.1
            WHERE {column_name} IS NOT NULL 
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
        """Get sample data from ClickHouse table"""
        try:
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            return self._execute_query(query)
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_table_size(self, table_name: str) -> Dict[str, Any]:
        """Get ClickHouse table size information"""
        try:
            query = f"""
            SELECT
                sum(rows) as total_rows,
                sum(data_compressed_bytes) as compressed_size,
                sum(data_uncompressed_bytes) as uncompressed_size,
                sum(data_compressed_bytes) / (1024 * 1024) as size_mb
            FROM system.parts
            WHERE table = '{table_name}' AND active = 1
            """
            
            result = self._execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            return {"error": str(e)}
    
    def get_database_version(self) -> str:
        """Get ClickHouse version"""
        try:
            result = self._execute_query("SELECT version()")
            return result[0]['version()'] if result else "Unknown"
        except Exception:
            return "Unknown"
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Get ClickHouse cluster information"""
        try:
            cluster_query = "SELECT * FROM system.clusters"
            clusters = self._execute_query(cluster_query)
            
            return {
                "clusters": clusters,
                "cluster_count": len(clusters)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def execute_with_progress(self, query: str) -> Dict[str, Any]:
        """Execute query with progress information"""
        try:
            # ClickHouse supports progress callbacks
            progress_data = []
            
            def progress_callback(progress):
                progress_data.append({
                    "read_rows": progress.read_rows,
                    "read_bytes": progress.read_bytes,
                    "total_rows": progress.total_rows,
                    "written_rows": progress.written_rows,
                    "written_bytes": progress.written_bytes
                })
            
            result = self.client.execute(query, progress=progress_callback, with_column_types=True)
            
            return {
                "result": result,
                "progress": progress_data[-1] if progress_data else {},
                "total_progress_updates": len(progress_data)
            }
        except Exception as e:
            return {"error": str(e)}