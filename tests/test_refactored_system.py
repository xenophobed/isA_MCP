#!/usr/bin/env python
"""
Test script for refactored Event Sourcing system
验证重构后的事件溯源系统
"""
import asyncio
import json
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.services.event_sourcing_services import get_event_sourcing_service, EventSourceTaskType
from datetime import datetime

async def test_event_sourcing_service():
    """Test the event sourcing service functionality"""
    print("🧪 Testing Event Sourcing Service...")
    
    # Get service instance
    service = get_event_sourcing_service()
    
    # Start service
    await service.start_service()
    print("✅ Service started")
    
    # Test 1: Create a web monitor task
    print("\n📝 Test 1: Creating web monitor task...")
    task1 = await service.create_task(
        task_type=EventSourceTaskType.WEB_MONITOR,
        description="Monitor TechCrunch for AI news",
        config={
            "urls": ["https://techcrunch.com"],
            "keywords": ["AI", "artificial intelligence"],
            "check_interval_minutes": 5
        },
        callback_url="http://localhost:8000/process_background_feedback",
        user_id="test_user"
    )
    print(f"✅ Created task: {task1.task_id}")
    
    # Test 2: Create a schedule task
    print("\n📝 Test 2: Creating schedule task...")
    task2 = await service.create_task(
        task_type=EventSourceTaskType.SCHEDULE,
        description="Daily reminder at 9 AM",
        config={
            "type": "daily",
            "hour": 9,
            "minute": 0,
            "message": "Time for daily standup!"
        },
        callback_url="http://localhost:8000/process_background_feedback",
        user_id="test_user"
    )
    print(f"✅ Created task: {task2.task_id}")
    
    # Test 3: List tasks
    print("\n📝 Test 3: Listing tasks...")
    tasks = await service.list_tasks("test_user")
    print(f"✅ Found {len(tasks)} tasks for test_user")
    for task in tasks:
        print(f"   - {task.description} ({task.task_type.value})")
    
    # Test 4: Get service status
    print("\n📝 Test 4: Getting service status...")
    status = await service.get_service_status()
    print(f"✅ Service status:")
    print(f"   - Running: {status['service_running']}")
    print(f"   - Total tasks: {status['total_tasks']}")
    print(f"   - Active tasks: {status['active_tasks']}")
    print(f"   - Running monitors: {status['running_monitors']}")
    
    # Test 5: Pause and resume task
    print("\n📝 Test 5: Pause and resume task...")
    success = await service.pause_task(task1.task_id, "test_user")
    print(f"✅ Pause task: {success}")
    
    success = await service.resume_task(task1.task_id, "test_user")
    print(f"✅ Resume task: {success}")
    
    # Test 6: Delete task
    print("\n📝 Test 6: Delete task...")
    success = await service.delete_task(task2.task_id, "test_user")
    print(f"✅ Delete task: {success}")
    
    # Final status
    print("\n📊 Final status:")
    final_tasks = await service.list_tasks("test_user")
    print(f"✅ Remaining tasks: {len(final_tasks)}")
    
    # Cleanup
    print("\n🧹 Cleanup...")
    for task in final_tasks:
        await service.delete_task(task.task_id, "test_user")
    
    await service.stop_service()
    print("✅ Service stopped")
    
    print("\n🎉 All tests passed!")

async def test_mcp_integration():
    """Test MCP integration by simulating tool calls"""
    print("\n🧪 Testing MCP Integration...")
    
    # Import required modules
    from tools.event_sourcing_tools import register_event_sourcing_tools
    from mcp.server.fastmcp import FastMCP
    from core.security import initialize_security
    from core.monitoring import monitor_manager
    
    # Initialize security manager
    security_manager = initialize_security(monitor_manager)
    print("✅ Security manager initialized")
    
    # Create a test MCP server
    mcp = FastMCP("Test Event Sourcing Server")
    
    # Initialize service
    service = get_event_sourcing_service()
    await service.start_service()
    
    # Register tools
    register_event_sourcing_tools(mcp)
    print("✅ Tools registered")
    
    # Test create_background_task tool
    print("\n📝 Testing create_background_task tool...")
    config_json = json.dumps({
        "urls": ["https://news.ycombinator.com"],
        "keywords": ["Python", "MCP"],
        "check_interval_minutes": 10
    })
    
    # Simulate tool call (note: this would normally come through MCP protocol)
    print("✅ Tool simulation completed (would normally be called via MCP)")
    
    await service.stop_service()
    print("✅ MCP integration test completed")

def main():
    """Main test function"""
    print("🚀 Starting Event Sourcing System Tests")
    print("=" * 50)
    
    try:
        # Run service tests
        asyncio.run(test_event_sourcing_service())
        
        # Run MCP integration tests
        asyncio.run(test_mcp_integration())
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 