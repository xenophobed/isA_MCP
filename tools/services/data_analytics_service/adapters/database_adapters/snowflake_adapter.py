#!/usr/bin/env python3
"""
Snowflake data warehouse adapter
"""

from typing import Dict, List, Any, Optional
from .base_adapter import DatabaseAdapter
from ...processors.data_processors.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

try:
    import snowflake.connector
    from snowflake.connector import DictCursor
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False

class SnowflakeAdapter(DatabaseAdapter):
    """Snowflake data warehouse adapter"""
    
    def __init__(self):
        super().__init__()
        if not SNOWFLAKE_AVAILABLE:
            raise ImportError("snowflake-connector-python is required for Snowflake adapter. Install with: pip install snowflake-connector-python")
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create Snowflake connection"""
        connection_params = {
            'user': config['username'],
            'password': config['password'],
            'account': config['account'],  # Required for Snowflake
            'warehouse': config.get('warehouse'),
            'database': config.get('database'),
            'schema': config.get('schema', 'PUBLIC'),
            'role': config.get('role'),
            'timeout': config.get('timeout', 30)
        }
        
        # Remove None values
        connection_params = {k: v for k, v in connection_params.items() if v is not None}
        
        connection = snowflake.connector.connect(**connection_params)
        self.cursor = connection.cursor(DictCursor)
        return connection
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute Snowflake query"""
        try:
            self.cursor.execute(query, params)
            
            # Handle queries that don't return results
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'TRUNCATE')):
                return []
            
            # Fetch results for SELECT queries
            results = self.cursor.fetchall()
            return results if results else []
        except Exception as e:
            raise e
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get Snowflake table information"""
        schema_condition = ""
        if schema_filter:
            schema_list = "','".join(schema_filter)
            schema_condition = f"AND TABLE_SCHEMA IN ('{schema_list}')"
        
        query = f"""
        SELECT 
            TABLE_NAME,
            TABLE_SCHEMA,
            TABLE_TYPE,
            COALESCE(ROW_COUNT, 0) as RECORD_COUNT,
            COALESCE(COMMENT, '') as TABLE_COMMENT,
            CREATED as CREATED_DATE,
            LAST_ALTERED as LAST_MODIFIED
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
        {schema_condition}
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        
        results = self._execute_query(query)
        
        tables = []
        for row in results:
            tables.append(TableInfo(
                table_name=row['TABLE_NAME'],
                schema_name=row['TABLE_SCHEMA'],
                table_type=row['TABLE_TYPE'],
                record_count=row['RECORD_COUNT'] or 0,
                table_comment=row['TABLE_COMMENT'] or '',
                created_date=str(row['CREATED_DATE']) if row['CREATED_DATE'] else '',
                last_modified=str(row['LAST_MODIFIED']) if row['LAST_MODIFIED'] else ''
            ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get Snowflake column information"""
        table_condition = ""
        if table_name:
            table_condition = f"AND TABLE_NAME = '{table_name.upper()}'"
        
        query = f"""
        SELECT 
            TABLE_NAME,
            COLUMN_NAME,
            DATA_TYPE,
            COALESCE(CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, 0) as MAX_LENGTH,
            CASE WHEN IS_NULLABLE = 'YES' THEN true ELSE false END as IS_NULLABLE,
            COALESCE(COLUMN_DEFAULT, '') as DEFAULT_VALUE,
            COALESCE(COMMENT, '') as COLUMN_COMMENT,
            ORDINAL_POSITION
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE 1=1
        {table_condition}
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """
        
        results = self._execute_query(query)
        
        columns = []
        for row in results:
            columns.append(ColumnInfo(
                table_name=row['TABLE_NAME'],
                column_name=row['COLUMN_NAME'],
                data_type=row['DATA_TYPE'],
                max_length=row['MAX_LENGTH'],
                is_nullable=row['IS_NULLABLE'],
                default_value=row['DEFAULT_VALUE'],
                column_comment=row['COLUMN_COMMENT'],
                ordinal_position=row['ORDINAL_POSITION']
            ))
        
        return columns
    
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get Snowflake foreign key relationships"""
        query = """
        SELECT
            FK.CONSTRAINT_NAME,
            FK.TABLE_NAME as FROM_TABLE,
            FK.COLUMN_NAME as FROM_COLUMN,
            PK.TABLE_NAME as TO_TABLE,
            PK.COLUMN_NAME as TO_COLUMN,
            'FOREIGN KEY' as CONSTRAINT_TYPE
        FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS RC
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE FK 
            ON RC.CONSTRAINT_NAME = FK.CONSTRAINT_NAME
            AND RC.CONSTRAINT_SCHEMA = FK.CONSTRAINT_SCHEMA
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE PK
            ON RC.UNIQUE_CONSTRAINT_NAME = PK.CONSTRAINT_NAME
            AND RC.UNIQUE_CONSTRAINT_SCHEMA = PK.CONSTRAINT_SCHEMA
        ORDER BY FK.TABLE_NAME, FK.CONSTRAINT_NAME
        """
        
        results = self._execute_query(query)
        
        relationships = []
        for row in results:
            relationships.append(RelationshipInfo(
                constraint_name=row['CONSTRAINT_NAME'],
                from_table=row['FROM_TABLE'],
                from_column=row['FROM_COLUMN'],
                to_table=row['TO_TABLE'],
                to_column=row['TO_COLUMN'],
                constraint_type=row['CONSTRAINT_TYPE']
            ))
        
        return relationships
    
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Get Snowflake clustering keys (equivalent to indexes)"""
        # Snowflake doesn't have traditional indexes, but has clustering keys
        indexes = []
        
        table_condition = ""
        if table_name:
            table_condition = f"AND TABLE_NAME = '{table_name.upper()}'"
        
        query = f"""
        SELECT
            TABLE_NAME,
            CLUSTERING_KEY
        FROM INFORMATION_SCHEMA.TABLES
        WHERE CLUSTERING_KEY IS NOT NULL
        {table_condition}
        ORDER BY TABLE_NAME
        """
        
        try:
            results = self._execute_query(query)
            
            for row in results:
                if row['CLUSTERING_KEY']:
                    # Parse clustering key (usually comma-separated column names)
                    clustering_columns = [col.strip().strip('"') for col in row['CLUSTERING_KEY'].split(',')]
                    
                    indexes.append(IndexInfo(
                        index_name=f"CLUSTERING_KEY_{row['TABLE_NAME']}",
                        table_name=row['TABLE_NAME'],
                        column_names=clustering_columns,
                        is_unique=False,  # Clustering keys are not unique constraints
                        index_type='CLUSTERING',
                        is_primary=False
                    ))
        except Exception:
            pass  # Clustering keys might not be available in all Snowflake editions
        
        return indexes
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze Snowflake data distribution"""
        try:
            # Basic statistics query
            stats_query = f"""
            SELECT 
                COUNT(*) as TOTAL_COUNT,
                COUNT(DISTINCT "{column_name}") as UNIQUE_COUNT,
                COUNT("{column_name}") as NON_NULL_COUNT,
                COUNT(*) - COUNT("{column_name}") as NULL_COUNT
            FROM "{table_name}"
            """
            
            stats_result = self._execute_query(stats_query)
            if not stats_result:
                return {"error": "No data found"}
            
            stats = stats_result[0]
            
            # Sample data query
            sample_query = f"""
            SELECT "{column_name}" 
            FROM "{table_name}" 
            WHERE "{column_name}" IS NOT NULL 
            SAMPLE ({min(sample_size, 1000)} ROWS)
            LIMIT 100
            """
            
            sample_results = self._execute_query(sample_query)
            sample_values = [row[column_name] for row in sample_results]
            
            # Calculate percentages
            total_count = stats['TOTAL_COUNT']
            null_percentage = stats['NULL_COUNT'] / total_count if total_count > 0 else 0
            unique_percentage = stats['UNIQUE_COUNT'] / stats['NON_NULL_COUNT'] if stats['NON_NULL_COUNT'] > 0 else 0
            
            return {
                "total_count": total_count,
                "unique_count": stats['UNIQUE_COUNT'],
                "null_count": stats['NULL_COUNT'],
                "null_percentage": round(null_percentage, 4),
                "unique_percentage": round(unique_percentage, 4),
                "sample_values": sample_values[:10]
            }
        
        except Exception as e:
            return {"error": str(e), "analysis_failed": True}
    
    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from Snowflake table"""
        try:
            query = f'SELECT * FROM "{table_name}" LIMIT {limit}'
            return self._execute_query(query)
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_table_size(self, table_name: str) -> Dict[str, Any]:
        """Get Snowflake table size information"""
        try:
            query = f"""
            SELECT
                ROW_COUNT,
                BYTES,
                BYTES / (1024 * 1024) as SIZE_MB
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = '{table_name.upper()}'
            """
            
            result = self._execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            return {"error": str(e)}
    
    def get_warehouse_info(self) -> Dict[str, Any]:
        """Get Snowflake warehouse information"""
        try:
            query = """
            SELECT 
                WAREHOUSE_NAME,
                WAREHOUSE_SIZE,
                AUTO_SUSPEND,
                AUTO_RESUME,
                RESOURCE_MONITOR,
                STATE
            FROM INFORMATION_SCHEMA.WAREHOUSES
            ORDER BY WAREHOUSE_NAME
            """
            
            results = self._execute_query(query)
            return {"warehouses": results}
        except Exception as e:
            return {"error": str(e)}
    
    def get_database_version(self) -> str:
        """Get Snowflake version"""
        try:
            result = self._execute_query("SELECT CURRENT_VERSION()")
            return result[0]['CURRENT_VERSION()'] if result else "Unknown"
        except Exception:
            return "Unknown"
    
    def execute_dml_with_history(self, table_name: str, operation: str = "SELECT") -> List[Dict[str, Any]]:
        """Execute queries with Snowflake's time travel capability"""
        try:
            if operation.upper() == "HISTORY":
                # Query historical data (last 24 hours)
                query = f"""
                SELECT *
                FROM "{table_name}" AT (OFFSET => -3600)  -- 1 hour ago
                LIMIT 10
                """
            else:
                query = f'SELECT * FROM "{table_name}" LIMIT 10'
            
            return self._execute_query(query)
        except Exception as e:
            return [{"error": str(e)}]