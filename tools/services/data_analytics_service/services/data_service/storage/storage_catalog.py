"""
Storage Catalog Service - Step 3 of Storage Pipeline
Updates metadata store and creates storage catalogs/indexes
"""

import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

from ..management.metadata.metadata_store_service import MetadataStoreService

logger = logging.getLogger(__name__)

@dataclass
class CatalogResult:
    """Result of storage cataloging step"""
    success: bool
    catalog_entries: List[Dict[str, Any]] = field(default_factory=list)
    metadata_updates: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

class StorageCatalogService:
    """
    Storage Catalog Service - Step 3 of Storage Pipeline
    
    Handles:
    - Storage metadata cataloging
    - Integration with existing metadata store service
    - Storage index creation and maintenance
    - Storage lineage tracking
    """
    
    def __init__(self):
        self.execution_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'catalog_entries_created': 0,
            'average_duration': 0.0
        }
        
        # Initialize metadata store service
        self.metadata_service = MetadataStoreService()
        
        logger.info("Storage Catalog Service initialized")
    
    def catalog_storage(self, 
                       storage_details: Dict[str, Any],
                       catalog_config: Dict[str, Any]) -> CatalogResult:
        """
        Create catalog entries for stored data
        
        Args:
            storage_details: Details from persistence step
            catalog_config: Configuration for cataloging
            
        Returns:
            CatalogResult with catalog information
        """
        start_time = datetime.now()
        
        try:
            # Extract storage information
            storage_type = storage_details.get('storage_type')
            destination = storage_details.get('destination')
            table_name = storage_details.get('table_name')
            
            if not all([storage_type, destination, table_name]):
                return CatalogResult(
                    success=False,
                    errors=["Storage details missing required fields: storage_type, destination, table_name"]
                )
            
            # Create catalog entry
            catalog_entry = self._create_catalog_entry(storage_details, catalog_config)
            
            # Update metadata store
            metadata_updates = self._update_metadata_store(catalog_entry, catalog_config)
            
            # Create storage index if requested
            index_results = {}
            if catalog_config.get('create_index', True):
                index_results = self._create_storage_index(catalog_entry, catalog_config)
            
            # Track storage lineage
            lineage_results = {}
            if catalog_config.get('track_lineage', True):
                lineage_results = self._track_storage_lineage(catalog_entry, catalog_config)
            
            # Calculate performance metrics
            duration = (datetime.now() - start_time).total_seconds()
            performance_metrics = {
                'duration_seconds': duration,
                'catalog_entries_processed': 1,
                'metadata_updates_made': len(metadata_updates),
                'indexes_created': len(index_results)
            }
            
            # Update execution stats
            self._update_stats(True, duration, 1)
            
            return CatalogResult(
                success=True,
                catalog_entries=[catalog_entry],
                metadata_updates={
                    'metadata_store': metadata_updates,
                    'indexes': index_results,
                    'lineage': lineage_results
                },
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(False, duration, 0)
            
            logger.error(f"Storage cataloging failed: {e}")
            return CatalogResult(
                success=False,
                errors=[f"Cataloging error: {str(e)}"],
                performance_metrics={'duration_seconds': duration}
            )
    
    def _create_catalog_entry(self, storage_details: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a comprehensive catalog entry for the stored data"""
        try:
            storage_result = storage_details.get('storage_result', {})
            verification = storage_details.get('verification', {})
            
            catalog_entry = {
                'catalog_id': self._generate_catalog_id(storage_details),
                'created_at': datetime.now().isoformat(),
                'storage_info': {
                    'storage_type': storage_details.get('storage_type'),
                    'destination': storage_details.get('destination'),
                    'table_name': storage_details.get('table_name'),
                    'full_path': self._get_full_storage_path(storage_details)
                },
                'data_info': {
                    'rows_stored': storage_result.get('rows_stored', 0),
                    'columns_stored': storage_result.get('columns_stored', 0),
                    'storage_size_bytes': storage_result.get('file_size_bytes', 0),
                    'storage_size_mb': storage_result.get('file_size_mb', 0),
                    'compression': storage_details.get('storage_options', {}).get('compression'),
                    'format_version': self._get_format_version(storage_details.get('storage_type'))
                },
                'quality_info': {
                    'verification_passed': verification.get('verified', False),
                    'row_count_verified': verification.get('row_count_match', False),
                    'column_count_verified': verification.get('column_count_match', False),
                    'storage_integrity': 'verified' if verification.get('verified') else 'unverified'
                },
                'access_info': {
                    'read_permissions': config.get('read_permissions', 'default'),
                    'write_permissions': config.get('write_permissions', 'restricted'),
                    'access_pattern': config.get('expected_access_pattern', 'unknown'),
                    'retention_policy': config.get('retention_policy')
                },
                'technical_metadata': {
                    'adapter_used': storage_details.get('adapter_info', {}).get('adapter_class'),
                    'storage_options': storage_details.get('storage_options', {}),
                    'performance_metrics': storage_details.get('performance_metrics', {}),
                    'creation_source': config.get('source_system', 'data_analytics_service')
                },
                'tags': config.get('tags', []),
                'description': config.get('description', ''),
                'owner': config.get('owner', 'system')
            }
            
            return catalog_entry
            
        except Exception as e:
            logger.error(f"Failed to create catalog entry: {e}")
            return {}
    
    def _generate_catalog_id(self, storage_details: Dict[str, Any]) -> str:
        """Generate unique catalog ID for storage entry"""
        storage_type = storage_details.get('storage_type', 'unknown')
        destination = storage_details.get('destination', 'unknown')
        table_name = storage_details.get('table_name', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return f"{storage_type}_{table_name}_{timestamp}"
    
    def _get_full_storage_path(self, storage_details: Dict[str, Any]) -> str:
        """Get full path to stored data"""
        storage_type = storage_details.get('storage_type')
        destination = storage_details.get('destination')
        table_name = storage_details.get('table_name')
        
        if storage_type == 'duckdb':
            return f"{destination}::{table_name}"
        elif storage_type == 'parquet':
            return str(Path(destination) / f"{table_name}.parquet")
        elif storage_type == 'csv':
            return str(Path(destination) / f"{table_name}.csv")
        else:
            return f"{destination}/{table_name}"
    
    def _get_format_version(self, storage_type: str) -> str:
        """Get format version information"""
        versions = {
            'duckdb': '0.9.x',
            'parquet': '1.0',
            'csv': 'RFC4180'
        }
        return versions.get(storage_type, 'unknown')
    
    def _update_metadata_store(self, catalog_entry: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Update the metadata store with storage information"""
        try:
            # Prepare metadata for the metadata store service
            metadata_entry = {
                'dataset_id': catalog_entry['catalog_id'],
                'dataset_name': catalog_entry['storage_info']['table_name'],
                'storage_location': catalog_entry['storage_info']['full_path'],
                'storage_type': catalog_entry['storage_info']['storage_type'],
                'row_count': catalog_entry['data_info']['rows_stored'],
                'column_count': catalog_entry['data_info']['columns_stored'],
                'size_bytes': catalog_entry['data_info']['storage_size_bytes'],
                'created_at': catalog_entry['created_at'],
                'tags': catalog_entry.get('tags', []),
                'owner': catalog_entry.get('owner', 'system'),
                'description': catalog_entry.get('description', ''),
                'quality_score': 1.0 if catalog_entry['quality_info']['verification_passed'] else 0.7,
                'metadata': {
                    'storage_catalog_entry': catalog_entry,
                    'format_version': catalog_entry['data_info']['format_version'],
                    'compression': catalog_entry['data_info']['compression']
                }
            }
            
            # Store in metadata service
            store_result = self.metadata_service.store_metadata(
                metadata=metadata_entry,
                source_type="storage_catalog",
                confidence_score=0.95
            )
            
            return {
                'metadata_store_result': store_result,
                'metadata_entry_id': metadata_entry['dataset_id'],
                'stored_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update metadata store: {e}")
            return {'error': str(e)}
    
    def _create_storage_index(self, catalog_entry: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Create storage indexes for faster lookup"""
        try:
            storage_type = catalog_entry['storage_info']['storage_type']
            indexes_created = []
            
            # Create type-based index
            type_index = {
                'index_type': 'storage_type',
                'index_key': storage_type,
                'catalog_id': catalog_entry['catalog_id'],
                'created_at': datetime.now().isoformat()
            }
            indexes_created.append(type_index)
            
            # Create size-based index
            size_category = self._categorize_by_size(catalog_entry['data_info']['storage_size_mb'])
            size_index = {
                'index_type': 'size_category',
                'index_key': size_category,
                'catalog_id': catalog_entry['catalog_id'],
                'created_at': datetime.now().isoformat()
            }
            indexes_created.append(size_index)
            
            # Create tag-based indexes
            for tag in catalog_entry.get('tags', []):
                tag_index = {
                    'index_type': 'tag',
                    'index_key': tag,
                    'catalog_id': catalog_entry['catalog_id'],
                    'created_at': datetime.now().isoformat()
                }
                indexes_created.append(tag_index)
            
            return {
                'indexes_created': indexes_created,
                'index_count': len(indexes_created)
            }
            
        except Exception as e:
            logger.error(f"Failed to create storage index: {e}")
            return {'error': str(e)}
    
    def _categorize_by_size(self, size_mb: float) -> str:
        """Categorize storage by size"""
        if size_mb < 1:
            return 'small'
        elif size_mb < 100:
            return 'medium'
        elif size_mb < 1000:
            return 'large'
        else:
            return 'very_large'
    
    def _track_storage_lineage(self, catalog_entry: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Track storage lineage and relationships"""
        try:
            lineage_entry = {
                'catalog_id': catalog_entry['catalog_id'],
                'lineage_type': 'storage_creation',
                'source_data': config.get('source_data_info', {}),
                'transformations_applied': config.get('transformations_applied', []),
                'processing_pipeline': config.get('processing_pipeline', []),
                'created_at': datetime.now().isoformat(),
                'lineage_metadata': {
                    'storage_service_version': '1.0',
                    'processing_timestamp': catalog_entry['created_at'],
                    'data_quality_score': catalog_entry['quality_info'].get('storage_integrity', 'unknown')
                }
            }
            
            return {
                'lineage_entry': lineage_entry,
                'lineage_tracked': True
            }
            
        except Exception as e:
            logger.error(f"Failed to track storage lineage: {e}")
            return {'error': str(e)}
    
    def search_catalog(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search storage catalog using metadata store"""
        try:
            # Convert search criteria to metadata store format
            search_params = {
                'source_type': 'storage_catalog'
            }
            
            if 'storage_type' in search_criteria:
                search_params['metadata.storage_type'] = search_criteria['storage_type']
            
            if 'tags' in search_criteria:
                search_params['tags'] = search_criteria['tags']
            
            if 'owner' in search_criteria:
                search_params['owner'] = search_criteria['owner']
            
            if 'size_range' in search_criteria:
                size_range = search_criteria['size_range']
                if 'min_mb' in size_range:
                    search_params['size_bytes_min'] = size_range['min_mb'] * 1024 * 1024
                if 'max_mb' in size_range:
                    search_params['size_bytes_max'] = size_range['max_mb'] * 1024 * 1024
            
            # Execute search through metadata service
            search_result = self.metadata_service.search_metadata(search_params)
            
            # Extract catalog entries from metadata
            catalog_entries = []
            if search_result.get('success'):
                for metadata_entry in search_result.get('results', []):
                    catalog_entry = metadata_entry.get('metadata', {}).get('storage_catalog_entry')
                    if catalog_entry:
                        catalog_entries.append(catalog_entry)
            
            return catalog_entries
            
        except Exception as e:
            logger.error(f"Catalog search failed: {e}")
            return []
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get statistics about cataloged storage"""
        try:
            # Get all storage catalog entries
            all_entries = self.search_catalog({})
            
            if not all_entries:
                return {
                    'total_entries': 0,
                    'storage_types': {},
                    'total_size_mb': 0,
                    'size_distribution': {},
                    'quality_summary': {}
                }
            
            # Calculate statistics
            storage_types = {}
            total_size_mb = 0
            size_categories = {'small': 0, 'medium': 0, 'large': 0, 'very_large': 0}
            verified_count = 0
            
            for entry in all_entries:
                # Storage type distribution
                storage_type = entry['storage_info']['storage_type']
                storage_types[storage_type] = storage_types.get(storage_type, 0) + 1
                
                # Size statistics
                size_mb = entry['data_info']['storage_size_mb']
                total_size_mb += size_mb
                
                # Size distribution
                size_category = self._categorize_by_size(size_mb)
                size_categories[size_category] += 1
                
                # Quality statistics
                if entry['quality_info']['verification_passed']:
                    verified_count += 1
            
            return {
                'total_entries': len(all_entries),
                'storage_types': storage_types,
                'total_size_mb': round(total_size_mb, 2),
                'average_size_mb': round(total_size_mb / len(all_entries), 2),
                'size_distribution': size_categories,
                'quality_summary': {
                    'verified_entries': verified_count,
                    'verification_rate': round((verified_count / len(all_entries)) * 100, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")
            return {'error': str(e)}
    
    def _update_stats(self, success: bool, duration: float, entries_created: int):
        """Update execution statistics"""
        self.execution_stats['total_operations'] += 1
        
        if success:
            self.execution_stats['successful_operations'] += 1
            self.execution_stats['catalog_entries_created'] += entries_created
        else:
            self.execution_stats['failed_operations'] += 1
        
        # Update average duration
        total = self.execution_stats['total_operations']
        old_avg = self.execution_stats['average_duration']
        self.execution_stats['average_duration'] = (old_avg * (total - 1) + duration) / total
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_operations'] / 
                max(1, self.execution_stats['total_operations'])
            )
        }