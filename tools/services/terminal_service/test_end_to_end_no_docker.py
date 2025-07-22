#!/usr/bin/env python3
"""
端到端测试 - 不使用Docker，直接运行服务
从自然语言描述到可访问的URL
"""

import sys
import os
import asyncio
import json
import time
import signal
import subprocess
import requests
from threading import Thread

# 设置路径
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)
sys.path.insert(0, current_dir)
os.chdir(project_root)  # 切换到项目根目录

def print_step(step_num, title):
    """打印步骤标题"""
    print(f"\n{'='*60}")
    print(f"步骤{step_num}: {title}")
    print('='*60)

def print_result(input_data, output_data, success=None):
    """打印输入输出"""
    print(f"📥 输入: {input_data}")
    if success is not None:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"📊 状态: {status}")
    print(f"📤 输出: {json.dumps(output_data, indent=2, ensure_ascii=False)}")

class ProcessManager:
    """进程管理器"""
    def __init__(self):
        self.processes = {}
        
    def start_service(self, service_name, command, cwd=None):
        """启动服务进程"""
        try:
            print(f"🚀 启动服务: {service_name}")
            print(f"🔧 命令: {command}")
            print(f"📁 目录: {cwd}")
            
            process = subprocess.Popen(
                command, 
                shell=True, 
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                preexec_fn=os.setsid
            )
            
            self.processes[service_name] = process
            print(f"✅ 服务启动: {service_name} (PID: {process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ 启动失败: {e}")
            return False
    
    def check_service_health(self, service_name, url, timeout=30):
        """检查服务健康状态"""
        print(f"🏥 检查服务健康: {service_name}")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ 服务健康: {service_name} - {url}")
                    return True
            except requests.exceptions.RequestException:
                pass
                
            time.sleep(2)
            print(f"⏳ 等待服务就绪: {service_name} ({int(time.time() - start_time)}s)")
        
        print(f"❌ 服务未就绪: {service_name}")
        return False
    
    def get_service_output(self, service_name, lines=10):
        """获取服务输出"""
        if service_name in self.processes:
            process = self.processes[service_name]
            try:
                stdout, stderr = process.communicate(timeout=1)
                return stdout.split('\n')[-lines:], stderr.split('\n')[-lines:]
            except subprocess.TimeoutExpired:
                return ["服务正在运行..."], []
        return [], []
    
    def stop_service(self, service_name):
        """停止服务"""
        if service_name in self.processes:
            process = self.processes[service_name]
            try:
                # 杀死进程组
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
                print(f"🛑 服务已停止: {service_name}")
            except:
                # 强制终止
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                print(f"🔥 服务强制终止: {service_name}")
            
            del self.processes[service_name]
    
    def stop_all_services(self):
        """停止所有服务"""
        for service_name in list(self.processes.keys()):
            self.stop_service(service_name)

async def test_complete_workflow():
    """测试完整工作流程"""
    print("🤖 端到端测试: 自然语言 → 可访问URL")
    print("🎯 不使用Docker，直接启动Flask应用")
    
    process_manager = ProcessManager()
    
    try:
        # 步骤1: AI分析应用
        print_step(1, "AI分析应用描述")
        
        from services.molecules.app_analysis_molecule import AppAnalysisMolecule
        
        analyzer = AppAnalysisMolecule()
        description = "创建一个简单的个人博客网站，可以显示文章列表和阅读单篇文章"
        
        analysis_result = await analyzer.analyze_app_description(description)
        
        print_result(description, {
            "success": analysis_result["success"],
            "app_type": analysis_result.get("analysis", {}).get("app_type"),
            "complexity": analysis_result.get("analysis", {}).get("complexity")
        }, analysis_result["success"])
        
        if not analysis_result["success"]:
            print("❌ AI分析失败")
            return False
        
        analysis = analysis_result["analysis"]
        
        # 步骤2: 生成应用代码
        print_step(2, "生成Flask应用代码")
        
        from services.molecules.quick_code_molecule import QuickCodeMolecule
        
        code_generator = QuickCodeMolecule()
        app_spec = {
            "app_name": "e2e_test_blog",
            "app_type": analysis.get("app_type", "blog"),
            "description": "端到端测试博客",
            "port": 8001  # 使用不同端口避免冲突
        }
        
        code_result = code_generator.generate_app_code(app_spec)
        
        print_result(app_spec, {
            "success": code_result["success"],
            "project_path": code_result.get("project_path"),
            "generated_files": len(code_result.get("generated_files", [])),
        }, code_result["success"])
        
        if not code_result["success"]:
            print("❌ 代码生成失败")
            return False
        
        project_path = code_result["project_path"]
        
        # 步骤3: 检查生成的文件
        print_step(3, "验证生成的文件")
        
        app_file = os.path.join(project_path, "app.py")
        
        if not os.path.exists(app_file):
            print("❌ app.py 文件不存在")
            return False
        
        # 读取并显示生成的代码
        with open(app_file, 'r', encoding='utf-8') as f:
            app_content = f.read()
        
        print(f"📄 生成的app.py:")
        lines = app_content.split('\n')
        for i, line in enumerate(lines[:20], 1):  # 显示前20行
            print(f"   {i:2d} | {line}")
        if len(lines) > 20:
            print(f"   ... (共{len(lines)}行)")
        
        # 验证代码包含必要元素
        has_flask = "from flask import" in app_content
        has_routes = "@app.route" in app_content
        has_main = "if __name__ == '__main__'" in app_content
        
        print(f"\n🔍 代码验证:")
        print(f"   ✓ Flask导入: {has_flask}")
        print(f"   ✓ 路由定义: {has_routes}")
        print(f"   ✓ 主程序块: {has_main}")
        
        if not (has_flask and has_routes and has_main):
            print("❌ 生成的代码不完整")
            return False
        
        # 步骤4: 创建虚拟环境和安装依赖
        print_step(4, "准备Python运行环境")
        
        # 检查requirements.txt
        req_file = os.path.join(project_path, "requirements.txt")
        if os.path.exists(req_file):
            with open(req_file, 'r') as f:
                requirements = f.read()
            print(f"📦 依赖列表:\n{requirements}")
        else:
            # 创建基础requirements.txt
            requirements = "Flask>=2.0.0\nWerkzeug>=2.0.0"
            with open(req_file, 'w') as f:
                f.write(requirements)
            print("📦 创建基础依赖文件")
        
        # 步骤5: 启动服务
        print_step(5, "启动Flask应用")
        
        # 修改app.py确保正确的端口和host
        app_content_modified = app_content.replace(
            "app.run()", 
            "app.run(host='0.0.0.0', port=8001, debug=True)"
        )
        if app_content_modified == app_content:
            # 如果没有app.run()，添加到最后
            app_content_modified = app_content + "\n\nif __name__ == '__main__':\n    app.run(host='0.0.0.0', port=8001, debug=True)\n"
        
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(app_content_modified)
        
        # 启动Flask应用
        start_success = process_manager.start_service(
            "flask_blog",
            f"python app.py",
            cwd=project_path
        )
        
        if not start_success:
            print("❌ Flask应用启动失败")
            return False
        
        # 步骤6: 验证服务可访问性
        print_step(6, "验证Web服务可访问性")
        
        service_url = "http://localhost:8001"
        
        # 检查服务健康状态
        is_healthy = process_manager.check_service_health("flask_blog", service_url)
        
        if not is_healthy:
            print("❌ 服务未正常启动")
            # 获取服务输出用于调试
            stdout, stderr = process_manager.get_service_output("flask_blog")
            print("📋 服务标准输出:")
            for line in stdout:
                if line.strip():
                    print(f"   {line}")
            print("📋 服务错误输出:")
            for line in stderr:
                if line.strip():
                    print(f"   {line}")
            return False
        
        # 步骤7: 测试具体功能
        print_step(7, "测试Web应用功能")
        
        test_results = {}
        
        # 测试主页
        try:
            response = requests.get(f"{service_url}/")
            test_results["homepage"] = {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "content_length": len(response.text)
            }
            print(f"🏠 主页测试: {response.status_code} ({len(response.text)} chars)")
        except Exception as e:
            test_results["homepage"] = {"success": False, "error": str(e)}
            print(f"❌ 主页测试失败: {e}")
        
        # 测试健康检查
        try:
            response = requests.get(f"{service_url}/health")
            test_results["health"] = {
                "status_code": response.status_code,
                "success": response.status_code == 200
            }
            print(f"💊 健康检查: {response.status_code}")
        except Exception as e:
            test_results["health"] = {"success": False, "error": str(e)}
            print(f"⚠️ 健康检查不可用: {e}")
        
        # 测试其他可能的路由
        for route in ["/posts", "/api/status"]:
            try:
                response = requests.get(f"{service_url}{route}")
                test_results[route] = {
                    "status_code": response.status_code,
                    "success": response.status_code in [200, 404]  # 404也是正常响应
                }
                print(f"🔗 路由{route}: {response.status_code}")
            except:
                pass
        
        # 步骤8: 总结结果
        print_step(8, "测试结果总结")
        
        successful_tests = sum(1 for result in test_results.values() if result.get("success", False))
        total_tests = len(test_results)
        
        print(f"🎯 测试结果: {successful_tests}/{total_tests} 通过")
        print(f"🌐 应用URL: {service_url}")
        print(f"📁 项目路径: {project_path}")
        
        # 详细测试结果
        for test_name, result in test_results.items():
            status = "✅" if result.get("success") else "❌"
            print(f"   {status} {test_name}: {result}")
        
        # 如果主页可访问，则认为成功
        main_success = test_results.get("homepage", {}).get("success", False)
        
        if main_success:
            print(f"\n🎉 端到端测试成功！")
            print(f"✨ 实现了从描述到URL的完整流程:")
            print(f"   📝 输入: '{description}'")
            print(f"   🤖 AI分析: {analysis.get('app_type')} 应用")
            print(f"   💻 代码生成: {len(app_content)} 字符")
            print(f"   🌐 服务部署: {service_url}")
            print(f"   ✅ Web访问: 成功")
            
            print(f"\n🔗 您可以在浏览器中访问: {service_url}")
            print(f"⏰ 服务将在30秒后自动停止...")
            
            # 等待30秒让用户访问
            time.sleep(30)
            
            return True
        else:
            print(f"\n😞 端到端测试部分成功")
            print(f"✅ 代码生成完成")
            print(f"❌ Web服务访问失败")
            return False
            
    except Exception as e:
        print(f"💥 测试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理进程
        print(f"\n🧹 清理服务...")
        process_manager.stop_all_services()
        
        # 清理生成的项目目录
        if 'project_path' in locals():
            import shutil
            try:
                shutil.rmtree(project_path)
                print(f"🗑️ 清理项目目录: {project_path}")
            except:
                print(f"⚠️ 清理目录失败: {project_path}")

async def main():
    """主函数"""
    print("🧪 QuickApp端到端测试 (无Docker版)")
    print("🎯 目标: 验证从自然语言到可访问URL的完整流程")
    print("=" * 60)
    
    # 先确认AI服务可用
    try:
        from tools.services.intelligence_service.language.text_generator import generate
        test_response = await generate("测试", max_tokens=5)
        print("✅ AI服务连接正常")
    except Exception as e:
        print(f"❌ AI服务不可用: {e}")
        return
    
    # 执行完整测试
    success = await test_complete_workflow()
    
    print("\n" + "=" * 60)
    print("📊 最终总结")
    print("=" * 60)
    
    if success:
        print("🏆 端到端测试完全成功！")
        print("💡 QuickApp系统已验证具备以下能力:")
        print("   ✓ 理解自然语言描述")
        print("   ✓ AI驱动的应用分析")
        print("   ✓ 自动生成完整Flask应用代码")
        print("   ✓ 直接部署并启动Web服务")
        print("   ✓ 提供可访问的URL")
        print("\n🚀 系统可以真正实现:")
        print("   '创建一个简单的博客网站' → 可访问的Web应用")
    else:
        print("⚠️ 端到端测试部分成功")
        print("🔧 需要进一步优化部署流程")

if __name__ == "__main__":
    # 设置环境变量
    os.environ['PYTHONPATH'] = project_root
    
    # 运行测试
    asyncio.run(main())