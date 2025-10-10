#!/usr/bin/env python3
"""
Preprocessor Service - Integrated Steps 1-3 Pipeline
Combines data loading, validation, and cleaning services
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# Import the 3 preprocessing services
from .data_loading import DataLoadingService
from .data_validation import DataValidationService
from .data_cleaning import DataCleaningService

# Import new storage service suite
from tools.services.data_analytics_service.services.data_service.storage import DataStorageService

logger = logging.getLogger(__name__)

@dataclass
class PreprocessingResult:
    """Result from the complete preprocessing pipeline"""
    success: bool
    pipeline_id: str
    source_path: str
    user_id: str
    
    # Step 1: Data Loading & Format Detection
    loading_info: Dict[str, Any]
    loading_duration: float
    rows_detected: int
    columns_detected: int
    
    # Step 2: Data Validation & Type Analysis
    validation_info: Dict[str, Any]
    validation_duration: float
    data_quality_score: float
    validation_passed: bool
    
    # Step 3: Data Cleaning & Standardization
    cleaning_info: Dict[str, Any]
    cleaning_duration: float
    columns_standardized: int
    data_ready: bool
    
    # Overall Pipeline (required fields)
    total_duration: float
    created_at: datetime
    
    # Optional Step 4: Storage (new integration) - defaults last
    storage_info: Optional[Dict[str, Any]] = None
    storage_duration: float = 0.0
    data_stored: bool = False
    storage_locations: Optional[List[str]] = None
    error_message: Optional[str] = None

class PreprocessorService:
    """
    Preprocessor Service - Steps 1-3 Pipeline
    
    Orchestrates the complete preprocessing workflow:
    Step 1: Data Loading & Format Detection (DataLoadingService)
    Step 2: Data Validation & Type Analysis (DataValidationService)  
    Step 3: Data Cleaning & Standardization (DataCleaningService)
    
    Provides unified interface for preprocessing raw data into analysis-ready format
    """
    
    def __init__(self, user_id: str = "default_user"):
        """
        Initialize Preprocessor Service
        
        Args:
            user_id: User identifier for resource isolation
        """
        self.user_id = user_id
        self.service_name = "PreprocessorService"
        
        # Initialize the 3 step services
        self.loading_service = DataLoadingService()
        self.validation_service = DataValidationService()
        self.cleaning_service = DataCleaningService()
        
        # Initialize storage service (new integration)
        self.storage_service = DataStorageService()
        
        # Pipeline tracking
        self.processed_sources = {}
        self.pipeline_stats = {
            'total_pipelines': 0,
            'successful_pipelines': 0,
            'failed_pipelines': 0,
            'total_files_processed': 0,
            'total_rows_processed': 0,
            'average_quality_score': 0.0
        }
        
        logger.info(f"Preprocessor Service initialized for user: {user_id}")
        
        # Load existing pipeline state from disk
        self._load_pipeline_state()
    
    def _get_state_file_path(self) -> str:
        """Get the file path for storing pipeline state"""
        cache_dir = Path("cache/pipeline_state")
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir / f"preprocessor_{self.user_id}.json")
    
    def _load_pipeline_state(self):
        """Load pipeline state from disk"""
        try:
            state_file = self._get_state_file_path()
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    
                    # Reconstruct PreprocessingResult objects from JSON data
                    loaded_sources = {}
                    raw_sources = state.get('processed_sources', {})
                    for pipeline_id, result_data in raw_sources.items():
                        if isinstance(result_data, dict) and 'success' in result_data:
                            # Reconstruct PreprocessingResult from dictionary
                            loaded_sources[pipeline_id] = PreprocessingResult(**result_data)
                        else:
                            loaded_sources[pipeline_id] = result_data
                    
                    self.processed_sources = loaded_sources
                    self.pipeline_stats = state.get('pipeline_stats', self.pipeline_stats)
                    logger.info(f"Loaded pipeline state for user {self.user_id}: {len(self.processed_sources)} pipelines")
        except Exception as e:
            logger.warning(f"Failed to load pipeline state for user {self.user_id}: {e}")
    
    def _save_pipeline_state(self):
        """Save pipeline state to disk"""
        try:
            state_file = self._get_state_file_path()
            
            # Convert dataclass objects to dictionaries for JSON serialization
            serializable_sources = {}
            for pipeline_id, result in self.processed_sources.items():
                if hasattr(result, '__dict__'):
                    serializable_sources[pipeline_id] = asdict(result)
                else:
                    serializable_sources[pipeline_id] = result
            
            state = {
                'processed_sources': serializable_sources,
                'pipeline_stats': self.pipeline_stats,
                'last_updated': datetime.now().isoformat()
            }
            with open(state_file, 'w') as f:
                json.dump(state, f, default=str, indent=2)
            logger.debug(f"Saved pipeline state for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to save pipeline state for user {self.user_id}: {e}")
    
    async def process_data_source(self, 
                                source_path: str,
                                target_hint: Optional[str] = None,
                                cleaning_options: Dict[str, Any] = None,
                                pipeline_id: Optional[str] = None,
                                storage_options: Optional[Dict[str, Any]] = None) -> PreprocessingResult:
        """
        Process a complete data source through the 3-step preprocessing pipeline
        with optional storage integration
        
        Args:
            source_path: Path to data source file
            target_hint: Optional target column hint for ML preparation
            cleaning_options: Optional cleaning configuration
            pipeline_id: Optional custom pipeline identifier
            storage_options: Optional storage configuration for auto-storage
            
        Returns:
            PreprocessingResult with complete pipeline information
        """
        pipeline_start = datetime.now()
        
        if not pipeline_id:
            pipeline_id = f"preprocess_{int(pipeline_start.timestamp())}"
        
        logger.info(f"Starting preprocessing pipeline {pipeline_id} for source: {source_path}")
        
        try:
            # Step 1: Data Loading & Format Detection
            step1_start = datetime.now()
            logger.info(f"Pipeline {pipeline_id}: Step 1 - Data loading and format detection")
            
            loading_result = self.loading_service.load_data_source(source_path)
            
            if not loading_result.get('success'):
                raise Exception(f"Data loading failed: {loading_result.get('error')}")
            
            loaded_df = loading_result['dataframe']
            step1_duration = (datetime.now() - step1_start).total_seconds()
            rows_detected = loading_result['shape'][0]
            columns_detected = loading_result['shape'][1]
            
            logger.info(f"Pipeline {pipeline_id}: Step 1 completed - {rows_detected} rows, {columns_detected} columns ({step1_duration:.2f}s)")
            
            # Step 2: Data Validation & Type Analysis
            step2_start = datetime.now()
            logger.info(f"Pipeline {pipeline_id}: Step 2 - Data validation and type analysis")
            
            validation_result = self.validation_service.validate_dataframe(
                loaded_df, 
                source_info=loading_result.get('format_info', {})
            )
            
            if not validation_result.get('success'):
                raise Exception(f"Data validation failed: {validation_result.get('error')}")
            
            step2_duration = (datetime.now() - step2_start).total_seconds()
            data_quality_score = validation_result['validation_summary']['overall_score']
            validation_passed = validation_result['validation_summary']['validation_passed']
            
            logger.info(f"Pipeline {pipeline_id}: Step 2 completed - Quality score: {data_quality_score:.2f}, Passed: {validation_passed} ({step2_duration:.2f}s)")
            
            # Step 3: Data Cleaning & Standardization
            step3_start = datetime.now()
            logger.info(f"Pipeline {pipeline_id}: Step 3 - Data cleaning and standardization")
            
            cleaning_result = self.cleaning_service.clean_dataframe(
                loaded_df,
                validation_result,
                target_hint=target_hint,
                cleaning_options=cleaning_options
            )
            
            if not cleaning_result.get('success'):
                raise Exception(f"Data cleaning failed: {cleaning_result.get('error')}")
            
            step3_duration = (datetime.now() - step3_start).total_seconds()
            columns_standardized = cleaning_result['cleaning_summary']['column_standardization']['columns_renamed']
            data_ready = cleaning_result['cleaning_summary']['data_ready_for_analysis']
            
            logger.info(f"Pipeline {pipeline_id}: Step 3 completed - {columns_standardized} columns standardized, Data ready: {data_ready} ({step3_duration:.2f}s)")
            
            # Optional Step 4: Storage Integration (new)
            storage_info = {}
            storage_duration = 0.0
            data_stored = False
            storage_locations = []
            
            if storage_options and data_ready:
                step4_start = datetime.now()
                logger.info(f"Pipeline {pipeline_id}: Step 4 - Data storage (optional)")
                
                try:
                    cleaned_df = cleaning_result['cleaned_dataframe']
                    
                    # Prepare storage specification
                    storage_spec = self._prepare_storage_spec(
                        pipeline_id, source_path, storage_options, validation_result
                    )
                    
                    # Execute storage
                    storage_result = await self.storage_service.store_data(cleaned_df, storage_spec)
                    
                    if storage_result.success:
                        storage_info = {
                            'storage_result': storage_result,
                            'storage_spec': storage_spec
                        }
                        data_stored = True
                        
                        # Extract storage locations
                        if storage_result.stored_data_info:
                            destination = storage_result.stored_data_info.get('destination')
                            table_name = storage_result.stored_data_info.get('table_name')
                            if destination and table_name:
                                storage_locations.append(f"{destination}::{table_name}")
                        
                        logger.info(f"Pipeline {pipeline_id}: Step 4 completed - Data stored successfully")
                    else:
                        logger.warning(f"Pipeline {pipeline_id}: Step 4 failed - Storage errors: {storage_result.errors}")
                        storage_info = {'errors': storage_result.errors}
                
                except Exception as storage_error:
                    logger.warning(f"Pipeline {pipeline_id}: Step 4 failed - Storage error: {storage_error}")
                    storage_info = {'error': str(storage_error)}
                
                storage_duration = (datetime.now() - step4_start).total_seconds()
                logger.info(f"Pipeline {pipeline_id}: Step 4 completed in {storage_duration:.2f}s")
            
            # Calculate totals
            pipeline_end = datetime.now()
            total_duration = (pipeline_end - pipeline_start).total_seconds()
            
            # Create result
            result = PreprocessingResult(
                success=True,
                pipeline_id=pipeline_id,
                source_path=source_path,
                user_id=self.user_id,
                
                loading_info=loading_result,
                loading_duration=step1_duration,
                rows_detected=rows_detected,
                columns_detected=columns_detected,
                
                validation_info=validation_result,
                validation_duration=step2_duration,
                data_quality_score=data_quality_score,
                validation_passed=validation_passed,
                
                cleaning_info=cleaning_result,
                cleaning_duration=step3_duration,
                columns_standardized=columns_standardized,
                data_ready=data_ready,
                
                storage_info=storage_info,
                storage_duration=storage_duration,
                data_stored=data_stored,
                storage_locations=storage_locations,
                
                total_duration=total_duration,
                created_at=pipeline_start
            )
            
            # Update tracking
            self.processed_sources[pipeline_id] = result
            self._update_stats(result)
            
            # Save state to disk for persistence
            self._save_pipeline_state()
            
            logger.info(f"Preprocessing pipeline {pipeline_id} completed successfully in {total_duration:.2f}s")
            return result
            
        except Exception as e:
            error_duration = (datetime.now() - pipeline_start).total_seconds()
            error_message = str(e)
            
            logger.error(f"Preprocessing pipeline {pipeline_id} failed after {error_duration:.2f}s: {error_message}")
            
            # Create error result
            result = PreprocessingResult(
                success=False,
                pipeline_id=pipeline_id,
                source_path=source_path,
                user_id=self.user_id,
                
                loading_info={},
                loading_duration=0,
                rows_detected=0,
                columns_detected=0,
                
                validation_info={},
                validation_duration=0,
                data_quality_score=0.0,
                validation_passed=False,
                
                cleaning_info={},
                cleaning_duration=0,
                columns_standardized=0,
                data_ready=False,
                
                storage_info={},
                storage_duration=0.0,
                data_stored=False,
                storage_locations=[],
                
                total_duration=error_duration,
                created_at=pipeline_start,
                error_message=error_message
            )
            
            self.processed_sources[pipeline_id] = result
            self.pipeline_stats['failed_pipelines'] += 1
            
            # Save state to disk for persistence
            self._save_pipeline_state()
            
            return result
    
    async def process_multiple_sources(self, 
                                     sources: List[Dict[str, Any]], 
                                     concurrent_limit: int = 3) -> List[PreprocessingResult]:
        """
        Process multiple data sources with controlled concurrency
        
        Args:
            sources: List of source configurations [{'path': '...', 'target_hint': '...', 'cleaning_options': {...}, 'id': '...'}]
            concurrent_limit: Maximum concurrent pipeline executions
            
        Returns:
            List of PreprocessingResult objects
        """
        logger.info(f"Processing {len(sources)} sources with concurrency limit: {concurrent_limit}")
        
        semaphore = asyncio.Semaphore(concurrent_limit)
        
        async def process_with_semaphore(source_config):
            async with semaphore:
                return await self.process_data_source(
                    source_config['path'],
                    source_config.get('target_hint'),
                    source_config.get('cleaning_options'),
                    source_config.get('id')
                )
        
        # Execute with controlled concurrency
        tasks = [process_with_semaphore(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = PreprocessingResult(
                    success=False,
                    pipeline_id=f"error_{i}",
                    source_path=sources[i]['path'],
                    user_id=self.user_id,
                    loading_info={}, loading_duration=0, rows_detected=0, columns_detected=0,
                    validation_info={}, validation_duration=0, data_quality_score=0.0, validation_passed=False,
                    cleaning_info={}, cleaning_duration=0, columns_standardized=0, data_ready=False,
                    storage_info={}, storage_duration=0.0, data_stored=False, storage_locations=[],
                    total_duration=0, created_at=datetime.now(),
                    error_message=str(result)
                )
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        successful = sum(1 for r in final_results if r.success)
        failed = len(final_results) - successful
        
        logger.info(f"Batch preprocessing completed: {successful} successful, {failed} failed")
        
        return final_results
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        return {
            'service_info': {
                'service_name': self.service_name,
                'user_id': self.user_id,
                'total_processed_sources': len(self.processed_sources)
            },
            'pipeline_stats': self.pipeline_stats.copy(),
            'recent_pipelines': [
                {
                    'pipeline_id': result.pipeline_id,
                    'source_path': Path(result.source_path).name,
                    'success': result.success,
                    'duration': result.total_duration,
                    'data_quality_score': result.data_quality_score,
                    'data_ready': result.data_ready,
                    'created_at': result.created_at.isoformat()
                }
                for result in list(self.processed_sources.values())[-10:]  # Last 10
            ]
        }
    
    def get_pipeline_result(self, pipeline_id: str) -> Optional[PreprocessingResult]:
        """Get detailed result for a specific pipeline"""
        return self.processed_sources.get(pipeline_id)
    
    def get_cleaned_data(self, pipeline_id: str):
        """Get the cleaned DataFrame from a pipeline result"""
        result = self.get_pipeline_result(pipeline_id)
        if result and result.success:
            return result.cleaning_info.get('cleaned_dataframe')
        return None
    
    def get_column_mapping(self, pipeline_id: str) -> Dict[str, str]:
        """Get column mapping from a pipeline result"""
        result = self.get_pipeline_result(pipeline_id)
        if result and result.success:
            return result.cleaning_info.get('column_mapping', {})
        return {}
    
    def _prepare_storage_spec(self, 
                             pipeline_id: str, 
                             source_path: str, 
                             storage_options: Dict[str, Any],
                             validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare storage specification for the storage service"""
        storage_spec = {}
        
        # Default storage configuration
        default_destination = f"./preprocessed_data/{self.user_id}"
        default_table_name = f"preprocessed_{pipeline_id}"
        
        # Persistence configuration
        persistence_config = {
            'destination': storage_options.get('destination', default_destination),
            'table_name': storage_options.get('table_name', default_table_name),
            'storage_type': storage_options.get('storage_type'),  # Let storage service auto-select if None
            'verify_storage': storage_options.get('verify_storage', True)
        }
        
        # Add compression if specified
        if 'compression' in storage_options:
            persistence_config['compression'] = storage_options['compression']
        
        storage_spec['persistence'] = persistence_config
        
        # Cataloging configuration
        cataloging_config = {
            'tags': ['preprocessed', 'cleaned', f'user_{self.user_id}'],
            'description': f'Preprocessed data from {Path(source_path).name}',
            'owner': self.user_id,
            'source_data_info': {
                'original_source': source_path,
                'preprocessing_pipeline': pipeline_id,
                'data_quality_score': validation_result.get('validation_summary', {}).get('overall_score', 0)
            },
            'transformations_applied': [
                'data_loading',
                'data_validation', 
                'data_cleaning',
                'column_standardization'
            ]
        }
        
        # Add custom tags from storage options
        if 'tags' in storage_options:
            cataloging_config['tags'].extend(storage_options['tags'])
        
        storage_spec['cataloging'] = cataloging_config
        
        return storage_spec
    
    def _update_stats(self, result: PreprocessingResult):
        """Update internal pipeline statistics"""
        self.pipeline_stats['total_pipelines'] += 1
        
        if result.success:
            self.pipeline_stats['successful_pipelines'] += 1
            self.pipeline_stats['total_files_processed'] += 1
            self.pipeline_stats['total_rows_processed'] += result.rows_detected
            
            # Update average quality score
            current_avg = self.pipeline_stats['average_quality_score']
            successful_count = self.pipeline_stats['successful_pipelines']
            new_avg = ((current_avg * (successful_count - 1)) + result.data_quality_score) / successful_count
            self.pipeline_stats['average_quality_score'] = round(new_avg, 3)
        else:
            self.pipeline_stats['failed_pipelines'] += 1
    
    async def process_multiple_sources(self, 
                                      source_configs: List[Dict[str, Any]],
                                      batch_id: Optional[str] = None) -> Dict[str, PreprocessingResult]:
        """
        Process multiple data sources in batch
        
        Args:
            source_configs: List of source configurations, each containing:
                - source_path: path to data source
                - target_hint: optional target hint
                - cleaning_options: optional cleaning options  
                - storage_options: optional storage configuration
            batch_id: optional batch identifier
            
        Returns:
            Dictionary mapping source paths to preprocessing results
        """
        batch_id = batch_id or f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = {}
        
        logger.info(f"Starting batch preprocessing for {len(source_configs)} sources (batch: {batch_id})")
        
        for i, config in enumerate(source_configs):
            source_path = config.get('source_path')
            if not source_path:
                logger.error(f"Source config {i} missing source_path")
                continue
                
            pipeline_id = f"{batch_id}_source_{i}"
            
            try:
                result = await self.process_data_source(
                    source_path=source_path,
                    target_hint=config.get('target_hint'),
                    cleaning_options=config.get('cleaning_options'),
                    pipeline_id=pipeline_id,
                    storage_options=config.get('storage_options')
                )
                results[source_path] = result
                
            except Exception as e:
                logger.error(f"Batch processing failed for {source_path}: {e}")
                results[source_path] = PreprocessingResult(
                    success=False,
                    pipeline_id=pipeline_id,
                    errors=[f"Batch processing error: {str(e)}"]
                )
        
        logger.info(f"Batch preprocessing completed: {sum(1 for r in results.values() if r.success)}/{len(results)} successful")
        return results
    
    def get_stored_data_locations(self, pipeline_id: str) -> Dict[str, str]:
        """Get storage locations for preprocessed data from a pipeline"""
        result = self.get_pipeline_result(pipeline_id)
        if result and result.success and result.storage_info:
            storage_details = result.storage_info.get('storage_details', {})
            if storage_details:
                storage_type = storage_details.get('storage_type')
                destination = storage_details.get('destination')
                table_name = storage_details.get('table_name')
                
                if storage_type == 'duckdb':
                    return {
                        'type': storage_type,
                        'location': f"{destination}::{table_name}",
                        'destination': destination,
                        'table_name': table_name
                    }
                elif storage_type in ['parquet', 'csv']:
                    extension = '.parquet' if storage_type == 'parquet' else '.csv'
                    full_path = str(Path(destination) / f"{table_name}{extension}")
                    return {
                        'type': storage_type,
                        'location': full_path,
                        'destination': destination,
                        'table_name': table_name
                    }
        return {}
    
    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics including storage metrics"""
        stats = self.pipeline_stats.copy()
        
        # Add storage statistics
        stored_pipelines = 0
        storage_types = {}
        total_storage_size_mb = 0
        
        for result in self.processed_sources.values():
            if result.success and result.storage_info:
                stored_pipelines += 1
                storage_details = result.storage_info.get('storage_details', {})
                
                if storage_details:
                    storage_type = storage_details.get('storage_type', 'unknown')
                    storage_types[storage_type] = storage_types.get(storage_type, 0) + 1
                    
                    # Get storage size
                    storage_result = storage_details.get('storage_result', {})
                    size_mb = storage_result.get('file_size_mb', 0)
                    total_storage_size_mb += size_mb
        
        stats.update({
            'storage_statistics': {
                'pipelines_with_storage': stored_pipelines,
                'storage_types_used': storage_types,
                'total_storage_size_mb': round(total_storage_size_mb, 2),
                'average_storage_size_mb': round(total_storage_size_mb / max(stored_pipelines, 1), 2)
            }
        })
        
        return stats


# Global instances for different users
_preprocessor_services = {}

def get_preprocessor_service(user_id: str = "default_user") -> PreprocessorService:
    """Get preprocessor service instance for a specific user"""
    global _preprocessor_services
    
    if user_id not in _preprocessor_services:
        _preprocessor_services[user_id] = PreprocessorService(user_id)
    
    return _preprocessor_services[user_id]

# Convenience functions
async def preprocess_data_source(source_path: str, 
                               user_id: str = "default_user",
                               target_hint: Optional[str] = None,
                               cleaning_options: Dict[str, Any] = None,
                               storage_options: Optional[Dict[str, Any]] = None) -> PreprocessingResult:
    """Convenience function to preprocess a single data source with optional storage"""
    service = get_preprocessor_service(user_id)
    return await service.process_data_source(source_path, target_hint, cleaning_options, 
                                           storage_options=storage_options)

async def preprocess_multiple_sources(source_configs: List[Dict[str, Any]],
                                     user_id: str = "default_user",
                                     batch_id: Optional[str] = None) -> Dict[str, PreprocessingResult]:
    """Convenience function to preprocess multiple data sources in batch"""
    service = get_preprocessor_service(user_id)
    return await service.process_multiple_sources(source_configs, batch_id)

async def get_preprocessed_data(pipeline_id: str, user_id: str = "default_user"):
    """Convenience function to get preprocessed data"""
    service = get_preprocessor_service(user_id)
    return service.get_cleaned_data(pipeline_id)

def get_stored_data_location(pipeline_id: str, user_id: str = "default_user") -> Dict[str, str]:
    """Convenience function to get stored data location for a pipeline"""
    service = get_preprocessor_service(user_id)
    return service.get_stored_data_locations(pipeline_id)

def get_preprocessing_statistics(user_id: str = "default_user") -> Dict[str, Any]:
    """Convenience function to get preprocessing statistics"""
    service = get_preprocessor_service(user_id)
    return service.get_pipeline_statistics()