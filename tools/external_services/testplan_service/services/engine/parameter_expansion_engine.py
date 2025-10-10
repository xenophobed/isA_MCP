#!/usr/bin/env python3
"""
Parameter Expansion Engine for 3GPP Test Plans
基于数学优化方法的参数展开引擎

实现三种优化策略：
1. 正交数组（Orthogonal Arrays）
2. 成对测试（Pairwise Testing）  
3. 约束满足问题（CSP）求解
"""

import itertools
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """优化策略"""
    FULL_FACTORIAL = "full_factorial"  # 全排列
    ORTHOGONAL_ARRAY = "orthogonal_array"  # 正交数组
    PAIRWISE = "pairwise"  # 成对测试
    CSP = "csp"  # 约束满足
    TEMPLATE = "template"  # 基于模板


@dataclass
class ParameterDimension:
    """参数维度定义"""
    name: str  # 参数名称 (band, bandwidth, temp, etc.)
    values: List[Any]  # 可能的值
    mandatory: bool = True  # 是否必须测试
    constraints: List[str] = field(default_factory=list)  # 约束条件
    
    @property
    def level_count(self) -> int:
        """参数水平数"""
        return len(self.values)


@dataclass
class TestParameterSpace:
    """测试参数空间定义"""
    test_id: str
    test_type: str
    dimensions: List[ParameterDimension]
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    certification_requirements: Dict[str, Any] = field(default_factory=dict)
    
    def get_full_space_size(self) -> int:
        """计算全排列空间大小"""
        size = 1
        for dim in self.dimensions:
            size *= dim.level_count
        return size


@dataclass 
class TestInstance:
    """展开后的测试实例"""
    test_id: str
    parameters: Dict[str, Any]  # 参数组合
    priority: float = 1.0  # 优先级
    coverage_score: float = 0.0  # 覆盖分数
    risk_score: float = 0.0  # 风险分数
    
    def to_dict(self) -> Dict:
        return {
            'test_id': self.test_id,
            **self.parameters,
            'priority': self.priority,
            'coverage_score': self.coverage_score,
            'risk_score': self.risk_score
        }


class ParameterExpansionEngine:
    """参数展开引擎"""
    
    def __init__(self, spec_path: Path, strategy: OptimizationStrategy = OptimizationStrategy.PAIRWISE):
        """
        初始化展开引擎
        
        Args:
            spec_path: 规范文档路径（-1文档）
            strategy: 优化策略
        """
        self.spec_path = spec_path
        self.strategy = strategy
        self.parameter_tables = {}  # 缓存的参数表
        self.test_spaces = {}  # 测试参数空间
        
    def extract_parameter_space(self, test_id: str) -> Optional[TestParameterSpace]:
        """
        从-1文档提取测试用例的参数空间
        
        Args:
            test_id: 测试用例ID (e.g., "6.2.2")
        """
        # 使用ParameterTableExtractor提取参数表
        from .parameter_table_extractor import ParameterTableExtractor
        
        extractor = ParameterTableExtractor(self.spec_path)
        params = extractor.get_test_parameters(test_id)
        
        if not params:
            logger.warning(f"No parameter table found for test {test_id}")
            return None
            
        # 构建参数维度
        dimensions = []
        
        # 1. 频段维度（从PICS获取）
        if 'Band' in params or 'Bands' in params:
            band_values = params.get('Band', params.get('Bands', []))
            dimensions.append(ParameterDimension(
                name='band',
                values=band_values,
                mandatory=True
            ))
        
        # 2. 带宽维度
        if 'Channel bandwidth' in params or 'Bandwidth' in params:
            bw_values = params.get('Channel bandwidth', params.get('Bandwidth', []))
            dimensions.append(ParameterDimension(
                name='bandwidth',
                values=bw_values,
                mandatory=True
            ))
        
        # 3. 频率点维度
        if 'Test frequency' in params or 'Frequency range' in params:
            freq_values = params.get('Test frequency', params.get('Frequency range', ['Low', 'Mid', 'High']))
            dimensions.append(ParameterDimension(
                name='frequency',
                values=freq_values,
                mandatory=True
            ))
        
        # 4. 温度维度
        temp_values = params.get('Temperature', ['Normal', 'Low extreme', 'High extreme'])
        dimensions.append(ParameterDimension(
            name='temperature',
            values=temp_values,
            mandatory=False  # 可优化
        ))
        
        # 5. 电压维度
        volt_values = params.get('Voltage', ['Nominal', 'Low', 'High'])
        dimensions.append(ParameterDimension(
            name='voltage',
            values=volt_values,
            mandatory=False  # 可优化
        ))
        
        # 6. 其他维度（调制方式、MIMO配置等）
        if 'Modulation' in params:
            dimensions.append(ParameterDimension(
                name='modulation',
                values=params['Modulation'],
                mandatory=True
            ))
        
        if 'MIMO configuration' in params:
            dimensions.append(ParameterDimension(
                name='mimo',
                values=params['MIMO configuration'],
                mandatory=True
            ))
        
        # 构建参数空间
        test_space = TestParameterSpace(
            test_id=test_id,
            test_type=self._identify_test_type(test_id),
            dimensions=dimensions
        )
        
        # 添加约束
        test_space.constraints = self._extract_constraints(test_id, params)
        
        return test_space
    
    def expand_test_cases(self, test_ids: List[str], pics_capabilities: Dict) -> List[TestInstance]:
        """
        展开测试用例为测试实例
        
        Args:
            test_ids: 测试用例ID列表
            pics_capabilities: PICS能力字典
        
        Returns:
            展开后的测试实例列表
        """
        all_instances = []
        
        for test_id in test_ids:
            logger.info(f"Expanding test case: {test_id}")
            
            # 提取参数空间
            test_space = self.extract_parameter_space(test_id)
            if not test_space:
                continue
            
            # 过滤支持的参数值
            test_space = self._filter_by_pics(test_space, pics_capabilities)
            
            # 根据策略生成组合
            if self.strategy == OptimizationStrategy.FULL_FACTORIAL:
                instances = self._expand_full_factorial(test_space)
            elif self.strategy == OptimizationStrategy.ORTHOGONAL_ARRAY:
                instances = self._expand_orthogonal_array(test_space)
            elif self.strategy == OptimizationStrategy.PAIRWISE:
                instances = self._expand_pairwise(test_space)
            elif self.strategy == OptimizationStrategy.CSP:
                instances = self._expand_csp(test_space)
            else:  # TEMPLATE
                instances = self._expand_template(test_space, pics_capabilities)
            
            # 应用约束过滤
            instances = self._apply_constraints(instances, test_space.constraints)
            
            # 计算优先级和分数
            instances = self._calculate_scores(instances, test_space)
            
            all_instances.extend(instances)
            
            logger.info(f"  Generated {len(instances)} instances for test {test_id}")
        
        return all_instances
    
    def _expand_full_factorial(self, test_space: TestParameterSpace) -> List[TestInstance]:
        """全排列展开"""
        instances = []
        
        # 获取所有维度的值
        dim_values = [dim.values for dim in test_space.dimensions]
        
        # 生成笛卡尔积
        for combo in itertools.product(*dim_values):
            params = {}
            for i, dim in enumerate(test_space.dimensions):
                params[dim.name] = combo[i]
            
            instance = TestInstance(
                test_id=test_space.test_id,
                parameters=params
            )
            instances.append(instance)
        
        return instances
    
    def _expand_pairwise(self, test_space: TestParameterSpace) -> List[TestInstance]:
        """成对测试展开（使用简化的IPOG算法）"""
        instances = []
        covered_pairs = set()
        
        dimensions = test_space.dimensions
        n_dims = len(dimensions)
        
        # 初始化：选择前两个维度的全组合
        if n_dims >= 2:
            for v1 in dimensions[0].values:
                for v2 in dimensions[1].values:
                    params = {
                        dimensions[0].name: v1,
                        dimensions[1].name: v2
                    }
                    
                    # 为其他维度选择值
                    for i in range(2, n_dims):
                        # 选择能覆盖最多新pairs的值
                        best_value = self._select_best_value(
                            dimensions[i], params, covered_pairs, dimensions
                        )
                        params[dimensions[i].name] = best_value
                    
                    instance = TestInstance(
                        test_id=test_space.test_id,
                        parameters=params
                    )
                    instances.append(instance)
                    
                    # 记录覆盖的pairs
                    self._record_covered_pairs(params, covered_pairs, dimensions)
        
        # 检查是否有未覆盖的pairs，补充测试用例
        uncovered = self._find_uncovered_pairs(dimensions, covered_pairs)
        for pair in uncovered[:10]:  # 限制补充数量
            params = self._create_test_for_pair(pair, dimensions)
            instance = TestInstance(
                test_id=test_space.test_id,
                parameters=params
            )
            instances.append(instance)
        
        return instances
    
    def _expand_orthogonal_array(self, test_space: TestParameterSpace) -> List[TestInstance]:
        """正交数组展开"""
        # 使用预定义的正交数组或生成
        instances = []
        
        # 简化实现：对于混合水平，使用L36正交数组
        # 实际应用中应根据参数水平数选择合适的OA
        
        dimensions = test_space.dimensions
        
        # 生成正交数组索引
        oa_size = 36  # L36 for mixed levels
        n_dims = len(dimensions)
        
        for row in range(min(oa_size, test_space.get_full_space_size())):
            params = {}
            for i, dim in enumerate(dimensions):
                # 使用模运算分配值（简化版）
                value_idx = (row * (i + 1)) % dim.level_count
                params[dim.name] = dim.values[value_idx]
            
            instance = TestInstance(
                test_id=test_space.test_id,
                parameters=params
            )
            instances.append(instance)
        
        return instances
    
    def _expand_csp(self, test_space: TestParameterSpace) -> List[TestInstance]:
        """约束满足问题求解展开"""
        instances = []
        
        # 定义约束求解器（简化版）
        mandatory_combinations = []
        optional_combinations = []
        
        # 首先生成必须的组合
        for dim in test_space.dimensions:
            if dim.mandatory:
                # 确保每个必须维度的每个值至少被测试一次
                for value in dim.values:
                    params = {dim.name: value}
                    # 为其他维度选择默认值
                    for other_dim in test_space.dimensions:
                        if other_dim.name != dim.name:
                            params[other_dim.name] = other_dim.values[0]
                    
                    instance = TestInstance(
                        test_id=test_space.test_id,
                        parameters=params
                    )
                    mandatory_combinations.append(instance)
        
        # 合并重复的组合
        unique_instances = {}
        for inst in mandatory_combinations:
            key = tuple(sorted(inst.parameters.items()))
            unique_instances[key] = inst
        
        instances = list(unique_instances.values())
        
        # 添加关键边界条件组合
        boundary_combos = self._generate_boundary_combinations(test_space)
        instances.extend(boundary_combos)
        
        return instances
    
    def _expand_template(self, test_space: TestParameterSpace, pics_capabilities: Dict) -> List[TestInstance]:
        """基于模板的展开（使用已验证的模式）"""
        from ..templates.test_template_generator import TestTemplateLibrary, TestPlanGenerator
        
        generator = TestPlanGenerator()
        
        # 获取测试ID对应的模板
        template = generator.library.get_template(test_space.test_id)
        if not template:
            # 回退到pairwise
            return self._expand_pairwise(test_space)
        
        instances = []
        
        # 对每个支持的频段生成组合
        for band in pics_capabilities.get('supported_bands', []):
            band_bws = pics_capabilities.get('band_bandwidths', {}).get(band, [5, 10, 20])
            combos = template.get_combinations_for_band(band, band_bws)
            
            for combo in combos:
                params = {
                    'band': combo['band'],
                    'bandwidth': int(combo['bw'].replace(' MHz', '')),
                    'temperature': combo['temp'],
                    'voltage': combo['volt'],
                    'frequency': combo.get('tf', 'Mid')
                }
                
                instance = TestInstance(
                    test_id=test_space.test_id,
                    parameters=params
                )
                instances.append(instance)
        
        return instances
    
    def _filter_by_pics(self, test_space: TestParameterSpace, pics_capabilities: Dict) -> TestParameterSpace:
        """根据PICS能力过滤参数空间"""
        filtered_space = TestParameterSpace(
            test_id=test_space.test_id,
            test_type=test_space.test_type,
            dimensions=[],
            constraints=test_space.constraints,
            certification_requirements=test_space.certification_requirements
        )
        
        for dim in test_space.dimensions:
            if dim.name == 'band':
                # 过滤到支持的频段
                supported_bands = pics_capabilities.get('supported_bands', [])
                filtered_values = [v for v in dim.values if v in supported_bands]
                if filtered_values:
                    filtered_dim = ParameterDimension(
                        name=dim.name,
                        values=filtered_values,
                        mandatory=dim.mandatory,
                        constraints=dim.constraints
                    )
                    filtered_space.dimensions.append(filtered_dim)
            
            elif dim.name == 'bandwidth':
                # 根据频段过滤带宽
                # 这里简化处理，实际应根据每个频段的支持情况
                filtered_space.dimensions.append(dim)
            
            else:
                # 其他维度直接添加
                filtered_space.dimensions.append(dim)
        
        return filtered_space
    
    def _apply_constraints(self, instances: List[TestInstance], constraints: List[Dict]) -> List[TestInstance]:
        """应用约束条件过滤不合法的组合"""
        filtered = []
        
        for instance in instances:
            valid = True
            
            for constraint in constraints:
                if not self._evaluate_constraint(instance.parameters, constraint):
                    valid = False
                    break
            
            if valid:
                filtered.append(instance)
        
        return filtered
    
    def _evaluate_constraint(self, params: Dict, constraint: Dict) -> bool:
        """评估单个约束"""
        # 简化的约束评估
        # 例如: {"if": {"band": "eFDD1", "bandwidth": 25}, "then": False}
        
        if 'if' in constraint and 'then' in constraint:
            # 检查if条件
            if_condition = constraint['if']
            condition_met = all(
                params.get(k) == v for k, v in if_condition.items()
            )
            
            if condition_met:
                return constraint['then']
        
        return True
    
    def _calculate_scores(self, instances: List[TestInstance], test_space: TestParameterSpace) -> List[TestInstance]:
        """计算测试实例的优先级和分数"""
        for instance in instances:
            # 覆盖分数：基于参数组合的重要性
            coverage_score = self._calculate_coverage_score(instance.parameters, test_space)
            
            # 风险分数：基于历史数据和参数组合
            risk_score = self._calculate_risk_score(instance.parameters, test_space)
            
            # 优先级：综合考虑
            priority = coverage_score * 0.6 + risk_score * 0.4
            
            instance.coverage_score = coverage_score
            instance.risk_score = risk_score
            instance.priority = priority
        
        return instances
    
    def _calculate_coverage_score(self, params: Dict, test_space: TestParameterSpace) -> float:
        """计算覆盖分数"""
        score = 0.0
        
        # 边界条件加分
        if params.get('frequency') in ['Low', 'High']:
            score += 0.2
        
        # 极限环境加分
        if params.get('temperature') in ['Low extreme', 'High extreme']:
            score += 0.15
        
        # 极限带宽加分
        bw = params.get('bandwidth')
        if bw and (bw <= 5 or bw >= 100):
            score += 0.15
        
        # 基础分
        score += 0.5
        
        return min(score, 1.0)
    
    def _calculate_risk_score(self, params: Dict, test_space: TestParameterSpace) -> float:
        """计算风险分数"""
        # 基于历史经验的风险评估
        risk = 0.3  # 基础风险
        
        # 特定组合的已知风险
        if params.get('band') in ['eFDD1', 'eFDD3']:
            risk += 0.2
        
        if params.get('temperature') == 'High extreme':
            risk += 0.15
        
        return min(risk, 1.0)
    
    def _identify_test_type(self, test_id: str) -> str:
        """识别测试类型"""
        if test_id.startswith('6.2'):
            return 'Power'
        elif test_id.startswith('7.'):
            return 'Sensitivity'
        elif test_id.startswith('6.6'):
            return 'Spurious'
        elif test_id.startswith('6.5'):
            return 'Modulation'
        else:
            return 'General'
    
    def _extract_constraints(self, test_id: str, params: Dict) -> List[Dict]:
        """提取测试约束条件"""
        constraints = []
        
        # 从参数表中提取的约束
        # 例如：某些频段不支持特定带宽
        
        # Band-specific bandwidth constraints
        band_bw_constraints = {
            'eFDD1': [5, 10, 15, 20],  # 不支持25MHz以上
            'eTDD38': [5, 10, 20, 40],  # TDD特定带宽
        }
        
        for band, valid_bws in band_bw_constraints.items():
            for bw in [25, 30, 50, 100]:
                if bw not in valid_bws:
                    constraints.append({
                        'if': {'band': band, 'bandwidth': bw},
                        'then': False
                    })
        
        return constraints
    
    # 辅助方法
    def _select_best_value(self, dimension, existing_params, covered_pairs, all_dimensions):
        """为pairwise选择最佳值"""
        best_value = dimension.values[0]
        max_new_pairs = 0
        
        for value in dimension.values:
            new_pairs = 0
            test_params = {**existing_params, dimension.name: value}
            
            # 计算会覆盖多少新的pairs
            for other_dim in all_dimensions:
                if other_dim.name in test_params and other_dim.name != dimension.name:
                    pair = (dimension.name, value, other_dim.name, test_params[other_dim.name])
                    if pair not in covered_pairs:
                        new_pairs += 1
            
            if new_pairs > max_new_pairs:
                max_new_pairs = new_pairs
                best_value = value
        
        return best_value
    
    def _record_covered_pairs(self, params, covered_pairs, dimensions):
        """记录已覆盖的参数对"""
        dim_names = [d.name for d in dimensions]
        
        for i in range(len(dim_names)):
            for j in range(i + 1, len(dim_names)):
                if dim_names[i] in params and dim_names[j] in params:
                    pair1 = (dim_names[i], params[dim_names[i]], dim_names[j], params[dim_names[j]])
                    pair2 = (dim_names[j], params[dim_names[j]], dim_names[i], params[dim_names[i]])
                    covered_pairs.add(pair1)
                    covered_pairs.add(pair2)
    
    def _find_uncovered_pairs(self, dimensions, covered_pairs):
        """找到未覆盖的参数对"""
        uncovered = []
        
        for i in range(len(dimensions)):
            for j in range(i + 1, len(dimensions)):
                for v1 in dimensions[i].values:
                    for v2 in dimensions[j].values:
                        pair = (dimensions[i].name, v1, dimensions[j].name, v2)
                        if pair not in covered_pairs:
                            uncovered.append(pair)
        
        return uncovered
    
    def _create_test_for_pair(self, pair, dimensions):
        """为特定参数对创建测试"""
        params = {
            pair[0]: pair[1],
            pair[2]: pair[3]
        }
        
        # 为其他维度选择默认值
        for dim in dimensions:
            if dim.name not in params:
                params[dim.name] = dim.values[0]
        
        return params
    
    def _generate_boundary_combinations(self, test_space):
        """生成边界条件组合"""
        boundary_instances = []
        
        # 极限组合1：所有最小值
        min_params = {}
        for dim in test_space.dimensions:
            if dim.values:
                if isinstance(dim.values[0], (int, float)):
                    min_params[dim.name] = min(dim.values)
                else:
                    min_params[dim.name] = dim.values[0]
        
        boundary_instances.append(TestInstance(
            test_id=test_space.test_id,
            parameters=min_params,
            priority=0.9
        ))
        
        # 极限组合2：所有最大值
        max_params = {}
        for dim in test_space.dimensions:
            if dim.values:
                if isinstance(dim.values[0], (int, float)):
                    max_params[dim.name] = max(dim.values)
                else:
                    max_params[dim.name] = dim.values[-1]
        
        boundary_instances.append(TestInstance(
            test_id=test_space.test_id,
            parameters=max_params,
            priority=0.9
        ))
        
        return boundary_instances
    

def optimize_test_plan(test_instances: List[TestInstance], 
                       max_tests: Optional[int] = None,
                       min_coverage: float = 0.95) -> List[TestInstance]:
    """
    优化测试计划，平衡覆盖率和测试数量
    
    Args:
        test_instances: 所有可能的测试实例
        max_tests: 最大测试数量限制
        min_coverage: 最小覆盖率要求
    
    Returns:
        优化后的测试实例列表
    """
    # 按优先级排序
    sorted_instances = sorted(test_instances, key=lambda x: x.priority, reverse=True)
    
    if max_tests and len(sorted_instances) > max_tests:
        # 选择优先级最高的测试
        selected = sorted_instances[:max_tests]
        
        # 验证覆盖率
        coverage = calculate_coverage(selected, test_instances)
        if coverage < min_coverage:
            logger.warning(f"Coverage {coverage:.2%} is below minimum {min_coverage:.2%}")
    else:
        selected = sorted_instances
    
    return selected


def calculate_coverage(selected: List[TestInstance], 
                       all_instances: List[TestInstance]) -> float:
    """计算测试覆盖率"""
    if not all_instances:
        return 0.0
    
    # 基于参数组合的覆盖率
    all_combos = set()
    selected_combos = set()
    
    for inst in all_instances:
        combo = tuple(sorted(inst.parameters.items()))
        all_combos.add(combo)
    
    for inst in selected:
        combo = tuple(sorted(inst.parameters.items()))
        selected_combos.add(combo)
    
    return len(selected_combos) / len(all_combos)


if __name__ == "__main__":
    # 测试代码
    import sys
    base_path = Path(__file__).parent.parent.parent
    
    # 初始化引擎
    spec_path = base_path / "data_source/specs/ts_138521-1_v1840_2024q3.docx"
    engine = ParameterExpansionEngine(spec_path, OptimizationStrategy.PAIRWISE)
    
    # 测试参数空间提取
    test_space = engine.extract_parameter_space("6.2.2")
    if test_space:
        print(f"Test space for 6.2.2:")
        print(f"  Dimensions: {len(test_space.dimensions)}")
        print(f"  Full space size: {test_space.get_full_space_size()}")
        
        # 模拟PICS能力
        pics_capabilities = {
            'supported_bands': ['eFDD1', 'eFDD3', 'eFDD7', 'eTDD38'],
            'band_bandwidths': {
                'eFDD1': [5, 10, 15, 20],
                'eFDD3': [5, 10, 15, 20],
                'eFDD7': [5, 10, 20],
                'eTDD38': [5, 10, 20, 40]
            }
        }
        
        # 展开测试
        instances = engine.expand_test_cases(['6.2.2'], pics_capabilities)
        print(f"  Expanded instances: {len(instances)}")
        
        # 优化
        optimized = optimize_test_plan(instances, max_tests=50)
        print(f"  Optimized instances: {len(optimized)}")
        print(f"  Coverage: {calculate_coverage(optimized, instances):.2%}")