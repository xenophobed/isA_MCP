#!/usr/bin/env python3
"""
RAG综合评估测试 - 困难测试案例
设计多维度评估所有7个RAG模式的性能
"""

import asyncio
import time
import json
from typing import Dict, Any, List
from dataclasses import dataclass
from tools.services.data_analytics_service.services.digital_service.base.base_rag_service import RAGConfig

# 复杂测试文档 - 多主题、多关系、需要推理
COMPLEX_TEST_DOCUMENT = """
人工智能发展历程与商业应用分析报告

## 历史背景
人工智能(AI)概念最早由Alan Turing在1950年提出，他在论文《Computing Machinery and Intelligence》中首次探讨了机器思维的可能性。1956年，John McCarthy、Marvin Minsky、Claude Shannon和Nathaniel Rochester在达特茅斯学院组织了第一次AI会议，正式确立了"人工智能"这一术语。

## 技术发展阶段
1960-1970年代被称为AI的"黄金时代"，专家系统开始兴起。然而，由于计算能力限制和过高期望，1974-1980年经历了第一次"AI寒冬"。1980年代专家系统商业化成功，但1987-1993年再次进入第二次寒冬期。

1997年，IBM的Deep Blue击败了国际象棋世界冠军Garry Kasparov，标志着AI在特定领域的突破。2011年，IBM Watson在智力竞赛节目Jeopardy!中击败人类冠军，展示了自然语言处理的进步。

## 现代AI革命
2012年，Geoffrey Hinton团队的AlexNet在ImageNet竞赛中取得突破性成果，深度学习重新兴起。2016年，Google DeepMind的AlphaGo击败围棋世界冠军李世石，展现了强化学习的威力。

2017年，Google发布了Transformer架构论文《Attention Is All You Need》，彻底改变了自然语言处理领域。2018年，OpenAI发布GPT-1，参数量1.17亿。2019年GPT-2参数增至15亿，2020年GPT-3达到1750亿参数，展现了惊人的语言生成能力。

## 商业应用现状
截至2023年，全球AI市场规模已达到1368亿美元，预计2030年将增长至1.8万亿美元，年复合增长率为36.8%。主要应用领域包括：

### 医疗健康
- Google Health的AI系统在糖尿病视网膜病变检测准确率达到90%以上
- IBM Watson for Oncology协助癌症治疗决策，在某些癌症类型的治疗建议准确率达到85%
- Moderna利用AI技术在不到一年时间内开发出COVID-19疫苗

### 自动驾驶
- Tesla的Full Self-Driving (FSD)系统已收集超过30亿英里的驾驶数据
- Waymo自动驾驶汽车在亚利桑那州凤凰城提供商业服务，累计行驶超过2000万英里
- 中国百度Apollo平台在北京、上海等城市开展自动驾驶测试

### 金融科技
- JPMorgan Chase的COIN系统每年可处理相当于36万小时律师工作量的法律文件
- Goldman Sachs使用机器学习算法进行高频交易，算法交易占其股票交易量的45%
- 蚂蚁金服的风控系统每秒可处理12万笔交易，欺诈识别准确率达99.9%

## 技术挑战与风险
尽管AI取得巨大进展，但仍面临诸多挑战：数据隐私问题、算法偏见、就业替代风险、技能差距等。2023年，欧盟通过了《人工智能法案》，成为全球首个全面的AI监管法律框架。

## 未来展望
专家预测，到2030年，AI将在以下领域实现重大突破：
1. 通用人工智能(AGI)的初步实现，某些AI系统可能通过图灵测试
2. 量子计算与AI结合，解决现有算法无法处理的复杂问题
3. 脑机接口技术成熟，实现人脑与AI的直接交互
4. AI科学家出现，能够独立进行科学研究和发现

投资方面，2023年全球AI初创企业获得投资总额达到251亿美元，其中生成式AI企业占比超过40%。中美两国在AI投资竞争激烈，美国占全球AI投资的45%，中国占30%。

## 结论
人工智能正在从实验室走向现实世界，其发展速度远超预期。然而，技术进步必须与伦理考量、监管框架和社会适应性相平衡。未来十年将是AI发展的关键期，其影响将深刻改变人类社会的方方面面。
"""

# 复杂查询问题 - 测试不同层次的理解和推理能力
COMPLEX_QUERIES = [
    {
        "id": "Q1",
        "question": "分析人工智能发展过程中的两次'寒冬'，比较它们的时间、原因和影响，并解释为什么2012年后AI能够重新兴起？",
        "difficulty": "高",
        "required_skills": ["时间序列分析", "因果关系推理", "比较分析"],
        "expected_facts": [
            "第一次AI寒冬：1974-1980年",
            "第二次AI寒冬：1987-1993年",
            "2012年AlexNet突破",
            "深度学习重新兴起的原因"
        ]
    },
    {
        "id": "Q2", 
        "question": "根据文档中的数据，计算并分析全球AI市场从2023年到2030年的增长趋势，并说明哪些商业应用领域展现出最强的技术实力？",
        "difficulty": "高",
        "required_skills": ["数值计算", "趋势分析", "性能比较"],
        "expected_facts": [
            "2023年市场规模：1368亿美元",
            "2030年预测：1.8万亿美元",
            "年复合增长率：36.8%",
            "各领域的具体性能数据"
        ]
    },
    {
        "id": "Q3",
        "question": "从技术演进角度，解释Transformer架构对现代AI发展的重要性，并分析GPT系列模型的参数规模增长对AI能力提升的影响。",
        "difficulty": "极高",
        "required_skills": ["技术因果关系", "参数规模分析", "技术影响评估"],
        "expected_facts": [
            "2017年Transformer论文",
            "GPT-1：1.17亿参数",
            "GPT-2：15亿参数", 
            "GPT-3：1750亿参数",
            "技术影响分析"
        ]
    }
]

@dataclass
class EvaluationMetrics:
    """评估指标"""
    accuracy: float  # 准确性 (0-1)
    relevance: float  # 相关性 (0-1)
    faithfulness: float  # 真实性 (0-1)
    recall: float  # 召回率 (0-1)
    completeness: float  # 完整性 (0-1)
    consistency: float  # 一致性 (0-1)
    citation_quality: float  # 引用质量 (0-1)
    response_time: float  # 响应时间 (秒)

@dataclass
class RAGTestResult:
    """单个RAG模式的测试结果"""
    rag_mode: str
    query_id: str
    response: str
    sources_count: int
    processing_time: float
    metrics: EvaluationMetrics
    raw_metadata: Dict[str, Any]

class RAGEvaluator:
    """RAG评估器"""
    
    def __init__(self):
        self.config = RAGConfig(chunk_size=800, overlap=100, top_k=5)
        self.results: List[RAGTestResult] = []
    
    def evaluate_response(self, query: Dict, response: str, sources: List, processing_time: float) -> EvaluationMetrics:
        """评估响应质量"""
        
        # 1. 准确性评估 - 检查期望事实是否被正确提及
        expected_facts = query["expected_facts"]
        found_facts = sum(1 for fact in expected_facts if any(keyword in response.lower() for keyword in fact.lower().split()[:3]))
        accuracy = found_facts / len(expected_facts)
        
        # 2. 相关性评估 - 响应与查询的相关程度
        query_keywords = set(query["question"].lower().split())
        response_keywords = set(response.lower().split())
        relevance = len(query_keywords.intersection(response_keywords)) / len(query_keywords)
        
        # 3. 真实性评估 - 响应是否基于提供的源文档
        source_texts = " ".join([source.get('text', '') for source in sources])
        response_words = response.lower().split()
        faithful_words = sum(1 for word in response_words[:50] if word in source_texts.lower())
        faithfulness = faithful_words / min(len(response_words), 50) if response_words else 0
        
        # 4. 召回率评估 - 是否找到了相关信息源
        recall = min(len(sources) / 3, 1.0)  # 期望至少3个源
        
        # 5. 完整性评估 - 响应长度和覆盖度
        completeness = min(len(response) / 500, 1.0)  # 期望至少500字符
        
        # 6. 一致性评估 - 简单检查是否有明显矛盾
        consistency = 0.9 if "但是" not in response and "然而" not in response else 0.7
        
        # 7. 引用质量评估 - 检查citation格式
        citation_count = response.count('[') + response.count('】')
        citation_quality = min(citation_count / max(len(sources), 1), 1.0)
        
        return EvaluationMetrics(
            accuracy=accuracy,
            relevance=relevance,
            faithfulness=faithfulness,
            recall=recall,
            completeness=completeness,
            consistency=consistency,
            citation_quality=citation_quality,
            response_time=processing_time
        )
    
    async def test_rag_service(self, rag_service, service_name: str, query: Dict) -> RAGTestResult:
        """测试单个RAG服务"""
        print(f"\n🔍 Testing {service_name} on {query['id']}...")
        
        try:
            # 处理文档
            start_time = time.time()
            
            doc_result = await rag_service.process_document(
                COMPLEX_TEST_DOCUMENT,
                user_id='eval_user',
                metadata={'source': 'ai_comprehensive_report'}
            )
            
            if not doc_result.success:
                print(f"❌ {service_name} document processing failed")
                return None
            
            # 执行查询
            query_result = await rag_service.query(
                query["question"],
                user_id='eval_user'
            )
            
            processing_time = time.time() - start_time
            
            if not query_result.success:
                print(f"❌ {service_name} query failed")
                return None
            
            # 评估结果
            metrics = self.evaluate_response(
                query, 
                query_result.content, 
                query_result.sources,
                processing_time
            )
            
            result = RAGTestResult(
                rag_mode=service_name,
                query_id=query["id"],
                response=query_result.content,
                sources_count=len(query_result.sources),
                processing_time=processing_time,
                metrics=metrics,
                raw_metadata=query_result.metadata
            )
            
            print(f"✅ {service_name} completed - Accuracy: {metrics.accuracy:.2f}, Sources: {len(query_result.sources)}")
            return result
            
        except Exception as e:
            print(f"❌ {service_name} failed: {e}")
            return None

# 这个函数已经在后面更完整地定义了，删除这个不完整的版本

def analyze_results(results: List[RAGTestResult]) -> Dict[str, Any]:
    """分析测试结果"""
    
    if not results:
        return {"error": "No results to analyze"}
    
    # 按RAG模式分组
    by_mode = {}
    for result in results:
        if result.rag_mode not in by_mode:
            by_mode[result.rag_mode] = []
        by_mode[result.rag_mode].append(result)
    
    # 计算每个模式的平均分数
    mode_scores = {}
    for mode, mode_results in by_mode.items():
        metrics_sum = {
            'accuracy': 0, 'relevance': 0, 'faithfulness': 0, 'recall': 0,
            'completeness': 0, 'consistency': 0, 'citation_quality': 0, 'response_time': 0
        }
        
        for result in mode_results:
            metrics_sum['accuracy'] += result.metrics.accuracy
            metrics_sum['relevance'] += result.metrics.relevance
            metrics_sum['faithfulness'] += result.metrics.faithfulness
            metrics_sum['recall'] += result.metrics.recall
            metrics_sum['completeness'] += result.metrics.completeness
            metrics_sum['consistency'] += result.metrics.consistency
            metrics_sum['citation_quality'] += result.metrics.citation_quality
            metrics_sum['response_time'] += result.metrics.response_time
        
        count = len(mode_results)
        mode_scores[mode] = {
            'accuracy': metrics_sum['accuracy'] / count,
            'relevance': metrics_sum['relevance'] / count,
            'faithfulness': metrics_sum['faithfulness'] / count,
            'recall': metrics_sum['recall'] / count,
            'completeness': metrics_sum['completeness'] / count,
            'consistency': metrics_sum['consistency'] / count,
            'citation_quality': metrics_sum['citation_quality'] / count,
            'response_time': metrics_sum['response_time'] / count,
            'test_count': count
        }
        
        # 计算综合评分 (加权平均)
        weights = {
            'accuracy': 0.25, 'relevance': 0.20, 'faithfulness': 0.20, 
            'recall': 0.15, 'completeness': 0.10, 'consistency': 0.05, 'citation_quality': 0.05
        }
        
        overall_score = sum(mode_scores[mode][metric] * weight for metric, weight in weights.items())
        mode_scores[mode]['overall_score'] = overall_score
    
    # 排名
    ranking = sorted(mode_scores.items(), key=lambda x: x[1]['overall_score'], reverse=True)
    
    return {
        'mode_scores': mode_scores,
        'ranking': ranking,
        'total_tests': len(results)
    }

def generate_evaluation_report(results: List[RAGTestResult]) -> str:
    """生成评估报告"""
    
    analysis = analyze_results(results)
    
    if 'error' in analysis:
        return f"❌ 评估失败: {analysis['error']}"
    
    report = []
    report.append("🏆 RAG模式综合评估报告")
    report.append("=" * 80)
    report.append(f"📊 总测试数: {analysis['total_tests']} (7个模式 × 3个查询)")
    report.append("")
    
    # 排行榜
    report.append("🥇 RAG模式排行榜 (按综合评分)")
    report.append("-" * 50)
    
    for i, (mode, scores) in enumerate(analysis['ranking']):
        rank_emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣"][i] if i < 7 else "🔢"
        report.append(f"{rank_emoji} {mode}: {scores['overall_score']:.3f}")
        report.append(f"   准确性:{scores['accuracy']:.2f} 相关性:{scores['relevance']:.2f} 真实性:{scores['faithfulness']:.2f}")
        report.append(f"   召回率:{scores['recall']:.2f} 完整性:{scores['completeness']:.2f} 引用质量:{scores['citation_quality']:.2f}")
        report.append(f"   平均响应时间:{scores['response_time']:.2f}秒")
        report.append("")
    
    # 详细分析
    report.append("📈 详细性能分析")
    report.append("-" * 50)
    
    # 各维度最强者
    best_in_category = {}
    for category in ['accuracy', 'relevance', 'faithfulness', 'recall', 'completeness', 'consistency', 'citation_quality']:
        best_mode = max(analysis['mode_scores'].items(), key=lambda x: x[1][category])
        best_in_category[category] = (best_mode[0], best_mode[1][category])
    
    category_names = {
        'accuracy': '准确性', 'relevance': '相关性', 'faithfulness': '真实性',
        'recall': '召回率', 'completeness': '完整性', 'consistency': '一致性', 'citation_quality': '引用质量'
    }
    
    for category, (mode, score) in best_in_category.items():
        report.append(f"🏅 {category_names[category]}最强: {mode} ({score:.3f})")
    
    report.append("")
    
    # 速度分析
    fastest_mode = min(analysis['mode_scores'].items(), key=lambda x: x[1]['response_time'])
    report.append(f"⚡ 最快响应: {fastest_mode[0]} ({fastest_mode[1]['response_time']:.2f}秒)")
    report.append("")
    
    # 结论
    winner = analysis['ranking'][0]
    report.append("🎯 评估结论")
    report.append("-" * 30)
    report.append(f"👑 综合实力最强: {winner[0]}")
    report.append(f"🔥 综合评分: {winner[1]['overall_score']:.3f}/1.000")
    
    if len(analysis['ranking']) > 1:
        runner_up = analysis['ranking'][1]
        score_diff = winner[1]['overall_score'] - runner_up[1]['overall_score']
        report.append(f"🥈 亚军: {runner_up[0]} (差距: {score_diff:.3f})")
    
    return "\n".join(report)

async def run_comprehensive_evaluation():
    """运行综合评估"""
    print("🚀 RAG COMPREHENSIVE EVALUATION - BATTLE OF THE MODES!")
    print("=" * 80)
    
    evaluator = RAGEvaluator()
    
    # RAG服务配置
    rag_services = [
        ("Simple RAG", "tools.services.data_analytics_service.services.digital_service.patterns.simple_rag_service", "SimpleRAGService"),
        ("RAPTOR RAG", "tools.services.data_analytics_service.services.digital_service.patterns.raptor_rag_service", "RAPTORRAGService"),
        ("Self RAG", "tools.services.data_analytics_service.services.digital_service.patterns.self_rag_service", "SelfRAGService"),
        ("CRAG RAG", "tools.services.data_analytics_service.services.digital_service.patterns.crag_rag_service", "CRAGRAGService"),
        ("Plan-RAG", "tools.services.data_analytics_service.services.digital_service.patterns.plan_rag_service", "PlanRAGRAGService"),
        ("HM-RAG", "tools.services.data_analytics_service.services.digital_service.patterns.hm_rag_service", "HMRAGRAGService"),
        ("Graph RAG", "tools.services.data_analytics_service.services.digital_service.patterns.graph_rag_service", "GraphRAGService")
    ]
    
    all_results = []
    
    for query in COMPLEX_QUERIES:
        print(f"\n📋 QUERY {query['id']}: {query['question'][:80]}...")
        print(f"   Difficulty: {query['difficulty']}, Skills: {', '.join(query['required_skills'])}")
        print("-" * 80)
        
        for service_name, module, class_name in rag_services:
            try:
                # 动态导入RAG服务
                exec(f"from {module} import {class_name}")
                service = eval(f"{class_name}(evaluator.config)")
                
                # 运行测试
                result = await evaluator.test_rag_service(service, service_name, query)
                if result:
                    all_results.append(result)
                    
            except Exception as e:
                print(f"❌ {service_name} initialization failed: {e}")
    
    # 生成报告
    report = generate_evaluation_report(all_results)
    print("\n" + report)
    
    return all_results, report

if __name__ == "__main__":
    results, report = asyncio.run(run_comprehensive_evaluation())
    
    # 保存详细结果
    with open('/Users/xenodennis/Documents/Fun/isA_MCP/rag_evaluation_results.json', 'w', encoding='utf-8') as f:
        json.dump([{
            'rag_mode': r.rag_mode,
            'query_id': r.query_id,
            'response_preview': r.response[:200],
            'sources_count': r.sources_count,
            'processing_time': r.processing_time,
            'metrics': {
                'accuracy': r.metrics.accuracy,
                'relevance': r.metrics.relevance,
                'faithfulness': r.metrics.faithfulness,
                'recall': r.metrics.recall,
                'completeness': r.metrics.completeness,
                'consistency': r.metrics.consistency,
                'citation_quality': r.metrics.citation_quality,
                'response_time': r.metrics.response_time
            }
        } for r in results], f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 详细结果已保存到: rag_evaluation_results.json")
    print(f"📊 总共完成 {len(results)} 项测试")