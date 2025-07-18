#!/usr/bin/env python3
"""
Interfaces for Analytics Service Components

Defines abstract interfaces for adapters, processors, and services
to ensure consistent implementation across the architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
from .data_models import (
    DataSource, DataTarget, DataSchema, DataRecord, 
    QueryRequest, QueryResult, AnalyticsRequest, AnalyticsResult
)
from .graph_models import GraphEntity, GraphRelationship, GraphQuery, GraphResult
from .base_models import ProcessingRequest, ProcessingResult

class IDataSource(ABC):
    """Interface for data source connections"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to data source"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Close connection to data source"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if connection is valid"""
        pass
    
    @abstractmethod
    async def get_schema(self) -> DataSchema:
        """Get data source schema"""
        pass
    
    @abstractmethod
    async def execute_query(self, query: QueryRequest) -> QueryResult:
        """Execute query against data source"""
        pass

class IDataTarget(ABC):
    """Interface for data target connections"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to data target"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Close connection to data target"""
        pass
    
    @abstractmethod
    async def write_data(self, data: List[DataRecord]) -> bool:
        """Write data to target"""
        pass
    
    @abstractmethod
    async def create_schema(self, schema: DataSchema) -> bool:
        """Create schema in target"""
        pass

class IAdapter(ABC):
    """Base interface for all adapters"""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize adapter with configuration"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if adapter is healthy"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Get adapter capabilities"""
        pass

class IExtractor(ABC):
    """Interface for data extractors"""
    
    @abstractmethod
    async def extract(self, source: DataSource, options: Dict[str, Any]) -> List[DataRecord]:
        """Extract data from source"""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported data formats"""
        pass

class IAnalyzer(ABC):
    """Interface for data analyzers"""
    
    @abstractmethod
    async def analyze(self, data: List[DataRecord], options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data and return insights"""
        pass
    
    @abstractmethod
    def get_analysis_types(self) -> List[str]:
        """Get list of supported analysis types"""
        pass

class ITransformer(ABC):
    """Interface for data transformers"""
    
    @abstractmethod
    async def transform(self, data: List[DataRecord], options: Dict[str, Any]) -> List[DataRecord]:
        """Transform data according to options"""
        pass
    
    @abstractmethod
    def get_transformation_types(self) -> List[str]:
        """Get list of supported transformation types"""
        pass

class IProcessor(ABC):
    """Base interface for all processors"""
    
    @abstractmethod
    async def process(self, request: ProcessingRequest) -> ProcessingResult:
        """Process request and return result"""
        pass
    
    @abstractmethod
    def get_supported_operations(self) -> List[str]:
        """Get list of supported operations"""
        pass
    
    @abstractmethod
    async def validate_request(self, request: ProcessingRequest) -> bool:
        """Validate if request can be processed"""
        pass

class IService(ABC):
    """Base interface for all services"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize service"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """Shutdown service gracefully"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        pass
    
    @abstractmethod
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        pass

class IMetadataService(IService):
    """Interface for metadata services"""
    
    @abstractmethod
    async def extract_metadata(self, source: DataSource) -> Dict[str, Any]:
        """Extract metadata from data source"""
        pass
    
    @abstractmethod
    async def enrich_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich metadata with semantic information"""
        pass
    
    @abstractmethod
    async def store_metadata(self, metadata: Dict[str, Any], target: DataTarget) -> bool:
        """Store metadata in target"""
        pass

class IAnalyticsService(IService):
    """Interface for analytics services"""
    
    @abstractmethod
    async def execute_analytics(self, request: AnalyticsRequest) -> AnalyticsResult:
        """Execute analytics operation"""
        pass
    
    @abstractmethod
    async def get_analytics_history(self, limit: int = 100) -> List[AnalyticsResult]:
        """Get analytics execution history"""
        pass

class IVisualizationService(IService):
    """Interface for visualization services"""
    
    @abstractmethod
    async def generate_visualization(self, data: List[Dict[str, Any]], 
                                   chart_type: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Generate visualization from data"""
        pass
    
    @abstractmethod
    def get_supported_chart_types(self) -> List[str]:
        """Get list of supported chart types"""
        pass

class IGraphService(IService):
    """Interface for graph services"""
    
    @abstractmethod
    async def create_entity(self, entity: GraphEntity) -> bool:
        """Create graph entity"""
        pass
    
    @abstractmethod
    async def create_relationship(self, relationship: GraphRelationship) -> bool:
        """Create graph relationship"""
        pass
    
    @abstractmethod
    async def execute_graph_query(self, query: GraphQuery) -> GraphResult:
        """Execute graph query"""
        pass
    
    @abstractmethod
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get graph statistics"""
        pass

class IEmbeddingService(IService):
    """Interface for embedding services"""
    
    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        pass
    
    @abstractmethod
    async def similarity_search(self, query_embedding: List[float], 
                              limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar embeddings"""
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension"""
        pass

class IStreamProcessor(ABC):
    """Interface for stream processors"""
    
    @abstractmethod
    async def process_stream(self, data_stream: AsyncGenerator[Dict[str, Any], None]) -> AsyncGenerator[Dict[str, Any], None]:
        """Process streaming data"""
        pass
    
    @abstractmethod
    async def start_stream(self, source_config: Dict[str, Any]) -> bool:
        """Start stream processing"""
        pass
    
    @abstractmethod
    async def stop_stream(self) -> bool:
        """Stop stream processing"""
        pass

class IBatchProcessor(ABC):
    """Interface for batch processors"""
    
    @abstractmethod
    async def process_batch(self, data_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process batch of data"""
        pass
    
    @abstractmethod
    def get_batch_size(self) -> int:
        """Get optimal batch size"""
        pass
    
    @abstractmethod
    async def process_large_dataset(self, source: DataSource, 
                                   target: DataTarget, batch_size: Optional[int] = None) -> Dict[str, Any]:
        """Process large dataset in batches"""
        pass 