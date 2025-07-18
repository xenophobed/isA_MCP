#!/usr/bin/env python3
"""
Unified Metadata Extraction Interface
Provides a simple, unified interface for extracting metadata from any data source
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Type
from abc import ABC, abstractmethod

from .processors.data_processors.metadata_extractor import (
    MetadataExtractor, 
    DataSourceConfig, 
    MetadataExtractionResult,
    TableInfo,
    ColumnInfo,
    RelationshipInfo,
    IndexInfo
)

logger = logging.getLogger(__name__)

class MetadataExtractionInterface:
    """
    Unified interface for extracting metadata from any data source
    
    This class provides a simple, consistent API for metadata extraction
    regardless of the underlying data source type.
    """
    
    def __init__(self):
        self.extractors: Dict[str, Type[MetadataExtractor]] = {}
        self.active_connections: Dict[str, MetadataExtractor] = {}
        
    def register_extractor(self, source_type: str, extractor_class: Type[MetadataExtractor]) -> None:
        """
        Register a metadata extractor for a specific source type
        
        Args:
            source_type: Type of data source (e.g., 'postgresql', 'mysql', 'csv', 'excel')
            extractor_class: MetadataExtractor subclass for this source type
        """
        self.extractors[source_type] = extractor_class
        logger.info(f"Registered extractor for source type: {source_type}")
    
    def get_supported_sources(self) -> List[str]:
        """Get list of supported data source types"""
        return list(self.extractors.keys())
    
    async def extract_metadata(self, 
                             source_type: str,
                             connection_params: Dict[str, Any],
                             include_data_analysis: bool = False,
                             sample_size: int = 1000,
                             cache_path: Optional[str] = None) -> MetadataExtractionResult:
        """
        Extract metadata from a data source
        
        Args:
            source_type: Type of data source
            connection_params: Connection parameters specific to the source type
            include_data_analysis: Whether to include detailed data analysis
            sample_size: Sample size for data analysis
            cache_path: Optional path to save/load cached results
            
        Returns:
            Complete metadata extraction result
            
        Raises:
            ValueError: If source type is not supported
            ConnectionError: If connection to data source fails
        """
        if source_type not in self.extractors:
            raise ValueError(f"Unsupported source type: {source_type}. Supported types: {self.get_supported_sources()}")
        
        # Create configuration
        config = DataSourceConfig(
            source_type=source_type,
            source_subtype=connection_params.get('subtype'),
            connection_params=connection_params,
            metadata_cache_path=cache_path,
            include_data_analysis=include_data_analysis,
            sample_size=sample_size
        )
        
        # Create extractor instance
        extractor_class = self.extractors[source_type]
        extractor = extractor_class(source_type)
        
        try:
            # Extract metadata
            logger.info(f"Starting metadata extraction for {source_type} source")
            result = await extractor.extract_full_metadata(config)
            
            logger.info(f"Successfully extracted metadata: {result.source_info['total_tables']} tables, "
                       f"{result.source_info['total_columns']} columns")
            
            return result
            
        except Exception as e:
            logger.error(f"Metadata extraction failed for {source_type}: {e}")
            raise
        finally:
            # Ensure cleanup
            try:
                await extractor.disconnect()
            except Exception as e:
                logger.warning(f"Error during extractor cleanup: {e}")
    
    async def quick_schema_summary(self, 
                                 source_type: str,
                                 connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a quick schema summary without full analysis
        
        Args:
            source_type: Type of data source
            connection_params: Connection parameters
            
        Returns:
            High-level schema summary
        """
        if source_type not in self.extractors:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        extractor_class = self.extractors[source_type]
        extractor = extractor_class(source_type)
        
        config = DataSourceConfig(
            source_type=source_type,
            connection_params=connection_params,
            include_data_analysis=False
        )
        
        try:
            if not await extractor.connect(config):
                raise ConnectionError(f"Failed to connect to {source_type}")
            
            summary = await extractor.get_schema_summary()
            return summary
            
        finally:
            await extractor.disconnect()
    
    async def test_connection(self, 
                            source_type: str,
                            connection_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test connection to a data source
        
        Args:
            source_type: Type of data source
            connection_params: Connection parameters
            
        Returns:
            Connection test result
        """
        if source_type not in self.extractors:
            return {
                "success": False,
                "error": f"Unsupported source type: {source_type}",
                "supported_types": self.get_supported_sources()
            }
        
        extractor_class = self.extractors[source_type]
        extractor = extractor_class(source_type)
        
        config = DataSourceConfig(
            source_type=source_type,
            connection_params=connection_params
        )
        
        try:
            success = await extractor.connect(config)
            
            if success:
                health = await extractor.health_check()
                await extractor.disconnect()
                return {
                    "success": True,
                    "health_check": health,
                    "message": f"Successfully connected to {source_type}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to connect to {source_type}",
                    "source_type": source_type
                }
                
        except Exception as e:
            try:
                await extractor.disconnect()
            except:
                pass
            
            return {
                "success": False,
                "error": str(e),
                "source_type": source_type
            }
    
    async def compare_schemas(self, 
                            source1_config: Dict[str, Any],
                            source2_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare schemas between two data sources
        
        Args:
            source1_config: Configuration for first source (must include 'source_type')
            source2_config: Configuration for second source (must include 'source_type')
            
        Returns:
            Schema comparison result
        """
        # Extract metadata from both sources
        metadata1 = await self.extract_metadata(
            source1_config['source_type'],
            source1_config,
            include_data_analysis=False
        )
        
        metadata2 = await self.extract_metadata(
            source2_config['source_type'],
            source2_config,
            include_data_analysis=False
        )
        
        # Compare schemas
        comparison = {
            "comparison_time": metadata1.source_info['extraction_time'],
            "source1_info": metadata1.source_info,
            "source2_info": metadata2.source_info,
            "table_comparison": self._compare_tables(metadata1.tables, metadata2.tables),
            "column_comparison": self._compare_columns(metadata1.columns, metadata2.columns),
            "relationship_comparison": self._compare_relationships(metadata1.relationships, metadata2.relationships)
        }
        
        return comparison
    
    def _compare_tables(self, tables1: List[Dict], tables2: List[Dict]) -> Dict[str, Any]:
        """Compare tables between two sources"""
        names1 = {t['table_name'] for t in tables1}
        names2 = {t['table_name'] for t in tables2}
        
        return {
            "common_tables": list(names1 & names2),
            "source1_only": list(names1 - names2),
            "source2_only": list(names2 - names1),
            "total_source1": len(names1),
            "total_source2": len(names2),
            "similarity_ratio": len(names1 & names2) / max(len(names1), len(names2)) if (names1 or names2) else 0
        }
    
    def _compare_columns(self, columns1: List[Dict], columns2: List[Dict]) -> Dict[str, Any]:
        """Compare columns between two sources"""
        # Group by table
        tables1_cols = {}
        tables2_cols = {}
        
        for col in columns1:
            table = col['table_name']
            if table not in tables1_cols:
                tables1_cols[table] = []
            tables1_cols[table].append(col['column_name'])
        
        for col in columns2:
            table = col['table_name']
            if table not in tables2_cols:
                tables2_cols[table] = []
            tables2_cols[table].append(col['column_name'])
        
        # Compare common tables
        common_tables = set(tables1_cols.keys()) & set(tables2_cols.keys())
        table_comparisons = {}
        
        for table in common_tables:
            cols1 = set(tables1_cols[table])
            cols2 = set(tables2_cols[table])
            
            table_comparisons[table] = {
                "common_columns": list(cols1 & cols2),
                "source1_only": list(cols1 - cols2),
                "source2_only": list(cols2 - cols1),
                "similarity_ratio": len(cols1 & cols2) / max(len(cols1), len(cols2)) if (cols1 or cols2) else 0
            }
        
        return {
            "table_comparisons": table_comparisons,
            "total_columns_source1": len(columns1),
            "total_columns_source2": len(columns2)
        }
    
    def _compare_relationships(self, relationships1: List[Dict], relationships2: List[Dict]) -> Dict[str, Any]:
        """Compare relationships between two sources"""
        rel_sigs1 = {f"{r['from_table']}.{r['from_column']} -> {r['to_table']}.{r['to_column']}" for r in relationships1}
        rel_sigs2 = {f"{r['from_table']}.{r['from_column']} -> {r['to_table']}.{r['to_column']}" for r in relationships2}
        
        return {
            "common_relationships": list(rel_sigs1 & rel_sigs2),
            "source1_only": list(rel_sigs1 - rel_sigs2),
            "source2_only": list(rel_sigs2 - rel_sigs1),
            "total_source1": len(rel_sigs1),
            "total_source2": len(rel_sigs2),
            "similarity_ratio": len(rel_sigs1 & rel_sigs2) / max(len(rel_sigs1), len(rel_sigs2)) if (relationships1 or relationships2) else 0
        }
    
    async def cleanup_all_connections(self) -> None:
        """Clean up all active connections"""
        for connection_id, extractor in list(self.active_connections.items()):
            try:
                await extractor.disconnect()
                logger.info(f"Cleaned up connection: {connection_id}")
            except Exception as e:
                logger.warning(f"Error cleaning up connection {connection_id}: {e}")
        
        self.active_connections.clear()

# Global instance for easy access
metadata_interface = MetadataExtractionInterface()

# Convenience functions
async def extract_metadata(source_type: str, 
                         connection_params: Dict[str, Any], 
                         **kwargs) -> MetadataExtractionResult:
    """Convenience function to extract metadata"""
    return await metadata_interface.extract_metadata(source_type, connection_params, **kwargs)

async def test_connection(source_type: str, 
                        connection_params: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to test connection"""
    return await metadata_interface.test_connection(source_type, connection_params)

def register_extractor(source_type: str, extractor_class: Type[MetadataExtractor]) -> None:
    """Convenience function to register extractor"""
    metadata_interface.register_extractor(source_type, extractor_class)

def get_supported_sources() -> List[str]:
    """Convenience function to get supported sources"""
    return metadata_interface.get_supported_sources()