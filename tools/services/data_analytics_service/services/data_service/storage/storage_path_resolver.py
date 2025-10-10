#!/usr/bin/env python3
"""
Storage Path Resolver Service
Resolves storage paths using metadata service dataset mappings and professional storage client
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..management.metadata.metadata_store_service import get_metadata_store_service
from core.storage_client import get_storage_client

logger = logging.getLogger(__name__)

@dataclass
class PathResolutionResult:
    """Result of storage path resolution"""
    success: bool
    resolved_path: Optional[str] = None
    dataset_name: Optional[str] = None
    storage_type: Optional[str] = None
    user_id: Optional[str] = None
    resolution_method: Optional[str] = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

class StoragePathResolver:
    """
    Storage Path Resolver Service
    
    Provides generic, robust storage path resolution using:
    1. Metadata service dataset mappings
    2. Professional storage client integration  
    3. Multiple fallback strategies
    4. User-specific storage isolation
    """
    
    def __init__(self, database_name: str = "default_db"):
        self.database_name = database_name
        self.metadata_service = get_metadata_store_service(database_name)
        self.service_name = "StoragePathResolver"
        
        logger.info(f"Storage Path Resolver initialized for database: {database_name}")
    
    async def resolve_storage_path(self, 
                                 table_name: str, 
                                 user_id: str = "default_user",
                                 preferred_format: str = "parquet") -> PathResolutionResult:
        """
        Resolve storage path for a table name using metadata service
        
        Args:
            table_name: Table name to resolve
            user_id: User identifier for storage isolation
            preferred_format: Preferred file format (parquet, csv, etc.)
            
        Returns:
            PathResolutionResult with resolved path and metadata
        """
        try:
            logger.info(f"Resolving storage path for table '{table_name}', user '{user_id}'")
            
            # Method 1: Direct dataset mapping lookup
            mapping_result = await self._resolve_via_dataset_mapping(table_name, user_id)
            if mapping_result.success:
                return mapping_result
            
            # Method 2: Search semantic metadata for storage paths
            semantic_result = await self._resolve_via_semantic_search(table_name, user_id)
            if semantic_result.success:
                return semantic_result
            
            # Method 3: Professional storage service lookup
            storage_result = await self._resolve_via_storage_service(table_name, user_id, preferred_format)
            if storage_result.success:
                return storage_result
            
            # Method 4: Fallback to conventional path
            fallback_result = self._resolve_via_fallback(table_name, user_id, preferred_format)
            return fallback_result
            
        except Exception as e:
            logger.error(f"Storage path resolution failed for '{table_name}': {e}")
            return PathResolutionResult(
                success=False,
                error=f"Resolution error: {str(e)}",
                resolution_method="error"
            )
    
    async def _resolve_via_dataset_mapping(self, table_name: str, user_id: str) -> PathResolutionResult:
        """Resolve using direct dataset mapping from metadata service"""
        try:
            mapping = await self.metadata_service.get_dataset_mapping(table_name, user_id)
            
            if mapping and mapping.get('found'):
                dataset_name = mapping.get('dataset_name')
                storage_path = mapping.get('storage_path')
                
                logger.info(f"Found dataset mapping: {table_name} → {dataset_name} at {storage_path}")
                
                return PathResolutionResult(
                    success=True,
                    resolved_path=storage_path,
                    dataset_name=dataset_name,
                    storage_type=self._detect_storage_type(storage_path),
                    user_id=user_id,
                    resolution_method="dataset_mapping",
                    metadata=mapping
                )
            
            return PathResolutionResult(success=False, resolution_method="dataset_mapping_not_found")
            
        except Exception as e:
            logger.warning(f"Dataset mapping resolution failed: {e}")
            return PathResolutionResult(success=False, error=str(e), resolution_method="dataset_mapping_error")
    
    async def _resolve_via_semantic_search(self, table_name: str, user_id: str) -> PathResolutionResult:
        """Resolve using semantic search through metadata"""
        try:
            # Search for storage path information in semantic metadata
            query = f"storage path table {table_name} user {user_id}"
            results = await self.metadata_service.search_metadata(query, limit=10)
            
            for result in results:
                metadata = result.get('metadata', {})
                content = result.get('content', '')
                
                # Look for storage path in metadata
                if 'storage_path' in metadata:
                    storage_path = metadata['storage_path']
                    dataset_name = metadata.get('dataset_name', table_name)
                    
                    logger.info(f"Found via semantic search: {table_name} → {dataset_name} at {storage_path}")
                    
                    return PathResolutionResult(
                        success=True,
                        resolved_path=storage_path,
                        dataset_name=dataset_name,
                        storage_type=self._detect_storage_type(storage_path),
                        user_id=user_id,
                        resolution_method="semantic_search",
                        metadata=metadata
                    )
            
            return PathResolutionResult(success=False, resolution_method="semantic_search_not_found")
            
        except Exception as e:
            logger.warning(f"Semantic search resolution failed: {e}")
            return PathResolutionResult(success=False, error=str(e), resolution_method="semantic_search_error")
    
    async def _resolve_via_storage_service(self, table_name: str, user_id: str, preferred_format: str) -> PathResolutionResult:
        """Resolve using professional storage service"""
        try:
            storage_client = await get_storage_client()
            
            # Get user files of analytics type
            files = await storage_client.get_user_files(user_id, file_type="analytics_parquet")
            
            for file_info in files:
                filename = file_info.get('filename', '')
                file_id = file_info.get('file_id')
                
                # Check if filename matches table name pattern
                if table_name.lower() in filename.lower() or filename.lower().startswith(table_name.lower()):
                    # Get download URL
                    download_url = await storage_client.get_file_download_url(file_id, user_id)
                    
                    if download_url:
                        dataset_name = filename.replace('.parquet', '').replace('.csv', '')
                        
                        logger.info(f"Found via storage service: {table_name} → {dataset_name} at {download_url}")
                        
                        return PathResolutionResult(
                            success=True,
                            resolved_path=download_url,
                            dataset_name=dataset_name,
                            storage_type="storage_service",
                            user_id=user_id,
                            resolution_method="storage_service",
                            metadata=file_info
                        )
            
            return PathResolutionResult(success=False, resolution_method="storage_service_not_found")
            
        except Exception as e:
            logger.warning(f"Storage service resolution failed: {e}")
            return PathResolutionResult(success=False, error=str(e), resolution_method="storage_service_error")
    
    def _resolve_via_fallback(self, table_name: str, user_id: str, preferred_format: str) -> PathResolutionResult:
        """Fallback to conventional storage path"""
        try:
            # Construct conventional path based on patterns
            dataset_name = table_name
            
            # Try multiple conventional patterns
            conventional_paths = [
                f"analytics-data/{user_id}/{dataset_name}.{preferred_format}",
                f"analytics-data/{user_id}/{table_name}.{preferred_format}",
                f"{user_id}/{dataset_name}.{preferred_format}",
                f"{user_id}/{table_name}.{preferred_format}"
            ]
            
            # Return the first conventional pattern
            fallback_path = conventional_paths[0]
            
            logger.info(f"Using fallback path: {table_name} → {fallback_path}")
            
            return PathResolutionResult(
                success=True,
                resolved_path=fallback_path,
                dataset_name=dataset_name,
                storage_type=preferred_format,
                user_id=user_id,
                resolution_method="fallback_conventional",
                metadata={'conventional_patterns': conventional_paths}
            )
            
        except Exception as e:
            logger.error(f"Fallback resolution failed: {e}")
            return PathResolutionResult(
                success=False,
                error=f"Fallback error: {str(e)}",
                resolution_method="fallback_error"
            )
    
    def _detect_storage_type(self, storage_path: str) -> str:
        """Detect storage type from path"""
        if not storage_path:
            return "unknown"
        
        path_lower = storage_path.lower()
        if '.parquet' in path_lower:
            return "parquet"
        elif '.csv' in path_lower:
            return "csv"
        elif '.json' in path_lower:
            return "json"
        elif 'duckdb' in path_lower or '.db' in path_lower:
            return "duckdb"
        elif 'http' in path_lower:
            return "url"
        else:
            return "file"
    
    async def list_available_datasets(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        """
        List all available datasets for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of available dataset information
        """
        try:
            datasets = []
            
            # Get from dataset mappings
            query = f"Dataset mapping user '{user_id}'"
            results = await self.metadata_service.search_metadata(query, limit=50)
            
            for result in results:
                metadata = result.get('metadata', {})
                if metadata.get('mapping_type') == 'dataset_storage' and metadata.get('user_id') == user_id:
                    datasets.append({
                        'table_name': metadata.get('table_name'),
                        'dataset_name': metadata.get('dataset_name'),
                        'storage_path': metadata.get('storage_path'),
                        'source': 'dataset_mapping'
                    })
            
            # Get from storage service
            try:
                storage_client = await get_storage_client()
                files = await storage_client.get_user_files(user_id, file_type="analytics_parquet")
                
                for file_info in files:
                    filename = file_info.get('filename', '')
                    dataset_name = filename.replace('.parquet', '').replace('.csv', '')
                    
                    # Avoid duplicates
                    existing = any(d['dataset_name'] == dataset_name for d in datasets)
                    if not existing:
                        datasets.append({
                            'table_name': dataset_name,
                            'dataset_name': dataset_name,
                            'storage_path': f"storage_service://{file_info.get('file_id')}",
                            'source': 'storage_service',
                            'file_info': file_info
                        })
            except Exception as e:
                logger.warning(f"Could not list storage service files: {e}")
            
            logger.info(f"Found {len(datasets)} available datasets for user '{user_id}'")
            return datasets
            
        except Exception as e:
            logger.error(f"Failed to list available datasets: {e}")
            return []

# Global service instances
_path_resolvers = {}

def get_storage_path_resolver(database_name: str = "default_db") -> StoragePathResolver:
    """Get storage path resolver instance for a specific database"""
    global _path_resolvers
    
    if database_name not in _path_resolvers:
        _path_resolvers[database_name] = StoragePathResolver(database_name)
    
    return _path_resolvers[database_name]

# Convenience functions
async def resolve_storage_path(table_name: str, user_id: str = "default_user", 
                             database_name: str = "default_db") -> PathResolutionResult:
    """Convenience function to resolve storage path"""
    resolver = get_storage_path_resolver(database_name)
    return await resolver.resolve_storage_path(table_name, user_id)

async def list_user_datasets(user_id: str = "default_user", 
                           database_name: str = "default_db") -> List[Dict[str, Any]]:
    """Convenience function to list user datasets"""
    resolver = get_storage_path_resolver(database_name)
    return await resolver.list_available_datasets(user_id)