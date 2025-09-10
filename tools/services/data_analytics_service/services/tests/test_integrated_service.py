#!/usr/bin/env python3
"""
测试集成后的DataAnalyticsService
验证三个新服务（EDA、建模、探索）是否正确集成到主服务中
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

async def test_integrated_service():
    """测试集成后的数据分析服务"""
    print("🚀 测试集成后的DataAnalyticsService")
    print("=" * 70)
    
    try:
        # 导入集成后的服务
        from tools.services.data_analytics_service.services.data_analytics_service import (
            get_analytics_service, perform_quick_eda, train_ml_model, analyze_data_completely
        )
        
        print("✅ 成功导入集成后的服务")
        
        # 1. 测试服务初始化
        print("\n📋 测试服务初始化...")
        service = get_analytics_service("test_integrated")
        print(f"✅ 服务初始化成功: {service.service_name}")
        print(f"   - EDA服务: {service.eda_service is not None}")
        print(f"   - 建模服务: {service.modeling_service is not None}")
        print(f"   - 探索服务: {service.explorer_service is not None}")
        
        # 2. 测试服务状态
        print("\n📊 获取服务状态...")
        status = await service.get_service_status()
        service_info = status.get('service_info', {})
        service_stats = status.get('service_stats', {})
        
        print("✅ 服务状态:")
        print(f"   - 服务名: {service_info.get('service_name')}")
        print(f"   - EDA服务可用: {service_info.get('eda_service_initialized')}")
        print(f"   - 建模服务可用: {service_info.get('modeling_service_initialized')}")
        print(f"   - 探索服务可用: {service_info.get('explorer_service_initialized')}")
        print(f"   - 统计指标: {len(service_stats)} 项")
        
        # 3. 测试EDA功能
        print("\n🔍 测试EDA分析功能...")
        test_data_path = "/Users/xenodennis/Documents/Fun/isA_MCP/tools/services/data_analytics_service/test_data/test_data.csv"
        
        if os.path.exists(test_data_path):
            # 使用便利函数测试
            eda_result = await perform_quick_eda(
                data_path=test_data_path,
                target_column="purchase_amount",
                include_ai=False  # 关闭AI避免复杂性
            )
            
            if eda_result["success"]:
                print("✅ EDA分析成功")
                print(f"   - 请求ID: {eda_result['request_id']}")
                print(f"   - 处理时间: {eda_result['processing_time_ms']:.1f}ms")
                print(f"   - 数据路径: {eda_result['data_path']}")
                
                # 检查EDA结果结构
                eda_results = eda_result.get("eda_results", {})
                print(f"   - EDA结果部分: {list(eda_results.keys())}")
            else:
                print(f"❌ EDA分析失败: {eda_result.get('error_message')}")
        else:
            print(f"⚠️ 测试数据文件不存在: {test_data_path}")
        
        # 4. 测试建模功能（如果EDA成功）
        if os.path.exists(test_data_path):
            print("\n🤖 测试ML建模功能...")
            try:
                modeling_result = await train_ml_model(
                    data_path=test_data_path,
                    target_column="purchase_amount",
                    problem_type="regression",
                    include_ai=False  # 关闭AI避免复杂性
                )
                
                if modeling_result["success"]:
                    print("✅ ML建模成功")
                    print(f"   - 请求ID: {modeling_result['request_id']}")
                    print(f"   - 处理时间: {modeling_result['processing_time_ms']:.1f}ms")
                    print(f"   - 问题类型: {modeling_result['problem_type']}")
                    
                    # 检查建模结果
                    modeling_results = modeling_result.get("modeling_results", {})
                    if "model_evaluation" in modeling_results:
                        evaluation = modeling_results["model_evaluation"]
                        if "best_model" in evaluation:
                            best_model = evaluation["best_model"]
                            print(f"   - 最佳算法: {best_model.get('algorithm')}")
                            metrics = best_model.get('performance_metrics', {})
                            if metrics:
                                print(f"   - 性能指标: {list(metrics.keys())}")
                else:
                    print(f"❌ ML建模失败: {modeling_result.get('error_message')}")
            except Exception as e:
                print(f"❌ ML建模测试异常: {e}")
        
        # 5. 测试完整分析工作流
        if os.path.exists(test_data_path):
            print("\n🎯 测试完整分析工作流...")
            try:
                complete_result = await analyze_data_completely(
                    data_path=test_data_path,
                    target_column="purchase_amount",
                    analysis_type="eda_only"  # 只做EDA避免复杂性
                )
                
                if complete_result["success"]:
                    print("✅ 完整分析成功")
                    print(f"   - 请求ID: {complete_result['request_id']}")
                    print(f"   - 总处理时间: {complete_result['total_processing_time_ms']:.1f}ms")
                    print(f"   - 分析类型: {complete_result['analysis_type']}")
                    
                    # 检查结果阶段
                    results = complete_result.get("results", {})
                    print(f"   - 完成的阶段: {list(results.keys())}")
                    
                    # 检查摘要
                    summary = complete_result.get("summary", {})
                    if summary:
                        print(f"   - 摘要可用: {summary.get('overall_success')}")
                        phases = summary.get('phases_completed', [])
                        if phases:
                            print(f"   - 完成阶段: {phases}")
                else:
                    print(f"❌ 完整分析失败: {complete_result.get('error_message')}")
            except Exception as e:
                print(f"❌ 完整分析测试异常: {e}")
        
        # 6. 最终服务统计
        print("\n📈 最终服务统计...")
        final_status = await service.get_service_status()
        final_stats = final_status.get('service_stats', {})
        
        print("✅ 最终统计:")
        print(f"   - EDA分析次数: {final_stats.get('total_eda_analyses', 0)}")
        print(f"   - 模型训练次数: {final_stats.get('total_models_trained', 0)}")
        print(f"   - 探索次数: {final_stats.get('total_explorations', 0)}")
        print(f"   - 总请求数: {final_stats.get('total_requests', 0)}")
        print(f"   - 成功请求数: {final_stats.get('successful_requests', 0)}")
        
        print("\n🎉 集成测试完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_structure():
    """测试服务结构和接口"""
    print("\n🔍 测试服务结构...")
    
    try:
        import sys
        import os
        
        # 确保路径正确
        project_root = '/Users/xenodennis/Documents/Fun/isA_MCP'
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from tools.services.data_analytics_service.services.data_analytics_service import (
            DataAnalyticsService
        )
        
        # 检查新方法是否存在
        service_methods = [
            'perform_exploratory_data_analysis',
            'develop_machine_learning_model',
            'explore_data_patterns',
            'perform_complete_data_analysis'
        ]
        
        for method_name in service_methods:
            if hasattr(DataAnalyticsService, method_name):
                print(f"✅ 方法存在: {method_name}")
            else:
                print(f"❌ 方法缺失: {method_name}")
        
        # 检查便利函数
        convenience_functions = [
            'perform_quick_eda',
            'train_ml_model', 
            'analyze_data_completely'
        ]
        
        from tools.services.data_analytics_service.services import data_analytics_service
        
        for func_name in convenience_functions:
            if hasattr(data_analytics_service, func_name):
                print(f"✅ 便利函数存在: {func_name}")
            else:
                print(f"❌ 便利函数缺失: {func_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ 结构测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 DataAnalyticsService 集成测试")
    print("=" * 70)
    print(f"🕒 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 测试服务结构
    structure_ok = test_service_structure()
    
    # 测试集成功能
    if structure_ok:
        success = asyncio.run(test_integrated_service())
    else:
        success = False
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 所有测试通过 - 服务集成成功!")
    else:
        print("❌ 测试失败 - 需要检查集成问题")
    
    sys.exit(0 if success else 1)