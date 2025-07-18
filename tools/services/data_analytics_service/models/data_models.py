#!/usr/bin/env python3
"""
Data Models for Analytics Service

Comprehensive data models for sources, targets, schemas, and operations.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path

class DataSourceType(Enum):
    """Data source types"""
    DATABASE = "database"
    FILE = "file"
    API = "api"
    STREAM = "stream"
    GRAPH = "graph"
    MEMORY = "memory"

class DataTargetType(Enum):
    """Data target types"""
    DATABASE = "database"
    FILE = "file"
    VECTOR_DB = "vector_db"
    GRAPH_DB = "graph_db"
    MEMORY = "memory"
    VISUALIZATION = "visualization"

class DataFormat(Enum):
    """Data formats"""
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    EXCEL = "excel"
    PDF = "pdf"
    TEXT = "text"
    BINARY = "binary"
    GRAPH = "graph"

class QueryType(Enum):
    """Query types"""
    SQL = "sql"
    SEMANTIC = "semantic"
    GRAPH = "graph"
    NATURAL_LANGUAGE = "natural_language"
    VECTOR = "vector"

@dataclass
class DataSource:
    """Data source configuration"""
    name: str
    type: DataSourceType
    connection_config: Dict[str, Any]
    schema: Optional['DataSchema'] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate data source configuration"""
        if self.type == DataSourceType.DATABASE:
            required_keys = ['host', 'database', 'username']
            if not all(key in self.connection_config for key in required_keys):
                raise ValueError(f"Database source requires: {required_keys}")
        elif self.type == DataSourceType.FILE:
            if 'path' not in self.connection_config:
                raise ValueError("File source requires 'path' in connection_config")

@dataclass
class DataTarget:
    """Data target configuration"""
    name: str
    type: DataTargetType
    connection_config: Dict[str, Any]
    schema: Optional['DataSchema'] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class DataSchema:
    """Data schema definition"""
    name: str
    fields: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_field_names(self) -> List[str]:
        """Get list of field names"""
        return [field['name'] for field in self.fields if 'name' in field and field['name']]
    
    def get_field_types(self) -> Dict[str, str]:
        """Get field name to type mapping"""
        return {
            field['name']: field['type'] 
            for field in self.fields 
            if 'name' in field and 'type' in field and field['name'] and field['type']
        }

@dataclass
class DataRecord:
    """Individual data record"""
    id: str
    data: Dict[str, Any]
    schema_name: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class QueryRequest:
    """Query request model"""
    query: str
    query_type: QueryType
    source: Union[str, DataSource]
    parameters: Dict[str, Any] = field(default_factory=dict)
    limit: Optional[int] = None
    offset: Optional[int] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(datetime.now().timestamp()))
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class QueryResult:
    """Query result model"""
    request_id: str
    success: bool
    data: List[Dict[str, Any]]
    schema: Optional[DataSchema] = None
    total_count: Optional[int] = None
    execution_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class AnalyticsRequest:
    """Analytics operation request"""
    operation: str  # extract, analyze, transform, summarize
    source: Union[str, DataSource]
    target: Optional[Union[str, DataTarget]] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(datetime.now().timestamp()))
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class AnalyticsResult:
    """Analytics operation result"""
    request_id: str
    operation: str
    success: bool
    data: Dict[str, Any]
    metrics: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class VisualizationRequest:
    """Visualization generation request"""
    data: List[Dict[str, Any]]
    chart_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    format: str = "json"  # json, html, svg, png
    request_id: str = field(default_factory=lambda: str(datetime.now().timestamp()))
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class VisualizationResult:
    """Visualization generation result"""
    request_id: str
    success: bool
    visualization_spec: Dict[str, Any]
    format: str
    data_summary: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now) 