#!/usr/bin/env python3
"""
Oracle database adapter
"""

from typing import Dict, List, Any, Optional
from .base_adapter import DatabaseAdapter
from ...processors.data_processors.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

try:
    import cx_Oracle
    ORACLE_AVAILABLE = True
except ImportError:
    try:
        import oracledb
        cx_Oracle = oracledb
        ORACLE_AVAILABLE = True
    except ImportError:
        ORACLE_AVAILABLE = False

class OracleAdapter(DatabaseAdapter):
    """Oracle database adapter"""
    
    def __init__(self):
        super().__init__()
        if not ORACLE_AVAILABLE:
            raise ImportError("cx_Oracle or oracledb is required for Oracle adapter. Install with: pip install cx_Oracle or pip install oracledb")
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create Oracle connection"""
        # Support different connection methods
        if 'service_name' in config:
            # Service name connection
            dsn = cx_Oracle.makedsn(
                config['host'], 
                config.get('port', 1521), 
                service_name=config['service_name']
            )
        elif 'sid' in config:
            # SID connection
            dsn = cx_Oracle.makedsn(
                config['host'], 
                config.get('port', 1521), 
                sid=config['sid']
            )
        else:
            # Default to service_name with database name
            dsn = cx_Oracle.makedsn(
                config['host'], 
                config.get('port', 1521), 
                service_name=config['database']
            )
        
        connection = cx_Oracle.connect(
            user=config['username'],
            password=config['password'],
            dsn=dsn
        )
        self.cursor = connection.cursor()
        return connection
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute Oracle query"""
        try:
            self.cursor.execute(query, params or ())
            
            # Handle queries that don't return results
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
                self.connection.commit()
                return []
            
            # Fetch results for SELECT queries
            columns = [desc[0] for desc in self.cursor.description]
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            raise e
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get Oracle table information"""
        schema_condition = ""
        if schema_filter:
            schema_list = "','".join(schema_filter)
            schema_condition = f"AND t.OWNER IN ('{schema_list}')"
        else:
            # Default to current user's tables
            schema_condition = "AND t.OWNER = USER"
        
        query = f"""
        SELECT 
            t.TABLE_NAME,
            t.OWNER as TABLE_SCHEMA,
            'BASE TABLE' as TABLE_TYPE,
            COALESCE(t.NUM_ROWS, 0) as RECORD_COUNT,
            COALESCE(c.COMMENTS, '') as TABLE_COMMENT,
            TO_CHAR(t.CREATED, 'YYYY-MM-DD HH24:MI:SS') as CREATED_DATE,
            TO_CHAR(t.LAST_ANALYZED, 'YYYY-MM-DD HH24:MI:SS') as LAST_MODIFIED
        FROM ALL_TABLES t
        LEFT JOIN ALL_TAB_COMMENTS c ON c.TABLE_NAME = t.TABLE_NAME AND c.OWNER = t.OWNER
        WHERE 1=1
        {schema_condition}
        ORDER BY t.OWNER, t.TABLE_NAME
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
                created_date=row['CREATED_DATE'] or '',
                last_modified=row['LAST_MODIFIED'] or ''
            ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get Oracle column information"""
        table_condition = ""
        if table_name:
            table_condition = f"AND c.TABLE_NAME = '{table_name.upper()}'"
        
        query = f"""
        SELECT 
            c.TABLE_NAME,
            c.COLUMN_NAME,
            c.DATA_TYPE,
            COALESCE(c.DATA_LENGTH, c.DATA_PRECISION, 0) as MAX_LENGTH,
            CASE WHEN c.NULLABLE = 'Y' THEN 1 ELSE 0 END as IS_NULLABLE,
            COALESCE(c.DATA_DEFAULT, '') as DEFAULT_VALUE,
            COALESCE(cc.COMMENTS, '') as COLUMN_COMMENT,
            c.COLUMN_ID as ORDINAL_POSITION
        FROM ALL_TAB_COLUMNS c
        LEFT JOIN ALL_COL_COMMENTS cc ON cc.TABLE_NAME = c.TABLE_NAME 
            AND cc.COLUMN_NAME = c.COLUMN_NAME 
            AND cc.OWNER = c.OWNER
        WHERE c.OWNER = USER
        {table_condition}
        ORDER BY c.TABLE_NAME, c.COLUMN_ID
        """
        
        results = self._execute_query(query)
        
        columns = []
        for row in results:
            columns.append(ColumnInfo(
                table_name=row['TABLE_NAME'],
                column_name=row['COLUMN_NAME'],
                data_type=row['DATA_TYPE'],
                max_length=row['MAX_LENGTH'],
                is_nullable=bool(row['IS_NULLABLE']),
                default_value=row['DEFAULT_VALUE'],
                column_comment=row['COLUMN_COMMENT'],
                ordinal_position=row['ORDINAL_POSITION']
            ))
        
        return columns
    
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get Oracle foreign key relationships"""
        query = """
        SELECT
            c.CONSTRAINT_NAME,
            c.TABLE_NAME as FROM_TABLE,
            cc.COLUMN_NAME as FROM_COLUMN,
            r.TABLE_NAME as TO_TABLE,
            rc.COLUMN_NAME as TO_COLUMN,
            'FOREIGN KEY' as CONSTRAINT_TYPE
        FROM ALL_CONSTRAINTS c
        JOIN ALL_CONS_COLUMNS cc ON c.CONSTRAINT_NAME = cc.CONSTRAINT_NAME AND c.OWNER = cc.OWNER
        JOIN ALL_CONSTRAINTS r ON c.R_CONSTRAINT_NAME = r.CONSTRAINT_NAME AND c.R_OWNER = r.OWNER
        JOIN ALL_CONS_COLUMNS rc ON r.CONSTRAINT_NAME = rc.CONSTRAINT_NAME AND r.OWNER = rc.OWNER
        WHERE c.CONSTRAINT_TYPE = 'R'
        AND c.OWNER = USER
        ORDER BY c.TABLE_NAME, c.CONSTRAINT_NAME
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
        """Get Oracle index information"""
        table_condition = ""
        if table_name:
            table_condition = f"AND i.TABLE_NAME = '{table_name.upper()}'"
        
        query = f"""
        SELECT
            i.INDEX_NAME,
            i.TABLE_NAME,
            LISTAGG(ic.COLUMN_NAME, ',') WITHIN GROUP (ORDER BY ic.COLUMN_POSITION) as COLUMN_NAMES,
            CASE WHEN i.UNIQUENESS = 'UNIQUE' THEN 1 ELSE 0 END as IS_UNIQUE,
            i.INDEX_TYPE,
            CASE WHEN i.INDEX_NAME IN (
                SELECT CONSTRAINT_NAME FROM ALL_CONSTRAINTS 
                WHERE CONSTRAINT_TYPE = 'P' AND TABLE_NAME = i.TABLE_NAME
            ) THEN 1 ELSE 0 END as IS_PRIMARY
        FROM ALL_INDEXES i
        JOIN ALL_IND_COLUMNS ic ON i.INDEX_NAME = ic.INDEX_NAME AND i.OWNER = ic.INDEX_OWNER
        WHERE i.OWNER = USER
        {table_condition}
        GROUP BY i.INDEX_NAME, i.TABLE_NAME, i.UNIQUENESS, i.INDEX_TYPE
        ORDER BY i.TABLE_NAME, i.INDEX_NAME
        """
        
        results = self._execute_query(query)
        
        indexes = []
        for row in results:
            column_names = row['COLUMN_NAMES'].split(',') if row['COLUMN_NAMES'] else []
            indexes.append(IndexInfo(
                index_name=row['INDEX_NAME'],
                table_name=row['TABLE_NAME'],
                column_names=column_names,
                is_unique=bool(row['IS_UNIQUE']),
                index_type=row['INDEX_TYPE'],
                is_primary=bool(row['IS_PRIMARY'])
            ))
        
        return indexes
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze Oracle data distribution"""
        try:
            # Basic statistics query
            stats_query = f"""
            SELECT 
                COUNT(*) as TOTAL_COUNT,
                COUNT(DISTINCT {column_name}) as UNIQUE_COUNT,
                COUNT({column_name}) as NON_NULL_COUNT,
                COUNT(*) - COUNT({column_name}) as NULL_COUNT
            FROM {table_name}
            """
            
            stats_result = self._execute_query(stats_query)
            if not stats_result:
                return {"error": "No data found"}
            
            stats = stats_result[0]
            
            # Sample data query
            sample_query = f"""
            SELECT {column_name} 
            FROM (
                SELECT {column_name} 
                FROM {table_name} 
                WHERE {column_name} IS NOT NULL 
                ORDER BY DBMS_RANDOM.VALUE
            )
            WHERE ROWNUM <= {min(sample_size, 100)}
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
        """Get sample data from Oracle table"""
        try:
            query = f"SELECT * FROM {table_name} WHERE ROWNUM <= {limit}"
            return self._execute_query(query)
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_table_size(self, table_name: str) -> Dict[str, Any]:
        """Get Oracle table size information"""
        try:
            query = f"""
            SELECT
                ROUND((BLOCKS * 8192) / 1024 / 1024, 2) as TOTAL_SIZE_MB,
                NUM_ROWS,
                AVG_ROW_LEN,
                LAST_ANALYZED
            FROM ALL_TABLES 
            WHERE TABLE_NAME = '{table_name.upper()}'
            AND OWNER = USER
            """
            
            result = self._execute_query(query)
            return result[0] if result else {}
        except Exception as e:
            return {"error": str(e)}
    
    def get_database_version(self) -> str:
        """Get Oracle version"""
        try:
            result = self._execute_query("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1")
            return result[0]['BANNER'] if result else "Unknown"
        except Exception:
            return "Unknown"