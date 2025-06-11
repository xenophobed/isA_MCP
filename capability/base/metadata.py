from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

class CapabilityMetadata(BaseModel):
    capability_id: str
    name: str
    type: str
    description: str
    last_updated: datetime = datetime.now()
    status: str = "active"
    version: str = "1.0.0"
    graph_source: str = "search_graph"
    node_name: Optional[str] = None
    key_elements: List[str] = []

class KnowledgeMetadata(CapabilityMetadata):
    source_type: str
    content_types: List[str]
    update_frequency: str
    collections: Dict[str, Dict] = {}
    document_semantics: Dict[str, Dict[str, Any]] = {}
    entries: Dict[str, List[Dict]] = {}
    example_queries: List[str] = []
    key_elements: List[str] = []

class ToolMetadata(CapabilityMetadata):
    api_endpoint: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    rate_limits: Dict[str, Any]
    key_elements: List[str]
    example_uses: List[str]

class DatabaseMetadata(CapabilityMetadata):
    database_type: str
    tables: List[str]
    schema: Dict[str, Any]
    example_queries: List[str]
    order_data: List[Dict]
