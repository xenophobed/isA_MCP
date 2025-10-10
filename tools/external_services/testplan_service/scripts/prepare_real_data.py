#!/usr/bin/env python3
"""
准备真实数据用于验证PICS到TestPlan的计算
从已提取的文档中整理数据
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add paths
sys.path.insert(0, "/Users/xenodennis/Documents/Fun/isA_MCP")
base_path = Path(__file__).parent.parent
sys.path.insert(0, str(base_path))

from services.parser.document_parser import DocumentParser


def extract_real_data():
    """提取真实数据"""
    
    print("🚀 Extracting real data from 3GPP documents...")
    
    # 1. 提取条件定义（从36.521-2）
    conditions = extract_conditions_from_36521_2()
    
    # 2. 提取测试用例（从36.521-1）
    test_cases = extract_test_cases_from_36521_1()
    
    # 3. 提取PICS定义（从36.521-2 Annex A）
    pics_definitions = extract_pics_definitions()
    
    # 4. 组装完整数据
    complete_data = {
        "source": "3GPP TS 36.521 series",
        "extraction_date": "2024-12-20",
        "conditions": conditions,
        "test_cases": test_cases,
        "pics_definitions": pics_definitions,
        "test_to_condition_mapping": map_tests_to_conditions(test_cases),
        "summary": {
            "total_conditions": len(conditions),
            "total_test_cases": len(test_cases),
            "total_pics_items": len(pics_definitions)
        }
    }
    
    # 保存到JSON文件
    output_file = base_path / "services/store/real_3gpp_data.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(complete_data, f, indent=2)
    
    print(f"✅ Saved real data to: {output_file}")
    print(f"📊 Summary:")
    print(f"  - Conditions: {len(conditions)}")
    print(f"  - Test cases: {len(test_cases)}")
    print(f"  - PICS items: {len(pics_definitions)}")
    
    return complete_data


def extract_conditions_from_36521_2():
    """从36.521-2提取条件定义"""
    
    parser = DocumentParser()
    doc_path = base_path / "data_source/3GPP/TS 36.521-2/36521-2-i80/36521-2-i80.docx"
    
    print("📄 Extracting conditions from 36.521-2...")
    
    parsed_doc = parser.parse_document(str(doc_path))
    if not parsed_doc.success:
        return []
    
    content = parsed_doc.content
    conditions = []
    
    # 提取IF-THEN条件
    pattern = r'(C\d{1,3})[:\s]+IF\s+([^T]+?)THEN\s+([^E]+?)ELSE\s+([^\n]+?)(?=C\d+|$)'
    matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
    
    for cond_id, if_clause, then_val, else_val in matches:
        # 清理文本
        if_clause = ' '.join(if_clause.split()).strip()
        then_val = then_val.strip()
        else_val = else_val.strip()
        
        # 提取PICS引用
        pics_refs = re.findall(r'A\.\d+(?:[/\-]\d+)*', if_clause)
        
        conditions.append({
            "condition_id": cond_id.strip(),
            "if_clause": if_clause,
            "then_value": then_val,
            "else_value": else_val,
            "pics_references": pics_refs
        })
    
    print(f"  Found {len(conditions)} conditions")
    
    # 显示样本
    if conditions:
        print("  Sample conditions:")
        for cond in conditions[:3]:
            print(f"    - {cond['condition_id']}: IF {cond['if_clause'][:50]}... THEN {cond['then_value']}")
    
    return conditions


def extract_test_cases_from_36521_1():
    """从36.521-1提取测试用例"""
    
    # 从之前的提取结果读取
    extraction_file = base_path / "outputs/complete_3gpp_extraction.json"
    
    if extraction_file.exists():
        print("📄 Loading test cases from previous extraction...")
        with open(extraction_file, 'r') as f:
            data = json.load(f)
            test_cases = data.get("test_cases", [])
            print(f"  Loaded {len(test_cases)} test cases")
            return test_cases
    
    # 如果没有之前的提取结果，从文档提取
    parser = DocumentParser()
    doc_path = base_path / "data_source/3GPP/TS 36.521-1/36521-1-i80/36521-1-i80_s06a-s06b4.docx"
    
    print("📄 Extracting test cases from 36.521-1...")
    
    if not doc_path.exists():
        print("  ⚠️ 36.521-1 document not found")
        return []
    
    parsed_doc = parser.parse_document(str(doc_path))
    if not parsed_doc.success:
        return []
    
    content = parsed_doc.content[:100000]  # First 100k chars
    test_cases = []
    
    # 提取测试用例（格式: 6.2.2, 7.1.1.1, etc.）
    pattern = r'(\d+\.\d+(?:\.\d+)*)\s+([^\n]{1,200})'
    matches = re.findall(pattern, content)
    
    for test_id, test_name in matches[:100]:  # 限制数量
        # 过滤明显不是测试用例的
        if len(test_id.split('.')) >= 2 and not test_name.startswith('The'):
            test_cases.append({
                "test_id": test_id,
                "test_name": test_name.strip(),
                "specification": "36.521-1"
            })
    
    print(f"  Found {len(test_cases)} test cases")
    return test_cases


def extract_pics_definitions():
    """从36.521-2 Annex A提取PICS定义"""
    
    parser = DocumentParser()
    doc_path = base_path / "data_source/3GPP/TS 36.521-2/36521-2-i80/36521-2-i80.docx"
    
    print("📄 Extracting PICS definitions from 36.521-2 Annex A...")
    
    parsed_doc = parser.parse_document(str(doc_path))
    if not parsed_doc.success:
        return []
    
    content = parsed_doc.content
    pics_items = []
    
    # 查找Annex A
    annex_pos = content.find("Annex A")
    if annex_pos == -1:
        annex_pos = content.find("A.4")  # 尝试直接找A.4节
    
    if annex_pos != -1:
        # 提取Annex A后的内容
        annex_content = content[annex_pos:min(annex_pos+200000, len(content))]
        
        # 提取PICS项（格式: A.4.1-1/1）
        pattern = r'(A\.\d+(?:\.\d+)*(?:[/\-]\d+)*)\s+([^\n]{1,200})'
        matches = re.findall(pattern, annex_content)
        
        seen = set()
        for pics_id, description in matches:
            if pics_id not in seen and not description.startswith('A.'):
                seen.add(pics_id)
                pics_items.append({
                    "pics_id": pics_id,
                    "description": description.strip()[:200],
                    "category": pics_id.split('.')[1] if '.' in pics_id else "unknown"
                })
    
    print(f"  Found {len(pics_items)} PICS items")
    
    # 显示样本
    if pics_items:
        print("  Sample PICS items:")
        for item in pics_items[:5]:
            print(f"    - {item['pics_id']}: {item['description'][:50]}...")
    
    return pics_items


def map_tests_to_conditions(test_cases):
    """建立测试用例到条件的映射"""
    
    # 从36.521-2的Table 4.1-1读取映射
    parser = DocumentParser()
    doc_path = base_path / "data_source/3GPP/TS 36.521-2/36521-2-i80/36521-2-i80.docx"
    
    print("📄 Extracting test-to-condition mappings from Table 4.1-1...")
    
    parsed_doc = parser.parse_document(str(doc_path))
    if not parsed_doc.success:
        return []
    
    content = parsed_doc.content
    mappings = []
    
    # 查找Table 4.1-1
    table_pos = content.find("Table 4.1-1")
    if table_pos != -1:
        # 提取表格内容
        table_content = content[table_pos:table_pos+300000]
        
        # 查找测试用例和条件的对应关系
        # 格式: 6.2.2 ... C186 ...
        lines = table_content.split('\n')
        
        for line in lines:
            # 查找包含测试ID和条件ID的行
            test_match = re.search(r'(\d+\.\d+(?:\.\d+)*)', line)
            cond_match = re.search(r'(C\d+)', line)
            
            if test_match and cond_match:
                test_id = test_match.group(1)
                condition_id = cond_match.group(1)
                
                mappings.append({
                    "test_id": test_id,
                    "condition_id": condition_id
                })
    
    print(f"  Found {len(mappings)} test-condition mappings")
    
    # 显示样本
    if mappings:
        print("  Sample mappings:")
        for mapping in mappings[:5]:
            print(f"    - Test {mapping['test_id']} → Condition {mapping['condition_id']}")
    
    return mappings


if __name__ == "__main__":
    data = extract_real_data()
    print("\n✅ Data preparation complete!")
    print("Next step: Implement calculation logic to verify PICS → TestPlan transformation")