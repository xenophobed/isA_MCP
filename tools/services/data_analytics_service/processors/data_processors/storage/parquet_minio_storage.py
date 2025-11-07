#!/usr/bin/env python3
"""
Parquet MinIO Storage Processor
Handles efficient storage of DataFrames as Parquet files in MinIO object storage
"""

import pandas as pd
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import io
import uuid

from core.clients.minio_client import get_minio_client

logger = logging.getLogger(__name__)

@dataclass
class StorageConfig:
    """Configuration for parquet storage operations"""
    user_id: str
    dataset_name: str
    bucket_name: Optional[str] = None  # Uses default if None
    base_path: Optional[str] = None    # Uses user_id/dataset_name if None
    compression: str = 'snappy'        # snappy, gzip, lz4, brotli
    partition_cols: Optional[List[str]] = None
    max_file_size_mb: int = 100        # Split large files
    include_metadata: bool = True      # Store metadata alongside parquet
    versioning: bool = True            # Version files with timestamp

@dataclass
class StorageResult:
    """Result from parquet storage operation"""
    success: bool
    storage_id: str                    # Unique identifier for this storage
    parquet_path: str                  # MinIO object path to parquet file
    metadata_path: Optional[str] = None # MinIO object path to metadata JSON
    presigned_urls: Dict[str, str] = field(default_factory=dict)
    file_size_bytes: int = 0
    row_count: int = 0
    column_count: int = 0
    compression_ratio: float = 0.0
    storage_duration_ms: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ParquetMinIOStorage:
    """
    Parquet MinIO Storage Processor
    
    Efficiently stores pandas DataFrames as Parquet files in MinIO object storage
    with metadata extraction and optional partitioning.
    
    Features:
    - Automatic compression (snappy by default)
    - Metadata extraction and storage
    - File versioning with timestamps
    - Large file partitioning
    - Presigned URL generation for access
    - Storage metrics and validation
    """
    
    def __init__(self):
        self.minio_client = get_minio_client()
        self.processor_name = "ParquetMinIOStorage"
        
    def store_dataframe(self, 
                       df: pd.DataFrame, 
                       config: StorageConfig) -> StorageResult:
        """
        Store DataFrame as Parquet in MinIO
        
        Args:
            df: Input DataFrame to store
            config: Storage configuration
            
        Returns:
            StorageResult with storage information and access details
        """
        start_time = datetime.now()
        storage_id = f"storage_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Starting parquet storage {storage_id} for dataset: {config.dataset_name}")
        logger.info(f"DataFrame shape: {df.shape}, User: {config.user_id}")
        
        try:
            # Validate inputs
            if df.empty:
                return StorageResult(
                    success=False,
                    storage_id=storage_id,
                    parquet_path="",
                    errors=["Cannot store empty DataFrame"]
                )
            
            # Generate storage paths
            paths = self._generate_storage_paths(config, storage_id)
            
            # Convert DataFrame to Parquet bytes
            parquet_bytes = self._dataframe_to_parquet_bytes(df, config)
            if not parquet_bytes:
                return StorageResult(
                    success=False,
                    storage_id=storage_id,
                    parquet_path="",
                    errors=["Failed to convert DataFrame to Parquet"]
                )
            
            # Upload parquet to MinIO
            parquet_uploaded = self.minio_client.upload_data(
                data=parquet_bytes,
                object_name=paths['parquet_path'],
                bucket_name=config.bucket_name,
                content_type='application/octet-stream'
            )
            
            if not parquet_uploaded:
                return StorageResult(
                    success=False,
                    storage_id=storage_id,
                    parquet_path=paths['parquet_path'],
                    errors=["Failed to upload parquet to MinIO"]
                )
            
            # Extract and store metadata
            metadata_path = None
            if config.include_metadata:
                metadata = self._extract_dataframe_metadata(df, config, storage_id)
                metadata_bytes = self._metadata_to_json_bytes(metadata)
                
                metadata_uploaded = self.minio_client.upload_data(
                    data=metadata_bytes,
                    object_name=paths['metadata_path'],
                    bucket_name=config.bucket_name,
                    content_type='application/json'
                )
                
                if metadata_uploaded:
                    metadata_path = paths['metadata_path']
                else:
                    logger.warning(f"Failed to upload metadata for {storage_id}")
            
            # Generate presigned URLs
            presigned_urls = self._generate_presigned_urls(paths, config)
            
            # Calculate metrics
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Create successful result
            result = StorageResult(
                success=True,
                storage_id=storage_id,
                parquet_path=paths['parquet_path'],
                metadata_path=metadata_path,
                presigned_urls=presigned_urls,
                file_size_bytes=len(parquet_bytes),
                row_count=len(df),
                column_count=len(df.columns),
                compression_ratio=self._calculate_compression_ratio(df, parquet_bytes),
                storage_duration_ms=duration_ms,
                metadata={
                    'bucket_name': config.bucket_name or self.minio_client._config['default_bucket'],
                    'compression': config.compression,
                    'original_shape': df.shape,
                    'column_types': df.dtypes.to_dict(),
                    'storage_timestamp': end_time.isoformat()
                }
            )
            
            logger.info(f" Successfully stored {storage_id}: {result.row_count} rows, {result.file_size_bytes} bytes")
            return result
            
        except Exception as e:
            logger.error(f"L Storage failed for {storage_id}: {e}")
            return StorageResult(
                success=False,
                storage_id=storage_id,
                parquet_path="",
                errors=[str(e)],
                storage_duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
    
    def _generate_storage_paths(self, config: StorageConfig, storage_id: str) -> Dict[str, str]:
        """Generate MinIO object paths for parquet and metadata files"""
        # Base path: user_id/dataset_name/YYYY/MM/DD/
        if config.base_path:
            base_path = config.base_path
        else:
            today = datetime.now()
            base_path = f"{config.user_id}/{config.dataset_name}/{today.year:04d}/{today.month:02d}/{today.day:02d}"
        
        # Add versioning if enabled
        if config.versioning:
            timestamp = datetime.now().strftime("%H%M%S")
            filename_base = f"{config.dataset_name}_{timestamp}_{storage_id}"
        else:
            filename_base = f"{config.dataset_name}_{storage_id}"
        
        return {
            'parquet_path': f"{base_path}/{filename_base}.parquet",
            'metadata_path': f"{base_path}/{filename_base}_metadata.json"
        }
    
    def _dataframe_to_parquet_bytes(self, df: pd.DataFrame, config: StorageConfig) -> Optional[bytes]:
        """Convert DataFrame to Parquet bytes with compression"""
        try:
            buffer = io.BytesIO()
            
            # Configure parquet options
            parquet_options = {
                'compression': config.compression,
                'index': False,  # Don't store DataFrame index
                'engine': 'pyarrow'  # Use pyarrow for better performance
            }
            
            # Write to buffer
            df.to_parquet(buffer, **parquet_options)
            parquet_bytes = buffer.getvalue()
            buffer.close()
            
            logger.debug(f"Converted DataFrame to Parquet: {len(parquet_bytes)} bytes with {config.compression} compression")
            return parquet_bytes
            
        except Exception as e:
            logger.error(f"Failed to convert DataFrame to Parquet: {e}")
            return None
    
    def _extract_dataframe_metadata(self, df: pd.DataFrame, config: StorageConfig, storage_id: str) -> Dict[str, Any]:
        """Extract comprehensive metadata from DataFrame"""
        metadata = {
            'storage_id': storage_id,
            'dataset_name': config.dataset_name,
            'user_id': config.user_id,
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
                'compression': config.compression,
                'versioning': config.versioning,
                'bucket_name': config.bucket_name or self.minio_client._config['default_bucket']
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
    
    def _generate_presigned_urls(self, paths: Dict[str, str], config: StorageConfig) -> Dict[str, str]:
        """Generate presigned URLs for accessing stored files"""
        urls = {}
        bucket_name = config.bucket_name or self.minio_client._config['default_bucket']
        
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
    
    def load_dataframe(self, parquet_path: str, bucket_name: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Load DataFrame from MinIO parquet file
        
        Args:
            parquet_path: MinIO object path to parquet file
            bucket_name: Bucket name (uses default if None)
            
        Returns:
            Loaded DataFrame or None if failed
        """
        try:
            parquet_bytes = self.minio_client.download_data(parquet_path, bucket_name)
            if not parquet_bytes:
                return None
            
            buffer = io.BytesIO(parquet_bytes)
            df = pd.read_parquet(buffer)
            buffer.close()
            
            logger.info(f" Loaded DataFrame from MinIO: {df.shape} from {parquet_path}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to load DataFrame from MinIO: {e}")
            return None
    
    def get_metadata(self, metadata_path: str, bucket_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load metadata from MinIO JSON file
        
        Args:
            metadata_path: MinIO object path to metadata JSON
            bucket_name: Bucket name (uses default if None)
            
        Returns:
            Metadata dict or None if failed
        """
        try:
            metadata_bytes = self.minio_client.download_data(metadata_path, bucket_name)
            if not metadata_bytes:
                return None
            
            import json
            metadata = json.loads(metadata_bytes.decode('utf-8'))
            
            logger.info(f" Loaded metadata from MinIO: {metadata_path}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to load metadata from MinIO: {e}")
            return None