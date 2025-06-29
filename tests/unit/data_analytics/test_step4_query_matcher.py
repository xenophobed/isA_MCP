#!/usr/bin/env python3
"""
Step 4 Test: 查询匹配测试
使用Step 2的语义增强结果和Step 3的向量存储进行查询匹配
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 直接导入
sys.path.insert(0, str(project_root / "tools" / "services" / "data_analytics_service" / "services"))

from query_matcher import QueryMatcher, QueryContext, MetadataMatch, QueryPlan
from embedding_storage import EmbeddingStorage
from semantic_enricher import SemanticMetadata

# 测试查询列表
TEST_QUERIES = [
    "Show me all companies with their codes",
    "Find customs declarations from last month", 
    "Get products that have been shipped recently",
    "How many companies are registered?",
    "List all shipping containers and their contents",
    "Show trade volume by country",
    "Find all transactions above 100000",
    "Get customer details for company_code ABC123",
    "Show recent import declarations",
    "List all products with their categories"
]

def load_step2_result():
    """加载Step 2的语义增强结果"""
    result_file = "semantic_enricher_test_result_20250629_021702.json"
    
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ 成功加载Step 2结果: {result_file}")
        return data
    except FileNotFoundError:
        print(f"❌ 未找到Step 2结果文件: {result_file}")
        return None
    except Exception as e:
        print(f"❌ 加载Step 2结果失败: {e}")
        return None

async def test_query_matcher_initialization():
    """测试查询匹配器初始化"""
    print("🔧 测试查询匹配器初始化...")
    
    try:
        # 初始化向量存储
        embedding_storage = EmbeddingStorage("customs_trade_db")
        await embedding_storage.initialize()
        
        # 初始化查询匹配器
        query_matcher = QueryMatcher(embedding_storage)
        
        print("✅ 查询匹配器初始化成功")
        return query_matcher
        
    except Exception as e:
        print(f"❌ 查询匹配器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_query_context_extraction(query_matcher, test_queries):
    """测试查询上下文提取"""
    print("\n🧠 测试查询上下文提取...")
    
    if not query_matcher:
        print("❌ 查询匹配器实例无效")
        return False
    
    extraction_results = []
    
    for i, query in enumerate(test_queries[:5]):  # 测试前5个查询
        try:
            print(f"\n📝 查询 {i+1}: {query}")
            
            query_context = await query_matcher._extract_query_context(query)
            
            print(f"   实体: {query_context.entities_mentioned}")
            print(f"   属性: {query_context.attributes_mentioned}")
            print(f"   操作: {query_context.operations}")
            print(f"   过滤器: {len(query_context.filters)}")
            print(f"   聚合: {query_context.aggregations}")
            print(f"   业务意图: {query_context.business_intent}")
            print(f"   置信度: {query_context.confidence_score:.2f}")
            
            extraction_results.append({
                'query': query,
                'context': {
                    'entities': query_context.entities_mentioned,
                    'attributes': query_context.attributes_mentioned,
                    'operations': query_context.operations,
                    'filters': len(query_context.filters),
                    'aggregations': query_context.aggregations,
                    'business_intent': query_context.business_intent,
                    'confidence_score': query_context.confidence_score
                }
            })
            
        except Exception as e:
            print(f"   ❌ 提取失败: {e}")
            return False
    
    print(f"\n📊 上下文提取完成，处理了 {len(extraction_results)} 个查询")
    return len(extraction_results) > 0

async def test_metadata_matching(query_matcher, semantic_data):
    """测试元数据匹配"""
    print("\n🔍 测试元数据匹配...")
    
    if not query_matcher or not semantic_data:
        print("❌ 查询匹配器或语义数据无效")
        return False
    
    try:
        # 构造SemanticMetadata对象
        semantic_metadata = SemanticMetadata(
            original_metadata=semantic_data.get('original_metadata', {}),
            business_entities=semantic_data.get('business_entities', []),
            semantic_tags=semantic_data.get('semantic_tags', {}),
            data_patterns=semantic_data.get('data_patterns', []),
            business_rules=semantic_data.get('business_rules', []),
            domain_classification=semantic_data.get('domain_classification', {}),
            confidence_scores=semantic_data.get('confidence_scores', {})
        )
        
        # 测试查询
        test_query = "Show me all companies with their codes"
        
        print(f"🔍 测试查询: {test_query}")
        
        # 执行匹配
        query_context, metadata_matches = await query_matcher.match_query_to_metadata(
            test_query, semantic_metadata
        )
        
        print(f"📊 匹配结果:")
        print(f"   查询上下文置信度: {query_context.confidence_score:.2f}")
        print(f"   找到匹配项: {len(metadata_matches)}")
        
        for i, match in enumerate(metadata_matches[:3]):  # 显示前3个匹配
            print(f"   {i+1}. {match.entity_name} ({match.entity_type}) - {match.match_type}")
            print(f"      相似度: {match.similarity_score:.3f}")
            print(f"      相关属性: {match.relevant_attributes}")
        
        return len(metadata_matches) > 0
        
    except Exception as e:
        print(f"❌ 元数据匹配测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_query_plan_generation(query_matcher, semantic_data):
    """测试查询计划生成"""
    print("\n📋 测试查询计划生成...")
    
    if not query_matcher or not semantic_data:
        print("❌ 查询匹配器或语义数据无效")
        return False
    
    try:
        # 构造SemanticMetadata对象
        semantic_metadata = SemanticMetadata(
            original_metadata=semantic_data.get('original_metadata', {}),
            business_entities=semantic_data.get('business_entities', []),
            semantic_tags=semantic_data.get('semantic_tags', {}),
            data_patterns=semantic_data.get('data_patterns', []),
            business_rules=semantic_data.get('business_rules', []),
            domain_classification=semantic_data.get('domain_classification', {}),
            confidence_scores=semantic_data.get('confidence_scores', {})
        )
        
        # 测试查询
        test_query = "How many companies are registered?"
        
        print(f"📋 测试查询: {test_query}")
        
        # 先获取匹配
        query_context, metadata_matches = await query_matcher.match_query_to_metadata(
            test_query, semantic_metadata
        )
        
        # 生成查询计划
        query_plan = await query_matcher.generate_query_plan(
            query_context, metadata_matches, semantic_metadata
        )
        
        print(f"📊 查询计划:")
        print(f"   主要表: {query_plan.primary_tables}")
        print(f"   所需连接: {len(query_plan.required_joins)}")
        print(f"   选择列: {query_plan.select_columns}")
        print(f"   WHERE条件: {query_plan.where_conditions}")
        print(f"   聚合函数: {query_plan.aggregations}")
        print(f"   排序: {query_plan.order_by}")
        print(f"   计划置信度: {query_plan.confidence_score:.2f}")
        print(f"   替代方案: {len(query_plan.alternative_plans)}")
        
        return query_plan.confidence_score > 0.0
        
    except Exception as e:
        print(f"❌ 查询计划生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_related_entities_search(query_matcher):
    """测试相关实体搜索"""
    print("\n🔗 测试相关实体搜索...")
    
    if not query_matcher:
        print("❌ 查询匹配器实例无效")
        return False
    
    try:
        # 测试实体
        test_entity = "companies"
        
        print(f"🔍 搜索与 '{test_entity}' 相关的实体...")
        
        related_entities = await query_matcher.find_related_entities(
            test_entity, relationship_type='related'
        )
        
        print(f"📊 搜索结果:")
        print(f"   找到相关实体: {len(related_entities)}")
        
        for i, entity in enumerate(related_entities[:3]):  # 显示前3个
            print(f"   {i+1}. {entity.entity_name} ({entity.entity_type})")
            print(f"      相似度: {entity.similarity_score:.3f}")
            print(f"      内容: {entity.content[:60]}...")
        
        return len(related_entities) > 0
        
    except Exception as e:
        print(f"❌ 相关实体搜索测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_query_improvements(query_matcher):
    """测试查询改进建议"""
    print("\n💡 测试查询改进建议...")
    
    if not query_matcher:
        print("❌ 查询匹配器实例无效")
        return False
    
    try:
        # 模拟一个低置信度的查询计划
        from query_matcher import QueryPlan
        
        mock_query_plan = QueryPlan(
            primary_tables=['companies'],
            required_joins=[],
            select_columns=['companies.id'],
            where_conditions=[],
            aggregations=[],
            order_by=[],
            confidence_score=0.5,  # 低置信度
            alternative_plans=[]
        )
        
        test_query = "show companies"
        
        print(f"💡 生成改进建议: {test_query}")
        
        suggestions = await query_matcher.suggest_query_improvements(
            test_query, mock_query_plan
        )
        
        print(f"📊 改进建议:")
        for i, suggestion in enumerate(suggestions):
            print(f"   {i+1}. {suggestion}")
        
        return len(suggestions) > 0
        
    except Exception as e:
        print(f"❌ 查询改进建议测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_comprehensive_query_workflow(query_matcher, semantic_data):
    """测试完整查询工作流"""
    print("\n🔄 测试完整查询工作流...")
    
    if not query_matcher or not semantic_data:
        print("❌ 查询匹配器或语义数据无效")
        return False
    
    try:
        # 构造SemanticMetadata对象
        semantic_metadata = SemanticMetadata(
            original_metadata=semantic_data.get('original_metadata', {}),
            business_entities=semantic_data.get('business_entities', []),
            semantic_tags=semantic_data.get('semantic_tags', {}),
            data_patterns=semantic_data.get('data_patterns', []),
            business_rules=semantic_data.get('business_rules', []),
            domain_classification=semantic_data.get('domain_classification', {}),
            confidence_scores=semantic_data.get('confidence_scores', {})
        )
        
        # 复杂查询测试
        complex_query = "Find all customs declarations from companies in China with value greater than 50000 in the last 6 months"
        
        print(f"🔄 复杂查询: {complex_query}")
        
        # 步骤1: 提取查询上下文
        query_context = await query_matcher._extract_query_context(complex_query)
        print(f"   ✅ 查询上下文提取完成 (置信度: {query_context.confidence_score:.2f})")
        
        # 步骤2: 匹配元数据
        query_context, metadata_matches = await query_matcher.match_query_to_metadata(
            complex_query, semantic_metadata
        )
        print(f"   ✅ 元数据匹配完成 (找到 {len(metadata_matches)} 个匹配)")
        
        # 步骤3: 生成查询计划
        query_plan = await query_matcher.generate_query_plan(
            query_context, metadata_matches, semantic_metadata
        )
        print(f"   ✅ 查询计划生成完成 (置信度: {query_plan.confidence_score:.2f})")
        
        # 步骤4: 生成改进建议
        suggestions = await query_matcher.suggest_query_improvements(
            complex_query, query_plan
        )
        print(f"   ✅ 改进建议生成完成 ({len(suggestions)} 个建议)")
        
        # 步骤5: 搜索相关实体
        if metadata_matches:
            primary_entity = metadata_matches[0].entity_name
            related_entities = await query_matcher.find_related_entities(primary_entity)
            print(f"   ✅ 相关实体搜索完成 (找到 {len(related_entities)} 个相关实体)")
        
        print(f"🎯 完整工作流总结:")
        print(f"   - 主要表: {query_plan.primary_tables}")
        print(f"   - 选择列: {query_plan.select_columns[:3]}")  # 前3个
        print(f"   - 过滤器: {len(query_context.filters)}")
        print(f"   - 聚合: {query_plan.aggregations}")
        print(f"   - 总体置信度: {query_plan.confidence_score:.2f}")
        
        return query_plan.confidence_score > 0.3
        
    except Exception as e:
        print(f"❌ 完整查询工作流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🚀 开始Step 4查询匹配测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 加载Step 2结果
    semantic_data = load_step2_result()
    if not semantic_data:
        print("❌ 无法加载Step 2结果，测试终止")
        return False
    
    print(f"📊 Step 2数据概况:")
    print(f"   - 业务实体: {len(semantic_data.get('business_entities', []))}")
    print(f"   - 语义标签: {len(semantic_data.get('semantic_tags', {}))}")
    print(f"   - 数据模式: {len(semantic_data.get('data_patterns', []))}")
    print(f"   - 业务规则: {len(semantic_data.get('business_rules', []))}")
    print()
    
    passed_tests = 0
    failed_tests = 0
    query_matcher = None
    
    # 测试初始化
    print(f"{'='*15} 查询匹配器初始化 {'='*15}")
    try:
        query_matcher = await test_query_matcher_initialization()
        if query_matcher:
            passed_tests += 1
            print("✅ 查询匹配器初始化 测试通过")
        else:
            failed_tests += 1
            print("❌ 查询匹配器初始化 测试失败")
            return False
    except Exception as e:
        failed_tests += 1
        print(f"❌ 查询匹配器初始化 测试异常: {e}")
        return False
    
    # 运行后续测试
    if query_matcher:
        tests = [
            ("查询上下文提取", lambda: test_query_context_extraction(query_matcher, TEST_QUERIES)),
            ("元数据匹配", lambda: test_metadata_matching(query_matcher, semantic_data)),
            ("查询计划生成", lambda: test_query_plan_generation(query_matcher, semantic_data)),
            ("相关实体搜索", lambda: test_related_entities_search(query_matcher)),
            ("查询改进建议", lambda: test_query_improvements(query_matcher)),
            ("完整查询工作流", lambda: test_comprehensive_query_workflow(query_matcher, semantic_data)),
        ]
        
        for test_name, test_func in tests:
            try:
                print(f"\n{'='*15} {test_name} {'='*15}")
                result = await test_func()
                if result:
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
    if passed_tests + failed_tests > 0:
        print(f"📈 成功率: {passed_tests/(passed_tests+failed_tests)*100:.1f}%")
    
    # 保存测试结果
    test_result = {
        'test_time': datetime.now().isoformat(),
        'total_tests': passed_tests + failed_tests,
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'success_rate': passed_tests/(passed_tests+failed_tests)*100 if (passed_tests + failed_tests) > 0 else 0,
        'test_queries': TEST_QUERIES,
        'database_source': 'customs_trade_db'
    }
    
    result_file = f"step4_query_matcher_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(test_result, f, indent=2, ensure_ascii=False)
    
    print(f"📄 测试结果已保存到: {result_file}")
    
    if failed_tests == 0:
        print("\n🎉 Step 4查询匹配所有测试通过!")
        return True
    else:
        print(f"\n⚠️ 有 {failed_tests} 个测试失败，需要检查")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)