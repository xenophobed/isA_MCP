#!/usr/bin/env python3
"""
从34.121-2文档中提取Applicability表格
查找C_RF04等条件定义和IF-THEN逻辑
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, List
import logging

# Add paths
sys.path.insert(0, "/Users/xenodennis/Documents/Fun/isA_MCP")
base_path = Path(__file__).parent.parent
sys.path.insert(0, str(base_path))

from services.parser.document_parser import DocumentParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_applicability_conditions():
    """提取Applicability表格中的条件定义"""
    
    parser = DocumentParser()
    doc_path = base_path / "data_source/3GPP/TS 34.121-2/34121-2-f10/34121-2-f10.doc"
    
    logger.info(f"📄 Parsing document: {doc_path.name}")
    
    # 解析文档
    parsed_doc = parser.parse_document(str(doc_path))
    if not parsed_doc.success:
        logger.error(f"Failed to parse: {parsed_doc.error}")
        return
    
    content = parsed_doc.content
    logger.info(f"Document length: {len(content)} chars")
    
    # 查找Table 1b: Applicability区域
    table_patterns = [
        r'Table\s+1b[:\s]+Applicability',
        r'Applicability\s+Table',
        r'Table.*Applicability.*conditions'
    ]
    
    table_start = -1
    for pattern in table_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            table_start = match.start()
            logger.info(f"✅ Found Table 1b at position {table_start}")
            break
    
    if table_start == -1:
        logger.warning("Could not find Table 1b: Applicability")
        # 尝试直接查找条件模式
        logger.info("Searching for conditions directly...")
    else:
        # 提取表格内容（接下来的10000字符）
        table_content = content[table_start:table_start+10000]
        logger.info(f"Extracted table content: {len(table_content)} chars")
        
        # 查找条件定义
        # 模式: C_RF04    IF A.7/9 OR A.7/10 THEN R ELSE N/A
        condition_patterns = [
            r'(C_[A-Z0-9]+)\s+IF\s+([^T]+)\s+THEN\s+([RMO])\s+ELSE\s+([^\n]+)',
            r'(C_[A-Z0-9]+)\s+([A-Z]\.\d+[/\-]\d+(?:\s+(?:OR|AND)\s+[A-Z]\.\d+[/\-]\d+)*)',
            r'(C\d+)\s+IF\s+([^T]+)\s+THEN\s+([RMO])\s+ELSE\s+([^\n]+)'
        ]
        
        conditions_found = []
        for pattern in condition_patterns:
            matches = re.findall(pattern, table_content, re.IGNORECASE)
            logger.info(f"Pattern '{pattern[:50]}...' found {len(matches)} matches")
            
            for match in matches:
                if len(match) == 4:  # IF-THEN-ELSE format
                    condition_id, condition, then_value, else_value = match
                    conditions_found.append({
                        "condition_id": condition_id.strip(),
                        "if_condition": condition.strip(),
                        "then_value": then_value.strip(),
                        "else_value": else_value.strip(),
                        "full_expression": f"IF {condition.strip()} THEN {then_value.strip()} ELSE {else_value.strip()}"
                    })
                elif len(match) == 2:  # Simple condition
                    condition_id, pics_refs = match
                    conditions_found.append({
                        "condition_id": condition_id.strip(),
                        "pics_references": pics_refs.strip()
                    })
        
        logger.info(f"\n📊 Found {len(conditions_found)} conditions in Table 1b")
        
        # 显示找到的条件
        for i, cond in enumerate(conditions_found[:10], 1):
            logger.info(f"\nCondition {i}:")
            logger.info(f"  ID: {cond.get('condition_id')}")
            if 'full_expression' in cond:
                logger.info(f"  Expression: {cond['full_expression']}")
            elif 'pics_references' in cond:
                logger.info(f"  PICS Refs: {cond['pics_references']}")
    
    # 在整个文档中搜索C_RF04等特定条件
    logger.info("\n🔍 Searching for specific conditions in entire document...")
    
    specific_conditions = ['C_RF04', 'C_RF01', 'C_RF02', 'C_RF03', 'C_RF05']
    all_conditions = {}
    
    for cond_id in specific_conditions:
        # 查找条件定义
        pattern = rf'{cond_id}\s+[^\n]{{1,200}}'
        matches = re.findall(pattern, content, re.IGNORECASE)
        
        if matches:
            logger.info(f"\n✅ Found {cond_id}:")
            for match in matches[:3]:  # 显示前3个匹配
                logger.info(f"  - {match.strip()}")
            all_conditions[cond_id] = matches
    
    # 查找所有C_开头的条件
    all_c_conditions = re.findall(r'(C_[A-Z0-9]+)\s+([^\n]{1,200})', content)
    logger.info(f"\n📋 Found {len(all_c_conditions)} total C_ conditions")
    
    # 统计不同类型的条件
    condition_types = {}
    for cond_id, desc in all_c_conditions:
        prefix = cond_id.split('_')[1][:2] if '_' in cond_id else 'OTHER'
        if prefix not in condition_types:
            condition_types[prefix] = []
        condition_types[prefix].append(cond_id)
    
    logger.info("\n📊 Condition categories:")
    for prefix, conditions in condition_types.items():
        logger.info(f"  {prefix}: {len(conditions)} conditions")
        logger.info(f"    Examples: {', '.join(list(set(conditions))[:5])}")
    
    # 查找PICS项引用（A.x/x格式）
    pics_refs = re.findall(r'([A-Z]\.\d+[/\-]\d+(?:[/\-]\d+)?)', content)
    unique_pics = list(set(pics_refs))
    logger.info(f"\n🔗 Found {len(unique_pics)} unique PICS references")
    logger.info(f"  Examples: {', '.join(unique_pics[:10])}")
    
    # 保存结果
    results = {
        "document": "34.121-2-f10",
        "conditions_in_table": conditions_found if table_start != -1 else [],
        "all_c_conditions": [
            {"id": cond_id, "description": desc.strip()[:200]} 
            for cond_id, desc in all_c_conditions[:100]
        ],
        "condition_categories": {
            prefix: list(set(conditions))[:20] 
            for prefix, conditions in condition_types.items()
        },
        "unique_pics_refs": unique_pics[:50],
        "summary": {
            "total_conditions": len(all_c_conditions),
            "total_pics_refs": len(unique_pics),
            "has_applicability_table": table_start != -1
        }
    }
    
    output_file = base_path / "outputs/34121_applicability_conditions.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n💾 Saved results to: {output_file}")
    
    # 返回一些关键信息用于进一步分析
    return results


if __name__ == "__main__":
    logger.info("🚀 Extracting Applicability conditions from 34.121-2...")
    results = extract_applicability_conditions()
    
    if results and results['conditions_in_table']:
        logger.info("\n✨ Successfully found Table 1b conditions with IF-THEN logic!")
        logger.info("This proves that 3GPP documents DO contain explicit condition mappings.")
        logger.info("We need to apply similar extraction logic to 36.521-2 and 36.523-2 documents.")
    
    logger.info("\n✅ Extraction complete!")