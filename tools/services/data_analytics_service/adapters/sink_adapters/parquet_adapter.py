#!/usr/bin/env python3
"""
Parquet Sink Adapter
Stores data TO Parquet files in MinIO object storage for efficient columnar storage
"""

import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import io
import uuid
from datetime import datetime

from .base_sink_adapter import BaseSinkAdapter
from core.minio_client import get_minio_client

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
            
            # Ensure bucket exists
            if not self.minio_client.ensure_bucket_exists(bucket_name):
                return False
            
            # Store connection info
            self.storage_info = {
                'bucket_name': bucket_name,
                'base_path': base_path,
                'storage_type': 'parquet_minio',
                'pyarrow_available': self.pyarrow_available,
                'minio_available': self.minio_client.is_available(),
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
    
    def store_dataframe(self, df: pd.DataFrame, 
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
            
            # Upload parquet to MinIO
            bucket_name = self.storage_info['bucket_name']
            parquet_uploaded = self.minio_client.upload_data(
                data=parquet_bytes,
                object_name=paths['parquet_path'],
                bucket_name=bucket_name,
                content_type='application/octet-stream'
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
                
                metadata_uploaded = self.minio_client.upload_data(
                    data=metadata_bytes,
                    object_name=paths['metadata_path'],
                    bucket_name=bucket_name,
                    content_type='application/json'
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
    
    def _dataframe_to_parquet_bytes(self, df: pd.DataFrame, compression: str) -> Optional[bytes]:
        """Convert DataFrame to Parquet bytes with compression"""
        try:
            buffer = io.BytesIO()
            
            # Configure parquet options
            parquet_options = {
                'compression': compression,
                'index': False,  # Don't store DataFrame index
                'engine': 'pyarrow' if self.pyarrow_available else 'auto'
            }
            
            # Write to buffer
            df.to_parquet(buffer, **parquet_options)
            parquet_bytes = buffer.getvalue()
            buffer.close()
            
            logger.debug(f"Converted DataFrame to Parquet: {len(parquet_bytes)} bytes with {compression} compression")
            return parquet_bytes
            
        except Exception as e:
            logger.error(f"Failed to convert DataFrame to Parquet: {e}")
            return None
    
    def _extract_dataframe_metadata(self, df: pd.DataFrame, user_id: str, dataset_name: str, storage_id: str) -> Dict[str, Any]:
        """Extract comprehensive metadata from DataFrame"""
        metadata = {
            'storage_id': storage_id,
            'dataset_name': dataset_name,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'shape': {
                'rows': len(df),
                'columns': len(df.columns)
            },
            'columns': {
                col: {
                    'dtype': str(df[col].dtype),
                    'null_count': int(df[col].isnull().sum()),
                    'unique_count': int(df[col].nunique()),
                    'sample_values': df[col].dropna().head(3).tolist() if not df[col].empty else []
                } for col in df.columns
            },
            'data_types': {
                'numeric_columns': df.select_dtypes(include=['number']).columns.tolist(),
                'categorical_columns': df.select_dtypes(include=['object', 'category']).columns.tolist(),
                'datetime_columns': df.select_dtypes(include=['datetime']).columns.tolist()
            },
            'statistics': {
                'total_null_values': int(df.isnull().sum().sum()),
                'duplicate_rows': int(df.duplicated().sum()),
                'memory_usage_mb': round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2)
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
        
        # Generate URL for parquet file
        parquet_url = self.minio_client.get_presigned_url(
            object_name=paths['parquet_path'],
            bucket_name=bucket_name,
            expires_in_seconds=3600  # 1 hour
        )
        if parquet_url:
            urls['parquet'] = parquet_url
        
        # Generate URL for metadata if exists
        if 'metadata_path' in paths:
            metadata_url = self.minio_client.get_presigned_url(
                object_name=paths['metadata_path'],
                bucket_name=bucket_name,
                expires_in_seconds=3600
            )
            if metadata_url:
                urls['metadata'] = metadata_url
        
        return urls
    
    def _calculate_compression_ratio(self, df: pd.DataFrame, parquet_bytes: bytes) -> float:
        """Calculate compression ratio compared to CSV"""
        try:
            # Estimate CSV size (rough approximation)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_size = len(csv_buffer.getvalue().encode('utf-8'))
            csv_buffer.close()
            
            if csv_size > 0:
                return round(len(parquet_bytes) / csv_size, 3)
            else:
                return 0.0
        except:
            return 0.0
    
    def read_parquet(self, object_path: str, bucket_name: Optional[str] = None, **kwargs) -> pd.DataFrame:
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
                return pd.DataFrame()
            
            buffer = io.BytesIO(parquet_bytes)
            df = pd.read_parquet(buffer, **kwargs)
            buffer.close()
            
            logger.info(f"Loaded DataFrame from MinIO: {df.shape} from {object_path}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to read Parquet file from MinIO: {e}")
            return pd.DataFrame()
    
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