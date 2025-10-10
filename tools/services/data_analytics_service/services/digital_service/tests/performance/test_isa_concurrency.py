#!/usr/bin/env python3
"""
ISA客户端并发测试
测试ISA客户端在并发调用时是否会出现空结果问题
"""

import asyncio
import time
from typing import List, Dict, Any
from core.isa_client_factory import ISAClientFactory, get_isa_client

async def single_isa_call(client, prompt: str, call_id: int) -> Dict[str, Any]:
    """单次ISA调用"""
    try:
        start_time = time.time()
        response = await client.invoke(
            input_data=prompt,
            task="chat",
            service_type="text",
            stream=False,
            max_tokens=50
        )
        
        result = response.get('result', '')
        success = response.get('success', False)
        
        return {
            'call_id': call_id,
            'success': success,
            'result_empty': result == '' or not result.strip(),
            'result_length': len(str(result)) if result else 0,
            'execution_time': time.time() - start_time,
            'prompt': prompt,
            'error': None if success else response.get('error', 'Unknown error')
        }
        
    except Exception as e:
        return {
            'call_id': call_id,
            'success': False,
            'result_empty': True,
            'result_length': 0,
            'execution_time': time.time() - start_time,
            'prompt': prompt,
            'error': str(e)
        }

async def test_sequential_calls():
    """测试顺序调用"""
    print("🔄 测试顺序调用 (Sequential Calls)")
    print("=" * 50)
    
    client = ISAClientFactory.get_client_sync()
    prompts = [
        "What is AI?",
        "Explain machine learning",
        "Define deep learning",
        "What is neural network?",
        "Describe computer vision"
    ]
    
    results = []
    for i, prompt in enumerate(prompts):
        print(f"  Call {i+1}: {prompt}")
        result = await single_isa_call(client, prompt, i+1)
        results.append(result)
        print(f"    ✅ Success: {result['success']}, Empty: {result['result_empty']}, Length: {result['result_length']}")
        await asyncio.sleep(0.1)  # 小延迟
    
    return results

async def test_concurrent_calls():
    """测试并发调用"""
    print("\n⚡ 测试并发调用 (Concurrent Calls)")
    print("=" * 50)
    
    client = ISAClientFactory.get_client_sync()
    prompts = [
        "What is AI?",
        "Explain machine learning", 
        "Define deep learning",
        "What is neural network?",
        "Describe computer vision",
        "What is NLP?",
        "Explain reinforcement learning",
        "What is computer science?",
        "Define algorithm",
        "What is data science?"
    ]
    
    print(f"  启动 {len(prompts)} 个并发调用...")
    
    # 创建并发任务
    tasks = [
        single_isa_call(client, prompt, i+1) 
        for i, prompt in enumerate(prompts)
    ]
    
    # 并发执行
    results = await asyncio.gather(*tasks)
    
    # 分析结果
    for result in results:
        status = "✅" if result['success'] and not result['result_empty'] else "❌"
        print(f"    {status} Call {result['call_id']}: Success={result['success']}, Empty={result['result_empty']}, Length={result['result_length']}")
    
    return results

async def test_shared_vs_individual_clients():
    """测试共享客户端 vs 独立客户端"""
    print("\n🔀 测试共享客户端 vs 独立客户端")
    print("=" * 50)
    
    prompts = ["What is AI?", "What is ML?", "What is DL?"]
    
    # 测试1: 共享客户端
    print("  测试1: 共享客户端 (Shared Client)")
    shared_client = ISAClientFactory.get_client_sync()
    shared_tasks = [
        single_isa_call(shared_client, prompt, i+1) 
        for i, prompt in enumerate(prompts)
    ]
    shared_results = await asyncio.gather(*shared_tasks)
    
    for result in shared_results:
        status = "✅" if result['success'] and not result['result_empty'] else "❌"
        print(f"    {status} Shared Call {result['call_id']}: Empty={result['result_empty']}")
    
    # 测试2: 多个客户端实例 (应该都是同一个，因为单例)
    print("  测试2: 多个get_isa_client调用 (Multiple get_isa_client)")
    individual_tasks = [
        single_isa_call(get_isa_client(), prompt, i+1) 
        for i, prompt in enumerate(prompts)
    ]
    individual_results = await asyncio.gather(*individual_tasks)
    
    for result in individual_results:
        status = "✅" if result['success'] and not result['result_empty'] else "❌"
        print(f"    {status} Individual Call {result['call_id']}: Empty={result['result_empty']}")
    
    return shared_results, individual_results

async def test_high_concurrency():
    """测试高并发"""
    print("\n🚀 测试高并发 (High Concurrency)")
    print("=" * 50)
    
    client = ISAClientFactory.get_client_sync()
    
    # 20个并发调用
    prompts = [f"What is concept {i}?" for i in range(20)]
    
    print(f"  启动 {len(prompts)} 个高并发调用...")
    
    tasks = [
        single_isa_call(client, prompt, i+1) 
        for i, prompt in enumerate(prompts)
    ]
    
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # 统计结果
    successful = sum(1 for r in results if r['success'] and not r['result_empty'])
    empty_results = sum(1 for r in results if r['result_empty'])
    errors = sum(1 for r in results if not r['success'])
    
    print(f"  总时间: {total_time:.2f}秒")
    print(f"  成功: {successful}/{len(results)}")
    print(f"  空结果: {empty_results}/{len(results)}")
    print(f"  错误: {errors}/{len(results)}")
    
    # 显示前几个失败的案例
    failed_results = [r for r in results if r['result_empty'] or not r['success']]
    if failed_results:
        print("  前5个失败案例:")
        for result in failed_results[:5]:
            print(f"    Call {result['call_id']}: Success={result['success']}, Empty={result['result_empty']}, Error={result['error']}")
    
    return results

def analyze_results(test_name: str, results: List[Dict[str, Any]]):
    """分析测试结果"""
    print(f"\n📊 {test_name} 结果分析")
    print("-" * 30)
    
    total = len(results)
    successful = sum(1 for r in results if r['success'] and not r['result_empty'])
    empty_results = sum(1 for r in results if r['result_empty'])
    errors = sum(1 for r in results if not r['success'])
    
    print(f"总调用数: {total}")
    print(f"成功率: {successful/total*100:.1f}% ({successful}/{total})")
    print(f"空结果率: {empty_results/total*100:.1f}% ({empty_results}/{total})")
    print(f"错误率: {errors/total*100:.1f}% ({errors}/{total})")
    
    if results:
        avg_time = sum(r['execution_time'] for r in results) / len(results)
        print(f"平均执行时间: {avg_time:.3f}秒")

async def main():
    """主测试函数"""
    print("🧪 ISA客户端并发测试")
    print("=" * 60)
    print("目标：检测ISA客户端在并发调用时是否会返回空结果")
    print()
    
    try:
        # 测试1: 顺序调用
        sequential_results = await test_sequential_calls()
        analyze_results("顺序调用", sequential_results)
        
        # 测试2: 并发调用
        concurrent_results = await test_concurrent_calls()
        analyze_results("并发调用", concurrent_results)
        
        # 测试3: 共享 vs 独立客户端
        shared_results, individual_results = await test_shared_vs_individual_clients()
        analyze_results("共享客户端", shared_results)
        analyze_results("独立客户端", individual_results)
        
        # 测试4: 高并发
        high_concurrency_results = await test_high_concurrency()
        analyze_results("高并发", high_concurrency_results)
        
        # 总结
        print("\n🎯 测试总结")
        print("=" * 60)
        
        all_tests = [
            ("顺序调用", sequential_results),
            ("并发调用", concurrent_results), 
            ("高并发", high_concurrency_results)
        ]
        
        for test_name, results in all_tests:
            empty_count = sum(1 for r in results if r['result_empty'])
            if empty_count > 0:
                print(f"❌ {test_name}: 发现 {empty_count} 个空结果，存在并发问题！")
            else:
                print(f"✅ {test_name}: 无空结果，并发正常")
        
        # 检查是否确实是单例
        client1 = ISAClientFactory.get_client_sync()
        client2 = get_isa_client()
        print(f"\n🔍 客户端单例验证: {client1 is client2} (应该是True)")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())