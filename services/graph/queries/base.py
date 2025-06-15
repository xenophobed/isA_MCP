from typing import Dict, Any, Optional, List, Protocol
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class QueryType(Enum):
    READ = "read"
    WRITE = "write"
    ANALYTICS = "analytics"
    MAINTENANCE = "maintenance"

@dataclass
class QueryMetrics:
    execution_time: float
    timestamp: datetime
    cache_hit: bool = False
    error: Optional[str] = None
    affected_nodes: int = 0
    affected_relationships: int = 0

class QueryTemplate(Protocol):
    name: str
    query: str
    query_type: QueryType
    version: str
    cacheable: bool
    timeout: int
    retry_count: int
    parameters: Dict[str, Any]

class BaseQuery:
    """Base class for all Neo4j queries"""
    
    def __init__(
        self,
        name: str,
        query: str,
        query_type: QueryType,
        version: str = "1.0",
        cacheable: bool = True,
        timeout: int = 30,
        retry_count: int = 3,
        parameters: Optional[Dict[str, Any]] = None,
        vector_field: str = "embedding"
    ):
        self.name = name
        self.query = query
        self.query_type = query_type
        self.version = version
        self.cacheable = cacheable
        self.timeout = timeout
        self.retry_count = retry_count
        self.parameters = parameters or {}
        self.metrics: List[QueryMetrics] = []
        self.vector_field = vector_field

    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate query parameters"""
        if not self.parameters:  # If no parameters defined, any params are valid
            return True
            
        if not params:
            raise ValueError(f"Required parameters: {list(self.parameters.keys())}")
            
        required_params = set(self.parameters.keys())
        provided_params = set(params.keys())
        
        missing_params = required_params - provided_params
        if missing_params:
            raise ValueError(f"Missing required parameters: {list(missing_params)}")
            
        # Type validation
        for param_name, expected_type in self.parameters.items():
            if param_name in params:
                value = params[param_name]
                if not isinstance(value, expected_type) and value is not None:
                    raise ValueError(
                        f"Parameter '{param_name}' must be of type {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )
        
        return True

    def record_metrics(self, metrics: QueryMetrics) -> None:
        """Record query execution metrics"""
        self.metrics.append(metrics)
        if len(self.metrics) > 1000:  # Keep last 1000 metrics
            self.metrics = self.metrics[-1000:]

    def get_average_execution_time(self) -> float:
        """Calculate average execution time"""
        if not self.metrics:
            return 0.0
        return sum(m.execution_time for m in self.metrics) / len(self.metrics)

    def get_error_rate(self) -> float:
        """Calculate error rate"""
        if not self.metrics:
            return 0.0
        error_count = sum(1 for m in self.metrics if m.error)
        return error_count / len(self.metrics)

    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if not self.metrics:
            return 0.0
        cache_hits = sum(1 for m in self.metrics if m.cache_hit)
        return cache_hits / len(self.metrics)

    def prepare_vector_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare parameters for vector operations"""
        if "embedding" in params:
            # Ensure vector is in correct format
            vector = params["embedding"]
            if hasattr(vector, 'tolist'):
                vector = vector.tolist()
            if isinstance(vector[0], list):
                vector = vector[0]
            params["embedding"] = [float(x) for x in vector]
        return params