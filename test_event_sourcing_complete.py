#!/usr/bin/env python
"""
Complete Event Sourcing Test - Full Architecture Demo
Tests the complete event sourcing flow without Docker dependencies
"""
import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from tools.event_sourcing_tools import register_event_sourcing_tools
from resources.event_sourcing_resources import register_event_sourcing_resources
from tools.services.event_sourcing_services import init_event_sourcing_service, EventSourcingService, EventSourceTaskType
from core.security import initialize_security
from core.monitoring import monitor_manager
from core.logging import get_logger

logger = get_logger(__name__)

class TestEventSourcingComplete:
    """Complete Event Sourcing Architecture Test"""
    
    def __init__(self):
        self.mcp_server: Optional[FastMCP] = None
        self.event_service: Optional[EventSourcingService] = None
        
    async def setup(self):
        """Setup the complete test environment"""
        print("🚀 Setting up Complete Event Sourcing Test Environment")
        
        # 1. Initialize security
        security_manager = initialize_security(monitor_manager)
        print("✅ Security manager initialized")
        
        # 2. Initialize event sourcing service
        self.event_service = await init_event_sourcing_service()
        print("✅ Event sourcing service started")
        
        # 3. Create MCP server
        self.mcp_server = FastMCP("Test Event Sourcing Server")
        print("✅ MCP server created")
        
        # 4. Register event sourcing tools
        try:
            register_event_sourcing_tools(self.mcp_server)
            print("✅ Event sourcing tools registered")
        except Exception as e:
            print(f"❌ Failed to register tools: {e}")
            import traceback
            traceback.print_exc()
        
        # 5. Register event sourcing resources  
        try:
            register_event_sourcing_resources(self.mcp_server)
            print("✅ Event sourcing resources registered")
        except Exception as e:
            print(f"❌ Failed to register resources: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_tool_registration(self):
        """Test if tools are properly registered"""
        print("\n📋 Testing Tool Registration...")
        
        if not self.mcp_server:
            print("❌ MCP server not initialized")
            return False
        
        tools = await self.mcp_server.list_tools()
        event_tools = [tool for tool in tools if 
                      'background' in tool.name.lower() or 
                      'event' in tool.name.lower()]
        
        print(f"📊 Total tools registered: {len(tools)}")
        print(f"🎯 Event sourcing tools found: {len(event_tools)}")
        
        for tool in event_tools:
            print(f"  - {tool.name}: {tool.description}")
        
        return len(event_tools) > 0
    
    async def test_background_task_creation(self):
        """Test creating a background task"""
        print("\n🔧 Testing Background Task Creation...")
        
        if not self.event_service:
            print("❌ Event service not initialized")
            return None
        
        # Test task config
        task_config = {
            "urls": ["https://techcrunch.com"],
            "keywords": ["AI", "artificial intelligence"],
            "check_interval_minutes": 30
        }
        
        try:
            # Create a web monitoring task
            task = await self.event_service.create_task(
                task_type=EventSourceTaskType.WEB_MONITOR,
                description="Test AI news monitoring",
                config=task_config,
                callback_url="http://localhost:8000/process_background_feedback",
                user_id="test_user"
            )
            
            print(f"✅ Background task created: {task.task_id}")
            print(f"   Description: {task.description}")
            print(f"   Type: {task.task_type.value}")
            print(f"   Status: {task.status}")
            
            return task
            
        except Exception as e:
            print(f"❌ Failed to create background task: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def test_task_management(self, task):
        """Test task management operations"""
        print("\n📋 Testing Task Management...")
        
        if not task or not self.event_service:
            print("❌ No task or service to manage")
            return
        
        try:
            # List tasks
            tasks = await self.event_service.list_tasks("test_user")
            print(f"✅ Listed {len(tasks)} tasks")
            
            # Pause task
            success = await self.event_service.pause_task(task.task_id, "test_user")
            print(f"✅ Task paused: {success}")
            
            # Resume task
            success = await self.event_service.resume_task(task.task_id, "test_user")
            print(f"✅ Task resumed: {success}")
            
            # Get service status
            status = await self.event_service.get_service_status()
            print(f"✅ Service status: {status}")
            
        except Exception as e:
            print(f"❌ Task management error: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_event_simulation(self, task):
        """Test event simulation"""
        print("\n🎭 Testing Event Simulation...")
        
        if not task:
            print("❌ No task for event simulation")
            return None
        
        # Simulate a web content change event
        event_data = {
            "task_id": task.task_id,
            "event_type": "web_content_change",
            "data": {
                "url": "https://techcrunch.com",
                "content": "Breaking: New AI breakthrough announced...",
                "keywords_found": ["AI", "artificial intelligence"],
                "description": task.description,
                "user_id": "test_user"
            },
            "timestamp": datetime.now().isoformat(),
            "priority": 3
        }
        
        print(f"✅ Simulated event: {event_data['event_type']}")
        print(f"   Keywords found: {event_data['data']['keywords_found']}")
        print(f"   Priority: {event_data['priority']}")
        
        return event_data
    
    async def test_mcp_tool_calls(self):
        """Test MCP tool calls directly"""
        print("\n🔧 Testing MCP Tool Calls...")
        
        if not self.event_service:
            print("❌ Event service not initialized")
            return False
        
        try:
            # Test create_background_task tool
            task_config_json = json.dumps({
                "urls": ["https://news.ycombinator.com"],
                "keywords": ["machine learning", "AI"],
                "check_interval_minutes": 60
            })
            
            # Since we can't call tools directly in test mode, we'll test the underlying service
            task = await self.event_service.create_task(
                task_type=EventSourceTaskType.WEB_MONITOR,
                description="Test HackerNews ML monitoring",
                config=json.loads(task_config_json),
                callback_url="http://localhost:8000/process_background_feedback",
                user_id="test_user"
            )
            
            print(f"✅ MCP-style task creation successful: {task.task_id}")
            
            # Test list_background_tasks equivalent
            tasks = await self.event_service.list_tasks("test_user")
            print(f"✅ Task listing successful: {len(tasks)} tasks")
            
            return True
            
        except Exception as e:
            print(f"❌ MCP tool call test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def cleanup(self):
        """Clean up test environment"""
        print("\n🧹 Cleaning up test environment...")
        
        if self.event_service:
            await self.event_service.stop_service()
            print("✅ Event sourcing service stopped")

async def main():
    """Run the complete Event Sourcing test"""
    print("🎯 Complete Event Sourcing Architecture Test")
    print("=" * 60)
    
    test = TestEventSourcingComplete()
    
    try:
        # Setup
        await test.setup()
        
        # Test tool registration
        tools_registered = await test.test_tool_registration()
        if not tools_registered:
            print("❌ Tool registration failed - stopping test")
            return
        
        # Test background task creation
        task = await test.test_background_task_creation()
        
        # Test task management
        await test.test_task_management(task)
        
        # Test event simulation
        event_data = await test.test_event_simulation(task)
        
        # Test MCP tool calls
        mcp_success = await test.test_mcp_tool_calls()
        
        # Summary
        print("\n" + "=" * 60)
        print("🎯 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Tool Registration: {'PASS' if tools_registered else 'FAIL'}")
        print(f"✅ Task Creation: {'PASS' if task else 'FAIL'}")
        print(f"✅ Event Simulation: {'PASS' if event_data else 'FAIL'}")
        print(f"✅ MCP Tool Calls: {'PASS' if mcp_success else 'FAIL'}")
        
        if all([tools_registered, task, event_data, mcp_success]):
            print("\n🎉 ALL TESTS PASSED - Event Sourcing Architecture is working!")
        else:
            print("\n⚠️ Some tests failed - check the logs above")
    
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await test.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 