#!/usr/bin/env python3
"""
从36.521-2和36.523-2文档中提取Applicability条件
寻找类似34.121-2的IF-THEN逻辑
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Add paths
sys.path.insert(0, "/Users/xenodennis/Documents/Fun/isA_MCP")
base_path = Path(__file__).parent.parent
sys.path.insert(0, str(base_path))

from services.parser.document_parser import DocumentParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ApplicabilityExtractor:
    """Applicability条件提取器"""
    
    def __init__(self):
        self.parser = DocumentParser()
        self.data_source = base_path / "data_source/3GPP"
        self.all_conditions = {}
        self.all_mappings = []
        
    def extract_from_36_series(self):
        """从36系列文档提取Applicability条件"""
        
        documents = [
            ("36.521-2", "TS 36.521-2/36521-2-i80/36521-2-i80.docx"),
            ("36.523-2", "TS 36.523-2/36523-2-i80/36523-2-i80.docx")
        ]
        
        for spec_name, doc_path_str in documents:
            doc_path = self.data_source / doc_path_str
            if not doc_path.exists():
                logger.warning(f"❌ Not found: {doc_path_str}")
                continue
                
            logger.info(f"\n{'='*80}")
            logger.info(f"📄 Processing {spec_name}: {doc_path.name}")
            logger.info(f"{'='*80}")
            
            self._extract_from_document(doc_path, spec_name)
        
        # 保存结果
        self._save_results()
    
    def _extract_from_document(self, doc_path: Path, spec_name: str):
        """从单个文档提取条件"""
        
        parsed_doc = self.parser.parse_document(str(doc_path))
        if not parsed_doc.success:
            logger.error(f"Failed to parse: {parsed_doc.error}")
            return
        
        content = parsed_doc.content
        logger.info(f"Document length: {len(content)} chars")
        
        # 1. 查找Applicability表格
        table_patterns = [
            r'Table.*Applicability',
            r'Applicability.*Table',
            r'Table\s+\w+[:\s]+Applicability',
            r'Annex.*Applicability.*conditions',
            r'A\.\d+.*Applicability'
        ]
        
        table_positions = []
        for pattern in table_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                table_positions.append((match.start(), match.group()))
        
        logger.info(f"Found {len(table_positions)} potential Applicability tables")
        
        # 2. 提取每个表格区域的条件
        conditions_found = []
        
        for pos, table_name in table_positions[:5]:  # 处理前5个表格
            logger.info(f"\n📋 Analyzing table at position {pos}: {table_name}")
            
            # 提取表格内容（接下来的5000字符）
            table_content = content[pos:pos+5000]
            
            # 查找IF-THEN条件
            # 模式1: C_xxx IF ... THEN ... ELSE ...
            pattern1 = r'(C_[A-Z0-9]+)\s+IF\s+([^T]+?)\s+THEN\s+([RMO])\s+ELSE\s+([^\n]+)'
            matches1 = re.findall(pattern1, table_content, re.IGNORECASE)
            
            # 模式2: Cxxx: IF ... THEN ... ELSE ...
            pattern2 = r'(C\d+)[:\s]+IF\s+([^T]+?)\s+THEN\s+([RMO])\s+ELSE\s+([^\n]+)'
            matches2 = re.findall(pattern2, table_content, re.IGNORECASE)
            
            # 模式3: 条件引用 (e.g., A.4.1-1/1)
            pattern3 = r'([A-Z]\.\d+(?:[/\-]\d+)+)\s+[^\n]{0,100}?(?:IF|THEN|condition)'
            matches3 = re.findall(pattern3, table_content, re.IGNORECASE)
            
            logger.info(f"  Pattern 1 (C_xxx): {len(matches1)} matches")
            logger.info(f"  Pattern 2 (Cxxx): {len(matches2)} matches")
            logger.info(f"  Pattern 3 (PICS refs): {len(matches3)} matches")
            
            # 处理找到的条件
            for match in matches1 + matches2:
                if len(match) == 4:
                    cond_id, condition, then_val, else_val = match
                    conditions_found.append({
                        "condition_id": cond_id.strip(),
                        "if_condition": condition.strip(),
                        "then_value": then_val.strip(),
                        "else_value": else_val.strip(),
                        "source": spec_name,
                        "table": table_name
                    })
        
        # 3. 在整个文档中查找条件定义
        logger.info("\n🔍 Searching for conditions in entire document...")
        
        # 查找所有Cxxx格式的条件
        all_c_conditions = re.findall(r'(C\d+)[:\s]+([^\n]{1,200})', content)
        logger.info(f"Found {len(all_c_conditions)} Cxxx conditions")
        
        # 查找所有C_xxx格式的条件
        all_c_underscore = re.findall(r'(C_[A-Z0-9]+)[:\s]+([^\n]{1,200})', content)
        logger.info(f"Found {len(all_c_underscore)} C_xxx conditions")
        
        # 4. 查找PICS项引用
        pics_patterns = [
            r'([A-Z]\.\d+[/\-]\d+(?:[/\-]\d+)?)',  # A.4.1-1/1格式
            r'PICS[:\s]+([^\n]+)',  # PICS: 后面的内容
            r'Required PICS[:\s]+([^\n]+)'  # Required PICS: 后面的内容
        ]
        
        all_pics_refs = []
        for pattern in pics_patterns:
            matches = re.findall(pattern, content[:50000])  # 扫描前50k字符
            all_pics_refs.extend(matches)
        
        unique_pics = list(set([ref for ref in all_pics_refs if re.match(r'[A-Z]\.\d+', ref)]))
        logger.info(f"Found {len(unique_pics)} unique PICS references")
        
        # 5. 查找测试条件映射
        # 模式: Test x.x.x.x requires condition Cxxx
        test_condition_pattern = r'(\d+\.\d+(?:\.\d+)*)[^\n]{0,200}?(?:condition|requires|applicable)\s+(C\d+|C_[A-Z0-9]+)'
        test_conditions = re.findall(test_condition_pattern, content, re.IGNORECASE)
        logger.info(f"Found {len(test_conditions)} test-condition mappings")
        
        # 保存到类变量
        self.all_conditions[spec_name] = {
            "if_then_conditions": conditions_found,
            "c_conditions": all_c_conditions[:50],
            "c_underscore_conditions": all_c_underscore[:50],
            "pics_references": unique_pics[:50],
            "test_conditions": test_conditions[:50]
        }
    
    def _save_results(self):
        """保存提取结果"""
        
        results = {
            "extraction_type": "36_series_applicability",
            "documents_processed": list(self.all_conditions.keys()),
            "conditions_by_document": self.all_conditions,
            "summary": {
                "total_if_then_conditions": sum(
                    len(doc["if_then_conditions"]) 
                    for doc in self.all_conditions.values()
                ),
                "total_c_conditions": sum(
                    len(doc["c_conditions"]) 
                    for doc in self.all_conditions.values()
                ),
                "total_pics_refs": sum(
                    len(doc["pics_references"]) 
                    for doc in self.all_conditions.values()
                ),
                "total_test_conditions": sum(
                    len(doc["test_conditions"]) 
                    for doc in self.all_conditions.values()
                )
            }
        }
        
        output_file = base_path / "outputs/36_series_applicability.json"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\n💾 Saved results to: {output_file}")
        
        # 显示摘要
        logger.info("\n📊 Extraction Summary:")
        for doc_name, doc_data in self.all_conditions.items():
            logger.info(f"\n{doc_name}:")
            logger.info(f"  - IF-THEN conditions: {len(doc_data['if_then_conditions'])}")
            logger.info(f"  - C conditions: {len(doc_data['c_conditions'])}")
            logger.info(f"  - C_ conditions: {len(doc_data['c_underscore_conditions'])}")
            logger.info(f"  - PICS references: {len(doc_data['pics_references'])}")
            logger.info(f"  - Test conditions: {len(doc_data['test_conditions'])}")
            
            if doc_data['if_then_conditions']:
                logger.info(f"\n  ✨ Found IF-THEN conditions!")
                for cond in doc_data['if_then_conditions'][:3]:
                    logger.info(f"    • {cond['condition_id']}: IF {cond['if_condition']} THEN {cond['then_value']}")
        
        # 创建映射文档
        self._create_mapping_document()
    
    def _create_mapping_document(self):
        """创建映射文档，总结发现的条件"""
        
        doc_content = """# 36 Series Applicability Conditions

## Key Findings

### IF-THEN Conditions Found
"""
        
        for doc_name, doc_data in self.all_conditions.items():
            if doc_data['if_then_conditions']:
                doc_content += f"\n#### {doc_name}\n"
                for cond in doc_data['if_then_conditions']:
                    doc_content += f"- **{cond['condition_id']}**: IF {cond['if_condition']} THEN {cond['then_value']} ELSE {cond['else_value']}\n"
        
        doc_content += """

### Implementation Plan

1. **Extract Conditions**: Parse all C_xxx and Cxxx conditions from PICS documents
2. **Map to PICS Items**: Link conditions to PICS features (A.x.x-x/x format)
3. **Map to Tests**: Link conditions to test cases
4. **Build Logic Engine**: Implement IF-THEN evaluator

### Example Usage

```python
def evaluate_pics_condition(condition, user_pics):
    '''Evaluate if a condition is met based on user's PICS'''
    
    # Parse condition: "IF A.7/9 OR A.7/10 THEN R ELSE N/A"
    if_part = extract_if_part(condition)  # "A.7/9 OR A.7/10"
    then_part = extract_then_part(condition)  # "R"
    else_part = extract_else_part(condition)  # "N/A"
    
    # Evaluate boolean expression
    if evaluate_expression(if_part, user_pics):
        return then_part  # Required
    else:
        return else_part  # Not Applicable
```
"""
        
        output_file = base_path / "docs/36_SERIES_APPLICABILITY.md"
        with open(output_file, 'w') as f:
            f.write(doc_content)
        
        logger.info(f"📝 Created mapping document: {output_file}")


def main():
    """主函数"""
    logger.info("🚀 Starting 36 series Applicability extraction...")
    logger.info("Looking for IF-THEN conditions similar to 34.121-2")
    
    extractor = ApplicabilityExtractor()
    extractor.extract_from_36_series()
    
    logger.info("\n✅ Extraction complete!")
    logger.info("Next steps:")
    logger.info("1. Parse and store conditions in DuckDB")
    logger.info("2. Build logic engine for IF-THEN evaluation")
    logger.info("3. Create PICS to Test Plan selector")


if __name__ == "__main__":
    main()