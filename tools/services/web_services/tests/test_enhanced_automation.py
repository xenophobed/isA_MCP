#!/usr/bin/env python3
"""
Test Enhanced Automation with ActionExecutor
"""

import asyncio
import time
import json
from pathlib import Path

from tools.services.web_services.services.web_automation_service import WebAutomationService
from tools.services.web_services.core.action_executor import get_action_executor


async def test_basic_actions():
    """Test basic action strategies"""
    print("🔧 Testing Enhanced Action System")
    print("=" * 60)
    
    service = WebAutomationService()
    executor = get_action_executor()
    
    try:
        # Start browser
        print("🚀 Starting browser...")
        start = time.time()
        await service._start_browser()
        print(f"✅ Browser started: {time.time() - start:.2f}s")
        
        # Navigate to test page
        print("🌐 Navigating to example.com...")
        start = time.time()
        await service.page.goto("https://example.com", wait_until="domcontentloaded")
        print(f"✅ Page loaded: {time.time() - start:.2f}s")
        
        # Test different action types - simpler actions for example.com
        test_actions = [
            {
                "action": "wait",
                "type": "delay",
                "delay": 1000
            },
            {
                "action": "scroll",
                "direction": "down",
                "amount": 300
            },
            {
                "action": "scroll",
                "direction": "up",
                "amount": 300
            },
            {
                "action": "click",
                "selector": "h1"  # Click on the h1 element
            },
            {
                "action": "screenshot",
                "path": "test_enhanced.png",
                "full_page": False
            }
        ]
        
        print(f"\n📋 Executing {len(test_actions)} test actions...")
        start = time.time()
        
        # Execute action sequence
        result = await executor.execute_action_sequence(
            page=service.page,
            actions=test_actions,
            delay_between_actions=500,
            stop_on_error=False
        )
        
        execution_time = time.time() - start
        
        # Report results
        print(f"\n📊 Execution Summary:")
        print(f"  Total actions: {result['total_actions']}")
        print(f"  Executed: {result['executed']}")
        print(f"  Successful: {result['successful']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Time: {execution_time:.2f}s")
        
        # Show individual results
        print(f"\n📝 Action Results:")
        for i, action_result in enumerate(result['results']):
            status = "✅" if action_result.get('success') else "❌"
            action_type = action_result.get('action_type', 'unknown')
            print(f"  {status} Action {i+1}: {action_type}")
            if not action_result.get('success'):
                print(f"     Error: {action_result.get('error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        await service.close()


async def test_complex_workflow():
    """Test complex automation workflow with multiple action types"""
    print("\n🚀 Testing Complex Workflow")
    print("=" * 60)
    
    service = WebAutomationService()
    executor = get_action_executor()
    
    try:
        await service._start_browser()
        
        # Simpler workflow that works with example.com
        workflow_actions = [
            {
                "action": "navigate",
                "url": "https://example.com",
                "wait_until": "domcontentloaded"
            },
            {
                "action": "wait",
                "type": "delay", 
                "delay": 1000
            },
            {
                "action": "hover",
                "selector": "h1",
                "duration": 500
            },
            {
                "action": "click",
                "selector": "p a",  # Click "More information..." link
            },
            {
                "action": "wait",
                "type": "delay",
                "delay": 2000
            },
            {
                "action": "navigate",
                "url": "https://example.com"  # Navigate back to example.com
            },
            {
                "action": "scroll",
                "direction": "down",
                "amount": 200
            },
            {
                "action": "screenshot",
                "path": "workflow_result.png"
            }
        ]
        
        print(f"📋 Executing workflow with {len(workflow_actions)} actions...")
        
        result = await executor.execute_action_sequence(
            page=service.page,
            actions=workflow_actions,
            delay_between_actions=1000
        )
        
        print(f"\n📊 Workflow Results:")
        print(f"  Success rate: {result['successful']}/{result['total_actions']}")
        
        if result['successful'] == result['total_actions']:
            print("  ✅ All actions completed successfully!")
        else:
            print(f"  ⚠️ {result['failed']} actions failed")
        
        return result
        
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        return None
    
    finally:
        await service.close()


async def test_action_strategies():
    """Test all available action strategies"""
    print("\n🧪 Testing Individual Action Strategies")
    print("=" * 60)
    
    executor = get_action_executor()
    available = executor.get_available_actions()
    
    print(f"📋 Available action types: {', '.join(available)}")
    
    # Get info for each action
    print("\n📚 Action Documentation:")
    for action_type in available:
        info = executor.get_action_info(action_type)
        print(f"\n  {action_type}:")
        if 'description' in info:
            print(f"    Description: {info['description']}")
        if 'required_params' in info:
            print(f"    Required: {info.get('required_params', [])}")
        if 'parameters' in info:
            for param, desc in info['parameters'].items():
                print(f"    - {param}: {desc}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 ENHANCED AUTOMATION SYSTEM TEST")
    print("=" * 60)
    
    # Test action info
    await test_action_strategies()
    
    # Test basic actions
    basic_result = await test_basic_actions()
    
    # Test complex workflow
    workflow_result = await test_complex_workflow()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    if basic_result and basic_result['successful'] > 0:
        print("✅ Basic actions test: PASSED")
    else:
        print("❌ Basic actions test: FAILED")
    
    if workflow_result and workflow_result['successful'] > 0:
        print("✅ Complex workflow test: PASSED")
    else:
        print("❌ Complex workflow test: FAILED")
    
    print("\n✨ Enhanced automation testing complete!")


if __name__ == "__main__":
    asyncio.run(main())