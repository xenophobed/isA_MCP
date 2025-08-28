"""
Data Explorer Service - Trial & Error探索工具
为data_service提供智能数据探索能力，通过试验和错误更好地理解metadata

Integration with existing services:
- Enhances semantic_enricher.py with exploration capabilities
- Provides hypothesis-driven analysis for better metadata understanding
- Supports adaptive learning for improved semantic analysis

Features:
- 智能数据探索策略
- 试验假设生成和验证
- 自适应探索路径
- 探索结果学习和优化
- 与semantic_enricher集成
"""

import json
import logging
import asyncio
import random
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class ExplorationStrategy(Enum):
    """探索策略"""
    SYSTEMATIC = "systematic"
    RANDOM = "random"
    HYPOTHESIS_DRIVEN = "hypothesis_driven"
    PATTERN_SEEKING = "pattern_seeking"
    CURIOSITY_DRIVEN = "curiosity_driven"


class ExplorationResult(Enum):
    """探索结果类型"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    INCONCLUSIVE = "inconclusive"


@dataclass
class Hypothesis:
    """探索假设"""
    id: str
    description: str
    assumption: str
    expected_outcome: str
    confidence: float
    priority: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tested: bool = False
    result: Optional[ExplorationResult] = None
    evidence: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)


@dataclass
class ExplorationSession:
    """探索会话"""
    session_id: str
    metadata: Dict[str, Any]
    strategy: ExplorationStrategy
    hypotheses: List[Hypothesis] = field(default_factory=list)
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    discoveries: List[Dict[str, Any]] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    exploration_depth: int = 0
    max_depth: int = 5
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())


class DataExplorer:
    """数据探索服务 - 为semantic_enricher提供探索增强"""
    
    def __init__(self, max_exploration_time: float = 60.0, max_actions: int = 20):
        self.max_exploration_time = max_exploration_time
        self.max_actions = max_actions
        
        # 探索知识库
        self.pattern_library = self._initialize_pattern_library()
        self.hypothesis_templates = self._initialize_hypothesis_templates()
        self.exploration_history = []
        
        # 学习机制
        self.success_patterns = defaultdict(int)
        self.failure_patterns = defaultdict(int)
        
        logger.info("Data Explorer service initialized")
    
    async def enhance_metadata_understanding(self, metadata: Dict[str, Any],
                                           focus_areas: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        增强元数据理解 - 主要接口方法
        
        Args:
            metadata: 原始元数据
            focus_areas: 重点关注的领域
            
        Returns:
            增强后的元数据理解
        """
        logger.info("Starting enhanced metadata understanding")
        
        try:
            # 快速探索模式 - 适合production环境
            session = await self._quick_exploration(metadata, focus_areas)
            
            # 提取探索增强的洞察
            enhanced_insights = self._extract_exploration_insights(session)
            
            # 生成探索建议
            exploration_suggestions = self._generate_exploration_suggestions(session)
            
            # 返回增强的理解
            return {
                'original_metadata': metadata,
                'exploration_insights': enhanced_insights,
                'exploration_suggestions': exploration_suggestions,
                'confidence_improvements': session.confidence_scores,
                'discovered_patterns': [d for d in session.discoveries if d.get('confidence', 0) > 0.7],
                'exploration_summary': {
                    'session_id': session.session_id,
                    'strategy': session.strategy.value,
                    'hypotheses_tested': len([h for h in session.hypotheses if h.tested]),
                    'discoveries_count': len(session.discoveries),
                    'insights_count': len(session.insights)
                }
            }
            
        except Exception as e:
            logger.error(f"Enhanced metadata understanding failed: {e}")
            return {
                'original_metadata': metadata,
                'error': str(e),
                'fallback_insights': self._generate_fallback_insights(metadata)
            }
    
    async def _quick_exploration(self, metadata: Dict[str, Any], 
                               focus_areas: Optional[List[str]]) -> ExplorationSession:
        """快速探索模式 - 适合production使用"""
        session = ExplorationSession(
            session_id=f"quick_explore_{int(datetime.now().timestamp())}",
            metadata=metadata,
            strategy=ExplorationStrategy.HYPOTHESIS_DRIVEN,
            max_depth=3  # 限制深度以提高性能
        )
        
        # Phase 1: 生成关键假设
        key_hypotheses = self._generate_key_hypotheses(metadata, focus_areas)
        session.hypotheses = key_hypotheses[:5]  # 限制假设数量
        
        # Phase 2: 快速验证假设
        for hypothesis in session.hypotheses:
            if len(session.actions_taken) >= 10:  # 限制行动数量
                break
            await self._quick_test_hypothesis(session, hypothesis)
        
        # Phase 3: 快速模式识别
        await self._quick_pattern_recognition(session)
        
        return session
    
    def _generate_key_hypotheses(self, metadata: Dict[str, Any], 
                               focus_areas: Optional[List[str]]) -> List[Hypothesis]:
        """生成关键假设"""
        hypotheses = []
        
        tables = metadata.get('tables', [])
        columns = metadata.get('columns', [])
        
        # 假设1: 数据质量假设
        quality_hypothesis = self._create_data_quality_hypothesis(columns)
        if quality_hypothesis:
            hypotheses.append(quality_hypothesis)
        
        # 假设2: 业务实体假设
        entity_hypothesis = self._create_business_entity_hypothesis(tables, columns)
        if entity_hypothesis:
            hypotheses.append(entity_hypothesis)
        
        # 假设3: 关系模式假设
        if len(tables) > 1:
            relationship_hypothesis = self._create_relationship_hypothesis(tables, columns)
            if relationship_hypothesis:
                hypotheses.append(relationship_hypothesis)
        
        # 假设4: 时间模式假设
        temporal_hypothesis = self._create_temporal_hypothesis(columns)
        if temporal_hypothesis:
            hypotheses.append(temporal_hypothesis)
        
        # 基于focus_areas的特定假设
        if focus_areas:
            for area in focus_areas:
                focused_hypothesis = self._create_focused_hypothesis(area, metadata)
                if focused_hypothesis:
                    hypotheses.append(focused_hypothesis)
        
        return hypotheses
    
    def _create_data_quality_hypothesis(self, columns: List[Dict[str, Any]]) -> Optional[Hypothesis]:
        """创建数据质量假设"""
        if not columns:
            return None
        
        # 分析null值分布
        null_columns = [col for col in columns if col.get('null_percentage', 0) > 10]
        
        if null_columns:
            return Hypothesis(
                id=f"quality_{int(datetime.now().timestamp())}",
                description=f"Data quality issues detected in {len(null_columns)} columns",
                assumption="High null percentages indicate data collection or integration issues",
                expected_outcome="Identify data quality patterns and root causes",
                confidence=0.8,
                priority=3
            )
        return None
    
    def _create_business_entity_hypothesis(self, tables: List[Dict[str, Any]], 
                                         columns: List[Dict[str, Any]]) -> Optional[Hypothesis]:
        """创建业务实体假设"""
        if not tables:
            return None
        
        # 分析表名中的业务关键词
        business_keywords = ['customer', 'user', 'product', 'order', 'transaction', 'invoice', 'employee']
        business_tables = []
        
        for table in tables:
            table_name = table['table_name'].lower()
            for keyword in business_keywords:
                if keyword in table_name:
                    business_tables.append((table['table_name'], keyword))
                    break
        
        if business_tables:
            entities = [f"{table} ({entity})" for table, entity in business_tables]
            return Hypothesis(
                id=f"business_{int(datetime.now().timestamp())}",
                description=f"Business entities detected: {', '.join(entities)}",
                assumption="Table names reflect business domain entities",
                expected_outcome="Confirm business entity patterns and relationships",
                confidence=0.7,
                priority=2
            )
        return None
    
    def _create_relationship_hypothesis(self, tables: List[Dict[str, Any]], 
                                      columns: List[Dict[str, Any]]) -> Optional[Hypothesis]:
        """创建关系假设"""
        # 分析可能的外键关系
        id_columns = [col for col in columns if 'id' in col['column_name'].lower()]
        
        if len(id_columns) > len(tables):  # 有外键的可能
            return Hypothesis(
                id=f"relationship_{int(datetime.now().timestamp())}",
                description=f"Potential foreign key relationships detected",
                assumption="Multiple ID columns suggest relational data model",
                expected_outcome="Identify table relationships and foreign keys",
                confidence=0.6,
                priority=2
            )
        return None
    
    def _create_temporal_hypothesis(self, columns: List[Dict[str, Any]]) -> Optional[Hypothesis]:
        """创建时间模式假设"""
        temporal_keywords = ['date', 'time', 'timestamp', 'created', 'updated', 'modified']
        temporal_columns = []
        
        for col in columns:
            col_name = col['column_name'].lower()
            if any(keyword in col_name for keyword in temporal_keywords):
                temporal_columns.append(col['column_name'])
        
        if temporal_columns:
            return Hypothesis(
                id=f"temporal_{int(datetime.now().timestamp())}",
                description=f"Temporal data patterns in {len(temporal_columns)} columns",
                assumption="Temporal columns indicate time-series or audit trail data",
                expected_outcome="Understand temporal data patterns and usage",
                confidence=0.8,
                priority=2
            )
        return None
    
    def _create_focused_hypothesis(self, focus_area: str, metadata: Dict[str, Any]) -> Optional[Hypothesis]:
        """基于focus_area创建假设"""
        if focus_area == 'ecommerce':
            return self._create_ecommerce_hypothesis(metadata)
        elif focus_area == 'finance':
            return self._create_finance_hypothesis(metadata)
        elif focus_area == 'analytics':
            return self._create_analytics_hypothesis(metadata)
        return None
    
    def _create_ecommerce_hypothesis(self, metadata: Dict[str, Any]) -> Optional[Hypothesis]:
        """创建电商相关假设"""
        tables = metadata.get('tables', [])
        ecommerce_indicators = ['product', 'order', 'cart', 'customer', 'inventory', 'price']
        
        matches = []
        for table in tables:
            table_name = table['table_name'].lower()
            for indicator in ecommerce_indicators:
                if indicator in table_name:
                    matches.append(f"{table['table_name']} -> {indicator}")
        
        if matches:
            return Hypothesis(
                id=f"ecommerce_{int(datetime.now().timestamp())}",
                description="E-commerce domain patterns detected",
                assumption="Table structure suggests e-commerce business model",
                expected_outcome="Identify e-commerce entities and workflows",
                confidence=0.7,
                priority=3
            )
        return None
    
    def _create_finance_hypothesis(self, metadata: Dict[str, Any]) -> Optional[Hypothesis]:
        """创建金融相关假设"""
        columns = metadata.get('columns', [])
        finance_indicators = ['amount', 'balance', 'transaction', 'payment', 'account', 'currency']
        
        matches = []
        for col in columns:
            col_name = col['column_name'].lower()
            for indicator in finance_indicators:
                if indicator in col_name:
                    matches.append(f"{col['column_name']} -> {indicator}")
        
        if matches:
            return Hypothesis(
                id=f"finance_{int(datetime.now().timestamp())}",
                description="Financial domain patterns detected",
                assumption="Column names suggest financial data model",
                expected_outcome="Identify financial entities and transaction patterns",
                confidence=0.7,
                priority=3
            )
        return None
    
    def _create_analytics_hypothesis(self, metadata: Dict[str, Any]) -> Optional[Hypothesis]:
        """创建分析相关假设"""
        columns = metadata.get('columns', [])
        tables = metadata.get('tables', [])
        
        # 检查是否有分析型数据特征
        numeric_columns = [col for col in columns if col.get('data_type') in ['INTEGER', 'FLOAT', 'DECIMAL', 'NUMERIC']]
        large_tables = [table for table in tables if table.get('record_count', 0) > 10000]
        
        if len(numeric_columns) > len(columns) * 0.3 and large_tables:
            return Hypothesis(
                id=f"analytics_{int(datetime.now().timestamp())}",
                description="Analytics-oriented data structure detected",
                assumption="High ratio of numeric columns and large tables suggest analytical workload",
                expected_outcome="Identify analytical patterns and aggregation opportunities",
                confidence=0.6,
                priority=2
            )
        return None
    
    async def _quick_test_hypothesis(self, session: ExplorationSession, hypothesis: Hypothesis):
        """快速测试假设"""
        try:
            # 根据假设类型进行快速验证
            if "quality" in hypothesis.id:
                result = self._test_quality_hypothesis_quick(session.metadata, hypothesis)
            elif "business" in hypothesis.id:
                result = self._test_business_hypothesis_quick(session.metadata, hypothesis)
            elif "relationship" in hypothesis.id:
                result = self._test_relationship_hypothesis_quick(session.metadata, hypothesis)
            elif "temporal" in hypothesis.id:
                result = self._test_temporal_hypothesis_quick(session.metadata, hypothesis)
            else:
                result = self._test_general_hypothesis_quick(session.metadata, hypothesis)
            
            # 更新假设结果
            hypothesis.tested = True
            hypothesis.result = result['result']
            hypothesis.evidence = result['evidence']
            hypothesis.insights = result['insights']
            
            # 记录行动
            session.actions_taken.append({
                'action': 'quick_test_hypothesis',
                'hypothesis_id': hypothesis.id,
                'result': result['result'].value,
                'timestamp': datetime.now().isoformat()
            })
            
            # 如果成功，添加到发现
            if result['result'] == ExplorationResult.SUCCESS:
                session.discoveries.append({
                    'type': 'hypothesis_validation',
                    'hypothesis': hypothesis.description,
                    'evidence': result['evidence'],
                    'confidence': hypothesis.confidence
                })
            
        except Exception as e:
            logger.warning(f"Quick hypothesis test failed for {hypothesis.id}: {e}")
            hypothesis.result = ExplorationResult.FAILURE
            hypothesis.evidence = [f"Test failed: {str(e)}"]
    
    def _test_quality_hypothesis_quick(self, metadata: Dict[str, Any], hypothesis: Hypothesis) -> Dict[str, Any]:
        """快速测试数据质量假设"""
        evidence = []
        insights = []
        
        columns = metadata.get('columns', [])
        
        # 快速分析null值分布
        null_analysis = []
        for col in columns:
            null_pct = col.get('null_percentage', 0)
            if null_pct > 0:
                null_analysis.append((col['column_name'], null_pct))
        
        if null_analysis:
            sorted_nulls = sorted(null_analysis, key=lambda x: x[1], reverse=True)
            evidence.append(f"Top null columns: {sorted_nulls[:3]}")
            
            if sorted_nulls[0][1] > 50:
                insights.append("High null percentage suggests data integration issues")
            
            return {
                'result': ExplorationResult.SUCCESS,
                'evidence': evidence,
                'insights': insights
            }
        
        return {
            'result': ExplorationResult.INCONCLUSIVE,
            'evidence': ["No significant null patterns found"],
            'insights': []
        }
    
    def _test_business_hypothesis_quick(self, metadata: Dict[str, Any], hypothesis: Hypothesis) -> Dict[str, Any]:
        """快速测试业务假设"""
        evidence = []
        insights = []
        
        tables = metadata.get('tables', [])
        columns = metadata.get('columns', [])
        
        # 快速业务实体分析
        business_patterns = {}
        for table in tables:
            table_name = table['table_name'].lower()
            if 'customer' in table_name or 'user' in table_name:
                business_patterns['customer_entity'] = table['table_name']
            elif 'product' in table_name or 'item' in table_name:
                business_patterns['product_entity'] = table['table_name']
            elif 'order' in table_name or 'transaction' in table_name:
                business_patterns['transaction_entity'] = table['table_name']
        
        if business_patterns:
            evidence.append(f"Business entities: {list(business_patterns.keys())}")
            insights.append("Clear business domain structure detected")
            
            return {
                'result': ExplorationResult.SUCCESS,
                'evidence': evidence,
                'insights': insights
            }
        
        return {
            'result': ExplorationResult.PARTIAL,
            'evidence': ["Some business patterns detected but unclear"],
            'insights': []
        }
    
    def _test_relationship_hypothesis_quick(self, metadata: Dict[str, Any], hypothesis: Hypothesis) -> Dict[str, Any]:
        """快速测试关系假设"""
        evidence = []
        insights = []
        
        tables = metadata.get('tables', [])
        columns = metadata.get('columns', [])
        
        # 快速外键分析
        table_names = [t['table_name'].lower() for t in tables]
        potential_fks = []
        
        for col in columns:
            col_name = col['column_name'].lower()
            if col_name.endswith('_id') and col_name != 'id':
                fk_table = col_name[:-3]  # 移除'_id'
                if fk_table in table_names:
                    potential_fks.append(f"{col['table_name']}.{col['column_name']} -> {fk_table}")
        
        if potential_fks:
            evidence.append(f"Potential foreign keys: {potential_fks[:3]}")
            insights.append("Relational data model with foreign key relationships")
            
            return {
                'result': ExplorationResult.SUCCESS,
                'evidence': evidence,
                'insights': insights
            }
        
        return {
            'result': ExplorationResult.INCONCLUSIVE,
            'evidence': ["No clear foreign key patterns found"],
            'insights': []
        }
    
    def _test_temporal_hypothesis_quick(self, metadata: Dict[str, Any], hypothesis: Hypothesis) -> Dict[str, Any]:
        """快速测试时间假设"""
        evidence = []
        insights = []
        
        columns = metadata.get('columns', [])
        
        # 快速时间列分析
        temporal_patterns = []
        for col in columns:
            col_name = col['column_name'].lower()
            if 'created' in col_name:
                temporal_patterns.append(f"{col['column_name']} (creation tracking)")
            elif 'updated' in col_name or 'modified' in col_name:
                temporal_patterns.append(f"{col['column_name']} (modification tracking)")
            elif 'date' in col_name or 'time' in col_name:
                temporal_patterns.append(f"{col['column_name']} (temporal data)")
        
        if temporal_patterns:
            evidence.append(f"Temporal patterns: {temporal_patterns[:3]}")
            
            if any('created' in pattern for pattern in temporal_patterns):
                insights.append("Audit trail pattern detected - good for data lineage")
            
            return {
                'result': ExplorationResult.SUCCESS,
                'evidence': evidence,
                'insights': insights
            }
        
        return {
            'result': ExplorationResult.INCONCLUSIVE,
            'evidence': ["No clear temporal patterns found"],
            'insights': []
        }
    
    def _test_general_hypothesis_quick(self, metadata: Dict[str, Any], hypothesis: Hypothesis) -> Dict[str, Any]:
        """快速测试通用假设"""
        return {
            'result': ExplorationResult.PARTIAL,
            'evidence': ["General hypothesis partially validated"],
            'insights': ["Quick analysis completed"]
        }
    
    async def _quick_pattern_recognition(self, session: ExplorationSession):
        """快速模式识别"""
        metadata = session.metadata
        
        # 识别命名模式
        naming_patterns = self._analyze_naming_patterns_quick(metadata)
        if naming_patterns:
            session.discoveries.append({
                'type': 'naming_patterns',
                'patterns': naming_patterns,
                'confidence': 0.7
            })
        
        # 识别数据类型模式
        type_patterns = self._analyze_type_patterns_quick(metadata)
        if type_patterns:
            session.discoveries.append({
                'type': 'data_type_patterns',
                'patterns': type_patterns,
                'confidence': 0.8
            })
    
    def _analyze_naming_patterns_quick(self, metadata: Dict[str, Any]) -> List[str]:
        """快速分析命名模式"""
        patterns = []
        
        columns = metadata.get('columns', [])
        
        # 检查ID命名一致性
        id_columns = [col['column_name'] for col in columns if 'id' in col['column_name'].lower()]
        if len(id_columns) > 3:
            consistent_suffix = all(name.endswith('_id') or name == 'id' for name in id_columns)
            if consistent_suffix:
                patterns.append("Consistent ID naming convention")
        
        # 检查时间字段命名
        time_columns = [col['column_name'] for col in columns if any(kw in col['column_name'].lower() for kw in ['date', 'time', 'created', 'updated'])]
        if len(time_columns) > 2:
            patterns.append("Consistent temporal field naming")
        
        return patterns
    
    def _analyze_type_patterns_quick(self, metadata: Dict[str, Any]) -> List[str]:
        """快速分析数据类型模式"""
        patterns = []
        
        columns = metadata.get('columns', [])
        if not columns:
            return patterns
        
        # 分析数据类型分布
        type_counts = Counter(col.get('data_type', 'unknown') for col in columns)
        total_columns = len(columns)
        
        for data_type, count in type_counts.most_common(3):
            percentage = (count / total_columns) * 100
            if percentage > 30:
                patterns.append(f"High proportion of {data_type} columns ({percentage:.1f}%)")
        
        return patterns
    
    def _extract_exploration_insights(self, session: ExplorationSession) -> List[str]:
        """提取探索洞察"""
        insights = []
        
        # 基于成功假设的洞察
        successful_hypotheses = [h for h in session.hypotheses if h.result == ExplorationResult.SUCCESS]
        
        if len(successful_hypotheses) > len(session.hypotheses) * 0.7:
            insights.append("High hypothesis validation rate indicates well-structured data")
        
        # 基于发现的洞察
        discovery_types = [d.get('type') for d in session.discoveries]
        
        if 'business_entity' in str(discovery_types):
            insights.append("Clear business domain patterns suitable for domain-driven analysis")
        
        if 'temporal_patterns' in str(discovery_types):
            insights.append("Temporal data patterns enable time-series analysis")
        
        if 'relationship' in str(discovery_types):
            insights.append("Relational structure supports complex queries and joins")
        
        # 添加具体的洞察
        for hypothesis in successful_hypotheses:
            insights.extend(hypothesis.insights)
        
        return list(set(insights))  # 去重
    
    def _generate_exploration_suggestions(self, session: ExplorationSession) -> List[str]:
        """生成探索建议"""
        suggestions = []
        
        # 基于失败假设的建议
        failed_hypotheses = [h for h in session.hypotheses if h.result == ExplorationResult.FAILURE]
        
        if len(failed_hypotheses) > len(session.hypotheses) * 0.5:
            suggestions.append("Consider additional metadata enrichment for better analysis")
        
        # 基于探索深度的建议
        if session.exploration_depth < session.max_depth:
            suggestions.append("Deeper exploration might reveal additional patterns")
        
        # 基于发现类型的建议
        discovery_types = [d.get('type') for d in session.discoveries]
        
        if 'data_type_patterns' not in discovery_types:
            suggestions.append("Analyze data type patterns for better schema understanding")
        
        if 'naming_patterns' not in discovery_types:
            suggestions.append("Investigate naming conventions for consistency")
        
        return suggestions
    
    def _generate_fallback_insights(self, metadata: Dict[str, Any]) -> List[str]:
        """生成回退洞察"""
        insights = []
        
        tables = metadata.get('tables', [])
        columns = metadata.get('columns', [])
        
        insights.append(f"Basic structure: {len(tables)} tables, {len(columns)} columns")
        
        if tables:
            avg_columns = len(columns) / len(tables)
            insights.append(f"Average {avg_columns:.1f} columns per table")
        
        return insights
    
    def _initialize_pattern_library(self) -> Dict[str, List[str]]:
        """初始化模式库"""
        return {
            'naming_patterns': ['id_suffix', 'name_field', 'date_prefix', 'status_field'],
            'relationship_patterns': ['foreign_key', 'junction_table', 'hierarchy'],
            'business_patterns': ['customer_entity', 'product_catalog', 'order_process'],
            'data_quality_patterns': ['null_clustering', 'value_distribution']
        }
    
    def _initialize_hypothesis_templates(self) -> List[Dict[str, Any]]:
        """初始化假设模板"""
        return [
            {
                'category': 'data_quality',
                'description': 'Data has quality issues',
                'assumption': 'High null percentages indicate problems',
                'expected_outcome': 'Identify quality issues',
                'base_confidence': 0.6,
                'priority': 2
            },
            {
                'category': 'business_logic',
                'description': 'Data reflects business processes',
                'assumption': 'Names indicate business domain',
                'expected_outcome': 'Identify business entities',
                'base_confidence': 0.7,
                'priority': 3
            }
        ]


# 便利函数
async def explore_and_enhance_metadata(metadata: Dict[str, Any], 
                                     focus_areas: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    便利函数：探索并增强元数据理解
    
    Args:
        metadata: 原始元数据
        focus_areas: 重点关注的领域
        
    Returns:
        增强后的元数据理解
    """
    explorer = DataExplorer(max_exploration_time=30.0, max_actions=15)  # 适合production的参数
    return await explorer.enhance_metadata_understanding(metadata, focus_areas)


# 与semantic_enricher集成的便利函数
def integrate_with_semantic_enricher(semantic_metadata: Dict[str, Any], 
                                   exploration_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    将探索结果集成到semantic_enricher的输出中
    
    Args:
        semantic_metadata: semantic_enricher的输出
        exploration_results: data_explorer的输出
        
    Returns:
        集成后的增强元数据
    """
    # 合并洞察
    combined_insights = []
    
    # 添加语义分析的洞察
    if 'insights' in semantic_metadata:
        combined_insights.extend(semantic_metadata['insights'])
    
    # 添加探索分析的洞察
    if 'exploration_insights' in exploration_results:
        combined_insights.extend(exploration_results['exploration_insights'])
    
    # 合并置信度分数
    combined_confidence = {}
    if 'confidence_scores' in semantic_metadata:
        combined_confidence.update(semantic_metadata['confidence_scores'])
    
    if 'confidence_improvements' in exploration_results:
        for key, value in exploration_results['confidence_improvements'].items():
            combined_confidence[f"exploration_{key}"] = value
    
    # 返回增强的结果
    enhanced_result = semantic_metadata.copy()
    enhanced_result.update({
        'enhanced_insights': combined_insights,
        'combined_confidence_scores': combined_confidence,
        'exploration_discoveries': exploration_results.get('discovered_patterns', []),
        'exploration_suggestions': exploration_results.get('exploration_suggestions', []),
        'exploration_summary': exploration_results.get('exploration_summary', {})
    })
    
    return enhanced_result