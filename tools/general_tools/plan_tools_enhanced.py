#!/usr/bin/env python3
"""
Enhanced Autonomous Planning and Execution Tools
Intelligent task planning with state management, branching, and dynamic adjustment

Inspired by MCP Sequential Thinking patterns:
- Execution history tracking with full lineage
- Plan branching and revision support
- Dynamic plan adjustment during execution
- Rich visual feedback with status indicators
- Hypothesis generation and verification
"""

import json
import re
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.services.intelligence_service.language.text_generator import generate
from tools.general_tools.plan_state_manager import create_state_manager, PlanStateManager
from core.logging import get_logger

logger = get_logger(__name__)


class EnhancedAutonomousPlanner(BaseTool):
    """
    Enhanced intelligent planning tool with state management and dynamic adjustment

    Features:
    - Full execution history tracking
    - Plan branching and revision
    - Dynamic plan adjustment
    - Real-time status monitoring
    - Hypothesis-driven planning
    """

    def __init__(self, state_manager: Optional[PlanStateManager] = None):
        super().__init__()
        self.state_manager = state_manager or create_state_manager(prefer_redis=True)
        self.current_plan_id: Optional[str] = None

    def _validate_plan_data(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate plan structure"""
        required_fields = ["execution_mode", "tasks"]
        for field in required_fields:
            if field not in plan_data:
                raise ValueError(f"Missing required field: {field}")

        if not isinstance(plan_data["tasks"], list):
            raise ValueError("tasks must be a list")

        for task in plan_data["tasks"]:
            required_task_fields = ["id", "title", "description", "tools"]
            for field in required_task_fields:
                if field not in task:
                    raise ValueError(f"Task {task.get('id', '?')} missing field: {field}")

        return plan_data

    def _format_task_status(self, task: Dict[str, Any], status: str = None) -> str:
        """Format task with visual indicators"""
        emojis = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "failed": "❌",
            "blocked": "🚫",
            "revision": "🔄",
            "branch": "🌿"
        }

        task_status = status or task.get("status", "pending")
        task_type = "revision" if task.get("is_revision") else \
                    "branch" if task.get("branch_from_task_id") else \
                    task_status

        emoji = emojis.get(task_type, "📌")

        output = f"{emoji} Task {task['id']}"
        if task.get("total_tasks"):
            output += f"/{task['total_tasks']}"
        output += f" - {task['title']}"

        if task.get("is_revision"):
            output += f" (revising task {task.get('revises_task_id')})"
        elif task.get("branch_from_task_id"):
            output += f" (branch from task {task.get('branch_from_task_id')})"

        return output

    def _create_planning_prompt(self, guidance: str, available_tools: List[str], request: str) -> str:
        """Create enhanced planning prompt with hypothesis-driven approach"""
        tool_list = "\n".join([f"- {tool}" for tool in available_tools])

        return f"""
        You are an intelligent task planner with hypothesis-driven problem solving capabilities.
        Create an execution plan based on the following:

        GUIDANCE: {guidance}
        REQUEST: {request}

        AVAILABLE_TOOLS:
        {tool_list}

        Your planning should include:
        1. Initial hypothesis about the solution approach
        2. Verification steps to test the hypothesis
        3. Flexibility to revise if hypothesis proves incorrect
        4. Ability to branch into alternative approaches

        Analyze the request and guidance to determine:
        1. The best execution mode for this type of task
        2. The optimal number of tasks needed
        3. The most logical task breakdown and dependencies
        4. Potential risks and alternative approaches

        Create a detailed execution plan with the following structure:
        {{
            "solution_hypothesis": "Your initial assumption about how to solve this",
            "verification_strategy": "How you'll validate the approach is working",
            "execution_mode": "sequential|parallel|fan_out|pipeline",
            "max_tasks_reasoning": "Brief explanation of why this number of tasks is optimal",
            "alternative_approaches": ["List of alternative approaches if main hypothesis fails"],
            "tasks": [
                {{
                    "id": 1,
                    "title": "Task Title",
                    "description": "Detailed description",
                    "tools": ["tool1", "tool2"],
                    "execution_type": "sequential|parallel|fan_out|pipeline",
                    "dependencies": ["task_id_list"],
                    "expected_output": "What this task should produce",
                    "verification_criteria": "How to verify this task succeeded",
                    "priority": "high|medium|low",
                    "status": "pending",
                    "is_revision": false,
                    "revises_task_id": null,
                    "branch_from_task_id": null,
                    "branch_id": null
                }}
            ]
        }}

        EXECUTION MODES - Choose the most appropriate:
        - sequential: Tasks have clear dependencies and must run in order
        - parallel: Tasks are independent and can run simultaneously
        - fan_out: One initial task should spawn multiple parallel subtasks
        - pipeline: Data flows naturally from one task to the next

        TASK COUNT: Generate 2-6 tasks based on complexity. Simple requests need fewer tasks, complex ones need more.

        For each task, consider:
        - What assumption am I making?
        - How will I verify this assumption?
        - What alternative approach exists if this fails?

        Only use tools from the available tools list. Return valid JSON.
        """

    async def create_execution_plan(
        self,
        guidance: str,
        available_tools: List[str],
        request: str,
        plan_id: Optional[str] = None
    ) -> str:
        """
        Create execution plan with state tracking

        Args:
            guidance: Task guidance and instructions
            available_tools: List of available tools
            request: Task request
            plan_id: Optional plan ID (auto-generated if not provided)
        """
        plan_id = plan_id or f"plan_{uuid.uuid4().hex[:8]}"
        print(f"🎯 Starting intelligent planning: {request}")
        print(f"📋 Plan ID: {plan_id}")

        try:
            # Create planning prompt
            prompt = self._create_planning_prompt(guidance, available_tools, request)

            # Use simplified text generator
            result_data = await generate(prompt, temperature=0.1)

            # Parse results
            if isinstance(result_data, str):
                # Extract JSON from markdown code blocks if present
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_data, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find JSON object in the text
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', result_data, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = result_data

                try:
                    plan_data = json.loads(json_str)
                    print(f"✅ Successfully parsed JSON plan")
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON parsing failed: {e}")
                    print(f"Raw response: {result_data[:200]}...")
                    # If parsing fails, create simple plan
                    plan_data = self._create_fallback_plan(request, available_tools)
            else:
                plan_data = result_data

            # Validate plan structure
            plan_data = self._validate_plan_data(plan_data)

            # Initialize task statuses
            for task in plan_data.get("tasks", []):
                task["status"] = task.get("status", "pending")
                task["total_tasks"] = len(plan_data["tasks"])

            # Add metadata
            plan = {
                "plan_id": plan_id,
                "plan_title": "Enhanced Execution Plan",
                "request": request,
                "guidance": guidance,
                "available_tools": available_tools,
                "total_tasks": len(plan_data.get("tasks", [])),
                "created_at": datetime.utcnow().isoformat(),
                "status": "created",
                **plan_data
            }

            # Save to state manager
            if self.state_manager.save_plan(plan_id, plan):
                self.current_plan_id = plan_id
                print(f"✅ Plan saved with {len(plan_data.get('tasks', []))} tasks")

                # Print visual summary
                print("\n" + "="*60)
                print(f"📊 PLAN SUMMARY")
                print("="*60)
                print(f"Hypothesis: {plan.get('solution_hypothesis', 'N/A')}")
                print(f"Execution Mode: {plan.get('execution_mode', 'N/A')}")
                print(f"Total Tasks: {plan['total_tasks']}")
                print("\nTasks:")
                for task in plan_data.get("tasks", []):
                    print(f"  {self._format_task_status(task)}")
                print("="*60 + "\n")
            else:
                print("⚠️ Failed to save plan to state manager")

            return self.create_response(
                "success",
                "create_execution_plan",
                plan
            )

        except Exception as e:
            logger.error(f"Planning creation failed: {str(e)}", exc_info=True)
            return self.create_response(
                "error",
                "create_execution_plan",
                {},
                f"Planning creation failed: {str(e)}"
            )

    def _create_fallback_plan(self, request: str, available_tools: List[str]) -> Dict[str, Any]:
        """Create fallback plan when JSON parsing fails"""
        return {
            "solution_hypothesis": "Direct execution approach",
            "verification_strategy": "Monitor task completion status",
            "execution_mode": "sequential",
            "max_tasks_reasoning": "Fallback plan with single task",
            "alternative_approaches": ["Break down into smaller tasks if needed"],
            "tasks": [
                {
                    "id": 1,
                    "title": "Execute Request",
                    "description": f"Execute the request: {request}",
                    "tools": available_tools[:3],  # Use first 3 tools
                    "execution_type": "sequential",
                    "dependencies": [],
                    "expected_output": "Completed request",
                    "verification_criteria": "Task completes without errors",
                    "priority": "high",
                    "status": "pending"
                }
            ]
        }

    async def adjust_execution_plan(
        self,
        plan_id: str,
        adjustment_type: str,
        task_id: Optional[int] = None,
        new_tasks: Optional[List[Dict[str, Any]]] = None,
        reasoning: str = ""
    ) -> str:
        """
        Dynamically adjust plan during execution

        Args:
            plan_id: Plan ID to adjust
            adjustment_type: Type of adjustment (expand, revise, branch)
            task_id: Task ID to adjust (for revise/branch)
            new_tasks: New tasks to add (for expand/branch)
            reasoning: Reason for adjustment
        """
        print(f"🔧 Adjusting plan {plan_id}: {adjustment_type}")

        try:
            plan = self.state_manager.get_plan(plan_id)
            if not plan:
                return self.create_response(
                    "error",
                    "adjust_execution_plan",
                    {},
                    f"Plan {plan_id} not found"
                )

            if adjustment_type == "expand":
                # Add new tasks beyond initial count
                if not new_tasks:
                    return self.create_response("error", "adjust_execution_plan", {},
                                              "new_tasks required for expand adjustment")

                current_tasks = plan.get("tasks", [])
                max_id = max([t["id"] for t in current_tasks]) if current_tasks else 0

                for i, new_task in enumerate(new_tasks):
                    new_task["id"] = max_id + i + 1
                    new_task["status"] = "pending"
                    new_task["added_during_execution"] = True
                    current_tasks.append(new_task)

                plan["total_tasks"] = len(current_tasks)
                plan["tasks"] = current_tasks

                # Add event
                self.state_manager.add_execution_event(plan_id, {
                    "event_type": "plan_expanded",
                    "data": {
                        "new_task_count": len(new_tasks),
                        "reasoning": reasoning
                    }
                })

                print(f"✅ Plan expanded with {len(new_tasks)} new tasks")

            elif adjustment_type == "revise":
                # Revise existing task
                if task_id is None:
                    return self.create_response("error", "adjust_execution_plan", {},
                                              "task_id required for revise adjustment")

                tasks = plan.get("tasks", [])
                for task in tasks:
                    if task["id"] == task_id:
                        task["is_revision"] = True
                        task["revision_reasoning"] = reasoning
                        task["status"] = "pending"  # Reset status for revision
                        break

                # Add event
                self.state_manager.add_execution_event(plan_id, {
                    "event_type": "task_revised",
                    "data": {
                        "task_id": task_id,
                        "reasoning": reasoning
                    }
                })

                print(f"✅ Task {task_id} marked for revision")

            elif adjustment_type == "branch":
                # Create alternative execution branch
                if task_id is None or not new_tasks:
                    return self.create_response("error", "adjust_execution_plan", {},
                                              "task_id and new_tasks required for branch adjustment")

                branch_id = f"branch_{uuid.uuid4().hex[:8]}"

                # Create branch with new tasks
                self.state_manager.create_branch(plan_id, branch_id, {
                    "branch_from_task": task_id,
                    "tasks": new_tasks,
                    "reasoning": reasoning
                })

                print(f"✅ Branch {branch_id} created from task {task_id}")

            else:
                return self.create_response("error", "adjust_execution_plan", {},
                                          f"Unknown adjustment type: {adjustment_type}")

            # Save updated plan
            self.state_manager.save_plan(plan_id, plan)

            return self.create_response(
                "success",
                "adjust_execution_plan",
                {
                    "plan_id": plan_id,
                    "adjustment_type": adjustment_type,
                    "updated_plan": plan
                }
            )

        except Exception as e:
            logger.error(f"Plan adjustment failed: {str(e)}", exc_info=True)
            return self.create_response(
                "error",
                "adjust_execution_plan",
                {},
                f"Plan adjustment failed: {str(e)}"
            )

    def update_task_status(
        self,
        plan_id: str,
        task_id: int,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Update task status with visual feedback

        Args:
            plan_id: Plan ID
            task_id: Task ID to update
            status: New status (pending, in_progress, completed, failed, blocked)
            result: Optional result data
        """
        try:
            plan = self.state_manager.get_plan(plan_id)
            if not plan:
                return self.create_response("error", "update_task_status", {},
                                          f"Plan {plan_id} not found")

            # Find task
            task = None
            for t in plan.get("tasks", []):
                if t["id"] == task_id:
                    task = t
                    break

            if not task:
                return self.create_response("error", "update_task_status", {},
                                          f"Task {task_id} not found in plan")

            # Update status
            success = self.state_manager.update_task_status(plan_id, task_id, status, result)

            if success:
                # Print visual feedback
                updated_task = task.copy()
                updated_task["status"] = status
                print(self._format_task_status(updated_task, status))

                return self.create_response(
                    "success",
                    "update_task_status",
                    {
                        "plan_id": plan_id,
                        "task_id": task_id,
                        "status": status,
                        "task": updated_task
                    }
                )
            else:
                return self.create_response("error", "update_task_status", {},
                                          "Failed to update task status")

        except Exception as e:
            logger.error(f"Task status update failed: {str(e)}", exc_info=True)
            return self.create_response(
                "error",
                "update_task_status",
                {},
                f"Task status update failed: {str(e)}"
            )

    def get_plan_status(self, plan_id: str) -> str:
        """Get real-time plan execution status"""
        try:
            plan = self.state_manager.get_plan(plan_id)
            if not plan:
                return self.create_response("error", "get_plan_status", {},
                                          f"Plan {plan_id} not found")

            tasks = plan.get("tasks", [])
            total_tasks = len(tasks)

            # Calculate status counts
            completed = sum(1 for t in tasks if t.get("status") == "completed")
            failed = sum(1 for t in tasks if t.get("status") == "failed")
            in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
            pending = sum(1 for t in tasks if t.get("status") == "pending")
            blocked = sum(1 for t in tasks if t.get("status") == "blocked")

            # Determine overall status
            if failed > 0:
                overall_status = "failed"
            elif completed == total_tasks:
                overall_status = "completed"
            elif in_progress > 0:
                overall_status = "in_progress"
            else:
                overall_status = "pending"

            # Get current task
            current_task = None
            for task in tasks:
                if task.get("status") == "in_progress":
                    current_task = task["title"]
                    break

            # Get execution history
            history = self.state_manager.get_execution_history(plan_id)
            branches = self.state_manager.get_branches(plan_id)

            status_data = {
                "plan_id": plan_id,
                "status": overall_status,
                "total_tasks": total_tasks,
                "completed_tasks": completed,
                "failed_tasks": failed,
                "in_progress_tasks": in_progress,
                "pending_tasks": pending,
                "blocked_tasks": blocked,
                "current_task": current_task,
                "progress_percentage": round((completed / total_tasks * 100) if total_tasks > 0 else 0, 2),
                "execution_events": len(history),
                "active_branches": len(branches),
                "branch_ids": [b.get("branch_id") for b in branches],
                "created_at": plan.get("created_at"),
                "last_updated": plan.get("last_updated")
            }

            # Print visual status
            print("\n" + "="*60)
            print(f"📊 PLAN STATUS: {plan_id}")
            print("="*60)
            print(f"Overall: {overall_status.upper()}")
            print(f"Progress: {status_data['progress_percentage']}% ({completed}/{total_tasks} tasks)")
            if current_task:
                print(f"Current: {current_task}")
            print(f"✅ Completed: {completed} | 🔄 In Progress: {in_progress} | ⏳ Pending: {pending}")
            if failed > 0:
                print(f"❌ Failed: {failed}")
            if blocked > 0:
                print(f"🚫 Blocked: {blocked}")
            if branches:
                print(f"🌿 Branches: {len(branches)}")
            print("="*60 + "\n")

            return self.create_response(
                "success",
                "get_plan_status",
                status_data
            )

        except Exception as e:
            logger.error(f"Get plan status failed: {str(e)}", exc_info=True)
            return self.create_response(
                "error",
                "get_plan_status",
                {},
                f"Get plan status failed: {str(e)}"
            )

    async def replan_execution(
        self,
        original_request: str,
        previous_plan: Dict[str, Any],
        execution_status: Dict[str, Any],
        feedback: str,
        available_tools: List[str]
    ) -> str:
        """
        Replan execution based on previous execution status and feedback
        (Existing replanning logic from original plan_tools.py)
        """
        # Use existing replanning logic...
        # (Keeping original implementation for compatibility)
        print(f"🔄 Starting replanning: {original_request}")

        try:
            from tools.general_tools.plan_tools import AutonomousPlanner

            # Use original replanning logic
            original_planner = AutonomousPlanner()
            return await original_planner.replan_execution(
                original_request, previous_plan, execution_status, feedback, available_tools
            )
        except Exception as e:
            logger.error(f"Replanning failed: {str(e)}", exc_info=True)
            return self.create_response(
                "error",
                "replan_execution",
                {},
                f"Replanning failed: {str(e)}"
            )


def register_enhanced_plan_tools(mcp: FastMCP):
    """Register enhanced autonomous planning tools"""
    planner = EnhancedAutonomousPlanner()

    @mcp.tool()
    async def create_execution_plan_v2(
        guidance: str,
        available_tools: str,  # JSON string or comma-separated list
        request: str,
        plan_id: str = None
    ) -> str:
        """
        Create enhanced execution plan with state tracking and hypothesis-driven planning

        This tool creates intelligent execution plans with:
        - Full execution history tracking
        - Hypothesis generation and verification
        - Support for dynamic adjustment and branching
        - Real-time status monitoring
        - Persistent state storage (Redis or in-memory)

        Keywords: plan, execution, task, workflow, organize, coordinate, hypothesis
        Category: planning

        Args:
            guidance: Task guidance and instructions
            available_tools: List of available tools (JSON array or comma-separated)
            request: Task request
            plan_id: Optional plan ID (auto-generated if not provided)
        """
        # Parse tool list
        try:
            if available_tools.startswith('['):
                tools_list = json.loads(available_tools)
            else:
                tools_list = [tool.strip() for tool in available_tools.split(',')]
        except:
            tools_list = [available_tools]

        return await planner.create_execution_plan(
            guidance, tools_list, request, plan_id
        )

    @mcp.tool()
    async def adjust_plan(
        plan_id: str,
        adjustment_type: str,
        task_id: int = None,
        new_tasks_json: str = None,
        reasoning: str = ""
    ) -> str:
        """
        Dynamically adjust execution plan during execution

        Supports three adjustment types:
        - expand: Add new tasks beyond initial count
        - revise: Mark existing task for revision
        - branch: Create alternative execution path

        Keywords: adjust, modify, expand, revise, branch, dynamic
        Category: planning

        Args:
            plan_id: Plan ID to adjust
            adjustment_type: Type of adjustment (expand, revise, branch)
            task_id: Task ID to adjust (required for revise/branch)
            new_tasks_json: JSON array of new tasks (required for expand/branch)
            reasoning: Reason for adjustment
        """
        # Parse new tasks if provided
        new_tasks = None
        if new_tasks_json:
            try:
                new_tasks = json.loads(new_tasks_json)
            except json.JSONDecodeError as e:
                return planner.create_response(
                    "error",
                    "adjust_plan",
                    {},
                    f"Failed to parse new_tasks_json: {str(e)}"
                )

        return await planner.adjust_execution_plan(
            plan_id, adjustment_type, task_id, new_tasks, reasoning
        )

    @mcp.tool()
    def update_task_status(
        plan_id: str,
        task_id: int,
        status: str,
        result_json: str = None
    ) -> str:
        """
        Update task status in execution plan

        Valid statuses: pending, in_progress, completed, failed, blocked

        Keywords: status, update, task, progress
        Category: planning

        Args:
            plan_id: Plan ID
            task_id: Task ID to update
            status: New status
            result_json: Optional JSON result data
        """
        # Parse result if provided
        result = None
        if result_json:
            try:
                result = json.loads(result_json)
            except json.JSONDecodeError as e:
                return planner.create_response(
                    "error",
                    "update_task_status",
                    {},
                    f"Failed to parse result_json: {str(e)}"
                )

        return planner.update_task_status(plan_id, task_id, status, result)

    @mcp.tool()
    def get_plan_status(plan_id: str) -> str:
        """
        Get real-time execution plan status

        Returns detailed status including:
        - Overall plan status
        - Task completion statistics
        - Current executing task
        - Execution history length
        - Active branches

        Keywords: status, progress, monitor, check
        Category: planning

        Args:
            plan_id: Plan ID to check
        """
        return planner.get_plan_status(plan_id)

    @mcp.tool()
    def get_execution_history(plan_id: str) -> str:
        """
        Get complete execution history for a plan

        Returns all execution events including:
        - Plan creation
        - Task status changes
        - Plan adjustments
        - Branch creation

        Keywords: history, events, audit, timeline
        Category: planning

        Args:
            plan_id: Plan ID
        """
        try:
            history = planner.state_manager.get_execution_history(plan_id)

            return planner.create_response(
                "success",
                "get_execution_history",
                {
                    "plan_id": plan_id,
                    "event_count": len(history),
                    "events": history
                }
            )
        except Exception as e:
            return planner.create_response(
                "error",
                "get_execution_history",
                {},
                f"Failed to get execution history: {str(e)}"
            )

    @mcp.tool()
    def list_active_plans() -> str:
        """
        List all active execution plans

        Returns list of all plan IDs currently stored in the state manager

        Keywords: list, plans, active
        Category: planning
        """
        try:
            plan_ids = planner.state_manager.list_active_plans()

            return planner.create_response(
                "success",
                "list_active_plans",
                {
                    "plan_count": len(plan_ids),
                    "plan_ids": plan_ids
                }
            )
        except Exception as e:
            return planner.create_response(
                "error",
                "list_active_plans",
                {},
                f"Failed to list active plans: {str(e)}"
            )

    print("🤖 Enhanced execution planning tools registered successfully")
    print("   ✅ State persistence enabled")
    print(f"   💾 Storage backend: {type(planner.state_manager).__name__}")
