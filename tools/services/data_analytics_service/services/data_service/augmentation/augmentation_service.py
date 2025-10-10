"""
Data Augmentation Service Suite
Main orchestrator for data augmentation operations following 3-step pipeline pattern
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Union
import logging
from dataclasses import dataclass, field
from datetime import datetime

from .external_integration import ExternalIntegrationService
from .data_enrichment import DataEnrichmentService
from .merge_validation import MergeValidationService

logger = logging.getLogger(__name__)

@dataclass
class AugmentationConfig:
    """Configuration for augmentation operations"""
    integration_enabled: bool = True
    enrichment_enabled: bool = True
    validation_enabled: bool = True
    conflict_resolution: str = "primary_first"  # primary_first, external_first, merge_all
    quality_threshold: float = 0.8

@dataclass
class AugmentationResult:
    """Result of complete augmentation process"""
    success: bool
    augmented_data: Optional[pd.DataFrame] = None
    original_data: Optional[pd.DataFrame] = None
    augmentation_summary: Dict[str, Any] = field(default_factory=dict)
    integration_results: Dict[str, Any] = field(default_factory=dict)
    enrichment_results: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class DataAugmentationService:
    """
    Data Augmentation Service Suite

    Orchestrates data augmentation through 3 steps:
    1. External Integration (connect to external data sources)
    2. Data Enrichment (merge and enhance data)
    3. Merge Validation (validate merged data quality)

    Follows the same pattern as other data_service modules.
    """

    def __init__(self, config: Optional[AugmentationConfig] = None):
        self.config = config or AugmentationConfig()

        # Initialize step services
        self.integration_service = ExternalIntegrationService()
        self.enrichment_service = DataEnrichmentService()
        self.validation_service = MergeValidationService()

        # Performance tracking
        self.execution_stats = {
            'total_augmentations': 0,
            'successful_augmentations': 0,
            'failed_augmentations': 0,
            'total_records_augmented': 0,
            'total_fields_added': 0,
            'average_duration': 0.0
        }

        logger.info("Data Augmentation Service initialized")

    def augment_data(self,
                    primary_data: pd.DataFrame,
                    augmentation_spec: Dict[str, Any],
                    config: Optional[AugmentationConfig] = None) -> AugmentationResult:
        """
        Execute complete augmentation pipeline

        Args:
            primary_data: Primary DataFrame to augment
            augmentation_spec: Specification of augmentation requirements
            config: Optional configuration override

        Returns:
            AugmentationResult with augmented data and metadata
        """
        start_time = datetime.now()
        config = config or self.config

        try:
            logger.info(f"Starting augmentation for data shape: {primary_data.shape}")

            # Initialize result
            result = AugmentationResult(
                success=False,
                original_data=primary_data.copy(),
                metadata={
                    'start_time': start_time,
                    'primary_shape': primary_data.shape,
                    'primary_columns': list(primary_data.columns),
                    'augmentation_spec': augmentation_spec
                }
            )

            # Step 1: External Integration (if enabled)
            external_data = None
            if config.integration_enabled and augmentation_spec.get('external_sources'):
                logger.info("Step 1: Integrating external data sources")
                integration_result = self.integration_service.integrate_external_sources(
                    primary_data=primary_data,
                    external_spec=augmentation_spec.get('external_sources', {})
                )

                if integration_result.success:
                    external_data = integration_result.external_data
                    result.integration_results = integration_result.to_dict()
                    logger.info(f"External integration successful: {len(external_data) if external_data is not None else 0} records")
                else:
                    result.warnings.append(f"External integration failed: {integration_result.error_message}")
                    logger.warning(f"External integration failed: {integration_result.error_message}")

            # Step 2: Data Enrichment (if enabled)
            enriched_data = primary_data.copy()
            if config.enrichment_enabled:
                logger.info("Step 2: Enriching data")
                enrichment_result = self.enrichment_service.enrich_data(
                    primary_data=primary_data,
                    external_data=external_data,
                    enrichment_spec=augmentation_spec.get('enrichment', {}),
                    conflict_resolution=config.conflict_resolution
                )

                if enrichment_result.success:
                    enriched_data = enrichment_result.enriched_data
                    result.enrichment_results = enrichment_result.to_dict()
                    logger.info(f"Data enrichment successful: {enriched_data.shape[1] - primary_data.shape[1]} fields added")
                else:
                    result.warnings.append(f"Data enrichment failed: {enrichment_result.error_message}")
                    logger.warning(f"Data enrichment failed: {enrichment_result.error_message}")

            # Step 3: Merge Validation (if enabled)
            if config.validation_enabled and enriched_data is not None:
                logger.info("Step 3: Validating merged data")
                validation_result = self.validation_service.validate_merge(
                    primary_data=primary_data,
                    augmented_data=enriched_data,
                    validation_spec=augmentation_spec.get('validation', {}),
                    quality_threshold=config.quality_threshold
                )

                result.validation_results = validation_result.to_dict()

                if not validation_result.passed:
                    result.warnings.append(f"Validation warnings: {validation_result.issues_count} issues found")
                    logger.warning(f"Merge validation found {validation_result.issues_count} issues")

            # Finalize result
            result.augmented_data = enriched_data
            result.success = True

            # Calculate summary
            result.augmentation_summary = {
                'records_processed': len(primary_data),
                'records_augmented': len(enriched_data) if enriched_data is not None else 0,
                'fields_original': len(primary_data.columns),
                'fields_final': len(enriched_data.columns) if enriched_data is not None else 0,
                'fields_added': (len(enriched_data.columns) - len(primary_data.columns)) if enriched_data is not None else 0,
                'external_sources_used': len(augmentation_spec.get('external_sources', [])),
                'enrichment_methods_applied': len(augmentation_spec.get('enrichment', {}))
            }

            # Performance metrics
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            result.performance_metrics = {
                'total_duration_seconds': duration,
                'records_per_second': len(primary_data) / duration if duration > 0 else 0,
                'integration_duration': result.integration_results.get('duration_seconds', 0),
                'enrichment_duration': result.enrichment_results.get('duration_seconds', 0),
                'validation_duration': result.validation_results.get('duration_seconds', 0)
            }

            # Update stats
            self.execution_stats['total_augmentations'] += 1
            self.execution_stats['successful_augmentations'] += 1
            self.execution_stats['total_records_augmented'] += len(primary_data)
            self.execution_stats['total_fields_added'] += result.augmentation_summary['fields_added']

            logger.info(f"Augmentation completed successfully in {duration:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Augmentation failed: {e}", exc_info=True)
            self.execution_stats['total_augmentations'] += 1
            self.execution_stats['failed_augmentations'] += 1

            return AugmentationResult(
                success=False,
                original_data=primary_data,
                errors=[str(e)],
                metadata={'error': str(e), 'start_time': start_time}
            )

    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get service execution statistics"""
        stats = self.execution_stats.copy()

        if stats['total_augmentations'] > 0:
            stats['success_rate'] = stats['successful_augmentations'] / stats['total_augmentations']
            stats['average_fields_per_augmentation'] = (
                stats['total_fields_added'] / stats['successful_augmentations']
                if stats['successful_augmentations'] > 0 else 0
            )
        else:
            stats['success_rate'] = 0.0
            stats['average_fields_per_augmentation'] = 0.0

        return stats
