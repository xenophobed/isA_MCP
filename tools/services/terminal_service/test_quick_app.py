#!/usr/bin/env python3
"""
QuickApp测试脚本
测试从描述到URL的完整流程
"""

import asyncio
import sys
import os

# 添加路径
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

# 修复导入路径
try:
    from tools.quick_app_tools import QuickAppTools
except ImportError:
    # 如果直接导入失败，尝试相对导入
    sys.path.insert(0, current_dir)
    from tools.quick_app_tools import QuickAppTools


async def test_create_blog():
    """测试创建博客网站"""
    print("=" * 60)
    print("🧪 QuickApp 测试: 创建简单博客网站")
    print("=" * 60)
    
    tools = QuickAppTools()
    
    # 测试描述
    description = "创建一个简单的博客网站"
    
    print(f"📝 输入描述: {description}")
    print("⏳ 开始创建应用...")
    
    try:
        # 调用创建方法
        result_json = await tools.create_quick_app(description)
        
        # 解析结果
        import json
        result = json.loads(result_json)
        
        print("\n" + "=" * 40)
        print("📊 执行结果:")
        print("=" * 40)
        
        if result["status"] == "success":
            data = result["data"]
            print(f"✅ 状态: 成功")
            print(f"🏷️  应用名称: {data['app_name']}")
            print(f"🌐 服务URL: {data['service_url']}")
            print(f"⏱️  创建耗时: {data['total_time_seconds']:.1f}秒")
            print(f"🔍 验证通过: {data['verification_passed']}")
            
            print("\n🔗 快速链接:")
            for name, url in data['quick_links'].items():
                print(f"   {name}: {url}")
                
            print(f"\n{data['summary']}")
            
            return data['service_url']
        else:
            print(f"❌ 状态: 失败")
            print(f"🚨 错误: {result['error_message']}")
            if 'failed_stage' in result['data']:
                print(f"📍 失败阶段: {result['data']['failed_stage']}")
                print(f"✅ 完成阶段: {result['data']['completed_stages']}")
            
            return None
            
    except Exception as e:
        print(f"💥 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def test_list_apps():
    """测试列出应用"""
    print("\n" + "=" * 60)
    print("🧪 测试: 列出快速应用")
    print("=" * 60)
    
    tools = QuickAppTools()
    
    try:
        result_json = await tools.list_quick_apps()
        result = json.loads(result_json)
        
        if result["status"] == "success":
            data = result["data"]
            print(f"✅ 找到 {data['total_apps']} 个应用")
            
            for app in data['running_apps']:
                print(f"\n📱 {app['app_name']}")
                print(f"   🌐 URL: {app['service_url']}")
                print(f"   📊 状态: {app['status']}")
                print(f"   🔌 端口: {app['port']}")
        else:
            print(f"❌ 列出应用失败: {result['error_message']}")
            
    except Exception as e:
        print(f"💥 列出应用异常: {str(e)}")


async def verify_url_accessible(url):
    """验证URL是否可访问"""
    if not url:
        return False
        
    print(f"\n🔍 验证URL可访问性: {url}")
    
    try:
        import subprocess
        
        # 使用curl测试URL
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--connect-timeout", "10", url],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        http_code = result.stdout.strip()
        print(f"📊 HTTP状态码: {http_code}")
        
        if http_code.startswith("2"):
            print("✅ URL可访问!")
            return True
        else:
            print("❌ URL不可访问")
            return False
            
    except Exception as e:
        print(f"❌ URL验证失败: {str(e)}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始QuickApp端到端测试")
    
    # 检查前置条件
    print("\n🔧 检查前置条件...")
    
    # 检查Docker
    try:
        import subprocess
        docker_result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if docker_result.returncode == 0:
            print("✅ Docker已安装")
        else:
            print("❌ Docker未安装或不可用")
            return
    except:
        print("❌ Docker未安装或不可用")
        return
    
    # 检查Docker守护进程
    try:
        daemon_result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if daemon_result.returncode == 0:
            print("✅ Docker守护进程运行中")
        else:
            print("❌ Docker守护进程未运行")
            return
    except:
        print("❌ Docker守护进程未运行")
        return
    
    # 测试1: 创建博客应用
    service_url = await test_create_blog()
    
    # 测试2: 列出应用
    await test_list_apps()
    
    # 测试3: 验证URL
    if service_url:
        accessible = await verify_url_accessible(service_url)
        
        if accessible:
            print(f"\n🎉 测试成功! 应用已可访问: {service_url}")
            print("👆 请在浏览器中打开上述链接查看您的博客网站")
        else:
            print("\n⚠️  应用创建成功但暂时不可访问，可能需要等待容器启动")
    else:
        print("\n😞 测试失败，应用创建未成功")
    
    print("\n" + "=" * 60)
    print("🧪 QuickApp测试完成")
    print("=" * 60)


if __name__ == "__main__":
    import json
    asyncio.run(main())