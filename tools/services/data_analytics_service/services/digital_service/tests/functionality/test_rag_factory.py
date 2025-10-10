#!/usr/bin/env python3
"""
RAG Factory Test - 测试新的Factory模式架构

这个文件用于测试新的RAG Factory模式架构的基本功能。
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from rag_factory import RAGService, RAGFactory
from base.base_rag_service import RAGConfig, RAGMode

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_factory_creation():
    """测试工厂创建"""
    print("测试1: 工厂创建")
    
    try:
        factory = RAGFactory()
        available_modes = factory.get_available_modes()
        
        print(f"✓ 工厂创建成功")
        print(f"✓ 可用模式: {[mode.value for mode in available_modes]}")
        
        # 测试创建服务
        simple_service = factory.create_service(RAGMode.SIMPLE)
        print(f"✓ Simple RAG服务创建成功: {simple_service.get_capabilities()['name']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 工厂创建失败: {e}")
        return False

async def test_service_creation():
    """测试服务创建"""
    print("\n测试2: 服务创建")
    
    try:
        rag_service = RAGService()
        
        print(f"✓ 主RAG服务创建成功")
        print(f"✓ 可用模式: {[mode.value for mode in rag_service.get_available_modes()]}")
        
        # 测试模式信息
        simple_info = rag_service.get_mode_info(RAGMode.SIMPLE)
        print(f"✓ Simple RAG信息: {simple_info['name']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 服务创建失败: {e}")
        return False

async def test_config_validation():
    """测试配置验证"""
    print("\n测试3: 配置验证")
    
    try:
        # 测试有效配置
        valid_config = RAGConfig(
            mode=RAGMode.SIMPLE,
            chunk_size=400,
            overlap=50,
            top_k=5
        )
        
        rag_service = RAGService(valid_config)
        print(f"✓ 有效配置创建成功")
        
        # 测试无效配置
        try:
            invalid_config = RAGConfig(
                mode=RAGMode.SIMPLE,
                chunk_size=-1,  # 无效值
                overlap=50,
                top_k=5
            )
            rag_service_invalid = RAGService(invalid_config)
            print(f"✗ 无效配置应该失败但没有失败")
            return False
        except ValueError:
            print(f"✓ 无效配置正确被拒绝")
        
        return True
        
    except Exception as e:
        print(f"✗ 配置验证失败: {e}")
        return False

async def test_mode_recommendation():
    """测试模式推荐"""
    print("\n测试4: 模式推荐")
    
    try:
        rag_service = RAGService()
        
        # 测试简单查询
        simple_query = "什么是AI？"
        simple_rec = await rag_service.recommend_mode(simple_query, "user123")
        print(f"✓ 简单查询推荐: {simple_rec['recommended_mode']}")
        
        # 测试复杂查询
        complex_query = "请详细分析人工智能的发展历程、技术分支和未来趋势"
        complex_rec = await rag_service.recommend_mode(complex_query, "user123")
        print(f"✓ 复杂查询推荐: {complex_rec['recommended_mode']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 模式推荐失败: {e}")
        return False

async def test_performance_monitoring():
    """测试性能监控"""
    print("\n测试5: 性能监控")
    
    try:
        rag_service = RAGService()
        
        # 获取初始指标
        initial_metrics = rag_service.get_performance_metrics()
        print(f"✓ 初始指标获取成功")
        print(f"  总查询数: {initial_metrics['total_queries']}")
        
        # 模拟一些查询（不会真正执行，因为需要数据库连接）
        # 这里只是测试指标更新逻辑
        rag_service._update_performance_metrics(RAGMode.SIMPLE, 1.5, True)
        rag_service._update_performance_metrics(RAGMode.RAPTOR, 2.3, True)
        
        updated_metrics = rag_service.get_performance_metrics()
        print(f"✓ 性能指标更新成功")
        print(f"  总查询数: {updated_metrics['total_queries']}")
        print(f"  成功率: {updated_metrics['success_rate']:.2%}")
        
        return True
        
    except Exception as e:
        print(f"✗ 性能监控失败: {e}")
        return False

async def test_mode_comparison():
    """测试模式对比"""
    print("\n测试6: 模式对比")
    
    try:
        rag_service = RAGService()
        
        comparison = rag_service.get_mode_comparison()
        print(f"✓ 模式对比获取成功")
        
        for mode, info in comparison.items():
            print(f"  {mode}: {info['name']} - 复杂度: {info['complexity']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 模式对比失败: {e}")
        return False

async def test_service_capabilities():
    """测试服务能力"""
    print("\n测试7: 服务能力")
    
    try:
        factory = RAGFactory()
        
        # 测试所有模式的能力
        for mode in [RAGMode.SIMPLE, RAGMode.RAPTOR, RAGMode.SELF_RAG]:
            service = factory.create_service(mode)
            capabilities = service.get_capabilities()
            
            print(f"✓ {mode.value}: {capabilities['name']}")
            print(f"  特性: {capabilities['features'][:2]}...")
            print(f"  复杂度: {capabilities['complexity']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 服务能力测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("RAG Factory模式架构测试")
    print("=" * 40)
    
    tests = [
        test_factory_creation,
        test_service_creation,
        test_config_validation,
        test_mode_recommendation,
        test_performance_monitoring,
        test_mode_comparison,
        test_service_capabilities
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            print(f"✗ 测试异常: {e}")
    
    print("\n" + "=" * 40)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return True
    else:
        print("❌ 部分测试失败")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
