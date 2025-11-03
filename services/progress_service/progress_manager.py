#!/usr/bin/env python3
"""
Progress Manager - Track progress for long-running operations

Uses isa_common RedisClient (gRPC) for storage
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

from core.config import get_settings
from core.logging import get_logger

# Import isa_common RedisClient
try:
    from isa_common.redis_client import RedisClient
    REDIS_CLIENT_AVAILABLE = True
except ImportError:
    REDIS_CLIENT_AVAILABLE = False
    RedisClient = None

logger = get_logger(__name__)


class OperationStatus(str, Enum):
    """Operation status enum"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressData:
    """Progress data structure"""
    operation_id: str
    status: OperationStatus
    progress: float  # 0-100
    total: Optional[int] = None
    current: Optional[int] = None
    message: str = ""
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['status'] = self.status.value if isinstance(self.status, OperationStatus) else self.status
        return data


class ProgressManager:
    """
    Manage progress for long-running operations using isa_common RedisClient

    Features:
    - Store and retrieve operation progress
    - Update progress in real-time
    - Support cancellation
    - Automatic expiry (1 hour default)
    """

    def __init__(self, expiry_seconds: int = 3600):
        """
        Initialize progress manager

        Args:
            expiry_seconds: How long to keep progress data (default: 1 hour)
        """
        self.expiry_seconds = expiry_seconds

        # Get Redis config from settings
        settings = get_settings()
        infra = settings.infrastructure

        self.redis_host = infra.redis_grpc_host
        self.redis_port = infra.redis_grpc_port

        # Initialize RedisClient
        if REDIS_CLIENT_AVAILABLE:
            self.redis = RedisClient(
                host=self.redis_host,
                port=self.redis_port,
                user_id='progress-manager'
            )
            logger.info(f"ProgressManager initialized with RedisClient at {self.redis_host}:{self.redis_port}")
        else:
            # Use in-memory fallback
            self.redis = None
            self._memory_store = {}
            logger.warning("Using in-memory storage (Redis not available)")

    async def start_operation(
        self,
        operation_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProgressData:
        """
        Start tracking a new operation

        Args:
            operation_id: Unique operation identifier
            metadata: Optional metadata to store

        Returns:
            ProgressData object
        """
        progress = ProgressData(
            operation_id=operation_id,
            status=OperationStatus.RUNNING,
            progress=0.0,
            message="Starting...",
            started_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            metadata=metadata or {}
        )

        await self._save_progress(progress)
        logger.info(f"Started tracking operation: {operation_id}")
        return progress

    async def update_progress(
        self,
        operation_id: str,
        progress: float,
        current: Optional[int] = None,
        total: Optional[int] = None,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ProgressData]:
        """
        Update operation progress

        Args:
            operation_id: Operation identifier
            progress: Progress percentage (0-100)
            current: Current step number
            total: Total steps
            message: Progress message
            metadata: Additional metadata to merge

        Returns:
            Updated ProgressData or None if not found
        """
        existing = await self.get_progress(operation_id)
        if not existing:
            logger.warning(f"Operation {operation_id} not found")
            return None

        # Check if cancelled
        if existing.status == OperationStatus.CANCELLED:
            logger.info(f"Operation {operation_id} was cancelled, skipping update")
            return existing

        # Update fields
        existing.progress = min(100.0, max(0.0, progress))
        existing.current = current
        existing.total = total
        existing.message = message or existing.message
        existing.updated_at = datetime.now().isoformat()

        # Merge metadata
        if metadata:
            if existing.metadata is None:
                existing.metadata = {}
            existing.metadata.update(metadata)

        await self._save_progress(existing)
        logger.debug(f"Updated progress for {operation_id}: {progress}%")
        return existing

    async def complete_operation(
        self,
        operation_id: str,
        result: Optional[Dict[str, Any]] = None,
        message: str = "Completed"
    ) -> Optional[ProgressData]:
        """
        Mark operation as completed

        Args:
            operation_id: Operation identifier
            result: Final result data
            message: Completion message

        Returns:
            Updated ProgressData or None if not found
        """
        existing = await self.get_progress(operation_id)
        if not existing:
            return None

        existing.status = OperationStatus.COMPLETED
        existing.progress = 100.0
        existing.message = message
        existing.completed_at = datetime.now().isoformat()
        existing.updated_at = datetime.now().isoformat()

        await self._save_progress(existing)

        # Store result separately (might be large)
        if result:
            await self._save_result(operation_id, result)

        logger.info(f"Completed operation: {operation_id}")
        return existing

    async def fail_operation(
        self,
        operation_id: str,
        error: str,
        message: str = "Failed"
    ) -> Optional[ProgressData]:
        """
        Mark operation as failed

        Args:
            operation_id: Operation identifier
            error: Error message
            message: Failure message

        Returns:
            Updated ProgressData or None if not found
        """
        existing = await self.get_progress(operation_id)
        if not existing:
            return None

        existing.status = OperationStatus.FAILED
        existing.error = error
        existing.message = message
        existing.completed_at = datetime.now().isoformat()
        existing.updated_at = datetime.now().isoformat()

        await self._save_progress(existing)
        logger.error(f"Failed operation {operation_id}: {error}")
        return existing

    async def cancel_operation(self, operation_id: str) -> Optional[ProgressData]:
        """
        Cancel a running operation

        Args:
            operation_id: Operation identifier

        Returns:
            Updated ProgressData or None if not found
        """
        existing = await self.get_progress(operation_id)
        if not existing:
            return None

        if existing.status in [OperationStatus.COMPLETED, OperationStatus.FAILED]:
            logger.warning(f"Cannot cancel {existing.status.value} operation: {operation_id}")
            return existing

        existing.status = OperationStatus.CANCELLED
        existing.message = "Cancelled by user"
        existing.completed_at = datetime.now().isoformat()
        existing.updated_at = datetime.now().isoformat()

        await self._save_progress(existing)
        logger.info(f"Cancelled operation: {operation_id}")
        return existing

    async def get_progress(self, operation_id: str) -> Optional[ProgressData]:
        """
        Get current operation progress

        Args:
            operation_id: Operation identifier

        Returns:
            ProgressData or None if not found
        """
        key = f"progress:{operation_id}"

        try:
            if self.redis:
                # Use RedisClient (sync call in async context)
                with self.redis:
                    data = self.redis.get(key)
            else:
                # Use in-memory fallback
                data = self._memory_store.get(key)
                if data:
                    data = json.dumps(data)

            if data:
                parsed = json.loads(data)
                return ProgressData(**parsed)
            return None

        except Exception as e:
            logger.error(f"Error getting progress for {operation_id}: {e}")
            return None

    async def get_result(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get operation result

        Args:
            operation_id: Operation identifier

        Returns:
            Result data or None if not found
        """
        key = f"result:{operation_id}"

        try:
            if self.redis:
                with self.redis:
                    data = self.redis.get(key)
            else:
                # In-memory fallback
                return self._memory_store.get(key)

            if data:
                return json.loads(data)
            return None

        except Exception as e:
            logger.error(f"Error getting result for {operation_id}: {e}")
            return None

    async def list_operations(
        self,
        status: Optional[OperationStatus] = None,
        limit: int = 100
    ) -> List[ProgressData]:
        """
        List all tracked operations

        Args:
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of ProgressData
        """
        try:
            if self.redis:
                with self.redis:
                    keys = self.redis.list_keys("progress:*", limit=limit * 2)
            else:
                # In-memory fallback
                keys = [k for k in self._memory_store.keys() if k.startswith("progress:")]

            operations = []
            for key in keys[:limit * 2]:  # Get more keys in case we need to filter
                op_id = key.replace("progress:", "")
                progress = await self.get_progress(op_id)
                if progress:
                    if status is None or progress.status == status:
                        operations.append(progress)
                        if len(operations) >= limit:
                            break

            return sorted(operations, key=lambda x: x.updated_at or "", reverse=True)

        except Exception as e:
            logger.error(f"Error listing operations: {e}")
            return []

    async def cleanup_old_operations(self, older_than_hours: int = 24) -> int:
        """
        Clean up operations older than specified hours

        Args:
            older_than_hours: Delete operations older than this

        Returns:
            Number of deleted operations
        """
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        cutoff_str = cutoff.isoformat()

        operations = await self.list_operations()
        deleted = 0

        for op in operations:
            if op.updated_at and op.updated_at < cutoff_str:
                try:
                    if self.redis:
                        with self.redis:
                            self.redis.delete_multiple([
                                f"progress:{op.operation_id}",
                                f"result:{op.operation_id}"
                            ])
                    else:
                        # In-memory fallback
                        self._memory_store.pop(f"progress:{op.operation_id}", None)
                        self._memory_store.pop(f"result:{op.operation_id}", None)
                    deleted += 1
                except Exception as e:
                    logger.error(f"Error deleting {op.operation_id}: {e}")

        logger.info(f"Cleaned up {deleted} old operations")
        return deleted

    # Private methods

    async def _save_progress(self, progress: ProgressData):
        """Save progress data to Redis"""
        key = f"progress:{progress.operation_id}"
        data = json.dumps(progress.to_dict())

        try:
            if self.redis:
                # Use RedisClient with TTL
                with self.redis:
                    self.redis.set_with_ttl(key, data, self.expiry_seconds)
            else:
                # Use in-memory fallback
                self._memory_store[key] = json.loads(data)
        except Exception as e:
            logger.error(f"Error saving progress: {e}")
            raise

    async def _save_result(self, operation_id: str, result: Dict[str, Any]):
        """Save result data to Redis"""
        key = f"result:{operation_id}"
        data = json.dumps(result)

        try:
            if self.redis:
                # Use RedisClient with TTL
                with self.redis:
                    self.redis.set_with_ttl(key, data, self.expiry_seconds)
            else:
                # Use in-memory fallback
                self._memory_store[key] = result
        except Exception as e:
            logger.error(f"Error saving result: {e}")
            raise

    async def close(self):
        """Close connections"""
        if self.redis:
            self.redis.close()
        logger.info("ProgressManager closed")
