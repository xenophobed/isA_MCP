#!/usr/bin/env python3
"""
通用应用生成器测试示例
演示从用户需求到部署URL的完整流程
"""

import asyncio
import sys
import os

# 添加路径以便导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.append(os.path.dirname(__file__))

from universal_app_generator_service import generate_app, analyze_requirement


async def test_requirement_analysis():
    """测试需求分析功能"""
    print("🔍 测试需求分析...")
    
    requirements = [
        "我要一个简单的博客系统",
        "创建一个API服务，能够管理用户数据",
        "做一个商品展示的网站",
    ]
    
    for req in requirements:
        print(f"\n需求: {req}")
        try:
            analysis = await analyze_requirement(req)
            print(f"  应用类型: {analysis.app_type}")
            print(f"  技术栈: {analysis.tech_stack}")
            print(f"  功能: {', '.join(analysis.features)}")
            print(f"  复杂度: {analysis.complexity}")
        except Exception as e:
            print(f"  ❌ 分析失败: {e}")


async def test_code_generation_only():
    """测试仅代码生成（不部署）"""
    print("\n\n💻 测试代码生成（不部署）...")
    
    requirement = "创建一个简单的任务管理API"
    
    try:
        result = await generate_app(
            requirement, 
            deploy_immediately=False,
            output_dir="./test_generated_apps"
        )
        
        if result.success:
            print(f"✅ 代码生成成功!")
            print(f"   项目路径: {result.project_path}")
            print(f"   应用类型: {result.analysis.app_type}")
            print(f"   技术栈: {result.analysis.tech_stack}")
            print(f"   生成文件数: {len(result.files) if result.files else 0}")
            
            # 显示生成的文件列表
            if result.files:
                print("   生成的文件:")
                for file_path in result.files.keys():
                    print(f"     - {file_path}")
        else:
            print(f"❌ 代码生成失败: {result.error_message}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")


async def test_full_generation_and_deployment():
    """测试完整的生成和部署流程"""
    print("\n\n🚀 测试完整流程（生成 + 部署）...")
    
    requirement = "创建一个简单的欢迎页面网站"
    
    try:
        result = await generate_app(
            requirement,
            deploy_immediately=True,
            custom_port=8888
        )
        
        if result.success and result.url:
            print(f"🎉 应用生成并部署成功!")
            print(f"   🌐 访问地址: {result.url}")
            print(f"   📁 项目路径: {result.project_path}")
            print(f"   🔧 技术栈: {result.analysis.tech_stack}")
            print(f"   ⚡ 进程ID: {result.deployment_info.process_id}")
            print(f"   🚪 端口: {result.deployment_info.port}")
            
            print(f"\n✨ 你可以访问 {result.url} 查看生成的应用!")
            
            # 等待几秒让用户看到结果
            print("\n⏳ 等待5秒后自动停止服务...")
            await asyncio.sleep(5)
            
            # 停止服务（演示用）
            from universal_app_generator_service import universal_app_generator
            stop_success = await universal_app_generator.stop_app(result.project_path)
            if stop_success:
                print("✅ 服务已停止")
            else:
                print("⚠️ 服务停止失败")
                
        else:
            print(f"❌ 应用生成失败: {result.error_message}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")


async def test_multiple_apps():
    """测试同时运行多个应用"""
    print("\n\n🔄 测试多应用同时运行...")
    
    requirements = [
        "创建一个Hello World网站",
        "做一个简单的计算器API"
    ]
    
    deployed_apps = []
    
    for i, req in enumerate(requirements):
        print(f"\n部署应用 {i+1}: {req}")
        try:
            result = await generate_app(
                req,
                deploy_immediately=True,
                custom_port=9000 + i
            )
            
            if result.success and result.url:
                print(f"✅ 应用 {i+1} 部署成功: {result.url}")
                deployed_apps.append(result)
            else:
                print(f"❌ 应用 {i+1} 部署失败: {result.error_message}")
                
        except Exception as e:
            print(f"❌ 应用 {i+1} 部署异常: {e}")
    
    if deployed_apps:
        print(f"\n🎯 成功部署 {len(deployed_apps)} 个应用:")
        for i, app in enumerate(deployed_apps):
            print(f"   应用 {i+1}: {app.url}")
        
        print("\n⏳ 等待3秒后清理所有应用...")
        await asyncio.sleep(3)
        
        # 清理所有应用
        from universal_app_generator_service import universal_app_generator
        stop_results = await universal_app_generator.stop_all_apps()
        print(f"✅ 清理完成，停止了 {len(stop_results)} 个应用")


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 通用应用生成器测试套件")
    print("=" * 60)
    
    # 测试1: 需求分析
    await test_requirement_analysis()
    
    # 测试2: 仅代码生成
    await test_code_generation_only()
    
    # 测试3: 完整流程
    await test_full_generation_and_deployment()
    
    # 测试4: 多应用测试
    await test_multiple_apps()
    
    print("\n" + "=" * 60)
    print("🎉 所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())