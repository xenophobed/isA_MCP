#!/usr/bin/env python3
"""
Progress Tracking Tools for Long-Running Operations

Provides MCP tools for:
- Starting long-running tasks
- Polling progress
- Getting results
- Cancelling operations
"""
import uuid
import asyncio
from datetime import datetime
from typing import Annotated, Dict, Any, Optional
from pydantic import Field

from tools.base_tool import BaseTool
from core.security import SecurityLevel
from core.logging import get_logger
from services.progress_service import ProgressManager

logger = get_logger(__name__)


class ProgressTools(BaseTool):
    """Tools for tracking progress of long-running operations"""

    def __init__(self):
        super().__init__()
        self.progress_manager = ProgressManager()
        logger.info("ProgressTools initialized with ProgressManager")

    def register_tools(self, mcp):
        """Register all progress tracking tools"""

        # Start a long-running task
        self.register_tool(
            mcp,
            self.start_long_task_impl,
            name="start_long_task",
            description="Start long-running task return operation ID for progress tracking monitoring",
            security_level=SecurityLevel.LOW
        )

        # Get progress
        self.register_tool(
            mcp,
            self.get_task_progress_impl,
            name="get_task_progress",
            description="Get current progress status percentage message of long-running task operation",
            security_level=SecurityLevel.LOW
        )

        # Get result
        self.register_tool(
            mcp,
            self.get_task_result_impl,
            name="get_task_result",
            description="Get final result output data of completed long-running task operation",
            security_level=SecurityLevel.LOW
        )

        # Cancel operation
        self.register_tool(
            mcp,
            self.cancel_task_impl,
            name="cancel_task",
            description="Cancel abort stop running long-running task operation by ID",
            security_level=SecurityLevel.LOW
        )

        # List operations
        self.register_tool(
            mcp,
            self.list_operations_impl,
            name="list_operations",
            description="List all tracked operations tasks with status progress filter",
            security_level=SecurityLevel.LOW
        )

        logger.debug(f"Registered {len(self.registered_tools)} progress tracking tools")

    # ========================================================================
    # Tool Implementations
    # ========================================================================

    async def start_long_task_impl(
        self,
        task_type: Annotated[str, Field(description="Type of task to run (e.g., 'data_analysis', 'web_scraping')")],
        duration_seconds: Annotated[int, Field(description="Task duration in seconds", ge=5, le=300)] = 30,
        steps: Annotated[int, Field(description="Number of processing steps", ge=1, le=100)] = 10,
        metadata: Annotated[Optional[Dict[str, Any]], Field(description="Optional task metadata")] = None
    ) -> Dict[str, Any]:
        """
        Start a long-running task and return operation ID for tracking

        The task runs in the background. Use get_task_progress() to poll progress.

        Args:
            task_type: Type of task
            duration_seconds: How long the task will run (5-300 seconds)
            steps: Number of steps to simulate (1-100)
            metadata: Optional metadata dictionary

        Returns:
            operation_id and status
        """
        # Generate unique operation ID
        operation_id = str(uuid.uuid4())

        # Start tracking
        await self.progress_manager.start_operation(
            operation_id,
            metadata={
                "task_type": task_type,
                "duration_seconds": duration_seconds,
                "steps": steps,
                **(metadata or {})
            }
        )

        # Start background task
        asyncio.create_task(
            self._run_long_task(operation_id, task_type, duration_seconds, steps)
        )

        logger.info(f"Started long task: {operation_id} ({task_type}, {duration_seconds}s)")

        return self.create_response(
            "success",
            "start_long_task",
            {
                "operation_id": operation_id,
                "status": "running",
                "task_type": task_type,
                "duration_seconds": duration_seconds,
                "steps": steps,
                "message": f"Task started. Poll get_task_progress('{operation_id}') to track progress."
            }
        )

    async def get_task_progress_impl(
        self,
        operation_id: Annotated[str, Field(description="Operation ID from start_long_task")]
    ) -> Dict[str, Any]:
        """
        Get current progress of a long-running task

        Poll this endpoint every 1-2 seconds to get real-time progress updates.

        Args:
            operation_id: The operation ID returned by start_long_task

        Returns:
            Current progress status, percentage, and message
        """
        progress = await self.progress_manager.get_progress(operation_id)

        if not progress:
            return self.create_response(
                "error",
                "get_task_progress",
                {
                    "error": "Operation not found",
                    "operation_id": operation_id
                },
                error_code="NOT_FOUND"
            )

        return self.create_response(
            "success",
            "get_task_progress",
            {
                "operation_id": progress.operation_id,
                "status": progress.status,
                "progress": progress.progress,
                "current": progress.current,
                "total": progress.total,
                "message": progress.message,
                "started_at": progress.started_at,
                "updated_at": progress.updated_at,
                "metadata": progress.metadata,
                "error": progress.error
            }
        )

    async def get_task_result_impl(
        self,
        operation_id: Annotated[str, Field(description="Operation ID from start_long_task")]
    ) -> Dict[str, Any]:
        """
        Get final result of a completed task

        Call this after get_task_progress shows status='completed'.

        Args:
            operation_id: The operation ID returned by start_long_task

        Returns:
            Final task result
        """
        # Check progress first
        progress = await self.progress_manager.get_progress(operation_id)

        if not progress:
            return self.create_response(
                "error",
                "get_task_result",
                {
                    "error": "Operation not found",
                    "operation_id": operation_id
                },
                error_code="NOT_FOUND"
            )

        if progress.status != "completed":
            return self.create_response(
                "error",
                "get_task_result",
                {
                    "error": f"Task not completed yet. Current status: {progress.status}",
                    "operation_id": operation_id,
                    "progress": progress.progress,
                    "message": progress.message
                },
                error_code="NOT_READY"
            )

        # Get result
        result = await self.progress_manager.get_result(operation_id)

        if not result:
            return self.create_response(
                "error",
                "get_task_result",
                {"error": "Result not found", "operation_id": operation_id},
                error_code="RESULT_NOT_FOUND"
            )

        return self.create_response(
            "success",
            "get_task_result",
            {
                "operation_id": operation_id,
                "result": result,
                "completed_at": progress.completed_at
            }
        )

    async def cancel_task_impl(
        self,
        operation_id: Annotated[str, Field(description="Operation ID to cancel")]
    ) -> Dict[str, Any]:
        """
        Cancel a running task

        The task will stop processing and status will change to 'cancelled'.

        Args:
            operation_id: The operation ID to cancel

        Returns:
            Cancellation status
        """
        progress = await self.progress_manager.cancel_operation(operation_id)

        if not progress:
            return self.create_response(
                "error",
                "cancel_task",
                {
                    "error": "Operation not found",
                    "operation_id": operation_id
                },
                error_code="NOT_FOUND"
            )

        return self.create_response(
            "success",
            "cancel_task",
            {
                "operation_id": operation_id,
                "status": progress.status,
                "message": progress.message
            }
        )

    async def list_operations_impl(
        self,
        status: Annotated[Optional[str], Field(description="Filter by status: running, completed, failed, cancelled")] = None,
        limit: Annotated[int, Field(description="Maximum number of results", ge=1, le=100)] = 20
    ) -> Dict[str, Any]:
        """
        List all tracked operations

        Args:
            status: Optional status filter
            limit: Maximum results (1-100)

        Returns:
            List of operations with their current status
        """
        from services.progress_service.progress_manager import OperationStatus

        # Convert status string to enum
        status_enum = None
        if status:
            try:
                status_enum = OperationStatus(status.lower())
            except ValueError:
                return self.create_response(
                    "error",
                    "list_operations",
                    {
                        "error": f"Invalid status: {status}",
                        "valid_statuses": [s.value for s in OperationStatus]
                    },
                    error_code="INVALID_STATUS"
                )

        operations = await self.progress_manager.list_operations(
            status=status_enum,
            limit=limit
        )

        return self.create_response(
            "success",
            "list_operations",
            {
                "operations": [
                    {
                        "operation_id": op.operation_id,
                        "status": op.status,
                        "progress": op.progress,
                        "message": op.message,
                        "started_at": op.started_at,
                        "updated_at": op.updated_at,
                        "metadata": op.metadata
                    }
                    for op in operations
                ],
                "count": len(operations),
                "filter_status": status
            }
        )

    # ========================================================================
    # Background Task Execution
    # ========================================================================

    async def _run_long_task(
        self,
        operation_id: str,
        task_type: str,
        duration_seconds: int,
        steps: int
    ):
        """
        Background task that simulates long-running work with progress updates

        Args:
            operation_id: Operation identifier
            task_type: Type of task
            duration_seconds: Total duration
            steps: Number of steps
        """
        try:
            delay_per_step = duration_seconds / steps

            for step in range(1, steps + 1):
                # Check if cancelled
                progress = await self.progress_manager.get_progress(operation_id)
                if progress and progress.status == "cancelled":
                    logger.info(f"Task {operation_id} was cancelled at step {step}")
                    return

                # Calculate progress
                progress_pct = (step / steps) * 100
                message = f"Processing step {step}/{steps} - {task_type}"

                # Update progress
                await self.progress_manager.update_progress(
                    operation_id,
                    progress=progress_pct,
                    current=step,
                    total=steps,
                    message=message,
                    metadata={"last_step_time": datetime.now().isoformat()}
                )

                logger.debug(f"Task {operation_id}: {progress_pct:.1f}% - {message}")

                # Simulate work
                await asyncio.sleep(delay_per_step)

            # Complete with result
            result = {
                "task_type": task_type,
                "duration_seconds": duration_seconds,
                "steps_completed": steps,
                "status": "success",
                "completed_at": datetime.now().isoformat(),
                "summary": f"Successfully completed {steps} steps of {task_type}"
            }

            await self.progress_manager.complete_operation(
                operation_id,
                result=result,
                message=f"Completed {steps} steps successfully"
            )

            logger.info(f"Task {operation_id} completed successfully")

        except Exception as e:
            logger.error(f"Task {operation_id} failed: {e}", exc_info=True)
            await self.progress_manager.fail_operation(
                operation_id,
                error=str(e),
                message="Task failed with error"
            )


# ============================================================================
# Auto-discovery Registration
# ============================================================================

def register_progress_example_tools(mcp):
    """
    Register progress tracking example tools

    IMPORTANT: Function name must match pattern: register_{filename}(mcp)
    For progress_example_tools.py, function must be: register_progress_example_tools(mcp)
    """
    tool = ProgressTools()
    tool.register_tools(mcp)
    logger.debug(f"✅ Progress tracking example tools registered successfully")
    return tool
