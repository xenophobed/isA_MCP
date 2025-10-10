#!/usr/bin/env python3
"""
测试TestID Mapping Service的功能
"""

from pathlib import Path
import sys

# 添加服务路径
sys.path.append(str(Path(__file__).parent))

from testid_mapping_service import TestIDMappingService, MappingResult
from testid_filter_service import TestIDFilterService
from pics_extraction_service import PICSExtractionService


def test_mapping_examples():
    """测试特定的映射示例"""
    print("="*60)
    print("测试1: 特定映射示例")
    print("="*60)
    
    # 创建映射服务
    service = TestIDMappingService()
    
    # 测试特定的ID
    test_ids = [
        '6.2.2A.1_3',    # A.x_3格式
        '6.2.2_1',       # 基本_1格式
        '6.2.2_s',       # _s后缀
        '6.3.4A.0_2',    # A.0_2格式
        '6.3.5.1.1',     # 多层级
        '6.5.2.1A.0_1',  # 复杂格式
        '7.1.1_H',       # _H后缀（高功率）
        '7.1.2_L',       # _L后缀（低功率）
        '7.1.3',         # 无后缀
    ]
    
    try:
        # 执行映射
        result = service.map_test_ids(test_ids)
        
        # 显示结果
        print(f"\n输入测试ID数量: {result.total_input}")
        print(f"成功映射数量: {result.successfully_mapped}")
        print(f"\n映射详情:")
        print("-"*50)
        
        for mapped in result.mapped_ids:
            status = "✓" if mapped.confidence >= 0.8 else "?"
            print(f"{status} {mapped.original_id:20} -> {mapped.mapped_id:20} [{mapped.mapping_source}, conf={mapped.confidence:.1f}]")
        
        print(f"\n映射统计:")
        for source, count in result.mapping_stats.items():
            if count > 0:
                print(f"  {source}: {count}")
        
        if result.warnings:
            print(f"\n警告:")
            for warning in result.warnings:
                print(f"  ⚠️ {warning}")
        
        return result
        
    finally:
        service.disconnect()


def test_full_pipeline():
    """测试完整的流程：PICS提取 -> 过滤 -> 映射"""
    print("\n" + "="*60)
    print("测试2: 完整流程测试")
    print("="*60)
    
    # 查找Excel文件
    base_path = Path(__file__).parent.parent.parent
    excel_files = list(base_path.glob("*.xlsx"))
    
    if not excel_files:
        print("未找到Excel文件，跳过完整流程测试")
        return None
    
    excel_file = excel_files[0]
    print(f"使用Excel文件: {excel_file.name}")
    
    try:
        # 1. PICS提取
        print("\n步骤1: PICS提取")
        pics_service = PICSExtractionService()
        pics_result = pics_service.extract_from_excel(str(excel_file))
        print(f"  ✓ 提取 {pics_result.true_items} 个TRUE项目")
        
        # 2. TestID过滤
        print("\n步骤2: TestID过滤")
        filter_service = TestIDFilterService()
        pics_dicts = [item.to_dict() for item in pics_result.pics_items]
        filter_result = filter_service.filter_test_ids(pics_dicts, spec_id="365212")
        print(f"  ✓ 过滤出 {filter_result.matched_count} 个匹配的测试ID")
        
        # 3. TestID映射
        print("\n步骤3: TestID映射")
        mapping_service = TestIDMappingService()
        mapping_result = mapping_service.map_test_ids(filter_result.matched_test_ids)
        
        print(f"  ✓ 映射 {mapping_result.successfully_mapped}/{mapping_result.total_input} 个测试ID")
        print(f"  独特映射: {mapping_result.metadata.get('unique_mappings', 0)}")
        
        # 显示样本
        print(f"\n映射样本（前5个）:")
        for mapped in mapping_result.mapped_ids[:5]:
            print(f"  {mapped.original_id} -> {mapped.mapped_id}")
        
        # 统计
        print(f"\n映射源分布:")
        for source, count in mapping_result.mapping_stats.items():
            if count > 0:
                percentage = count / mapping_result.total_input * 100
                print(f"  {source}: {count} ({percentage:.1f}%)")
        
        return mapping_result
        
    finally:
        if 'filter_service' in locals():
            filter_service.disconnect()
        if 'mapping_service' in locals():
            mapping_service.disconnect()


def test_mapping_rules():
    """测试映射规则的准确性"""
    print("\n" + "="*60)
    print("测试3: 映射规则验证")
    print("="*60)
    
    service = TestIDMappingService()
    
    # 定义测试用例和期望结果
    test_cases = [
        # (输入, 期望输出, 说明)
        ('6.2.2_s', '6.2.2', '_s后缀应该被移除'),
        ('6.2.2_1', '6.2.2_1', '_1后缀应该保留'),
        ('6.2.2_3', '6.2.2', '_3后缀应该被移除'),
        ('6.2.2A.1_3', '6.2.2A.1', 'A.x_3格式应该移除_3'),
        ('6.3.4A.0_2', '6.3.4A', 'A.0格式应该简化为A'),
        ('6.3.5.1.1', '6.3.5.1', '多层级应该简化'),
        ('7.1.1_H', '7.1.1', '_H后缀应该被移除'),
        ('7.1.1_L', '7.1.1', '_L后缀应该被移除'),
    ]
    
    try:
        print("\n规则验证:")
        print("-"*50)
        
        passed = 0
        failed = 0
        
        for input_id, expected, description in test_cases:
            result = service.map_test_ids([input_id])
            if result.mapped_ids:
                actual = result.mapped_ids[0].mapped_id
                if actual == expected:
                    print(f"✓ {input_id} -> {actual} ({description})")
                    passed += 1
                else:
                    print(f"✗ {input_id} -> {actual} (期望: {expected}) - {description}")
                    failed += 1
            else:
                print(f"✗ {input_id} 无法映射 - {description}")
                failed += 1
        
        print(f"\n测试结果: {passed} 通过, {failed} 失败")
        
        # 测试去重功能
        print("\n去重测试:")
        duplicate_ids = ['6.2.2_s', '6.2.2_3', '6.2.2_H']  # 都应该映射到6.2.2
        result = service.map_test_ids(duplicate_ids)
        
        unique_targets = set(m.mapped_id for m in result.mapped_ids)
        print(f"  输入: {duplicate_ids}")
        print(f"  输出: {list(unique_targets)}")
        print(f"  去重效果: {len(duplicate_ids)} -> {len(unique_targets)}")
        
    finally:
        service.disconnect()


def main():
    """运行所有测试"""
    print("TestID Mapping Service 测试套件")
    print("="*60)
    
    # 测试1: 特定示例
    result1 = test_mapping_examples()
    
    # 测试2: 完整流程
    result2 = test_full_pipeline()
    
    # 测试3: 规则验证
    test_mapping_rules()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    if result1:
        print(f"✓ 映射示例测试完成: {result1.successfully_mapped}/{result1.total_input} 成功")
    
    if result2:
        print(f"✓ 完整流程测试完成: {result2.successfully_mapped}/{result2.total_input} 成功")
    
    print("\n服务边界清晰:")
    print("  1. PICSExtractionService: 提取PICS TRUE项目")
    print("  2. TestIDFilterService: 根据条件过滤测试ID")
    print("  3. TestIDMappingService: 映射测试ID格式")
    print("\n下一步:")
    print("  4. ParameterExpansionService: 展开测试参数")
    print("  5. ValidationService: PTCRB/GCF合规性验证")
    print("  6. ExcelGenerationService: 生成标准Excel输出")


if __name__ == "__main__":
    main()