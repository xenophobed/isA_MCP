from typing import Optional
from app.services.db.duckdb.duck_service import DuckDBService
from app.services.db.duckdb.duck_pool import DuckDBConnectionPool

__all__ = ['DuckDBService', 'DuckDBConnectionPool', 'get_duckdb_service']

_service_instance: Optional[DuckDBService] = None

def get_duckdb_service(config=None) -> DuckDBService:
    """Get DuckDB service singleton instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = DuckDBService(config)
    return _service_instance 