#!/usr/bin/env python3
"""
Unit tests for autonomous_tools.py
测试自主规划工具的各种功能
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# 导入被测试的模块
from tools.autonomous_tools import AutonomousPlanner, register_autonomous_tools


class MockMCPTool:
    """Mock MCP Tool"""
    def __init__(self, name: str, description: str = None):
        self.name = name
        self.description = description or f"Mock tool: {name}"
        self.inputSchema = {'properties': {'param1': {'type': 'string'}}}


class MockMCPResource:
    """Mock MCP Resource"""
    def __init__(self, name: str, description: str = None, uri: str = None):
        self.name = name
        self.description = description or f"Mock resource: {name}"
        self.uri = uri or f"resource://{name}"
        self.mimeType = "text/plain"


class MockMCPPrompt:
    """Mock MCP Prompt"""
    def __init__(self, name: str, description: str = None):
        self.name = name
        self.description = description or f"Mock prompt: {name}"
        self.arguments = [{'name': 'arg1', 'type': 'string'}]


class MockMCPServer:
    """Mock MCP Server for testing"""
    
    def __init__(self):
        self.tools = [
            MockMCPTool("web_search", "Search web content"),
            MockMCPTool("scrape_content", "Scrape web pages"),
            MockMCPTool("analyze_content", "Analyze text content"),
            MockMCPTool("generate_summary", "Generate content summary"),
            MockMCPTool("remember", "Remember information"),
            MockMCPTool("format_response", "Format response")
        ]
        self.resources = [
            MockMCPResource("test_database", "Test database", "db://test"),
            MockMCPResource("config_file", "Configuration file", "file://config.json")
        ]
        self.prompts = [
            MockMCPPrompt("analysis_prompt", "Analysis prompt"),
            MockMCPPrompt("summary_prompt", "Summary prompt")
        ]
    
    async def list_tools(self):
        """返回模拟的工具列表"""
        return self.tools
    
    async def list_resources(self):
        """返回模拟的资源列表"""
        return self.resources
    
    async def list_prompts(self):
        """返回模拟的提示词列表"""
        return self.prompts


class TestAutonomousPlanner:
    """测试 AutonomousPlanner 类"""
    
    @pytest.fixture
    def mock_mcp_server(self):
        """创建模拟的MCP服务器"""
        return MockMCPServer()
    
    @pytest.fixture
    def planner(self):
        """创建 AutonomousPlanner 实例"""
        return AutonomousPlanner()
    
    
    def test_init(self, planner):
        """测试初始化"""
        assert planner.mcp_server is None
        assert planner.available_tools == {}
        assert planner.available_resources == {}
        assert planner.available_prompts == {}
        assert planner.initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_with_mcp(self, planner, mock_mcp_server):
        """测试MCP初始化"""
        await planner.initialize_with_mcp(mock_mcp_server)
        
        assert planner.initialized is True
        assert planner.mcp_server == mock_mcp_server
        assert len(planner.available_tools) == 6  # 6个模拟工具
        assert len(planner.available_resources) == 2  # 2个模拟资源
        assert len(planner.available_prompts) == 2  # 2个模拟提示词
        
        # 检查工具分类
        assert planner.available_tools["web_search"]["category"] == "web"
        assert planner.available_tools["remember"]["category"] == "memory"
        assert planner.available_tools["analyze_content"]["category"] == "analysis"
    
    @pytest.mark.asyncio
    async def test_initialize_with_no_mcp(self, planner):
        """测试没有MCP服务器的初始化"""
        await planner.initialize_with_mcp(None)
        
        assert planner.initialized is True
        assert planner.available_tools == {}
        assert planner.available_resources == {}
        assert planner.available_prompts == {}
    
    def test_categorize_capability(self, planner):
        """测试能力分类"""
        assert planner._categorize_capability("web_search") == "web"
        assert planner._categorize_capability("image_generate") == "image"
        assert planner._categorize_capability("memory_store") == "memory"
        assert planner._categorize_capability("document_rag") == "document"
        assert planner._categorize_capability("admin_monitor") == "system"
        assert planner._categorize_capability("analyze_data") == "analysis"
        assert planner._categorize_capability("unknown_tool") == "general"
    
    @pytest.mark.asyncio
    async def test_get_dynamic_planning_prompts(self, planner, mock_mcp_server):
        """测试动态提示词生成"""
        await planner.initialize_with_mcp(mock_mcp_server)
        prompts = planner._get_dynamic_planning_prompts()
        
        assert "task_analysis" in prompts
        assert "task_breakdown" in prompts
        assert "execution_strategy" in prompts
        
        # 检查提示词包含可用工具信息
        assert "web_search" in prompts["task_analysis"]
        assert "test_database" in prompts["task_analysis"]
    
    @pytest.mark.asyncio
    async def test_analyze_request_not_initialized(self, planner):
        """测试未初始化时的请求分析"""
        result = await planner.analyze_request("测试请求")
        
        assert result["success"] is False
        assert "not initialized" in result["error"]
        assert result["analysis"] == {}
    
    @pytest.mark.asyncio
    async def test_analyze_request_success(self, planner, mock_mcp_server):
        """测试成功的请求分析"""
        await planner.initialize_with_mcp(mock_mcp_server)
        mock_response = {
            "core_goals": ["搜索信息", "生成摘要"],
            "tools_needed": ["web_search", "generate_summary"],
            "complexity": "medium"
        }
        
        with patch.object(planner, 'call_isa_with_billing', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (json.dumps(mock_response), {"cost_usd": 0.001})
            
            result = await planner.analyze_request("搜索Python测试资料并生成摘要")
            
            assert result["success"] is True
            assert "analysis" in result
            assert "billing" in result
            assert result["analysis"]["core_goals"] == ["搜索信息", "生成摘要"]
    
    @pytest.mark.asyncio
    async def test_breakdown_tasks_not_initialized(self, planner):
        """测试未初始化时的任务分解"""
        result = await planner.breakdown_tasks({"test": "analysis"})
        
        assert len(result) == 2  # 默认通用任务
        assert result[0]["title"] == "任务分析"
        assert result[1]["title"] == "任务执行"
    
    @pytest.mark.asyncio
    async def test_breakdown_tasks_success(self, planner, mock_mcp_server):
        """测试成功的任务分解"""
        await planner.initialize_with_mcp(mock_mcp_server)
        mock_tasks = {
            "tasks": [
                {
                    "id": 1,
                    "title": "搜索资料",
                    "description": "在网上搜索Python测试资料",
                    "tools": ["web_search", "scrape_content"],
                    "resources": ["test_database"],
                    "dependencies": [],
                    "priority": "high"
                }
            ]
        }
        
        with patch.object(planner, 'call_isa_with_billing', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (json.dumps(mock_tasks), {"cost_usd": 0.002})
            
            result = await planner.breakdown_tasks({"test": "analysis"})
            
            assert len(result) == 1
            assert result[0]["title"] == "搜索资料"
            assert result[0]["tools"] == ["web_search", "scrape_content"]  # 有效工具
            assert result[0]["resources"] == ["test_database"]  # 有效资源
    
    @pytest.mark.asyncio
    async def test_plan_autonomous_task_success(self, planner, mock_mcp_server):
        """测试成功的自主任务规划"""
        await planner.initialize_with_mcp(mock_mcp_server)
        # Mock analyze_request
        mock_analysis = {
            "core_goals": ["搜索", "总结"],
            "complexity": "medium"
        }
        
        # Mock breakdown_tasks
        mock_tasks = [
            {
                "id": 1,
                "title": "搜索资料",
                "tools": ["web_search"],
                "status": "pending",
                "priority": "high"
            }
        ]
        
        with patch.object(planner, 'analyze_request', new_callable=AsyncMock) as mock_analyze:
            with patch.object(planner, 'breakdown_tasks', new_callable=AsyncMock) as mock_breakdown:
                mock_analyze.return_value = {"success": True, "analysis": mock_analysis}
                mock_breakdown.return_value = mock_tasks
                
                result = await planner.plan_autonomous_task("搜索Python测试资料")
                
                # 解析JSON响应
                response = json.loads(result)
                
                assert response["status"] == "success"
                assert response["action"] == "plan_autonomous_task"
                assert response["data"]["plan_title"] == "智能自主执行计划"
                assert response["data"]["total_tasks"] == 1
                assert response["data"]["complexity"] == "low"  # 1个任务 = low complexity
                assert len(response["data"]["tasks"]) == 1
    
    def test_calculate_complexity(self, planner):
        """测试复杂度计算"""
        assert planner._calculate_complexity([1, 2]) == "low"
        assert planner._calculate_complexity([1, 2, 3]) == "medium"
        assert planner._calculate_complexity([1, 2, 3, 4, 5]) == "high"
    
    def test_estimate_duration(self, planner):
        """测试时间估算"""
        tasks = [1, 2, 3]
        duration = planner._estimate_duration(tasks)
        assert duration == "6-12 minutes"  # 3个任务 * 2-4分钟


class TestRegistration:
    """测试工具注册功能"""
    
    @pytest.fixture
    def mock_mcp(self):
        """创建模拟的MCP实例"""
        mock = Mock()
        mock.tool = Mock(return_value=lambda func: func)
        return mock
    
    def test_register_autonomous_tools(self, mock_mcp):
        """测试工具注册"""
        register_autonomous_tools(mock_mcp)
        
        # 检查是否调用了tool装饰器
        assert mock_mcp.tool.call_count == 2  # plan_autonomous_task 和 get_autonomous_status


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])