#!/usr/bin/env python3
"""
测试QuickCodeMolecule接收PRD输入
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# 设置路径
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

from tools.services.terminal_service.services.molecules.app_analysis_molecule import AppAnalysisMolecule
from tools.services.terminal_service.services.molecules.quick_code_molecule import QuickCodeMolecule

async def test_prd_to_code():
    """测试从PRD生成代码"""
    
    print("🧪 测试PRD到代码生成")
    print("=" * 60)
    
    # 1. 使用AppAnalysisMolecule生成PRD
    print("\n📋 步骤1: 生成PRD")
    analyzer = AppAnalysisMolecule()
    
    description = "创建一个简单的任务管理工具，包含任务列表、创建、编辑和删除功能"
    analysis_result = await analyzer.analyze_app_description(description)
    
    if not analysis_result["success"]:
        print(f"❌ PRD生成失败: {analysis_result.get('error')}")
        return
    
    if "prd" not in analysis_result or analysis_result["prd"] is None:
        print(f"❌ 没有生成PRD: {analysis_result.get('prd_error')}")
        return
    
    prd = analysis_result["prd"]
    print(f"✅ PRD生成成功")
    print(f"   - 应用名称: {prd.get('app_name')}")
    print(f"   - 应用类型: {prd.get('app_type')}")
    print(f"   - 功能模块: {len(prd.get('features', []))}")
    
    # 2. 使用QuickCodeMolecule从PRD生成代码
    print(f"\n📋 步骤2: 从PRD生成代码")
    code_generator = QuickCodeMolecule()
    
    # 准备app_spec（包含PRD）
    app_spec = {
        "prd": prd,
        "port": 8020
    }
    
    code_result = code_generator.generate_app_code(app_spec)
    
    if not code_result["success"]:
        print(f"❌ 代码生成失败: {code_result.get('error')}")
        return
    
    print(f"✅ 代码生成成功")
    print(f"   - 项目路径: {code_result.get('project_path')}")
    print(f"   - 生成文件数: {code_result.get('generated_files')}")
    print(f"   - 失败文件: {code_result.get('failed_files', [])}")
    
    # 3. 检查生成的文件
    print(f"\n📋 步骤3: 检查生成的文件")
    project_path = code_result.get('project_path')
    
    if project_path and os.path.exists(project_path):
        print(f"✅ 项目目录存在: {project_path}")
        
        # 检查app.py
        app_py_path = os.path.join(project_path, "app.py")
        if os.path.exists(app_py_path):
            print(f"✅ app.py 文件存在")
            # 读取部分内容
            with open(app_py_path, 'r', encoding='utf-8') as f:
                content = f.read()[:500]
                print(f"   - 文件开头内容:")
                print(f"     {content}...")
        else:
            print(f"❌ app.py 文件不存在")
        
        # 检查requirements.txt
        req_path = os.path.join(project_path, "requirements.txt")
        if os.path.exists(req_path):
            print(f"✅ requirements.txt 文件存在")
            with open(req_path, 'r', encoding='utf-8') as f:
                req_content = f.read()
                print(f"   - 依赖列表:")
                for line in req_content.strip().split('\n')[:5]:
                    print(f"     {line}")
        else:
            print(f"❌ requirements.txt 文件不存在")
    
    print(f"\n🎉 PRD到代码生成测试完成!")

if __name__ == '__main__':
    asyncio.run(test_prd_to_code())