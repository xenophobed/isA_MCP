#!/usr/bin/env python3
"""
QuickApp分步测试 - 验证每个步骤的输入输出
"""

import sys
import os
import asyncio
import json

# 设置路径
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

def print_step(step_num, title):
    """打印步骤标题"""
    print(f"\n{'='*60}")
    print(f"步骤{step_num}: {title}")
    print('='*60)

def print_input_output(input_data, output_data, success=None):
    """打印输入输出"""
    print(f"📥 输入: {input_data}")
    if success is not None:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"📊 状态: {status}")
    print(f"📤 输出: {json.dumps(output_data, indent=2, ensure_ascii=False)}")

async def test_step1_app_analysis():
    """步骤1: 测试应用分析"""
    print_step(1, "应用分析 (AppAnalysisMolecule)")
    
    try:
        from services.molecules.app_analysis_molecule import AppAnalysisMolecule
        
        analyzer = AppAnalysisMolecule()
        
        # 测试输入
        description = "创建一个简单的博客网站"
        
        # 执行分析
        result = await analyzer.analyze_app_description(description)
        
        # 输出结果
        print_input_output(description, result, result["success"])
        
        if result["success"]:
            analysis = result["analysis"]
            print(f"\n🔍 关键信息:")
            print(f"   应用类型: {analysis['app_type']}")
            print(f"   复杂度: {analysis['complexity']}")
            print(f"   预估时间: {analysis['estimated_time']}")
            print(f"   技术栈: {analysis['tech_stack']}")
            return analysis
        else:
            return None
            
    except Exception as e:
        print(f"💥 异常: {str(e)}")
        return None

def test_step2_code_generation(app_analysis):
    """步骤2: 测试代码生成"""
    print_step(2, "代码生成 (QuickCodeMolecule)")
    
    if not app_analysis:
        print("❌ 跳过：前一步骤失败")
        return None
    
    try:
        from services.molecules.quick_code_molecule import QuickCodeMolecule
        
        generator = QuickCodeMolecule()
        
        # 构建应用规格
        app_spec = {
            "app_name": "test_blog_step",
            "app_type": app_analysis.get("app_type", "blog"),
            "description": "步骤测试博客",
            "port": 5000
        }
        
        # 执行代码生成
        result = generator.generate_app_code(app_spec)
        
        # 输出结果
        print_input_output(app_spec, {
            "success": result["success"],
            "project_path": result.get("project_path"),
            "generated_files": result.get("generated_files"),
            "failed_files": result.get("failed_files")
        }, result["success"])
        
        if result["success"]:
            print(f"\n📁 生成的文件:")
            project_path = result["project_path"]
            
            # 检查关键文件
            key_files = ["app.py", "Dockerfile", "docker-compose.yml", "requirements.txt"]
            for file_name in key_files:
                file_path = os.path.join(project_path, file_name)
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"   ✅ {file_name} ({file_size} bytes)")
                else:
                    print(f"   ❌ {file_name} (不存在)")
            
            return result
        else:
            return None
            
    except Exception as e:
        print(f"💥 异常: {str(e)}")
        return None

async def test_step3_deployment_prep(code_result):
    """步骤3: 测试部署准备"""
    print_step(3, "部署准备 (QuickDeploymentMolecule)")
    
    if not code_result:
        print("❌ 跳过：前一步骤失败")
        return None
    
    try:
        from services.molecules.quick_deployment_molecule import QuickDeploymentMolecule
        
        deployer = QuickDeploymentMolecule()
        project_path = code_result["project_path"]
        
        # 执行部署准备
        result = await deployer.prepare_deployment(project_path)
        
        # 输出结果
        print_input_output(project_path, {
            "success": result["success"],
            "allocated_port": result.get("allocated_port"),
            "preparation_steps": len(result.get("preparation_steps", []))
        }, result["success"])
        
        if result["success"]:
            print(f"\n🔧 准备详情:")
            print(f"   分配端口: {result['allocated_port']}")
            
            for step_name, step_result in result["preparation_steps"]:
                status = "✅" if step_result.get("success") else "❌"
                print(f"   {status} {step_name}")
            
            return result
        else:
            return None
            
    except Exception as e:
        print(f"💥 异常: {str(e)}")
        return None

def test_step4_port_management():
    """步骤4: 测试端口管理"""
    print_step(4, "端口管理 (PortManager)")
    
    try:
        from services.atomic.port_manager import PortManager
        
        port_manager = PortManager()
        
        # 测试端口分配
        service_name = "test_service_step"
        result = port_manager.allocate_port(service_name)
        
        print_input_output(service_name, result, result["success"])
        
        if result["success"]:
            allocated_port = result["port"]
            
            # 测试端口状态查询
            usage_result = port_manager.get_port_usage()
            print(f"\n🔌 端口使用情况:")
            print(f"   总端口范围: {usage_result['data']['port_range']}")
            print(f"   已分配: {usage_result['data']['allocated_count']}")
            print(f"   可用: {usage_result['data']['available_count']}")
            
            # 测试端口释放
            release_result = port_manager.release_port(allocated_port)
            print(f"\n🔓 端口释放:")
            print(f"   释放端口 {allocated_port}: {'成功' if release_result['success'] else '失败'}")
            
            return result
        else:
            return None
            
    except Exception as e:
        print(f"💥 异常: {str(e)}")
        return None

def test_step5_template_engine():
    """步骤5: 测试模板引擎"""
    print_step(5, "模板引擎 (TemplateEngine)")
    
    try:
        from services.atomic.template_engine import TemplateEngine
        
        engine = TemplateEngine()
        
        # 测试模板列表
        templates_result = engine.list_templates()
        
        print_input_output("list_templates()", {
            "success": templates_result["success"],
            "template_count": templates_result.get("template_count", 0),
            "template_names": [t["name"] for t in templates_result.get("templates", [])]
        }, templates_result["success"])
        
        if templates_result["success"]:
            print(f"\n📋 可用模板:")
            for template in templates_result["templates"]:
                print(f"   📄 {template['name']} ({template['content_length']} chars)")
                if template['variables']:
                    print(f"      变量: {', '.join(template['variables'])}")
            
            # 测试模板渲染
            variables = {
                "app_name": "test_app",
                "description": "测试应用",
                "port": 5000,
                "timestamp": "2024-01-01",
                "secret_key": "test_secret"
            }
            
            render_result = engine.render_template("flask_app", variables)
            
            print(f"\n🎨 模板渲染测试:")
            print_input_output({"template": "flask_app", "variables": variables}, {
                "success": render_result["success"],
                "content_length": len(render_result.get("rendered_content", ""))
            }, render_result["success"])
            
            return render_result
        else:
            return None
            
    except Exception as e:
        print(f"💥 异常: {str(e)}")
        return None

def test_step6_file_operations():
    """步骤6: 测试文件操作"""
    print_step(6, "文件操作 (FileOperations)")
    
    try:
        from services.atomic.file_operations import FileOperations
        
        file_ops = FileOperations()
        
        # 测试文件创建
        test_path = "/tmp/quickapp_step_test.txt"
        test_content = "# QuickApp Step Test\nprint('Hello from step test!')"
        
        create_result = file_ops.create_file(test_path, test_content, executable=True)
        
        print_input_output({
            "file_path": test_path,
            "content_length": len(test_content),
            "executable": True
        }, create_result, create_result["success"])
        
        if create_result["success"]:
            # 测试文件读取
            read_result = file_ops.read_file(test_path)
            
            print(f"\n📖 文件读取:")
            print_input_output(test_path, {
                "success": read_result["success"],
                "content_length": len(read_result.get("content", ""))
            }, read_result["success"])
            
            # 测试文件删除
            delete_result = file_ops.delete_file(test_path)
            
            print(f"\n🗑️ 文件删除:")
            print_input_output(test_path, delete_result, delete_result["success"])
            
            return create_result
        else:
            return None
            
    except Exception as e:
        print(f"💥 异常: {str(e)}")
        return None

async def main():
    """主测试函数"""
    print("🧪 QuickApp分步测试")
    print("🎯 目标: 验证每个组件的输入输出是否符合设计")
    
    # 记录测试结果
    results = {}
    
    # 执行各步骤测试
    results["app_analysis"] = await test_step1_app_analysis()
    results["code_generation"] = test_step2_code_generation(results["app_analysis"])
    results["deployment_prep"] = await test_step3_deployment_prep(results["code_generation"])
    results["port_management"] = test_step4_port_management()
    results["template_engine"] = test_step5_template_engine()
    results["file_operations"] = test_step6_file_operations()
    
    # 总结测试结果
    print(f"\n{'='*60}")
    print("📊 测试总结")
    print('='*60)
    
    passed = 0
    total = len(results)
    
    for step_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} {step_name}")
        if result:
            passed += 1
    
    print(f"\n📈 总体结果: {passed}/{total} 步骤通过")
    
    if passed == total:
        print("🎉 所有步骤测试通过！设计符合预期")
        print("💡 可以尝试完整的端到端流程")
    else:
        print("⚠️ 部分步骤存在问题，需要修复")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())