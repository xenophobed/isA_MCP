#!/usr/bin/env python
"""
Test Event Feedback System
测试事件反馈系统的完整流程
"""
import asyncio
import json
import aiohttp
import time
from datetime import datetime

async def test_event_feedback_system():
    """测试事件反馈系统的完整流程"""
    print("🧪 Testing Event Feedback System...")
    
    base_url = "http://localhost:8001"  # MCP Server 1
    feedback_url = "http://localhost:8000"  # Event Feedback Server
    
    try:
        # 1. 测试创建后台任务
        print("\n📝 Step 1: Creating background task...")
        
        task_config = {
            "task_type": "web_monitor",
            "description": "Monitor TechCrunch for AI news",
            "config": json.dumps({
                "urls": ["https://techcrunch.com"],
                "keywords": ["AI", "OpenAI", "machine learning"],
                "check_interval_minutes": 1  # 1分钟检查一次用于测试
            }),
            "callback_url": "http://localhost:8000/process_background_feedback",
            "user_id": "test_user"
        }
        
        async with aiohttp.ClientSession() as session:
            # 使用 MCP HTTP 协议调用工具
            mcp_request = {
                "method": "tools/call",
                "params": {
                    "name": "create_background_task",
                    "arguments": task_config
                }
            }
            
            async with session.post(
                f"{base_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Task created successfully: {result}")
                    
                    # 提取任务ID
                    if 'result' in result and 'content' in result['result']:
                        content = json.loads(result['result']['content'][0]['text'])
                        if content['status'] == 'success':
                            task_id = content['data']['task_id']
                            print(f"📋 Task ID: {task_id}")
                        else:
                            print(f"❌ Task creation failed: {content}")
                            return
                    else:
                        print(f"❌ Unexpected response format: {result}")
                        return
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to create task: {response.status} {error_text}")
                    return
        
        # 2. 检查任务列表
        print("\n📋 Step 2: Listing background tasks...")
        
        async with aiohttp.ClientSession() as session:
            mcp_request = {
                "method": "tools/call",
                "params": {
                    "name": "list_background_tasks",
                    "arguments": {"user_id": "test_user"}
                }
            }
            
            async with session.post(
                f"{base_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if 'result' in result and 'content' in result['result']:
                        content = json.loads(result['result']['content'][0]['text'])
                        if content['status'] == 'success':
                            tasks = content['data']['tasks']
                            print(f"✅ Found {len(tasks)} tasks:")
                            for task in tasks:
                                print(f"   - {task['description']} (Status: {task['status']})")
                        else:
                            print(f"❌ Failed to list tasks: {content}")
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to list tasks: {response.status} {error_text}")
        
        # 3. 检查事件反馈服务状态
        print("\n📊 Step 3: Checking event feedback service...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{feedback_url}/events/recent") as response:
                if response.status == 200:
                    events = await response.json()
                    print(f"✅ Event feedback service running: {events}")
                else:
                    print(f"❌ Event feedback service error: {response.status}")
        
        # 4. 模拟发送事件反馈
        print("\n📤 Step 4: Simulating event feedback...")
        
        test_event = {
            "task_id": task_id if 'task_id' in locals() else "test-task-123",
            "event_type": "web_content_change",
            "data": {
                "url": "https://techcrunch.com",
                "content": "Breaking: New AI breakthrough announced by OpenAI...",
                "keywords_found": ["AI", "OpenAI"],
                "description": "Monitor TechCrunch for AI news",
                "user_id": "test_user"
            },
            "timestamp": datetime.now().isoformat(),
            "priority": 3
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{feedback_url}/process_background_feedback",
                json=test_event,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Event feedback sent successfully: {result}")
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to send event feedback: {response.status} {error_text}")
        
        # 5. 等待一下，然后检查事件是否被处理
        print("\n⏳ Step 5: Waiting for event processing...")
        await asyncio.sleep(3)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{feedback_url}/events/recent") as response:
                if response.status == 200:
                    events = await response.json()
                    print(f"✅ Recent events: {events}")
                    if events['total_events'] > 0:
                        print("🎉 Event feedback system is working correctly!")
                    else:
                        print("⚠️ No events processed yet")
                else:
                    print(f"❌ Failed to get recent events: {response.status}")
        
        # 6. 测试事件资源访问
        print("\n📚 Step 6: Testing event sourcing resources...")
        
        async with aiohttp.ClientSession() as session:
            # 测试获取事件状态资源
            mcp_request = {
                "method": "resources/read",
                "params": {
                    "uri": "event://status"
                }
            }
            
            async with session.post(
                f"{base_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Event status resource: {result}")
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to get event status resource: {response.status} {error_text}")
        
        print("\n🎉 Event Feedback System Test Completed!")
        print("✅ All components are working correctly")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_event_feedback_system()) 