"""
Data Storage Service Suite
Main orchestrator for data storage operations following 3-step pipeline pattern
"""

import polars as pl
from typing import Dict, List, Any, Optional, Union
import logging
from dataclasses import dataclass, field
from datetime import datetime

from .storage_target_selection import StorageTargetSelectionService
from .data_persistence import DataPersistenceService
from .storage_catalog import StorageCatalogService

logger = logging.getLogger(__name__)

@dataclass
class StorageConfig:
    """Configuration for storage operations"""
    target_selection_enabled: bool = True
    persistence_enabled: bool = True
    cataloging_enabled: bool = True
    validation_level: str = "standard"  # basic, standard, strict
    auto_select_target: bool = True
    verify_storage: bool = True

@dataclass
class StorageResult:
    """Result of complete storage process"""
    success: bool
    stored_data_info: Optional[Dict[str, Any]] = None
    target_recommendations: Optional[List[Dict[str, Any]]] = None
    storage_summary: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    catalog_info: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class DataStorageService:
    """
    Data Storage Service Suite
    
    Orchestrates data storage through 3 steps:
    1. Storage Target Selection (analyze data and recommend storage types)
    2. Data Persistence (execute storage using sink adapters)
    3. Storage Cataloging (update metadata store and create indexes)
    
    Follows the same pattern as preprocessor and transformation services.
    """
    
    def __init__(self, config: Optional[StorageConfig] = None):
        self.config = config or StorageConfig()
        
        # Initialize step services
        self.target_service = StorageTargetSelectionService()
        self.persistence_service = DataPersistenceService()
        self.catalog_service = StorageCatalogService()
        
        # Performance tracking
        self.execution_stats = {
            'total_storage_operations': 0,
            'successful_storage_operations': 0,
            'failed_storage_operations': 0,
            'total_data_stored_mb': 0,
            'average_duration': 0.0
        }
        
        logger.info("Data Storage Service initialized")
    
    async def store_data(self,
                  data: pl.DataFrame,
                  storage_spec: Dict[str, Any],
                  config: Optional[StorageConfig] = None) -> StorageResult:
        """
        Execute complete storage pipeline
        
        Args:
            data: Input DataFrame to store
            storage_spec: Specification of storage requirements
            config: Optional configuration override
            
        Returns:
            StorageResult with complete storage information
        """
        start_time = datetime.now()
        config = config or self.config
        
        try:
            logger.info(f"Starting storage pipeline for data shape: {(data.height, data.width)}")
            
            # Initialize result
            result = StorageResult(
                success=False,
                metadata={
                    'start_time': start_time,
                    'input_shape': (data.height, data.width),
                    'input_columns': list(data.columns),
                    'storage_spec': storage_spec
                }
            )
            
            storage_summary = {}
            performance_metrics = {}
            target_recommendations = []
            
            # Step 1: Storage Target Selection
            if config.target_selection_enabled:
                logger.info("Executing Step 1: Storage Target Selection")
                selection_result = self.target_service.select_targets(
                    data, 
                    storage_spec.get('target_selection', {})
                )
                
                if selection_result.success:
                    target_recommendations = selection_result.recommended_targets
                    storage_summary['target_selection'] = {
                        'recommendations': target_recommendations,
                        'data_analysis': selection_result.data_analysis
                    }
                    performance_metrics['target_selection'] = selection_result.performance_metrics
                    if selection_result.warnings:
                        result.warnings.extend(selection_result.warnings)
                else:
                    result.errors.extend(selection_result.errors)
                    result.errors.append("Step 1 (Target Selection) failed")
                    return self._finalize_result(result, start_time)
            
            # Determine storage configuration for persistence
            persistence_config = self._prepare_persistence_config(
                storage_spec, target_recommendations, config
            )
            
            # Step 2: Data Persistence
            if config.persistence_enabled:
                logger.info("Executing Step 2: Data Persistence")
                persistence_result = self.persistence_service.persist_data(
                    data,
                    persistence_config
                )
                
                if persistence_result.success:
                    storage_summary['persistence'] = persistence_result.storage_details
                    performance_metrics['persistence'] = persistence_result.performance_metrics
                    if persistence_result.warnings:
                        result.warnings.extend(persistence_result.warnings)
                else:
                    result.errors.extend(persistence_result.errors)
                    result.errors.append("Step 2 (Data Persistence) failed")
                    return self._finalize_result(result, start_time)
            else:
                return self._finalize_result(result, start_time, 
                                           error="Persistence disabled but required for storage")
            
            # Step 3: Storage Cataloging
            catalog_info = {}
            if config.cataloging_enabled:
                logger.info("Executing Step 3: Storage Cataloging")
                catalog_config = self._prepare_catalog_config(storage_spec, persistence_result)
                
                # Now that store_data is async, we can properly await catalog_storage
                catalog_result = await self.catalog_service.catalog_storage(
                    persistence_result.storage_details,
                    catalog_config
                )
                
                if catalog_result.success:
                    catalog_info = {
                        'catalog_entries': catalog_result.catalog_entries,
                        'metadata_updates': catalog_result.metadata_updates
                    }
                    storage_summary['cataloging'] = catalog_info
                    performance_metrics['cataloging'] = catalog_result.performance_metrics
                    if catalog_result.warnings:
                        result.warnings.extend(catalog_result.warnings)
                else:
                    result.errors.extend(catalog_result.errors)
                    result.errors.append("Step 3 (Storage Cataloging) failed")
                    # Don't fail the entire operation for cataloging errors
                    logger.warning("Cataloging failed but storage was successful")
            
            # Success
            result.success = True
            result.target_recommendations = target_recommendations
            result.stored_data_info = storage_summary.get('persistence', {})
            result.storage_summary = storage_summary
            result.performance_metrics = performance_metrics
            result.catalog_info = catalog_info
            
            return self._finalize_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Storage pipeline failed: {e}")
            result.errors.append(f"Pipeline error: {str(e)}")
            return self._finalize_result(result, start_time)
    
    def _prepare_persistence_config(self, 
                                   storage_spec: Dict[str, Any],
                                   recommendations: List[Dict[str, Any]],
                                   config: StorageConfig) -> Dict[str, Any]:
        """Prepare configuration for persistence step"""
        persistence_config = storage_spec.get('persistence', {}).copy()
        
        # Auto-select storage type if not specified and auto-selection is enabled
        if config.auto_select_target and not persistence_config.get('storage_type'):
            if recommendations:
                # Use top recommendation
                top_recommendation = recommendations[0]
                persistence_config['storage_type'] = top_recommendation['storage_type']
                logger.info(f"Auto-selected storage type: {top_recommendation['storage_type']} "
                           f"(score: {top_recommendation['score']})")
            else:
                # Default fallback
                persistence_config['storage_type'] = 'duckdb'
                logger.warning("No recommendations available, defaulting to DuckDB")
        
        # Ensure required fields
        if 'destination' not in persistence_config:
            persistence_config['destination'] = './data_storage'
        
        if 'table_name' not in persistence_config:
            persistence_config['table_name'] = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Add verification setting
        persistence_config['verify_storage'] = config.verify_storage
        
        return persistence_config
    
    def _prepare_catalog_config(self, 
                               storage_spec: Dict[str, Any],
                               persistence_result) -> Dict[str, Any]:
        """Prepare configuration for cataloging step"""
        catalog_config = storage_spec.get('cataloging', {}).copy()
        
        # Add default cataloging options
        catalog_config.setdefault('create_index', True)
        catalog_config.setdefault('track_lineage', True)
        catalog_config.setdefault('tags', [])
        catalog_config.setdefault('owner', 'system')
        
        # Add processing information for lineage
        catalog_config['source_data_info'] = {
            'input_shape': persistence_result.storage_details.get('storage_result', {}).get('rows_stored', 0),
            'processing_timestamp': datetime.now().isoformat()
        }
        
        return catalog_config
    
    def _finalize_result(self, 
                        result: StorageResult, 
                        start_time: datetime,
                        error: Optional[str] = None) -> StorageResult:
        """Finalize storage result with timing and stats"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if error:
            result.success = False
            result.errors.append(error)
        
        # Update performance metrics
        result.performance_metrics['total_duration'] = duration
        result.performance_metrics['end_time'] = end_time
        result.metadata['end_time'] = end_time
        result.metadata['duration_seconds'] = duration
        
        # Calculate storage size
        storage_size_mb = 0
        if result.stored_data_info:
            storage_size_mb = result.stored_data_info.get('storage_result', {}).get('file_size_mb', 0)
        
        # Update execution stats
        self.execution_stats['total_storage_operations'] += 1
        if result.success:
            self.execution_stats['successful_storage_operations'] += 1
            self.execution_stats['total_data_stored_mb'] += storage_size_mb
        else:
            self.execution_stats['failed_storage_operations'] += 1
        
        # Update average duration
        total = self.execution_stats['total_storage_operations']
        old_avg = self.execution_stats['average_duration']
        self.execution_stats['average_duration'] = (old_avg * (total - 1) + duration) / total
        
        logger.info(f"Storage completed: success={result.success}, duration={duration:.2f}s, "
                   f"size={storage_size_mb:.1f}MB")
        return result
    
    async def store_multiple_targets(self, 
                              data: pl.DataFrame,
                              target_configs: List[Dict[str, Any]]) -> Dict[str, StorageResult]:
        """Store data in multiple storage targets simultaneously"""
        results = {}
        
        for i, target_config in enumerate(target_configs):
            target_name = target_config.get('name', f'target_{i}')
            try:
                result = await self.store_data(data, target_config)
                results[target_name] = result
            except Exception as e:
                logger.error(f"Multi-target storage failed for {target_name}: {e}")
                results[target_name] = StorageResult(
                    success=False,
                    errors=[str(e)]
                )
        
        return results
    
    def get_storage_recommendations(self, data: pl.DataFrame, preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get storage recommendations without actually storing data"""
        try:
            selection_config = {'user_preferences': preferences} if preferences else {}
            
            selection_result = self.target_service.select_targets(data, selection_config)
            
            if selection_result.success:
                return {
                    'success': True,
                    'recommendations': selection_result.recommended_targets,
                    'data_analysis': selection_result.data_analysis,
                    'performance_metrics': selection_result.performance_metrics
                }
            else:
                return {
                    'success': False,
                    'errors': selection_result.errors
                }
                
        except Exception as e:
            logger.error(f"Storage recommendations failed: {e}")
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def search_stored_data(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search previously stored data using catalog service"""
        try:
            return self.catalog_service.search_catalog(search_criteria)
        except Exception as e:
            logger.error(f"Storage search failed: {e}")
            return []
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics"""
        try:
            catalog_stats = self.catalog_service.get_storage_statistics()
            
            return {
                'service_stats': self.get_execution_stats(),
                'catalog_stats': catalog_stats,
                'individual_service_stats': {
                    'target_selection': self.target_service.get_execution_stats(),
                    'persistence': self.persistence_service.get_execution_stats(),
                    'cataloging': self.catalog_service.get_execution_stats()
                }
            }
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")
            return {'error': str(e)}
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        return {
            **self.execution_stats,
            'success_rate': (
                self.execution_stats['successful_storage_operations'] / 
                max(1, self.execution_stats['total_storage_operations'])
            ),
            'average_storage_size_mb': (
                self.execution_stats['total_data_stored_mb'] / 
                max(1, self.execution_stats['successful_storage_operations'])
            )
        }
    
    def cleanup(self):
        """Cleanup all service resources"""
        try:
            self.persistence_service.cleanup()
            logger.info("Data Storage Service cleanup completed")
        except Exception as e:
            logger.warning(f"Storage service cleanup warning: {e}")
    
    def create_storage_spec(self, 
                           storage_type: Optional[str] = None,
                           destination: Optional[str] = None,
                           table_name: Optional[str] = None,
                           target_preferences: Optional[Dict[str, Any]] = None,
                           catalog_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Helper to create storage specification
        
        Args:
            storage_type: Specific storage type to use
            destination: Storage destination path
            table_name: Name for stored data
            target_preferences: Preferences for target selection
            catalog_options: Options for cataloging
            
        Returns:
            Complete storage specification
        """
        spec = {}
        
        # Target selection configuration
        if target_preferences:
            spec['target_selection'] = target_preferences
        
        # Persistence configuration
        persistence_config = {}
        if storage_type:
            persistence_config['storage_type'] = storage_type
        if destination:
            persistence_config['destination'] = destination
        if table_name:
            persistence_config['table_name'] = table_name
        
        if persistence_config:
            spec['persistence'] = persistence_config
        
        # Cataloging configuration
        if catalog_options:
            spec['cataloging'] = catalog_options
        
        return spec