#!/usr/bin/env python3
"""
简单的集成测试 - 验证DataAnalyticsService集成成功
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

def test_integration():
    """测试集成"""
    print("🧪 简单集成测试")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Basic imports
    total_tests += 1
    try:
        from tools.services.data_analytics_service.services.data_analytics_service import DataAnalyticsService
        print("✅ DataAnalyticsService 导入成功")
        success_count += 1
    except Exception as e:
        print(f"❌ DataAnalyticsService 导入失败: {e}")
    
    # Test 2: Service creation
    total_tests += 1
    try:
        service = DataAnalyticsService("test_db")
        print("✅ DataAnalyticsService 创建成功")
        success_count += 1
    except Exception as e:
        print(f"❌ DataAnalyticsService 创建失败: {e}")
        return success_count, total_tests
    
    # Test 3: Check new methods exist
    new_methods = [
        'perform_exploratory_data_analysis',
        'develop_machine_learning_model', 
        'explore_data_patterns',
        'perform_complete_data_analysis'
    ]
    
    for method in new_methods:
        total_tests += 1
        if hasattr(service, method):
            print(f"✅ 方法存在: {method}")
            success_count += 1
        else:
            print(f"❌ 方法缺失: {method}")
    
    # Test 4: Check service properties
    total_tests += 1
    if hasattr(service, 'eda_service'):
        print("✅ eda_service 属性存在")
        success_count += 1
    else:
        print("❌ eda_service 属性缺失")
    
    total_tests += 1
    if hasattr(service, 'modeling_service'):
        print("✅ modeling_service 属性存在")
        success_count += 1
    else:
        print("❌ modeling_service 属性缺失")
    
    total_tests += 1
    if hasattr(service, 'explorer_service'):
        print("✅ explorer_service 属性存在")
        success_count += 1
    else:
        print("❌ explorer_service 属性缺失")
    
    # Test 5: Check updated stats structure
    total_tests += 1
    expected_stats = ['total_eda_analyses', 'total_models_trained', 'total_explorations']
    stats_ok = all(stat in service.service_stats for stat in expected_stats)
    if stats_ok:
        print("✅ 服务统计结构正确")
        success_count += 1
    else:
        print("❌ 服务统计结构不完整")
    
    # Test 6: Test convenience functions import
    total_tests += 1
    try:
        from tools.services.data_analytics_service.services.data_analytics_service import (
            perform_quick_eda, train_ml_model, analyze_data_completely
        )
        print("✅ 便利函数导入成功")
        success_count += 1
    except Exception as e:
        print(f"❌ 便利函数导入失败: {e}")
    
    return success_count, total_tests

if __name__ == "__main__":
    success, total = test_integration()
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {success}/{total} 通过")
    print(f"成功率: {success/total*100:.1f}%")
    
    if success == total:
        print("🎉 集成完全成功!")
        sys.exit(0)
    else:
        print("⚠️ 部分集成问题")
        sys.exit(1)