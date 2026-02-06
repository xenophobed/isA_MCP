#!/usr/bin/env python3
"""
Plan State Management System
Provides abstraction layer for storing and retrieving execution plans
Supports multiple backends: In-Memory, Redis, etc.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
from core.logging import get_logger

logger = get_logger(__name__)


class PlanStateManager(ABC):
    """Abstract base class for plan state storage"""

    @abstractmethod
    def save_plan(self, plan_id: str, plan_data: Dict[str, Any]) -> bool:
        """Save complete plan state"""
        pass

    @abstractmethod
    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve plan by ID"""
        pass

    @abstractmethod
    def update_task_status(self, plan_id: str, task_id: int, status: str,
                          result: Optional[Dict[str, Any]] = None) -> bool:
        """Update status of a specific task"""
        pass

    @abstractmethod
    def add_execution_event(self, plan_id: str, event: Dict[str, Any]) -> bool:
        """Add execution event to history"""
        pass

    @abstractmethod
    def get_execution_history(self, plan_id: str) -> List[Dict[str, Any]]:
        """Get execution history for a plan"""
        pass

    @abstractmethod
    def create_branch(self, parent_plan_id: str, branch_id: str,
                     branch_data: Dict[str, Any]) -> bool:
        """Create a branch from existing plan"""
        pass

    @abstractmethod
    def get_branches(self, plan_id: str) -> List[Dict[str, Any]]:
        """Get all branches of a plan"""
        pass

    @abstractmethod
    def list_active_plans(self) -> List[str]:
        """List all active plan IDs"""
        pass

    @abstractmethod
    def delete_plan(self, plan_id: str) -> bool:
        """Delete a plan and its history"""
        pass


class InMemoryStateStore(PlanStateManager):
    """In-memory implementation of plan state storage (fallback/dev mode)"""

    def __init__(self):
        self.plans: Dict[str, Dict[str, Any]] = {}
        self.execution_history: Dict[str, List[Dict[str, Any]]] = {}
        self.branches: Dict[str, List[Dict[str, Any]]] = {}
        logger.debug("InMemoryStateStore initialized (no persistence)")

    def save_plan(self, plan_id: str, plan_data: Dict[str, Any]) -> bool:
        """Save plan to memory"""
        try:
            plan_data['plan_id'] = plan_id
            plan_data['last_updated'] = datetime.utcnow().isoformat()
            self.plans[plan_id] = plan_data

            # Initialize history if not exists
            if plan_id not in self.execution_history:
                self.execution_history[plan_id] = []

            # Add creation event
            self.add_execution_event(plan_id, {
                'event_type': 'plan_created',
                'timestamp': datetime.utcnow().isoformat(),
                'data': {'total_tasks': plan_data.get('total_tasks', 0)}
            })

            logger.info(f"✅ Plan saved to memory: {plan_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save plan {plan_id}: {e}")
            return False

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve plan from memory"""
        plan = self.plans.get(plan_id)
        if plan:
            logger.debug(f"Retrieved plan from memory: {plan_id}")
        else:
            logger.warning(f"Plan not found in memory: {plan_id}")
        return plan

    def update_task_status(self, plan_id: str, task_id: int, status: str,
                          result: Optional[Dict[str, Any]] = None) -> bool:
        """Update task status in memory"""
        try:
            plan = self.plans.get(plan_id)
            if not plan:
                logger.error(f"Plan not found: {plan_id}")
                return False

            # Find and update task
            tasks = plan.get('tasks', [])
            for task in tasks:
                if task.get('id') == task_id:
                    task['status'] = status
                    task['last_updated'] = datetime.utcnow().isoformat()
                    if result:
                        task['result'] = result
                    break

            # Update plan timestamp
            plan['last_updated'] = datetime.utcnow().isoformat()

            # Add event
            self.add_execution_event(plan_id, {
                'event_type': 'task_status_updated',
                'timestamp': datetime.utcnow().isoformat(),
                'data': {
                    'task_id': task_id,
                    'status': status,
                    'result': result
                }
            })

            logger.info(f"✅ Task {task_id} status updated to '{status}' in plan {plan_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            return False

    def add_execution_event(self, plan_id: str, event: Dict[str, Any]) -> bool:
        """Add execution event to history"""
        try:
            if plan_id not in self.execution_history:
                self.execution_history[plan_id] = []

            event['event_id'] = str(uuid.uuid4())
            event['timestamp'] = event.get('timestamp', datetime.utcnow().isoformat())
            self.execution_history[plan_id].append(event)
            return True
        except Exception as e:
            logger.error(f"Failed to add execution event: {e}")
            return False

    def get_execution_history(self, plan_id: str) -> List[Dict[str, Any]]:
        """Get execution history from memory"""
        return self.execution_history.get(plan_id, [])

    def create_branch(self, parent_plan_id: str, branch_id: str,
                     branch_data: Dict[str, Any]) -> bool:
        """Create branch in memory"""
        try:
            if parent_plan_id not in self.branches:
                self.branches[parent_plan_id] = []

            branch_data['branch_id'] = branch_id
            branch_data['parent_plan_id'] = parent_plan_id
            branch_data['created_at'] = datetime.utcnow().isoformat()

            self.branches[parent_plan_id].append(branch_data)

            # Add event to parent plan
            self.add_execution_event(parent_plan_id, {
                'event_type': 'branch_created',
                'timestamp': datetime.utcnow().isoformat(),
                'data': {
                    'branch_id': branch_id,
                    'branch_from_task': branch_data.get('branch_from_task')
                }
            })

            logger.info(f"✅ Branch {branch_id} created from plan {parent_plan_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create branch: {e}")
            return False

    def get_branches(self, plan_id: str) -> List[Dict[str, Any]]:
        """Get branches from memory"""
        return self.branches.get(plan_id, [])

    def list_active_plans(self) -> List[str]:
        """List all plan IDs in memory"""
        return list(self.plans.keys())

    def delete_plan(self, plan_id: str) -> bool:
        """Delete plan from memory"""
        try:
            if plan_id in self.plans:
                del self.plans[plan_id]
            if plan_id in self.execution_history:
                del self.execution_history[plan_id]
            if plan_id in self.branches:
                del self.branches[plan_id]

            logger.info(f"✅ Plan {plan_id} deleted from memory")
            return True
        except Exception as e:
            logger.error(f"Failed to delete plan: {e}")
            return False


class RedisStateStore(PlanStateManager):
    """Redis-backed implementation using native redis-py"""

    def __init__(self, redis_host: str = None, redis_port: int = None, user_id: str = "mcp-planner"):
        """
        Initialize Redis state store

        Args:
            redis_host: Redis service host (default from env or localhost)
            redis_port: Redis native port (default from env or 6379)
            user_id: User ID for Redis operations (used as key prefix)
        """
        try:
            import redis

            host = redis_host or os.getenv("REDIS_HOST", "localhost")
            port = redis_port or int(os.getenv("REDIS_PORT", "6379"))

            self.redis = redis.Redis(host=host, port=port, decode_responses=True)
            self.user_id = user_id

            # Test connection
            self.redis.ping()
            logger.info(f"✅ RedisStateStore connected to Redis at {host}:{port}")

        except Exception as e:
            logger.debug(f"Failed to initialize RedisStateStore: {e}")
            raise

    def _plan_key(self, plan_id: str) -> str:
        """Generate Redis key for plan"""
        return f"plan:{plan_id}"

    def _history_key(self, plan_id: str) -> str:
        """Generate Redis key for execution history"""
        return f"plan:history:{plan_id}"

    def _branch_key(self, plan_id: str) -> str:
        """Generate Redis key for branches"""
        return f"plan:branches:{plan_id}"

    def save_plan(self, plan_id: str, plan_data: Dict[str, Any]) -> bool:
        """Save plan to Redis"""
        try:
            plan_data['plan_id'] = plan_id
            plan_data['last_updated'] = datetime.utcnow().isoformat()

            # Save as JSON string with 24h TTL
            plan_json = json.dumps(plan_data, ensure_ascii=False)
            result = self.redis.set(self._plan_key(plan_id), plan_json, ex=86400)

            if result:
                # Add creation event
                self.add_execution_event(plan_id, {
                    'event_type': 'plan_created',
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': {'total_tasks': plan_data.get('total_tasks', 0)}
                })
                logger.info(f"✅ Plan saved to Redis: {plan_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save plan to Redis: {e}")
            return False

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve plan from Redis"""
        try:
            plan_json = self.redis.get(self._plan_key(plan_id))
            if plan_json:
                plan = json.loads(plan_json)
                logger.debug(f"Retrieved plan from Redis: {plan_id}")
                return plan
            logger.warning(f"Plan not found in Redis: {plan_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get plan from Redis: {e}")
            return None

    def update_task_status(self, plan_id: str, task_id: int, status: str,
                          result: Optional[Dict[str, Any]] = None) -> bool:
        """Update task status in Redis"""
        try:
            plan = self.get_plan(plan_id)
            if not plan:
                logger.error(f"Plan not found: {plan_id}")
                return False

            # Find and update task
            tasks = plan.get('tasks', [])
            for task in tasks:
                if task.get('id') == task_id:
                    task['status'] = status
                    task['last_updated'] = datetime.utcnow().isoformat()
                    if result:
                        task['result'] = result
                    break

            # Update plan timestamp
            plan['last_updated'] = datetime.utcnow().isoformat()

            # Save updated plan
            self.save_plan(plan_id, plan)

            # Add event
            self.add_execution_event(plan_id, {
                'event_type': 'task_status_updated',
                'timestamp': datetime.utcnow().isoformat(),
                'data': {
                    'task_id': task_id,
                    'status': status,
                    'result': result
                }
            })

            logger.info(f"✅ Task {task_id} status updated to '{status}' in Redis plan {plan_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update task status in Redis: {e}")
            return False

    def add_execution_event(self, plan_id: str, event: Dict[str, Any]) -> bool:
        """Add execution event to Redis list"""
        try:
            event['event_id'] = str(uuid.uuid4())
            event['timestamp'] = event.get('timestamp', datetime.utcnow().isoformat())
            event_json = json.dumps(event, ensure_ascii=False)

            # Use Redis RPUSH to append to list
            result = self.redis.rpush(self._history_key(plan_id), event_json)

            # Set TTL on history list
            self.redis.expire(self._history_key(plan_id), 86400)  # 24h

            return result is not None
        except Exception as e:
            logger.error(f"Failed to add execution event to Redis: {e}")
            return False

    def get_execution_history(self, plan_id: str) -> List[Dict[str, Any]]:
        """Get execution history from Redis"""
        try:
            # Get all events from Redis list
            events_json = self.redis.lrange(self._history_key(plan_id), 0, -1)
            if not events_json:
                return []

            events = [json.loads(e) for e in events_json]
            return events
        except Exception as e:
            logger.error(f"Failed to get execution history from Redis: {e}")
            return []

    def create_branch(self, parent_plan_id: str, branch_id: str,
                     branch_data: Dict[str, Any]) -> bool:
        """Create branch in Redis"""
        try:
            branch_data['branch_id'] = branch_id
            branch_data['parent_plan_id'] = parent_plan_id
            branch_data['created_at'] = datetime.utcnow().isoformat()

            branch_json = json.dumps(branch_data, ensure_ascii=False)

            # Add to branch list
            result = self.redis.rpush(self._branch_key(parent_plan_id), branch_json)

            # Set TTL
            self.redis.expire(self._branch_key(parent_plan_id), 86400)  # 24h

            if result:
                # Add event to parent plan
                self.add_execution_event(parent_plan_id, {
                    'event_type': 'branch_created',
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': {
                        'branch_id': branch_id,
                        'branch_from_task': branch_data.get('branch_from_task')
                    }
                })
                logger.info(f"✅ Branch {branch_id} created in Redis from plan {parent_plan_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to create branch in Redis: {e}")
            return False

    def get_branches(self, plan_id: str) -> List[Dict[str, Any]]:
        """Get branches from Redis"""
        try:
            branches_json = self.redis.lrange(self._branch_key(plan_id), 0, -1)
            if not branches_json:
                return []

            branches = [json.loads(b) for b in branches_json]
            return branches
        except Exception as e:
            logger.error(f"Failed to get branches from Redis: {e}")
            return []

    def list_active_plans(self) -> List[str]:
        """List all active plan IDs in Redis"""
        try:
            # Use Redis KEYS to find all plan keys
            plan_keys = self.redis.keys("plan:*")
            if not plan_keys:
                return []

            # Extract plan IDs from keys
            plan_ids = []
            for key in plan_keys:
                if key.startswith("plan:") and not ("history:" in key or "branches:" in key):
                    plan_id = key.replace("plan:", "")
                    plan_ids.append(plan_id)

            return plan_ids
        except Exception as e:
            logger.error(f"Failed to list active plans from Redis: {e}")
            return []

    def delete_plan(self, plan_id: str) -> bool:
        """Delete plan from Redis"""
        try:
            # Delete plan, history, and branches
            self.redis.delete(self._plan_key(plan_id))
            self.redis.delete(self._history_key(plan_id))
            self.redis.delete(self._branch_key(plan_id))

            logger.info(f"✅ Plan {plan_id} deleted from Redis")
            return True
        except Exception as e:
            logger.error(f"Failed to delete plan from Redis: {e}")
            return False

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        try:
            self.redis.close()
        except:
            pass


def create_state_manager(prefer_redis: bool = True, **kwargs) -> PlanStateManager:
    """
    Factory function to create appropriate state manager

    Args:
        prefer_redis: Try to use Redis if available (default: True)
        **kwargs: Additional arguments for Redis connection

    Returns:
        PlanStateManager instance (Redis or InMemory fallback)
    """
    if prefer_redis:
        try:
            # Try to create Redis store
            redis_store = RedisStateStore(**kwargs)
            logger.debug("Using RedisStateStore for plan persistence")
            return redis_store
        except Exception as e:
            logger.debug(f"Redis unavailable, falling back to InMemory: {e}")

    # Fallback to in-memory
    logger.debug("Using InMemoryStateStore (no persistence)")
    return InMemoryStateStore()
