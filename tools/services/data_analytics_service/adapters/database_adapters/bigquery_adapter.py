#!/usr/bin/env python3
"""
Google BigQuery data warehouse adapter
"""

from typing import Dict, List, Any, Optional
from .base_adapter import DatabaseAdapter
from ...processors.data_processors.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

try:
    from google.cloud import bigquery
    from google.oauth2 import service_account
    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False

class BigQueryAdapter(DatabaseAdapter):
    """Google BigQuery data warehouse adapter"""
    
    def __init__(self):
        super().__init__()
        if not BIGQUERY_AVAILABLE:
            raise ImportError("google-cloud-bigquery is required for BigQuery adapter. Install with: pip install google-cloud-bigquery")
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create BigQuery connection"""
        # Authentication methods
        if 'service_account_path' in config:
            # Service account file
            credentials = service_account.Credentials.from_service_account_file(config['service_account_path'])
            client = bigquery.Client(
                credentials=credentials,
                project=config['project_id']
            )
        elif 'service_account_info' in config:
            # Service account info (dict)
            credentials = service_account.Credentials.from_service_account_info(config['service_account_info'])
            client = bigquery.Client(
                credentials=credentials,
                project=config['project_id']
            )
        else:
            # Default authentication (using environment variables or gcloud)
            client = bigquery.Client(project=config['project_id'])
        
        # Set default dataset if provided
        if 'dataset' in config:
            self.default_dataset = config['dataset']
        else:
            self.default_dataset = None
        
        self.project_id = config['project_id']
        self.client = client
        return client
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute BigQuery query"""
        try:
            # Configure query job
            job_config = bigquery.QueryJobConfig()
            
            # Set parameters if provided
            if params:
                # Convert tuple to list of BigQuery parameters
                job_config.query_parameters = []
                for i, param in enumerate(params):
                    job_config.query_parameters.append(
                        bigquery.ScalarQueryParameter(f"param_{i}", "STRING", str(param))
                    )
            
            # Execute query
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()  # Wait for job to complete
            
            # Convert results to list of dictionaries
            rows = []
            for row in results:
                row_dict = {}
                for field in results.schema:
                    value = row[field.name]
                    # Convert BigQuery types to Python types
                    if hasattr(value, 'isoformat'):  # datetime objects
                        value = value.isoformat()
                    elif isinstance(value, bytes):
                        value = value.decode('utf-8')
                    row_dict[field.name] = value
                rows.append(row_dict)
            
            return rows
        except Exception as e:
            raise e
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get BigQuery table information"""
        tables = []
        
        try:
            # Get datasets to search
            datasets_to_search = schema_filter if schema_filter else []
            if not datasets_to_search and self.default_dataset:
                datasets_to_search = [self.default_dataset]
            
            if not datasets_to_search:
                # Get all datasets in the project
                datasets = list(self.client.list_datasets(self.project_id))
                datasets_to_search = [dataset.dataset_id for dataset in datasets]
            
            # Get tables from each dataset
            for dataset_id in datasets_to_search:
                try:
                    dataset_ref = self.client.dataset(dataset_id, project=self.project_id)
                    dataset_tables = list(self.client.list_tables(dataset_ref))
                    
                    for table in dataset_tables:
                        # Get detailed table info
                        try:
                            full_table = self.client.get_table(table.reference)
                            
                            table_type = 'BASE TABLE'
                            if full_table.table_type == 'VIEW':
                                table_type = 'VIEW'
                            elif full_table.table_type == 'EXTERNAL':
                                table_type = 'EXTERNAL'
                            
                            tables.append(TableInfo(
                                table_name=full_table.table_id,
                                schema_name=full_table.dataset_id,
                                table_type=table_type,
                                record_count=full_table.num_rows or 0,
                                table_comment=full_table.description or '',
                                created_date=full_table.created.isoformat() if full_table.created else '',
                                last_modified=full_table.modified.isoformat() if full_table.modified else ''
                            ))
                        except Exception:
                            # Add basic table info if detailed info fails
                            tables.append(TableInfo(
                                table_name=table.table_id,
                                schema_name=dataset_id,
                                table_type='BASE TABLE',
                                record_count=0,
                                table_comment='',
                                created_date='',
                                last_modified=''
                            ))
                
                except Exception as e:
                    # Add error entry for dataset
                    tables.append(TableInfo(
                        table_name='error',
                        schema_name=dataset_id,
                        table_type='ERROR',
                        record_count=0,
                        table_comment=f'Error accessing dataset: {str(e)}',
                        created_date='',
                        last_modified=''
                    ))
        
        except Exception as e:
            tables.append(TableInfo(
                table_name='global_error',
                schema_name='error',
                table_type='ERROR',
                record_count=0,
                table_comment=f'Error retrieving tables: {str(e)}',
                created_date='',
                last_modified=''
            ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get BigQuery column information"""
        columns = []
        
        try:
            if table_name:
                # Get columns for specific table
                # Assume format: dataset.table or just table (use default dataset)
                if '.' in table_name:
                    dataset_id, table_id = table_name.split('.', 1)
                else:
                    dataset_id = self.default_dataset
                    table_id = table_name
                
                if not dataset_id:
                    raise ValueError("No dataset specified and no default dataset set")
                
                table_ref = self.client.dataset(dataset_id, project=self.project_id).table(table_id)
                table = self.client.get_table(table_ref)
                
                for i, field in enumerate(table.schema, 1):
                    columns.append(ColumnInfo(
                        table_name=table_id,
                        column_name=field.name,
                        data_type=field.field_type,
                        max_length=0,  # BigQuery doesn't specify max length
                        is_nullable=field.mode != 'REQUIRED',
                        default_value='',
                        column_comment=field.description or '',
                        ordinal_position=i
                    ))
            
            else:
                # Get columns for all tables
                tables = self.get_tables()
                for table in tables:
                    if table.table_type != 'ERROR':
                        table_columns = self.get_columns(f"{table.schema_name}.{table.table_name}")
                        columns.extend(table_columns)
        
        except Exception as e:
            columns.append(ColumnInfo(
                table_name=table_name or 'unknown',
                column_name='_error',
                data_type='error',
                max_length=0,
                is_nullable=True,
                default_value=str(e),
                column_comment='Error retrieving columns',
                ordinal_position=1
            ))
        
        return columns
    
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get BigQuery relationships (limited - no formal foreign keys)"""
        # BigQuery doesn't have traditional foreign key constraints
        # But we can analyze table/column naming patterns or metadata
        relationships = []
        
        try:
            # This is a simplified implementation
            # In practice, you might analyze:
            # 1. Column naming patterns (e.g., user_id references users.id)
            # 2. Table metadata/comments
            # 3. Data lineage information
            
            tables = self.get_tables()
            
            # Look for common ID patterns
            for table in tables:
                if table.table_type == 'ERROR':
                    continue
                
                try:
                    columns = self.get_columns(f"{table.schema_name}.{table.table_name}")
                    
                    for column in columns:
                        # Simple heuristic: column ending with _id might reference another table
                        if column.column_name.endswith('_id') and column.column_name != 'id':
                            potential_table = column.column_name[:-3]  # Remove '_id'
                            
                            # Check if potential referenced table exists
                            for ref_table in tables:
                                if ref_table.table_name.lower() == potential_table.lower():
                                    relationships.append(RelationshipInfo(
                                        constraint_name=f"{table.table_name}_{column.column_name}_ref",
                                        from_table=table.table_name,
                                        from_column=column.column_name,
                                        to_table=ref_table.table_name,
                                        to_column='id',
                                        constraint_type='INFERRED_REFERENCE'
                                    ))
                                    break
                
                except Exception:
                    continue
        
        except Exception:
            pass  # Relationship discovery is best-effort
        
        return relationships
    
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Get BigQuery clustering/partitioning info (equivalent to indexes)"""
        indexes = []
        
        try:
            if table_name:
                # Get clustering/partitioning for specific table
                if '.' in table_name:
                    dataset_id, table_id = table_name.split('.', 1)
                else:
                    dataset_id = self.default_dataset
                    table_id = table_name
                
                if not dataset_id:
                    return indexes
                
                table_ref = self.client.dataset(dataset_id, project=self.project_id).table(table_id)
                table = self.client.get_table(table_ref)
                
                # Check for partitioning
                if table.time_partitioning:
                    partition_field = table.time_partitioning.field or '_PARTITIONTIME'
                    indexes.append(IndexInfo(
                        index_name=f"PARTITION_{table_id}",
                        table_name=table_id,
                        column_names=[partition_field],
                        is_unique=False,
                        index_type='PARTITION',
                        is_primary=False
                    ))
                
                # Check for clustering
                if table.clustering_fields:
                    indexes.append(IndexInfo(
                        index_name=f"CLUSTER_{table_id}",
                        table_name=table_id,
                        column_names=list(table.clustering_fields),
                        is_unique=False,
                        index_type='CLUSTERING',
                        is_primary=False
                    ))
            
            else:
                # Get indexes for all tables
                tables = self.get_tables()
                for table in tables:
                    if table.table_type != 'ERROR':
                        table_indexes = self.get_indexes(f"{table.schema_name}.{table.table_name}")
                        indexes.extend(table_indexes)
        
        except Exception:
            pass
        
        return indexes
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze BigQuery data distribution"""
        try:
            # Ensure proper table reference
            if '.' not in table_name and self.default_dataset:
                table_name = f"`{self.project_id}.{self.default_dataset}.{table_name}`"
            elif '.' in table_name:
                parts = table_name.split('.')
                if len(parts) == 2:
                    table_name = f"`{self.project_id}.{parts[0]}.{parts[1]}`"
            
            # Basic statistics query
            stats_query = f"""
            SELECT 
                COUNT(*) as total_count,
                COUNT(DISTINCT `{column_name}`) as unique_count,
                COUNT(`{column_name}`) as non_null_count,
                COUNT(*) - COUNT(`{column_name}`) as null_count
            FROM {table_name}
            """
            
            stats_result = self._execute_query(stats_query)
            if not stats_result:
                return {"error": "No data found"}
            
            stats = stats_result[0]
            
            # Sample data query
            sample_query = f"""
            SELECT `{column_name}` 
            FROM {table_name} 
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
        """Get sample data from BigQuery table"""
        try:
            # Ensure proper table reference
            if '.' not in table_name and self.default_dataset:
                table_name = f"`{self.project_id}.{self.default_dataset}.{table_name}`"
            elif '.' in table_name:
                parts = table_name.split('.')
                if len(parts) == 2:
                    table_name = f"`{self.project_id}.{parts[0]}.{parts[1]}`"
            
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            return self._execute_query(query)
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_table_size(self, table_name: str) -> Dict[str, Any]:
        """Get BigQuery table size information"""
        try:
            if '.' not in table_name and self.default_dataset:
                dataset_id = self.default_dataset
                table_id = table_name
            else:
                dataset_id, table_id = table_name.split('.', 1)
            
            table_ref = self.client.dataset(dataset_id, project=self.project_id).table(table_id)
            table = self.client.get_table(table_ref)
            
            return {
                "num_rows": table.num_rows or 0,
                "num_bytes": table.num_bytes or 0,
                "size_mb": (table.num_bytes or 0) / (1024 * 1024),
                "created": table.created.isoformat() if table.created else None,
                "modified": table.modified.isoformat() if table.modified else None
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_database_version(self) -> str:
        """Get BigQuery version info"""
        try:
            # BigQuery doesn't have a traditional version, but we can get service info
            query = "SELECT @@version.query_engine as version"
            result = self._execute_query(query)
            return result[0]['version'] if result else "BigQuery Standard"
        except Exception:
            return "BigQuery Standard"
    
    def execute_dry_run(self, query: str) -> Dict[str, Any]:
        """Execute BigQuery dry run to estimate query cost"""
        try:
            job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
            query_job = self.client.query(query, job_config=job_config)
            
            return {
                "bytes_processed": query_job.total_bytes_processed,
                "bytes_billed": query_job.total_bytes_billed,
                "estimated_cost_usd": (query_job.total_bytes_billed or 0) * 5.0 / (1024**4),  # $5 per TB
                "cache_hit": query_job.cache_hit,
                "valid": True
            }
        except Exception as e:
            return {"error": str(e), "valid": False}