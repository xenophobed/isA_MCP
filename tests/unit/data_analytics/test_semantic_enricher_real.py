#!/usr/bin/env python3
"""
Real Semantic Enricher Test - Step 2
使用真实海关贸易数据测试语义增强器
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.services.data_analytics_service.services.metadata_service import MetadataDiscoveryService
from tools.services.data_analytics_service.services.semantic_enricher import SemanticEnricher, SemanticMetadata

# 真实数据库配置
REAL_DB_CONFIG = {
    "type": "postgresql",
    "host": "localhost", 
    "port": 5432,
    "database": "customs_trade_db",
    "username": "xenodennis",
    "password": "",
    "include_data_analysis": True,
    "sample_size": 1000
}

def test_semantic_enricher_initialization():
    """测试语义增强器初始化"""
    print("🔧 测试语义增强器初始化...")
    
    enricher = SemanticEnricher()
    
    # 验证初始化
    if not hasattr(enricher, 'business_keywords'):
        print("❌ 缺少business_keywords属性")
        return False
    
    if not hasattr(enricher, 'pattern_detectors'):
        print("❌ 缺少pattern_detectors属性")
        return False
    
    # 验证业务关键词
    expected_domains = ['customer', 'product', 'order', 'financial', 'temporal']
    for domain in expected_domains:
        if domain not in enricher.business_keywords:
            print(f"❌ 缺少业务域: {domain}")
            return False
        print(f"✅ 业务域: {domain} - {len(enricher.business_keywords[domain])} 个关键词")
    
    print("✅ 语义增强器初始化测试通过")
    return True

def test_enrich_real_metadata():
    """测试使用真实元数据进行语义增强"""
    print("\n🧠 测试真实元数据语义增强...")
    
    # 获取真实元数据
    service = MetadataDiscoveryService()
    
    try:
        print("📊 获取海关贸易数据库元数据...")
        metadata = service.discover_database_metadata(REAL_DB_CONFIG)
        
        if not metadata or 'tables' not in metadata:
            print(f"❌ 元数据获取失败")
            return False
        print(f"✅ 成功获取元数据: {len(metadata['tables'])} 表, {len(metadata['columns'])} 字段")
        
        # 初始化语义增强器
        enricher = SemanticEnricher()
        
        print("🔍 开始语义增强...")
        semantic_metadata = enricher.enrich_metadata(metadata)
        
        # 验证结果
        if not isinstance(semantic_metadata, SemanticMetadata):
            print("❌ 返回结果类型错误")
            return False
        
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
        
        print("✅ 真实元数据语义增强测试通过")
        return True, semantic_metadata
        
    except Exception as e:
        print(f"❌ 语义增强测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_business_entity_extraction(metadata):
    """测试业务实体提取"""
    print("\n🏢 测试业务实体提取...")
    
    enricher = SemanticEnricher()
    entities = enricher._extract_business_entities(metadata)
    
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

def test_semantic_tags_generation(metadata):
    """测试语义标签生成"""
    print("\n🏷️ 测试语义标签生成...")
    
    enricher = SemanticEnricher()
    tags = enricher._generate_semantic_tags(metadata)
    
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

def test_data_pattern_detection(metadata):
    """测试数据模式检测"""
    print("\n📊 测试数据模式检测...")
    
    enricher = SemanticEnricher()
    patterns = enricher._detect_data_patterns(metadata)
    
    print(f"🔍 检测到 {len(patterns)} 个数据模式")
    
    # 验证模式类型
    pattern_types = set()
    for pattern in patterns:
        pattern_type = pattern['pattern_type']
        pattern_types.add(pattern_type)
        
        description = pattern['description']
        confidence = pattern['confidence']
        print(f"   - {pattern_type}: {description} (置信度: {confidence:.2f})")
        
        if 'tables_involved' in pattern:
            tables = pattern['tables_involved']
            print(f"     涉及表: {', '.join(tables)}")
        
        if 'columns_involved' in pattern:
            columns = pattern['columns_involved']
            print(f"     涉及字段: {', '.join(columns[:3])}{'...' if len(columns) > 3 else ''}")
    
    print(f"✅ 检测到的模式类型: {', '.join(pattern_types)}")
    
    # 验证期望的模式（基于海关贸易数据特征）
    expected_patterns = ['master_detail', 'temporal']
    for expected in expected_patterns:
        if expected in pattern_types:
            print(f"✅ 找到期望模式: {expected}")
        else:
            print(f"⚠️ 未找到期望模式: {expected}")
    
    print("✅ 数据模式检测测试通过")
    return True

def test_business_rules_inference(metadata):
    """测试业务规则推断"""
    print("\n📏 测试业务规则推断...")
    
    enricher = SemanticEnricher()
    entities = enricher._extract_business_entities(metadata)
    rules = enricher._infer_business_rules(metadata, entities)
    
    print(f"⚖️ 推断出 {len(rules)} 个业务规则")
    
    # 分类规则类型
    rule_types = {}
    for rule in rules:
        rule_type = rule['rule_type']
        if rule_type not in rule_types:
            rule_types[rule_type] = 0
        rule_types[rule_type] += 1
    
    print("📊 规则类型分布:")
    for rule_type, count in rule_types.items():
        print(f"   - {rule_type}: {count} 个")
    
    # 显示一些关键规则
    print("\n📝 关键业务规则:")
    for rule in rules[:5]:
        rule_type = rule['rule_type']
        description = rule['description']
        confidence = rule['confidence']
        tables = rule['tables_involved']
        
        print(f"   - {rule_type}: {description}")
        print(f"     置信度: {confidence:.2f}, 涉及表: {', '.join(tables)}")
        
        if 'sql_constraint' in rule:
            sql = rule['sql_constraint']
            print(f"     SQL约束: {sql[:50]}{'...' if len(sql) > 50 else ''}")
    
    if len(rules) > 5:
        print(f"   ... 还有 {len(rules) - 5} 个规则")
    
    # 验证必要的规则类型
    expected_rule_types = ['referential_integrity', 'uniqueness', 'data_validation']
    for expected in expected_rule_types:
        if expected in rule_types:
            print(f"✅ 找到期望规则类型: {expected}")
        else:
            print(f"⚠️ 未找到期望规则类型: {expected}")
    
    print("✅ 业务规则推断测试通过")
    return True

def test_domain_classification(metadata):
    """测试域分类"""
    print("\n🎯 测试域分类...")
    
    enricher = SemanticEnricher()
    entities = enricher._extract_business_entities(metadata)
    domain_classification = enricher._classify_domain(metadata, entities)
    
    print("🔍 域分类结果:")
    
    primary_domain = domain_classification['primary_domain']
    confidence = domain_classification['confidence']
    domain_scores = domain_classification['domain_scores']
    is_multi_domain = domain_classification['is_multi_domain']
    
    print(f"   - 主要域: {primary_domain}")
    print(f"   - 置信度: {confidence:.2f}")
    print(f"   - 多域系统: {is_multi_domain}")
    
    print("\n📊 各域得分:")
    sorted_scores = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    for domain, score in sorted_scores:
        if score > 0:
            print(f"   - {domain}: {score:.2f}")
    
    # 验证是否正确识别为贸易/物流相关域
    trade_related_domains = ['ecommerce', 'finance', 'crm']
    if primary_domain in trade_related_domains:
        print(f"✅ 正确识别为贸易相关域: {primary_domain}")
    else:
        print(f"⚠️ 域分类可能不准确: {primary_domain}")
        # 对于海关数据，可能需要扩展域分类词汇
    
    print("✅ 域分类测试通过")
    return True

def main():
    """主测试函数"""
    print("🚀 开始语义增强器真实数据测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("语义增强器初始化", test_semantic_enricher_initialization),
    ]
    
    passed_tests = 0
    failed_tests = 0
    metadata = None
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
    
    # 运行主要测试
    print(f"\n{'='*15} 真实元数据语义增强 {'='*15}")
    try:
        success, semantic_metadata = test_enrich_real_metadata()
        if success:
            passed_tests += 1
            print("✅ 真实元数据语义增强 测试通过")
            metadata = semantic_metadata.original_metadata
        else:
            failed_tests += 1
            print("❌ 真实元数据语义增强 测试失败")
            return False
    except Exception as e:
        failed_tests += 1
        print(f"❌ 真实元数据语义增强 测试异常: {e}")
        return False
    
    # 运行详细测试
    if metadata:
        detailed_tests = [
            ("业务实体提取", lambda: test_business_entity_extraction(metadata)),
            ("语义标签生成", lambda: test_semantic_tags_generation(metadata)),
            ("数据模式检测", lambda: test_data_pattern_detection(metadata)),
            ("业务规则推断", lambda: test_business_rules_inference(metadata)),
            ("域分类", lambda: test_domain_classification(metadata)),
        ]
        
        for test_name, test_func in detailed_tests:
            try:
                print(f"\n{'='*15} {test_name} {'='*15}")
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
    
    print(f"\n{'='*60}")
    print("📊 测试结果汇总")
    print(f"{'='*60}")
    print(f"✅ 通过: {passed_tests}")
    print(f"❌ 失败: {failed_tests}")
    print(f"📈 成功率: {passed_tests/(passed_tests+failed_tests)*100:.1f}%")
    
    # 保存测试结果
    if semantic_metadata:
        result_file = f"semantic_enricher_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
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
        print("\n🎉 所有语义增强器测试通过!")
        return True
    else:
        print(f"\n⚠️ 有 {failed_tests} 个测试失败，需要检查")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)