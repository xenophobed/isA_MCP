"""
End-to-End Data Pipeline Orchestrator

Demonstrates the complete capability of the data_service module by orchestrating
all services into a cohesive data pipeline.

Pipeline Stages:
1. Data Ingestion & Preprocessing (Loading, Cleaning, Validation)
2. Data Augmentation (External Integration, Enrichment, Validation)
3. Data Transformation (Filtering, Aggregation, Feature Engineering)
4. Quality Management (Assessment, Monitoring, Improvement)
5. Metadata Management (Exploration, Semantic Enrichment, Storage)
6. Analytics & Visualization (EDA, SQL Query, Visualization)
7. Storage & Cataloging (Persistence, Target Selection, Cataloging)
"""

import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Import all data service components
from .preprocessor.preprocessor_service import PreprocessorService
from .augmentation.augmentation_service import DataAugmentationService
from .transformation.transformation_service import TransformationService
from .management.quality.quality_management_service import QualityManagementService
from .management.metadata.metadata_store_service import MetadataStoreService
from .analytics.data_eda import DataEDAService
from .search.sql_query_service import SQLQueryService
from .visualization.data_visualization import DataVisualizationService
from .storage.data_storage_service import DataStorageService

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline execution stages"""
    INGESTION = "ingestion"
    AUGMENTATION = "augmentation"
    TRANSFORMATION = "transformation"
    QUALITY = "quality"
    METADATA = "metadata"
    ANALYTICS = "analytics"
    STORAGE = "storage"


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution"""

    # Stage enablement
    enable_preprocessing: bool = True
    enable_augmentation: bool = True
    enable_transformation: bool = True
    enable_quality: bool = True
    enable_metadata: bool = True
    enable_analytics: bool = True
    enable_storage: bool = True

    # Stage-specific configs
    preprocessing_config: Optional[Dict[str, Any]] = None
    augmentation_spec: Optional[Dict[str, Any]] = None
    transformation_spec: Optional[Dict[str, Any]] = None
    quality_config: Optional[Dict[str, Any]] = None
    metadata_config: Optional[Dict[str, Any]] = None
    analytics_config: Optional[Dict[str, Any]] = None
    storage_config: Optional[Dict[str, Any]] = None

    # Pipeline behavior
    stop_on_error: bool = False
    quality_threshold: float = 0.7
    enable_monitoring: bool = True
    enable_caching: bool = True


@dataclass
class StageResult:
    """Result of a single pipeline stage"""
    stage: PipelineStage
    success: bool
    data: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


@dataclass
class PipelineResult:
    """Complete pipeline execution result"""
    success: bool
    final_data: Optional[pd.DataFrame] = None
    stage_results: List[StageResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    records_processed: int = 0
    quality_score: float = 0.0
    pipeline_metadata: Dict[str, Any] = field(default_factory=dict)
    visualizations: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'final_data_shape': self.final_data.shape if self.final_data is not None else None,
            'stage_results': [
                {
                    'stage': sr.stage.value,
                    'success': sr.success,
                    'data_shape': sr.data.shape if sr.data is not None else None,
                    'metrics': sr.metrics,
                    'duration_seconds': sr.duration_seconds,
                    'error_message': sr.error_message
                }
                for sr in self.stage_results
            ],
            'total_duration_seconds': self.total_duration_seconds,
            'records_processed': self.records_processed,
            'quality_score': self.quality_score,
            'pipeline_metadata': self.pipeline_metadata,
            'visualizations_count': len(self.visualizations),
            'error_message': self.error_message
        }


class DataPipelineOrchestrator:
    """
    End-to-End Data Pipeline Orchestrator

    Coordinates all data service components to execute a complete data pipeline:

    Stage 1 - Ingestion & Preprocessing:
        - Data loading from various sources
        - Data cleaning (nulls, duplicates, outliers)
        - Data validation (schema, constraints)

    Stage 2 - Data Augmentation:
        - External data integration
        - Data enrichment and merging
        - Merge validation

    Stage 3 - Data Transformation:
        - Filtering and sorting
        - Aggregation and grouping
        - Feature engineering
        - Business rules application

    Stage 4 - Quality Management:
        - Quality assessment
        - Quality monitoring
        - Quality improvement

    Stage 5 - Metadata Management:
        - Data exploration and profiling
        - Semantic enrichment
        - Metadata storage and retrieval

    Stage 6 - Analytics & Visualization:
        - Exploratory Data Analysis (EDA)
        - SQL-based querying
        - Data visualization

    Stage 7 - Storage & Cataloging:
        - Storage target selection
        - Data persistence
        - Catalog management
    """

    def __init__(self):
        """Initialize all service components"""
        # Core services that don't require special configuration
        self.preprocessor = PreprocessorService()
        self.augmentation = DataAugmentationService()
        self.transformation = TransformationService()
        self.quality_mgmt = QualityManagementService()
        self.metadata_store = MetadataStoreService()
        self.visualization = DataVisualizationService()
        self.storage = DataStorageService()

        # Services initialized per-pipeline as needed
        self.eda = None
        self.sql_query = None

        # Pipeline state
        self.execution_history: List[PipelineResult] = []

        logger.info("Data Pipeline Orchestrator initialized with core services")

    async def execute_pipeline(self,
                               input_data: pd.DataFrame,
                               config: PipelineConfig) -> PipelineResult:
        """
        Execute the complete end-to-end data pipeline

        Args:
            input_data: Raw input data
            config: Pipeline configuration

        Returns:
            PipelineResult with final data and execution details
        """
        start_time = datetime.now()
        stage_results = []
        current_data = input_data.copy()
        pipeline_metadata = {
            'start_time': start_time.isoformat(),
            'input_shape': input_data.shape,
            'stages_executed': []
        }

        try:
            logger.info(f"Starting pipeline execution with {len(input_data)} records")

            # Stage 1: Ingestion & Preprocessing
            if config.enable_preprocessing:
                stage_result = await self._execute_preprocessing(
                    current_data,
                    config.preprocessing_config or {}
                )
                stage_results.append(stage_result)

                if not stage_result.success and config.stop_on_error:
                    return self._build_error_result(stage_results, start_time, stage_result.error_message)

                if stage_result.data is not None:
                    current_data = stage_result.data
                    pipeline_metadata['stages_executed'].append('preprocessing')

            # Stage 2: Data Augmentation
            if config.enable_augmentation:
                stage_result = await self._execute_augmentation(
                    current_data,
                    config.augmentation_spec or {}
                )
                stage_results.append(stage_result)

                if not stage_result.success and config.stop_on_error:
                    return self._build_error_result(stage_results, start_time, stage_result.error_message)

                if stage_result.data is not None:
                    current_data = stage_result.data
                    pipeline_metadata['stages_executed'].append('augmentation')

            # Stage 3: Data Transformation
            if config.enable_transformation:
                stage_result = await self._execute_transformation(
                    current_data,
                    config.transformation_spec or {}
                )
                stage_results.append(stage_result)

                if not stage_result.success and config.stop_on_error:
                    return self._build_error_result(stage_results, start_time, stage_result.error_message)

                if stage_result.data is not None:
                    current_data = stage_result.data
                    pipeline_metadata['stages_executed'].append('transformation')

            # Stage 4: Quality Management
            if config.enable_quality:
                stage_result = await self._execute_quality_management(
                    current_data,
                    config.quality_config or {},
                    config.quality_threshold
                )
                stage_results.append(stage_result)

                quality_score = stage_result.metrics.get('quality_score', 0.0)

                if quality_score < config.quality_threshold and config.stop_on_error:
                    return self._build_error_result(
                        stage_results,
                        start_time,
                        f"Quality score {quality_score} below threshold {config.quality_threshold}"
                    )

                if stage_result.data is not None:
                    current_data = stage_result.data
                    pipeline_metadata['stages_executed'].append('quality')

            # Stage 5: Metadata Management
            if config.enable_metadata:
                stage_result = await self._execute_metadata_management(
                    current_data,
                    config.metadata_config or {}
                )
                stage_results.append(stage_result)
                pipeline_metadata['stages_executed'].append('metadata')
                pipeline_metadata['data_metadata'] = stage_result.metadata

            # Stage 6: Analytics & Visualization
            visualizations = []
            if config.enable_analytics:
                stage_result = await self._execute_analytics(
                    current_data,
                    config.analytics_config or {}
                )
                stage_results.append(stage_result)
                pipeline_metadata['stages_executed'].append('analytics')
                pipeline_metadata['analytics_summary'] = stage_result.metadata
                visualizations = stage_result.metadata.get('visualizations', [])

            # Stage 7: Storage & Cataloging
            if config.enable_storage:
                stage_result = await self._execute_storage(
                    current_data,
                    config.storage_config or {},
                    pipeline_metadata
                )
                stage_results.append(stage_result)
                pipeline_metadata['stages_executed'].append('storage')
                pipeline_metadata['storage_info'] = stage_result.metadata

            # Calculate final metrics
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()

            # Get final quality score
            quality_score = 0.0
            for sr in stage_results:
                if sr.stage == PipelineStage.QUALITY:
                    quality_score = sr.metrics.get('quality_score', 0.0)
                    break

            pipeline_metadata['end_time'] = end_time.isoformat()
            pipeline_metadata['output_shape'] = current_data.shape

            result = PipelineResult(
                success=True,
                final_data=current_data,
                stage_results=stage_results,
                total_duration_seconds=total_duration,
                records_processed=len(current_data),
                quality_score=quality_score,
                pipeline_metadata=pipeline_metadata,
                visualizations=visualizations
            )

            self.execution_history.append(result)
            logger.info(f"Pipeline completed successfully in {total_duration:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            return self._build_error_result(stage_results, start_time, str(e))

    async def _execute_preprocessing(self,
                                     data: pd.DataFrame,
                                     config: Dict[str, Any]) -> StageResult:
        """Execute preprocessing stage"""
        start_time = datetime.now()

        try:
            logger.info("Executing preprocessing stage")

            # Save data to temp file for preprocessor
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
            data.to_csv(temp_file.name, index=False)
            temp_file.close()

            # Use preprocessor service
            source_config = {
                'source_path': temp_file.name,
                'format': 'csv',
                'preprocessing_config': config
            }
            result = await self.preprocessor.process_data_source(source_config)

            duration = (datetime.now() - start_time).total_seconds()

            return StageResult(
                stage=PipelineStage.INGESTION,
                success=result.success,
                data=result.cleaned_data,
                metadata={
                    'validation_passed': result.validation_passed,
                    'cleaning_actions': result.cleaning_actions
                },
                metrics={
                    'records_in': len(data),
                    'records_out': len(result.cleaned_data) if result.cleaned_data is not None else 0,
                    'nulls_removed': result.cleaning_actions.get('nulls_removed', 0),
                    'duplicates_removed': result.cleaning_actions.get('duplicates_removed', 0)
                },
                duration_seconds=duration,
                error_message=result.error_message
            )

        except Exception as e:
            logger.error(f"Preprocessing stage failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            return StageResult(
                stage=PipelineStage.INGESTION,
                success=False,
                data=data,
                duration_seconds=duration,
                error_message=str(e)
            )

    async def _execute_augmentation(self,
                                    data: pd.DataFrame,
                                    spec: Dict[str, Any]) -> StageResult:
        """Execute augmentation stage"""
        start_time = datetime.now()

        try:
            logger.info("Executing augmentation stage")

            # Use augmentation service
            result = self.augmentation.augment_data(data, spec)

            duration = (datetime.now() - start_time).total_seconds()

            return StageResult(
                stage=PipelineStage.AUGMENTATION,
                success=result.success,
                data=result.augmented_data,
                metadata={
                    'external_sources': result.external_sources_connected,
                    'enrichment_rate': result.enrichment_rate,
                    'validation_passed': result.validation_passed
                },
                metrics={
                    'fields_added': result.fields_added,
                    'records_enriched': result.records_enriched,
                    'enrichment_rate': result.enrichment_rate,
                    'quality_score': result.quality_score
                },
                duration_seconds=duration,
                error_message=result.error_message
            )

        except Exception as e:
            logger.error(f"Augmentation stage failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            return StageResult(
                stage=PipelineStage.AUGMENTATION,
                success=False,
                data=data,
                duration_seconds=duration,
                error_message=str(e)
            )

    async def _execute_transformation(self,
                                      data: pd.DataFrame,
                                      spec: Dict[str, Any]) -> StageResult:
        """Execute transformation stage"""
        start_time = datetime.now()

        try:
            logger.info("Executing transformation stage")

            # Use transformation service
            result = await self.transformation.transform_data(data, spec)

            duration = (datetime.now() - start_time).total_seconds()

            return StageResult(
                stage=PipelineStage.TRANSFORMATION,
                success=result.success,
                data=result.transformed_data,
                metadata={
                    'transformations_applied': result.transformations_applied
                },
                metrics={
                    'records_in': len(data),
                    'records_out': len(result.transformed_data) if result.transformed_data is not None else 0,
                    'features_created': result.features_created,
                    'rules_applied': result.rules_applied
                },
                duration_seconds=duration,
                error_message=result.error_message
            )

        except Exception as e:
            logger.error(f"Transformation stage failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            return StageResult(
                stage=PipelineStage.TRANSFORMATION,
                success=False,
                data=data,
                duration_seconds=duration,
                error_message=str(e)
            )

    async def _execute_quality_management(self,
                                          data: pd.DataFrame,
                                          config: Dict[str, Any],
                                          threshold: float) -> StageResult:
        """Execute quality management stage"""
        start_time = datetime.now()

        try:
            logger.info("Executing quality management stage")

            # Use quality management service
            result = self.quality_mgmt.manage_data_quality(data, config)

            duration = (datetime.now() - start_time).total_seconds()

            return StageResult(
                stage=PipelineStage.QUALITY,
                success=result.success and result.overall_quality_score >= threshold,
                data=result.improved_data,
                metadata={
                    'quality_profile': result.quality_profile,
                    'issues_found': result.issues_found,
                    'improvements_applied': result.improvements_applied
                },
                metrics={
                    'quality_score': result.overall_quality_score,
                    'completeness': result.quality_profile.get('completeness', 0.0),
                    'consistency': result.quality_profile.get('consistency', 0.0),
                    'issues_count': result.issues_found
                },
                duration_seconds=duration,
                error_message=result.error_message
            )

        except Exception as e:
            logger.error(f"Quality management stage failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            return StageResult(
                stage=PipelineStage.QUALITY,
                success=False,
                data=data,
                duration_seconds=duration,
                error_message=str(e)
            )

    async def _execute_metadata_management(self,
                                           data: pd.DataFrame,
                                           config: Dict[str, Any]) -> StageResult:
        """Execute metadata management stage"""
        start_time = datetime.now()

        try:
            logger.info("Executing metadata management stage")

            # Store metadata
            metadata_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            result = self.metadata_store.store_dataset_metadata(
                dataset_name=metadata_id,
                data=data,
                user_metadata=config
            )

            duration = (datetime.now() - start_time).total_seconds()

            return StageResult(
                stage=PipelineStage.METADATA,
                success=result.success,
                data=data,
                metadata={
                    'metadata_id': metadata_id,
                    'metadata_stored': result.metadata_stored,
                    'semantic_tags': result.semantic_metadata.get('semantic_tags', []) if hasattr(result, 'semantic_metadata') else []
                },
                metrics={
                    'columns_analyzed': len(data.columns),
                    'rows_analyzed': len(data)
                },
                duration_seconds=duration,
                error_message=result.error_message
            )

        except Exception as e:
            logger.error(f"Metadata management stage failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            return StageResult(
                stage=PipelineStage.METADATA,
                success=False,
                data=data,
                duration_seconds=duration,
                error_message=str(e)
            )

    async def _execute_analytics(self,
                                 data: pd.DataFrame,
                                 config: Dict[str, Any]) -> StageResult:
        """Execute analytics stage"""
        start_time = datetime.now()

        try:
            logger.info("Executing analytics stage")

            # Create temp file for EDA if needed
            import tempfile
            import os

            temp_file = None
            eda_result = None

            try:
                # Save data to temporary CSV for EDA
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
                data.to_csv(temp_file.name, index=False)
                temp_file.close()

                # Initialize EDA with temp file
                from .analytics.data_eda import DataEDAService
                eda_service = DataEDAService(file_path=temp_file.name)

                # Perform EDA
                eda_result = await eda_service.perform_eda(data, config)
            finally:
                # Clean up temp file
                if temp_file and os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)

            # Generate visualizations
            visualizations = []

            # Create summary visualization
            if len(data.columns) > 0:
                numeric_cols = data.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    viz_result = await self.visualization.create_visualization(
                        data=data,
                        viz_type='bar',
                        config={
                            'x': numeric_cols[0],
                            'title': f'Distribution of {numeric_cols[0]}'
                        }
                    )
                    if viz_result.success:
                        visualizations.append({
                            'type': 'bar',
                            'title': f'Distribution of {numeric_cols[0]}',
                            'data': viz_result.chart_data
                        })

            duration = (datetime.now() - start_time).total_seconds()

            return StageResult(
                stage=PipelineStage.ANALYTICS,
                success=eda_result.success,
                data=data,
                metadata={
                    'eda_summary': eda_result.summary,
                    'visualizations': visualizations
                },
                metrics={
                    'insights_generated': len(eda_result.insights) if hasattr(eda_result, 'insights') else 0,
                    'visualizations_created': len(visualizations)
                },
                duration_seconds=duration,
                error_message=eda_result.error_message
            )

        except Exception as e:
            logger.error(f"Analytics stage failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            return StageResult(
                stage=PipelineStage.ANALYTICS,
                success=False,
                data=data,
                duration_seconds=duration,
                error_message=str(e)
            )

    async def _execute_storage(self,
                               data: pd.DataFrame,
                               config: Dict[str, Any],
                               pipeline_metadata: Dict[str, Any]) -> StageResult:
        """Execute storage stage"""
        start_time = datetime.now()

        try:
            logger.info("Executing storage stage")

            # Use storage service
            result = await self.storage.store_data(
                data=data,
                storage_spec=config,
                metadata=pipeline_metadata
            )

            duration = (datetime.now() - start_time).total_seconds()

            return StageResult(
                stage=PipelineStage.STORAGE,
                success=result.success,
                data=data,
                metadata={
                    'storage_location': result.storage_location,
                    'storage_format': result.storage_format,
                    'cataloged': result.cataloged
                },
                metrics={
                    'records_stored': len(data),
                    'size_bytes': result.size_bytes
                },
                duration_seconds=duration,
                error_message=result.error_message
            )

        except Exception as e:
            logger.error(f"Storage stage failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            return StageResult(
                stage=PipelineStage.STORAGE,
                success=False,
                data=data,
                duration_seconds=duration,
                error_message=str(e)
            )

    def _build_error_result(self,
                           stage_results: List[StageResult],
                           start_time: datetime,
                           error_message: str) -> PipelineResult:
        """Build error result for pipeline failure"""
        total_duration = (datetime.now() - start_time).total_seconds()

        return PipelineResult(
            success=False,
            stage_results=stage_results,
            total_duration_seconds=total_duration,
            error_message=error_message
        )

    def get_execution_history(self) -> List[PipelineResult]:
        """Get pipeline execution history"""
        return self.execution_history

    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get aggregated pipeline metrics"""
        if not self.execution_history:
            return {'total_executions': 0}

        successful = sum(1 for r in self.execution_history if r.success)
        total_records = sum(r.records_processed for r in self.execution_history)
        avg_duration = sum(r.total_duration_seconds for r in self.execution_history) / len(self.execution_history)
        avg_quality = sum(r.quality_score for r in self.execution_history) / len(self.execution_history)

        return {
            'total_executions': len(self.execution_history),
            'successful_executions': successful,
            'failed_executions': len(self.execution_history) - successful,
            'success_rate': successful / len(self.execution_history),
            'total_records_processed': total_records,
            'avg_execution_duration': avg_duration,
            'avg_quality_score': avg_quality
        }
