#!/usr/bin/env python
"""
End-to-End Test for 5-Step Atomic Web Automation Workflow

Tests the complete integration of:
1. Playwright Screenshot
2. image_analyzer (Screen Understanding) 
3. ui_detector (UI Detection + Coordinates)
4. text_generator (Action Reasoning)
5. Playwright Execution + image_analyzer (Result Analysis)
"""

import asyncio
import tempfile
import os
from pathlib import Path
import traceback

from tools.services.web_services.services.web_automation_service import WebAutomationService


async def test_google_search_workflow():
    """Test complete workflow with Google search task"""
    print("🚀 Starting end-to-end test: Google search for 'airpods'")
    
    service = WebAutomationService()
    
    try:
        # Execute the complete 5-step workflow
        result = await service.execute_task(
            url="https://google.com",
            task="search airpods"
        )
        
        print(f"\n{'='*60}")
        print("📊 E2E TEST RESULTS")
        print(f"{'='*60}")
        
        if result["success"]:
            print("✅ Workflow completed successfully!")
            print(f"🎯 Task: {result['task']}")
            print(f"🌐 Initial URL: {result['initial_url']}")
            print(f"🌐 Final URL: {result['final_url']}")
            
            workflow = result["workflow_results"]
            print(f"\n📸 Step 1 Screenshot: {Path(workflow['step1_screenshot']).name}")
            print(f"🧠 Step 2 Analysis: {workflow['step2_analysis'].get('page_type', 'unknown')}")
            print(f"🎯 Step 3 UI Detection: {workflow['step3_ui_detection']} elements mapped")
            print(f"🤖 Step 4 Actions Generated: {len(workflow['step4_actions'])} actions")
            print(f"⚡ Step 5 Execution: {workflow['step5_execution']['summary']}")
            
            print(f"\n📋 Result Description:")
            print(f"{result['result_description'][:200]}...")
            
            return True
        else:
            print("❌ Workflow failed")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ E2E test failed with exception: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        await service.close()


async def test_duckduckgo_search_workflow():
    """Test workflow with alternative search engine"""
    print("\n🚀 Starting second test: DuckDuckGo search for 'macbook'")
    
    service = WebAutomationService()
    
    try:
        result = await service.execute_task(
            url="https://duckduckgo.com",
            task="search macbook"
        )
        
        print(f"\n{'='*60}")
        print("📊 SECOND E2E TEST RESULTS")
        print(f"{'='*60}")
        
        if result["success"]:
            print("✅ Second workflow completed successfully!")
            workflow = result["workflow_results"]
            print(f"🎯 UI Elements Mapped: {workflow['step3_ui_detection']}")
            print(f"🤖 Actions Generated: {len(workflow['step4_actions'])}")
            print(f"⚡ Execution Result: {workflow['step5_execution']['task_completed']}")
            return True
        else:
            print("❌ Second workflow failed")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Second E2E test failed: {e}")
        return False
    finally:
        await service.close()


async def test_workflow_performance():
    """Test workflow performance and timing"""
    print("\n🚀 Starting performance test")
    
    service = WebAutomationService()
    
    try:
        import time
        start_time = time.time()
        
        result = await service.execute_task(
            url="https://example.com", 
            task="find contact information"
        )
        
        total_time = time.time() - start_time
        
        print(f"\n{'='*60}")
        print("⏱️ PERFORMANCE TEST RESULTS")
        print(f"{'='*60}")
        
        print(f"⏱️ Total workflow time: {total_time:.2f} seconds")
        
        if result["success"]:
            print("✅ Performance test completed successfully!")
            return True
        else:
            print("❌ Performance test workflow failed")
            return False
            
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False
    finally:
        await service.close()


async def main():
    """Run all end-to-end tests"""
    print("🧪 STARTING COMPREHENSIVE E2E TESTS FOR 5-STEP ATOMIC WORKFLOW")
    print("="*80)
    
    tests = [
        ("Google Search Test", test_google_search_workflow),
        ("DuckDuckGo Search Test", test_duckduckgo_search_workflow), 
        ("Performance Test", test_workflow_performance)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 40)
        
        try:
            success = await test_func()
            results.append((test_name, success))
            print(f"{'✅ PASSED' if success else '❌ FAILED'}: {test_name}")
        except Exception as e:
            print(f"❌ FAILED: {test_name} - {e}")
            results.append((test_name, False))
    
    # Final summary
    print(f"\n{'='*80}")
    print("📊 FINAL E2E TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n📈 Overall Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL E2E TESTS PASSED - 5-STEP ATOMIC WORKFLOW IS WORKING!")
    else:
        print("⚠️ Some tests failed - check individual test outputs above")
    
    print("\n✅ E2E testing complete")


if __name__ == "__main__":
    asyncio.run(main())