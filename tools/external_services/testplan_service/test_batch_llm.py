#!/usr/bin/env python3
"""
测试批量LLM条件解析功能
"""

import sys
from pathlib import Path
import importlib.util
import asyncio

# 导入批量LLM解析器
spec = importlib.util.spec_from_file_location('llm_parser', 'services/utils/llm_condition_parser.py')
llm_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(llm_module)

LLMConditionParser = llm_module.LLMConditionParser

async def test_batch_processing():
    parser = LLMConditionParser()
    
    # 测试批量条件
    test_conditions = [
        'A.4.1-1 AND A.4.1-2 THEN R ELSE N/A',
        'A.4.3-3b/2 AND NOT A.5.1-8a THEN M ELSE O',
        'A.4.1-1 OR A.4.1-2 THEN R ELSE N/A'
    ]
    
    print('🧪 测试批量LLM条件解析')
    print(f'条件数量: {len(test_conditions)}')
    
    try:
        # 批量解析
        batch_result = await parser.parse_conditions_batch(test_conditions)
        
        if batch_result.get('success'):
            print('✅ 批量解析成功')
            results = batch_result.get('results', [])
            
            for i, result in enumerate(results):
                print(f'\n条件 {i+1}:')
                print(f'  原始: {test_conditions[i]}')
                print(f'  解析条件: {result.get("if_condition")}')
                print(f'  THEN: {result.get("then_result")}')
                print(f'  ELSE: {result.get("else_result")}')
                print(f'  PICS引用: {result.get("pics_references")}')
            
            # 检查成本效益
            billing = batch_result.get('billing_info', {})
            if billing:
                total_cost = billing.get('cost_usd', 0)
                avg_cost = total_cost / len(test_conditions) if len(test_conditions) > 0 else 0
                print(f'\n💰 批量处理成本: ${total_cost:.6f}')
                print(f'   平均每个条件: ${avg_cost:.6f}')
        else:
            print(f'❌ 批量解析失败: {batch_result.get("error")}')
            
    except Exception as e:
        print(f'异常: {e}')

if __name__ == "__main__":
    asyncio.run(test_batch_processing())