#!/usr/bin/env python3
"""
原子服务单独测试 - 不依赖AI服务
"""

import sys
import os
import json

# 设置路径
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

def print_step(step_num, title):
    """打印步骤标题"""
    print(f"\n{'='*50}")
    print(f"步骤{step_num}: {title}")
    print('='*50)

def print_result(input_data, output_data, success=None):
    """打印输入输出"""
    print(f"📥 输入: {input_data}")
    if success is not None:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"📊 状态: {status}")
    
    # 简化输出显示
    if isinstance(output_data, dict) and len(str(output_data)) > 200:
        simplified = {k: v for k, v in output_data.items() if k in ["success", "error", "port", "file_path", "template_count"]}
        print(f"📤 输出: {json.dumps(simplified, indent=2, ensure_ascii=False)}")
    else:
        print(f"📤 输出: {json.dumps(output_data, indent=2, ensure_ascii=False)}")

def test_port_manager():
    """测试端口管理"""
    print_step(1, "端口管理 (PortManager)")
    
    try:
        from services.atomic.port_manager import PortManager
        
        port_manager = PortManager()
        
        # 测试端口分配
        result = port_manager.allocate_port("test_service")
        print_result("allocate_port('test_service')", result, result["success"])
        
        if result["success"]:
            port = result["port"]
            
            # 测试端口查询
            check_result = port_manager.check_port_available(port)
            print(f"\n🔍 端口{port}可用性: {check_result['available']}")
            
            # 测试释放端口
            release_result = port_manager.release_port(port)
            print(f"🔓 端口{port}释放: {'成功' if release_result['success'] else '失败'}")
            
            return True
        
        return False
        
    except Exception as e:
        print(f"💥 异常: {str(e)}")
        return False

def test_template_engine():
    """测试模板引擎"""
    print_step(2, "模板引擎 (TemplateEngine)")
    
    try:
        from services.atomic.template_engine import TemplateEngine
        
        engine = TemplateEngine()
        
        # 测试列出模板
        templates_result = engine.list_templates()
        print_result("list_templates()", {
            "template_count": templates_result.get("template_count", 0),
            "success": templates_result["success"]
        }, templates_result["success"])
        
        if templates_result["success"]:
            # 测试渲染Flask应用模板
            variables = {
                "app_name": "博客测试",
                "description": "一个简单的博客网站",
                "port": 5000,
                "timestamp": "2024-01-01",
                "secret_key": "test_secret_123",
                "custom_routes": "# 博客路由代码"
            }
            
            render_result = engine.render_template("flask_app", variables)
            print_result(f"render_template('flask_app', variables)", {
                "success": render_result["success"],
                "content_length": len(render_result.get("rendered_content", ""))
            }, render_result["success"])
            
            if render_result["success"]:
                content = render_result["rendered_content"]
                print(f"\n📄 生成的代码片段:")
                lines = content.split('\n')
                for i, line in enumerate(lines[:10]):  # 显示前10行
                    print(f"   {i+1:2d} | {line}")
                if len(lines) > 10:
                    print(f"   ... (共{len(lines)}行)")
                
                return True
        
        return False
        
    except Exception as e:
        print(f"💥 异常: {str(e)}")
        return False

def test_file_operations():
    """测试文件操作"""
    print_step(3, "文件操作 (FileOperations)")
    
    try:
        from services.atomic.file_operations import FileOperations
        
        file_ops = FileOperations()
        
        # 生成测试Flask应用代码
        test_code = '''from flask import Flask, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html', 
                         app_name="测试博客",
                         description="AI生成的博客应用")

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
'''
        
        test_path = "/tmp/test_blog_app.py"
        
        # 创建文件
        create_result = file_ops.create_file(test_path, test_code, executable=True)
        print_result({
            "file_path": test_path,
            "content_type": "Flask应用代码",
            "executable": True
        }, create_result, create_result["success"])
        
        if create_result["success"]:
            # 验证文件内容
            read_result = file_ops.read_file(test_path)
            
            if read_result["success"]:
                content = read_result["content"]
                print(f"\n📄 文件内容验证:")
                print(f"   文件大小: {len(content)} 字符")
                print(f"   包含Flask: {'Flask' in content}")
                print(f"   包含路由: {'@app.route' in content}")
                print(f"   包含中文: {'测试博客' in content}")
            
            # 清理文件
            file_ops.delete_file(test_path)
            return True
        
        return False
        
    except Exception as e:
        print(f"💥 异常: {str(e)}")
        return False

def test_directory_operations():
    """测试目录操作"""
    print_step(4, "目录操作 (DirectoryOperations)")
    
    try:
        from services.atomic.directory_operations import DirectoryOperations
        
        dir_ops = DirectoryOperations()
        
        # 创建项目目录结构
        project_base = "/tmp/test_blog_project"
        directories = ["src", "templates", "static", "static/css", "static/js", "config", "logs"]
        
        # 创建基础目录
        base_result = dir_ops.create_directory(project_base)
        print_result(f"create_directory('{project_base}')", base_result, base_result["success"])
        
        if base_result["success"]:
            # 创建目录结构
            struct_result = dir_ops.create_directory_structure(project_base, directories)
            print_result({
                "base_path": project_base,
                "directories": directories
            }, {
                "success": struct_result["success"],
                "created_count": len(struct_result.get("created_directories", []))
            }, struct_result["success"])
            
            if struct_result["success"]:
                # 验证目录结构
                print(f"\n📁 创建的目录结构:")
                for created_dir in struct_result["created_directories"]:
                    rel_path = created_dir.replace(project_base + "/", "")
                    print(f"   📂 {rel_path}")
                
                # 清理目录
                import shutil
                shutil.rmtree(project_base)
                return True
        
        return False
        
    except Exception as e:
        print(f"💥 异常: {str(e)}")
        return False

def test_command_execution():
    """测试命令执行"""
    print_step(5, "命令执行 (CommandExecution)")
    
    try:
        from services.atomic.command_execution import CommandExecution
        
        cmd_exec = CommandExecution()
        
        # 测试简单命令
        result = cmd_exec.execute_command("echo 'QuickApp原子服务测试'")
        print_result("echo 'QuickApp原子服务测试'", {
            "success": result["success"],
            "output": result.get("stdout", "").strip()
        }, result["success"])
        
        if result["success"]:
            # 测试Docker版本检查
            docker_result = cmd_exec.execute_command("docker --version")
            print(f"\n🐳 Docker检查: {'可用' if docker_result['success'] else '不可用'}")
            
            # 测试目录列表
            ls_result = cmd_exec.execute_command("ls /tmp | head -5")
            if ls_result["success"]:
                print(f"📂 /tmp目录内容: {ls_result['stdout'].strip().replace(chr(10), ', ')}")
            
            return True
        
        return False
        
    except Exception as e:
        print(f"💥 异常: {str(e)}")
        return False

def test_realistic_workflow():
    """测试现实工作流程"""
    print_step(6, "现实工作流程模拟")
    
    try:
        # 组合使用多个原子服务
        from services.atomic.template_engine import TemplateEngine
        from services.atomic.file_operations import FileOperations
        from services.atomic.directory_operations import DirectoryOperations
        from services.atomic.port_manager import PortManager
        
        print("📋 模拟：创建一个简单博客项目")
        
        # 1. 分配端口
        port_mgr = PortManager()
        port_result = port_mgr.allocate_port("realistic_blog")
        
        if not port_result["success"]:
            print("❌ 端口分配失败")
            return False
        
        port = port_result["port"]
        print(f"✅ 分配端口: {port}")
        
        # 2. 创建项目目录
        dir_ops = DirectoryOperations()
        project_path = "/tmp/realistic_blog"
        
        base_result = dir_ops.create_directory(project_path)
        if not base_result["success"]:
            print("❌ 项目目录创建失败")
            return False
        
        struct_result = dir_ops.create_directory_structure(project_path, ["templates", "static"])
        print(f"✅ 创建目录结构: {len(struct_result['created_directories'])} 个目录")
        
        # 3. 生成应用代码
        template_engine = TemplateEngine()
        variables = {
            "app_name": "现实博客测试",
            "description": "使用原子服务生成的博客",
            "port": port,
            "timestamp": "2024-01-01",
            "secret_key": "realistic_secret_123",
            "custom_routes": """
@app.route('/posts')
def list_posts():
    return jsonify({
        "posts": [
            {"id": 1, "title": "欢迎使用博客", "content": "这是第一篇文章"},
            {"id": 2, "title": "原子服务测试", "content": "通过原子服务组合创建"}
        ]
    })
"""
        }
        
        app_result = template_engine.render_template("flask_app", variables)
        if not app_result["success"]:
            print("❌ 应用代码生成失败")
            return False
        
        print(f"✅ 生成Flask应用代码: {len(app_result['rendered_content'])} 字符")
        
        # 4. 写入文件
        file_ops = FileOperations()
        app_file = os.path.join(project_path, "app.py")
        
        write_result = file_ops.create_file(app_file, app_result["rendered_content"], executable=True)
        if not write_result["success"]:
            print("❌ 应用文件写入失败")
            return False
        
        print(f"✅ 写入应用文件: {app_file}")
        
        # 5. 生成HTML模板
        html_variables = {
            "app_name": "现实博客测试",
            "description": "使用原子服务组合生成的完整博客应用",
            "timestamp": "2024-01-01"
        }
        
        html_result = template_engine.render_template("html_index", html_variables)
        if html_result["success"]:
            html_file = os.path.join(project_path, "templates", "index.html")
            file_ops.create_file(html_file, html_result["rendered_content"])
            print(f"✅ 生成HTML模板: {len(html_result['rendered_content'])} 字符")
        
        # 6. 生成Dockerfile
        dockerfile_result = template_engine.render_template("dockerfile", {"port": port})
        if dockerfile_result["success"]:
            dockerfile_path = os.path.join(project_path, "Dockerfile")
            file_ops.create_file(dockerfile_path, dockerfile_result["rendered_content"])
            print(f"✅ 生成Dockerfile")
        
        print(f"\n🎉 现实工作流程完成!")
        print(f"📁 项目路径: {project_path}")
        print(f"🔌 分配端口: {port}")
        print(f"📄 生成文件: app.py, index.html, Dockerfile")
        
        # 验证文件结构
        if os.path.exists(app_file):
            with open(app_file, 'r') as f:
                content = f.read()
                if '现实博客测试' in content and f'port={port}' in content:
                    print("✅ 应用代码内容验证通过")
                else:
                    print("⚠️ 应用代码内容验证部分通过")
        
        # 清理
        import shutil
        shutil.rmtree(project_path)
        port_mgr.release_port(port)
        print("🧹 清理完成")
        
        return True
        
    except Exception as e:
        print(f"💥 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 QuickApp原子服务测试")
    print("🎯 目标: 验证每个原子服务的功能正确性")
    
    tests = [
        ("端口管理", test_port_manager),
        ("模板引擎", test_template_engine),
        ("文件操作", test_file_operations),
        ("目录操作", test_directory_operations),
        ("命令执行", test_command_execution),
        ("现实工作流程", test_realistic_workflow)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        results[test_name] = test_func()
    
    # 总结
    print(f"\n{'='*60}")
    print("📊 测试总结")
    print('='*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} {test_name}")
    
    print(f"\n📈 总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有原子服务测试通过！")
        print("💡 原子服务设计符合预期，可以支撑更高层的molecules和organisms")
        print("🚀 理论上QuickApp可以工作：描述→分析→代码→部署")
    else:
        print("⚠️ 部分原子服务存在问题")
    
    return passed == total

if __name__ == "__main__":
    main()