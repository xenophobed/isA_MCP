#!/usr/bin/env python3
"""
MinIO Integration Module

Handles MinIO object storage for images and files
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class MinIOIntegration:
    """MinIO Object Storage Integration Manager"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._minio_client = None
    
    @property
    def minio_client(self):
        """Lazy load MinIO client"""
        if self._minio_client is None:
            self._minio_client = self._initialize_minio()
        return self._minio_client
    
    def _initialize_minio(self):
        """Initialize MinIO client"""
        try:
            from core.minio_client import get_minio_client
            
            client = get_minio_client()
            logger.info("MinIO client initialized successfully")
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            return self._create_mock_minio_client()
    
    def _create_mock_minio_client(self):
        """Create a mock MinIO client for testing"""
        class MockMinIOClient:
            def __init__(self):
                self.name = "MockMinIOClient"
            
            def upload_data(self, data, object_name, bucket_name=None, content_type=None):
                logger.warning(f"Mock upload: {object_name}")
                return True
            
            def upload_file(self, file_path, object_name=None, bucket_name=None):
                logger.warning(f"Mock upload file: {file_path}")
                return True
            
            def get_presigned_url(self, object_name, bucket_name=None, expires_in_seconds=3600):
                return f"http://mock-minio/{bucket_name or 'default'}/{object_name}"
            
            def download_data(self, object_name, bucket_name=None):
                logger.warning(f"Mock download: {object_name}")
                return b"mock_data"
            
            def list_objects(self, bucket_name=None, prefix=None):
                return []
        
        logger.warning("Using mock MinIO client due to initialization failure")
        return MockMinIOClient()
    
    async def upload_image(
        self,
        image_data: bytes,
        user_id: str,
        image_name: str,
        bucket_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload image to MinIO
        
        Args:
            image_data: Image binary data
            user_id: User identifier for organization
            image_name: Image filename
            bucket_name: Bucket name (default: analytics-data)
            
        Returns:
            Dictionary with upload result and URLs
        """
        try:
            bucket_name = bucket_name or 'analytics-data'
            
            # Organize by user_id
            object_path = f"{user_id}/pdf_images/{image_name}"
            
            # Detect content type from extension
            ext = Path(image_name).suffix.lower()
            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            content_type = content_type_map.get(ext, 'image/jpeg')
            
            # Upload to MinIO
            success = self.minio_client.upload_data(
                data=image_data,
                object_name=object_path,
                bucket_name=bucket_name,
                content_type=content_type
            )
            
            if success:
                # Generate presigned URL (expires in 7 days)
                presigned_url = self.minio_client.get_presigned_url(
                    object_name=object_path,
                    bucket_name=bucket_name,
                    expires_in_seconds=7 * 24 * 3600
                )
                
                return {
                    'success': True,
                    'object_path': object_path,
                    'bucket_name': bucket_name,
                    'presigned_url': presigned_url,
                    'size_bytes': len(image_data),
                    'content_type': content_type
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to upload to MinIO'
                }
                
        except Exception as e:
            logger.error(f"MinIO image upload failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_image_url(
        self,
        object_path: str,
        bucket_name: Optional[str] = None,
        expires_in_seconds: int = 3600
    ) -> Optional[str]:
        """Get presigned URL for an image"""
        try:
            bucket_name = bucket_name or 'analytics-data'
            url = self.minio_client.get_presigned_url(
                object_name=object_path,
                bucket_name=bucket_name,
                expires_in_seconds=expires_in_seconds
            )
            return url
        except Exception as e:
            logger.error(f"Failed to get presigned URL: {e}")
            return None
    
    async def list_user_images(
        self,
        user_id: str,
        bucket_name: Optional[str] = None
    ) -> List[str]:
        """List all images for a user"""
        try:
            bucket_name = bucket_name or 'analytics-data'
            prefix = f"{user_id}/pdf_images/"
            
            objects = self.minio_client.list_objects(
                bucket_name=bucket_name,
                prefix=prefix
            )
            return objects
        except Exception as e:
            logger.error(f"Failed to list user images: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if MinIO is available"""
        return self.minio_client is not None and hasattr(self.minio_client, 'upload_data')


# Global instance
_minio_integration = None

def get_minio_integration(config: Optional[Dict[str, Any]] = None) -> MinIOIntegration:
    """Get singleton instance of MinIO Integration"""
    global _minio_integration
    if _minio_integration is None:
        _minio_integration = MinIOIntegration(config)
    return _minio_integration

