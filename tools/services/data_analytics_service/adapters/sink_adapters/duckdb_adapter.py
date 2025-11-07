#!/usr/bin/env python3
"""
DuckDB Sink Adapter
Stores data TO DuckDB using enterprise DuckDB service
"""

import polars as pl
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path

from .base_sink_adapter import BaseSinkAdapter
from resources.dbs.duckdb.core import get_duckdb_service, AccessLevel, ConnectionConfig

logger = logging.getLogger(__name__)

class DuckDBSinkAdapter(BaseSinkAdapter):
    """
    DuckDB sink adapter using enterprise DuckDB service
    
    Features:
    - Connection pooling and management
    - Transaction support
    - Security controls
    - Performance monitoring
    - Fast analytical queries
    """
    
    def __init__(self):
        super().__init__()
        self.db_path = None
        self._duckdb_service = None
    
    @property
    def duckdb_service(self):
        """Lazy initialization of enterprise DuckDB service"""
        if self._duckdb_service is None:
            config = ConnectionConfig(
                database_path=self.db_path or ":memory:",
                read_only=False,
                threads=4,
                memory_limit="1GB"
            )
            self._duckdb_service = get_duckdb_service(connection_config=config)
        return self._duckdb_service
    
    def connect(self, destination: str, **kwargs) -> bool:
        """
        Initialize DuckDB service connection
        
        Args:
            destination: Database file path (or ":memory:" for in-memory)
            **kwargs: Additional connection parameters
            
        Returns:
            True if connection successful
        """
        try:
            self.db_path = destination
            
            # Create directory if needed
            if destination != ":memory:":
                Path(destination).parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize enterprise service (lazy loaded)
            _ = self.duckdb_service
            
            # Store connection info
            self.storage_info = {
                'database_path': destination,
                'database_type': 'duckdb_enterprise',
                'connection_mode': 'in_memory' if destination == ':memory:' else 'file',
                'service_features': ['connection_pooling', 'transactions', 'security', 'monitoring']
            }
            
            logger.info(f"Connected to DuckDB via enterprise service: {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB service: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Cleanup DuckDB service resources"""
        try:
            # Enterprise service manages connections via pool
            # No explicit cleanup needed as it's handled by the service
            self._duckdb_service = None
            logger.info("Disconnected from DuckDB enterprise service")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect from DuckDB service: {e}")
            return False
    
    def store_dataframe(self, df: pl.DataFrame,
                       destination: str,
                       table_name: Optional[str] = None,
                       storage_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Store DataFrame in DuckDB using enterprise service

        Args:
            df: DataFrame to store
            destination: DuckDB database path
            table_name: Table name (default: 'data')
            storage_options: Storage configuration

        Returns:
            Storage result information
        """
        from datetime import datetime
        start_time = datetime.now()
        
        try:
            # Validate DataFrame
            validation = self.validate_dataframe(df)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': f"DataFrame validation failed: {validation['errors']}",
                    'warnings': validation['warnings']
                }
            
            # Ensure connection is established
            if not self.storage_info:
                if not self.connect(destination):
                    return {
                        'success': False,
                        'error': 'Failed to initialize DuckDB service'
                    }
            
            # Prepare storage options
            options = storage_options or {}
            table_name = self._sanitize_table_name(table_name or 'data')
            if_exists = options.get('if_exists', 'replace')  # replace, append, fail
            
            # Store DataFrame using enterprise service (DuckDB supports Polars natively)
            self.duckdb_service.create_table_from_dataframe(
                data=df,
                table_name=table_name,
                framework='polars',
                if_exists=if_exists
            )

            # Verify storage and get table info
            verify_query = f"""
                SELECT
                    COUNT(*) as row_count,
                    COUNT(DISTINCT *) as unique_rows
                FROM {table_name}
            """
            table_info = self.duckdb_service.execute_query(
                verify_query,
                access_level=AccessLevel.READ_ONLY
            )

            storage_duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'destination': destination,
                'table_name': table_name,
                'storage_adapter': 'DuckDBSinkAdapter_Enterprise',
                'storage_duration': storage_duration,
                'rows_stored': table_info[0][0] if table_info else len(df),
                'unique_rows': table_info[0][1] if table_info and len(table_info[0]) > 1 else None,
                'columns_stored': len(df.columns),
                'database_path': self.db_path,
                'storage_options_used': options,
                'warnings': validation.get('warnings', []),
                'service_features': self.storage_info.get('service_features', [])
            }
            
            self._log_storage_operation('DataFrame storage', True, {
                'table': table_name,
                'rows': result['rows_stored'],
                'duration': f"{storage_duration:.2f}s",
                'service': 'enterprise'
            })
            
            return result
            
        except Exception as e:
            storage_duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)

            self._log_storage_operation('DataFrame storage', False, {
                'error': error_msg,
                'duration': f"{storage_duration:.2f}s",
                'service': 'enterprise'
            })

            return {
                'success': False,
                'error': error_msg,
                'storage_duration': storage_duration,
                'destination': destination,
                'table_name': table_name
            }

    def query_table(self, table_name: str, query: Optional[str] = None) -> pl.DataFrame:
        """
        Query data from DuckDB table using enterprise service

        Args:
            table_name: Name of table to query
            query: Optional SQL query (default: SELECT * FROM table)

        Returns:
            DataFrame with query results
        """
        try:
            if not self._duckdb_service:
                raise Exception("DuckDB service not initialized")

            if query:
                return self.duckdb_service.execute_query_df(
                    query=query,
                    framework='polars',
                    access_level=AccessLevel.READ_ONLY
                )
            else:
                return self.duckdb_service.execute_query_df(
                    query=f"SELECT * FROM {table_name}",
                    framework='polars',
                    access_level=AccessLevel.READ_ONLY
                )

        except Exception as e:
            logger.error(f"Query failed: {e}")
            return pl.DataFrame()
    
    def list_tables(self) -> List[str]:
        """List all tables in the DuckDB database using enterprise service"""
        try:
            if not self._duckdb_service:
                return []
            
            result = self.duckdb_service.execute_query(
                "SHOW TABLES",
                access_level=AccessLevel.READ_ONLY
            )
            return [row[0] for row in result] if result else []
            
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return []
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a specific table using enterprise service"""
        try:
            if not self._duckdb_service:
                return {}
            
            # Get table schema
            schema_result = self.duckdb_service.execute_query(
                f"DESCRIBE {table_name}",
                access_level=AccessLevel.READ_ONLY
            )
            columns = [{'name': row[0], 'type': row[1], 'null': row[2] == 'YES'} 
                      for row in schema_result] if schema_result else []
            
            # Get row count
            count_result = self.duckdb_service.execute_query(
                f"SELECT COUNT(*) FROM {table_name}",
                access_level=AccessLevel.READ_ONLY
            )
            row_count = count_result[0][0] if count_result else 0
            
            return {
                'table_name': table_name,
                'row_count': row_count,
                'column_count': len(columns),
                'columns': columns,
                'service_type': 'enterprise'
            }
            
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return {}
    
    def delete_table(self, table_name: str) -> bool:
        """Delete a table from DuckDB using enterprise service"""
        try:
            if not self._duckdb_service:
                return False
            
            self.duckdb_service.execute_query(
                f"DROP TABLE IF EXISTS {table_name}",
                access_level=AccessLevel.READ_WRITE,
                fetch_result=False
            )
            logger.info(f"Deleted table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete table {table_name}: {e}")
            return False
    
    def export_to_parquet(self, table_name: str, output_path: str) -> bool:
        """Export DuckDB table to Parquet file using enterprise service"""
        try:
            if not self._duckdb_service:
                return False
            
            # Create output directory if needed
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Export to Parquet using enterprise service
            self.duckdb_service.execute_query(
                f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET)",
                access_level=AccessLevel.READ_ONLY,
                fetch_result=False
            )
            
            logger.info(f"Exported table {table_name} to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export to Parquet: {e}")
            return False
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get enterprise DuckDB service statistics"""
        try:
            if not self._duckdb_service:
                return {'status': 'not_initialized'}
            
            return self.duckdb_service.get_service_stats()
            
        except Exception as e:
            logger.error(f"Failed to get service stats: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def execute_transaction(self, operations: List[str]) -> Dict[str, Any]:
        """Execute multiple operations in a transaction using enterprise service"""
        try:
            if not self._duckdb_service:
                return {'success': False, 'error': 'Service not initialized'}
            
            with self.duckdb_service.transaction(access_level=AccessLevel.READ_WRITE) as conn:
                results = []
                for op in operations:
                    result = conn.execute(op)
                    results.append(result)
                
                return {
                    'success': True,
                    'operations_executed': len(operations),
                    'results': results
                }
                
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return {'success': False, 'error': str(e)}