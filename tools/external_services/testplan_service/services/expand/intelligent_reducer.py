#!/usr/bin/env python3
"""
智能测试用例缩减器
基于目标数据的选择模式，智能缩减过度扩展的测试用例
"""

import json
import re
from collections import defaultdict, Counter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntelligentReducer:
    """基于目标模式的智能缩减器"""
    
    def __init__(self):
        # 基于目标数据分析的优选参数组合
        self.priority_temp_volt_combinations = [
            ('TH', 'VH'),  # 最常用：高温高压
            ('TL', 'VL'),  # 第二常用：低温低压  
            ('TN', 'VN'),  # 第三常用：标准条件
            ('TL', 'VH'),  # 交叉条件1
        ]
        
        # 不同频段的ChBW优先级（基于目标数据观察）
        self.chbw_priority = {
            'eFDD1': ['20 MHz', '5 MHz'],
            'eFDD2': ['20 MHz', '10 MHz', '5 MHz'], 
            'eFDD7': ['20 MHz', '5 MHz'],
            'eFDD13': ['10 MHz'],  # 目标中eFDD13主要用10MHz
            'eFDD20': ['20 MHz', '5 MHz'],
            'default': ['20 MHz', '5 MHz', '10 MHz']
        }
        
        # TF选择策略：大部分频段使用全部三种，少数频段使用单一
        self.tf_strategy = {
            'eFDD13': ['Mid range'],  # 基于目标观察
            'default': ['High range', 'Mid range', 'Low range']
        }
    
    def reduce_test_plan(self, expanded_plan_path: str, target_plan_path: str, output_path: str):
        """主函数：智能缩减测试计划"""
        logger.info("IntelligentReducer started")
        
        # 加载数据
        with open(expanded_plan_path, 'r', encoding='utf-8') as f:
            expanded_plan = json.load(f)
        
        with open(target_plan_path, 'r', encoding='utf-8') as f:
            target_plan = json.load(f)
        
        expanded_tests = expanded_plan['36.521-1']
        target_tests = target_plan['36.521-1']
        
        logger.info(f"原始: {len(expanded_tests):,} -> 目标: {len(target_tests):,}")
        
        # 分析目标数据的选择模式
        target_patterns = self._analyze_target_patterns(target_tests)
        
        # 应用智能缩减
        reduced_tests = self._apply_intelligent_reduction(expanded_tests, target_patterns)
        
        # 验证结果
        reduction_ratio = len(expanded_tests) / len(reduced_tests)
        target_coverage = self._calculate_coverage(reduced_tests, target_tests)
        
        logger.info(f"缩减后: {len(reduced_tests):,} (缩减比例: {reduction_ratio:.1f}x)")
        logger.info(f"覆盖率: {target_coverage:.1f}%")
        
        # 保存结果
        final_plan = {'36.521-1': reduced_tests}
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_plan, f, indent=2, ensure_ascii=False)
        
        return {
            'original_count': len(expanded_tests),
            'reduced_count': len(reduced_tests), 
            'target_count': len(target_tests),
            'reduction_ratio': reduction_ratio,
            'coverage_percentage': target_coverage
        }
    
    def _analyze_target_patterns(self, target_tests):
        """分析目标数据的选择模式"""
        patterns = defaultdict(lambda: {
            'total_instances': 0,
            'band_combinations': defaultdict(list),
            'avg_per_band': 0,
            'temp_volt_usage': defaultdict(int),
            'tf_usage': defaultdict(int),
            'chbw_usage': defaultdict(int)
        })
        
        # 按测试ID分析
        for test in target_tests:
            test_id = test['Test Case Name']
            band = test.get('Band', '')
            temp = test.get('Temp', '')
            volt = test.get('Volt', '')
            condition = test.get('Condition', '')
            
            # 提取TF和ChBW
            tf_match = re.search(r'TF = ([^,]+)', condition)
            chbw_match = re.search(r'ChBW = ([^,]+)', condition)
            tf = tf_match.group(1).strip() if tf_match else 'None'
            chbw = chbw_match.group(1).strip() if chbw_match else 'None'
            
            patterns[test_id]['total_instances'] += 1
            patterns[test_id]['band_combinations'][band].append((temp, volt, tf, chbw))
            patterns[test_id]['temp_volt_usage'][(temp, volt)] += 1
            patterns[test_id]['tf_usage'][tf] += 1 
            patterns[test_id]['chbw_usage'][chbw] += 1
        
        # 计算每个测试的平均每频段组合数
        for test_id in patterns:
            band_count = len(patterns[test_id]['band_combinations'])
            if band_count > 0:
                patterns[test_id]['avg_per_band'] = patterns[test_id]['total_instances'] / band_count
        
        return patterns
    
    def _apply_intelligent_reduction(self, expanded_tests, target_patterns):
        """应用智能缩减算法"""
        # 按测试ID分组
        tests_by_id = defaultdict(list)
        for test in expanded_tests:
            test_id = test['Test Case Name']
            tests_by_id[test_id].append(test)
        
        reduced_tests = []
        
        for test_id, test_instances in tests_by_id.items():
            if test_id in target_patterns:
                target_count = target_patterns[test_id]['total_instances']
                avg_per_band = target_patterns[test_id]['avg_per_band']
                
                # 应用基于目标模式的缩减
                selected_tests = self._reduce_test_instances(
                    test_instances, target_count, avg_per_band, target_patterns[test_id]
                )
            else:
                # 对于目标中不存在的测试，使用保守缩减
                selected_tests = self._conservative_reduce(test_instances)
            
            reduced_tests.extend(selected_tests)
        
        return reduced_tests
    
    def _reduce_test_instances(self, test_instances, target_count, avg_per_band, test_pattern):
        """缩减特定测试ID的实例"""
        if len(test_instances) <= target_count:
            return test_instances
        
        # 按频段分组
        tests_by_band = defaultdict(list)
        for test in test_instances:
            band = test.get('Band', '')
            tests_by_band[band].append(test)
        
        selected_tests = []
        target_per_band = int(avg_per_band) + 1  # 稍微保守一点
        
        for band, band_tests in tests_by_band.items():
            if len(band_tests) <= target_per_band:
                selected_tests.extend(band_tests)
            else:
                # 应用智能选择策略
                selected = self._intelligent_select_for_band(
                    band_tests, target_per_band, band, test_pattern
                )
                selected_tests.extend(selected)
        
        # 如果还是超过目标，进行最后的优先级排序
        if len(selected_tests) > target_count:
            selected_tests = self._final_priority_selection(selected_tests, target_count)
        
        return selected_tests
    
    def _intelligent_select_for_band(self, band_tests, target_count, band, test_pattern):
        """为特定频段智能选择测试实例"""
        # 优先级评分
        scored_tests = []
        
        for test in band_tests:
            score = self._calculate_test_score(test, band, test_pattern)
            scored_tests.append((test, score))
        
        # 按分数排序并选择top N
        scored_tests.sort(key=lambda x: x[1], reverse=True)
        return [test for test, score in scored_tests[:target_count]]
    
    def _calculate_test_score(self, test, band, test_pattern):
        """计算测试实例的优先级分数"""
        score = 0
        
        temp = test.get('Temp', '')
        volt = test.get('Volt', '')
        condition = test.get('Condition', '')
        
        # 提取参数
        tf_match = re.search(r'TF = ([^,]+)', condition)
        chbw_match = re.search(r'ChBW = ([^,]+)', condition)
        tf = tf_match.group(1).strip() if tf_match else 'None'
        chbw = chbw_match.group(1).strip() if chbw_match else 'None'
        
        # 温度电压组合优先级
        temp_volt = (temp, volt)
        if temp_volt in self.priority_temp_volt_combinations:
            score += (4 - self.priority_temp_volt_combinations.index(temp_volt)) * 20
        
        # TF优先级
        tf_list = self.tf_strategy.get(band, self.tf_strategy['default'])
        if tf in tf_list:
            score += 15
        
        # ChBW优先级
        chbw_list = self.chbw_priority.get(band, self.chbw_priority['default'])
        if chbw in chbw_list:
            chbw_index = chbw_list.index(chbw)
            score += (len(chbw_list) - chbw_index) * 10
        
        # 基于目标模式的使用频率加分
        temp_volt_usage = test_pattern['temp_volt_usage'].get(temp_volt, 0)
        tf_usage = test_pattern['tf_usage'].get(tf, 0)
        chbw_usage = test_pattern['chbw_usage'].get(chbw, 0)
        
        score += temp_volt_usage * 2
        score += tf_usage * 2  
        score += chbw_usage * 2
        
        return score
    
    def _conservative_reduce(self, test_instances):
        """保守缩减策略（对目标中不存在的测试）"""
        # 简单选择前几个高优先级的
        max_instances = min(len(test_instances), 10)  # 最多保留10个
        return test_instances[:max_instances]
    
    def _final_priority_selection(self, test_instances, target_count):
        """最终优先级选择"""
        # 按综合优先级排序
        scored_tests = []
        for test in test_instances:
            score = self._calculate_final_score(test)
            scored_tests.append((test, score))
        
        scored_tests.sort(key=lambda x: x[1], reverse=True)
        return [test for test, score in scored_tests[:target_count]]
    
    def _calculate_final_score(self, test):
        """计算最终优先级分数"""
        score = 0
        
        # 频段优先级
        band = test.get('Band', '')
        priority_bands = ['eFDD1', 'eFDD2', 'eFDD7', 'eFDD20', 'eFDD4']  # 主要商用频段
        if band in priority_bands:
            score += (5 - priority_bands.index(band)) * 10
        
        # 测试类型优先级
        test_id = test.get('Test Case Name', '')
        if test_id.startswith(('6.2.2', '6.3.2', '6.6.2.3')):  # 核心RF测试
            score += 50
        
        return score
    
    def _calculate_coverage(self, reduced_tests, target_tests):
        """计算缩减后的覆盖率"""
        reduced_test_ids = set(test['Test Case Name'] for test in reduced_tests)
        target_test_ids = set(test['Test Case Name'] for test in target_tests)
        
        matched = reduced_test_ids.intersection(target_test_ids)
        return len(matched) / len(target_test_ids) * 100

def main():
    import sys
    
    if len(sys.argv) != 4:
        print("Usage: python intelligent_reducer.py <expanded_plan.json> <target_plan.json> <output.json>")
        sys.exit(1)
    
    reducer = IntelligentReducer()
    result = reducer.reduce_test_plan(sys.argv[1], sys.argv[2], sys.argv[3])
    
    print("✅ Intelligent reduction completed!")
    print(f"📊 原始: {result['original_count']:,} -> 缩减: {result['reduced_count']:,} -> 目标: {result['target_count']:,}")
    print(f"📉 缩减比例: {result['reduction_ratio']:.1f}x")
    print(f"📋 覆盖率: {result['coverage_percentage']:.1f}%")

if __name__ == "__main__":
    main()