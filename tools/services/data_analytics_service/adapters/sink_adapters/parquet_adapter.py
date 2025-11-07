#!/usr/bin/env python3
"""
Parquet Sink Adapter
Stores data TO Parquet files in MinIO object storage for efficient columnar storage
"""

import polars as pl
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import io
import uuid
from datetime import datetime

from .base_sink_adapter import BaseSinkAdapter
from core.clients.minio_client import get_minio_client

logger = logging.getLogger(__name__)

class ParquetSinkAdapter(BaseSinkAdapter):
    """
    Parquet sink adapter for storing data in MinIO object storage as Parquet format
    
    Features:
    - MinIO object storage with Parquet format
    - Columnar storage efficiency
    - Fast compression
    - Schema preservation
    - Automatic bucket management
    - Metadata extraction and storage
    """
    
    def __init__(self):
        super().__init__()
        self.pyarrow_available = False
        self.minio_client = get_minio_client()
        
        # Check for pyarrow availability
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
            self.pyarrow_available = True
            self.pa = pa
            self.pq = pq
        except ImportError:
            logger.warning("PyArrow not available. Install with: pip install pyarrow")
    
    def connect(self, destination: str, **kwargs) -> bool:
        """
        Prepare for MinIO Parquet storage
        
        Args:
            destination: Bucket name or bucket/path
            **kwargs: Additional configuration (user_id, etc.)
            
        Returns:
            True if setup successful
        """
        try:
            # Parse destination (bucket or bucket/path)
            if '/' in destination:
                bucket_name, base_path = destination.split('/', 1)
            else:
                bucket_name = destination
                base_path = ""
            
            # Ensure bucket exists (isa-common MinIOClient API)
            if not self.minio_client.bucket_exists(bucket_name):
                if not self.minio_client.create_bucket(bucket_name):
                    logger.error(f"Failed to create bucket: {bucket_name}")
                    return False

            # Store connection info
            health_status = self.minio_client.health_check(detailed=False)
            self.storage_info = {
                'bucket_name': bucket_name,
                'base_path': base_path,
                'storage_type': 'parquet_minio',
                'pyarrow_available': self.pyarrow_available,
                'minio_available': health_status is not None if health_status else False,
                'user_id': kwargs.get('user_id', 'default_user')
            }
            
            logger.info(f"Parquet MinIO adapter ready for bucket: {bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Parquet MinIO adapter: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Cleanup resources"""
        # MinIO client is managed globally
        return True
    
    def store_dataframe(self, df: pl.DataFrame,
                       destination: str,
                       table_name: Optional[str] = None,
                       storage_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Store DataFrame as Parquet file in MinIO
        
        Args:
            df: DataFrame to store
            destination: Bucket name or bucket/path
            table_name: Object name prefix
            storage_options: MinIO-specific options
            
        Returns:
            Storage result information
        """
        start_time = datetime.now()
        storage_id = f"storage_{uuid.uuid4().hex[:8]}"
        
        try:
            # Validate DataFrame
            validation = self.validate_dataframe(df)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': f"DataFrame validation failed: {validation['errors']}",
                    'warnings': validation['warnings']
                }
            
            # Setup if not already done
            if not self.storage_info:
                if not self.connect(destination, **storage_options or {}):
                    return {
                        'success': False,
                        'error': 'Failed to setup Parquet MinIO adapter'
                    }
            
            # Prepare storage options
            options = storage_options or {}
            compression = options.get('compression', 'snappy')
            include_metadata = options.get('include_metadata', True)
            user_id = self.storage_info.get('user_id', 'default_user')
            
            # Generate object paths
            dataset_name = self._sanitize_table_name(table_name or 'data')
            paths = self._generate_storage_paths(user_id, dataset_name, storage_id)
            
            # Convert DataFrame to Parquet bytes
            parquet_bytes = self._dataframe_to_parquet_bytes(df, compression)
            if not parquet_bytes:
                return {
                    'success': False,
                    'error': 'Failed to convert DataFrame to Parquet'
                }
            
            # Upload parquet to MinIO (isa-common MinIOClient API)
            bucket_name = self.storage_info['bucket_name']
            parquet_uploaded = self.minio_client.put_object(
                bucket_name=bucket_name,
                object_key=paths['parquet_path'],
                data=parquet_bytes,
                size=len(parquet_bytes),
                metadata={'content_type': 'application/octet-stream'}
            )
            
            if not parquet_uploaded:
                return {
                    'success': False,
                    'error': 'Failed to upload parquet to MinIO'
                }
            
            # Upload metadata if requested
            metadata_path = None
            if include_metadata:
                metadata = self._extract_dataframe_metadata(df, user_id, dataset_name, storage_id)
                metadata_bytes = self._metadata_to_json_bytes(metadata)

                metadata_uploaded = self.minio_client.put_object(
                    bucket_name=bucket_name,
                    object_key=paths['metadata_path'],
                    data=metadata_bytes,
                    size=len(metadata_bytes),
                    metadata={'content_type': 'application/json'}
                )
                
                if metadata_uploaded:
                    metadata_path = paths['metadata_path']
                else:
                    logger.warning(f"Failed to upload metadata for {storage_id}")
            
            # Generate presigned URLs
            presigned_urls = self._generate_presigned_urls(paths, bucket_name)
            
            storage_duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'storage_id': storage_id,
                'destination': destination,
                'bucket_name': bucket_name,
                'parquet_path': paths['parquet_path'],
                'metadata_path': metadata_path,
                'presigned_urls': presigned_urls,
                'storage_adapter': 'ParquetSinkAdapter',
                'storage_duration': storage_duration,
                'rows_stored': len(df),
                'columns_stored': len(df.columns),
                'file_size_bytes': len(parquet_bytes),
                'file_size_mb': round(len(parquet_bytes) / 1024 / 1024, 2),
                'compression': compression,
                'compression_ratio': self._calculate_compression_ratio(df, parquet_bytes),
                'storage_options_used': options,
                'warnings': validation.get('warnings', [])
            }
            
            self._log_storage_operation('Parquet MinIO storage', True, {
                'bucket': bucket_name,
                'object': paths['parquet_path'],
                'rows': len(df),
                'size': f"{result['file_size_mb']}MB",
                'duration': f"{storage_duration:.2f}s"
            })
            
            return result
            
        except Exception as e:
            storage_duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            
            self._log_storage_operation('Parquet MinIO storage', False, {
                'error': error_msg,
                'duration': f"{storage_duration:.2f}s"
            })
            
            return {
                'success': False,
                'error': error_msg,
                'storage_duration': storage_duration,
                'destination': destination,
                'storage_id': storage_id
            }
    
    def _generate_storage_paths(self, user_id: str, dataset_name: str, storage_id: str) -> Dict[str, str]:
        """Generate MinIO object paths for parquet and metadata files"""
        base_path = self.storage_info.get('base_path', '')
        
        # Create hierarchical path: base_path/user_id/dataset_name/YYYY/MM/DD/
        today = datetime.now()
        date_path = f"{today.year:04d}/{today.month:02d}/{today.day:02d}"
        
        if base_path:
            full_path = f"{base_path}/{user_id}/{dataset_name}/{date_path}"
        else:
            full_path = f"{user_id}/{dataset_name}/{date_path}"
        
        # Add versioning with timestamp
        timestamp = datetime.now().strftime("%H%M%S")
        filename_base = f"{dataset_name}_{timestamp}_{storage_id}"
        
        return {
            'parquet_path': f"{full_path}/{filename_base}.parquet",
            'metadata_path': f"{full_path}/{filename_base}_metadata.json"
        }
    
    def _dataframe_to_parquet_bytes(self, df: pl.DataFrame, compression: str) -> Optional[bytes]:
        """Convert DataFrame to Parquet bytes with compression"""
        try:
            buffer = io.BytesIO()

            # Map compression format (Polars uses slightly different names)
            compression_map = {
                'snappy': 'snappy',
                'gzip': 'gzip',
                'lz4': 'lz4',
                'zstd': 'zstd',
                'brotli': 'brotli',
                'uncompressed': 'uncompressed'
            }
            polars_compression = compression_map.get(compression.lower(), 'snappy')

            # Write to buffer using Polars
            df.write_parquet(buffer, compression=polars_compression)
            parquet_bytes = buffer.getvalue()
            buffer.close()

            logger.debug(f"Converted DataFrame to Parquet: {len(parquet_bytes)} bytes with {compression} compression")
            return parquet_bytes

        except Exception as e:
            logger.error(f"Failed to convert DataFrame to Parquet: {e}")
            return None
    
    def _extract_dataframe_metadata(self, df: pl.DataFrame, user_id: str, dataset_name: str, storage_id: str) -> Dict[str, Any]:
        """Extract comprehensive metadata from DataFrame"""
        # Get numeric, string, and datetime columns
        numeric_columns = [col for col, dtype in df.schema.items() if dtype in [pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64, pl.Float32, pl.Float64]]
        string_columns = [col for col, dtype in df.schema.items() if dtype in [pl.Utf8, pl.Categorical]]
        datetime_columns = [col for col, dtype in df.schema.items() if dtype in [pl.Date, pl.Datetime, pl.Time, pl.Duration]]

        metadata = {
            'storage_id': storage_id,
            'dataset_name': dataset_name,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'shape': {
                'rows': df.height,
                'columns': df.width
            },
            'columns': {
                col: {
                    'dtype': str(df[col].dtype),
                    'null_count': int(df[col].null_count()),
                    'unique_count': int(df[col].n_unique()),
                    'sample_values': df[col].drop_nulls().head(3).to_list() if df[col].len() > 0 else []
                } for col in df.columns
            },
            'data_types': {
                'numeric_columns': numeric_columns,
                'categorical_columns': string_columns,
                'datetime_columns': datetime_columns
            },
            'statistics': {
                'total_null_values': sum(df.null_count().row(0)),  # polars null_count returns DataFrame
                'duplicate_rows': int(df.is_duplicated().sum()),
                'memory_usage_mb': round(df.estimated_size('mb'), 2)
            },
            'storage_config': {
                'storage_type': 'parquet_minio',
                'bucket_name': self.storage_info['bucket_name']
            }
        }

        return metadata
    
    def _metadata_to_json_bytes(self, metadata: Dict[str, Any]) -> bytes:
        """Convert metadata dict to JSON bytes"""
        import json
        
        # Convert any non-serializable types
        def json_serializer(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif hasattr(obj, 'tolist'):
                return obj.tolist()
            else:
                return str(obj)
        
        json_str = json.dumps(metadata, indent=2, default=json_serializer)
        return json_str.encode('utf-8')
    
    def _generate_presigned_urls(self, paths: Dict[str, str], bucket_name: str) -> Dict[str, str]:
        """Generate presigned URLs for accessing stored files"""
        urls = {}
        
        # Generate URL for parquet file (isa-common MinIOClient API)
        parquet_url = self.minio_client.generate_presigned_url(
            bucket_name=bucket_name,
            object_key=paths['parquet_path'],
            expiry_seconds=3600  # 1 hour
        )
        if parquet_url:
            urls['parquet'] = parquet_url
        
        # Generate URL for metadata if exists
        if 'metadata_path' in paths:
            metadata_url = self.minio_client.generate_presigned_url(
                bucket_name=bucket_name,
                object_key=paths['metadata_path'],
                expiry_seconds=3600
            )
            if metadata_url:
                urls['metadata'] = metadata_url
        
        return urls
    
    def _calculate_compression_ratio(self, df: pl.DataFrame, parquet_bytes: bytes) -> float:
        """Calculate compression ratio compared to CSV"""
        try:
            # Estimate CSV size (rough approximation)
            csv_buffer = io.BytesIO()
            df.write_csv(csv_buffer)
            csv_size = len(csv_buffer.getvalue())
            csv_buffer.close()

            if csv_size > 0:
                return round(len(parquet_bytes) / csv_size, 3)
            else:
                return 0.0
        except:
            return 0.0
    
    def read_parquet(self, object_path: str, bucket_name: Optional[str] = None, **kwargs) -> pl.DataFrame:
        """
        Read Parquet file from MinIO back to DataFrame

        Args:
            object_path: MinIO object path to Parquet file
            bucket_name: Bucket name (uses configured bucket if None)
            **kwargs: Additional read options

        Returns:
            DataFrame with loaded data
        """
        try:
            bucket = bucket_name or self.storage_info.get('bucket_name')
            parquet_bytes = self.minio_client.download_data(object_path, bucket)

            if not parquet_bytes:
                logger.error(f"Failed to download parquet from MinIO: {object_path}")
                return pl.DataFrame()

            buffer = io.BytesIO(parquet_bytes)
            df = pl.read_parquet(buffer, **kwargs)
            buffer.close()

            logger.info(f"Loaded DataFrame from MinIO: ({df.height}, {df.width}) from {object_path}")
            return df

        except Exception as e:
            logger.error(f"Failed to read Parquet file from MinIO: {e}")
            return pl.DataFrame()
    
    def list_parquet_objects(self, prefix: Optional[str] = None, bucket_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all Parquet objects in MinIO bucket with metadata"""
        try:
            bucket = bucket_name or self.storage_info.get('bucket_name')
            if not bucket:
                return []
            
            # Get list of objects
            objects = self.minio_client.list_objects(bucket, prefix)
            parquet_objects = [obj for obj in objects if obj.endswith('.parquet')]
            
            files_info = []
            for object_name in parquet_objects:
                try:
                    files_info.append({
                        'object_path': object_name,
                        'object_name': Path(object_name).name,
                        'bucket_name': bucket,
                        'storage_type': 'parquet_minio'
                    })
                        
                except Exception as e:
                    logger.warning(f"Could not get metadata for {object_name}: {e}")
                    continue
            
            return files_info
            
        except Exception as e:
            logger.error(f"Failed to list Parquet objects in MinIO: {e}")
            return []
    
    def get_metadata(self, metadata_path: str, bucket_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load metadata from MinIO JSON file"""
        try:
            bucket = bucket_name or self.storage_info.get('bucket_name')
            metadata_bytes = self.minio_client.download_data(metadata_path, bucket)
            
            if not metadata_bytes:
                return None
            
            import json
            metadata = json.loads(metadata_bytes.decode('utf-8'))
            
            logger.info(f"Loaded metadata from MinIO: {metadata_path}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to load metadata from MinIO: {e}")
            return None