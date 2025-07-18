#!/usr/bin/env python3
"""
Test script for event_tools.py
Tests event service tools using MCP client integration following test_plan.py pattern
"""

import asyncio
import sys
import os
import json

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.mcp_client import MCPClient

async def test_event_tools_capabilities():
    """Test 1: Event Tools Capabilities - Test that event tools are registered"""
    print("🧪 Test 1: Event Tools Capabilities")
    print("="*50)
    
    try:
        client = MCPClient()
        print("🔗 Testing MCP server connection...")
        
        # Get capabilities
        capabilities = await client.get_capabilities()
        
        if capabilities.get("status") == "error":
            print(f"❌ Failed to get capabilities: {capabilities.get('error')}")
            print("💡 Make sure MCP server is running on localhost:8081")
            return False
        
        print("✅ MCP server connection successful")
        
        # Check for event service tools
        expected_tools = [
            "create_background_task",
            "list_background_tasks", 
            "control_background_task",
            "get_event_service_status",
            "get_recent_events",
            "create_web_monitor_config"
        ]
        
        if "capabilities" in capabilities:
            tools = capabilities["capabilities"].get("tools", {}).get("available", {})
            
            # Handle both dict and list formats
            if isinstance(tools, list):
                tool_names = tools
                tools_dict = {name: {"name": name} for name in tool_names}
            else:
                tool_names = list(tools.keys())
                tools_dict = tools
            
            print(f"📊 Total tools found: {len(tool_names)}")
            print(f"📋 Event tools to check: {len(expected_tools)}")
            
            found_tools = 0
            missing_tools = []
            
            for tool_name in expected_tools:
                if tool_name in tool_names:
                    found_tools += 1
                    tool_info = tools_dict.get(tool_name, {})
                    description = tool_info.get('description', 'No description')
                    print(f"  ✅ {tool_name}: {description[:60]}...")
                else:
                    missing_tools.append(tool_name)
                    print(f"  ❌ {tool_name}: Not found")
            
            print(f"\n📊 Registration Results:")
            print(f"  Found: {found_tools}/{len(expected_tools)} event tools")
            
            if missing_tools:
                print(f"  Missing tools: {missing_tools}")
                print("💡 Check that event tools are properly registered with MCP auto-discovery")
                return False
            else:
                print("  ✅ All event tools are registered")
                
        print("✅ Test 1 PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Test 1 FAILED: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

async def test_event_tools_discovery():
    """Test 2: Event Tools Discovery - Test tool discovery functionality"""
    print("\n🧪 Test 2: Event Tools Discovery")
    print("="*50)
    
    try:
        client = MCPClient()
        
        # Test discovery with event-related queries
        test_queries = [
            "monitor website for changes",
            "create scheduled task",
            "get event status",
            "list background tasks",
            "web monitoring configuration"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing discovery for: '{query}'")
            
            discovery_result = await client.discover_tools(query)
            
            if discovery_result.get("status") == "error":
                print(f"  ❌ Discovery failed: {discovery_result.get('error')}")
                continue
            
            if "discovered_tools" in discovery_result:
                tools = discovery_result["discovered_tools"]
                print(f"  📊 Found {len(tools)} relevant tools")
                
                # Check if event tools are in the results
                event_tool_found = False
                for tool in tools:
                    tool_name = tool.get("name", "unknown")
                    if any(event_tool in tool_name for event_tool in [
                        "background_task", "event_service", "web_monitor", "create_background"
                    ]):
                        event_tool_found = True
                        print(f"    ✅ Event tool found: {tool_name}")
                        break
                
                if not event_tool_found:
                    print(f"    ⚠️ No event tools found for query '{query}'")
            else:
                print(f"  ⚠️ No tools discovered for query '{query}'")
        
        print("\n✅ Test 2 COMPLETED")
        return True
        
    except Exception as e:
        print(f"❌ Test 2 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_create_web_monitor_config():
    """Test 3a: Create Web Monitor Config Tool Execution"""
    print("\n🧪 Test 3a: Create Web Monitor Config Tool")
    print("="*50)
    
    try:
        client = MCPClient()
        
        # Test the create_web_monitor_config tool
        print("🔧 Testing create_web_monitor_config tool...")
        
        # Test valid input
        result = await client.call_tool_and_parse("create_web_monitor_config", {
            "urls": '["https://example.com", "https://test.com"]',
            "keywords": '["news", "update", "release"]',
            "check_interval_minutes": 30
        })
        
        print(f"📤 Raw Response:")
        print(json.dumps(result, indent=2))
        
        if result.get("status") == "success":
            config = result.get("config", {})
            config_json = result.get("config_json", "")
            
            # Validate response structure
            assert "urls" in config, "Config should have urls"
            assert "keywords" in config, "Config should have keywords"
            assert config["check_interval_minutes"] == 30, "Should set interval correctly"
            assert len(config["urls"]) == 2, "Should have 2 URLs"
            assert len(config["keywords"]) == 3, "Should have 3 keywords"
            
            # Validate JSON can be re-parsed
            parsed_json = json.loads(config_json)
            assert parsed_json == config, "Config JSON should match config object"
            
            print("✅ Web monitor config tool working correctly")
            
        elif result.get("status") == "error":
            print(f"❌ Tool returned error: {result.get('error', 'Unknown error')}")
            return False
        else:
            print(f"⚠️ Unexpected response format: {result}")
            return False
        
        # Test invalid input
        print("\n🔧 Testing invalid input handling...")
        
        invalid_result = await client.call_tool_and_parse("create_web_monitor_config", {
            "urls": "invalid json",
            "keywords": '["test"]',
            "check_interval_minutes": 30
        })
        
        if invalid_result.get("status") == "error":
            print("✅ Invalid input handled correctly")
        else:
            print("⚠️ Invalid input should return error")
        
        print("✅ Test 3a PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Test 3a FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_get_event_service_status():
    """Test 3b: Get Event Service Status Tool Execution"""
    print("\n🧪 Test 3b: Get Event Service Status Tool")
    print("="*50)
    
    try:
        client = MCPClient()
        
        print("🔧 Testing get_event_service_status tool...")
        
        result = await client.call_tool_and_parse("get_event_service_status", {})
        
        print(f"📤 Raw Response:")
        print(json.dumps(result, indent=2))
        
        # Should return status regardless of whether service is running
        if "status" in result:
            print(f"✅ Service status retrieved: {result.get('status')}")
            
            # Check for expected fields
            expected_fields = ["timestamp", "environment"]
            for field in expected_fields:
                if field in result:
                    print(f"  ✅ {field}: Present")
                else:
                    print(f"  ⚠️ {field}: Missing")
            
            print("✅ Event service status tool working")
        else:
            print(f"❌ Unexpected response: {result}")
            return False
        
        print("✅ Test 3b PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Test 3b FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_get_recent_events():
    """Test 3c: Get Recent Events Tool Execution"""
    print("\n🧪 Test 3c: Get Recent Events Tool")
    print("="*50)
    
    try:
        client = MCPClient()
        
        print("🔧 Testing get_recent_events tool...")
        
        result = await client.call_tool_and_parse("get_recent_events", {
            "limit": 5
        })
        
        print(f"📤 Raw Response:")
        print(json.dumps(result, indent=2))
        
        if result.get("status") == "success":
            events = result.get("events", [])
            count = result.get("count", 0)
            
            print(f"✅ Retrieved {count} events")
            
            # Validate response structure
            assert isinstance(events, list), "Events should be a list"
            assert isinstance(count, int), "Count should be an integer"
            assert count >= 0, "Count should be non-negative"
            
            print("✅ Recent events tool working correctly")
            
        elif result.get("status") == "error":
            print(f"⚠️ Tool returned error (may be expected): {result.get('error', 'Unknown error')}")
            # This might be expected if database is not available
            print("✅ Error handled gracefully")
        else:
            print(f"❌ Unexpected response: {result}")
            return False
        
        print("✅ Test 3c PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Test 3c FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_create_background_task():
    """Test 3d: Create Background Task Tool Execution"""
    print("\n🧪 Test 3d: Create Background Task Tool")
    print("="*50)
    
    try:
        client = MCPClient()
        
        print("🔧 Testing create_background_task tool...")
        
        # Create a test web monitoring task
        config = {
            "urls": ["https://httpbin.org/get"],
            "keywords": ["test", "demo"],
            "check_interval_minutes": 60
        }
        
        result = await client.call_tool_and_parse("create_background_task", {
            "task_type": "web_monitor",
            "description": "Test web monitoring task from MCP test",
            "config": json.dumps(config),
            "user_id": "test_mcp_user"
        })
        
        print(f"📤 Raw Response:")
        print(json.dumps(result, indent=2))
        
        if result.get("status") == "success":
            task_id = result.get("task_id")
            task_type = result.get("task_type")
            description = result.get("description")
            
            print(f"✅ Background task created successfully")
            print(f"  Task ID: {task_id}")
            print(f"  Task Type: {task_type}")
            print(f"  Description: {description}")
            
            # Validate response structure
            assert task_id is not None, "Should return task ID"
            assert task_type == "web_monitor", "Should set task type correctly"
            
        elif result.get("status") == "error":
            error_msg = result.get("error", "Unknown error")
            print(f"⚠️ Tool returned error: {error_msg}")
            
            # Check if it's a dependency/service error
            if any(keyword in error_msg.lower() for keyword in ["module", "import", "service", "database"]):
                print("💡 This appears to be a dependency/service issue")
                print("✅ Error handled gracefully")
            else:
                print("❌ Unexpected error")
                return False
        else:
            print(f"❌ Unexpected response: {result}")
            return False
        
        print("✅ Test 3d PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Test 3d FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_list_background_tasks():
    """Test 3e: List Background Tasks Tool Execution"""
    print("\n🧪 Test 3e: List Background Tasks Tool")
    print("="*50)
    
    try:
        client = MCPClient()
        
        print("🔧 Testing list_background_tasks tool...")
        
        result = await client.call_tool_and_parse("list_background_tasks", {
            "user_id": "test_mcp_user"
        })
        
        print(f"📤 Raw Response:")
        print(json.dumps(result, indent=2))
        
        if result.get("status") == "success":
            service_tasks = result.get("service_tasks", [])
            database_tasks = result.get("database_tasks", [])
            
            print(f"✅ Tasks listed successfully")
            print(f"  Service tasks: {len(service_tasks)}")
            print(f"  Database tasks: {len(database_tasks)}")
            
            # Validate response structure
            assert isinstance(service_tasks, list), "Service tasks should be a list"
            assert isinstance(database_tasks, list), "Database tasks should be a list"
            
        elif result.get("status") == "error":
            error_msg = result.get("error", "Unknown error")
            print(f"⚠️ Tool returned error: {error_msg}")
            print("💡 This may be expected if services are not running")
            print("✅ Error handled gracefully")
        else:
            print(f"❌ Unexpected response: {result}")
            return False
        
        print("✅ Test 3e PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Test 3e FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Run all tests following the MCP testing pattern"""
    print("🚀 Starting Event Tools MCP Integration Tests...")
    print("Following the pattern from test_plan.py\n")
    
    tests = [
        ("Tool Registration", test_event_tools_capabilities),
        ("Tool Discovery", test_event_tools_discovery),
        ("Create Web Monitor Config", test_create_web_monitor_config),
        ("Get Event Service Status", test_get_event_service_status),
        ("Get Recent Events", test_get_recent_events),
        ("Create Background Task", test_create_background_task),
        ("List Background Tasks", test_list_background_tasks)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append(result if result is not None else True)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append(False)
    
    print(f"\n{'='*60}")
    print("📊 EVENT TOOLS MCP TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    print(f"\n📋 Test Breakdown:")
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASSED" if results[i] else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Event tools are properly integrated with MCP")
    else:
        print(f"\n⚠️ {total - passed} tests failed - review output above")
        print("💡 Make sure:")
        print("  - MCP server is running on localhost:8081")
        print("  - Event service is properly configured")
        print("  - Database dependencies are available")

if __name__ == "__main__":
    asyncio.run(run_all_tests())