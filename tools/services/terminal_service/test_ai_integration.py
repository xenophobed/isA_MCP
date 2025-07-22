#!/usr/bin/env python3
"""
测试AI服务与QuickApp的集成
"""

import sys
import os
import asyncio
import json

# 设置PYTHONPATH
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

async def test_ai_app_analysis():
    """测试AI驱动的应用分析"""
    print("🧪 测试AI驱动的应用分析")
    print("=" * 50)
    
    try:
        # 导入AI服务
        from tools.services.intelligence_service.language.text_generator import generate
        
        # 模拟AppAnalysisMolecule的AI分析逻辑
        description = "创建一个简单的博客网站，可以发布文章和查看文章列表"
        
        prompt = f"""分析以下应用描述，返回JSON格式的分析结果：

描述: {description}

请分析：
1. 应用类型 (web/api/blog/dashboard/chat/ecommerce/tool)
2. 主要功能列表
3. 推荐的技术栈
4. 复杂度级别 (simple/medium/complex)
5. 核心特性

返回格式：
{{
    "app_type": "类型",
    "main_features": ["功能1", "功能2"],
    "tech_stack": ["技术1", "技术2"],
    "complexity": "级别",
    "core_features": ["特性1", "特性2"]
}}

只返回JSON，不要其他说明。"""

        print(f"📥 输入描述: {description}")
        print("🤖 AI分析中...")
        
        ai_response = await generate(prompt, temperature=0.3, max_tokens=300)
        print(f"📤 AI响应: {ai_response}")
        
        try:
            analysis = json.loads(ai_response.strip())
            print(f"✅ JSON解析成功:")
            print(f"   应用类型: {analysis.get('app_type')}")
            print(f"   复杂度: {analysis.get('complexity')}")
            print(f"   主要功能: {analysis.get('main_features')}")
            print(f"   技术栈: {analysis.get('tech_stack')}")
            return analysis
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print("🔧 AI返回的不是有效JSON格式")
            return None
            
    except Exception as e:
        print(f"💥 AI分析异常: {e}")
        return None

async def test_ai_code_generation():
    """测试AI驱动的代码生成"""
    print("\n🧪 测试AI驱动的代码生成") 
    print("=" * 50)
    
    try:
        from tools.services.intelligence_service.language.text_generator import generate
        
        app_name = "AI博客网站"
        app_type = "blog"
        
        prompt = f"""为{app_type}应用'{app_name}'生成Flask主程序代码。

要求:
1. 包含Flask应用初始化
2. 添加路由: 主页(/)、文章列表(/posts)、健康检查(/health)
3. 包含错误处理和日志设置
4. 支持环境变量PORT配置
5. 添加中文注释

只返回Python代码，不要markdown格式。"""

        print(f"📥 应用规格: {app_name} ({app_type})")
        print("🤖 AI代码生成中...")
        
        generated_code = await generate(prompt, temperature=0.2, max_tokens=800)
        print(f"📤 生成代码长度: {len(generated_code)} 字符")
        
        # 验证生成的代码
        if "from flask import" in generated_code and "@app.route" in generated_code:
            print("✅ 代码验证通过:")
            print("   ✓ 包含Flask导入")
            print("   ✓ 包含路由定义")
            
            # 显示代码片段
            lines = generated_code.split('\n')
            print(f"\n📄 代码预览 (前15行):")
            for i, line in enumerate(lines[:15], 1):
                print(f"   {i:2d} | {line}")
            if len(lines) > 15:
                print(f"   ... (共{len(lines)}行)")
            
            return generated_code
        else:
            print("❌ 代码验证失败: 缺少必要的Flask元素")
            return None
            
    except Exception as e:
        print(f"💥 代码生成异常: {e}")
        return None

async def test_ai_requirements_generation():
    """测试AI生成requirements.txt"""
    print("\n🧪 测试AI生成requirements.txt")
    print("=" * 50)
    
    try:
        from tools.services.intelligence_service.language.text_generator import generate
        
        prompt = """为一个Flask博客应用生成requirements.txt文件内容。

要求包含:
1. Flask框架和相关依赖
2. 数据库ORM (SQLAlchemy)
3. 开发和部署工具
4. 指定合理的版本号

只返回requirements.txt的内容，每行一个依赖包。"""

        print("🤖 AI生成依赖列表...")
        
        requirements = await generate(prompt, temperature=0.1, max_tokens=200)
        print(f"📤 生成的requirements.txt:")
        print(requirements)
        
        # 验证内容
        lines = requirements.strip().split('\n')
        has_flask = any('flask' in line.lower() for line in lines)
        has_versions = any('==' in line or '>=' in line for line in lines)
        
        if has_flask and has_versions:
            print(f"✅ Requirements验证通过:")
            print(f"   ✓ 包含Flask: {has_flask}")
            print(f"   ✓ 指定版本: {has_versions}")
            print(f"   ✓ 依赖数量: {len([l for l in lines if l.strip()])}")
            return requirements
        else:
            print(f"❌ Requirements验证失败")
            return None
            
    except Exception as e:
        print(f"💥 Requirements生成异常: {e}")
        return None

async def test_complete_ai_workflow():
    """测试完整的AI工作流程"""
    print("\n🧪 测试完整AI工作流程")
    print("=" * 60)
    
    description = "创建一个简单的个人博客网站，支持文章发布和阅读"
    
    print(f"🎯 目标: 从描述 → AI分析 → AI代码生成")
    print(f"📝 输入: {description}")
    
    # 步骤1: AI分析
    print(f"\n🔍 步骤1: AI应用分析")
    analysis = await test_ai_app_analysis()
    
    if not analysis:
        print("❌ AI分析失败，流程终止")
        return False
    
    # 步骤2: AI代码生成
    print(f"\n💻 步骤2: AI代码生成")
    generated_code = await test_ai_code_generation()
    
    if not generated_code:
        print("❌ AI代码生成失败，流程终止")
        return False
    
    # 步骤3: AI依赖生成
    print(f"\n📦 步骤3: AI依赖生成")
    requirements = await test_ai_requirements_generation()
    
    if not requirements:
        print("❌ AI依赖生成失败，流程终止")
        return False
    
    # 步骤4: 组合原子服务写入文件
    print(f"\n📁 步骤4: 使用原子服务写入文件")
    try:
        # 导入原子服务
        sys.path.insert(0, current_dir)
        from services.atomic.directory_operations import DirectoryOperations
        from services.atomic.file_operations import FileOperations
        
        # 创建项目目录
        dir_ops = DirectoryOperations()
        project_path = "/tmp/ai_generated_blog"
        
        dir_result = dir_ops.create_directory(project_path)
        if not dir_result["success"]:
            print("❌ 目录创建失败")
            return False
        
        # 创建子目录
        struct_result = dir_ops.create_directory_structure(project_path, ["templates"])
        
        # 写入生成的代码
        file_ops = FileOperations()
        
        app_result = file_ops.create_file(
            os.path.join(project_path, "app.py"), 
            generated_code, 
            executable=True
        )
        
        req_result = file_ops.create_file(
            os.path.join(project_path, "requirements.txt"), 
            requirements
        )
        
        if app_result["success"] and req_result["success"]:
            print("✅ 文件写入成功:")
            print(f"   📄 {project_path}/app.py ({len(generated_code)} 字符)")
            print(f"   📄 {project_path}/requirements.txt")
            
            # 清理
            import shutil
            shutil.rmtree(project_path)
            print("🧹 清理完成")
            
            return True
        else:
            print("❌ 文件写入失败")
            return False
            
    except Exception as e:
        print(f"💥 文件写入异常: {e}")
        return False

async def main():
    """主测试函数"""
    print("🤖 AI服务集成测试")
    print("🎯 验证AI服务能否支撑QuickApp的智能化流程")
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
    success = await test_complete_ai_workflow()
    
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    if success:
        print("🎉 AI集成测试成功！")
        print("💭 验证了以下能力:")
        print("   ✓ AI理解自然语言描述")
        print("   ✓ AI分析应用需求并输出结构化数据")  
        print("   ✓ AI生成完整的Flask应用代码")
        print("   ✓ AI生成项目依赖配置")
        print("   ✓ 与原子服务的集成工作流程")
        print("\n🚀 理论上QuickApp完全可以实现:")
        print("   '创建一个简单的博客网站' → 可访问的URL")
    else:
        print("😞 AI集成测试失败")
        print("🔧 需要修复AI服务集成问题")

if __name__ == "__main__":
    # 设置环境变量确保AI服务能正常工作
    os.environ['PYTHONPATH'] = project_root
    asyncio.run(main())