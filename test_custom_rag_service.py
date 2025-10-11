#!/usr/bin/env python3
"""
Test script for Custom RAG Service

测试 custom_rag_service.py 的功能：
1. PDF 摄取（文本 + 图片）
2. 检索（文本 + 图片）
3. 生成（带图片引用的答案）
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.services.data_analytics_service.services.digital_service.patterns.custom_rag_service import (
    CustomRAGService
)


async def test_custom_rag_service():
    """测试 Custom RAG Service 的完整流程"""
    
    print("=" * 80)
    print("Custom RAG Service 测试")
    print("=" * 80)
    
    # 初始化服务（页面级多模态RAG）
    print("\n📦 1. 初始化 Custom RAG Service (页面级多模态)...")
    config = {
        'top_k_results': 5,
        'max_concurrent_pages': 2,  # 页面级并发数
        'max_pages': 3,  # 只处理 3 个页面（快速测试）
        'enable_vlm_analysis': True,   # 启用 VLM 页面分析
        'enable_minio_upload': False   # MinIO 不可用，暂时禁用
    }
    print(f"   配置: 页面级并发={config['max_concurrent_pages']}, 最多处理{config['max_pages']}页")
    print(f"   VLM分析: {'启用' if config['enable_vlm_analysis'] else '禁用'}")
    
    try:
        service = CustomRAGService(config)
        print("✅ Custom RAG Service 初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 测试 PDF 摄取
    print("\n📥 2. 测试 PDF 摄取...")
    pdf_path = "/Users/xenodennis/Documents/Fun/isA_MCP/test_data/crm_manual.pdf"
    user_id = "test_user_001"
    
    if not os.path.exists(pdf_path):
        print(f"⚠️ PDF 文件不存在: {pdf_path}")
        print("请提供一个有效的 PDF 文件路径")
        return
    
    print(f"   PDF 路径: {pdf_path}")
    print(f"   用户 ID: {user_id}")
    
    try:
        ingestion_result = await service.ingest_pdf(
            pdf_path=pdf_path,
            user_id=user_id,
            metadata={'source': 'test', 'category': 'crm_manual'}
        )
        
        if ingestion_result.get('success'):
            print("✅ PDF 摄取成功!")
            stats = ingestion_result.get('statistics', {})
            print(f"   📄 页面数: {stats.get('pages_stored', 0)}")
            print(f"   🖼️ 图片数: {stats.get('images_stored', 0)}")
            print(f"   📊 总记录数: {stats.get('total_records', 0)}")
            print(f"   ⏱️ 处理时间: {ingestion_result.get('processing_time', 0):.2f}s")
        else:
            print(f"❌ PDF 摄取失败: {ingestion_result.get('error')}")
            return
            
    except Exception as e:
        print(f"❌ PDF 摄取异常: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 测试检索
    print("\n🔍 3. 测试检索...")
    test_queries = [
        "订单管理页面应该如何操作？",
        "CRM系统的主要功能有哪些？",
        "如何创建新客户？"
    ]
    
    for query in test_queries:
        print(f"\n   查询: {query}")
        
        try:
            retrieval_result = await service.retrieve(
                user_id=user_id,
                query=query,
                top_k=3
            )
            
            if retrieval_result.get('success'):
                page_results = retrieval_result.get('page_results', [])
                total_photos = retrieval_result.get('total_photos', 0)
                
                print(f"   ✅ 检索成功:")
                print(f"      📄 页面结果: {len(page_results)} 个")
                print(f"      🖼️ 图片总数: {total_photos} 张")
                
                # 显示前 2 个页面结果
                for idx, result in enumerate(page_results[:2], 1):
                    page_num = result.get('page_number', 'N/A')
                    summary = result.get('page_summary', '')[:60]
                    score = result.get('similarity_score', 0)
                    photo_urls = result.get('photo_urls', [])
                    
                    print(f"      [{idx}] 页{page_num} (相似度:{score:.3f})")
                    if summary:
                        print(f"          摘要: {summary}...")
                    if photo_urls:
                        print(f"          包含 {len(photo_urls)} 张图片")
                        for photo_idx, url in enumerate(photo_urls[:2], 1):
                            print(f"            图{photo_idx}: {url[:60]}...")
                
            else:
                print(f"   ❌ 检索失败: {retrieval_result.get('error')}")
                
        except Exception as e:
            print(f"   ❌ 检索异常: {e}")
            import traceback
            traceback.print_exc()
    
    # 测试完整 RAG 流程（检索 + 生成）
    print("\n🤖 4. 测试完整 RAG 流程（检索 + 生成）...")
    test_query = "订单管理页面应该如何操作？请提供详细步骤。"
    print(f"   问题: {test_query}")
    
    try:
        rag_result = await service.query_with_generation(
            user_id=user_id,
            query=test_query,
            generation_config={'model': 'gpt-4o-mini', 'temperature': 0.3}
        )
        
        if rag_result.get('success'):
            print("   ✅ RAG 生成成功!")
            answer = rag_result.get('answer', '')
            sources = rag_result.get('sources', {})
            
            print(f"\n   📝 生成的答案:")
            print(f"   {'-' * 70}")
            print(f"   {answer[:500]}...")
            print(f"   {'-' * 70}")
            print(f"\n   📊 来源统计:")
            print(f"      页面来源: {sources.get('page_count', 0)} 个")
            print(f"      图片总数: {sources.get('photo_count', 0)} 张")
            
            # 显示页面来源和图片
            page_sources = sources.get('page_sources', [])
            if page_sources:
                print(f"\n   📄 相关页面和图片:")
                for idx, page_src in enumerate(page_sources, 1):
                    page_num = page_src.get('page_number', 'N/A')
                    summary = page_src.get('page_summary', '')[:50]
                    photo_urls = page_src.get('photo_urls', [])
                    
                    print(f"      [页面{idx}] 第{page_num}页: {summary}...")
                    if photo_urls:
                        for photo_idx, url in enumerate(photo_urls[:2], 1):
                            print(f"          图片{photo_idx}: {url[:60]}...")
        else:
            print(f"   ❌ RAG 生成失败: {rag_result.get('error')}")
            
    except Exception as e:
        print(f"   ❌ RAG 生成异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ 测试完成!")
    print("=" * 80)


async def test_components():
    """测试各个组件是否可用"""
    print("\n🔧 测试组件可用性...")
    
    # 测试 MinIO
    print("\n1. 测试 MinIO...")
    try:
        from core.minio_client import get_minio_client
        minio_client = get_minio_client()
        if minio_client.is_available():
            print("   ✅ MinIO 可用")
        else:
            print("   ⚠️ MinIO 不可用（将使用 Mock）")
    except Exception as e:
        print(f"   ❌ MinIO 错误: {e}")
    
    # 测试 ImageAnalyzer
    print("\n2. 测试 ImageAnalyzer...")
    try:
        from tools.services.intelligence_service.vision.image_analyzer import analyze
        print("   ✅ ImageAnalyzer 可用")
    except Exception as e:
        print(f"   ❌ ImageAnalyzer 错误: {e}")
    
    # 测试 PDFProcessor
    print("\n3. 测试 PDFProcessor...")
    try:
        from tools.services.data_analytics_service.processors.file_processors.pdf_processor import PDFProcessor
        pdf_processor = PDFProcessor()
        print("   ✅ PDFProcessor 可用")
    except Exception as e:
        print(f"   ❌ PDFProcessor 错误: {e}")
    
    # 测试 Embedding
    print("\n4. 测试 Embedding...")
    try:
        from tools.services.intelligence_service.language.embedding_generator import embedding_generator
        test_embedding = await embedding_generator.embed("test text")
        print(f"   ✅ Embedding 可用 (维度: {len(test_embedding)})")
    except Exception as e:
        print(f"   ❌ Embedding 错误: {e}")
    
    # 测试 Vector DB
    print("\n5. 测试 Vector DB (Supabase)...")
    try:
        from tools.services.intelligence_service.vector_db import get_vector_db, VectorDBType
        vector_db = get_vector_db(VectorDBType.SUPABASE)
        stats = await vector_db.get_stats()
        print(f"   ✅ Vector DB 可用: {stats}")
    except Exception as e:
        print(f"   ❌ Vector DB 错误: {e}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Custom RAG Service')
    parser.add_argument('--components-only', action='store_true', 
                       help='只测试组件可用性')
    parser.add_argument('--pdf', type=str, 
                       help='指定 PDF 文件路径')
    
    args = parser.parse_args()
    
    if args.components_only:
        await test_components()
    else:
        await test_components()
        print("\n")
        await test_custom_rag_service()


if __name__ == "__main__":
    asyncio.run(main())

