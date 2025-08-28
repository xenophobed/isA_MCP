"""
Sink Adapters Package
Data storage adapters for writing processed data TO various destinations
"""

from .base_sink_adapter import BaseSinkAdapter
from .duckdb_adapter import DuckDBSinkAdapter
from .parquet_adapter import ParquetSinkAdapter
from .csv_adapter import CSVSinkAdapter

__all__ = [
    'BaseSinkAdapter',
    'DuckDBSinkAdapter', 
    'ParquetSinkAdapter',
    'CSVSinkAdapter'
]

# Adapter registry for dynamic loading
SINK_ADAPTERS = {
    'duckdb': DuckDBSinkAdapter,
    'parquet': ParquetSinkAdapter,
    'csv': CSVSinkAdapter
}

def get_sink_adapter(adapter_type: str, **kwargs):
    """
    Factory function to get sink adapter by type
    
    Args:
        adapter_type: Type of adapter ('duckdb', 'parquet', 'csv')
        **kwargs: Adapter-specific initialization parameters
        
    Returns:
        Initialized adapter instance
        
    Raises:
        ValueError: If adapter type is not supported
    """
    if adapter_type not in SINK_ADAPTERS:
        available = ', '.join(SINK_ADAPTERS.keys())
        raise ValueError(f"Unsupported sink adapter: {adapter_type}. Available: {available}")
    
    adapter_class = SINK_ADAPTERS[adapter_type]
    return adapter_class(**kwargs)

def list_sink_adapters():
    """Get list of available sink adapter types"""
    return list(SINK_ADAPTERS.keys())