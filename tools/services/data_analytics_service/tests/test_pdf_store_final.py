#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 存储测试 - 使用 MCPContextClient (支持进度追踪)
"""

import sys
from pathlib import Path

# 添加项目路径
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 使用 Context Client (支持 SSE 和进度追踪)
from utils.mcp_context_client import MCPContextClient
import uuid


def test_mcp_pdf_storage():
    """测试 PDF 存储功能"""

    print("=" * 80)
    print("📚 PDF 存储测试 - MCPContextClient")
    print("=" * 80)
    print(f"项目路径: {project_root}")
    print()

    # 1. 创建客户端
    client = MCPContextClient(mcp_url="http://localhost:8081")
    session_id = f"pdf_test_{uuid.uuid4().hex[:8]}"

    print(f"会话ID: {session_id}\n")

    # 2. 测试数据
    user_id = "test_user_001"
    test_data_dir = project_root / "test_data"
    pdf_files = [
        test_data_dir / "bk01.pdf",
        test_data_dir / "bk02.pdf",
        test_data_dir / "bk03.pdf"
    ]

    # 3. 检查文件
    print("检查测试文件...")
    existing_files = []
    for pdf_path in pdf_files:
        if pdf_path.exists():
            size_mb = pdf_path.stat().st_size / (1024 * 1024)
            print(f"  ✅ {pdf_path.name} ({size_mb:.1f}MB)")
            existing_files.append(pdf_path)
        else:
            print(f"  ❌ {pdf_path.name} - 不存在")

    if not existing_files:
        print("\n❌ 没有可用的 PDF 文件")
        return 1

    # 4. 逐个处理 PDF
    results = []
    for idx, pdf_path in enumerate(existing_files, 1):
        print(f"\n{'=' * 80}")
        print(f"📄 处理 PDF {idx}/{len(existing_files)}: {pdf_path.name}")
        print(f"{'=' * 80}")

        # 定义进度回调
        def progress_handler(message: str):
            """实时显示进度"""
            if "[PROC]" in message:
                print(f"  ⏳ {message}")
            elif "[EXTR]" in message:
                print(f"  🔍 {message}")
            elif "[EMBD]" in message:
                print(f"  🧮 {message}")
            elif "[STOR]" in message:
                print(f"  💾 {message}")
            elif "Stage" in message or "%" in message:
                print(f"  📊 {message}")
            else:
                print(f"  ℹ️  {message}")

        # 调用工具
        result = client.call_tool(
            'store_knowledge',
            {
                'user_id': user_id,
                'content': str(pdf_path),
                'content_type': 'pdf',
                'metadata': {
                    'source': 'test_import',
                    'test_batch': 'pdf_store_test_final',
                    'pdf_name': pdf_path.name
                },
                'options': {
                    'rag_mode': 'custom',
                    'enable_vlm_analysis': True,
                    'enable_minio_upload': True,
                    'max_pages': 3,  # 限制为 3 页用于测试
                    'max_concurrent_pages': 2,
                    'chunking_strategy': 'page',
                    'chunk_size': 800,
                    'chunk_overlap': 100
                }
            },
            session_id=session_id,
            progress_callback=progress_handler
        )

        # 处理结果
        if result.get('success'):
            data = result.get('data', {})
            print(f"\n✅ {pdf_path.name} 存储成功!")
            print(f"   页面数: {data.get('pages_processed', 0)}")
            print(f"   图片数: {data.get('total_photos', 0)}")
            print(f"   耗时: {result.get('client_duration', 0):.2f}s")

            # Context 信息
            context = result.get('context', {})
            if context:
                print(f"\n📊 Context:")
                print(f"   Request ID: {context.get('request_id')}")
                print(f"   Correlation ID: {context.get('correlation_id')}")

            results.append({
                'pdf': pdf_path.name,
                'success': True,
                'pages': data.get('pages_processed', 0),
                'images': data.get('total_photos', 0),
                'time': result.get('client_duration', 0)
            })
        else:
            error = result.get('error', 'Unknown error')
            print(f"\n❌ {pdf_path.name} 存储失败!")
            print(f"   错误: {error}")

            results.append({
                'pdf': pdf_path.name,
                'success': False,
                'error': error
            })

    # 5. 汇总结果
    print("\n\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)

    success_count = sum(1 for r in results if r.get('success'))
    total_pages = sum(r.get('pages', 0) for r in results if r.get('success'))
    total_images = sum(r.get('images', 0) for r in results if r.get('success'))
    total_time = sum(r.get('time', 0) for r in results if r.get('success'))

    print(f"\n成功: {success_count}/{len(results)}")
    print(f"总页面数: {total_pages}")
    print(f"总图片数: {total_images}")
    print(f"总耗时: {total_time:.2f}s")

    print("\n详细结果:")
    for r in results:
        if r.get('success'):
            print(f"  ✅ {r['pdf']}: {r['pages']} 页, {r['images']} 图片, {r['time']:.2f}s")
        else:
            print(f"  ❌ {r['pdf']}: {r.get('error', 'Unknown error')}")

    print("\n" + "=" * 80)

    # 6. 显示会话历史
    print("\n📜 会话历史:")
    print("-" * 80)
    history = client.get_session_history(session_id)
    for i, entry in enumerate(history, 1):
        status_icon = "✅" if entry['success'] else "❌"
        print(f"{i}. {status_icon} {entry['tool']:20} | {entry['duration']:.2f}s | {entry['correlation_id']}")

    print("=" * 80)

    if success_count == len(results):
        print("\n🎉 所有 PDF 存储成功!")
        return 0
    else:
        print("\n⚠️ 部分 PDF 存储失败")
        return 1


if __name__ == "__main__":
    try:
        exit_code = test_mcp_pdf_storage()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
