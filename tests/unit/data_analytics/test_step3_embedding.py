#!/usr/bin/env python3
"""
Step 3 Test: 向量存储测试
使用Step 2的语义增强结果进行向量存储
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

from embedding_storage import EmbeddingStorage, EmbeddingRecord, SearchResult
from semantic_enricher import SemanticMetadata

# 加载Step 2的结果
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

async def test_embedding_storage_initialization():
    """测试向量存储初始化"""
    print("🔧 测试向量存储初始化...")
    
    try:
        storage = EmbeddingStorage("customs_trade_db")
        await storage.initialize()
        print("✅ 向量存储初始化成功")
        return storage
    except Exception as e:
        print(f"❌ 向量存储初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_store_semantic_metadata(storage, semantic_data):
    """测试存储语义元数据"""
    print("\n💾 测试存储语义元数据...")
    
    if not storage:
        print("❌ 存储实例无效")
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
        
        print(f"📊 准备存储:")
        print(f"   - 业务实体: {len(semantic_metadata.business_entities)}")
        print(f"   - 语义标签: {len(semantic_metadata.semantic_tags)}")
        print(f"   - 业务规则: {len(semantic_metadata.business_rules)}")
        print(f"   - 数据模式: {len(semantic_metadata.data_patterns)}")
        
        # 存储语义元数据
        results = await storage.store_semantic_metadata(semantic_metadata)
        
        print(f"📊 存储结果:")
        print(f"   - 成功存储: {results['stored_embeddings']} 个向量")
        print(f"   - 失败: {results['failed_embeddings']} 个")
        print(f"   - 错误数: {len(results['errors'])}")
        
        if results['errors']:
            print("⚠️ 错误列表:")
            for error in results['errors'][:3]:  # 显示前3个错误
                print(f"   - {error}")
        
        return results['stored_embeddings'] > 0
        
    except Exception as e:
        print(f"❌ 存储语义元数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_semantic_search(storage):
    """测试语义搜索"""
    print("\n🔍 测试语义搜索...")
    
    if not storage:
        print("❌ 存储实例无效")
        return False
    
    try:
        # 测试查询
        test_queries = [
            ("公司企业信息", "table"),
            ("海关申报单据", "table"),
            ("货物详细信息", None),
            ("业务规则约束", "business_rule"),
            ("数据模式关系", "data_pattern")
        ]
        
        search_results = []
        
        for query, entity_type in test_queries:
            print(f"🔍 搜索: {query} (类型: {entity_type or '全部'})")
            
            results = await storage.search_similar_entities(
                query, 
                entity_type=entity_type, 
                limit=3, 
                similarity_threshold=0.3  # 降低阈值
            )
            
            if results:
                print(f"   找到 {len(results)} 个相似结果:")
                for i, result in enumerate(results):
                    print(f"   {i+1}. {result.entity_name} ({result.entity_type}) - 相似度: {result.similarity_score:.3f}")
                    print(f"      {result.content[:60]}...")
                search_results.extend(results)
            else:
                print("   未找到相似结果")
        
        print(f"📊 搜索测试完成，总共找到 {len(search_results)} 个结果")
        return len(search_results) > 0
        
    except Exception as e:
        print(f"❌ 语义搜索测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_metadata_stats(storage):
    """测试元数据统计"""
    print("\n📊 测试元数据统计...")
    
    if not storage:
        print("❌ 存储实例无效")
        return False
    
    try:
        stats = await storage.get_metadata_stats()
        
        if stats['success']:
            print("📈 数据库统计:")
            for stat in stats['stats']:
                print(f"   - {stat['entity_type']}: {stat['total_entities']} 个 (平均置信度: {stat['avg_confidence']:.2f})")
            return True
        else:
            print(f"❌ 获取统计失败: {stats.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ 元数据统计测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🚀 开始Step 3向量存储测试")
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
    storage = None
    
    # 测试向量存储初始化
    print(f"{'='*15} 向量存储初始化 {'='*15}")
    try:
        storage = await test_embedding_storage_initialization()
        if storage:
            passed_tests += 1
            print("✅ 向量存储初始化 测试通过")
        else:
            failed_tests += 1
            print("❌ 向量存储初始化 测试失败")
            return False
    except Exception as e:
        failed_tests += 1
        print(f"❌ 向量存储初始化 测试异常: {e}")
        return False
    
    # 运行后续测试
    if storage:
        tests = [
            ("存储语义元数据", lambda: test_store_semantic_metadata(storage, semantic_data)),
            ("语义搜索", lambda: test_semantic_search(storage)),
            ("元数据统计", lambda: test_metadata_stats(storage)),
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
        'database_source': 'customs_trade_db'
    }
    
    result_file = f"step3_embedding_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(test_result, f, indent=2, ensure_ascii=False)
    
    print(f"📄 测试结果已保存到: {result_file}")
    
    if failed_tests == 0:
        print("\n🎉 Step 3向量存储所有测试通过!")
        return True
    else:
        print(f"\n⚠️ 有 {failed_tests} 个测试失败，需要检查")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)