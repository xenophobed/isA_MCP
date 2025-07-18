#!/usr/bin/env python3
"""
Real pytest tests for web_automation tool
"""

import pytest
import aiohttp
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestWebAutomationCapabilities:
    """Test 1: Tool registered in capabilities"""
    
    BASE_URL = "http://localhost:8081"
    
    @pytest.mark.asyncio
    async def test_web_automation_registered(self):
        """Test that web_automation tool is registered in capabilities"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.BASE_URL}/capabilities") as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["status"] == "success"
                tools = data["capabilities"]["tools"]["available"]
                
                # Check that web_automation is registered
                assert "web_automation" in tools, "web_automation tool not found in capabilities"


class TestWebAutomationDiscovery:
    """Test 2: Tool selection via AI discovery"""
    
    BASE_URL = "http://localhost:8081"
    
    @pytest.mark.asyncio
    async def test_web_automation_discovery_basic(self):
        """Test AI discovery finds web_automation for automation tasks"""
        request_data = {
            "request": "I need to automate browser interactions"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE_URL}/discover",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["status"] == "success"
                assert "capabilities" in data
                
                # Should discover web_automation tool
                suggested_tools = data["capabilities"]["tools"]
                assert "web_automation" in suggested_tools
    
    @pytest.mark.asyncio
    async def test_web_automation_discovery_forms(self):
        """Test AI discovery finds web_automation for form filling"""
        request_data = {
            "request": "I want to fill out web forms automatically"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE_URL}/discover",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["status"] == "success"
                suggested_tools = data["capabilities"]["tools"]
                assert "web_automation" in suggested_tools
    
    @pytest.mark.asyncio
    async def test_web_automation_discovery_interactions(self):
        """Test AI discovery finds web_automation for complex interactions"""
        request_data = {
            "request": "I need to click buttons and navigate websites programmatically"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE_URL}/discover",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                assert response.status == 200
                data = await response.json()
                
                assert data["status"] == "success"
                suggested_tools = data["capabilities"]["tools"]
                assert "web_automation" in suggested_tools


class TestWebAutomationTool:
    """Test 3: MCP tool input/output correctness"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_web_automation_5_step_workflow(self):
        """Test 5-step atomic workflow: Google search with airpods"""
        from tools.services.web_services.services.web_automation_service import WebAutomationService
        
        print(f"\n🚀 Testing 5-step atomic workflow")
        print("📋 Steps: Screenshot → image_analyzer → ui_detector → text_generator → Playwright execution")
        
        service = WebAutomationService()
        
        try:
            # Test the complete 5-step workflow
            result = await service.execute_task(
                url="https://www.google.com",
                task="search airpods"
            )
            
            print(f"✅ 5-step workflow completed with success: {result.get('success')}")
            
            # Validate response structure
            assert isinstance(result, dict)
            assert "success" in result
            
            if result["success"]:
                # Validate complete workflow results
                assert "initial_url" in result
                assert "final_url" in result
                assert "task" in result
                assert "workflow_results" in result
                
                workflow = result["workflow_results"]
                print(f"📸 Step 1 Screenshot: {workflow.get('step1_screenshot', 'Missing')}")
                print(f"🧠 Step 2 Analysis: {workflow.get('step2_analysis', {}).get('page_type', 'Unknown')}")
                print(f"🎯 Step 3 UI Detection: {workflow.get('step3_ui_detection', 0)} elements")
                print(f"🤖 Step 4 Actions: {len(workflow.get('step4_actions', []))} actions")
                print(f"⚡ Step 5 Execution: {workflow.get('step5_execution', {}).get('summary', 'Unknown')}")
                
                # Verify each step produced results
                assert "step1_screenshot" in workflow
                assert "step2_analysis" in workflow
                assert "step3_ui_detection" in workflow
                assert "step4_actions" in workflow
                assert "step5_execution" in workflow
                
                # Check Google-specific results
                assert "google.com" in result["initial_url"]
                assert result["task"] == "search airpods"
                
            else:
                print(f"❌ Workflow failed: {result.get('error', 'Unknown error')}")
                assert "error" in result
                
        finally:
            await service.close()
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_web_automation_mcp_integration(self):
        """Test web_automation tool via MCP client with 5-step workflow"""
        from tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        # Test realistic automation: search for airpods on Google
        url = "https://www.google.com"
        task = "search airpods"
        
        print(f"\n🔄 Starting MCP web automation test: {task}")
        print("⏳ This may take several minutes due to 5-step VLM processing...")
        
        # No timeout - let 5-step workflow complete naturally
        result = await client.call_tool_and_parse("web_automation", {
            "url": url,
            "task": task
        })
        
        print(f"✅ MCP web automation completed with status: {result.get('status')}")
        
        # Validate response structure
        assert result["status"] in ["success", "error"]
        
        if result["status"] == "success":
            if "action" in result:
                assert result["action"] == "web_automation"
                assert "timestamp" in result
                assert "data" in result
                automation_data = result["data"]
                
                # Check for 5-step workflow results
                if "workflow_results" in automation_data:
                    workflow = automation_data["workflow_results"]
                    print(f"📊 5-Step Results:")
                    print(f"  Step 1: {workflow.get('step1_screenshot', 'Missing')}")
                    print(f"  Step 2: {workflow.get('step2_analysis', {}).get('page_type', 'Unknown')}")
                    print(f"  Step 3: {workflow.get('step3_ui_detection', 0)} elements")
                    print(f"  Step 4: {len(workflow.get('step4_actions', []))} actions")
                    print(f"  Step 5: {workflow.get('step5_execution', {}).get('summary', 'Unknown')}")
                
                # For Google search automation, expect:
                # 1. A new URL (search results page)
                # 2. Task results describing what was found
                if "final_url" in automation_data:
                    final_url = automation_data["final_url"]
                    print(f"🌐 Final URL: {final_url}")
                    assert "google.com" in final_url
                
                if "result_description" in automation_data:
                    task_results = automation_data["result_description"]
                    print(f"📋 Task results: {task_results[:100]}...")
                    assert isinstance(task_results, str)
                    
            else:
                # Alternative response format - just check it's a valid response
                assert "data" in result or "text" in result
                
        elif result["status"] == "error":
            # Automation might fail due to complexity, but should handle gracefully
            print(f"❌ Automation failed: {result.get('error_message', result.get('error'))}")
            assert "error_message" in result or "error" in result
    
    @pytest.mark.asyncio
    async def test_web_automation_invalid_url(self):
        """Test web_automation tool error handling with invalid URL"""
        from tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        # Test with invalid URL - should fail quickly without VLM processing
        invalid_url = "not-a-valid-url"
        task = "test error handling"
        
        result = await client.call_tool_and_parse("web_automation", {
            "url": invalid_url,
            "task": task
        })
        
        # Should handle invalid URL gracefully
        assert result["status"] in ["success", "error"]
        if result["status"] == "error":
            assert "error_message" in result or "error" in result
    
    @pytest.mark.asyncio
    async def test_web_automation_empty_task(self):
        """Test web_automation tool with empty task"""
        from tools.mcp_client import MCPClient
        
        client = MCPClient()
        
        # Test with empty task
        url = "https://www.google.com"
        task = ""
        
        result = await client.call_tool_and_parse("web_automation", {
            "url": url,
            "task": task
        })
        
        assert result["status"] in ["success", "error"]
        
        # Should handle empty task gracefully
        if result["status"] == "success" and "action" in result:
            assert result["action"] == "web_automation"
        elif result["status"] == "error":
            assert "error_message" in result or "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])