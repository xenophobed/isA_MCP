#!/usr/bin/env python3
"""
示例：如何使用PICS提取和TestID过滤服务

这个例子展示了两个服务的通用性：
1. 没有hardcoded数据
2. 可以处理任何Excel输入
3. 可以配置任何spec_id
"""

from pathlib import Path
from typing import List, Dict, Any

# 导入服务
from pics_extraction_service import PICSExtractionService, PICSExtractionResult
from testid_filter_service import TestIDFilterService, FilterResult
from testid_mapping_service import TestIDMappingService, MappingResult


def process_test_plan(excel_path: str, 
                      spec_id: str = "365212",
                      db_path: str = None) -> Dict[str, Any]:
    """
    完整的测试计划处理流程
    
    Args:
        excel_path: 用户的PICS Excel文件路径
        spec_id: 规范ID (如365212表示36.521-2, 385212表示38.521-2等)
        db_path: 数据库路径（可选）
        
    Returns:
        包含完整处理结果的字典
    """
    results = {}
    
    # =============================
    # 步骤1: 提取PICS数据
    # =============================
    print("=" * 50)
    print("步骤1: 提取PICS数据")
    print("=" * 50)
    
    # 创建PICS提取服务实例
    pics_service = PICSExtractionService()
    
    # 提取PICS（可以处理任何Excel文件）
    pics_result = pics_service.extract_from_excel(
        file_path=excel_path,
        process_all_sheets=True  # 处理所有3GPP sheets
    )
    
    print(f"✅ 提取了 {pics_result.true_items} 个TRUE项目")
    print(f"   - Band信息: {len(pics_result.band_info)} 个")
    print(f"   - 详细Band: {len(pics_result.detailed_bands)} 个")
    print(f"   - Features: {len(pics_result.features)} 个")
    
    # 保存结果
    results['pics_extraction'] = {
        'total_items': pics_result.total_items,
        'true_items': pics_result.true_items,
        'band_count': len(pics_result.band_info),
        'detailed_band_count': len(pics_result.detailed_bands),
        'feature_count': len(pics_result.features),
        'spec_id': pics_result.spec_id
    }
    
    # =============================
    # 步骤2: 过滤测试ID
    # =============================
    print("\n" + "=" * 50)
    print("步骤2: 根据条件过滤测试ID")
    print("=" * 50)
    
    # 创建TestID过滤服务实例
    filter_service = TestIDFilterService(db_path=db_path)
    
    try:
        # 将PICS项目转换为字典格式
        pics_dicts = [item.to_dict() for item in pics_result.pics_items]
        
        # 过滤测试ID（可以使用任何spec_id）
        filter_result = filter_service.filter_test_ids(
            pics_items=pics_dicts,
            spec_id=spec_id
        )
        
        print(f"✅ 过滤结果:")
        print(f"   - 评估测试: {filter_result.total_evaluated} 个")
        print(f"   - 匹配测试: {filter_result.matched_count} 个")
        print(f"   - 匹配率: {filter_result.matched_count/filter_result.total_evaluated*100:.1f}%")
        
        # 显示评估分布
        print(f"\n   评估分布:")
        for eval_type, count in filter_result.evaluation_breakdown.items():
            if count > 0:
                print(f"     {eval_type}: {count}")
        
        # 保存结果
        results['test_filtering'] = {
            'spec_id': spec_id,
            'total_evaluated': filter_result.total_evaluated,
            'matched_count': filter_result.matched_count,
            'match_rate': filter_result.matched_count/filter_result.total_evaluated*100,
            'matched_test_ids': filter_result.matched_test_ids,
            'evaluation_breakdown': filter_result.evaluation_breakdown
        }
        
    finally:
        # 断开数据库连接
        filter_service.disconnect()
    
    # =============================
    # 步骤3: 映射测试ID格式
    # =============================
    print("\n" + "=" * 50)
    print("步骤3: 映射测试ID到标准格式")
    print("=" * 50)
    
    # 创建映射服务实例
    mapping_service = TestIDMappingService(db_path=db_path)
    
    try:
        # 映射测试ID（从36.521-2到36.521-1格式）
        mapping_result = mapping_service.map_test_ids(
            test_ids=filter_result.matched_test_ids,
            source_spec=spec_id,
            target_spec=spec_id[:-1] + "1"  # 365212 -> 365211
        )
        
        print(f"✅ 映射结果:")
        print(f"   - 输入测试: {mapping_result.total_input} 个")
        print(f"   - 成功映射: {mapping_result.successfully_mapped} 个")
        print(f"   - 独特映射: {mapping_result.metadata.get('unique_mappings', 0)} 个")
        
        # 显示映射源分布
        print(f"\n   映射源分布:")
        for source, count in mapping_result.mapping_stats.items():
            if count > 0:
                print(f"     {source}: {count}")
        
        # 保存结果
        results['test_mapping'] = {
            'total_input': mapping_result.total_input,
            'successfully_mapped': mapping_result.successfully_mapped,
            'unique_mappings': mapping_result.metadata.get('unique_mappings', 0),
            'mapping_stats': mapping_result.mapping_stats,
            'mapped_test_ids': [m.mapped_id for m in mapping_result.mapped_ids]
        }
        
    finally:
        # 断开数据库连接
        mapping_service.disconnect()
    
    # =============================
    # 步骤4: 后续处理（待实现）
    # =============================
    print("\n" + "=" * 50)
    print("步骤4: 后续处理")
    print("=" * 50)
    
    print(f"✅ 准备进行:")
    print(f"   - 参数展开（使用{len(pics_result.band_info)}个bands）")
    print(f"   - 标准验证（PTCRB/GCF）")
    print(f"   - Excel生成")
    
    return results


def example_different_specs():
    """演示处理不同规范的示例"""
    
    # 示例1: 处理36.521-2规范
    print("\n示例1: 处理36.521-2规范")
    result1 = process_test_plan(
        excel_path="user_pics_36521.xlsx",  # 任何Excel文件
        spec_id="365212",  # 36.521-2
        db_path="database/testplan.duckdb"
    )
    
    # 示例2: 处理38.521-2规范
    print("\n示例2: 处理38.521-2规范")
    result2 = process_test_plan(
        excel_path="user_pics_38521.xlsx",  # 任何Excel文件
        spec_id="385212",  # 38.521-2
        db_path="database/testplan.duckdb"
    )
    
    # 示例3: 处理34.123-2规范
    print("\n示例3: 处理34.123-2规范")
    result3 = process_test_plan(
        excel_path="user_pics_34123.xlsx",  # 任何Excel文件
        spec_id="341232",  # 34.123-2
        db_path="database/testplan.duckdb"
    )


def example_batch_processing():
    """批量处理多个文件的示例"""
    
    excel_files = [
        "customer1_pics.xlsx",
        "customer2_pics.xlsx",
        "customer3_pics.xlsx"
    ]
    
    all_results = []
    
    for excel_file in excel_files:
        print(f"\n处理文件: {excel_file}")
        try:
            result = process_test_plan(
                excel_path=excel_file,
                spec_id="365212",  # 可以根据文件动态确定
                db_path="database/testplan.duckdb"
            )
            all_results.append(result)
        except Exception as e:
            print(f"⚠️ 处理失败: {e}")
            continue
    
    # 汇总结果
    print("\n批量处理汇总:")
    for i, result in enumerate(all_results):
        print(f"文件{i+1}: {result['test_filtering']['matched_count']} 个匹配测试")


def example_api_usage():
    """作为API使用的示例"""
    
    class TestPlanAPI:
        """测试计划处理API"""
        
        def __init__(self, db_path: str = None):
            self.pics_service = PICSExtractionService()
            self.filter_service = TestIDFilterService(db_path=db_path)
            self.mapping_service = TestIDMappingService(db_path=db_path)
        
        def process(self, excel_path: str, spec_id: str) -> Dict[str, Any]:
            """处理测试计划"""
            # 步骤1: 提取PICS
            pics_result = self.pics_service.extract_from_excel(excel_path)
            
            # 步骤2: 过滤测试
            pics_dicts = [item.to_dict() for item in pics_result.pics_items]
            filter_result = self.filter_service.filter_test_ids(pics_dicts, spec_id)
            
            # 步骤3: 映射测试ID
            target_spec = spec_id[:-1] + "1"  # 365212 -> 365211
            mapping_result = self.mapping_service.map_test_ids(
                filter_result.matched_test_ids, 
                spec_id, 
                target_spec
            )
            
            # 返回结果
            return {
                'pics_count': pics_result.true_items,
                'band_info': pics_result.band_info,
                'filtered_test_ids': filter_result.matched_test_ids,
                'mapped_test_ids': [m.mapped_id for m in mapping_result.mapped_ids],
                'match_rate': filter_result.matched_count / filter_result.total_evaluated * 100,
                'mapping_success_rate': mapping_result.successfully_mapped / mapping_result.total_input * 100
            }
        
        def cleanup(self):
            """清理资源"""
            self.filter_service.disconnect()
            self.mapping_service.disconnect()
    
    # 使用API
    api = TestPlanAPI(db_path="database/testplan.duckdb")
    
    try:
        # 处理任何Excel文件和spec_id
        result = api.process(
            excel_path="any_customer_file.xlsx",
            spec_id="365212"  # 或任何其他spec_id
        )
        print(f"API结果: {result}")
    finally:
        api.cleanup()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python example_usage.py <excel_file> [spec_id] [db_path]")
        print("\n示例:")
        print("  python example_usage.py customer.xlsx")
        print("  python example_usage.py customer.xlsx 365212")
        print("  python example_usage.py customer.xlsx 385212 /path/to/db")
        sys.exit(1)
    
    # 从命令行参数获取输入
    excel_file = sys.argv[1]
    spec_id = sys.argv[2] if len(sys.argv) > 2 else "365212"
    db_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    # 处理测试计划
    result = process_test_plan(excel_file, spec_id, db_path)
    
    # 输出结果
    import json
    print("\n最终结果 (JSON):")
    print(json.dumps(result, indent=2, default=str))