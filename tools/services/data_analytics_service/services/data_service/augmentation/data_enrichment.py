"""
Data Enrichment Service
Step 2: Merge and enhance data from multiple sources
"""

import pandas as pd
from typing import Dict, Any, Optional
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class EnrichmentResult:
    """Result of data enrichment"""
    success: bool
    enriched_data: Optional[pd.DataFrame] = None
    fields_added: int = 0
    records_enriched: int = 0
    enrichment_rate: float = 0.0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    enrichment_details: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'enriched_data_shape': self.enriched_data.shape if self.enriched_data is not None else None,
            'fields_added': self.fields_added,
            'records_enriched': self.records_enriched,
            'enrichment_rate': self.enrichment_rate,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message,
            'enrichment_details': self.enrichment_details or {}
        }

class DataEnrichmentService:
    """
    Data Enrichment Service

    Merges primary data with external data:
    - Key-based joins
    - Fuzzy matching
    - Conflict resolution
    - Data transformation
    """

    def __init__(self):
        self.merge_strategies = {
            'left': self._merge_left,
            'inner': self._merge_inner,
            'outer': self._merge_outer,
            'fuzzy': self._merge_fuzzy
        }
        logger.info("Data Enrichment Service initialized")

    def enrich_data(self,
                   primary_data: pd.DataFrame,
                   external_data: Optional[pd.DataFrame],
                   enrichment_spec: Dict[str, Any],
                   conflict_resolution: str = "primary_first") -> EnrichmentResult:
        """
        Enrich primary data with external data

        Args:
            primary_data: Primary dataset
            external_data: External dataset to merge
            enrichment_spec: Enrichment configuration
            conflict_resolution: Strategy for resolving conflicts

        Returns:
            EnrichmentResult with enriched data
        """
        start_time = datetime.now()

        try:
            # If no external data, return primary data unchanged
            if external_data is None or len(external_data) == 0:
                logger.info("No external data available for enrichment")
                return EnrichmentResult(
                    success=True,
                    enriched_data=primary_data.copy(),
                    duration_seconds=0.0
                )

            # Get merge configuration
            merge_strategy = enrichment_spec.get('merge_strategy', 'left')
            join_keys = enrichment_spec.get('join_keys', {})

            if not join_keys:
                logger.warning("No join keys specified, cannot enrich data")
                return EnrichmentResult(
                    success=False,
                    error_message="No join keys specified",
                    enriched_data=primary_data.copy(),
                    duration_seconds=0.0
                )

            # Get merge method
            merge_method = self.merge_strategies.get(merge_strategy)
            if not merge_method:
                logger.error(f"Unsupported merge strategy: {merge_strategy}")
                return EnrichmentResult(
                    success=False,
                    error_message=f"Unsupported merge strategy: {merge_strategy}",
                    enriched_data=primary_data.copy(),
                    duration_seconds=0.0
                )

            # Perform merge
            logger.info(f"Enriching data using {merge_strategy} merge")
            enriched_data = merge_method(primary_data, external_data, join_keys, conflict_resolution)

            # Calculate enrichment metrics
            fields_added = len(enriched_data.columns) - len(primary_data.columns)
            records_enriched = self._count_enriched_records(primary_data, enriched_data, fields_added)
            enrichment_rate = records_enriched / len(primary_data) if len(primary_data) > 0 else 0.0

            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return EnrichmentResult(
                success=True,
                enriched_data=enriched_data,
                fields_added=fields_added,
                records_enriched=records_enriched,
                enrichment_rate=enrichment_rate,
                duration_seconds=duration,
                enrichment_details={
                    'merge_strategy': merge_strategy,
                    'join_keys': join_keys,
                    'conflict_resolution': conflict_resolution,
                    'original_fields': len(primary_data.columns),
                    'final_fields': len(enriched_data.columns),
                    'original_records': len(primary_data),
                    'final_records': len(enriched_data)
                }
            )

        except Exception as e:
            logger.error(f"Data enrichment failed: {e}", exc_info=True)
            duration = (datetime.now() - start_time).total_seconds()
            return EnrichmentResult(
                success=False,
                error_message=str(e),
                enriched_data=primary_data.copy(),
                duration_seconds=duration
            )

    def _merge_left(self,
                   primary_data: pd.DataFrame,
                   external_data: pd.DataFrame,
                   join_keys: Dict[str, Any],
                   conflict_resolution: str) -> pd.DataFrame:
        """Perform left merge (keep all primary records)"""
        left_on = join_keys.get('primary_key')
        right_on = join_keys.get('external_key', left_on)

        if not left_on or not right_on:
            logger.error("Join keys not specified")
            return primary_data.copy()

        merged = primary_data.merge(
            external_data,
            left_on=left_on,
            right_on=right_on,
            how='left',
            suffixes=('', '_external')
        )

        # Resolve conflicts
        if conflict_resolution == "external_first":
            merged = self._resolve_conflicts_external_first(merged)
        else:  # primary_first (default)
            merged = self._resolve_conflicts_primary_first(merged)

        return merged

    def _merge_inner(self,
                    primary_data: pd.DataFrame,
                    external_data: pd.DataFrame,
                    join_keys: Dict[str, Any],
                    conflict_resolution: str) -> pd.DataFrame:
        """Perform inner merge (only matching records)"""
        left_on = join_keys.get('primary_key')
        right_on = join_keys.get('external_key', left_on)

        merged = primary_data.merge(
            external_data,
            left_on=left_on,
            right_on=right_on,
            how='inner',
            suffixes=('', '_external')
        )

        return self._resolve_conflicts_primary_first(merged) if conflict_resolution == "primary_first" else self._resolve_conflicts_external_first(merged)

    def _merge_outer(self,
                    primary_data: pd.DataFrame,
                    external_data: pd.DataFrame,
                    join_keys: Dict[str, Any],
                    conflict_resolution: str) -> pd.DataFrame:
        """Perform outer merge (all records from both)"""
        left_on = join_keys.get('primary_key')
        right_on = join_keys.get('external_key', left_on)

        merged = primary_data.merge(
            external_data,
            left_on=left_on,
            right_on=right_on,
            how='outer',
            suffixes=('', '_external')
        )

        return self._resolve_conflicts_primary_first(merged) if conflict_resolution == "primary_first" else self._resolve_conflicts_external_first(merged)

    def _merge_fuzzy(self,
                    primary_data: pd.DataFrame,
                    external_data: pd.DataFrame,
                    join_keys: Dict[str, Any],
                    conflict_resolution: str) -> pd.DataFrame:
        """Perform fuzzy merge (approximate matching)"""
        # Placeholder for fuzzy matching implementation
        logger.warning("Fuzzy matching not yet implemented, falling back to left merge")
        return self._merge_left(primary_data, external_data, join_keys, conflict_resolution)

    def _resolve_conflicts_primary_first(self, merged_data: pd.DataFrame) -> pd.DataFrame:
        """Resolve conflicts by preferring primary data"""
        # Find columns with _external suffix
        external_cols = [col for col in merged_data.columns if col.endswith('_external')]

        for ext_col in external_cols:
            base_col = ext_col.replace('_external', '')

            if base_col in merged_data.columns:
                # Fill nulls in primary with external data
                merged_data[base_col] = merged_data[base_col].fillna(merged_data[ext_col])
                # Drop external column
                merged_data = merged_data.drop(columns=[ext_col])

        return merged_data

    def _resolve_conflicts_external_first(self, merged_data: pd.DataFrame) -> pd.DataFrame:
        """Resolve conflicts by preferring external data"""
        external_cols = [col for col in merged_data.columns if col.endswith('_external')]

        for ext_col in external_cols:
            base_col = ext_col.replace('_external', '')

            if base_col in merged_data.columns:
                # Use external data when available
                merged_data[base_col] = merged_data[ext_col].fillna(merged_data[base_col])
                # Drop external column
                merged_data = merged_data.drop(columns=[ext_col])

        return merged_data

    def _count_enriched_records(self, primary_data: pd.DataFrame, enriched_data: pd.DataFrame, fields_added: int) -> int:
        """Count how many records were actually enriched"""
        if fields_added == 0:
            return 0

        # Count records where at least one new field has a non-null value
        new_cols = [col for col in enriched_data.columns if col not in primary_data.columns]

        if not new_cols:
            return 0

        enriched_count = enriched_data[new_cols].notna().any(axis=1).sum()
        return enriched_count
