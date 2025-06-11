import asyncio
from app.services.ai.tools.tools_manager import tools_manager

async def check_web_search_registration():
    try:
        # 初始化 tools manager
        print("Initializing tools manager...")
        await tools_manager.initialize()
        
        # 获取所有注册的工具
        all_tools = tools_manager.get_tools()
        print("\nRegistered tools:")
        for tool in all_tools:
            print(f"- {tool.name}")
        
        # 检查 web_search 是否注册
        web_search_tools = [tool for tool in all_tools if tool.name == "web_search"]
        if web_search_tools:
            print("\n✅ web_search tool is registered!")
        else:
            print("\n❌ web_search tool not found in registered tools")
        
        # 获取注册状态
        status = await tools_manager.get_registry_status()
        print(f"\nRegistry status:")
        print(f"- Total tools: {status['total_tools']}")
        print(f"- Health status: {status['health_status']}")
        print(f"- Last sync: {status['last_sync']}")
        
        # 验证工具完整性
        print("\nChecking tool integrity...")
        integrity = await tools_manager.verify_tools_integrity()
        if integrity:
            print("⚠️  Tool integrity issues found:", integrity)
        else:
            print("✅ No integrity issues found")
            
    except Exception as e:
        print(f"\n❌ Error during check: {str(e)}")
    finally:
        # 清理资源
        await tools_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(check_web_search_registration()) 