#!/usr/bin/env python3
"""
Complete Event Service Workflow Test
Tests the full end-to-end joke generation workflow with self-contained callback
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from tools.mcp_client import MCPClient

async def test_complete_joke_workflow():
    """Test the complete joke generation workflow"""
    print("🎭 Testing Complete Joke Generation Workflow")
    print("="*60)
    print("This test creates a scheduled task that generates a joke every 1 minute")
    print("and sends callbacks to our own event server for verification.\n")
    
    try:
        client = MCPClient()
        
        # Step 1: Create scheduled joke task
        print("📝 Step 1: Creating scheduled joke task...")
        
        # Use our own event server as callback for testing
        callback_url = "http://localhost:8101/process_background_feedback"
        
        # Create config for joke generation every 1 minute
        config = {
            "type": "interval",
            "minutes": 1,
            "action": "generate_joke", 
            "target_user": "user123",
            "joke_type": "programming"
        }
        
        task_result = await client.call_tool_and_parse("create_background_task", {
            "task_type": "schedule",
            "description": "Generate a programming joke for user123 every 1 minute",
            "config": config,  # Pass as dict (our fixed validation handles this)
            "callback_url": callback_url,
            "user_id": "user123"
        })
        
        print(f"📤 Task Creation Response:")
        print(json.dumps(task_result, indent=2))
        
        if task_result.get("status") != "success":
            print("❌ Failed to create task")
            return False
            
        task_id = task_result.get("task_id")
        print(f"✅ Task created successfully with ID: {task_id}")
        
        # Step 2: Verify task is listed and active
        print(f"\n📋 Step 2: Verifying task is active...")
        
        list_result = await client.call_tool_and_parse("list_background_tasks", {
            "user_id": "user123"
        })
        
        service_tasks = list_result.get("service_tasks", [])
        our_task = None
        for task in service_tasks:
            if task.get("task_id") == task_id:
                our_task = task
                break
        
        if not our_task:
            print("❌ Task not found in active tasks")
            return False
            
        print(f"✅ Task found and active:")
        print(f"  Status: {our_task.get('status')}")
        print(f"  Type: {our_task.get('task_type')}")
        print(f"  Description: {our_task.get('description')}")
        
        # Step 3: Wait and monitor for events
        print(f"\n⏱️  Step 3: Monitoring for events (waiting up to 3 minutes)...")
        print("This will check for scheduled events every 15 seconds...")
        
        events_found = []
        max_wait_time = 180  # 3 minutes
        check_interval = 15  # Check every 15 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Check event server for recent events
            print(f"\n🔍 Checking for events... (elapsed: {int(time.time() - start_time)}s)")
            
            # Check both our MCP events and the event server
            recent_events = await client.call_tool_and_parse("get_recent_events", {
                "limit": 10,
                "task_id": task_id
            })
            
            events = recent_events.get("events", [])
            if events:
                print(f"📥 Found {len(events)} events for our task!")
                for event in events:
                    event_type = event.get("event_type", "unknown")
                    timestamp = event.get("timestamp", "unknown")
                    print(f"  - {event_type} at {timestamp}")
                events_found.extend(events)
            
            # Also check the event server directly via HTTP
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:8101/events/recent?limit=5") as response:
                        if response.status == 200:
                            server_data = await response.json()
                            memory_events = server_data.get("memory_events", [])
                            db_events = server_data.get("database_events", [])
                            
                            # Look for events related to our task
                            relevant_events = []
                            for event in memory_events + db_events:
                                if event.get("task_id") == task_id:
                                    relevant_events.append(event)
                            
                            if relevant_events:
                                print(f"🎯 Event server has {len(relevant_events)} relevant events!")
                                for event in relevant_events:
                                    event_type = event.get("event_type", "unknown")
                                    print(f"  - Server event: {event_type}")
                            
            except Exception as e:
                print(f"⚠️ Could not check event server directly: {e}")
            
            # If we found events, we can analyze them
            if events_found:
                print(f"\n🎉 SUCCESS! Found {len(events_found)} events from our scheduled task!")
                break
            
            print(f"⏳ No events yet, waiting {check_interval} seconds...")
            await asyncio.sleep(check_interval)
        
        # Step 4: Analyze results
        print(f"\n📊 Step 4: Analysis")
        if events_found:
            print("✅ WORKFLOW TEST SUCCESSFUL!")
            print(f"   - Task created and scheduled correctly")
            print(f"   - Event sourcing service is monitoring the schedule")
            print(f"   - Events are being generated as expected")
            print(f"   - Found {len(events_found)} events total")
            
            # Show event details
            for i, event in enumerate(events_found[:3]):  # Show first 3
                print(f"\n   Event {i+1}:")
                print(f"     Type: {event.get('event_type', 'unknown')}")
                print(f"     Time: {event.get('timestamp', 'unknown')}")
                if 'data' in event:
                    data = event['data']
                    print(f"     Action: {data.get('action', 'unknown')}")
                    print(f"     User: {data.get('target_user', 'unknown')}")
        else:
            print("⚠️  No events detected during monitoring period")
            print("   This could mean:")
            print("   - The 1-minute interval hasn't triggered yet")
            print("   - The event server is not receiving callbacks")
            print("   - The callback URL configuration needs adjustment")
            
        # Step 5: Cleanup - pause the task
        print(f"\n🧹 Step 5: Cleanup - Pausing task to stop further events...")
        
        control_result = await client.call_tool_and_parse("control_background_task", {
            "task_id": task_id,
            "action": "pause",
            "user_id": "user123"
        })
        
        if control_result.get("status") == "success":
            print("✅ Task paused successfully")
        else:
            print("⚠️ Could not pause task")
            
        # Final status check
        final_status = await client.call_tool_and_parse("get_event_service_status", {})
        service_stats = final_status.get("service_status", {})
        
        print(f"\n📈 Final Service Status:")
        print(f"   Total tasks: {service_stats.get('total_tasks', 0)}")
        print(f"   Active tasks: {service_stats.get('active_tasks', 0)}")
        print(f"   Paused tasks: {service_stats.get('paused_tasks', 0)}")
        
        return len(events_found) > 0
        
    except Exception as e:
        print(f"❌ Workflow test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_event_server_callback():
    """Test that our event server can receive and process callbacks"""
    print("\n🔧 Testing Event Server Callback Reception")
    print("="*50)
    
    try:
        # Send a test callback directly to our event server
        import aiohttp
        
        test_event = {
            "task_id": "test-callback-123",
            "event_type": "scheduled_trigger",
            "data": {
                "action": "generate_joke",
                "target_user": "test_user",
                "trigger_time": datetime.now().isoformat(),
                "description": "Test callback event"
            },
            "timestamp": datetime.now().isoformat(),
            "priority": 2
        }
        
        print("📤 Sending test callback to event server...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8101/process_background_feedback",
                json=test_event,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print("✅ Event server received callback successfully!")
                    print(f"   Response: {result.get('status', 'unknown')}")
                    return True
                else:
                    print(f"❌ Event server returned status {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Failed to test callback: {e}")
        return False

async def run_complete_workflow_test():
    """Run the complete workflow test suite"""
    print("🚀 Starting Complete Event Service Workflow Test")
    print("="*60)
    print("This test verifies the entire joke generation pipeline:")
    print("1. Create scheduled task via MCP")
    print("2. Monitor event generation")  
    print("3. Verify callback processing")
    print("4. Clean up resources")
    print("="*60)
    
    # First test callback reception
    callback_test = await test_event_server_callback()
    
    # Then test complete workflow
    workflow_test = await test_complete_joke_workflow()
    
    print(f"\n{'='*60}")
    print("📊 COMPLETE WORKFLOW TEST SUMMARY")
    print(f"{'='*60}")
    
    tests = [
        ("Event Server Callback", callback_test),
        ("Complete Joke Workflow", workflow_test)
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    print(f"\n📋 Test Breakdown:")
    for test_name, result in tests:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    if passed == total:
        print("\n🎉 ALL WORKFLOW TESTS PASSED!")
        print("✅ Complete event sourcing pipeline is functional")
        print("✅ Ready for production joke generation!")
    else:
        print(f"\n⚠️ {total - passed} tests failed")
        print("💡 Check that:")
        print("  - MCP server is running on localhost:8081")
        print("  - Event server is running on localhost:8101") 
        print("  - Event service is properly configured")

if __name__ == "__main__":
    asyncio.run(run_complete_workflow_test())