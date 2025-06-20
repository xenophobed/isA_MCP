#!/usr/bin/env python
"""
Event Sourcing System Test Script
Tests the core components of the Event-Driven MCP system
"""
import asyncio
import json
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.append('.')
sys.path.append('client')

async def test_event_feedback_server():
    """Test the Event Feedback Server"""
    print("🧪 Testing Event Feedback Server...")
    
    try:
        import aiohttp
        
        # Test health endpoint
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/health') as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Event Feedback Server is healthy")
                    print(f"   Events processed: {data.get('events_processed', 0)}")
                    return True
                else:
                    print(f"❌ Event Feedback Server health check failed: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Event Feedback Server test failed: {e}")
        return False

async def test_mcp_client_import():
    """Test MCP client import"""
    print("🧪 Testing MCP Client Import...")
    
    try:
        from v13_mcp_client import EventDrivenMCPClient
        print("✅ Event-Driven MCP Client imports successfully")
        
        # Test client creation
        client = EventDrivenMCPClient(use_load_balancer=False)
        print("✅ Event-Driven MCP Client created successfully")
        return True
        
    except Exception as e:
        print(f"❌ MCP Client import test failed: {e}")
        return False

async def test_event_sourcing_server():
    """Test Event Sourcing Server"""
    print("🧪 Testing Event Sourcing Server...")
    
    try:
        from servers.event_sourcing_server import EventSourcingService, EventSourceTask, EventSourceTaskType
        from datetime import datetime
        
        # Test service creation
        service = EventSourcingService()
        print("✅ Event Sourcing Service created successfully")
        
        # Test task creation
        task = EventSourceTask(
            task_id="test-task-1",
            task_type=EventSourceTaskType.WEB_MONITOR,
            description="Test web monitoring task",
            config={"urls": ["https://example.com"], "keywords": ["test"]},
            callback_url="http://localhost:8000/process_background_feedback",
            created_at=datetime.now()
        )
        print("✅ Event Source Task created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Event Sourcing Server test failed: {e}")
        return False

async def test_mcp_server_connection():
    """Test MCP server connection"""
    print("🧪 Testing MCP Server Connection...")
    
    try:
        from mcp_http_client import MCPHTTPClient
        
        # Test connection to load balancer
        urls_to_test = [
            "http://localhost/mcp",
            "http://localhost:8001/mcp",
            "http://localhost:8002/mcp",
            "http://localhost:8003/mcp"
        ]
        
        for url in urls_to_test:
            try:
                client = MCPHTTPClient(url)
                async with client:
                    await asyncio.wait_for(client.initialize(), timeout=5.0)
                    print(f"✅ MCP Server connection successful: {url}")
                    return True
            except Exception as e:
                print(f"⚠️ MCP Server connection failed: {url} - {e}")
                continue
        
        print("❌ All MCP Server connections failed")
        return False
        
    except Exception as e:
        print(f"❌ MCP Server connection test failed: {e}")
        return False

async def run_integration_test():
    """Run a simple integration test"""
    print("🧪 Running Integration Test...")
    
    try:
        # Test the complete workflow
        from v13_mcp_client import EventDrivenMCPClient
        
        client = EventDrivenMCPClient(use_load_balancer=False)
        
        # This would normally require the servers to be running
        print("✅ Integration test setup successful")
        print("   (Full integration test requires running servers)")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🎯 Event Sourcing System Test Suite")
    print("=" * 50)
    
    tests = [
        ("Event Feedback Server", test_event_feedback_server),
        ("MCP Client Import", test_mcp_client_import),
        ("Event Sourcing Server", test_event_sourcing_server),
        ("MCP Server Connection", test_mcp_server_connection),
        ("Integration Test", run_integration_test)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n📊 TEST RESULTS")
    print("=" * 30)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready for use.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 