#!/usr/bin/env python3
"""
Simple test script for Task API endpoints
Tests the MockTaskService directly without HTTP requests
"""

import sys
import os
import asyncio
from datetime import datetime

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from api.endpoints.tasks import MockTaskService
from models.schemas.task_models import UserTaskCreate
from models.schemas.enums import TaskType, TaskPriority

async def test_mock_task_service():
    """Test the MockTaskService functionality"""
    print("🚀 Testing MockTaskService...")
    
    # Create service instance
    service = MockTaskService()
    
    # Test data
    user_id = "test-user-123"
    
    # Test 1: Create a task
    print("\n1. Testing task creation...")
    task_data = UserTaskCreate(
        name="Test Weather Task",
        description="A test task for weather alerts",
        task_type=TaskType.DAILY_WEATHER,
        priority=TaskPriority.MEDIUM,
        config={
            "location": "Beijing",
            "notification_time": "08:00"
        },
        credits_per_run=0.5,
        tags=["weather", "daily"],
        metadata={"test": True}
    )
    
    result = await service.create_task(user_id, task_data)
    if result.success:
        task = result.data["task"]
        task_id = task["task_id"]
        print(f"✅ Task created successfully: {task_id}")
        print(f"   Name: {task['name']}")
        print(f"   Type: {task['task_type']}")
        print(f"   Priority: {task['priority']}")
    else:
        print(f"❌ Task creation failed: {result.error}")
        return
    
    # Test 2: Get task by ID
    print("\n2. Testing get task by ID...")
    result = await service.get_task(task_id, user_id)
    if result.success:
        task = result.data["task"]
        print(f"✅ Task retrieved successfully: {task['name']}")
    else:
        print(f"❌ Get task failed: {result.error}")
    
    # Test 3: Get user tasks
    print("\n3. Testing get user tasks...")
    result = await service.get_user_tasks(user_id)
    if result.success:
        tasks = result.data["tasks"]
        count = result.data["count"]
        print(f"✅ Retrieved {count} tasks for user {user_id}")
        for task in tasks:
            print(f"   - {task['name']} ({task['task_type']})")
    else:
        print(f"❌ Get user tasks failed: {result.error}")
    
    # Test 4: Execute task
    print("\n4. Testing task execution...")
    result = await service.execute_task(task_id)
    if result.success:
        execution_id = result.data["execution_id"]
        print(f"✅ Task execution started: {execution_id}")
    else:
        print(f"❌ Task execution failed: {result.error}")
    
    # Test 5: Get task templates
    print("\n5. Testing get task templates...")
    result = await service.get_task_templates(user_id)
    if result.success:
        templates = result.data["templates"]
        subscription_level = result.data["subscription_level"]
        print(f"✅ Retrieved {len(templates)} templates for {subscription_level} subscription")
        for template_id, template in templates.items():
            print(f"   - {template['name']}: {template['description']}")
    else:
        print(f"❌ Get templates failed: {result.error}")
    
    # Test 6: Get task analytics
    print("\n6. Testing get task analytics...")
    result = await service.get_task_analytics(user_id)
    if result.success:
        analytics = result.data["analytics"]
        print(f"✅ Analytics retrieved for user {user_id}")
        print(f"   Total tasks: {analytics['total_tasks']}")
        print(f"   Active tasks: {analytics['active_tasks']}")
        print(f"   Credits consumed: {analytics['total_credits_consumed']}")
    else:
        print(f"❌ Get analytics failed: {result.error}")
    
    print("\n🎉 MockTaskService test completed!")

def test_database_connection():
    """Test if we can connect to the database tables we created"""
    print("\n🔍 Testing database connection...")
    
    try:
        import subprocess
        
        # Test user_tasks table
        result = subprocess.run([
            'psql', '-h', '127.0.0.1', '-p', '54322', '-U', 'postgres', '-d', 'postgres',
            '-c', 'SELECT COUNT(*) FROM dev.user_tasks;'
        ], 
        capture_output=True, text=True, env={'PGPASSWORD': 'postgres'})
        
        if result.returncode == 0:
            print("✅ Connected to user_tasks table")
            print(f"   Current task count: {result.stdout.strip().split()[-1]}")
        else:
            print(f"❌ Failed to connect to user_tasks: {result.stderr}")
            return
        
        # Test task_executions table
        result = subprocess.run([
            'psql', '-h', '127.0.0.1', '-p', '54322', '-U', 'postgres', '-d', 'postgres',
            '-c', 'SELECT COUNT(*) FROM dev.task_executions;'
        ], 
        capture_output=True, text=True, env={'PGPASSWORD': 'postgres'})
        
        if result.returncode == 0:
            print("✅ Connected to task_executions table")
            print(f"   Current execution count: {result.stdout.strip().split()[-1]}")
        else:
            print(f"❌ Failed to connect to task_executions: {result.stderr}")
        
        # Test task_templates table
        result = subprocess.run([
            'psql', '-h', '127.0.0.1', '-p', '54322', '-U', 'postgres', '-d', 'postgres',
            '-c', 'SELECT template_id, name FROM dev.task_templates;'
        ], 
        capture_output=True, text=True, env={'PGPASSWORD': 'postgres'})
        
        if result.returncode == 0:
            print("✅ Connected to task_templates table")
            lines = result.stdout.strip().split('\n')
            template_count = len([l for l in lines if l.strip() and not l.startswith('-') and 'template_id' not in l])
            print(f"   Available templates: {template_count}")
        else:
            print(f"❌ Failed to connect to task_templates: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")

if __name__ == "__main__":
    print("🔧 Task API Testing Suite")
    print("=" * 50)
    
    # Test database connection first
    test_database_connection()
    
    # Test MockTaskService
    asyncio.run(test_mock_task_service())
    
    print("\n" + "=" * 50)
    print("✨ All tests completed!")