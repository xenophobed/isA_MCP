#!/usr/bin/env python3
"""
Unified Data Models for Data Analytics Service

This module provides all data models, interfaces, and types used across
the data analytics service architecture.
"""

from .base_models import (
    AssetType,
    ProcessingStatus,
    ServiceType,
    ProcessingRequest,
    ProcessingResult,
    LayerResult,
    ServiceCapabilities,
    ServiceHealth
)

from .data_models import (
    DataSource,
    DataTarget,
    DataSchema,
    DataRecord,
    QueryRequest,
    QueryResult,
    AnalyticsRequest,
    AnalyticsResult,
    VisualizationRequest,
    VisualizationResult
)

from .graph_models import (
    GraphEntity,
    GraphRelationship,
    GraphQuery,
    GraphResult,
    KnowledgeGraph,
    GraphSchema
)

from .interfaces import (
    IAdapter,
    IProcessor,
    IService,
    IDataSource,
    IDataTarget,
    IExtractor,
    IAnalyzer,
    ITransformer
)

__all__ = [
    # Base models
    "AssetType",
    "ProcessingStatus", 
    "ServiceType",
    "ProcessingRequest",
    "ProcessingResult",
    "LayerResult",
    "ServiceCapabilities",
    "ServiceHealth",
    
    # Data models
    "DataSource",
    "DataTarget",
    "DataSchema",
    "DataRecord",
    "QueryRequest",
    "QueryResult",
    "AnalyticsRequest",
    "AnalyticsResult",
    "VisualizationRequest",
    "VisualizationResult",
    
    # Graph models
    "GraphEntity",
    "GraphRelationship",
    "GraphQuery",
    "GraphResult",
    "KnowledgeGraph",
    "GraphSchema",
    
    # Interfaces
    "IAdapter",
    "IProcessor",
    "IService",
    "IDataSource",
    "IDataTarget",
    "IExtractor",
    "IAnalyzer",
    "ITransformer"
] 