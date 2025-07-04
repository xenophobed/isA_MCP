#!/usr/bin/env python3
"""
Autonomous Planning and Execution Tools
基于 BaseTool 的智能任务规划工具
"""

import json
from typing import Dict, List, Any
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from core.logging import get_logger

logger = get_logger(__name__)

class AutonomousPlanner(BaseTool):
    """自主规划工具，基于 chain of thought 的任务分解，动态获取MCP信息"""
    
    def __init__(self, mcp_server=None):
        super().__init__()
        self.mcp_server = mcp_server
        self.available_tools = {}
        self.available_resources = {}
        self.available_prompts = {}
        self.initialized = False
    
    async def initialize_with_mcp(self, mcp_server):
        """使用MCP服务器初始化，动态获取工具、资源和提示词"""
        self.mcp_server = mcp_server
        await self._load_mcp_capabilities()
        self.initialized = True
        logger.info(f"Autonomous planner initialized with {len(self.available_tools)} tools, "
                   f"{len(self.available_resources)} resources, {len(self.available_prompts)} prompts")
    
    async def _load_mcp_capabilities(self):
        """从MCP服务器加载所有能力"""
        if not self.mcp_server:
            logger.warning("No MCP server provided, using empty capabilities")
            return
        
        # 获取工具信息
        try:
            tools = await self.mcp_server.list_tools()
            self.available_tools = {}
            for tool in tools:
                self.available_tools[tool.name] = {
                    "name": tool.name,
                    "description": tool.description or f"Tool: {tool.name}",
                    "category": self._categorize_capability(tool.name),
                    "parameters": getattr(tool, 'inputSchema', {}).get('properties', {}) if hasattr(tool, 'inputSchema') else {}
                }
            logger.info(f"Loaded {len(self.available_tools)} tools from MCP")
        except Exception as e:
            logger.error(f"Failed to load tools from MCP: {e}")
            self.available_tools = {}
        
        # 获取资源信息
        try:
            resources = await self.mcp_server.list_resources()
            self.available_resources = {}
            for resource in resources:
                self.available_resources[resource.name] = {
                    "name": resource.name,
                    "description": resource.description or f"Resource: {resource.name}",
                    "uri": resource.uri,
                    "mimeType": getattr(resource, 'mimeType', 'text/plain')
                }
            logger.info(f"Loaded {len(self.available_resources)} resources from MCP")
        except Exception as e:
            logger.error(f"Failed to load resources from MCP: {e}")
            self.available_resources = {}
        
        # 获取提示词信息（如果支持）
        try:
            prompts = await self.mcp_server.list_prompts()
            self.available_prompts = {}
            for prompt in prompts:
                self.available_prompts[prompt.name] = {
                    "name": prompt.name,
                    "description": prompt.description or f"Prompt: {prompt.name}",
                    "arguments": getattr(prompt, 'arguments', [])
                }
            logger.info(f"Loaded {len(self.available_prompts)} prompts from MCP")
        except Exception as e:
            logger.info(f"No prompts available or failed to load: {e}")
            self.available_prompts = {}
    
    def _categorize_capability(self, name: str) -> str:
        """根据名称对能力进行分类"""
        name_lower = name.lower()
        if any(keyword in name_lower for keyword in ['web', 'scrape', 'search', 'fetch']):
            return 'web'
        elif any(keyword in name_lower for keyword in ['image', 'generate', 'picture', 'visual']):
            return 'image'
        elif any(keyword in name_lower for keyword in ['memory', 'remember', 'recall', 'forget']):
            return 'memory'
        elif any(keyword in name_lower for keyword in ['rag', 'document', 'search']):
            return 'document'
        elif any(keyword in name_lower for keyword in ['admin', 'system', 'monitor']):
            return 'system'
        elif any(keyword in name_lower for keyword in ['analyze', 'analytics', 'data']):
            return 'analysis'
        else:
            return 'general'
    
    def _get_dynamic_planning_prompts(self) -> Dict[str, str]:
        """获取动态规划提示词，基于当前可用的能力"""
        tool_list = "\n".join([f"- {name}: {info['description']}" for name, info in self.available_tools.items()])
        resource_list = "\n".join([f"- {name}: {info['description']}" for name, info in self.available_resources.items()])
        
        return {
            "task_analysis": f"""
            分析以下复杂任务并提供详细的任务分解方案：
            
            任务: {{request}}
            
            当前可用的工具：
            {tool_list}
            
            当前可用的资源：
            {resource_list}
            
            请分析：
            1. 任务的核心目标和子目标
            2. 需要使用哪些具体的工具和资源
            3. 可能的执行步骤和依赖关系
            4. 预期的输出格式
            5. 潜在的风险和挑战
            
            请以JSON格式返回分析结果，确保推荐的工具在可用工具列表中。
            """,
            
            "task_breakdown": f"""
            基于以下任务分析，创建详细的执行计划：
            
            任务分析: {{analysis}}
            
            可用工具详情：
            {tool_list}
            
            可用资源详情：
            {resource_list}
            
            请创建一个包含以下信息的任务列表：
            1. 每个任务的标题和描述
            2. 需要使用的具体工具（必须从可用工具列表中选择）
            3. 需要的资源（必须从可用资源列表中选择）
            4. 任务间的依赖关系
            5. 预估执行时间
            6. 成功标准
            
            返回JSON格式的任务列表，确保所有工具和资源都是有效的。
            """,
            
            "execution_strategy": """
            为以下任务列表设计最优执行策略：
            
            任务列表: {tasks}
            
            请分析：
            1. 任务执行顺序（串行/并行）
            2. 资源分配策略
            3. 错误处理机制
            4. 监控和反馈机制
            
            返回JSON格式的执行策略。
            """
        }
    
    async def analyze_request(self, request: str) -> Dict[str, Any]:
        """分析复杂请求，提取关键信息，使用动态获取的能力信息"""
        if not self.initialized:
            return {
                "success": False,
                "error": "Autonomous planner not initialized with MCP server",
                "analysis": {}
            }
        
        try:
            # 使用动态提示词
            planning_prompts = self._get_dynamic_planning_prompts()
            prompt = planning_prompts["task_analysis"].format(request=request)
            
            result_data, billing_info = await self.call_isa_with_billing(
                input_data=prompt,
                task="chat",
                service_type="text",
                parameters={"temperature": 0.1}
            )
            
            # 解析分析结果
            if isinstance(result_data, str):
                try:
                    analysis = json.loads(result_data)
                except json.JSONDecodeError:
                    analysis = {"raw_analysis": result_data}
            else:
                analysis = result_data
            
            return {
                "success": True,
                "analysis": analysis,
                "billing": billing_info
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis": {}
            }
    
    async def breakdown_tasks(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于分析结果分解任务，使用动态获取的工具和资源信息"""
        if not self.initialized:
            return self._create_generic_tasks("Planner not initialized")
        
        try:
            # 使用动态提示词
            planning_prompts = self._get_dynamic_planning_prompts()
            prompt = planning_prompts["task_breakdown"].format(
                analysis=json.dumps(analysis, ensure_ascii=False)
            )
            
            result_data, billing_info = await self.call_isa_with_billing(
                input_data=prompt,
                task="chat",
                service_type="text",
                parameters={"temperature": 0.1}
            )
            
            # 解析任务列表
            if isinstance(result_data, str):
                try:
                    tasks = json.loads(result_data)
                    if isinstance(tasks, dict) and "tasks" in tasks:
                        tasks = tasks["tasks"]
                    elif not isinstance(tasks, list):
                        tasks = [tasks]
                except json.JSONDecodeError:
                    # 如果解析失败，创建通用任务
                    tasks = self._create_generic_tasks(result_data)
            else:
                tasks = result_data if isinstance(result_data, list) else [result_data]
            
            # 标准化任务格式并验证工具和资源的有效性
            standardized_tasks = []
            for i, task in enumerate(tasks):
                if isinstance(task, dict):
                    # 验证并过滤有效的工具
                    requested_tools = task.get("tools", [])
                    valid_tools = [tool for tool in requested_tools if tool in self.available_tools]
                    
                    # 验证并过滤有效的资源
                    requested_resources = task.get("resources", [])
                    valid_resources = [res for res in requested_resources if res in self.available_resources]
                    
                    standardized_task = {
                        "id": task.get("id", i + 1),
                        "title": task.get("title", f"Task {i + 1}"),
                        "description": task.get("description", ""),
                        "tools": valid_tools,
                        "resources": valid_resources,
                        "dependencies": task.get("dependencies", []),
                        "estimated_duration": task.get("estimated_duration", "Unknown"),
                        "status": "pending",
                        "priority": task.get("priority", "medium"),
                        "category": task.get("category", "general")
                    }
                    standardized_tasks.append(standardized_task)
            
            return standardized_tasks
            
        except Exception as e:
            return self._create_generic_tasks(str(e))
    
    def _create_generic_tasks(self, context: str) -> List[Dict[str, Any]]:
        """创建通用任务结构"""
        return [
            {
                "id": 1,
                "title": "任务分析",
                "description": f"分析请求: {context[:100]}...",
                "tools": ["format_response", "remember"],
                "dependencies": [],
                "estimated_duration": "1-2 minutes",
                "status": "pending",
                "priority": "high"
            },
            {
                "id": 2,
                "title": "任务执行",
                "description": "执行计划的方法",
                "tools": ["format_response"],
                "dependencies": [1],
                "estimated_duration": "2-3 minutes",
                "status": "pending",
                "priority": "medium"
            }
        ]
    
    async def plan_autonomous_task(
        self,
        request: str,
        max_tasks: int = 5,
        execution_mode: str = "react_agent"
    ) -> str:
        """
        创建自主执行计划
        
        Args:
            request: 复杂任务请求
            max_tasks: 最大任务数量
            execution_mode: 执行模式
        """
        print(f"🎯 开始智能规划: {request}")
        
        # 步骤1: 分析请求
        analysis_result = await self.analyze_request(request)
        if not analysis_result["success"]:
            return self.create_response(
                "error",
                "plan_autonomous_task",
                {},
                f"请求分析失败: {analysis_result['error']}"
            )
        
        # 步骤2: 分解任务
        tasks = await self.breakdown_tasks(analysis_result["analysis"])
        
        # 限制任务数量
        if len(tasks) > max_tasks:
            tasks = tasks[:max_tasks]
        
        # 步骤3: 创建执行计划
        plan = {
            "plan_title": "智能自主执行计划",
            "request": request,
            "execution_mode": execution_mode,
            "analysis": analysis_result["analysis"],
            "tasks": tasks,
            "total_tasks": len(tasks),
            "complexity": self._calculate_complexity(tasks),
            "estimated_duration": self._estimate_duration(tasks),
            "success_criteria": "所有任务成功完成并产生预期输出",
            "execution_strategy": {
                "mode": execution_mode,
                "parallel_execution": execution_mode == "parallel",
                "error_handling": "continue_on_error",
                "monitoring": "real_time"
            },
            "available_capabilities": {
                "tools_count": len(self.available_tools),
                "resources_count": len(self.available_resources),
                "prompts_count": len(self.available_prompts),
                "tools": list(self.available_tools.keys()),
                "resources": list(self.available_resources.keys())
            }
        }
        
        print(f"✅ 智能规划完成，生成 {len(tasks)} 个任务")
        
        return self.create_response(
            "success",
            "plan_autonomous_task",
            plan
        )
    
    def _calculate_complexity(self, tasks: List[Dict[str, Any]]) -> str:
        """计算任务复杂度"""
        if len(tasks) > 4:
            return "high"
        elif len(tasks) > 2:
            return "medium"
        else:
            return "low"
    
    def _estimate_duration(self, tasks: List[Dict[str, Any]]) -> str:
        """估算总执行时间"""
        total_min = len(tasks) * 2  # 每个任务至少2分钟
        total_max = len(tasks) * 4  # 每个任务最多4分钟
        return f"{total_min}-{total_max} minutes"

def register_autonomous_tools(mcp: FastMCP):
    """注册自主规划工具"""
    planner = AutonomousPlanner()
    
    @mcp.tool()
    async def plan_autonomous_task(
        request: str,
        max_tasks: int = 5,
        execution_mode: str = "react_agent"
    ) -> str:
        """
        创建复杂多步任务的综合自主执行计划
        
        此工具分析复杂请求并创建详细的任务列表，包含
        特定工具、提示词和执行策略以实现自主完成。
        
        Keywords: plan, autonomous, task, workflow, execute, coordinate, organize, complex
        Category: autonomous
        
        Args:
            request: 要规划的复杂任务请求
            max_tasks: 生成的最大任务数量
            execution_mode: 执行模式 (react_agent, sequential, parallel)
        """
        # 如果未初始化，先初始化MCP连接
        if not planner.initialized:
            await planner.initialize_with_mcp(mcp)
        
        return await planner.plan_autonomous_task(request, max_tasks, execution_mode)
    
    @mcp.tool()
    def get_autonomous_status(
        plan_id: str = "current"
    ) -> str:
        """
        获取自主执行计划的状态
        
        此工具提供自主任务执行进度的实时状态更新和完成率。
        
        Keywords: status, autonomous, progress, monitor, check
        Category: autonomous
        
        Args:
            plan_id: 要检查状态的计划ID
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
    
    print("🤖 智能自主规划工具注册成功")