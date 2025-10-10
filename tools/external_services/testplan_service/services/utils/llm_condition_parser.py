#!/usr/bin/env python3
"""
LLM增强的3GPP条件表达式解析器
使用AI来解析复杂的IF-THEN-ELSE条件表达式，补充正则表达式的不足
"""

import json
import sys
import os
from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio

# 添加项目路径
sys.path.append('/Users/xenodennis/Documents/Fun/isA_MCP/tools/services')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMConditionParser:
    """
    使用LLM解析3GPP条件表达式的增强解析器
    """
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        """Lazy load ISA client"""
        if self._client is None:
            try:
                # 尝试直接使用ISA客户端
                sys.path.append('/Users/xenodennis/Documents/Fun/isA_Model')
                from isa_model.client import ISAModelClient
                self._client = ISAModelClient()
            except ImportError as e:
                logger.error(f"Failed to import ISAModelClient: {e}")
                raise
        return self._client
    
    async def parse_condition(self, condition_expr: str) -> Dict[str, Any]:
        """
        使用LLM解析3GPP条件表达式
        
        Args:
            condition_expr: 3GPP条件表达式，如 "IF A.4.3-3b/2 AND NOT(...) THEN R ELSE N/A"
            
        Returns:
            解析后的结构化数据
        """
        try:
            if not condition_expr or condition_expr.strip() == '':
                return {
                    'success': False,
                    'error': 'Empty condition expression',
                    'data': {}
                }
            
            # 构建专门的解析提示
            prompt = f"""Parse this 3GPP test condition expression and extract its components.

Condition Expression: {condition_expr}

This is a 3GPP conformance test condition. It may follow the pattern:
"IF (boolean_condition) THEN result ELSE alternative_result"

Or it may be a malformed condition that needs to be interpreted. For example:
- "A.4.3-3b/2 AND A.5.1-8a THEN R ELSE N/A" (missing IF keyword)
- "IF A.4.3-3b/2 AND NOT(...) THEN R ELSE N/A" (complex nested conditions)

Please parse and return a JSON object with the following structure:
{{
    "condition_type": "IF_THEN_ELSE",
    "if_condition": "the complete boolean condition part that should be evaluated",
    "then_result": "result when condition is true", 
    "else_result": "result when condition is false",
    "pics_references": ["list", "of", "PICS", "items", "referenced"],
    "boolean_operators": ["list", "of", "AND/OR/NOT", "operators", "found"],
    "parseable": true,
    "complexity": "simple/medium/complex"
}}

Extract:
- The boolean condition that needs to be evaluated (even if IF is missing)
- THEN result (usually R, M, O, N/A)
- ELSE result (usually N/A)  
- All PICS references (format: A.x.x-x/x or A.x.x-x)
- Boolean operators used (AND, OR, NOT)

For malformed conditions, infer the intended structure. For example:
"A.4.3-3b/2 AND A.5.1-8a THEN R ELSE N/A" should be interpreted as:
if_condition: "A.4.3-3b/2 AND A.5.1-8a"

Example PICS references: A.4.3-3b/2, A.4.3-4a/1, A.4.1-1/1"""

            # 使用ISA客户端进行解析
            response = await self.client.invoke(
                input_data=prompt,
                task="chat",
                service_type="text",
                model="gpt-4.1-mini",  # 使用更强模型处理复杂解析
                temperature=0.1,
                stream=False,
                response_format={"type": "json_object"}  # 启用JSON模式
            )
            
            if not response.get('success'):
                raise Exception(f"LLM parsing failed: {response.get('error', 'Unknown error')}")
            
            # 处理响应
            result = response.get('result', '')
            billing_info = response.get('metadata', {}).get('billing', {})
            
            # 处理AIMessage对象
            if hasattr(result, 'content'):
                result_text = result.content
            elif isinstance(result, str):
                result_text = result
            else:
                result_text = str(result)
            
            if not result_text:
                raise Exception("No result found in LLM response")
            
            # 解析JSON响应
            try:
                parsed_data = json.loads(result_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                logger.error(f"Response text: {result_text}")
                raise Exception(f"Invalid JSON from LLM: {e}")
            
            # 验证解析结果的完整性
            required_fields = ['if_condition', 'then_result', 'pics_references']
            missing_fields = [field for field in required_fields if field not in parsed_data]
            
            if missing_fields:
                logger.warning(f"Missing required fields in LLM response: {missing_fields}")
                # 尝试补充缺失字段
                parsed_data = self._supplement_missing_fields(parsed_data, condition_expr)
            
            # 记录成本信息
            if billing_info:
                logger.info(f"💰 LLM condition parsing cost: ${billing_info.get('cost_usd', 0.0):.6f}")
            
            return {
                'success': True,
                'data': parsed_data,
                'billing_info': billing_info,
                'original_expression': condition_expr
            }
            
        except Exception as e:
            logger.error(f"LLM condition parsing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'original_expression': condition_expr
            }
    
    def _supplement_missing_fields(self, data: Dict[str, Any], original_expr: str) -> Dict[str, Any]:
        """补充LLM解析结果中的缺失字段"""
        import re
        
        # 如果缺少PICS引用，尝试用正则表达式提取
        if 'pics_references' not in data or not data['pics_references']:
            pics_refs = re.findall(r'A\.[0-9.-]+/[0-9]+[a-z]*', original_expr)
            data['pics_references'] = list(set(pics_refs))
        
        # 如果缺少条件部分，尝试基本解析
        if 'if_condition' not in data:
            if_match = re.search(r'IF\s+(.+?)\s+THEN', original_expr, re.IGNORECASE)
            if if_match:
                data['if_condition'] = if_match.group(1).strip()
        
        # 如果缺少THEN结果
        if 'then_result' not in data:
            then_match = re.search(r'THEN\s+([A-Z/]+)', original_expr, re.IGNORECASE)
            if then_match:
                data['then_result'] = then_match.group(1)
        
        # 如果缺少ELSE结果
        if 'else_result' not in data:
            else_match = re.search(r'ELSE\s+([A-Z/]+)', original_expr, re.IGNORECASE)
            if else_match:
                data['else_result'] = else_match.group(1)
            else:
                data['else_result'] = 'N/A'  # 默认值
        
        return data
    
    async def evaluate_condition(
        self, 
        condition_expr: str, 
        pics_values: Dict[str, bool]
    ) -> Tuple[str, str, List[str]]:
        """
        解析并评估3GPP条件表达式
        
        Args:
            condition_expr: 3GPP条件表达式
            pics_values: PICS项目的值映射
            
        Returns:
            (result, logic, steps) - 评估结果、逻辑说明、步骤
        """
        try:
            # 先用LLM解析条件结构
            parse_result = await self.parse_condition(condition_expr)
            
            if not parse_result['success']:
                return 'N/A', f"Parse failed: {parse_result['error']}", []
            
            parsed_data = parse_result['data']
            if_condition = parsed_data.get('if_condition', '')
            then_result = parsed_data.get('then_result', 'R')
            else_result = parsed_data.get('else_result', 'N/A')
            pics_refs = parsed_data.get('pics_references', [])
            
            # 构建评估步骤
            evaluation_steps = []
            pics_used = {}
            
            # 获取相关PICS值
            for pics_ref in pics_refs:
                value = pics_values.get(pics_ref, False)  # 默认为False
                pics_used[pics_ref] = value
                evaluation_steps.append(f'{pics_ref} = {value}')
            
            # 使用LLM进行布尔表达式评估
            eval_result = await self._evaluate_boolean_expression(
                if_condition, pics_used
            )
            
            if eval_result['success']:
                condition_result = eval_result['result']
                evaluation_steps.extend(eval_result['steps'])
                
                final_result = then_result if condition_result else else_result
                logic = f"Condition: {if_condition}\nPICS values: {pics_used}\nEvaluated: {condition_result} → {final_result}"
                
                return final_result, logic, evaluation_steps
            else:
                return 'N/A', f"Evaluation error: {eval_result['error']}", evaluation_steps
                
        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            return 'N/A', f"Evaluation exception: {str(e)}", []
    
    async def _evaluate_boolean_expression(
        self, 
        expression: str, 
        pics_values: Dict[str, bool]
    ) -> Dict[str, Any]:
        """
        使用LLM评估复杂的布尔表达式
        """
        try:
            # 构建评估提示
            pics_str = json.dumps(pics_values, indent=2)
            
            prompt = f"""Evaluate this boolean expression using the provided PICS values.

Boolean Expression: {expression}

PICS Values:
{pics_str}

Instructions:
1. Replace each PICS reference (A.x.x-x/x) with its boolean value (true/false)
2. Evaluate the boolean expression step by step
3. Handle AND, OR, NOT operators correctly
4. Return the final boolean result

Return JSON format:
{{
    "result": true/false,
    "steps": ["step1", "step2", "final_evaluation"],
    "substituted_expression": "expression with PICS values substituted",
    "final_expression": "simplified boolean expression",
    "success": true
}}

Example:
Expression: A.4.3-3b/2 AND NOT(A.4.3-4a/1 OR A.4.3-4a/1a)  
With A.4.3-3b/2=true, A.4.3-4a/1=false, A.4.3-4a/1a=false
Steps: "true AND NOT(false OR false)" → "true AND NOT(false)" → "true AND true" → "true"
"""

            response = await self.client.invoke(
                input_data=prompt,
                task="chat", 
                service_type="text",
                model="gpt-4.1-mini",
                temperature=0.1,
                stream=False,
                response_format={"type": "json_object"}
            )
            
            if not response.get('success'):
                raise Exception(f"LLM evaluation failed: {response.get('error')}")
            
            result = response.get('result', '')
            if hasattr(result, 'content'):
                result_text = result.content
            else:
                result_text = str(result)
            
            eval_data = json.loads(result_text)
            
            return {
                'success': True,
                'result': eval_data.get('result', False),
                'steps': eval_data.get('steps', []),
                'substituted_expression': eval_data.get('substituted_expression', ''),
                'final_expression': eval_data.get('final_expression', '')
            }
            
        except Exception as e:
            logger.error(f"Boolean expression evaluation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'result': False,
                'steps': [f"Error: {str(e)}"]
            }
    
    async def parse_conditions_batch(self, condition_expressions: List[str]) -> Dict[str, Any]:
        """
        批量解析多个3GPP条件表达式
        
        Args:
            condition_expressions: 条件表达式列表
            
        Returns:
            批量解析结果
        """
        if not condition_expressions:
            return {'success': True, 'results': []}
        
        try:
            # 构建批量解析提示
            conditions_text = ""
            for i, expr in enumerate(condition_expressions):
                conditions_text += f"{i+1}. {expr}\n"
            
            prompt = f"""Parse these {len(condition_expressions)} 3GPP test condition expressions and extract their components.

Condition Expressions:
{conditions_text}

Each condition may follow the pattern "IF (boolean_condition) THEN result ELSE alternative_result"
or may be malformed (missing IF, etc.) that needs interpretation.

Please parse and return a JSON object with this structure:
{{
    "conditions": [
        {{
            "index": 1,
            "condition_type": "IF_THEN_ELSE",
            "if_condition": "the complete boolean condition part",
            "then_result": "result when condition is true", 
            "else_result": "result when condition is false",
            "pics_references": ["list", "of", "PICS", "items"],
            "boolean_operators": ["AND", "OR", "NOT"],
            "parseable": true,
            "complexity": "simple/medium/complex"
        }},
        ...
    ],
    "total_processed": {len(condition_expressions)},
    "processing_notes": ["any issues or notes"]
}}

Extract for each condition:
- The boolean condition (even if IF keyword is missing)
- THEN result (R, M, O, N/A)
- ELSE result (usually N/A)
- All PICS references (A.x.x-x/x format)
- Boolean operators (AND, OR, NOT)

For malformed conditions, infer the intended structure.
Example PICS: A.4.3-3b/2, A.4.1-1/1"""

            # 使用ISA客户端批量解析
            response = await self.client.invoke(
                input_data=prompt,
                task="chat",
                service_type="text",
                model="gpt-4.1-mini",
                temperature=0.1,
                stream=False,
                response_format={"type": "json_object"},
                max_tokens=4000  # 增加token限制以处理批量数据
            )
            
            if not response.get('success'):
                raise Exception(f"Batch LLM parsing failed: {response.get('error')}")
            
            result = response.get('result', '')
            if hasattr(result, 'content'):
                result_text = result.content
            else:
                result_text = str(result)
            
            # 解析批量JSON响应
            batch_data = json.loads(result_text)
            
            # 验证批量结果
            if 'conditions' not in batch_data:
                raise Exception("Missing 'conditions' in batch response")
            
            conditions = batch_data['conditions']
            if len(conditions) != len(condition_expressions):
                logger.warning(f"Batch size mismatch: expected {len(condition_expressions)}, got {len(conditions)}")
            
            # 记录成本信息
            billing_info = response.get('metadata', {}).get('billing', {})
            if billing_info:
                cost_per_condition = billing_info.get('cost_usd', 0.0) / len(condition_expressions)
                logger.info(f"💰 Batch LLM parsing cost: ${billing_info.get('cost_usd', 0.0):.6f} (${cost_per_condition:.6f} per condition)")
            
            return {
                'success': True,
                'results': conditions,
                'total_processed': len(conditions),
                'billing_info': billing_info,
                'original_expressions': condition_expressions
            }
            
        except Exception as e:
            logger.error(f"Batch LLM condition parsing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'original_expressions': condition_expressions
            }


# 测试函数
async def test_condition_parser():
    """测试LLM条件解析器"""
    parser = LLMConditionParser()
    
    # 测试条件
    test_conditions = [
        "IF A.4.3-3b/2 AND NOT(A.4.3-4a/1 OR A.4.3-4a/1a OR A.4.3-4aa/1) THEN R ELSE N/A",
        "IF (A.4.1-1/1 AND A.4.2-1/1) THEN R ELSE N/A",
        "IF NOT(A.4.3-4a/1) AND A.4.1-1/2 THEN M ELSE O"
    ]
    
    # 模拟PICS值
    pics_values = {
        'A.4.3-3b/2': True,
        'A.4.3-4a/1': False, 
        'A.4.3-4a/1a': False,
        'A.4.3-4aa/1': False,
        'A.4.1-1/1': True,
        'A.4.1-1/2': True,
        'A.4.2-1/1': True
    }
    
    print("🧪 测试LLM条件解析器")
    
    for i, condition in enumerate(test_conditions):
        print(f"\n--- 测试 {i+1} ---")
        print(f"条件: {condition}")
        
        # 解析条件
        parse_result = await parser.parse_condition(condition)
        if parse_result['success']:
            print("✅ 解析成功")
            data = parse_result['data']
            print(f"  IF条件: {data.get('if_condition')}")
            print(f"  THEN结果: {data.get('then_result')}")
            print(f"  ELSE结果: {data.get('else_result')}")
            print(f"  PICS引用: {data.get('pics_references')}")
            
            # 评估条件
            result, logic, steps = await parser.evaluate_condition(condition, pics_values)
            print(f"  评估结果: {result}")
            print(f"  评估步骤: {steps[:3]}...")  # 显示前3个步骤
        else:
            print(f"❌ 解析失败: {parse_result['error']}")


if __name__ == "__main__":
    asyncio.run(test_condition_parser())