#!/usr/bin/env python3
"""
QuickApp简化测试 - 测试核心流程
"""

import sys
import os
import asyncio

# 添加当前目录到路径
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

async def test_app_analysis():
    """测试应用分析"""
    print("🧪 测试AppAnalysisMolecule...")
    
    try:
        from services.molecules.app_analysis_molecule import AppAnalysisMolecule
        
        analyzer = AppAnalysisMolecule()
        
        # 测试分析博客描述
        description = "创建一个简单的博客网站"
        result = await analyzer.analyze_app_description(description)
        
        if result["success"]:
            analysis = result["analysis"]
            print("✅ AppAnalysis测试成功")
            print(f"   应用类型: {analysis['app_type']}")
            print(f"   复杂度: {analysis['complexity']}")
            print(f"   预估时间: {analysis['estimated_time']}")
            return analysis
        else:
            print(f"❌ AppAnalysis测试失败: {result['error']}")
            return None
            
    except Exception as e:
        print(f"💥 AppAnalysis测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_code_generation():
    """测试代码生成"""
    print("\n🧪 测试QuickCodeMolecule...")
    
    try:
        from services.molecules.quick_code_molecule import QuickCodeMolecule
        
        generator = QuickCodeMolecule()
        
        # 测试生成代码
        app_spec = {
            "app_name": "test_blog_simple",
            "app_type": "blog",
            "description": "简单博客测试",
            "port": 5000
        }
        
        result = generator.generate_app_code(app_spec)
        
        if result["success"]:
            print("✅ CodeGeneration测试成功")
            print(f"   项目路径: {result['project_path']}")
            print(f"   生成文件: {result['generated_files']} 个")
            print(f"   失败文件: {len(result['failed_files'])} 个")
            
            # 检查生成的文件
            import os
            project_path = result['project_path']
            if os.path.exists(f"{project_path}/app.py"):
                print("   ✅ app.py 生成成功")
            if os.path.exists(f"{project_path}/Dockerfile"):
                print("   ✅ Dockerfile 生成成功")
            if os.path.exists(f"{project_path}/docker-compose.yml"):
                print("   ✅ docker-compose.yml 生成成功")
            
            return result
        else:
            print(f"❌ CodeGeneration测试失败: {result}")
            return None
            
    except Exception as e:
        print(f"💥 CodeGeneration测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def test_deployment_preparation(project_path):
    """测试部署准备"""
    print("\n🧪 测试QuickDeploymentMolecule...")
    
    try:
        from services.molecules.quick_deployment_molecule import QuickDeploymentMolecule
        
        deployer = QuickDeploymentMolecule()
        
        # 测试部署准备
        result = await deployer.prepare_deployment(project_path)
        
        if result["success"]:
            print("✅ DeploymentPreparation测试成功")
            print(f"   分配端口: {result['allocated_port']}")
            print(f"   准备步骤: {len(result['preparation_steps'])} 个")
            return result
        else:
            print(f"❌ DeploymentPreparation测试失败: {result['error']}")
            return None
            
    except Exception as e:
        print(f"💥 DeploymentPreparation测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def test_full_quickapp():
    """测试完整QuickApp流程"""
    print("\n🧪 测试完整QuickApp流程...")
    
    try:
        # 由于导入问题，我们直接手动组合测试
        print("📝 步骤1: 应用分析")
        analysis = await test_app_analysis()
        
        if not analysis:
            print("❌ 应用分析失败，终止测试")
            return False
        
        print("\n💻 步骤2: 代码生成")
        code_result = test_code_generation()
        
        if not code_result:
            print("❌ 代码生成失败，终止测试")
            return False
        
        print("\n🔧 步骤3: 部署准备")
        prep_result = await test_deployment_preparation(code_result['project_path'])
        
        if not prep_result:
            print("❌ 部署准备失败，终止测试")
            return False
        
        print("\n🎉 QuickApp核心流程测试完成！")
        print(f"📁 项目目录: {code_result['project_path']}")
        print(f"🔌 分配端口: {prep_result['allocated_port']}")
        print(f"🌐 预期URL: http://localhost:{prep_result['allocated_port']}")
        
        # 检查Docker是否可用于实际部署
        from services.atomic.command_execution import CommandExecution
        cmd_exec = CommandExecution()
        docker_check = cmd_exec.execute_command("docker --version")
        
        if docker_check["success"]:
            print("\n✅ Docker可用，理论上可以完成实际部署")
            print("💡 要进行完整部署，需要运行docker build和docker-compose up")
        else:
            print("\n⚠️  Docker不可用，无法进行实际容器部署")
        
        return True
        
    except Exception as e:
        print(f"💥 完整流程测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("🚀 QuickApp 核心流程测试")
    print("=" * 60)
    print("测试目标: 验证 '描述 → 分析 → 代码 → 部署准备' 流程")
    print("=" * 60)
    
    # 检查基础环境
    print("🔧 检查基础环境...")
    
    try:
        from services.atomic.command_execution import CommandExecution
        cmd_exec = CommandExecution()
        
        # 检查Docker
        docker_result = cmd_exec.execute_command("docker --version")
        if docker_result["success"]:
            print("✅ Docker已安装")
        else:
            print("⚠️  Docker未安装")
        
        # 检查临时目录
        temp_check = cmd_exec.execute_command("mkdir -p /tmp/quickapps")
        if temp_check["success"]:
            print("✅ 临时目录可用")
        else:
            print("❌ 临时目录不可用")
            
    except Exception as e:
        print(f"⚠️  环境检查异常: {str(e)}")
    
    # 运行完整测试
    success = await test_full_quickapp()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 QuickApp核心流程测试成功！")
        print("💭 理论上，从'创建一个简单的博客网站'到生成可部署代码是可行的")
        print("🚀 下一步需要测试实际的Docker部署")
    else:
        print("😞 QuickApp核心流程测试失败")
        print("🔧 需要修复相关问题")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())