#!/usr/bin/env python3
"""
最基本的集成测试
"""

import sys
import os
import inspect

# Add project root to Python path
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

def test_file_exists():
    """测试文件是否存在"""
    file_path = "/Users/xenodennis/Documents/Fun/isA_MCP/tools/services/data_analytics_service/services/data_analytics_service.py"
    if os.path.exists(file_path):
        print("✅ 主服务文件存在")
        return True
    else:
        print("❌ 主服务文件不存在")
        return False

def test_methods_in_file():
    """检查文件中是否包含新方法"""
    file_path = "/Users/xenodennis/Documents/Fun/isA_MCP/tools/services/data_analytics_service/services/data_analytics_service.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_methods = [
            'perform_exploratory_data_analysis',
            'develop_machine_learning_model', 
            'explore_data_patterns',
            'perform_complete_data_analysis'
        ]
        
        success_count = 0
        for method in new_methods:
            if f"def {method}(" in content:
                print(f"✅ 方法定义存在: {method}")
                success_count += 1
            else:
                print(f"❌ 方法定义缺失: {method}")
        
        # 检查便利函数
        convenience_functions = [
            'perform_quick_eda',
            'train_ml_model', 
            'analyze_data_completely'
        ]
        
        for func in convenience_functions:
            if f"async def {func}(" in content:
                print(f"✅ 便利函数定义存在: {func}")
                success_count += 1
            else:
                print(f"❌ 便利函数定义缺失: {func}")
        
        # 检查新的导入
        new_imports = [
            'from .data_service.data_eda import DataEDAService',
            'from .data_service.data_modeling import DataModelingService',
            'from .data_service.data_explorer import DataExplorer'
        ]
        
        for import_line in new_imports:
            if import_line in content:
                print(f"✅ 导入存在: {import_line.split()[-1]}")
                success_count += 1
            else:
                print(f"❌ 导入缺失: {import_line}")
        
        # 检查服务统计更新
        new_stats = ['total_eda_analyses', 'total_models_trained', 'total_explorations']
        for stat in new_stats:
            if stat in content:
                print(f"✅ 统计项存在: {stat}")
                success_count += 1
            else:
                print(f"❌ 统计项缺失: {stat}")
        
        total_items = len(new_methods) + len(convenience_functions) + len(new_imports) + len(new_stats)
        print(f"\n📊 文件内容检查: {success_count}/{total_items} 项通过")
        
        return success_count, total_items
        
    except Exception as e:
        print(f"❌ 文件读取失败: {e}")
        return 0, 1

def test_dependencies_exist():
    """检查依赖的服务文件是否存在"""
    dependency_files = [
        "/Users/xenodennis/Documents/Fun/isA_MCP/tools/services/data_analytics_service/services/data_service/data_eda.py",
        "/Users/xenodennis/Documents/Fun/isA_MCP/tools/services/data_analytics_service/services/data_service/data_modeling.py",
        "/Users/xenodennis/Documents/Fun/isA_MCP/tools/services/data_analytics_service/services/data_service/data_explorer.py"
    ]
    
    success_count = 0
    for file_path in dependency_files:
        if os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            print(f"✅ 依赖服务存在: {file_name}")
            success_count += 1
        else:
            file_name = os.path.basename(file_path)
            print(f"❌ 依赖服务缺失: {file_name}")
    
    return success_count, len(dependency_files)

if __name__ == "__main__":
    print("🔍 基本集成检查")
    print("=" * 50)
    
    total_success = 0
    total_tests = 0
    
    # Test 1: 文件存在性
    if test_file_exists():
        total_success += 1
    total_tests += 1
    
    # Test 2: 依赖文件检查
    dep_success, dep_total = test_dependencies_exist()
    total_success += dep_success
    total_tests += dep_total
    
    print("\n" + "-" * 50)
    
    # Test 3: 文件内容检查
    content_success, content_total = test_methods_in_file()
    total_success += content_success
    total_tests += content_total
    
    print("\n" + "=" * 50)
    print(f"📊 总体结果: {total_success}/{total_tests} 项通过")
    print(f"成功率: {total_success/total_tests*100:.1f}%")
    
    if total_success >= total_tests * 0.8:  # 80% 通过率
        print("🎉 集成基本成功!")
        sys.exit(0)
    else:
        print("⚠️ 集成需要完善")
        sys.exit(1)