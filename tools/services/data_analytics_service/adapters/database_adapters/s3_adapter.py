#!/usr/bin/env python3
"""
S3/MinIO object storage adapter for data lake operations
"""

from typing import Dict, List, Any, Optional
from .base_adapter import DatabaseAdapter
from ...processors.data_processors.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    import io
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False

class S3Adapter(DatabaseAdapter):
    """S3/MinIO object storage adapter for data lake operations"""
    
    def __init__(self):
        super().__init__()
        if not S3_AVAILABLE:
            raise ImportError("boto3, pandas, and pyarrow are required for S3 adapter. Install with: pip install boto3 pandas pyarrow")
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create S3/MinIO connection"""
        # S3/MinIO configuration
        session_config = {
            'aws_access_key_id': config.get('access_key_id'),
            'aws_secret_access_key': config.get('secret_access_key'),
            'region_name': config.get('region', 'us-east-1')
        }
        
        # Support for custom endpoint (MinIO)
        if 'endpoint_url' in config:
            session_config['endpoint_url'] = config['endpoint_url']
        
        # Create session and client
        session = boto3.Session(**{k: v for k, v in session_config.items() if k != 'endpoint_url' and v})
        
        client_config = {}
        if 'endpoint_url' in config:
            client_config['endpoint_url'] = config['endpoint_url']
        
        self.s3_client = session.client('s3', **client_config)
        self.bucket_name = config['bucket_name']
        self.prefix = config.get('prefix', '')
        
        # Test connection
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise ConnectionError(f"Bucket '{self.bucket_name}' not found")
            else:
                raise ConnectionError(f"Error accessing bucket: {e}")
        
        return self.s3_client
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute S3 query (limited operations)"""
        try:
            query_upper = query.strip().upper()
            
            if query_upper.startswith('LIST'):
                # List objects
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=self.prefix
                )
                
                objects = response.get('Contents', [])
                return [{
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag'].strip('"')
                } for obj in objects]
            
            elif query_upper.startswith('SELECT'):
                # Basic SELECT from a file (Parquet/CSV)
                # Parse file path from query
                parts = query.split()
                if 'FROM' in [p.upper() for p in parts]:
                    from_idx = next(i for i, part in enumerate(parts) if part.upper() == 'FROM')
                    if from_idx + 1 < len(parts):
                        file_path = parts[from_idx + 1].strip('"\'')
                        return self._read_file_data(file_path, limit=100)
            
            elif query_upper.startswith('DESCRIBE'):
                # Describe file structure
                parts = query.split()
                if len(parts) >= 2:
                    file_path = parts[1].strip('"\'')
                    return self._describe_file(file_path)
            
            return []
        except Exception as e:
            raise e
    
    def _read_file_data(self, file_path: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Read data from S3 file"""
        try:
            full_key = f"{self.prefix}/{file_path}".strip('/')
            
            # Get object
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=full_key)
            file_content = response['Body'].read()
            
            # Determine file type and read accordingly
            if file_path.lower().endswith('.parquet'):
                # Parquet file
                parquet_file = pq.ParquetFile(io.BytesIO(file_content))
                table = parquet_file.read()
                df = table.to_pandas().head(limit)
                return df.to_dict('records')
            
            elif file_path.lower().endswith('.csv'):
                # CSV file
                df = pd.read_csv(io.BytesIO(file_content)).head(limit)
                return df.to_dict('records')
            
            elif file_path.lower().endswith('.json'):
                # JSON file
                df = pd.read_json(io.BytesIO(file_content)).head(limit)
                return df.to_dict('records')
            
            else:
                # Try to read as text
                text_content = file_content.decode('utf-8')[:1000]  # First 1000 chars
                return [{'content': text_content, 'file_type': 'text'}]
        
        except Exception as e:
            return [{'error': str(e)}]
    
    def _describe_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Describe file structure"""
        try:
            full_key = f"{self.prefix}/{file_path}".strip('/')
            
            # Get object metadata
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=full_key)
            
            result = [{
                'file_path': file_path,
                'size': response['ContentLength'],
                'last_modified': response['LastModified'].isoformat(),
                'content_type': response.get('ContentType', 'unknown')
            }]
            
            # If it's a structured file, get schema information
            if file_path.lower().endswith('.parquet'):
                try:
                    obj_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=full_key)
                    file_content = obj_response['Body'].read()
                    parquet_file = pq.ParquetFile(io.BytesIO(file_content))
                    schema = parquet_file.schema_arrow
                    
                    for field in schema:
                        result.append({
                            'column_name': field.name,
                            'data_type': str(field.type),
                            'nullable': field.nullable
                        })
                except Exception:
                    pass
            
            return result
        
        except Exception as e:
            return [{'error': str(e)}]
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get S3 objects/files as tables"""
        tables = []
        
        try:
            # List objects in bucket with prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix)
            
            # Group files by directory/prefix (treating directories as schemas)
            file_groups = {}
            
            for page in page_iterator:
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    
                    # Skip if not a data file
                    if not any(key.lower().endswith(ext) for ext in ['.parquet', '.csv', '.json', '.orc', '.avro']):
                        continue
                    
                    # Extract directory and file name
                    if '/' in key:
                        dir_path = '/'.join(key.split('/')[:-1])
                        file_name = key.split('/')[-1]
                    else:
                        dir_path = 'root'
                        file_name = key
                    
                    if dir_path not in file_groups:
                        file_groups[dir_path] = []
                    
                    file_groups[dir_path].append({
                        'key': key,
                        'name': file_name,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
            
            # Convert file groups to tables
            for dir_path, files in file_groups.items():
                for file_info in files:
                    # Determine table type based on file extension
                    file_ext = file_info['name'].split('.')[-1].upper()
                    table_type = f"{file_ext}_FILE"
                    
                    # Estimate record count (rough approximation)
                    estimated_records = 0
                    if file_ext in ['PARQUET', 'CSV']:
                        # Very rough estimation: 1 record per 100 bytes for CSV, 1 per 50 for Parquet
                        multiplier = 50 if file_ext == 'PARQUET' else 100
                        estimated_records = file_info['size'] // multiplier
                    
                    tables.append(TableInfo(
                        table_name=file_info['name'].split('.')[0],  # Remove extension
                        schema_name=dir_path,
                        table_type=table_type,
                        record_count=estimated_records,
                        table_comment=f"S3 object: {file_info['key']} ({file_info['size']} bytes)",
                        created_date='',  # S3 doesn't track creation date
                        last_modified=file_info['last_modified'].isoformat()
                    ))
        
        except Exception as e:
            tables.append(TableInfo(
                table_name='error',
                schema_name='s3',
                table_type='ERROR',
                record_count=0,
                table_comment=f'Error listing S3 objects: {str(e)}',
                created_date='',
                last_modified=''
            ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get S3 file schema information"""
        columns = []
        
        try:
            if table_name:
                # Find the file corresponding to this table
                tables = self.get_tables()
                target_table = None
                for table in tables:
                    if table.table_name == table_name:
                        target_table = table
                        break
                
                if target_table and target_table.table_type != 'ERROR':
                    # Extract file path from table comment
                    comment = target_table.table_comment
                    if 'S3 object: ' in comment:
                        file_key = comment.split('S3 object: ')[1].split(' (')[0]
                        
                        # Read file schema
                        try:
                            if file_key.lower().endswith('.parquet'):
                                obj_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
                                file_content = obj_response['Body'].read()
                                parquet_file = pq.ParquetFile(io.BytesIO(file_content))
                                schema = parquet_file.schema_arrow
                                
                                for i, field in enumerate(schema, 1):
                                    columns.append(ColumnInfo(
                                        table_name=table_name,
                                        column_name=field.name,
                                        data_type=str(field.type),
                                        max_length=0,
                                        is_nullable=field.nullable,
                                        default_value='',
                                        column_comment=f'Parquet field: {field.type}',
                                        ordinal_position=i
                                    ))
                            
                            elif file_key.lower().endswith('.csv'):
                                # For CSV, read first few rows to infer schema
                                obj_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
                                file_content = obj_response['Body'].read()
                                df = pd.read_csv(io.BytesIO(file_content), nrows=100)
                                
                                for i, (col_name, dtype) in enumerate(df.dtypes.items(), 1):
                                    columns.append(ColumnInfo(
                                        table_name=table_name,
                                        column_name=col_name,
                                        data_type=str(dtype),
                                        max_length=0,
                                        is_nullable=True,  # CSV columns are typically nullable
                                        default_value='',
                                        column_comment=f'Inferred from CSV: {dtype}',
                                        ordinal_position=i
                                    ))
                        
                        except Exception as e:
                            columns.append(ColumnInfo(
                                table_name=table_name,
                                column_name='_error',
                                data_type='error',
                                max_length=0,
                                is_nullable=True,
                                default_value=str(e),
                                column_comment='Error reading file schema',
                                ordinal_position=1
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
                column_name='_global_error',
                data_type='error',
                max_length=0,
                is_nullable=True,
                default_value=str(e),
                column_comment='Error retrieving columns',
                ordinal_position=1
            ))
        
        return columns
    
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get S3 relationships (none - object storage)"""
        # Object storage doesn't have relationships
        return []
    
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Get S3 partitioning information"""
        indexes = []
        
        try:
            # Look for partitioned data based on directory structure
            tables = self.get_tables()
            
            for table in tables:
                if table.table_type != 'ERROR':
                    # Check if data appears to be partitioned by directory structure
                    # Common patterns: year=2023/month=01/ or dt=2023-01-01/
                    schema_path = table.schema_name
                    
                    if '=' in schema_path:
                        # Hive-style partitioning
                        partition_parts = schema_path.split('/')
                        partition_columns = []
                        
                        for part in partition_parts:
                            if '=' in part:
                                partition_columns.append(part.split('=')[0])
                        
                        if partition_columns:
                            indexes.append(IndexInfo(
                                index_name=f"PARTITION_{table.table_name}",
                                table_name=table.table_name,
                                column_names=partition_columns,
                                is_unique=False,
                                index_type='HIVE_PARTITION',
                                is_primary=False
                            ))
        
        except Exception:
            pass
        
        return indexes
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze S3 file data distribution"""
        try:
            # Read sample data from file
            sample_data = self._read_file_data(f"{table_name}.parquet", limit=sample_size)
            
            if not sample_data or 'error' in sample_data[0]:
                # Try other file extensions
                for ext in ['csv', 'json']:
                    sample_data = self._read_file_data(f"{table_name}.{ext}", limit=sample_size)
                    if sample_data and 'error' not in sample_data[0]:
                        break
            
            if not sample_data or 'error' in sample_data[0]:
                return {"error": "Could not read data for analysis"}
            
            # Convert to pandas for analysis
            df = pd.DataFrame(sample_data)
            
            if column_name not in df.columns:
                return {"error": f"Column {column_name} not found"}
            
            column_data = df[column_name]
            
            # Calculate statistics
            total_count = len(df)
            non_null_count = column_data.notna().sum()
            null_count = column_data.isna().sum()
            unique_count = column_data.nunique()
            
            # Sample values
            sample_values = column_data.dropna().head(10).tolist()
            
            # Calculate percentages
            null_percentage = null_count / total_count if total_count > 0 else 0
            unique_percentage = unique_count / non_null_count if non_null_count > 0 else 0
            
            return {
                "total_count": total_count,
                "unique_count": unique_count,
                "null_count": null_count,
                "null_percentage": round(null_percentage, 4),
                "unique_percentage": round(unique_percentage, 4),
                "sample_values": sample_values,
                "note": "Analysis based on sample data"
            }
        
        except Exception as e:
            return {"error": str(e), "analysis_failed": True}
    
    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from S3 file"""
        try:
            # Try different file extensions
            for ext in ['parquet', 'csv', 'json']:
                result = self._read_file_data(f"{table_name}.{ext}", limit=limit)
                if result and 'error' not in result[0]:
                    return result
            
            return [{"error": f"Could not find readable file for table {table_name}"}]
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_database_version(self) -> str:
        """Get S3 service version"""
        return "AWS S3 / MinIO Object Storage"
    
    def get_bucket_info(self) -> Dict[str, Any]:
        """Get S3 bucket information"""
        try:
            # Get bucket metadata
            bucket_location = self.s3_client.get_bucket_location(Bucket=self.bucket_name)
            
            # Get bucket size and object count (approximation)
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix)
            
            total_size = 0
            object_count = 0
            
            for page in page_iterator:
                for obj in page.get('Contents', []):
                    total_size += obj['Size']
                    object_count += 1
            
            return {
                "bucket_name": self.bucket_name,
                "region": bucket_location.get('LocationConstraint', 'us-east-1'),
                "prefix": self.prefix,
                "total_objects": object_count,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def upload_file(self, local_path: str, s3_key: str) -> Dict[str, Any]:
        """Upload file to S3"""
        try:
            full_key = f"{self.prefix}/{s3_key}".strip('/')
            self.s3_client.upload_file(local_path, self.bucket_name, full_key)
            
            return {
                "status": "success",
                "operation": "upload",
                "local_path": local_path,
                "s3_key": full_key,
                "bucket": self.bucket_name
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    def download_file(self, s3_key: str, local_path: str) -> Dict[str, Any]:
        """Download file from S3"""
        try:
            full_key = f"{self.prefix}/{s3_key}".strip('/')
            self.s3_client.download_file(self.bucket_name, full_key, local_path)
            
            return {
                "status": "success",
                "operation": "download",
                "s3_key": full_key,
                "local_path": local_path,
                "bucket": self.bucket_name
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}