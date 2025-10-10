#!/usr/bin/env python3
"""
MinIO Client for Object Storage
Centralized MinIO client configuration and connection management
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from minio import Minio
    from minio.error import S3Error
    import urllib3
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    Minio = None
    S3Error = Exception

logger = logging.getLogger(__name__)

class MinIOClient:
    """
    Centralized MinIO client for object storage operations
    
    Configuration via environment variables:
    - MINIO_ENDPOINT: MinIO server endpoint (default: localhost:9000)
    - MINIO_ACCESS_KEY: Access key (default: minioadmin)
    - MINIO_SECRET_KEY: Secret key (default: minioadmin)
    - MINIO_SECURE: Use HTTPS (default: False)
    - MINIO_DEFAULT_BUCKET: Default bucket name (default: analytics-data)
    """
    
    _instance: Optional['MinIOClient'] = None
    _client: Optional[Minio] = None
    
    def __new__(cls) -> 'MinIOClient':
        """Singleton pattern for MinIO client"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._client = None
            self._config = self._load_config()
            self._connection_verified = False
    
    def _load_config(self) -> Dict[str, Any]:
        """Load MinIO configuration from environment variables"""
        return {
            'endpoint': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
            'access_key': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            'secret_key': os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
            'secure': os.getenv('MINIO_SECURE', 'false').lower() == 'true',
            'default_bucket': os.getenv('MINIO_DEFAULT_BUCKET', 'analytics-data'),
            'region': os.getenv('MINIO_REGION', 'us-east-1')
        }
    
    def get_client(self) -> Optional[Minio]:
        """
        Get MinIO client instance with lazy initialization
        
        Returns:
            Minio client instance or None if unavailable
        """
        if not MINIO_AVAILABLE:
            logger.warning("MinIO not available - install with: pip install minio")
            return None
        
        if self._client is None:
            try:
                # Disable SSL warnings for local development
                if not self._config['secure']:
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                self._client = Minio(
                    endpoint=self._config['endpoint'],
                    access_key=self._config['access_key'],
                    secret_key=self._config['secret_key'],
                    secure=self._config['secure']
                )
                
                # Verify connection
                if self._verify_connection():
                    logger.info(f"✅ MinIO client connected to {self._config['endpoint']}")
                else:
                    logger.error("❌ MinIO connection verification failed")
                    self._client = None
                    
            except Exception as e:
                logger.error(f"Failed to create MinIO client: {e}")
                self._client = None
        
        return self._client
    
    def _verify_connection(self) -> bool:
        """Verify MinIO connection by listing buckets"""
        if not self._client:
            return False
        
        try:
            # Try to list buckets to verify connection
            list(self._client.list_buckets())
            self._connection_verified = True
            return True
        except Exception as e:
            logger.error(f"MinIO connection verification failed: {e}")
            return False
    
    def ensure_bucket_exists(self, bucket_name: Optional[str] = None) -> bool:
        """
        Ensure bucket exists, create if it doesn't
        
        Args:
            bucket_name: Bucket name (uses default if None)
            
        Returns:
            True if bucket exists/created, False otherwise
        """
        bucket_name = bucket_name or self._config['default_bucket']
        client = self.get_client()
        
        if not client:
            return False
        
        try:
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name, location=self._config['region'])
                logger.info(f"✅ Created MinIO bucket: {bucket_name}")
            else:
                logger.debug(f"MinIO bucket already exists: {bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"Failed to ensure bucket {bucket_name}: {e}")
            return False
    
    def upload_data(self, 
                   data: bytes, 
                   object_name: str, 
                   bucket_name: Optional[str] = None,
                   content_type: str = 'application/octet-stream') -> bool:
        """
        Upload data to MinIO
        
        Args:
            data: Data to upload as bytes
            object_name: Object name/path in bucket
            bucket_name: Bucket name (uses default if None)
            content_type: MIME content type
            
        Returns:
            True if upload successful, False otherwise
        """
        bucket_name = bucket_name or self._config['default_bucket']
        client = self.get_client()
        
        if not client:
            return False
        
        if not self.ensure_bucket_exists(bucket_name):
            return False
        
        try:
            from io import BytesIO
            
            client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=BytesIO(data),
                length=len(data),
                content_type=content_type
            )
            
            logger.info(f"✅ Uploaded to MinIO: {bucket_name}/{object_name}")
            return True
            
        except S3Error as e:
            logger.error(f"Failed to upload to MinIO: {e}")
            return False
    
    def upload_file(self, 
                   file_path: str, 
                   object_name: Optional[str] = None, 
                   bucket_name: Optional[str] = None) -> bool:
        """
        Upload file to MinIO
        
        Args:
            file_path: Local file path
            object_name: Object name in bucket (uses filename if None)
            bucket_name: Bucket name (uses default if None)
            
        Returns:
            True if upload successful, False otherwise
        """
        bucket_name = bucket_name or self._config['default_bucket']
        object_name = object_name or os.path.basename(file_path)
        client = self.get_client()
        
        if not client:
            return False
        
        if not self.ensure_bucket_exists(bucket_name):
            return False
        
        try:
            client.fput_object(bucket_name, object_name, file_path)
            logger.info(f"✅ Uploaded file to MinIO: {bucket_name}/{object_name}")
            return True
            
        except S3Error as e:
            logger.error(f"Failed to upload file to MinIO: {e}")
            return False
    
    def download_data(self, 
                     object_name: str, 
                     bucket_name: Optional[str] = None) -> Optional[bytes]:
        """
        Download data from MinIO
        
        Args:
            object_name: Object name/path in bucket
            bucket_name: Bucket name (uses default if None)
            
        Returns:
            Data as bytes or None if failed
        """
        bucket_name = bucket_name or self._config['default_bucket']
        client = self.get_client()
        
        if not client:
            return None
        
        try:
            response = client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"✅ Downloaded from MinIO: {bucket_name}/{object_name}")
            return data
            
        except S3Error as e:
            logger.error(f"Failed to download from MinIO: {e}")
            return None
    
    def get_presigned_url(self, 
                         object_name: str, 
                         bucket_name: Optional[str] = None,
                         expires_in_seconds: int = 3600) -> Optional[str]:
        """
        Get presigned URL for object
        
        Args:
            object_name: Object name/path in bucket
            bucket_name: Bucket name (uses default if None)
            expires_in_seconds: URL expiration time
            
        Returns:
            Presigned URL or None if failed
        """
        bucket_name = bucket_name or self._config['default_bucket']
        client = self.get_client()
        
        if not client:
            return None
        
        try:
            from datetime import timedelta
            
            url = client.presigned_get_object(
                bucket_name, 
                object_name, 
                expires=timedelta(seconds=expires_in_seconds)
            )
            
            logger.info(f"✅ Generated presigned URL for: {bucket_name}/{object_name}")
            return url
            
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
    
    def list_objects(self, 
                    bucket_name: Optional[str] = None, 
                    prefix: Optional[str] = None) -> list:
        """
        List objects in bucket
        
        Args:
            bucket_name: Bucket name (uses default if None)
            prefix: Object prefix filter
            
        Returns:
            List of object names
        """
        bucket_name = bucket_name or self._config['default_bucket']
        client = self.get_client()
        
        if not client:
            return []
        
        try:
            objects = client.list_objects(bucket_name, prefix=prefix)
            return [obj.object_name for obj in objects]
            
        except S3Error as e:
            logger.error(f"Failed to list objects: {e}")
            return []
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        config_safe = self._config.copy()
        # Remove sensitive information
        config_safe['secret_key'] = '***masked***'
        return config_safe
    
    def is_available(self) -> bool:
        """Check if MinIO client is available and connected"""
        return MINIO_AVAILABLE and self._connection_verified


# Global instance
_minio_client = None

def get_minio_client() -> MinIOClient:
    """Get global MinIO client instance"""
    global _minio_client
    if _minio_client is None:
        _minio_client = MinIOClient()
    return _minio_client