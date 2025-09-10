#!/usr/bin/env python3
"""
RAG Service Usage Examples - 多模式RAG服务使用示例

展示如何使用升级后的多模式RAG服务
"""

import asyncio
import logging
from typing import Dict, Any

from .enhanced_rag_service import EnhancedRAGService, RAGMode, RAGConfig

logger = logging.getLogger(__name__)

async def example_simple_rag():
    """示例1: 简单RAG使用"""
    print("=== 简单RAG示例 ===")
    
    # 创建RAG服务
    config = RAGConfig(mode=RAGMode.SIMPLE)
    rag_service = EnhancedRAGService(config)
    
    # 处理文档
    document = """
    人工智能（AI）是计算机科学的一个分支，它企图了解智能的实质，
    并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
    该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
    """
    
    user_id = "user_123"
    
    # 存储文档
    result = await rag_service.process_document(
        content=document,
        user_id=user_id,
        metadata={"source": "ai_introduction", "category": "technology"}
    )
    
    print(f"文档处理结果: {result['success']}")
    print(f"处理模式: {result.get('mode', 'unknown')}")
    
    # 查询
    query = "什么是人工智能？"
    response = await rag_service.query(
        query=query,
        user_id=user_id
    )
    
    print(f"查询: {query}")
    print(f"回答: {response.content}")
    print(f"使用模式: {response.mode_used.value}")
    print(f"处理时间: {response.processing_time:.2f}秒")

async def example_raptor_rag():
    """示例2: RAPTOR RAG使用"""
    print("\n=== RAPTOR RAG示例 ===")
    
    # 创建RAPTOR RAG配置
    config = RAGConfig(mode=RAGMode.RAPTOR)
    rag_service = EnhancedRAGService(config)
    
    # 长文档处理
    long_document = """
    第一章：人工智能的发展历史
    
    人工智能的概念最早可以追溯到古希腊神话中的自动机器。
    现代人工智能的发展可以分为几个阶段：
    
    1. 符号主义阶段（1950s-1960s）
    这个阶段主要关注符号推理和逻辑编程。代表性工作包括：
    - 图灵测试的提出
    - 逻辑理论机的开发
    - 专家系统的兴起
    
    2. 连接主义阶段（1980s-1990s）
    这个阶段主要关注神经网络和机器学习：
    - 反向传播算法的发明
    - 多层感知机的应用
    - 支持向量机的提出
    
    3. 深度学习阶段（2000s-现在）
    这个阶段以深度学习为代表：
    - 卷积神经网络的成功
    - 循环神经网络的应用
    - 注意力机制的引入
    - Transformer架构的革命
    
    第二章：人工智能的技术分类
    
    人工智能技术可以分为以下几类：
    
    1. 机器学习
    机器学习是人工智能的核心技术之一，包括：
    - 监督学习：使用标记数据训练模型
    - 无监督学习：从无标记数据中发现模式
    - 强化学习：通过与环境交互学习最优策略
    
    2. 自然语言处理
    自然语言处理关注计算机理解和生成人类语言：
    - 文本分类和情感分析
    - 机器翻译
    - 问答系统
    - 文本生成
    
    3. 计算机视觉
    计算机视觉让机器能够"看见"和理解图像：
    - 图像分类
    - 目标检测
    - 图像分割
    - 人脸识别
    
    第三章：人工智能的应用领域
    
    人工智能在各个领域都有广泛应用：
    
    1. 医疗健康
    - 医学影像诊断
    - 药物发现
    - 个性化治疗
    - 健康监测
    
    2. 金融服务
    - 风险评估
    - 算法交易
    - 反欺诈检测
    - 智能投顾
    
    3. 交通运输
    - 自动驾驶
    - 交通优化
    - 智能物流
    - 无人机配送
    
    4. 教育领域
    - 个性化学习
    - 智能辅导
    - 自动评分
    - 学习分析
    """
    
    user_id = "user_456"
    
    # 处理长文档
    result = await rag_service.process_document(
        content=long_document,
        user_id=user_id,
        metadata={"source": "ai_comprehensive_guide", "category": "education"}
    )
    
    print(f"长文档处理结果: {result['success']}")
    print(f"树结构层级: {result.get('tree_levels', 0)}")
    print(f"总节点数: {result.get('total_nodes', 0)}")
    
    # 复杂查询
    complex_query = "人工智能在医疗领域有哪些具体应用？请详细说明。"
    response = await rag_service.query(
        query=complex_query,
        user_id=user_id
    )
    
    print(f"复杂查询: {complex_query}")
    print(f"回答: {response.content}")
    print(f"使用模式: {response.mode_used.value}")

async def example_auto_mode_selection():
    """示例3: 自动模式选择"""
    print("\n=== 自动模式选择示例 ===")
    
    # 创建支持自动选择的RAG服务
    config = RAGConfig()
    rag_service = EnhancedRAGService(config)
    
    user_id = "user_789"
    
    # 不同复杂度的查询
    queries = [
        "什么是机器学习？",  # 简单查询
        "请分析人工智能在医疗、金融、教育三个领域的应用差异和共同点",  # 复杂分析查询
        "为什么深度学习在2010年后突然爆发？请从技术、数据、计算三个角度解释",  # 推理查询
        "请评估当前大语言模型的优缺点，并预测未来发展趋势"  # 反思性查询
    ]
    
    for query in queries:
        print(f"\n查询: {query}")
        
        # 获取模式推荐
        recommendation = await rag_service.recommend_mode(query, user_id)
        print(f"推荐模式: {recommendation['recommended_mode']}")
        print(f"推荐原因: {recommendation['mode_info']['description']}")
        
        # 使用自动模式选择进行查询
        response = await rag_service.query(
            query=query,
            user_id=user_id,
            auto_mode_selection=True
        )
        
        print(f"实际使用模式: {response.mode_used.value}")
        print(f"回答: {response.content[:200]}...")

async def example_hybrid_rag():
    """示例4: 混合RAG模式"""
    print("\n=== 混合RAG模式示例 ===")
    
    config = RAGConfig()
    rag_service = EnhancedRAGService(config)
    
    user_id = "user_hybrid"
    
    # 处理文档
    document = """
    大语言模型（Large Language Models, LLMs）是近年来人工智能领域的重要突破。
    这些模型通过在大规模文本数据上进行预训练，学习到了丰富的语言知识和世界知识。
    
    主要特点包括：
    1. 参数规模巨大（数十亿到数千亿参数）
    2. 训练数据海量（数万亿token）
    3. 涌现能力（Emergent Abilities）
    4. 上下文学习能力（In-Context Learning）
    
    应用领域：
    - 文本生成和创作
    - 代码生成和编程辅助
    - 问答和对话系统
    - 文本摘要和翻译
    - 知识推理和问题求解
    """
    
    # 存储文档
    await rag_service.process_document(
        content=document,
        user_id=user_id,
        metadata={"source": "llm_overview", "category": "ai_technology"}
    )
    
    # 混合查询
    query = "大语言模型有哪些特点和应用？请详细分析其技术原理。"
    
    response = await rag_service.hybrid_query(
        query=query,
        user_id=user_id,
        modes=[RAGMode.SIMPLE, RAGMode.RAPTOR, RAGMode.SELF_RAG]
    )
    
    print(f"混合查询: {query}")
    print(f"使用模式: {response.metadata['modes_used']}")
    print(f"模式结果: {response.metadata['mode_results']}")
    print(f"整合回答: {response.content}")

async def example_performance_monitoring():
    """示例5: 性能监控"""
    print("\n=== 性能监控示例 ===")
    
    config = RAGConfig()
    rag_service = EnhancedRAGService(config)
    
    user_id = "user_perf"
    
    # 执行多个查询
    queries = [
        "什么是深度学习？",
        "请分析神经网络的发展历程",
        "机器学习和深度学习的区别是什么？",
        "请解释反向传播算法的原理",
        "卷积神经网络有哪些应用？"
    ]
    
    for i, query in enumerate(queries):
        # 随机选择模式
        mode = list(RAGMode)[i % len(RAGMode)]
        
        response = await rag_service.query(
            query=query,
            user_id=user_id,
            mode=mode
        )
        
        print(f"查询 {i+1}: {query[:30]}...")
        print(f"模式: {response.mode_used.value}")
        print(f"成功: {response.success}")
        print(f"时间: {response.processing_time:.2f}秒")
        print()
    
    # 获取性能指标
    metrics = await rag_service.get_performance_metrics()
    
    print("=== 性能指标 ===")
    print(f"总查询数: {metrics['total_queries']}")
    print(f"成功查询数: {metrics['successful_queries']}")
    print(f"成功率: {metrics['success_rate']:.2%}")
    print(f"平均响应时间: {metrics['average_response_time']:.2f}秒")
    print("\n模式使用统计:")
    for mode, count in metrics['mode_usage'].items():
        print(f"  {mode}: {count}次")
    
    print("\n模式性能统计:")
    for mode, perf in metrics['mode_performance'].items():
        if perf:
            print(f"  {mode}: 平均{perf['average_time']:.2f}秒, {perf['query_count']}次查询")

async def example_mode_comparison():
    """示例6: 模式对比"""
    print("\n=== 模式对比示例 ===")
    
    config = RAGConfig()
    rag_service = EnhancedRAGService(config)
    
    user_id = "user_compare"
    
    # 处理相同文档
    document = """
    区块链技术是一种分布式账本技术，通过密码学方法将数据块按时间顺序链接起来。
    每个区块包含前一个区块的哈希值，形成不可篡改的链条。
    
    主要特点：
    1. 去中心化：没有中央权威机构控制
    2. 不可篡改：一旦记录，难以修改
    3. 透明性：所有交易公开可查
    4. 共识机制：通过算法达成一致
    
    应用场景：
    - 加密货币（比特币、以太坊）
    - 智能合约
    - 供应链管理
    - 数字身份认证
    - 投票系统
    """
    
    await rag_service.process_document(
        content=document,
        user_id=user_id,
        metadata={"source": "blockchain_guide", "category": "technology"}
    )
    
    query = "区块链技术有哪些特点和应用？"
    
    # 测试不同模式
    modes_to_test = [RAGMode.SIMPLE, RAGMode.RAPTOR, RAGMode.SELF_RAG]
    
    results = {}
    
    for mode in modes_to_test:
        print(f"\n--- 测试 {mode.value.upper()} 模式 ---")
        
        start_time = asyncio.get_event_loop().time()
        
        response = await rag_service.query(
            query=query,
            user_id=user_id,
            mode=mode
        )
        
        end_time = asyncio.get_event_loop().time()
        
        results[mode] = {
            'response': response,
            'time': end_time - start_time
        }
        
        print(f"成功: {response.success}")
        print(f"响应时间: {response.processing_time:.2f}秒")
        print(f"源数量: {len(response.sources)}")
        print(f"回答长度: {len(response.content)}字符")
        print(f"回答预览: {response.content[:100]}...")
    
    # 对比分析
    print("\n=== 模式对比分析 ===")
    print(f"{'模式':<15} {'成功':<8} {'时间(秒)':<10} {'源数量':<8} {'回答长度':<10}")
    print("-" * 60)
    
    for mode, result in results.items():
        response = result['response']
        print(f"{mode.value:<15} {response.success!s:<8} {response.processing_time:<10.2f} {len(response.sources):<8} {len(response.content):<10}")

async def main():
    """主函数 - 运行所有示例"""
    print("🚀 多模式RAG服务使用示例")
    print("=" * 50)
    
    try:
        # 运行所有示例
        await example_simple_rag()
        await example_raptor_rag()
        await example_auto_mode_selection()
        await example_hybrid_rag()
        await example_performance_monitoring()
        await example_mode_comparison()
        
        print("\n✅ 所有示例运行完成！")
        
    except Exception as e:
        logger.error(f"示例运行失败: {e}")
        print(f"❌ 示例运行失败: {e}")

if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 运行示例
    asyncio.run(main())
