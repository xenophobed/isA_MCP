#!/usr/bin/env python3
"""
Delta Lake adapter
"""

from typing import Dict, List, Any, Optional
from .base_adapter import DatabaseAdapter
from ...processors.data_processors.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

try:
    from deltalake import DeltaTable
    import pyarrow as pa
    import pandas as pd
    DELTALAKE_AVAILABLE = True
except ImportError:
    DELTALAKE_AVAILABLE = False

class DeltaLakeAdapter(DatabaseAdapter):
    """Delta Lake adapter"""
    
    def __init__(self):
        super().__init__()
        if not DELTALAKE_AVAILABLE:
            raise ImportError("deltalake and pyarrow are required for Delta Lake adapter. Install with: pip install deltalake pyarrow pandas")
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create Delta Lake connection"""
        # Delta Lake works with file paths or cloud storage
        self.base_path = config.get('path', config.get('base_path', '/tmp/delta'))
        self.storage_options = config.get('storage_options', {})
        
        # Support for different storage backends
        if 'aws_access_key_id' in config:
            self.storage_options.update({
                'AWS_ACCESS_KEY_ID': config['aws_access_key_id'],
                'AWS_SECRET_ACCESS_KEY': config['aws_secret_access_key'],
                'AWS_REGION': config.get('aws_region', 'us-east-1')
            })
        
        if 'azure_storage_account_name' in config:
            self.storage_options.update({
                'AZURE_STORAGE_ACCOUNT_NAME': config['azure_storage_account_name'],
                'AZURE_STORAGE_ACCOUNT_KEY': config.get('azure_storage_account_key', '')
            })
        
        # Test connection by trying to list tables
        self._discover_tables()
        
        return {"base_path": self.base_path, "storage_options": self.storage_options}
    
    def _discover_tables(self) -> List[str]:
        """Discover Delta tables in the base path"""
        import os
        import glob
        
        try:
            if self.base_path.startswith('s3://') or self.base_path.startswith('azure://'):
                # For cloud storage, we need to use the storage options
                # This is a simplified implementation
                return []
            else:
                # Local file system
                delta_paths = []
                if os.path.exists(self.base_path):
                    for root, dirs, files in os.walk(self.base_path):
                        if '_delta_log' in dirs:
                            # This is a Delta table
                            table_name = os.path.basename(root)
                            delta_paths.append(table_name)
                return delta_paths
        except Exception:
            return []
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute Delta Lake query (limited SQL support)"""
        try:
            # Delta Lake doesn't have native SQL engine
            # This is a simplified implementation for basic operations
            
            query_upper = query.strip().upper()
            
            if query_upper.startswith('SELECT'):
                # Parse table name from query (simplified)
                if 'FROM' in query_upper:
                    parts = query.split()
                    from_idx = next(i for i, part in enumerate(parts) if part.upper() == 'FROM')
                    if from_idx + 1 < len(parts):
                        table_name = parts[from_idx + 1]
                        
                        # Get data from Delta table
                        table_path = f"{self.base_path}/{table_name}"
                        dt = DeltaTable(table_path, storage_options=self.storage_options)
                        
                        # Convert to pandas for query processing
                        df = dt.to_pandas()
                        
                        # Basic SELECT parsing
                        if 'LIMIT' in query_upper:
                            limit_parts = query.split()
                            limit_idx = next(i for i, part in enumerate(limit_parts) if part.upper() == 'LIMIT')
                            if limit_idx + 1 < len(limit_parts):
                                limit = int(limit_parts[limit_idx + 1])
                                df = df.head(limit)
                        
                        return df.to_dict('records')
            
            elif query_upper.startswith('DESCRIBE'):
                # Describe table
                parts = query.split()
                if len(parts) >= 2:
                    table_name = parts[1]
                    table_path = f"{self.base_path}/{table_name}"
                    dt = DeltaTable(table_path, storage_options=self.storage_options)
                    schema = dt.schema().to_pyarrow()
                    
                    result = []
                    for field in schema:
                        result.append({
                            "column_name": field.name,
                            "data_type": str(field.type),
                            "nullable": field.nullable
                        })
                    return result
            
            return []
        except Exception as e:
            raise e
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get Delta Lake tables"""
        tables = []
        
        try:
            table_names = self._discover_tables()
            
            for table_name in table_names:
                try:
                    table_path = f"{self.base_path}/{table_name}"
                    dt = DeltaTable(table_path, storage_options=self.storage_options)
                    
                    # Get table statistics
                    history = dt.history()
                    latest_version = dt.version()
                    
                    # Try to get row count (may be expensive for large tables)
                    try:
                        row_count = len(dt.to_pandas())
                    except Exception:
                        row_count = 0  # Skip if too large
                    
                    tables.append(TableInfo(
                        table_name=table_name,
                        schema_name='delta',
                        table_type='DELTA_TABLE',
                        record_count=row_count,
                        table_comment=f'Delta Lake table at {table_path} (version {latest_version})',
                        created_date=str(history.iloc[0]['timestamp']) if len(history) > 0 else '',
                        last_modified=str(history.iloc[-1]['timestamp']) if len(history) > 0 else ''
                    ))
                
                except Exception as e:
                    # Add error entry for problematic table
                    tables.append(TableInfo(
                        table_name=table_name,
                        schema_name='delta',
                        table_type='ERROR',
                        record_count=0,
                        table_comment=f'Error accessing table: {str(e)}',
                        created_date='',
                        last_modified=''
                    ))
        
        except Exception as e:
            tables.append(TableInfo(
                table_name='discovery_error',
                schema_name='delta',
                table_type='ERROR',
                record_count=0,
                table_comment=f'Error discovering tables: {str(e)}',
                created_date='',
                last_modified=''
            ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get Delta Lake table schema"""
        columns = []
        
        try:
            if table_name:
                table_path = f"{self.base_path}/{table_name}"
                dt = DeltaTable(table_path, storage_options=self.storage_options)
                schema = dt.schema().to_pyarrow()
                
                for i, field in enumerate(schema, 1):
                    columns.append(ColumnInfo(
                        table_name=table_name,
                        column_name=field.name,
                        data_type=str(field.type),
                        max_length=0,  # Arrow types don't specify max length
                        is_nullable=field.nullable,
                        default_value='',
                        column_comment=f'Arrow type: {field.type}',
                        ordinal_position=i
                    ))
            
            else:
                # Get columns for all tables
                tables = self.get_tables()
                for table in tables:
                    if table.table_type != 'ERROR':
                        table_columns = self.get_columns(table.table_name)
                        columns.extend(table_columns)
        
        except Exception as e:
            columns.append(ColumnInfo(
                table_name=table_name or 'unknown',
                column_name='_error',
                data_type='error',
                max_length=0,
                is_nullable=True,
                default_value=str(e),
                column_comment='Error retrieving schema',
                ordinal_position=1
            ))
        
        return columns
    
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get Delta Lake relationships (none - file-based storage)"""
        # Delta Lake doesn't have formal relationships
        return []
    
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Get Delta Lake partitioning information (equivalent to indexes)"""
        indexes = []
        
        try:
            if table_name:
                table_path = f"{self.base_path}/{table_name}"
                dt = DeltaTable(table_path, storage_options=self.storage_options)
                
                # Check if table is partitioned
                # This requires examining the metadata
                metadata = dt.metadata()
                partition_columns = metadata.partition_columns
                
                if partition_columns:
                    indexes.append(IndexInfo(
                        index_name=f"PARTITION_{table_name}",
                        table_name=table_name,
                        column_names=partition_columns,
                        is_unique=False,
                        index_type='PARTITION',
                        is_primary=False
                    ))
            
            else:
                # Get indexes for all tables
                tables = self.get_tables()
                for table in tables:
                    if table.table_type != 'ERROR':
                        table_indexes = self.get_indexes(table.table_name)
                        indexes.extend(table_indexes)
        
        except Exception:
            pass
        
        return indexes
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze Delta Lake data distribution"""
        try:
            table_path = f"{self.base_path}/{table_name}"
            dt = DeltaTable(table_path, storage_options=self.storage_options)
            
            # Convert to pandas for analysis
            df = dt.to_pandas()
            
            if column_name not in df.columns:
                return {"error": f"Column {column_name} not found"}
            
            column_data = df[column_name]
            
            # Calculate statistics
            total_count = len(df)
            non_null_count = column_data.notna().sum()
            null_count = column_data.isna().sum()
            unique_count = column_data.nunique()
            
            # Sample values
            sample_values = column_data.dropna().sample(min(sample_size, non_null_count)).tolist()[:10]
            
            # Calculate percentages
            null_percentage = null_count / total_count if total_count > 0 else 0
            unique_percentage = unique_count / non_null_count if non_null_count > 0 else 0
            
            return {
                "total_count": total_count,
                "unique_count": unique_count,
                "null_count": null_count,
                "null_percentage": round(null_percentage, 4),
                "unique_percentage": round(unique_percentage, 4),
                "sample_values": sample_values
            }
        
        except Exception as e:
            return {"error": str(e), "analysis_failed": True}
    
    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from Delta Lake table"""
        try:
            table_path = f"{self.base_path}/{table_name}"
            dt = DeltaTable(table_path, storage_options=self.storage_options)
            
            # Convert to pandas and sample
            df = dt.to_pandas().head(limit)
            
            return df.to_dict('records')
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_table_history(self, table_name: str) -> List[Dict[str, Any]]:
        """Get Delta Lake table history"""
        try:
            table_path = f"{self.base_path}/{table_name}"
            dt = DeltaTable(table_path, storage_options=self.storage_options)
            
            history = dt.history()
            return history.to_dict('records')
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_database_version(self) -> str:
        """Get Delta Lake version info"""
        try:
            import deltalake
            return f"Delta Lake {deltalake.__version__}"
        except Exception:
            return "Delta Lake Unknown"
    
    def time_travel_query(self, table_name: str, version: Optional[int] = None, 
                         timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query Delta Lake table at specific version or timestamp"""
        try:
            table_path = f"{self.base_path}/{table_name}"
            
            if version is not None:
                dt = DeltaTable(table_path, version=version, storage_options=self.storage_options)
            elif timestamp is not None:
                dt = DeltaTable(table_path, storage_options=self.storage_options)
                # Note: timestamp-based queries require additional implementation
            else:
                dt = DeltaTable(table_path, storage_options=self.storage_options)
            
            df = dt.to_pandas().head(10)  # Limit for safety
            return df.to_dict('records')
        except Exception as e:
            return [{"error": str(e)}]
    
    def optimize_table(self, table_name: str) -> Dict[str, Any]:
        """Optimize Delta Lake table (compact files)"""
        try:
            table_path = f"{self.base_path}/{table_name}"
            dt = DeltaTable(table_path, storage_options=self.storage_options)
            
            # Run optimization
            dt.optimize.compact()
            
            return {
                "status": "success",
                "operation": "optimize",
                "table": table_name,
                "message": "Table compaction completed"
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    def vacuum_table(self, table_name: str, retention_hours: int = 168) -> Dict[str, Any]:
        """Vacuum Delta Lake table (remove old files)"""
        try:
            table_path = f"{self.base_path}/{table_name}"
            dt = DeltaTable(table_path, storage_options=self.storage_options)
            
            # Run vacuum
            dt.vacuum(retention_hours=retention_hours)
            
            return {
                "status": "success",
                "operation": "vacuum",
                "table": table_name,
                "retention_hours": retention_hours,
                "message": f"Vacuum completed with {retention_hours} hours retention"
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}