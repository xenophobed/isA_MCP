#!/usr/bin/env python3
"""
RAG模式最终验证测试
验证所有RAG模式修复后的工作状态
"""

import asyncio
import time
from typing import Dict, Any
from core.isa_client_factory import ISAClientFactory
from tools.services.data_analytics_service.services.digital_service.base.base_rag_service import RAGConfig
from tools.services.data_analytics_service.services.digital_service.patterns.simple_rag_service import SimpleRAGService
from tools.services.data_analytics_service.services.digital_service.patterns.crag_rag_service import CRAGRAGService
from tools.services.data_analytics_service.services.digital_service.patterns.self_rag_service import SelfRAGService
from tools.services.data_analytics_service.services.digital_service.patterns.plan_rag_service import PlanRAGRAGService
from tools.services.data_analytics_service.services.digital_service.patterns.hm_rag_service import HMRAGRAGService
from tools.services.data_analytics_service.services.digital_service.patterns.raptor_rag_service import RAPTORRAGService

async def test_rag_mode(name: str, service, test_doc: str, test_query: str) -> Dict[str, Any]:
    """测试单个RAG模式"""
    start_time = time.time()
    
    try:
        user_id = f'test-{name.lower().replace(" ", "-").replace("*", "")}'
        
        # 添加文档
        doc_result = await service.process_document(
            content=test_doc,
            user_id=user_id,
            metadata={'source': 'final_test'}
        )
        
        if not doc_result.success:
            return {
                'name': name,
                'status': 'FAILED',
                'error': 'Document processing failed',
                'time': time.time() - start_time
            }
        
        # 查询
        query_result = await service.query(
            query=test_query,
            user_id=user_id
        )
        
        if not query_result.success:
            return {
                'name': name,
                'status': 'FAILED',
                'error': 'Query failed',
                'time': time.time() - start_time
            }
        
        # 检查是否使用真正的LLM生成
        is_degraded = 'Based on your knowledge base' in query_result.content
        sources_count = len(query_result.sources)
        
        return {
            'name': name,
            'status': 'DEGRADED' if is_degraded else 'SUCCESS',
            'sources': sources_count,
            'response_preview': query_result.content[:100],
            'time': time.time() - start_time
        }
        
    except Exception as e:
        return {
            'name': name,
            'status': 'ERROR',
            'error': str(e),
            'time': time.time() - start_time
        }

async def main():
    """主测试函数"""
    print("🚀 RAG模式最终验证测试")
    print("=" * 60)
    print("目标：验证所有RAG模式修复后都能正常工作\n")
    
    # 重置ISA客户端确保干净状态
    ISAClientFactory.reset_client()
    
    # 测试数据
    test_doc = """
    人工智能(AI)是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。
    机器学习是人工智能的一个子集，使计算机能够从数据中学习而无需显式编程。
    深度学习是机器学习的一个分支，使用多层神经网络来建模和理解复杂模式。
    """
    
    test_query = "什么是人工智能和机器学习的关系？"
    
    # RAG服务配置
    config = RAGConfig(
        chunk_size=500,
        overlap=50,
        top_k=3,
        similarity_threshold=0.6
    )
    
    # 所有RAG模式
    rag_services = [
        ("Simple RAG", SimpleRAGService(config)),
        ("RAPTOR RAG", RAPTORRAGService(config)),
        ("Self RAG", SelfRAGService(config)),
        ("CRAG RAG", CRAGRAGService(config)),
        ("Plan-RAG", PlanRAGRAGService(config)),
        ("HM-RAG", HMRAGRAGService(config))
    ]
    
    # 运行测试
    print("🧪 开始测试所有RAG模式...")
    print("-" * 60)
    
    results = []
    for name, service in rag_services:
        print(f"🔍 Testing {name}...", end=" ")
        result = await test_rag_mode(name, service, test_doc, test_query)
        results.append(result)
        
        # 实时反馈
        if result['status'] == 'SUCCESS':
            print("✅ SUCCESS")
        elif result['status'] == 'DEGRADED':
            print("❌ DEGRADED")
        elif result['status'] == 'ERROR':
            print(f"💥 ERROR: {result.get('error', 'Unknown')}")
        else:
            print(f"❓ {result['status']}")
    
    # 结果分析
    print("\n" + "=" * 60)
    print("📊 测试结果详细分析")
    print("=" * 60)
    
    success_count = 0
    degraded_count = 0
    error_count = 0
    
    for result in results:
        name = result['name']
        status = result['status']
        time_taken = result.get('time', 0)
        
        print(f"\n🎯 {name}")
        print(f"   状态: {status}")
        print(f"   耗时: {time_taken:.2f}秒")
        
        if status == 'SUCCESS':
            success_count += 1
            sources = result.get('sources', 0)
            preview = result.get('response_preview', '')
            print(f"   源数量: {sources}")
            print(f"   响应预览: {preview}...")
        elif status == 'DEGRADED':
            degraded_count += 1
            print(f"   ⚠️  使用降级响应")
        elif status == 'ERROR':
            error_count += 1
            error = result.get('error', 'Unknown error')
            print(f"   ❌ 错误: {error}")
    
    # 总结
    total = len(results)
    print(f"\n🎯 最终总结")
    print("=" * 30)
    print(f"总测试数: {total}")
    print(f"✅ 成功: {success_count} ({success_count/total*100:.1f}%)")
    print(f"⚠️  降级: {degraded_count} ({degraded_count/total*100:.1f}%)")
    print(f"❌ 错误: {error_count} ({error_count/total*100:.1f}%)")
    
    if success_count == total:
        print("\n🎉 所有RAG模式都正常工作！问题全部解决！")
    elif success_count > total * 0.8:
        print(f"\n✅ 大部分RAG模式工作正常！成功率: {success_count/total*100:.1f}%")
    else:
        print(f"\n⚠️  仍有问题需要解决。成功率: {success_count/total*100:.1f}%")
    
    # 具体问题分析
    if degraded_count > 0 or error_count > 0:
        print(f"\n🔍 问题分析:")
        for result in results:
            if result['status'] != 'SUCCESS':
                print(f"   - {result['name']}: {result['status']}")

if __name__ == "__main__":
    asyncio.run(main())