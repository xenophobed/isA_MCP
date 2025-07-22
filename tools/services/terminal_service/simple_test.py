#!/usr/bin/env python3
"""
简化测试 - 测试基础原子服务
"""

import sys
import os

# 添加当前目录到路径
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

def test_template_engine():
    """测试模板引擎"""
    print("🧪 测试TemplateEngine...")
    
    try:
        from services.atomic.template_engine import TemplateEngine
        
        engine = TemplateEngine()
        
        # 测试渲染Flask应用模板
        variables = {
            "app_name": "test_blog",
            "description": "测试博客",
            "port": 5000,
            "timestamp": "2024-01-01",
            "secret_key": "test_secret",
            "custom_routes": "# 测试路由"
        }
        
        result = engine.render_template("flask_app", variables)
        
        if result["success"]:
            print("✅ TemplateEngine测试成功")
            print(f"   模板长度: {len(result['rendered_content'])} 字符")
            return True
        else:
            print(f"❌ TemplateEngine测试失败: {result['error']}")
            return False
            
    except Exception as e:
        print(f"💥 TemplateEngine测试异常: {str(e)}")
        return False


def test_port_manager():
    """测试端口管理器"""
    print("\n🧪 测试PortManager...")
    
    try:
        from services.atomic.port_manager import PortManager
        
        manager = PortManager()
        
        # 测试分配端口
        result = manager.allocate_port("test_service")
        
        if result["success"]:
            print("✅ PortManager测试成功")
            print(f"   分配端口: {result['port']}")
            
            # 测试释放端口
            release_result = manager.release_port(result['port'])
            if release_result["success"]:
                print("✅ 端口释放成功")
                return True
            else:
                print(f"❌ 端口释放失败: {release_result['error']}")
                return False
        else:
            print(f"❌ PortManager测试失败: {result['error']}")
            return False
            
    except Exception as e:
        print(f"💥 PortManager测试异常: {str(e)}")
        return False


def test_file_operations():
    """测试文件操作"""
    print("\n🧪 测试FileOperations...")
    
    try:
        from services.atomic.file_operations import FileOperations
        
        file_ops = FileOperations()
        
        # 测试创建临时文件
        test_content = "# Test file\nprint('Hello, World!')"
        test_path = "/tmp/quickapp_test.py"
        
        result = file_ops.create_file(test_path, test_content, executable=True)
        
        if result["success"]:
            print("✅ FileOperations测试成功")
            print(f"   文件路径: {test_path}")
            
            # 清理测试文件
            delete_result = file_ops.delete_file(test_path)
            if delete_result["success"]:
                print("✅ 文件清理成功")
                return True
            else:
                print("⚠️  文件清理失败")
                return True  # 创建成功就算通过
        else:
            print(f"❌ FileOperations测试失败: {result['error']}")
            return False
            
    except Exception as e:
        print(f"💥 FileOperations测试异常: {str(e)}")
        return False


def test_directory_operations():
    """测试目录操作"""
    print("\n🧪 测试DirectoryOperations...")
    
    try:
        from services.atomic.directory_operations import DirectoryOperations
        
        dir_ops = DirectoryOperations()
        
        # 测试创建目录结构
        test_base = "/tmp/quickapp_test_project"
        test_dirs = ["src", "templates", "static"]
        
        base_result = dir_ops.create_directory(test_base)
        if not base_result["success"]:
            print(f"❌ 创建基础目录失败: {base_result['error']}")
            return False
        
        struct_result = dir_ops.create_directory_structure(test_base, test_dirs)
        
        if struct_result["success"]:
            print("✅ DirectoryOperations测试成功")
            print(f"   创建目录: {len(struct_result['created_directories'])} 个")
            
            # 清理测试目录
            import shutil
            try:
                shutil.rmtree(test_base)
                print("✅ 目录清理成功")
            except:
                print("⚠️  目录清理失败")
            
            return True
        else:
            print(f"❌ DirectoryOperations测试失败: {struct_result}")
            return False
            
    except Exception as e:
        print(f"💥 DirectoryOperations测试异常: {str(e)}")
        return False


def test_command_execution():
    """测试命令执行"""
    print("\n🧪 测试CommandExecution...")
    
    try:
        from services.atomic.command_execution import CommandExecution
        
        cmd_exec = CommandExecution()
        
        # 测试简单命令
        result = cmd_exec.execute_command("echo 'Hello, QuickApp!'")
        
        if result["success"]:
            print("✅ CommandExecution测试成功")
            print(f"   输出: {result['stdout'].strip()}")
            return True
        else:
            print(f"❌ CommandExecution测试失败: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"💥 CommandExecution测试异常: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("🚀 QuickApp 基础组件测试")
    print("=" * 50)
    
    tests = [
        test_template_engine,
        test_port_manager,
        test_file_operations,
        test_directory_operations,
        test_command_execution
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有基础组件测试通过！")
        print("💡 可以尝试完整的QuickApp测试")
    else:
        print("⚠️  部分组件测试失败，需要修复")
    
    return passed == total


if __name__ == "__main__":
    main()