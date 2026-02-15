"""
Transaction Manager - Provides atomic transaction support for multi-step DB operations.

This module ensures data consistency when multiple database operations must succeed
or fail together. It wraps the AsyncPostgresClient's transaction capabilities.

Usage:
    # Method 1: Using TransactionManager context manager
    async with TransactionManager(db_pool) as tx:
        await tx.execute("INSERT INTO table1 ...")
        await tx.execute("INSERT INTO table2 ...")
        # Auto-commits on success, auto-rollbacks on exception

    # Method 2: Using @transactional decorator
    @transactional
    async def install_package(self, tx, package_data):
        await tx.execute("INSERT INTO installations ...")
        await tx.execute("INSERT INTO tool_mappings ...")
"""

import logging
import functools
from typing import Any, Callable, List, Optional, Dict, TypeVar, ParamSpec
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class TransactionManager:
    """
    Manages database transactions for atomic multi-step operations.

    TRANSACTION BOUNDARIES ensure that multiple database operations either
    all succeed together or all fail together (rollback).

    Attributes:
        _pool: The database connection pool (asyncpg Pool)
        _conn: The active connection within the transaction
        _in_transaction: Whether we are currently inside a transaction
    """

    def __init__(self, db_pool):
        """
        Initialize transaction manager.

        Args:
            db_pool: asyncpg connection pool (from AsyncPostgresClient._pool)
        """
        self._pool = db_pool
        self._conn = None
        self._in_transaction = False
        self._schema = "mcp"

    async def __aenter__(self):
        """Enter transaction context - acquire connection and begin transaction."""
        self._conn = await self._pool.acquire()
        await self._conn.execute("BEGIN")
        self._in_transaction = True
        logger.debug("Transaction started")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction context - commit on success, rollback on exception."""
        try:
            if exc_type is not None:
                # Exception occurred - rollback
                await self._conn.execute("ROLLBACK")
                logger.warning(f"Transaction rolled back due to: {exc_type.__name__}: {exc_val}")
            else:
                # Success - commit
                await self._conn.execute("COMMIT")
                logger.debug("Transaction committed")
        finally:
            self._in_transaction = False
            await self._pool.release(self._conn)
            self._conn = None

        # Don't suppress the exception - let it propagate
        return False

    async def execute(self, sql: str, *params) -> str:
        """
        Execute SQL statement within the transaction.

        Args:
            sql: SQL statement
            *params: Query parameters

        Returns:
            Result string from PostgreSQL (e.g., "INSERT 0 1")
        """
        if not self._in_transaction:
            raise RuntimeError("Cannot execute outside of transaction context")

        # Set schema
        await self._conn.execute(f"SET search_path TO {self._schema}, public")

        if params:
            return await self._conn.execute(sql, *params)
        return await self._conn.execute(sql)

    async def fetch(self, sql: str, *params) -> List[Dict[str, Any]]:
        """
        Execute SELECT query within the transaction.

        Args:
            sql: SQL query
            *params: Query parameters

        Returns:
            List of row dictionaries
        """
        if not self._in_transaction:
            raise RuntimeError("Cannot fetch outside of transaction context")

        await self._conn.execute(f"SET search_path TO {self._schema}, public")

        if params:
            rows = await self._conn.fetch(sql, *params)
        else:
            rows = await self._conn.fetch(sql)

        return [dict(row) for row in rows]

    async def fetchrow(self, sql: str, *params) -> Optional[Dict[str, Any]]:
        """
        Execute single row SELECT query within the transaction.

        Args:
            sql: SQL query
            *params: Query parameters

        Returns:
            Single row dictionary or None
        """
        if not self._in_transaction:
            raise RuntimeError("Cannot fetchrow outside of transaction context")

        await self._conn.execute(f"SET search_path TO {self._schema}, public")

        if params:
            row = await self._conn.fetchrow(sql, *params)
        else:
            row = await self._conn.fetchrow(sql)

        return dict(row) if row else None

    async def fetchval(self, sql: str, *params) -> Any:
        """
        Execute query and return single value.

        Args:
            sql: SQL query
            *params: Query parameters

        Returns:
            Single value from first column of first row
        """
        if not self._in_transaction:
            raise RuntimeError("Cannot fetchval outside of transaction context")

        await self._conn.execute(f"SET search_path TO {self._schema}, public")

        if params:
            return await self._conn.fetchval(sql, *params)
        return await self._conn.fetchval(sql)


@asynccontextmanager
async def get_transaction(db_client):
    """
    Context manager to get a transaction from an AsyncPostgresClient.

    Usage:
        async with get_transaction(self.db) as tx:
            await tx.execute(...)
            await tx.execute(...)

    Args:
        db_client: AsyncPostgresClient instance

    Yields:
        TransactionManager instance
    """
    # Ensure connected
    await db_client._ensure_connected()

    async with TransactionManager(db_client._pool) as tx:
        yield tx


def transactional(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to wrap a method in a database transaction.

    The decorated method receives an additional 'tx' keyword argument
    which is the TransactionManager instance.

    Usage:
        class MyRepository:
            @transactional
            async def multi_step_operation(self, data, tx=None):
                await tx.execute("INSERT INTO table1 ...")
                await tx.execute("INSERT INTO table2 ...")
                return result

    Note:
        The repository must have a 'db' attribute that is an AsyncPostgresClient.
    """

    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        # If already in a transaction (tx provided), use it
        if "tx" in kwargs and kwargs["tx"] is not None:
            return await func(self, *args, **kwargs)

        # Otherwise, create a new transaction
        async with get_transaction(self.db) as tx:
            kwargs["tx"] = tx
            return await func(self, *args, **kwargs)

    return wrapper


class AtomicOperation:
    """
    Helper class to build atomic multi-step operations.

    TRANSACTION BOUNDARY: All operations added via add_operation()
    will be executed atomically - either all succeed or all rollback.

    Usage:
        atomic = AtomicOperation(db_pool)
        atomic.add_operation("INSERT INTO table1 ...", param1, param2)
        atomic.add_operation("UPDATE table2 ...", param3)
        success = await atomic.execute()
    """

    def __init__(self, db_pool, schema: str = "mcp"):
        """
        Initialize atomic operation builder.

        Args:
            db_pool: asyncpg connection pool
            schema: Database schema (default: mcp)
        """
        self._pool = db_pool
        self._schema = schema
        self._operations: List[tuple] = []

    def add_operation(self, sql: str, *params):
        """
        Add an operation to the atomic batch.

        Args:
            sql: SQL statement
            *params: Query parameters
        """
        self._operations.append((sql, params))

    async def execute(self) -> bool:
        """
        Execute all operations atomically.

        Returns:
            True if all operations succeeded, False if rolled back

        Raises:
            Exception: Re-raises the original exception after rollback
        """
        if not self._operations:
            return True

        async with TransactionManager(self._pool) as tx:
            tx._schema = self._schema
            for sql, params in self._operations:
                await tx.execute(sql, *params)

        return True
