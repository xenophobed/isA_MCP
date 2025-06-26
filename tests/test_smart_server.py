#!/usr/bin/env python3
"""
Test script for Smart MCP Server
测试智能MCP服务器的功能
"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_server_endpoints():
    """测试服务器端点"""
    print("🧪 Testing Smart MCP Server Endpoints")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # 测试健康检查
        print("\n=== 健康检查 ===")
        try:
            response = await client.get("http://localhost:4321/health")
            health_data = response.json()
            print(f"✅ Health: {health_data['status']}")
            print(f"📊 Loaded tools: {health_data['server_status']['loaded_tools']}")
            print(f"📦 Available tools: {health_data['server_status']['available_tools']}")
            print(f"🧠 AI selector: {health_data['server_status']['tool_selector_ready']}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return
        
        # 测试工具分析 - 记忆请求
        print("\n=== 测试1: 记忆请求分析 ===")
        try:
            analyze_data = {"request": "my name is dennis please remember it"}
            response = await client.post("http://localhost:4321/analyze", json=analyze_data)
            result = response.json()
            print(f"📊 Status: {result['status']}")
            print(f"🎯 Selected tools: {result.get('selected_tools', [])}")
            print(f"🆕 Newly loaded: {result.get('newly_loaded', [])}")
            print(f"📋 All loaded: {result.get('all_loaded', [])}")
        except Exception as e:
            print(f"❌ Memory analysis failed: {e}")
        
        # 测试工具分析 - 天气请求
        print("\n=== 测试2: 天气请求分析 ===")
        try:
            analyze_data = {"request": "what is the weather in Beijing?"}
            response = await client.post("http://localhost:4321/analyze", json=analyze_data)
            result = response.json()
            print(f"📊 Status: {result['status']}")
            print(f"🎯 Selected tools: {result.get('selected_tools', [])}")
            print(f"🆕 Newly loaded: {result.get('newly_loaded', [])}")
            print(f"📋 All loaded: {result.get('all_loaded', [])}")
        except Exception as e:
            print(f"❌ Weather analysis failed: {e}")
        
        # 测试工具分析 - 复杂任务
        print("\n=== 测试3: 复杂任务分析 ===")
        try:
            analyze_data = {"request": "create a blog post about AI"}
            response = await client.post("http://localhost:4321/analyze", json=analyze_data)
            result = response.json()
            print(f"📊 Status: {result['status']}")
            print(f"🎯 Selected tools: {result.get('selected_tools', [])}")
            print(f"🆕 Newly loaded: {result.get('newly_loaded', [])}")
            print(f"📋 All loaded: {result.get('all_loaded', [])}")
        except Exception as e:
            print(f"❌ Complex task analysis failed: {e}")

async def test_mcp_tools():
    """测试MCP工具调用"""
    print("\n🔧 Testing MCP Tool Calls")
    print("=" * 30)
    
    async with httpx.AsyncClient() as client:
        # 测试工具列表
        print("\n=== 获取工具列表 ===")
        try:
            mcp_data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            response = await client.post("http://localhost:4321/mcp/", json=mcp_data)
            result = response.json()
            if "result" in result and "tools" in result["result"]:
                tools = result["result"]["tools"]
                print(f"✅ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"   - {tool['name']}: {tool.get('description', 'No description')[:50]}...")
            else:
                print(f"❌ Unexpected response: {result}")
        except Exception as e:
            print(f"❌ Tools list failed: {e}")
        
        # 测试记忆工具调用
        print("\n=== 测试记忆工具 ===")
        try:
            mcp_data = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "remember",
                    "arguments": {
                        "key": "user_name",
                        "value": "Dennis",
                        "category": "personal"
                    }
                }
            }
            response = await client.post("http://localhost:4321/mcp/", json=mcp_data)
            result = response.json()
            print(f"📝 Memory tool result: {result}")
        except Exception as e:
            print(f"❌ Memory tool failed: {e}")

async def main():
    """主测试函数"""
    print(f"🚀 Smart MCP Server Test Suite")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 测试服务器端点
    await test_server_endpoints()
    
    # 测试MCP工具
    await test_mcp_tools()
    
    print("\n✅ Test suite completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main()) 