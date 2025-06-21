#!/usr/bin/env python
"""
Simple Event Feedback System Test
简化的事件反馈系统测试
"""
import asyncio
import json
import aiohttp
from datetime import datetime

async def test_simple_event_feedback():
    """简单测试事件反馈系统"""
    print("🧪 Simple Event Feedback Test...")
    
    feedback_url = "http://localhost:8000"
    
    # 1. 测试健康检查
    print("\n📊 Step 1: Health check...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{feedback_url}/health") as response:
            if response.status == 200:
                health = await response.json()
                print(f"✅ Health check passed: {health}")
            else:
                print(f"❌ Health check failed: {response.status}")
                return
    
    # 2. 检查根端点
    print("\n📋 Step 2: Root endpoint...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{feedback_url}/") as response:
            if response.status == 200:
                info = await response.json()
                print(f"✅ Root endpoint: {info}")
            else:
                print(f"❌ Root endpoint failed: {response.status}")
    
    # 3. 模拟事件反馈
    print("\n📤 Step 3: Sending test event...")
    test_event = {
        "task_id": "test-task-123",
        "event_type": "test_event",
        "data": {
            "message": "This is a test event",
            "timestamp": datetime.now().isoformat(),
            "user_id": "test_user"
        },
        "priority": 2
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{feedback_url}/process_background_feedback",
            json=test_event,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Event sent successfully: {result}")
            else:
                error_text = await response.text()
                print(f"❌ Event sending failed: {response.status} - {error_text}")
    
    # 4. 检查最近事件
    print("\n📋 Step 4: Checking recent events...")
    await asyncio.sleep(2)  # 等待处理
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{feedback_url}/events/recent") as response:
            if response.status == 200:
                events = await response.json()
                print(f"✅ Recent events: {json.dumps(events, indent=2)}")
                if events['total_events'] > 0:
                    print("🎉 Event feedback system is working!")
                else:
                    print("⚠️ No events processed")
            else:
                print(f"❌ Failed to get events: {response.status}")

if __name__ == "__main__":
    asyncio.run(test_simple_event_feedback()) 