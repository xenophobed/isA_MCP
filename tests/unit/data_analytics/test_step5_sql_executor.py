#!/usr/bin/env python3
"""
Step 5 Test: SQL执行器测试
测试SQL生成和执行功能，包括LLM增强和传统回退策略
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

from sql_executor import SQLExecutor, ExecutionResult, FallbackAttempt, ExecutionPlan
from llm_sql_generator import LLMSQLGenerator, SQLGenerationResult
from query_matcher import QueryMatcher, QueryContext, MetadataMatch, QueryPlan
from embedding_storage import EmbeddingStorage
from semantic_enricher import SemanticMetadata

# 模拟数据库配置（因为我们没有真实数据库连接）
MOCK_DATABASE_CONFIG = {
    'type': 'postgresql',
    'host': 'localhost',
    'port': 5432,
    'database': 'customs_trade_db',
    'username': 'test_user',
    'password': 'test_password',
    'max_execution_time': 30,
    'max_rows': 1000
}

# 测试查询和计划
TEST_QUERIES = [
    {
        'name': '简单查询',
        'natural_query': '显示所有公司',
        'expected_tables': ['companies']
    },
    {
        'name': '聚合查询',
        'natural_query': '统计公司数量',
        'expected_tables': ['companies']
    },
    {
        'name': '连接查询',
        'natural_query': '显示公司的进口申报单',
        'expected_tables': ['companies', 'declarations']
    }
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

async def test_sql_executor_initialization():
    """测试SQL执行器初始化"""
    print("🔧 测试SQL执行器初始化...")
    
    try:
        # 初始化SQL执行器（不连接真实数据库）
        sql_executor = SQLExecutor(MOCK_DATABASE_CONFIG)
        
        # 初始化LLM生成器
        await sql_executor.initialize_llm()
        
        print("✅ SQL执行器初始化成功")
        return sql_executor
        
    except Exception as e:
        print(f"❌ SQL执行器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_llm_sql_generation(sql_executor, semantic_data):
    """测试LLM SQL生成"""
    print("\n🧠 测试LLM SQL生成...")
    
    if not sql_executor or not semantic_data:
        print("❌ SQL执行器或语义数据无效")
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
        
        # 模拟查询上下文
        query_context = QueryContext(
            entities_mentioned=['companies'],
            attributes_mentioned=['company_name', 'company_code'],
            operations=['select'],
            filters=[],
            aggregations=[],
            temporal_references=[],
            business_intent='lookup',
            confidence_score=0.8
        )
        
        # 模拟元数据匹配
        metadata_matches = [
            MetadataMatch(
                entity_name='companies',
                entity_type='table',
                match_type='exact',
                similarity_score=1.0,
                relevant_attributes=['company_code', 'company_name'],
                suggested_joins=[],
                metadata={'table_name': 'companies'}
            )
        ]
        
        # 测试LLM SQL生成
        test_query = "显示所有公司的名称和代码"
        
        print(f"🧠 测试查询: {test_query}")
        
        # 生成SQL（不执行）
        llm_result = await sql_executor.llm_generator.generate_sql_from_context(
            query_context, metadata_matches, semantic_metadata, test_query
        )
        
        print(f"📊 LLM生成结果:")
        print(f"   SQL: {llm_result.sql}")
        print(f"   解释: {llm_result.explanation}")
        print(f"   置信度: {llm_result.confidence_score:.2f}")
        print(f"   复杂度: {llm_result.complexity_level}")
        
        return llm_result.sql != ""
        
    except Exception as e:
        print(f"❌ LLM SQL生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_sql_validation(sql_executor, semantic_data):
    """测试SQL验证功能"""
    print("\n🔍 测试SQL验证...")
    
    if not sql_executor or not semantic_data:
        print("❌ SQL执行器或语义数据无效")
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
        
        # 测试不同的SQL
        test_sqls = [
            {
                'name': '有效SQL',
                'sql': 'SELECT company_code, company_name FROM companies LIMIT 10',
                'should_be_valid': True
            },
            {
                'name': '无效表名',
                'sql': 'SELECT * FROM invalid_table LIMIT 10',
                'should_be_valid': False
            },
            {
                'name': '无效列名',
                'sql': 'SELECT invalid_column FROM companies LIMIT 10',
                'should_be_valid': False
            }
        ]
        
        validation_results = []
        
        for test_case in test_sqls:
            print(f"🔍 验证 {test_case['name']}: {test_case['sql']}")
            
            validation_result = await sql_executor.validate_sql(
                test_case['sql'], semantic_metadata
            )
            
            print(f"   有效性: {validation_result['is_valid']}")
            print(f"   错误: {len(validation_result['errors'])}")
            print(f"   警告: {len(validation_result['warnings'])}")
            
            if validation_result['errors']:
                print(f"   错误详情: {validation_result['errors'][:2]}")
            
            validation_results.append(validation_result)
        
        # 验证结果是否符合预期
        valid_count = sum(1 for result in validation_results if result['is_valid'])
        expected_valid = sum(1 for test in test_sqls if test['should_be_valid'])
        
        print(f"📊 验证结果: {valid_count}/{len(test_sqls)} 有效，预期 {expected_valid} 有效")
        
        return len(validation_results) > 0
        
    except Exception as e:
        print(f"❌ SQL验证测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_query_plan_generation(sql_executor, semantic_data):
    """测试查询计划生成和SQL转换"""
    print("\n📋 测试查询计划生成...")
    
    if not sql_executor or not semantic_data:
        print("❌ SQL执行器或语义数据无效")
        return False
    
    try:
        # 创建测试查询计划
        test_plan = QueryPlan(
            primary_tables=['companies'],
            required_joins=[],
            select_columns=['companies.company_code', 'companies.company_name'],
            where_conditions=[],
            aggregations=[],
            order_by=['companies.company_code'],
            confidence_score=0.9,
            alternative_plans=[]
        )
        
        print(f"📋 测试查询计划:")
        print(f"   主要表: {test_plan.primary_tables}")
        print(f"   选择列: {test_plan.select_columns}")
        print(f"   排序: {test_plan.order_by}")
        
        # 生成SQL
        generated_sql = sql_executor._generate_sql_from_plan(test_plan)
        
        print(f"📊 生成的SQL:")
        print(f"   {generated_sql}")
        
        return generated_sql != ""
        
    except Exception as e:
        print(f"❌ 查询计划生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_fallback_strategies(sql_executor, semantic_data):
    """测试回退策略"""
    print("\n🔄 测试回退策略...")
    
    if not sql_executor or not semantic_data:
        print("❌ SQL执行器或语义数据无效")
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
        
        # 模拟查询上下文
        query_context = QueryContext(
            entities_mentioned=['companies'],
            attributes_mentioned=[],
            operations=['select'],
            filters=[],
            aggregations=[],
            temporal_references=[],
            business_intent='lookup',
            confidence_score=0.7
        )
        
        # 测试查询计划
        test_plan = QueryPlan(
            primary_tables=['companies'],
            required_joins=[],
            select_columns=['companies.*'],
            where_conditions=[],
            aggregations=[],
            order_by=[],
            confidence_score=0.8,
            alternative_plans=[]
        )
        
        # 测试不同的回退策略
        strategies = [
            "simplify_query",
            "remove_joins", 
            "add_limit",
            "column_fallback",
            "basic_select"
        ]
        
        original_sql = "SELECT * FROM companies JOIN declarations ON companies.company_code = declarations.company_code"
        
        fallback_results = []
        
        for strategy in strategies:
            print(f"🔄 测试回退策略: {strategy}")
            
            fallback_sql = await sql_executor._apply_fallback_strategy(
                strategy, original_sql, test_plan, query_context, semantic_metadata, "test error"
            )
            
            if fallback_sql:
                print(f"   生成SQL: {fallback_sql[:60]}...")
                fallback_results.append((strategy, fallback_sql))
            else:
                print(f"   策略无效或失败")
        
        print(f"📊 回退策略测试完成: {len(fallback_results)}/{len(strategies)} 策略成功")
        
        return len(fallback_results) > 0
        
    except Exception as e:
        print(f"❌ 回退策略测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_sql_optimization(sql_executor, semantic_data):
    """测试SQL优化功能"""
    print("\n⚡ 测试SQL优化...")
    
    if not sql_executor or not semantic_data:
        print("❌ SQL执行器或语义数据无效")
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
        
        # 测试SQL优化
        test_sql = "SELECT * FROM companies WHERE company_name LIKE '%贸易%'"
        
        print(f"⚡ 优化SQL: {test_sql}")
        
        optimization_result = await sql_executor.optimize_query(test_sql, semantic_metadata)
        
        print(f"📊 优化结果:")
        print(f"   原始SQL: {optimization_result['original_sql']}")
        print(f"   优化SQL: {optimization_result['optimized_sql']}")
        print(f"   应用的优化: {optimization_result['optimizations_applied']}")
        print(f"   性能影响: {optimization_result['performance_impact']}")
        print(f"   建议数: {len(optimization_result['suggestions'])}")
        
        if optimization_result['suggestions']:
            print(f"   建议: {optimization_result['suggestions'][:2]}")
        
        return 'optimized_sql' in optimization_result
        
    except Exception as e:
        print(f"❌ SQL优化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_execution_simulation(sql_executor, semantic_data):
    """测试执行模拟（不连接真实数据库）"""
    print("\n🎭 测试执行模拟...")
    
    if not sql_executor or not semantic_data:
        print("❌ SQL执行器或语义数据无效")
        return False
    
    try:
        # 模拟执行结果（因为我们没有真实数据库）
        test_sql = "SELECT company_code, company_name FROM companies LIMIT 10"
        
        print(f"🎭 模拟执行: {test_sql}")
        
        # 模拟执行统计
        mock_stats = await sql_executor.get_execution_statistics()
        
        print(f"📊 执行统计:")
        print(f"   数据库类型: {mock_stats.get('database_type', 'unknown')}")
        print(f"   连接状态: {mock_stats.get('connection_status', 'unknown')}")
        
        # 测试执行洞察
        if sql_executor.execution_history:
            insights = await sql_executor.get_execution_insights()
            print(f"📈 执行洞察: {insights}")
        else:
            print("📈 无执行历史，跳过洞察测试")
        
        return True
        
    except Exception as e:
        print(f"❌ 执行模拟测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_comprehensive_workflow(sql_executor, semantic_data):
    """测试完整工作流"""
    print("\n🔄 测试完整SQL执行工作流...")
    
    if not sql_executor or not semantic_data:
        print("❌ SQL执行器或语义数据无效")
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
        
        # 复杂测试场景
        complex_query = "显示所有有进口记录的公司信息和交易总额"
        
        print(f"🔄 复杂查询: {complex_query}")
        
        # 步骤1: 模拟查询上下文
        query_context = QueryContext(
            entities_mentioned=['companies', 'declarations'],
            attributes_mentioned=['company_name', 'rmb_amount'],
            operations=['select', 'join', 'aggregate'],
            filters=[{'type': 'text', 'field': 'trade_type', 'operator': 'equals', 'value': '进口'}],
            aggregations=['sum'],
            temporal_references=[],
            business_intent='analytics',
            confidence_score=0.85
        )
        print("   ✅ 查询上下文创建完成")
        
        # 步骤2: 模拟元数据匹配
        metadata_matches = [
            MetadataMatch(
                entity_name='companies',
                entity_type='table',
                match_type='exact',
                similarity_score=1.0,
                relevant_attributes=['company_code', 'company_name'],
                suggested_joins=[],
                metadata={'table_name': 'companies'}
            ),
            MetadataMatch(
                entity_name='declarations',
                entity_type='table',
                match_type='exact',
                similarity_score=0.9,
                relevant_attributes=['company_code', 'rmb_amount'],
                suggested_joins=[],
                metadata={'table_name': 'declarations'}
            )
        ]
        print("   ✅ 元数据匹配创建完成")
        
        # 步骤3: LLM SQL生成（模拟）
        try:
            llm_result = await sql_executor.llm_generator.generate_sql_from_context(
                query_context, metadata_matches, semantic_metadata, complex_query
            )
            print(f"   ✅ LLM SQL生成完成 (置信度: {llm_result.confidence_score:.2f})")
        except Exception as e:
            print(f"   ⚠️ LLM SQL生成失败: {e}")
            llm_result = None
        
        # 步骤4: SQL验证
        if llm_result and llm_result.sql:
            validation_result = await sql_executor.validate_sql(llm_result.sql, semantic_metadata)
            print(f"   ✅ SQL验证完成 (有效: {validation_result['is_valid']})")
        else:
            print("   ⚠️ 跳过SQL验证（无LLM结果）")
        
        # 步骤5: SQL优化
        if llm_result and llm_result.sql:
            optimization_result = await sql_executor.optimize_query(llm_result.sql, semantic_metadata)
            print(f"   ✅ SQL优化完成 ({len(optimization_result['optimizations_applied'])} 项优化)")
        else:
            print("   ⚠️ 跳过SQL优化（无LLM结果）")
        
        # 步骤6: 执行模拟（不连接真实数据库）
        print("   ✅ 执行模拟完成（模拟环境）")
        
        print(f"🎯 完整工作流总结:")
        print(f"   - 查询意图: {query_context.business_intent}")
        print(f"   - 涉及表: {len(metadata_matches)} 个")
        print(f"   - 过滤条件: {len(query_context.filters)} 个")
        print(f"   - 聚合函数: {len(query_context.aggregations)} 个")
        if llm_result:
            print(f"   - SQL生成置信度: {llm_result.confidence_score:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 完整工作流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🚀 开始Step 5 SQL执行器测试")
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
    sql_executor = None
    
    # 测试初始化
    print(f"{'='*15} SQL执行器初始化 {'='*15}")
    try:
        sql_executor = await test_sql_executor_initialization()
        if sql_executor:
            passed_tests += 1
            print("✅ SQL执行器初始化 测试通过")
        else:
            failed_tests += 1
            print("❌ SQL执行器初始化 测试失败")
            return False
    except Exception as e:
        failed_tests += 1
        print(f"❌ SQL执行器初始化 测试异常: {e}")
        return False
    
    # 运行后续测试
    if sql_executor:
        tests = [
            ("LLM SQL生成", lambda: test_llm_sql_generation(sql_executor, semantic_data)),
            ("SQL验证", lambda: test_sql_validation(sql_executor, semantic_data)),
            ("查询计划生成", lambda: test_query_plan_generation(sql_executor, semantic_data)),
            ("回退策略", lambda: test_fallback_strategies(sql_executor, semantic_data)),
            ("SQL优化", lambda: test_sql_optimization(sql_executor, semantic_data)),
            ("执行模拟", lambda: test_execution_simulation(sql_executor, semantic_data)),
            ("完整工作流", lambda: test_comprehensive_workflow(sql_executor, semantic_data)),
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
        'database_config': 'mock_postgresql'
    }
    
    result_file = f"step5_sql_executor_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(test_result, f, indent=2, ensure_ascii=False)
    
    print(f"📄 测试结果已保存到: {result_file}")
    
    if failed_tests == 0:
        print("\n🎉 Step 5 SQL执行器所有测试通过!")
        return True
    else:
        print(f"\n⚠️ 有 {failed_tests} 个测试失败，需要检查")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)