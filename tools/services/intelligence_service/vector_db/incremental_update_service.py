#!/usr/bin/env python3
"""
Incremental Update Service

Manages incremental updates and index freshness for the RAG vector database.
Provides efficient mechanisms to keep the knowledge base current without
full reindexing.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class UpdateStrategy(Enum):
    """Update strategy enumeration"""

    IMMEDIATE = "immediate"  # Update immediately on change
    BATCH = "batch"  # Batch updates periodically
    LAZY = "lazy"  # Update on next access
    SCHEDULED = "scheduled"  # Update on schedule


@dataclass
class UpdatePolicy:
    """Configuration for incremental updates"""

    strategy: UpdateStrategy = UpdateStrategy.BATCH
    batch_size: int = 100
    batch_interval_minutes: int = 5
    max_staleness_hours: int = 24
    enable_auto_reindex: bool = True
    reindex_threshold_changes: int = 1000
    enable_change_tracking: bool = True
    vacuum_interval_hours: int = 168  # 1 week


@dataclass
class ChangeRecord:
    """Record of a change to track for updates"""

    id: str
    user_id: str
    operation: str  # "insert", "update", "delete"
    timestamp: datetime
    table_name: str
    metadata: Optional[Dict[str, Any]] = None


class IncrementalUpdateService:
    """
    Service for managing incremental updates to vector databases.

    Features:
    - Change tracking and batching
    - Automatic index maintenance
    - Freshness monitoring
    - Efficient update strategies
    - Performance optimization
    """

    def __init__(self, policy: Optional[UpdatePolicy] = None):
        """
        Initialize incremental update service.

        Args:
            policy: Update policy configuration
        """
        self.policy = policy or UpdatePolicy()
        self.pending_changes: Dict[str, ChangeRecord] = {}
        self.last_batch_update = datetime.now()
        self.last_reindex = datetime.now()
        self.change_count = 0
        self.logger = logger

        # Start background tasks if enabled
        if self.policy.strategy == UpdateStrategy.BATCH:
            asyncio.create_task(self._batch_update_loop())

        if self.policy.strategy == UpdateStrategy.SCHEDULED:
            asyncio.create_task(self._scheduled_update_loop())

    async def record_change(
        self,
        id: str,
        user_id: str,
        operation: str,
        table_name: str = "user_knowledge",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record a change for future batch processing.

        Args:
            id: Record identifier
            user_id: User identifier
            operation: Type of operation ("insert", "update", "delete")
            table_name: Table name
            metadata: Additional metadata

        Returns:
            Success status
        """
        try:
            change_record = ChangeRecord(
                id=id,
                user_id=user_id,
                operation=operation,
                timestamp=datetime.now(),
                table_name=table_name,
                metadata=metadata,
            )

            # Use composite key to handle duplicate changes
            change_key = f"{table_name}:{user_id}:{id}"
            self.pending_changes[change_key] = change_record
            self.change_count += 1

            self.logger.debug(f"Recorded change: {operation} for {change_key}")

            # Handle immediate updates
            if self.policy.strategy == UpdateStrategy.IMMEDIATE:
                await self._process_single_change(change_record)

            # Check if we need automatic reindexing
            if (
                self.policy.enable_auto_reindex
                and self.change_count >= self.policy.reindex_threshold_changes
            ):
                await self._trigger_reindex()

            return True

        except Exception as e:
            self.logger.error(f"Error recording change: {e}")
            return False

    async def process_pending_changes(self, force: bool = False) -> Dict[str, Any]:
        """
        Process all pending changes.

        Args:
            force: Force processing even if batch interval hasn't elapsed

        Returns:
            Processing result
        """
        try:
            current_time = datetime.now()
            time_since_last = (current_time - self.last_batch_update).total_seconds() / 60

            # Check if we should process based on policy
            should_process = (
                force
                or len(self.pending_changes) >= self.policy.batch_size
                or time_since_last >= self.policy.batch_interval_minutes
            )

            if not should_process:
                return {
                    "processed": False,
                    "reason": "batch_criteria_not_met",
                    "pending_count": len(self.pending_changes),
                    "time_since_last": time_since_last,
                }

            if not self.pending_changes:
                return {"processed": True, "changes_processed": 0, "message": "no_pending_changes"}

            # Group changes by operation and user for efficient processing
            grouped_changes = self._group_changes_for_processing()

            # Process changes
            results = {}
            total_processed = 0

            for group_key, changes in grouped_changes.items():
                try:
                    group_result = await self._process_change_group(group_key, changes)
                    results[group_key] = group_result
                    total_processed += len(changes)

                except Exception as e:
                    self.logger.error(f"Error processing change group {group_key}: {e}")
                    results[group_key] = {"success": False, "error": str(e)}

            # Clear processed changes
            self.pending_changes.clear()
            self.last_batch_update = current_time

            self.logger.info(
                f"Processed {total_processed} changes in {len(grouped_changes)} groups"
            )

            return {
                "processed": True,
                "changes_processed": total_processed,
                "groups_processed": len(grouped_changes),
                "results": results,
                "processing_time": datetime.now(),
            }

        except Exception as e:
            self.logger.error(f"Error processing pending changes: {e}")
            return {"processed": False, "error": str(e)}

    def _group_changes_for_processing(self) -> Dict[str, List[ChangeRecord]]:
        """Group changes for efficient batch processing."""
        groups = {}

        for change in self.pending_changes.values():
            # Group by table, user, and operation
            group_key = f"{change.table_name}:{change.user_id}:{change.operation}"

            if group_key not in groups:
                groups[group_key] = []

            groups[group_key].append(change)

        return groups

    async def _process_change_group(
        self, group_key: str, changes: List[ChangeRecord]
    ) -> Dict[str, Any]:
        """Process a group of similar changes efficiently."""
        try:
            table_name, user_id, operation = group_key.split(":", 2)

            if operation == "insert":
                return await self._process_inserts(table_name, user_id, changes)
            elif operation == "update":
                return await self._process_updates(table_name, user_id, changes)
            elif operation == "delete":
                return await self._process_deletes(table_name, user_id, changes)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

        except Exception as e:
            self.logger.error(f"Error processing change group {group_key}: {e}")
            return {"success": False, "error": str(e)}

    async def _process_inserts(
        self, table_name: str, user_id: str, changes: List[ChangeRecord]
    ) -> Dict[str, Any]:
        """Process insert operations."""
        try:
            # For inserts, we typically don't need to do anything extra
            # as the new records are already in the database with indexes

            insert_ids = [change.id for change in changes]

            # Could trigger index optimization if needed
            if len(insert_ids) > self.policy.batch_size:
                await self._optimize_indexes(table_name, user_id)

            return {
                "success": True,
                "operation": "insert",
                "processed_count": len(changes),
                "ids": insert_ids,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _process_updates(
        self, table_name: str, user_id: str, changes: List[ChangeRecord]
    ) -> Dict[str, Any]:
        """Process update operations."""
        try:
            # For updates, we may need to refresh any cached embeddings or indexes
            update_ids = [change.id for change in changes]

            # Update timestamp tracking
            await self._update_freshness_tracking(table_name, user_id, update_ids)

            return {
                "success": True,
                "operation": "update",
                "processed_count": len(changes),
                "ids": update_ids,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _process_deletes(
        self, table_name: str, user_id: str, changes: List[ChangeRecord]
    ) -> Dict[str, Any]:
        """Process delete operations."""
        try:
            # For deletes, we may need to clean up indexes or vacuum
            delete_ids = [change.id for change in changes]

            # Schedule vacuum if many deletes
            if len(delete_ids) > self.policy.batch_size // 2:
                await self._schedule_vacuum(table_name)

            return {
                "success": True,
                "operation": "delete",
                "processed_count": len(changes),
                "ids": delete_ids,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _process_single_change(self, change: ChangeRecord) -> bool:
        """Process a single change immediately."""
        try:
            # For immediate processing, we typically just log or trigger notifications
            self.logger.debug(f"Immediate processing: {change.operation} on {change.id}")

            # Could trigger real-time index updates here
            return True

        except Exception as e:
            self.logger.error(f"Error in immediate processing: {e}")
            return False

    async def _trigger_reindex(self) -> bool:
        """Trigger a full reindex operation."""
        try:
            self.logger.info(f"Triggering reindex after {self.change_count} changes")

            # Reset change count
            self.change_count = 0
            self.last_reindex = datetime.now()

            # In a full implementation, this would trigger database reindexing
            # For now, we just log the event

            return True

        except Exception as e:
            self.logger.error(f"Error triggering reindex: {e}")
            return False

    async def _optimize_indexes(self, table_name: str, user_id: str) -> bool:
        """Optimize indexes for a specific table/user."""
        try:
            self.logger.debug(f"Optimizing indexes for {table_name}:{user_id}")

            # In a full implementation, this would run VACUUM, ANALYZE, etc.
            return True

        except Exception as e:
            self.logger.error(f"Error optimizing indexes: {e}")
            return False

    async def _update_freshness_tracking(
        self, table_name: str, user_id: str, ids: List[str]
    ) -> bool:
        """Update freshness tracking for modified records."""
        try:
            # Track when records were last updated for freshness queries
            self.logger.debug(f"Updating freshness tracking for {len(ids)} records")
            return True

        except Exception as e:
            self.logger.error(f"Error updating freshness tracking: {e}")
            return False

    async def _schedule_vacuum(self, table_name: str) -> bool:
        """Schedule a vacuum operation for the table."""
        try:
            self.logger.info(f"Scheduling vacuum for {table_name}")

            # In a full implementation, this would schedule actual VACUUM operations
            return True

        except Exception as e:
            self.logger.error(f"Error scheduling vacuum: {e}")
            return False

    async def _batch_update_loop(self):
        """Background loop for batch updates."""
        while True:
            try:
                await asyncio.sleep(self.policy.batch_interval_minutes * 60)
                await self.process_pending_changes()

            except Exception as e:
                self.logger.error(f"Error in batch update loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _scheduled_update_loop(self):
        """Background loop for scheduled updates."""
        while True:
            try:
                # Wait until next scheduled time (simplified to daily)
                await asyncio.sleep(24 * 60 * 60)
                await self.process_pending_changes(force=True)

            except Exception as e:
                self.logger.error(f"Error in scheduled update loop: {e}")
                await asyncio.sleep(60 * 60)  # Wait an hour before retrying

    async def get_freshness_status(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get freshness status of the knowledge base.

        Args:
            user_id: Optional user filter

        Returns:
            Freshness status information
        """
        try:
            current_time = datetime.now()

            status = {
                "current_time": current_time,
                "last_batch_update": self.last_batch_update,
                "last_reindex": self.last_reindex,
                "pending_changes": len(self.pending_changes),
                "total_changes_since_reindex": self.change_count,
                "update_strategy": self.policy.strategy.value,
                "batch_interval_minutes": self.policy.batch_interval_minutes,
                "max_staleness_hours": self.policy.max_staleness_hours,
            }

            # Calculate staleness
            time_since_update = current_time - self.last_batch_update
            staleness_hours = time_since_update.total_seconds() / 3600

            status["staleness_hours"] = staleness_hours
            status["is_stale"] = staleness_hours > self.policy.max_staleness_hours

            # Time until next update
            if self.policy.strategy == UpdateStrategy.BATCH:
                time_since_last = (current_time - self.last_batch_update).total_seconds() / 60
                next_update_minutes = max(0, self.policy.batch_interval_minutes - time_since_last)
                status["next_update_minutes"] = next_update_minutes

            # User-specific information if requested
            if user_id:
                user_changes = [
                    change for change in self.pending_changes.values() if change.user_id == user_id
                ]
                status["user_pending_changes"] = len(user_changes)

            return status

        except Exception as e:
            self.logger.error(f"Error getting freshness status: {e}")
            return {"error": str(e)}

    async def force_refresh(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Force an immediate refresh of the knowledge base.

        Args:
            user_id: Optional user filter for targeted refresh

        Returns:
            Refresh result
        """
        try:
            self.logger.info(f"Force refresh requested for user: {user_id or 'all'}")

            # Process pending changes
            result = await self.process_pending_changes(force=True)

            # Trigger reindex if needed
            if self.change_count > 0:
                await self._trigger_reindex()

            result["forced"] = True
            result["refresh_time"] = datetime.now()

            return result

        except Exception as e:
            self.logger.error(f"Error in force refresh: {e}")
            return {"success": False, "error": str(e)}


# Global instance
incremental_update_service = IncrementalUpdateService()


# Convenience functions
async def record_knowledge_change(
    id: str, user_id: str, operation: str, metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Convenience function to record knowledge changes."""
    return await incremental_update_service.record_change(
        id=id, user_id=user_id, operation=operation, table_name="user_knowledge", metadata=metadata
    )


async def get_knowledge_freshness(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to get knowledge freshness status."""
    return await incremental_update_service.get_freshness_status(user_id)


async def refresh_knowledge_base(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to refresh knowledge base."""
    return await incremental_update_service.force_refresh(user_id)
