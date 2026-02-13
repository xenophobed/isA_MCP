"""
Mock for asyncpg database pool.

Provides a mock implementation of asyncpg connection pool
for testing without a real database connection.
"""

from typing import Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class QueryRecord:
    """Record of a query execution."""

    method: str
    query: str
    args: Tuple[Any, ...]


class MockAsyncpgPool:
    """
    Mock for asyncpg connection pool.

    Tracks all queries and allows setting mock responses.

    Example usage:
        pool = MockAsyncpgPool()
        pool.set_response("fetchrow", {"id": 1, "name": "test"})

        result = await pool.fetchrow("SELECT * FROM users WHERE id = $1", 1)
        assert result == {"id": 1, "name": "test"}

        # Verify query was executed
        assert len(pool.queries) == 1
        assert "SELECT * FROM users" in pool.queries[0].query
    """

    def __init__(self):
        self.queries: List[QueryRecord] = []
        self._responses: dict = {}
        self._response_sequences: dict = {}
        self._is_closed: bool = False

    async def fetchrow(self, query: str, *args) -> Optional[dict]:
        """Fetch a single row."""
        self._record_query("fetchrow", query, args)
        return self._get_response("fetchrow")

    async def fetch(self, query: str, *args) -> List[dict]:
        """Fetch multiple rows."""
        self._record_query("fetch", query, args)
        return self._get_response("fetch", default=[])

    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single value."""
        self._record_query("fetchval", query, args)
        return self._get_response("fetchval")

    async def execute(self, query: str, *args) -> str:
        """Execute a query without returning results."""
        self._record_query("execute", query, args)
        return self._get_response("execute", default="INSERT 0 1")

    async def executemany(self, query: str, args_list: List[Tuple]) -> None:
        """Execute a query with multiple argument sets."""
        for args in args_list:
            self._record_query("executemany", query, args)

    async def copy_records_to_table(self, table_name: str, records: List[Tuple], **kwargs) -> str:
        """Copy records to table."""
        self._record_query("copy", f"COPY TO {table_name}", tuple(records))
        return f"COPY {len(records)}"

    def set_response(self, method: str, data: Any) -> None:
        """Set a mock response for a method."""
        self._responses[method] = data

    def set_response_sequence(self, method: str, responses: List[Any]) -> None:
        """Set a sequence of responses for a method."""
        self._response_sequences[method] = list(responses)

    def _record_query(self, method: str, query: str, args: Tuple) -> None:
        """Record a query execution."""
        self.queries.append(QueryRecord(method=method, query=query, args=args))

    def _get_response(self, method: str, default: Any = None) -> Any:
        """Get the mock response for a method."""
        # Check for sequence first
        if method in self._response_sequences:
            seq = self._response_sequences[method]
            if seq:
                return seq.pop(0)

        return self._responses.get(method, default)

    def get_queries(self, method: str = None) -> List[QueryRecord]:
        """Get recorded queries, optionally filtered by method."""
        if method:
            return [q for q in self.queries if q.method == method]
        return self.queries

    def clear_queries(self) -> None:
        """Clear recorded queries."""
        self.queries = []

    def acquire(self) -> "MockConnectionContext":
        """Acquire a connection from the pool."""
        return MockConnectionContext(self)

    async def close(self) -> None:
        """Close the pool."""
        self._is_closed = True

    def is_closed(self) -> bool:
        """Check if pool is closed."""
        return self._is_closed


class MockConnectionContext:
    """
    Context manager for mock connection.

    Provides the same interface as asyncpg connection context.
    """

    def __init__(self, pool: MockAsyncpgPool):
        self.pool = pool
        self._in_transaction = False

    async def __aenter__(self) -> MockAsyncpgPool:
        """Enter context, return pool as connection."""
        return self.pool

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context."""
        pass

    def transaction(self) -> "MockTransactionContext":
        """Start a transaction."""
        return MockTransactionContext(self)


class MockTransactionContext:
    """Mock transaction context manager."""

    def __init__(self, conn: MockConnectionContext):
        self.conn = conn

    async def __aenter__(self) -> "MockTransactionContext":
        """Start transaction."""
        self.conn._in_transaction = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """End transaction."""
        self.conn._in_transaction = False
        if exc_type:
            # Rollback on exception
            pass
        else:
            # Commit on success
            pass


class MockDuckDBConnection:
    """
    Mock for DuckDB connection.

    Provides basic DuckDB-like interface for testing.
    """

    def __init__(self):
        self.queries: List[QueryRecord] = []
        self._responses: dict = {}

    def execute(self, query: str, parameters: Tuple = None) -> "MockDuckDBResult":
        """Execute a query."""
        self.queries.append(QueryRecord(method="execute", query=query, args=parameters or ()))
        return MockDuckDBResult(self._responses.get("execute", []))

    def executemany(self, query: str, parameters: List[Tuple]) -> None:
        """Execute query with multiple parameter sets."""
        for params in parameters:
            self.queries.append(QueryRecord(method="executemany", query=query, args=params))

    def set_response(self, method: str, data: Any) -> None:
        """Set mock response."""
        self._responses[method] = data

    def close(self) -> None:
        """Close connection."""
        pass


class MockDuckDBResult:
    """Mock DuckDB query result."""

    def __init__(self, data: List[Tuple]):
        self._data = data
        self._index = 0

    def fetchone(self) -> Optional[Tuple]:
        """Fetch one row."""
        if self._index < len(self._data):
            row = self._data[self._index]
            self._index += 1
            return row
        return None

    def fetchall(self) -> List[Tuple]:
        """Fetch all rows."""
        return self._data

    def fetchmany(self, size: int) -> List[Tuple]:
        """Fetch many rows."""
        result = self._data[self._index : self._index + size]
        self._index += size
        return result

    def df(self):
        """Return as pandas DataFrame."""
        try:
            import pandas as pd

            return pd.DataFrame(self._data)
        except ImportError:
            raise ImportError("pandas not installed")
