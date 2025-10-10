"""
External Integration Service
Step 1: Connect to and retrieve data from external sources
"""

import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ExternalIntegrationResult:
    """Result of external data integration"""
    success: bool
    external_data: Optional[pd.DataFrame] = None
    sources_connected: int = 0
    sources_failed: int = 0
    records_retrieved: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    source_details: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'external_data_shape': self.external_data.shape if self.external_data is not None else None,
            'sources_connected': self.sources_connected,
            'sources_failed': self.sources_failed,
            'records_retrieved': self.records_retrieved,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message,
            'source_details': self.source_details or {}
        }

class ExternalIntegrationService:
    """
    External Integration Service

    Connects to external data sources:
    - REST APIs
    - Database connections
    - File systems
    - Cloud storage
    - Third-party services
    """

    def __init__(self):
        self.supported_sources = {
            'rest_api': self._integrate_rest_api,
            'database': self._integrate_database,
            'file': self._integrate_file,
            'cloud_storage': self._integrate_cloud_storage,
            'custom': self._integrate_custom
        }
        logger.info("External Integration Service initialized")

    def integrate_external_sources(self,
                                   primary_data: pd.DataFrame,
                                   external_spec: Dict[str, Any]) -> ExternalIntegrationResult:
        """
        Integrate data from external sources

        Args:
            primary_data: Primary dataset
            external_spec: Specification of external sources

        Returns:
            ExternalIntegrationResult with retrieved data
        """
        start_time = datetime.now()

        try:
            sources = external_spec.get('sources', [])
            if not sources:
                logger.warning("No external sources specified")
                return ExternalIntegrationResult(
                    success=True,
                    external_data=None,
                    duration_seconds=0.0
                )

            all_external_data = []
            sources_connected = 0
            sources_failed = 0
            source_details = {}

            # Process each external source
            for source_config in sources:
                source_type = source_config.get('type', 'unknown')
                source_name = source_config.get('name', f'source_{len(all_external_data)}')

                try:
                    logger.info(f"Connecting to external source: {source_name} ({source_type})")

                    # Get integration method
                    integration_method = self.supported_sources.get(source_type)
                    if not integration_method:
                        logger.error(f"Unsupported source type: {source_type}")
                        sources_failed += 1
                        source_details[source_name] = {'status': 'unsupported', 'type': source_type}
                        continue

                    # Retrieve data
                    source_data = integration_method(primary_data, source_config)

                    if source_data is not None and len(source_data) > 0:
                        all_external_data.append(source_data)
                        sources_connected += 1
                        source_details[source_name] = {
                            'status': 'success',
                            'type': source_type,
                            'records': len(source_data),
                            'columns': list(source_data.columns)
                        }
                        logger.info(f"Successfully retrieved {len(source_data)} records from {source_name}")
                    else:
                        sources_failed += 1
                        source_details[source_name] = {'status': 'no_data', 'type': source_type}
                        logger.warning(f"No data retrieved from {source_name}")

                except Exception as e:
                    logger.error(f"Failed to integrate source {source_name}: {e}")
                    sources_failed += 1
                    source_details[source_name] = {'status': 'error', 'type': source_type, 'error': str(e)}

            # Combine all external data
            combined_external_data = None
            if all_external_data:
                if len(all_external_data) == 1:
                    combined_external_data = all_external_data[0]
                else:
                    # Concatenate if multiple sources
                    combined_external_data = pd.concat(all_external_data, axis=0, ignore_index=True)

            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return ExternalIntegrationResult(
                success=sources_connected > 0,
                external_data=combined_external_data,
                sources_connected=sources_connected,
                sources_failed=sources_failed,
                records_retrieved=len(combined_external_data) if combined_external_data is not None else 0,
                duration_seconds=duration,
                source_details=source_details
            )

        except Exception as e:
            logger.error(f"External integration failed: {e}", exc_info=True)
            duration = (datetime.now() - start_time).total_seconds()
            return ExternalIntegrationResult(
                success=False,
                error_message=str(e),
                duration_seconds=duration
            )

    def _integrate_rest_api(self, primary_data: pd.DataFrame, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Integrate data from REST API"""
        logger.info("REST API integration - placeholder implementation")
        return None

    def _integrate_database(self, primary_data: pd.DataFrame, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Integrate data from database"""
        logger.info("Database integration - placeholder implementation")
        return None

    def _integrate_file(self, primary_data: pd.DataFrame, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Integrate data from file"""
        logger.info("File integration - placeholder implementation")
        return None

    def _integrate_cloud_storage(self, primary_data: pd.DataFrame, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Integrate data from cloud storage"""
        logger.info("Cloud storage integration - placeholder implementation")
        return None

    def _integrate_custom(self, primary_data: pd.DataFrame, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Integrate data using custom function"""
        logger.info("Custom integration - placeholder implementation")
        return None
