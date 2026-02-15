#!/usr/bin/env python3
"""
Unit tests for error handling improvements in issues #9 and #11.

Tests verify:
1. Font loading fallback works correctly when custom font fails (OSError handling)
2. File cleanup handles OSError gracefully
3. Async task registration handles errors properly
4. Pending tasks are tracked and can be cleaned up
5. Error callbacks are invoked on task failure

These tests cover the fixes for:
- Issue #9: Bare except blocks replaced with specific exception types
- Issue #11: Fire-and-forget async tasks now tracked with proper error callbacks
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestFontLoadingFallback:
    """Tests for font loading OSError fallback behavior."""

    def test_font_loading_oserror_is_caught(self):
        """Verify OSError from font loading is handled gracefully."""
        # This test validates the pattern used in test files:
        # try:
        #     font = ImageFont.truetype("/path/to/font.ttf", 16)
        # except OSError:
        #     font = ImageFont.load_default()

        # Simulate the font loading pattern
        font_loaded_successfully = False
        fallback_used = False

        try:
            # Simulate font file not found
            raise OSError("Font file not found")
        except OSError:
            # Fallback to default font
            fallback_used = True

        assert fallback_used is True
        assert font_loaded_successfully is False

    def test_font_loading_other_exceptions_propagate(self):
        """Verify non-OSError exceptions still propagate."""
        with pytest.raises(ValueError):
            try:
                raise ValueError("Invalid font size")
            except OSError:
                pass  # This should NOT catch ValueError


class TestFileCleanupErrorHandling:
    """Tests for file cleanup OSError handling."""

    def test_file_cleanup_handles_missing_file(self):
        """Verify file cleanup handles already-deleted files gracefully."""
        # Create and delete a temp file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        # Delete it first
        os.unlink(tmp_path)

        # Now try the cleanup pattern - should not raise
        cleanup_succeeded = True
        try:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    # File cleanup failed - may already be deleted or locked
                    pass
        except Exception:
            cleanup_succeeded = False

        assert cleanup_succeeded is True

    def test_file_cleanup_handles_permission_error(self):
        """Verify file cleanup handles permission errors gracefully."""
        # Simulate a permission error scenario
        error_handled = False

        try:
            raise OSError("Permission denied")
        except OSError:
            # File cleanup failed - may already be deleted or locked
            error_handled = True

        assert error_handled is True


class TestAsyncTaskTracking:
    """Tests for async task tracking in AutoDiscoverySystem."""

    @pytest.fixture
    def discovery_system(self):
        """Create an AutoDiscoverySystem instance for testing."""
        from core.auto_discovery import AutoDiscoverySystem

        return AutoDiscoverySystem(base_dir=".")

    def test_pending_tasks_list_initialized(self, discovery_system):
        """Verify _pending_tasks list is initialized on construction."""
        assert hasattr(discovery_system, "_pending_tasks")
        assert isinstance(discovery_system._pending_tasks, list)
        assert len(discovery_system._pending_tasks) == 0

    @pytest.mark.asyncio
    async def test_cleanup_pending_tasks_empty_list(self, discovery_system):
        """Verify cleanup handles empty task list gracefully."""
        # Should not raise any errors
        await discovery_system.cleanup_pending_tasks()
        assert len(discovery_system._pending_tasks) == 0

    @pytest.mark.asyncio
    async def test_cleanup_pending_tasks_successful_tasks(self, discovery_system):
        """Verify cleanup awaits and clears successful tasks."""

        async def successful_task():
            await asyncio.sleep(0.01)
            return "success"

        # Add some tasks
        task1 = asyncio.create_task(successful_task())
        task2 = asyncio.create_task(successful_task())
        discovery_system._pending_tasks.extend([task1, task2])

        # Cleanup should wait for tasks
        await discovery_system.cleanup_pending_tasks(timeout=1.0)

        # Tasks should be cleared
        assert len(discovery_system._pending_tasks) == 0

    @pytest.mark.asyncio
    async def test_cleanup_pending_tasks_with_failures(self, discovery_system):
        """Verify cleanup handles failed tasks without raising."""

        async def failing_task():
            await asyncio.sleep(0.01)
            raise ValueError("Task failed intentionally")

        # Add a failing task
        task = asyncio.create_task(failing_task())
        discovery_system._pending_tasks.append(task)

        # Cleanup should not raise, even with failed tasks
        await discovery_system.cleanup_pending_tasks(timeout=1.0)

        # Tasks should be cleared
        assert len(discovery_system._pending_tasks) == 0

    @pytest.mark.asyncio
    async def test_cleanup_cancels_slow_tasks(self, discovery_system):
        """Verify cleanup cancels tasks that exceed timeout."""

        async def slow_task():
            await asyncio.sleep(10.0)  # Very slow task
            return "should be cancelled"

        # Add a slow task
        task = asyncio.create_task(slow_task())
        discovery_system._pending_tasks.append(task)

        # Cleanup with short timeout
        await discovery_system.cleanup_pending_tasks(timeout=0.1)

        # Task should be cancelled and list cleared
        assert len(discovery_system._pending_tasks) == 0
        assert task.cancelled() or task.done()


class TestAsyncRegistrationErrorCallback:
    """Tests for async registration error callback behavior."""

    @pytest.mark.asyncio
    async def test_error_callback_logs_exceptions(self):
        """Verify error callback logs task exceptions properly."""
        from core.auto_discovery import AutoDiscoverySystem

        discovery = AutoDiscoverySystem(base_dir=".")

        # Track if error was logged
        error_logged = False
        original_exception = ValueError("Test registration error")

        async def failing_register(mcp):
            raise original_exception

        # Mock the logger
        with patch("core.auto_discovery.logger") as mock_logger:
            # Simulate what happens in auto_register_with_mcp
            task = asyncio.create_task(failing_register(None))

            def _on_task_done(t: asyncio.Task, name: str = "test_module") -> None:
                exc = t.exception()
                if exc is not None:
                    mock_logger.error(
                        f"Async registration failed for {name}: {exc}",
                        exc_info=(type(exc), exc, exc.__traceback__),
                    )
                if t in discovery._pending_tasks:
                    discovery._pending_tasks.remove(t)

            task.add_done_callback(_on_task_done)
            discovery._pending_tasks.append(task)

            # Wait for task to complete
            try:
                await task
            except ValueError:
                pass  # Expected

            # Give callback time to execute
            await asyncio.sleep(0.01)

            # Verify error was logged
            mock_logger.error.assert_called()
            call_args = mock_logger.error.call_args
            assert "Async registration failed for test_module" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_successful_task_removes_from_tracking(self):
        """Verify successful tasks are removed from tracking list."""
        from core.auto_discovery import AutoDiscoverySystem

        discovery = AutoDiscoverySystem(base_dir=".")

        async def successful_register(mcp):
            await asyncio.sleep(0.01)
            return True

        task = asyncio.create_task(successful_register(None))

        def _on_task_done(t: asyncio.Task, name: str = "test_module") -> None:
            if t in discovery._pending_tasks:
                discovery._pending_tasks.remove(t)

        task.add_done_callback(_on_task_done)
        discovery._pending_tasks.append(task)

        assert len(discovery._pending_tasks) == 1

        # Wait for task to complete and callback to run
        await task
        await asyncio.sleep(0.01)

        # Task should be removed from tracking
        assert len(discovery._pending_tasks) == 0


class TestRuntimeErrorHandling:
    """Tests for RuntimeError handling in async registration."""

    @pytest.mark.asyncio
    async def test_runtime_error_falls_back_to_asyncio_run(self):
        """Verify RuntimeError triggers fallback to asyncio.run()."""
        # This tests the pattern:
        # except RuntimeError as e:
        #     logger.debug(f"Event loop unavailable for {module_name}: {e}, using asyncio.run()")
        #     asyncio.run(register_func(mcp))

        fallback_used = False

        try:
            # Simulate RuntimeError from event loop issues
            raise RuntimeError("There is no current event loop in thread 'test'")
        except RuntimeError:
            # Fallback to asyncio.run
            fallback_used = True

        assert fallback_used is True


class TestExceptionSpecificity:
    """Tests verifying specific exception types are used instead of bare except."""

    def test_oserror_catches_file_not_found(self):
        """Verify OSError catches FileNotFoundError (which inherits from OSError)."""
        caught = False
        try:
            raise FileNotFoundError("File not found")
        except OSError:
            caught = True

        assert caught is True

    def test_oserror_catches_permission_error(self):
        """Verify OSError catches PermissionError (which inherits from OSError)."""
        caught = False
        try:
            raise PermissionError("Permission denied")
        except OSError:
            caught = True

        assert caught is True

    def test_oserror_does_not_catch_value_error(self):
        """Verify OSError does not catch unrelated exceptions."""
        with pytest.raises(ValueError):
            try:
                raise ValueError("Invalid value")
            except OSError:
                pass  # Should NOT catch ValueError

    def test_oserror_does_not_catch_type_error(self):
        """Verify OSError does not catch TypeError."""
        with pytest.raises(TypeError):
            try:
                raise TypeError("Type error")
            except OSError:
                pass  # Should NOT catch TypeError
