#!/usr/bin/env python3
"""
Professional Storage Service Client
Enterprise-grade client for user storage service with proper service discovery
"""

import os
import aiohttp
import logging
import consul
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class StorageConfig:
    """Storage service configuration"""
    service_name: str = "storage_service"
    consul_host: str = "localhost"
    consul_port: int = 8500
    api_timeout: int = 30
    max_retries: int = 3
    fallback_host: str = "localhost"
    fallback_port: int = 8208
    
    @classmethod
    def from_settings(cls) -> 'StorageConfig':
        """Create config from global settings"""
        from core.config import get_settings
        settings = get_settings()
        return cls(
            consul_host=settings.storage_consul_host or "localhost",
            consul_port=settings.storage_consul_port,
            fallback_host=settings.storage_fallback_host or "localhost", 
            fallback_port=settings.storage_fallback_port
        )


class StorageServiceClient:
    """
    Professional storage service client with:
    - Consul service discovery
    - Environment configuration
    - Retry logic
    - Proper error handling
    """
    
    def __init__(self, config: Optional[StorageConfig] = None):
        self.config = config or StorageConfig.from_settings()
        self.consul_client = None
        self.service_url = None
        self._session = None
        
    def _load_config(self) -> StorageConfig:
        """Load configuration from environment variables"""
        return StorageConfig(
            service_name=os.getenv('STORAGE_SERVICE_NAME', 'storage_service'),
            consul_host=os.getenv('CONSUL_HOST', 'localhost'),
            consul_port=int(os.getenv('CONSUL_PORT', '8500')),
            api_timeout=int(os.getenv('STORAGE_API_TIMEOUT', '30')),
            max_retries=int(os.getenv('STORAGE_MAX_RETRIES', '3')),
            fallback_host=os.getenv('STORAGE_FALLBACK_HOST', 'localhost'),
            fallback_port=int(os.getenv('STORAGE_FALLBACK_PORT', '8208'))
        )
    
    async def _discover_service(self) -> Optional[str]:
        """Discover storage service URL via Consul"""
        try:
            if not self.consul_client:
                self.consul_client = consul.Consul(
                    host=self.config.consul_host,
                    port=self.config.consul_port
                )
            
            # Get healthy service instances
            services = self.consul_client.health.service(
                self.config.service_name,
                passing=True
            )[1]
            
            if services:
                service = services[0]['Service']
                service_url = f"http://{service['Address']}:{service['Port']}"
                logger.info(f"Discovered storage service at: {service_url}")
                return service_url
            else:
                logger.warning(f"No healthy {self.config.service_name} instances found in Consul")
                return None
                
        except Exception as e:
            logger.warning(f"Service discovery failed: {str(e)}")
            return None
    
    async def _get_service_url(self) -> str:
        """Get service URL with fallback"""
        if not self.service_url:
            # Try service discovery first
            discovered_url = await self._discover_service()
            if discovered_url:
                self.service_url = discovered_url
            else:
                # Fallback to configured host/port
                self.service_url = f"http://{self.config.fallback_host}:{self.config.fallback_port}"
                logger.info(f"Using fallback storage service URL: {self.service_url}")
        
        return self.service_url
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if not self._session or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.api_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        base_url = await self._get_service_url()
        url = f"{base_url}{endpoint}"
        session = await self._get_session()
        
        for attempt in range(self.config.max_retries):
            try:
                async with session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"Storage API error {response.status}: {error_text}")
                        
                        if response.status >= 500 and attempt < self.config.max_retries - 1:
                            # Retry on server errors
                            await asyncio.sleep(2 ** attempt)
                            continue
                        
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=error_text
                        )
                        
            except aiohttp.ClientError as e:
                logger.warning(f"Storage API request failed (attempt {attempt + 1}): {str(e)}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        
        raise Exception(f"Failed to complete request after {self.config.max_retries} attempts")
    
    async def upload_parquet_data(self, user_id: str, dataset_name: str, parquet_data: bytes) -> Dict[str, Any]:
        """
        Upload parquet data to user storage service
        
        Args:
            user_id: User identifier
            dataset_name: Dataset name
            parquet_data: Parquet file bytes
            
        Returns:
            Upload response with file information
        """
        try:
            # Prepare multipart form data
            form_data = aiohttp.FormData()
            form_data.add_field('user_id', user_id)
            form_data.add_field('description', f'Analytics dataset: {dataset_name}')
            form_data.add_field('access_level', 'private')
            form_data.add_field('metadata', '{"type": "analytics_parquet", "source": "mcp_data_tools"}')
            
            # Add file
            form_data.add_field(
                'file',
                parquet_data,
                filename=f"{dataset_name}.parquet",
                content_type='application/octet-stream'
            )
            
            # Make upload request
            response = await self._make_request(
                'POST',
                '/api/v1/files/upload',
                data=form_data
            )
            
            logger.info(f"Successfully uploaded {dataset_name} for user {user_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to upload parquet data: {str(e)}")
            raise
    
    async def get_user_files(self, user_id: str, file_type: str = "analytics_parquet") -> List[Dict[str, Any]]:
        """
        Get user's stored files filtered by type
        
        Args:
            user_id: User identifier
            file_type: File type filter
            
        Returns:
            List of user files
        """
        try:
            params = {
                'user_id': user_id,
                'page': 1,
                'limit': 100
            }
            
            response = await self._make_request(
                'GET',
                '/api/v1/files',
                params=params
            )
            
            # Response is directly a list of files
            files = response if isinstance(response, list) else response.get('files', [])
            
            # Filter by type if specified  
            if file_type:
                files = [f for f in files if f.get('metadata', {}).get('type') == file_type]
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to get user files: {str(e)}")
            return []
    
    async def get_file_download_url(self, file_id: str, user_id: str) -> Optional[str]:
        """
        Get download URL for a file
        
        Args:
            file_id: File identifier
            user_id: User identifier
            
        Returns:
            Download URL if successful
        """
        try:
            response = await self._make_request(
                'GET',
                f'/api/v1/files/{file_id}/download',
                params={'user_id': user_id}
            )
            
            return response.get('download_url')
            
        except Exception as e:
            logger.error(f"Failed to get download URL: {str(e)}")
            return None
    
    async def close(self):
        """Clean up resources"""
        if self._session and not self._session.closed:
            await self._session.close()


# Global client instance
_storage_client: Optional[StorageServiceClient] = None


async def get_storage_client() -> StorageServiceClient:
    """Get global storage service client instance"""
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageServiceClient()
    return _storage_client


async def cleanup_storage_client():
    """Cleanup global storage client"""
    global _storage_client
    if _storage_client:
        await _storage_client.close()
        _storage_client = None