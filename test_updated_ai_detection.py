#!/usr/bin/env python3
"""
Test Updated AI Detection with New ISA API
"""
import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.web_tools import register_web_tools
from core.logging import get_logger

logger = get_logger(__name__)

class MockMCP:
    """Mock MCP server for testing"""
    def __init__(self):
        self.tools = {}
    
    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator
    
    async def call_tool(self, tool_name, **kwargs):
        if tool_name in self.tools:
            return await self.tools[tool_name](**kwargs)
        else:
            raise ValueError(f"Tool {tool_name} not found")

async def test_simple_element_detection():
    """Test basic element detection on a simple site"""
    print("🧠 Testing Updated AI Element Detection")
    print("=" * 50)
    
    try:
        # Import required services directly
        from tools.services.web_services.core.web_service_manager import get_web_service_manager
        
        # Initialize web service manager
        web_manager = await get_web_service_manager()
        browser_manager = web_manager.get_browser_manager()
        session_manager = web_manager.get_session_manager()
        element_detector = web_manager.get_service('element_detector')
        
        # Initialize browser
        if not browser_manager.initialized:
            print("🔧 Initializing browser for AI detection test...")
            await browser_manager.initialize()
        
        # Test on Google (simple and reliable)
        session_id = "ai_detection_test"
        page = await session_manager.get_or_create_session(session_id, "stealth")
        
        print("🌐 Testing AI detection on Google...")
        await page.goto("https://www.google.com", wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        
        # Test search element detection with new ISA API
        print("🎯 Detecting search elements using updated ISA API...")
        search_elements = await element_detector.detect_search_elements(
            page, 
            target_elements=['search_input', 'search_button']
        )
        
        print(f"✅ AI Detection Results ({len(search_elements)} elements found):")
        for element_name, result in search_elements.items():
            print(f"   {element_name}:")
            print(f"     Position: ({result.x}, {result.y})")
            print(f"     Strategy: {result.strategy.value}")
            print(f"     Confidence: {result.confidence:.3f}")
            print(f"     Description: {result.description}")
            if 'isa_type' in result.metadata:
                print(f"     ISA Type: {result.metadata['isa_type']}")
            if 'content' in result.metadata:
                print(f"     Content: {result.metadata['content']}")
            print()
        
        return len(search_elements) > 0
        
    except Exception as e:
        print(f"❌ AI detection test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def test_deep_search_with_ai():
    """Test deep search using the updated AI detection"""
    print("\n🚀 Testing Deep Search with Updated AI Detection")
    print("=" * 55)
    
    mcp = MockMCP()
    register_web_tools(mcp)
    
    try:
        print("Executing deep search with updated AI detection...")
        
        result = await mcp.call_tool(
            "web_search",
            query="AirPods Pro comparison",
            mode="deep",
            max_results=4,  # Keep small for testing
            providers='["brave"]',
            user_id="ai_detection_test"
        )
        
        import json
        data = json.loads(result)
        print(f"\nStatus: {data['status']}")
        print(f"Mode: {data['mode']}")
        
        if data['status'] == 'success':
            print("\n✅ Deep Search with AI Detection SUCCESS!")
            
            # Check workflow steps
            workflow = data.get('workflow_steps', {})
            print(f"\n📋 Workflow Results:")
            for step, result_info in workflow.items():
                print(f"   {step}: {result_info}")
            
            # Check automation details
            automation = data['data'].get('automation_details', {})
            if automation:
                print(f"\n🤖 AI Automation Details:")
                print(f"   Sites automated: {automation.get('sites_automated', [])}")
                print(f"   Element detection: {automation.get('element_detection_used', False)}")
                print(f"   Intelligent navigation: {automation.get('intelligent_navigation', False)}")
            
            return True
        else:
            print(f"❌ Deep Search FAILED: {data.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Deep Search with AI FAILED: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Run AI detection tests"""
    print("🧪 Updated AI Detection Testing Suite")
    print("Testing new ISA OmniParser UI detection integration")
    print("=" * 60)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    # Test 1: Basic AI Element Detection
    result1 = await test_simple_element_detection()
    results.append(("AI Element Detection", result1))
    
    # Test 2: Deep Search with AI (if element detection works)
    if result1:
        print("AI detection works, testing full deep search...")
        result2 = await test_deep_search_with_ai()
        results.append(("Deep Search with AI", result2))
    else:
        print("Skipping deep search due to AI detection failure")
        results.append(("Deep Search with AI", False))
    
    # Results summary
    print("\n" + "=" * 60)
    print("📊 AI DETECTION TEST RESULTS")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name:30}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 UPDATED AI DETECTION IS WORKING!")
        print("✅ ISA OmniParser UI detection integration successful")
        print("✅ Deep search with AI automation functional")
        print("✅ Ready for Reddit/Twitter automation testing")
    else:
        print("⚠️  AI DETECTION COMPONENTS NEED ATTENTION")
        print("📋 Check ISA client configuration and model access")
    
    return all_passed

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)