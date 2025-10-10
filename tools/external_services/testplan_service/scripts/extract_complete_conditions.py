#!/usr/bin/env python3
"""
完整提取36.521-2和36.523-2的条件定义
包括IF-THEN-ELSE逻辑和PICS映射
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

# Add paths
sys.path.insert(0, "/Users/xenodennis/Documents/Fun/isA_MCP")
base_path = Path(__file__).parent.parent
sys.path.insert(0, str(base_path))

from services.parser.document_parser import DocumentParser


@dataclass
class ConditionDefinition:
    """条件定义"""
    condition_id: str
    description: str
    if_clause: str
    then_value: str
    else_value: str
    pics_references: List[str]
    source_document: str


class CompleteConditionExtractor:
    """完整条件提取器"""
    
    def __init__(self):
        self.parser = DocumentParser()
        self.data_source = base_path / "data_source/3GPP"
        self.all_conditions: List[ConditionDefinition] = []
        
    def extract_all(self):
        """提取所有条件"""
        
        documents = [
            ("36.521-2", "TS 36.521-2/36521-2-i80/36521-2-i80.docx"),
            ("36.523-2", "TS 36.523-2/36523-2-i80/36523-2-i80.docx")
        ]
        
        for spec_name, doc_path_str in documents:
            doc_path = self.data_source / doc_path_str
            if doc_path.exists():
                print(f"\n{'='*80}")
                print(f"📄 Processing {spec_name}")
                print(f"{'='*80}")
                self._extract_from_document(doc_path, spec_name)
        
        # 保存结果
        self._save_results()
    
    def _extract_from_document(self, doc_path: Path, spec_name: str):
        """从文档提取条件"""
        
        parsed_doc = self.parser.parse_document(str(doc_path))
        if not parsed_doc.success:
            print(f"Failed to parse: {parsed_doc.error}")
            return
        
        content = parsed_doc.content
        print(f"Document length: {len(content)} chars")
        
        # 查找Table 4.1-1b位置（条件定义表）
        table_41b_pos = content.find("Table 4.1-1b")
        if table_41b_pos == -1:
            # 尝试其他模式
            table_41b_pos = content.find("Applicability")
            
        if table_41b_pos != -1:
            print(f"✅ Found condition definition area at position {table_41b_pos}")
            
            # 提取条件定义区域（最多200k字符）
            end_pos = min(table_41b_pos + 200000, len(content))
            condition_section = content[table_41b_pos:end_pos]
            
            # 提取条件定义
            self._extract_conditions(condition_section, spec_name)
    
    def _extract_conditions(self, text: str, source_doc: str):
        """从文本中提取条件定义"""
        
        # 多种模式匹配条件定义
        patterns = [
            # Pattern 1: Cxxx IF ... THEN ... ELSE ...
            r'(C\d+)\s*[:]*\s*IF\s+([^T]+?)\s+THEN\s+([RMO]|N/A)\s+ELSE\s+([^C\n]+)',
            
            # Pattern 2: Cxxx: IF ... THEN ... ELSE ... (with colon)
            r'(C\d+):\s*IF\s+([^T]+?)\s+THEN\s+([RMO]|N/A)\s+ELSE\s+([^C\n]+)',
            
            # Pattern 3: Multi-line format
            r'(C\d+)[:\s]+\n?\s*IF\s+([^T]+?)\s+THEN\s+([RMO]|N/A)\s+ELSE\s+([^C\n]+)',
        ]
        
        conditions_found = []
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                if len(match) == 4:
                    cond_id, if_clause, then_val, else_val = match
                    
                    # 清理值
                    cond_id = cond_id.strip()
                    if_clause = ' '.join(if_clause.split()).strip()
                    then_val = then_val.strip()
                    else_val = else_val.strip()
                    
                    # 提取PICS引用
                    pics_refs = re.findall(r'A\.\d+(?:[/\-]\d+)*', if_clause)
                    
                    # 创建条件定义
                    condition = ConditionDefinition(
                        condition_id=cond_id,
                        description=f"Condition {cond_id}",
                        if_clause=if_clause,
                        then_value=then_val,
                        else_value=else_val,
                        pics_references=pics_refs,
                        source_document=source_doc
                    )
                    
                    # 避免重复
                    if not any(c.condition_id == cond_id for c in conditions_found):
                        conditions_found.append(condition)
        
        print(f"✅ Extracted {len(conditions_found)} unique conditions")
        
        # 显示样本
        if conditions_found:
            print("\nSample conditions:")
            for cond in conditions_found[:5]:
                print(f"\n  {cond.condition_id}:")
                print(f"    IF: {cond.if_clause[:80]}...")
                print(f"    THEN: {cond.then_value}")
                print(f"    ELSE: {cond.else_value}")
                if cond.pics_references:
                    print(f"    PICS: {', '.join(cond.pics_references[:3])}")
        
        self.all_conditions.extend(conditions_found)
    
    def _save_results(self):
        """保存提取结果"""
        
        # 转换为可序列化格式
        conditions_dict = [asdict(c) for c in self.all_conditions]
        
        # 按条件ID分组
        conditions_by_id = {}
        for cond in self.all_conditions:
            if cond.condition_id not in conditions_by_id:
                conditions_by_id[cond.condition_id] = []
            conditions_by_id[cond.condition_id].append(asdict(cond))
        
        # 创建PICS到条件的映射
        pics_to_conditions = {}
        for cond in self.all_conditions:
            for pics in cond.pics_references:
                if pics not in pics_to_conditions:
                    pics_to_conditions[pics] = []
                if cond.condition_id not in pics_to_conditions[pics]:
                    pics_to_conditions[pics].append(cond.condition_id)
        
        results = {
            "extraction_type": "complete_condition_extraction",
            "total_conditions": len(self.all_conditions),
            "unique_condition_ids": len(conditions_by_id),
            "conditions": conditions_dict,
            "conditions_by_id": conditions_by_id,
            "pics_to_conditions": pics_to_conditions,
            "summary": {
                "total_extracted": len(self.all_conditions),
                "unique_conditions": len(conditions_by_id),
                "conditions_with_pics": len([c for c in self.all_conditions if c.pics_references]),
                "unique_pics_referenced": len(pics_to_conditions),
                "sample_condition_ids": list(conditions_by_id.keys())[:20]
            }
        }
        
        output_file = base_path / "outputs/complete_conditions.json"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Saved complete conditions to: {output_file}")
        
        # 显示总结
        print("\n" + "="*80)
        print("📊 EXTRACTION SUMMARY")
        print("="*80)
        print(f"  Total conditions extracted: {len(self.all_conditions)}")
        print(f"  Unique condition IDs: {len(conditions_by_id)}")
        print(f"  Conditions with PICS: {len([c for c in self.all_conditions if c.pics_references])}")
        print(f"  Unique PICS referenced: {len(pics_to_conditions)}")
        
        if pics_to_conditions:
            print("\n  Sample PICS mappings:")
            for pics, conds in list(pics_to_conditions.items())[:5]:
                print(f"    {pics} → {', '.join(conds[:3])}")
        
        # 创建实现文档
        self._create_implementation_doc()
    
    def _create_implementation_doc(self):
        """创建实现文档"""
        
        doc = """# Complete Condition Mapping Implementation

## Discovered Structure

### Condition Format
Each condition follows the pattern:
```
Cxxx: IF [PICS conditions] THEN [R/M/O] ELSE [N/A or other]
```

Where:
- **Cxxx**: Condition identifier (e.g., C01, C186)
- **PICS conditions**: Boolean expression using A.x.x-x/x format
- **R**: Required/Recommended
- **M**: Mandatory
- **O**: Optional
- **N/A**: Not Applicable

### Example Conditions
"""
        
        # Add sample conditions
        for cond in self.all_conditions[:5]:
            doc += f"""
**{cond.condition_id}**:
- IF: `{cond.if_clause}`
- THEN: `{cond.then_value}`
- ELSE: `{cond.else_value}`
- PICS: {', '.join(cond.pics_references) if cond.pics_references else 'None'}
"""
        
        doc += """

## Implementation Algorithm

```python
def evaluate_test_applicability(test_case, user_pics):
    '''Determine if a test case is applicable based on user's PICS'''
    
    # Get condition ID from test case (e.g., C186)
    condition_id = test_case.applicability_condition
    
    # Load condition definition
    condition = load_condition(condition_id)
    
    # Parse IF clause
    if_expression = parse_boolean_expression(condition.if_clause)
    
    # Evaluate against user's PICS
    if evaluate_expression(if_expression, user_pics):
        return condition.then_value  # R/M/O
    else:
        return condition.else_value  # N/A
```

## Next Steps

1. **Store in DuckDB**: Create tables for conditions and mappings
2. **Build Parser**: Parse boolean expressions in IF clauses
3. **Create Selector**: Implement test case selection logic
4. **Generate Test Plan**: Filter applicable tests based on user PICS
"""
        
        output_file = base_path / "docs/COMPLETE_CONDITION_IMPLEMENTATION.md"
        with open(output_file, 'w') as f:
            f.write(doc)
        
        print(f"\n📝 Created implementation doc: {output_file}")


def main():
    """主函数"""
    print("🚀 Starting complete condition extraction...")
    print("Extracting IF-THEN-ELSE conditions from 36.521-2 and 36.523-2")
    
    extractor = CompleteConditionExtractor()
    extractor.extract_all()
    
    print("\n✅ Extraction complete!")
    print("\nNext: Store in DuckDB and implement PICS test selector")


if __name__ == "__main__":
    main()