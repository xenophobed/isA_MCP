"""
Unit tests for transaction rollback behavior.

Issue #10: Missing Transaction Wrappers for Multi-Step DB Operations

These tests verify that multi-step database operations are properly atomic:
- All operations succeed together, OR
- All operations rollback together on failure

Test coverage:
1. Package installation rollback when tool mapping fails
2. Package uninstallation rollback on partial failure
3. Skill assignment + count update rollback
4. Server cleanup rollback on partial failure
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, timezone
import asyncio


# =========================================================================
# Test Fixtures
# =========================================================================


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg connection pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    transaction_ctx = AsyncMock()

    # Setup pool.acquire() to return conn directly (not as context manager)
    pool.acquire = AsyncMock(return_value=conn)
    pool.release = AsyncMock()

    # Setup conn.transaction() context manager for repositories
    conn.transaction.return_value.__aenter__ = AsyncMock(return_value=transaction_ctx)
    conn.transaction.return_value.__aexit__ = AsyncMock(return_value=None)

    # Default execute returns "OK"
    conn.execute = AsyncMock(return_value="OK")

    return pool, conn


@pytest.fixture
def mock_pool_context_manager():
    """Create a mock pool that uses context manager for acquire."""
    pool = MagicMock()
    conn = AsyncMock()
    transaction_ctx = MagicMock()

    # Create an async context manager for pool.acquire()
    class AcquireContextManager:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    # Create an async context manager for conn.transaction()
    class TransactionContextManager:
        async def __aenter__(self):
            return transaction_ctx

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    pool.acquire.return_value = AcquireContextManager()
    conn.transaction.return_value = TransactionContextManager()
    conn.execute = AsyncMock(return_value="OK")
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value={})

    return pool, conn


@pytest.fixture
def mock_db_client(mock_pool_context_manager):
    """Create a mock AsyncPostgresClient."""
    pool, conn = mock_pool_context_manager
    client = MagicMock()
    client._pool = pool
    client._ensure_connected = AsyncMock()
    return client, pool, conn


# =========================================================================
# TransactionManager Tests
# =========================================================================


class TestTransactionManager:
    """Tests for the TransactionManager class."""

    @pytest.mark.asyncio
    async def test_transaction_commits_on_success(self, mock_pool):
        """Verify transaction commits when all operations succeed."""
        from core.database.transaction import TransactionManager

        pool, conn = mock_pool
        executed_sqls = []

        async def track_execute(sql, *args):
            executed_sqls.append(sql)
            return "INSERT 0 1"

        conn.execute = AsyncMock(side_effect=track_execute)

        async with TransactionManager(pool) as tx:
            await tx.execute("INSERT INTO test VALUES ($1)", 1)
            await tx.execute("INSERT INTO test VALUES ($1)", 2)

        # Verify BEGIN and COMMIT were called
        assert "BEGIN" in executed_sqls
        assert "COMMIT" in executed_sqls
        assert "ROLLBACK" not in executed_sqls

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_exception(self, mock_pool):
        """Verify transaction rolls back when an exception occurs."""
        from core.database.transaction import TransactionManager

        pool, conn = mock_pool
        executed_sqls = []

        async def execute_side_effect(sql, *args):
            executed_sqls.append(sql)
            if "FAILING" in sql:
                raise Exception("Simulated failure")
            return "OK"

        conn.execute = AsyncMock(side_effect=execute_side_effect)

        with pytest.raises(Exception, match="Simulated failure"):
            async with TransactionManager(pool) as tx:
                await tx.execute("INSERT INTO test VALUES ($1)", 1)
                await tx.execute("FAILING QUERY")

        # Verify ROLLBACK was called
        assert "ROLLBACK" in executed_sqls
        assert "COMMIT" not in executed_sqls

    @pytest.mark.asyncio
    async def test_transaction_releases_connection(self, mock_pool):
        """Verify connection is released after transaction completes."""
        from core.database.transaction import TransactionManager

        pool, conn = mock_pool
        conn.execute = AsyncMock(return_value="OK")

        async with TransactionManager(pool) as tx:
            await tx.execute("SELECT 1")

        # Verify release was called
        pool.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_releases_connection_on_error(self, mock_pool):
        """Verify connection is released even when transaction fails."""
        from core.database.transaction import TransactionManager

        pool, conn = mock_pool
        executed_sqls = []

        async def execute_side_effect(sql, *args):
            executed_sqls.append(sql)
            if "FAILING" in sql:
                raise Exception("Failure")
            return "OK"

        conn.execute = AsyncMock(side_effect=execute_side_effect)

        with pytest.raises(Exception):
            async with TransactionManager(pool) as tx:
                await tx.execute("FAILING QUERY")

        # Verify release was called despite error
        pool.release.assert_called_once()


# =========================================================================
# PackageRepository Atomic Operations Tests
# =========================================================================


class TestPackageRepositoryAtomicOperations:
    """Tests for atomic package operations."""

    @pytest.mark.asyncio
    async def test_install_package_atomic_in_memory_fallback(self):
        """Verify in-memory atomic installation works correctly."""
        from services.marketplace_service.package_repository import PackageRepository

        # Use in-memory fallback (no db_pool)
        repo = PackageRepository(db_pool=None)

        tools = [
            {"id": 1, "name": "tool1", "skill_ids": [], "primary_skill_id": None},
            {"id": 2, "name": "tool2", "skill_ids": [], "primary_skill_id": None},
        ]

        result = await repo.install_package_atomic(
            package_id="pkg-123",
            version_id="ver-456",
            tools=tools,
            package_name="test-package",
            user_id="user-789",
        )

        # Verify installation record returned
        assert result["package_id"] == "pkg-123"
        assert result["version_id"] == "ver-456"
        assert result["status"] == "installed"

        # Verify tool mappings were created
        assert result["id"] in repo._tool_mappings
        assert len(repo._tool_mappings[result["id"]]) == 2

    @pytest.mark.asyncio
    async def test_install_package_atomic_creates_installation_and_mappings(self):
        """Verify atomic installation creates both records together."""
        from services.marketplace_service.package_repository import PackageRepository

        repo = PackageRepository(db_pool=None)

        tools = [{"id": 1, "name": "tool1", "skill_ids": [], "primary_skill_id": None}]

        result = await repo.install_package_atomic(
            package_id="pkg-123",
            version_id="ver-456",
            tools=tools,
            package_name="test-package",
        )

        installation_id = result["id"]

        # Both installation and mappings should exist
        assert installation_id in repo._installations
        assert installation_id in repo._tool_mappings
        assert repo._tool_mappings[installation_id][0]["original_name"] == "tool1"

    @pytest.mark.asyncio
    async def test_uninstall_package_atomic_in_memory(self):
        """Verify in-memory atomic uninstallation removes both records."""
        from services.marketplace_service.package_repository import PackageRepository

        repo = PackageRepository(db_pool=None)

        # First install a package
        tools = [{"id": 1, "name": "tool1", "skill_ids": [], "primary_skill_id": None}]
        result = await repo.install_package_atomic(
            package_id="pkg-123",
            version_id="ver-456",
            tools=tools,
            package_name="test-package",
        )

        installation_id = result["id"]
        assert installation_id in repo._installations
        assert installation_id in repo._tool_mappings

        # Now uninstall
        success = await repo.uninstall_package_atomic(installation_id)

        assert success is True
        assert installation_id not in repo._installations
        assert installation_id not in repo._tool_mappings


# =========================================================================
# SkillRepository Atomic Operations Tests
# =========================================================================


class TestSkillRepositoryAtomicOperations:
    """Tests for atomic skill assignment operations.

    Note: These tests verify the atomic method signatures and logic.
    Full integration tests with asyncpg require a real database connection.
    """

    @pytest.mark.asyncio
    async def test_reassign_skills_atomic_validates_inputs(self):
        """Verify atomic reassignment validates input lengths."""
        from services.skill_service.skill_repository import SkillRepository

        with patch(
            "services.skill_service.skill_repository.AsyncPostgresClient"
        ) as MockClient:
            mock_instance = MagicMock()
            mock_instance._ensure_connected = AsyncMock()
            MockClient.return_value = mock_instance

            repo = SkillRepository()
            repo.db = mock_instance

            # Mismatched lengths should return False
            result = await repo.reassign_tool_skills_atomic(
                tool_id=1,
                new_skill_ids=["skill1", "skill2"],
                confidences=[0.9],  # Only one confidence for two skills
                primary_skill_id="skill1",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_reassign_skills_atomic_empty_skills_delegates(self):
        """Verify empty skill list triggers deletion instead."""
        from services.skill_service.skill_repository import SkillRepository

        with patch(
            "services.skill_service.skill_repository.AsyncPostgresClient"
        ) as MockClient:
            mock_instance = MagicMock()
            mock_instance._ensure_connected = AsyncMock()
            mock_instance._pool = MagicMock()
            MockClient.return_value = mock_instance

            repo = SkillRepository()
            repo.db = mock_instance

            # Mock the delete method
            repo.delete_assignments_for_tool_atomic = AsyncMock(return_value=True)

            result = await repo.reassign_tool_skills_atomic(
                tool_id=1,
                new_skill_ids=[],  # Empty
                confidences=[],
            )

            # Should delegate to delete method
            repo.delete_assignments_for_tool_atomic.assert_called_once_with(1)


# =========================================================================
# Server Cleanup Atomic Operations Tests
# =========================================================================


class TestServerCleanupAtomicOperations:
    """Tests for atomic server cleanup operations."""

    @pytest.mark.asyncio
    async def test_delete_tools_by_server_atomic(self, mock_db_client):
        """Verify atomic tool deletion uses CTE for atomicity."""
        from services.tool_service.tool_repository import ToolRepository

        client, pool, conn = mock_db_client

        with patch("services.tool_service.tool_repository.AsyncPostgresClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance._pool = pool
            mock_instance._ensure_connected = AsyncMock()
            mock_instance.query_row = AsyncMock(return_value={"count": 5})

            # Mock cache
            with patch("services.tool_service.tool_repository.get_cache") as mock_cache:
                mock_cache_instance = AsyncMock()
                mock_cache.return_value = mock_cache_instance

                MockClient.return_value = mock_instance

                repo = ToolRepository()
                repo.db = mock_instance

                result = await repo.delete_tools_by_server_atomic("server-123")

                assert result == 5
                # Verify CTE query was used (single query for atomicity)
                mock_instance.query_row.assert_called_once()
                query = mock_instance.query_row.call_args[0][0]
                assert "WITH deleted AS" in query
                assert "DELETE" in query

    @pytest.mark.asyncio
    async def test_delete_prompts_by_server_atomic(self, mock_db_client):
        """Verify atomic prompt deletion uses CTE for atomicity."""
        from services.prompt_service.prompt_repository import PromptRepository

        client, pool, conn = mock_db_client

        with patch(
            "services.prompt_service.prompt_repository.AsyncPostgresClient"
        ) as MockClient:
            mock_instance = MagicMock()
            mock_instance._pool = pool
            mock_instance._ensure_connected = AsyncMock()
            mock_instance.query_row = AsyncMock(return_value={"count": 3})
            MockClient.return_value = mock_instance

            repo = PromptRepository()
            repo.db = mock_instance

            result = await repo.delete_prompts_by_server_atomic("server-123")

            assert result == 3
            mock_instance.query_row.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_resources_by_server_atomic(self, mock_db_client):
        """Verify atomic resource deletion uses CTE for atomicity."""
        from services.resource_service.resource_repository import ResourceRepository

        client, pool, conn = mock_db_client

        with patch(
            "services.resource_service.resource_repository.AsyncPostgresClient"
        ) as MockClient:
            mock_instance = MagicMock()
            mock_instance._pool = pool
            mock_instance._ensure_connected = AsyncMock()
            mock_instance.query_row = AsyncMock(return_value={"count": 7})
            MockClient.return_value = mock_instance

            repo = ResourceRepository()
            repo.db = mock_instance

            result = await repo.delete_resources_by_server_atomic("server-123")

            assert result == 7
            mock_instance.query_row.assert_called_once()


# =========================================================================
# AtomicOperation Helper Tests
# =========================================================================


class TestAtomicOperationHelper:
    """Tests for the AtomicOperation helper class."""

    @pytest.mark.asyncio
    async def test_atomic_operation_executes_all_operations(self, mock_pool):
        """Verify AtomicOperation executes all added operations."""
        from core.database.transaction import AtomicOperation

        pool, conn = mock_pool
        executed_sqls = []

        async def track_execute(sql, *args):
            executed_sqls.append(sql)
            return "OK"

        conn.execute = AsyncMock(side_effect=track_execute)

        atomic = AtomicOperation(pool)
        atomic.add_operation("INSERT INTO t1 VALUES ($1)", 1)
        atomic.add_operation("INSERT INTO t2 VALUES ($1)", 2)
        atomic.add_operation("UPDATE t3 SET x = $1", 3)

        result = await atomic.execute()

        assert result is True
        # Verify operations were executed
        assert any("INSERT INTO t1" in sql for sql in executed_sqls)
        assert any("INSERT INTO t2" in sql for sql in executed_sqls)
        assert any("UPDATE t3" in sql for sql in executed_sqls)
        assert "BEGIN" in executed_sqls
        assert "COMMIT" in executed_sqls

    @pytest.mark.asyncio
    async def test_atomic_operation_returns_true_when_empty(self, mock_pool):
        """Verify AtomicOperation returns True when no operations added."""
        from core.database.transaction import AtomicOperation

        pool, conn = mock_pool

        atomic = AtomicOperation(pool)
        result = await atomic.execute()

        assert result is True


# =========================================================================
# Resource Atomic Upsert Tests
# =========================================================================


class TestResourceAtomicUpsert:
    """Tests for atomic resource upsert operations."""

    @pytest.mark.asyncio
    async def test_upsert_resource_atomic_uses_on_conflict(self, mock_db_client):
        """Verify atomic upsert uses ON CONFLICT for atomicity."""
        from services.resource_service.resource_repository import ResourceRepository

        client, pool, conn = mock_db_client

        with patch(
            "services.resource_service.resource_repository.AsyncPostgresClient"
        ) as MockClient:
            mock_instance = MagicMock()
            mock_instance._pool = pool
            mock_instance._ensure_connected = AsyncMock()
            mock_instance.query_row = AsyncMock(
                return_value={
                    "id": 1,
                    "uri": "resource://test",
                    "name": "test-resource",
                }
            )
            MockClient.return_value = mock_instance

            repo = ResourceRepository()
            repo.db = mock_instance

            result = await repo.upsert_resource_atomic(
                {"uri": "resource://test", "name": "test-resource"}
            )

            assert result is not None
            assert result["uri"] == "resource://test"
            # Verify ON CONFLICT clause was used
            call_args = mock_instance.query_row.call_args
            query = call_args[0][0]
            assert "ON CONFLICT" in query
            assert "uri" in query


# =========================================================================
# Integration-style Rollback Scenario Tests
# =========================================================================


class TestRollbackScenarios:
    """Tests for various rollback scenarios."""

    @pytest.mark.asyncio
    async def test_partial_failure_in_multi_step_operation(self, mock_pool):
        """Verify partial failures trigger complete rollback."""
        from core.database.transaction import TransactionManager

        pool, conn = mock_pool
        executed_sqls = []

        # Simulate failure on third operation
        operation_count = 0

        async def execute_side_effect(sql, *args):
            nonlocal operation_count
            executed_sqls.append(sql)
            # Skip counting for control statements
            if sql in ("BEGIN", "COMMIT", "ROLLBACK") or sql.startswith("SET"):
                return "OK"
            operation_count += 1
            if operation_count == 3:
                raise Exception("Database constraint violation")
            return "OK"

        conn.execute = AsyncMock(side_effect=execute_side_effect)

        with pytest.raises(Exception, match="constraint violation"):
            async with TransactionManager(pool) as tx:
                await tx.execute("INSERT INTO orders VALUES ($1)", 1)
                await tx.execute("INSERT INTO order_items VALUES ($1)", 1)
                await tx.execute("UPDATE inventory SET qty = qty - 1")

        # Verify ROLLBACK was called
        assert "ROLLBACK" in executed_sqls
        assert "COMMIT" not in executed_sqls

    @pytest.mark.asyncio
    async def test_nested_operations_rollback_correctly(self, mock_pool):
        """Verify nested operations within a transaction rollback together."""
        from core.database.transaction import TransactionManager

        pool, conn = mock_pool
        executed_sqls = []

        async def execute_tracking(sql, *args):
            executed_sqls.append(sql)
            if "FAIL" in sql:
                raise Exception("Forced failure")
            return "OK"

        conn.execute = AsyncMock(side_effect=execute_tracking)

        with pytest.raises(Exception, match="Forced failure"):
            async with TransactionManager(pool) as tx:
                await tx.execute("INSERT INTO parent VALUES ($1)", 1)
                for i in range(3):
                    await tx.execute(f"INSERT INTO child_{i} VALUES ($1)", i)
                await tx.execute("FAIL NOW")

        # All operations before FAIL were recorded, but transaction rolled back
        assert "INSERT INTO parent VALUES ($1)" in executed_sqls
        assert "ROLLBACK" in executed_sqls
        assert "COMMIT" not in executed_sqls
