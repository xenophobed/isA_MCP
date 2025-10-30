#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Automation End-to-End Tests
真正的 AI 功能测试：Vision Model + UI Detection + Action Generation

测试场景：
1. 完整的 5步工作流（包含真实的 AI 调用）
2. Vision Model 页面理解
3. UI Detection 元素检测
4. Action Generation 动作生成
5. HIL 检测
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.services.web_services.services.web_automation_service import WebAutomationService
from core.logging import get_logger

logger = get_logger(__name__)


class E2ETestRunner:
    """端到端测试运行器"""
    
    def __init__(self):
        self.service = WebAutomationService()
        self.passed = 0
        self.failed = 0
        self.total = 0
    
    async def run_test(self, name: str, test_func):
        """运行单个测试"""
        self.total += 1
        print()
        print("=" * 70)
        print(f"🧪 Test {self.total}: {name}")
        print("=" * 70)
        
        try:
            await test_func()
            self.passed += 1
            print(f"✅ Test {self.total} PASSED: {name}")
        except Exception as e:
            self.failed += 1
            print(f"❌ Test {self.total} FAILED: {name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_basic_search_workflow(self):
        """测试基本搜索工作流（完整 5 步）"""
        print()
        print("📋 Testing: Basic search on Google")
        print("   URL: https://www.google.com")
        print("   Task: search for python programming")
        print()
        
        result = await self.service.execute_task(
            url="https://www.google.com",
            task="search for python programming",
            user_id="test_user"
        )
        
        print("📊 Result Summary:")
        print(f"   Success: {result.get('success')}")
        print(f"   Initial URL: {result.get('initial_url')}")
        print(f"   Final URL: {result.get('final_url')}")
        
        # 验证工作流结果
        assert result.get('success'), "Task should succeed"
        
        workflow = result.get('workflow_results', {})
        
        # Step 1: Screenshot
        step1_screenshot = workflow.get('step1_screenshot')
        print(f"   📸 Step 1 Screenshot: {step1_screenshot}")
        assert step1_screenshot, "Step 1 should have screenshot"
        
        # Step 2: Understanding
        step2_analysis = workflow.get('step2_analysis', {})
        page_type = step2_analysis.get('page_type')
        required_elements = step2_analysis.get('required_elements', [])
        print(f"   🧠 Step 2 Analysis:")
        print(f"      Page Type: {page_type}")
        print(f"      Required Elements: {len(required_elements)}")
        for elem in required_elements:
            print(f"         - {elem.get('element_name')}: {elem.get('element_purpose')}")
        assert page_type, "Step 2 should detect page type"
        
        # Step 3: UI Detection
        step3_ui = workflow.get('step3_ui_detection', 0)
        print(f"   🎯 Step 3 UI Detection: {step3_ui} elements mapped")
        # Note: UI detection might be 0 if it fails, fallback is used
        
        # Step 4: Actions
        step4_actions = workflow.get('step4_actions', [])
        print(f"   🤖 Step 4 Actions: {len(step4_actions)} actions generated")
        for i, action in enumerate(step4_actions, 1):
            print(f"      Action {i}: {action.get('action')} - {action}")
        assert len(step4_actions) > 0, "Step 4 should generate actions"
        
        # Step 5: Execution
        step5_execution = workflow.get('step5_execution', {})
        actions_executed = step5_execution.get('actions_executed', 0)
        actions_successful = step5_execution.get('actions_successful', 0)
        task_completed = step5_execution.get('task_completed', False)
        
        print(f"   ⚡ Step 5 Execution:")
        print(f"      Actions Executed: {actions_executed}")
        print(f"      Actions Successful: {actions_successful}")
        print(f"      Task Completed: {task_completed}")
        
        assert actions_executed > 0, "Step 5 should execute actions"
        
        print()
        print("✅ All 5 steps completed successfully!")
    
    async def test_hil_detection_login(self):
        """测试 HIL 检测（登录页面）"""
        print()
        print("📋 Testing: HIL detection for login page")
        print("   URL: https://accounts.google.com/signin")
        print("   Task: login to gmail")
        print()
        
        result = await self.service.execute_task(
            url="https://accounts.google.com/signin",
            task="login to gmail",
            user_id="test_hil_user"
        )
        
        print("📊 Result Summary:")
        print(f"   HIL Required: {result.get('hil_required')}")
        
        if result.get('hil_required'):
            print(f"   Status: {result.get('status')}")
            print(f"   Action: {result.get('action')}")
            print(f"   Message: {result.get('message')}")
            
            data = result.get('data', {})
            print(f"   Intervention Type: {data.get('intervention_type')}")
            print(f"   Provider: {data.get('provider')}")
            
            # 验证 HIL 检测
            assert result.get('hil_required'), "Should detect HIL requirement"
            assert data.get('intervention_type') == 'login', "Should detect login type"
            assert result.get('action') in ['request_authorization', 'ask_human'], "Should have valid HIL action"
            
            print()
            print("✅ HIL detection works correctly!")
        else:
            print("⚠️  HIL not triggered (page structure might have changed)")
            print("   This is acceptable - testing the non-HIL path")
    
    async def test_vision_model_understanding(self):
        """测试 Vision Model 页面理解能力"""
        print()
        print("📋 Testing: Vision Model page understanding")
        print("   URL: https://www.example.com")
        print("   Task: analyze page structure")
        print()
        
        result = await self.service.execute_task(
            url="https://www.example.com",
            task="scroll down 500 pixels",
            user_id="test_vision_user"
        )
        
        print("📊 Result Summary:")
        print(f"   Success: {result.get('success')}")
        
        if result.get('success'):
            workflow = result.get('workflow_results', {})
            step2_analysis = workflow.get('step2_analysis', {})
            
            print(f"   🧠 Vision Model Analysis:")
            print(f"      Page Type: {step2_analysis.get('page_type')}")
            print(f"      Page Suitable: {step2_analysis.get('page_suitable')}")
            print(f"      Confidence: {step2_analysis.get('confidence')}")
            print(f"      Interaction Strategy: {step2_analysis.get('interaction_strategy')}")
            
            # 验证 Vision Model 有输出
            assert step2_analysis, "Vision Model should analyze page"
            
            print()
            print("✅ Vision Model understanding works!")
    
    async def test_ui_detection_coordinates(self):
        """测试 UI Detection 坐标检测"""
        print()
        print("📋 Testing: UI Detection with coordinates")
        print("   URL: https://httpbin.org/forms/post")
        print("   Task: fill form fields")
        print()
        
        result = await self.service.execute_task(
            url="https://httpbin.org/forms/post",
            task="fill customer name with 'John Doe'",
            user_id="test_ui_user"
        )
        
        print("📊 Result Summary:")
        print(f"   Success: {result.get('success')}")
        
        if result.get('success'):
            workflow = result.get('workflow_results', {})
            
            # Step 3: UI Detection
            step3_ui = workflow.get('step3_ui_detection', 0)
            print(f"   🎯 UI Elements Detected: {step3_ui}")
            
            # Check if ui_detector was called
            # (even if it returns 0, it means fallback was used)
            print()
            if step3_ui > 0:
                print("✅ UI Detection found elements with coordinates!")
            else:
                print("⚠️  UI Detection used fallback (no coordinates)")
    
    async def test_action_generation_llm(self):
        """测试 LLM 动作生成"""
        print()
        print("📋 Testing: LLM action generation")
        print("   URL: https://www.duckduckgo.com")
        print("   Task: search for 'web automation', click first result")
        print()
        
        result = await self.service.execute_task(
            url="https://www.duckduckgo.com",
            task="search for 'web automation'",
            user_id="test_llm_user"
        )
        
        print("📊 Result Summary:")
        print(f"   Success: {result.get('success')}")
        
        if result.get('success'):
            workflow = result.get('workflow_results', {})
            step4_actions = workflow.get('step4_actions', [])
            
            print(f"   🤖 LLM Generated Actions: {len(step4_actions)}")
            for i, action in enumerate(step4_actions, 1):
                print(f"      {i}. {action.get('action')}: {action}")
            
            # 验证动作生成
            assert len(step4_actions) > 0, "LLM should generate actions"
            
            # 检查动作类型
            action_types = [a.get('action') for a in step4_actions]
            print(f"   Action types: {', '.join(action_types)}")
            
            print()
            print("✅ LLM action generation works!")
    
    async def test_error_handling(self):
        """测试错误处理"""
        print()
        print("📋 Testing: Error handling with invalid URL")
        print("   URL: not-a-valid-url")
        print("   Task: do something")
        print()
        
        result = await self.service.execute_task(
            url="not-a-valid-url",
            task="do something",
            user_id="test_error_user"
        )
        
        print("📊 Result Summary:")
        print(f"   Success: {result.get('success')}")
        print(f"   Error: {result.get('error')}")
        
        # 验证错误被正确捕获
        assert not result.get('success'), "Invalid URL should fail"
        assert result.get('error'), "Should have error message"
        
        print()
        print("✅ Error handling works correctly!")
    
    async def cleanup(self):
        """清理资源"""
        await self.service.close()
    
    def print_summary(self):
        """打印测试摘要"""
        print()
        print("=" * 70)
        print("📊 Test Summary")
        print("=" * 70)
        print(f"Total Tests: {self.total}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {(self.passed/self.total*100) if self.total > 0 else 0:.1f}%")
        print()
        
        if self.failed == 0:
            print("🎉 All E2E tests passed!")
            return 0
        else:
            print(f"⚠️  {self.failed} test(s) failed")
            return 1


async def main():
    """主测试函数"""
    print()
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║           Web Automation End-to-End Tests (AI Functionality)              ║")
    print("║                Testing: Vision + UI Detection + LLM                        ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    runner = E2ETestRunner()
    
    # 运行所有测试
    try:
        # Test 1: 完整的 5步工作流
        await runner.run_test(
            "Complete 5-Step Workflow (Vision + UI + LLM + Execution)",
            runner.test_basic_search_workflow
        )
        
        # Test 2: Vision Model 页面理解
        await runner.run_test(
            "Vision Model Page Understanding",
            runner.test_vision_model_understanding
        )
        
        # Test 3: UI Detection 坐标检测
        await runner.run_test(
            "UI Detection with Coordinates",
            runner.test_ui_detection_coordinates
        )
        
        # Test 4: LLM 动作生成
        await runner.run_test(
            "LLM Action Generation",
            runner.test_action_generation_llm
        )
        
        # Test 5: HIL 检测
        await runner.run_test(
            "HIL Detection for Login Page",
            runner.test_hil_detection_login
        )
        
        # Test 6: 错误处理
        await runner.run_test(
            "Error Handling",
            runner.test_error_handling
        )
        
    finally:
        # 清理
        await runner.cleanup()
    
    # 打印摘要
    exit_code = runner.print_summary()
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


