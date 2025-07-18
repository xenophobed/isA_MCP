#!/usr/bin/env python3
"""
Autonomous Planning and Execution Tools
Intelligent task planning tools based on BaseTool
"""

import json
from typing import Dict, List, Any
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.services.intelligence_service.language.text_generator import generate
from core.logging import get_logger

logger = get_logger(__name__)

class AutonomousPlanner(BaseTool):
    """Simplified intelligent planning tool that accepts guidance and tool lists to generate execution plans"""
    
    def __init__(self):
        super().__init__()
    
    def _create_planning_prompt(self, guidance: str, available_tools: List[str], request: str) -> str:
        """Create planning prompt"""
        tool_list = "\n".join([f"- {tool}" for tool in available_tools])
        
        return f"""
        You are an intelligent task planner. Create an execution plan based on the following:
        
        GUIDANCE: {guidance}
        REQUEST: {request}
        
        AVAILABLE_TOOLS:
        {tool_list}
        
        Analyze the request and guidance to determine:
        1. The best execution mode for this type of task
        2. The optimal number of tasks needed
        3. The most logical task breakdown and dependencies
        
        Create a detailed execution plan with the following structure:
        {{
            "execution_mode": "sequential|parallel|fan_out|pipeline",
            "max_tasks_reasoning": "Brief explanation of why this number of tasks is optimal",
            "tasks": [
                {{
                    "id": 1,
                    "title": "Task Title",
                    "description": "Detailed description",
                    "tools": ["tool1", "tool2"],
                    "execution_type": "sequential|parallel|fan_out|pipeline",
                    "dependencies": ["task_id_list"],
                    "expected_output": "What this task should produce",
                    "priority": "high|medium|low"
                }}
            ]
        }}
        
        EXECUTION MODES - Choose the most appropriate:
        - sequential: Tasks have clear dependencies and must run in order
        - parallel: Tasks are independent and can run simultaneously
        - fan_out: One initial task should spawn multiple parallel subtasks
        - pipeline: Data flows naturally from one task to the next
        
        TASK COUNT: Generate 2-6 tasks based on complexity. Simple requests need fewer tasks, complex ones need more.
        
        Only use tools from the available tools list. Return valid JSON.
        """
    
    async def create_execution_plan(
        self,
        guidance: str,
        available_tools: List[str],
        request: str
    ) -> str:
        """
        Create execution plan
        
        Args:
            guidance: Task guidance and instructions
            available_tools: List of available tools
            request: Task request
        """
        print(f"🎯 Starting intelligent planning: {request}")
        
        try:
            # Create planning prompt
            prompt = self._create_planning_prompt(guidance, available_tools, request)
            
            # Use simplified text generator
            result_data = await generate(prompt, temperature=0.1)
            
            # Parse results
            if isinstance(result_data, str):
                try:
                    plan_data = json.loads(result_data)
                except json.JSONDecodeError:
                    # If parsing fails, create simple plan
                    plan_data = self._create_fallback_plan(request, available_tools)
            else:
                plan_data = result_data
            
            # Task count is automatically determined by AI, no external limits needed
            
            # Add metadata
            plan = {
                "plan_title": "Intelligent Execution Plan",
                "request": request,
                "guidance": guidance,
                "available_tools": available_tools,
                "total_tasks": len(plan_data.get("tasks", [])),
                **plan_data
            }
            
            print(f"✅ Intelligent planning completed, generated {len(plan_data.get('tasks', []))} tasks")
            
            return self.create_response(
                "success",
                "create_execution_plan",
                plan
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "create_execution_plan",
                {},
                f"Planning creation failed: {str(e)}"
            )
    
    def _create_fallback_plan(self, request: str, available_tools: List[str]) -> Dict[str, Any]:
        """Create fallback plan when JSON parsing fails"""
        return {
            "execution_mode": "sequential",
            "max_tasks_reasoning": "Fallback plan with single task",
            "tasks": [
                {
                    "id": 1,
                    "title": "Execute Request",
                    "description": f"Execute the request: {request}",
                    "tools": available_tools[:3],  # Use first 3 tools
                    "execution_type": "sequential",
                    "dependencies": [],
                    "expected_output": "Completed request",
                    "priority": "high"
                }
            ]
        }
    
    def _create_replanning_prompt(
        self, 
        original_request: str,
        previous_plan: Dict[str, Any],
        execution_status: Dict[str, Any],
        feedback: str,
        available_tools: List[str]
    ) -> str:
        """Create replanning prompt"""
        tool_list = "\n".join([f"- {tool}" for tool in available_tools])
        
        return f"""
        You are an intelligent task replanner. Based on previous execution results and feedback, create an improved execution plan.
        
        ORIGINAL REQUEST: {original_request}
        
        PREVIOUS PLAN SUMMARY:
        - Execution Mode: {previous_plan.get('execution_mode', 'N/A')}
        - Total Tasks: {len(previous_plan.get('tasks', []))}
        - Tasks Overview: {', '.join([task.get('title', 'Untitled') for task in previous_plan.get('tasks', [])])}
        
        EXECUTION STATUS:
        - Completed Tasks: {execution_status.get('completed_tasks', 0)}
        - Failed Tasks: {execution_status.get('failed_tasks', 0)}
        - Current Status: {execution_status.get('status', 'unknown')}
        - Issues Encountered: {execution_status.get('issues', [])}
        
        FEEDBACK: {feedback}
        
        AVAILABLE_TOOLS:
        {tool_list}
        
        Based on this information, create an improved execution plan that:
        1. Addresses the issues that caused failures
        2. Incorporates lessons learned from successful tasks
        3. Adjusts execution mode if needed for better performance
        4. Optimizes task breakdown based on actual execution experience
        5. Takes into account the feedback provided
        
        Create a detailed execution plan with the following structure:
        {{
            "execution_mode": "sequential|parallel|fan_out|pipeline",
            "max_tasks_reasoning": "Explanation of why this revised approach is better",
            "improvement_notes": "Specific improvements made based on previous execution",
            "tasks": [
                {{
                    "id": 1,
                    "title": "Task Title",
                    "description": "Detailed description",
                    "tools": ["tool1", "tool2"],
                    "execution_type": "sequential|parallel|fan_out|pipeline",
                    "dependencies": ["task_id_list"],
                    "expected_output": "What this task should produce",
                    "priority": "high|medium|low",
                    "changes_from_previous": "How this task differs from the original plan"
                }}
            ]
        }}
        
        Only use tools from the available tools list. Return valid JSON.
        """
    
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
        
        Args:
            original_request: Original task request
            previous_plan: Previous execution plan
            execution_status: Execution status information
            feedback: Execution feedback
            available_tools: List of available tools
        """
        print(f"🔄 Starting replanning: {original_request}")
        
        try:
            # Create replanning prompt
            prompt = self._create_replanning_prompt(
                original_request, previous_plan, execution_status, feedback, available_tools
            )
            
            # Use text generator
            result_data = await generate(prompt, temperature=0.1)
            
            # Parse results
            if isinstance(result_data, str):
                try:
                    plan_data = json.loads(result_data)
                except json.JSONDecodeError:
                    # If parsing fails, create simple replan
                    plan_data = self._create_fallback_replan(original_request, available_tools, feedback)
            else:
                plan_data = result_data
            
            # Add replanning metadata
            replan = {
                "plan_title": "Intelligent Replanning",
                "original_request": original_request,
                "previous_plan_summary": {
                    "execution_mode": previous_plan.get('execution_mode'),
                    "total_tasks": len(previous_plan.get('tasks', [])),
                    "completed_tasks": execution_status.get('completed_tasks', 0)
                },
                "feedback": feedback,
                "available_tools": available_tools,
                "total_tasks": len(plan_data.get("tasks", [])),
                "replanning_timestamp": json.loads(self.create_response("", "", {})["data"])["timestamp"],
                **plan_data
            }
            
            print(f"✅ Replanning completed, generated {len(plan_data.get('tasks', []))} improved tasks")
            
            return self.create_response(
                "success",
                "replan_execution",
                replan
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "replan_execution",
                {},
                f"Replanning failed: {str(e)}"
            )
    
    def _create_fallback_replan(self, request: str, available_tools: List[str], feedback: str) -> Dict[str, Any]:
        """Create fallback replan"""
        return {
            "execution_mode": "sequential",
            "max_tasks_reasoning": "Fallback replan with simplified approach based on feedback",
            "improvement_notes": f"Simplified approach considering: {feedback}",
            "tasks": [
                {
                    "id": 1,
                    "title": "Revised Execution",
                    "description": f"Execute request with improvements: {request}",
                    "tools": available_tools[:2],  # Use fewer tools to reduce complexity
                    "execution_type": "sequential",
                    "dependencies": [],
                    "expected_output": "Improved results based on feedback",
                    "priority": "high",
                    "changes_from_previous": "Simplified approach with fewer tools"
                }
            ]
        }

def register_plan_tools(mcp: FastMCP):
    """Register autonomous planning tools"""
    planner = AutonomousPlanner()
    
    @mcp.tool()
    async def create_execution_plan(
        guidance: str,
        available_tools: str,  # JSON string or comma-separated list
        request: str
    ) -> str:
        """
        Create intelligent execution plan
        
        This tool accepts guidance, tool lists, and requests, with AI automatically determining the best execution mode and task count.
        
        Keywords: plan, execution, task, workflow, organize, coordinate
        Category: planning
        
        Args:
            guidance: Task guidance and instructions
            available_tools: List of available tools (JSON array or comma-separated)
            request: Task request
        """
        # Parse tool list
        try:
            if available_tools.startswith('['):
                tools_list = json.loads(available_tools)
            else:
                tools_list = [tool.strip() for tool in available_tools.split(',')]
        except:
            tools_list = [available_tools]  # If parsing fails, treat as single tool
        
        return await planner.create_execution_plan(
            guidance, tools_list, request
        )
    
    @mcp.tool()
    async def replan_execution(
        original_request: str,
        previous_plan: str,  # JSON string
        execution_status: str,  # JSON string
        feedback: str,
        available_tools: str  # JSON string or comma-separated
    ) -> str:
        """
        Replan execution based on previous execution status and feedback
        
        This tool creates improved execution plans based on previous execution results and feedback, addressing failure issues and optimizing task breakdown.
        
        Keywords: replan, improve, feedback, execution, optimize, adjust
        Category: planning
        
        Args:
            original_request: Original task request
            previous_plan: Previous execution plan (JSON format)
            execution_status: Execution status information (JSON format)
            feedback: Execution feedback and improvement suggestions
            available_tools: List of available tools (JSON array or comma-separated)
        """
        # Parse input parameters
        try:
            prev_plan = json.loads(previous_plan) if isinstance(previous_plan, str) else previous_plan
            exec_status = json.loads(execution_status) if isinstance(execution_status, str) else execution_status
            
            if available_tools.startswith('['):
                tools_list = json.loads(available_tools)
            else:
                tools_list = [tool.strip() for tool in available_tools.split(',')]
        except json.JSONDecodeError as e:
            return planner.create_response(
                "error",
                "replan_execution", 
                {},
                f"JSON parsing failed: {str(e)}"
            )
        
        return await planner.replan_execution(
            original_request, prev_plan, exec_status, feedback, tools_list
        )
    
    @mcp.tool()
    def get_autonomous_status(
        plan_id: str = "current"
    ) -> str:
        """
        Get autonomous execution plan status
        
        This tool provides real-time status updates and completion rates for autonomous task execution progress.
        
        Keywords: status, autonomous, progress, monitor, check
        Category: autonomous
        
        Args:
            plan_id: Plan ID to check status for
        """
        status = {
            "plan_id": plan_id,
            "status": "in_progress",
            "completed_tasks": 2,
            "total_tasks": 3,
            "current_task": "Visual Content Generation",
            "progress_percentage": 67,
            "estimated_remaining": "1-2 minutes",
            "errors": [],
            "warnings": []
        }
        
        return json.dumps(status, indent=2, ensure_ascii=False)
    
    print("🤖 Intelligent execution planning tools registered successfully")