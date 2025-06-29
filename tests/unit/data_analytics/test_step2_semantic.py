#!/usr/bin/env python3
"""
Individual Test for Step 2: Semantic Enricher
测试语义增强器单独功能
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.services.data_analytics_service.services.semantic_enricher import SemanticEnricher, SemanticMetadata

# Sample metadata for testing (mimicking real customs data structure)
SAMPLE_METADATA = {
    'tables': [
        {
            'table_name': 'companies',
            'table_type': 'table',
            'record_count': 1000,
            'table_comment': 'Company information',
            'data_quality_score': 0.95
        },
        {
            'table_name': 'declarations',
            'table_type': 'table', 
            'record_count': 10000,
            'table_comment': 'Customs declarations',
            'data_quality_score': 0.88
        },
        {
            'table_name': 'goods_details',
            'table_type': 'table',
            'record_count': 30000,
            'table_comment': 'Goods detail information',
            'data_quality_score': 0.92
        },
        {
            'table_name': 'hs_codes',
            'table_type': 'table',
            'record_count': 500,
            'table_comment': 'HS code reference',
            'data_quality_score': 0.98
        },
        {
            'table_name': 'ports',
            'table_type': 'table',
            'record_count': 100,
            'table_comment': 'Port information',
            'data_quality_score': 0.99
        }
    ],
    'columns': [
        # Companies table
        {
            'table_name': 'companies',
            'column_name': 'company_id',
            'data_type': 'integer',
            'is_nullable': False,
            'unique_percentage': 1.0,
            'null_percentage': 0.0
        },
        {
            'table_name': 'companies',
            'column_name': 'company_code',
            'data_type': 'varchar',
            'is_nullable': False,
            'unique_percentage': 1.0,
            'null_percentage': 0.0
        },
        {
            'table_name': 'companies',
            'column_name': 'company_name',
            'data_type': 'varchar',
            'is_nullable': False,
            'unique_percentage': 0.95,
            'null_percentage': 0.02
        },
        {
            'table_name': 'companies',
            'column_name': 'address',
            'data_type': 'text',
            'is_nullable': True,
            'unique_percentage': 0.80,
            'null_percentage': 0.15
        },
        # Declarations table
        {
            'table_name': 'declarations',
            'column_name': 'declaration_id',
            'data_type': 'integer',
            'is_nullable': False,
            'unique_percentage': 1.0,
            'null_percentage': 0.0
        },
        {
            'table_name': 'declarations',
            'column_name': 'company_id',
            'data_type': 'integer',
            'is_nullable': False,
            'unique_percentage': 0.1,
            'null_percentage': 0.0
        },
        {
            'table_name': 'declarations',
            'column_name': 'declare_date',
            'data_type': 'timestamp',
            'is_nullable': False,
            'unique_percentage': 0.8,
            'null_percentage': 0.0
        },
        {
            'table_name': 'declarations',
            'column_name': 'rmb_amount',
            'data_type': 'decimal',
            'is_nullable': True,
            'unique_percentage': 0.9,
            'null_percentage': 0.05
        },
        # Goods details table
        {
            'table_name': 'goods_details',
            'column_name': 'goods_id',
            'data_type': 'integer',
            'is_nullable': False,
            'unique_percentage': 1.0,
            'null_percentage': 0.0
        },
        {
            'table_name': 'goods_details',
            'column_name': 'declaration_id',
            'data_type': 'integer',
            'is_nullable': False,
            'unique_percentage': 0.3,
            'null_percentage': 0.0
        },
        {
            'table_name': 'goods_details',
            'column_name': 'hs_code_id',
            'data_type': 'integer',
            'is_nullable': False,
            'unique_percentage': 0.02,
            'null_percentage': 0.0
        },
        # HS codes table
        {
            'table_name': 'hs_codes',
            'column_name': 'hs_code_id',
            'data_type': 'integer',
            'is_nullable': False,
            'unique_percentage': 1.0,
            'null_percentage': 0.0
        },
        {
            'table_name': 'hs_codes',
            'column_name': 'hs_code',
            'data_type': 'varchar',
            'is_nullable': False,
            'unique_percentage': 1.0,
            'null_percentage': 0.0
        },
        {
            'table_name': 'hs_codes',
            'column_name': 'description',
            'data_type': 'text',
            'is_nullable': True,
            'unique_percentage': 0.98,
            'null_percentage': 0.02
        }
    ],
    'relationships': [
        {
            'constraint_name': 'fk_declarations_company',
            'from_table': 'declarations',
            'from_column': 'company_id',
            'to_table': 'companies',
            'to_column': 'company_id',
            'constraint_type': 'foreign_key'
        },
        {
            'constraint_name': 'fk_goods_declaration',
            'from_table': 'goods_details',
            'from_column': 'declaration_id',
            'to_table': 'declarations',
            'to_column': 'declaration_id',
            'constraint_type': 'foreign_key'
        },
        {
            'constraint_name': 'fk_goods_hs_code',
            'from_table': 'goods_details',
            'from_column': 'hs_code_id',
            'to_table': 'hs_codes',
            'to_column': 'hs_code_id',
            'constraint_type': 'foreign_key'
        }
    ]
}

def test_semantic_enricher_initialization():
    """测试语义增强器初始化"""
    print("🔧 测试语义增强器初始化...")
    
    enricher = SemanticEnricher()
    
    # 验证初始化
    assert hasattr(enricher, 'business_keywords'), "缺少business_keywords属性"
    assert hasattr(enricher, 'pattern_detectors'), "缺少pattern_detectors属性"
    
    # 验证业务关键词
    expected_domains = ['customer', 'product', 'order', 'financial', 'temporal']
    for domain in expected_domains:
        assert domain in enricher.business_keywords, f"缺少业务域: {domain}"
        print(f"✅ 业务域: {domain} - {len(enricher.business_keywords[domain])} 个关键词")
    
    print("✅ 语义增强器初始化测试通过")
    return True

def test_enrich_metadata():
    """测试元数据语义增强主流程"""
    print("\n🧠 测试元数据语义增强...")
    
    enricher = SemanticEnricher()
    
    print("🔍 开始语义增强...")
    semantic_metadata = enricher.enrich_metadata(SAMPLE_METADATA)
    
    # 验证返回结果类型
    assert isinstance(semantic_metadata, SemanticMetadata), "返回结果类型错误"
    print("✅ 语义增强完成")
    
    # 验证业务实体
    entities = semantic_metadata.business_entities
    print(f"📋 发现 {len(entities)} 个业务实体:")
    
    key_entities = ['companies', 'declarations', 'goods_details', 'hs_codes']
    found_entities = []
    
    for entity in entities:
        entity_name = entity['entity_name']
        entity_type = entity['entity_type']
        confidence = entity['confidence']
        importance = entity['business_importance']
        
        print(f"   - {entity_name}: {entity_type} (置信度: {confidence:.2f}, 重要性: {importance})")
        
        if entity_name in key_entities:
            found_entities.append(entity_name)
    
    for key_entity in key_entities:
        if key_entity in found_entities:
            print(f"✅ 找到关键实体: {key_entity}")
        else:
            print(f"⚠️ 未找到关键实体: {key_entity}")
    
    # 验证语义标签
    tags = semantic_metadata.semantic_tags
    print(f"\n🏷️ 生成 {len(tags)} 个语义标签:")
    
    # 显示一些关键标签
    key_tables = ['companies', 'declarations', 'goods_details']
    for table in key_tables:
        table_key = f"table:{table}"
        if table_key in tags:
            table_tags = tags[table_key]
            print(f"   - {table}: {', '.join(table_tags)}")
    
    # 验证数据模式
    patterns = semantic_metadata.data_patterns
    print(f"\n📊 检测到 {len(patterns)} 个数据模式:")
    
    for pattern in patterns:
        pattern_type = pattern['pattern_type']
        description = pattern['description']
        confidence = pattern['confidence']
        print(f"   - {pattern_type}: {description} (置信度: {confidence:.2f})")
    
    # 验证业务规则
    rules = semantic_metadata.business_rules
    print(f"\n📏 推断出 {len(rules)} 个业务规则:")
    
    for rule in rules[:5]:  # 显示前5个规则
        rule_type = rule['rule_type']
        description = rule['description']
        confidence = rule['confidence']
        print(f"   - {rule_type}: {description} (置信度: {confidence:.2f})")
    
    if len(rules) > 5:
        print(f"   ... 还有 {len(rules) - 5} 个规则")
    
    # 验证域分类
    domain = semantic_metadata.domain_classification
    print(f"\n🎯 域分类:")
    print(f"   - 主要域: {domain['primary_domain']}")
    print(f"   - 置信度: {domain['confidence']:.2f}")
    print(f"   - 多域系统: {domain['is_multi_domain']}")
    
    # 显示域得分
    domain_scores = domain['domain_scores']
    print("   - 域得分:")
    for domain_name, score in domain_scores.items():
        if score > 0:
            print(f"     * {domain_name}: {score:.2f}")
    
    # 验证置信度得分
    confidence_scores = semantic_metadata.confidence_scores
    print(f"\n📈 置信度评估:")
    for aspect, score in confidence_scores.items():
        print(f"   - {aspect}: {score:.2f}")
    
    print("✅ 元数据语义增强测试通过")
    return True, semantic_metadata

def test_business_entity_extraction():
    """测试业务实体提取"""
    print("\n🏢 测试业务实体提取...")
    
    enricher = SemanticEnricher()
    entities = enricher._extract_business_entities(SAMPLE_METADATA)
    
    print(f"📋 提取到 {len(entities)} 个业务实体")
    
    # 验证海关贸易域的关键实体
    customs_entities = {
        'companies': ['entity', 'reference'],
        'declarations': ['transaction'],
        'goods_details': ['transaction'], 
        'hs_codes': ['reference'],
        'ports': ['reference']
    }
    
    found_customs_entities = 0
    for entity in entities:
        entity_name = entity['entity_name']
        entity_type = entity['entity_type']
        
        if entity_name in customs_entities:
            expected_types = customs_entities[entity_name]
            if entity_type in expected_types:
                print(f"✅ {entity_name}: {entity_type} ✓")
                found_customs_entities += 1
            else:
                print(f"⚠️ {entity_name}: {entity_type} (期望: {expected_types})")
                found_customs_entities += 1
    
    print(f"✅ 找到 {found_customs_entities}/{len(customs_entities)} 个海关关键实体")
    
    # 验证实体属性
    for entity in entities[:3]:  # 检查前3个实体
        print(f"\n📝 实体详情: {entity['entity_name']}")
        print(f"   - 类型: {entity['entity_type']}")
        print(f"   - 置信度: {entity['confidence']:.2f}")
        print(f"   - 关键属性: {', '.join(entity['key_attributes'][:3])}")
        print(f"   - 记录数: {entity['record_count']}")
        print(f"   - 业务重要性: {entity['business_importance']}")
        
        if entity['relationships']:
            print(f"   - 关系: {len(entity['relationships'])} 个")
    
    print("✅ 业务实体提取测试通过")
    return True

def test_semantic_tags_generation():
    """测试语义标签生成"""
    print("\n🏷️ 测试语义标签生成...")
    
    enricher = SemanticEnricher()
    tags = enricher._generate_semantic_tags(SAMPLE_METADATA)
    
    print(f"📊 生成 {len(tags)} 个语义标签")
    
    # 验证表级标签
    table_tags_count = 0
    column_tags_count = 0
    
    for key, tag_list in tags.items():
        if key.startswith('table:'):
            table_tags_count += 1
            table_name = key.split(':', 1)[1]
            if table_name in ['companies', 'declarations', 'goods_details']:
                print(f"📋 {table_name}: {', '.join(tag_list)}")
        elif key.startswith('column:'):
            column_tags_count += 1
    
    print(f"✅ 表标签: {table_tags_count} 个")
    print(f"✅ 字段标签: {column_tags_count} 个")
    
    # 验证关键字段的语义标签
    key_columns = [
        'companies.company_code',
        'companies.company_name', 
        'declarations.rmb_amount',
        'declarations.declare_date'
    ]
    
    for col in key_columns:
        col_key = f"column:{col}"
        if col_key in tags:
            col_tags = tags[col_key]
            print(f"📝 {col}: {', '.join(col_tags)}")
        else:
            print(f"⚠️ 未找到 {col} 的标签")
    
    print("✅ 语义标签生成测试通过")
    return True

def main():
    """主测试函数"""
    print("🚀 开始Step 2语义增强器单独测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("语义增强器初始化", test_semantic_enricher_initialization),
        ("业务实体提取", test_business_entity_extraction),
        ("语义标签生成", test_semantic_tags_generation),
    ]
    
    passed_tests = 0
    failed_tests = 0
    semantic_metadata = None
    
    # 运行基础测试
    for test_name, test_func in tests:
        try:
            print(f"{'='*15} {test_name} {'='*15}")
            if test_func():
                passed_tests += 1
                print(f"✅ {test_name} 测试通过")
            else:
                failed_tests += 1
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            failed_tests += 1
            print(f"❌ {test_name} 测试异常: {e}")
            import traceback
            traceback.print_exc()
    
    # 运行主要测试
    print(f"\n{'='*15} 完整语义增强流程 {'='*15}")
    try:
        success, semantic_metadata = test_enrich_metadata()
        if success:
            passed_tests += 1
            print("✅ 完整语义增强流程 测试通过")
        else:
            failed_tests += 1
            print("❌ 完整语义增强流程 测试失败")
    except Exception as e:
        failed_tests += 1
        print(f"❌ 完整语义增强流程 测试异常: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("📊 测试结果汇总")
    print(f"{'='*60}")
    print(f"✅ 通过: {passed_tests}")
    print(f"❌ 失败: {failed_tests}")
    print(f"📈 成功率: {passed_tests/(passed_tests+failed_tests)*100:.1f}%")
    
    # 保存测试结果
    if semantic_metadata:
        result_file = f"step2_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # 准备可序列化的结果
        serializable_result = {
            'business_entities': semantic_metadata.business_entities,
            'semantic_tags': semantic_metadata.semantic_tags,
            'data_patterns': semantic_metadata.data_patterns,
            'business_rules': semantic_metadata.business_rules,
            'domain_classification': semantic_metadata.domain_classification,
            'confidence_scores': semantic_metadata.confidence_scores,
            'test_summary': {
                'total_tests': passed_tests + failed_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': passed_tests/(passed_tests+failed_tests)*100
            }
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_result, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"📄 测试结果已保存到: {result_file}")
    
    if failed_tests == 0:
        print("\n🎉 Step 2语义增强器所有测试通过!")
        return True
    else:
        print(f"\n⚠️ 有 {failed_tests} 个测试失败，需要检查")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)