#!/usr/bin/env python3
"""
完整分析36.521-2文档结构
理解条件定义和映射关系
"""

import re
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, "/Users/xenodennis/Documents/Fun/isA_MCP")
base_path = Path(__file__).parent.parent
sys.path.insert(0, str(base_path))

from services.parser.document_parser import DocumentParser

def analyze_document_structure():
    """分析36.521-2文档的完整结构"""
    
    parser = DocumentParser()
    doc_path = base_path / "data_source/3GPP/TS 36.521-2/36521-2-i80/36521-2-i80.docx"
    
    print("📄 Parsing 36.521-2 document...")
    parsed_doc = parser.parse_document(str(doc_path))
    
    if not parsed_doc.success:
        print(f"Failed to parse: {parsed_doc.error}")
        return
    
    content = parsed_doc.content
    print(f"Document length: {len(content)} chars\n")
    
    # 1. 查找主要章节
    print("=" * 80)
    print("📚 DOCUMENT STRUCTURE")
    print("=" * 80)
    
    # 查找章节标题
    sections = []
    section_pattern = r'^(\d+(?:\.\d+)*)\s+([^\n]{1,100})'
    
    for match in re.finditer(section_pattern, content, re.MULTILINE):
        section_num = match.group(1)
        section_title = match.group(2).strip()
        
        # 只显示主要章节（1-2级）
        if len(section_num.split('.')) <= 2:
            sections.append((match.start(), section_num, section_title))
    
    print("\nMain sections:")
    for pos, num, title in sections[:20]:
        print(f"  {num}: {title}")
    
    # 2. 查找Table 4.1-1相关内容
    print("\n" + "=" * 80)
    print("📊 TABLE 4.1-1 ANALYSIS")
    print("=" * 80)
    
    # 查找Table 4.1-1
    table_41_pos = content.find("Table 4.1-1")
    if table_41_pos != -1:
        print(f"\n✅ Found Table 4.1-1 at position {table_41_pos}")
        
        # 提取表格后的内容（查找条件定义）
        table_section = content[table_41_pos:table_41_pos+5000]
        
        # 查找Applicability列
        if "Applicability" in table_section:
            print("✅ Table has Applicability column")
        
        # 查找Condition列
        if "Condition" in table_section:
            print("✅ Table has Condition column")
        
        # 显示表格的前几行
        print("\nTable header preview:")
        print("-" * 40)
        lines = table_section.split('\n')[:10]
        for line in lines:
            if line.strip():
                print(f"  {line[:100]}")
    
    # 3. 查找条件定义区域（在Table 4.1-1之后）
    print("\n" + "=" * 80)
    print("🔍 CONDITION DEFINITIONS")
    print("=" * 80)
    
    # 查找Table 4.1-1b（条件定义表）
    table_41b_pos = content.find("Table 4.1-1b")
    if table_41b_pos != -1:
        print(f"\n✅ Found Table 4.1-1b at position {table_41b_pos}")
        
        # 提取条件定义区域
        condition_section = content[table_41b_pos:table_41b_pos+30000]
        
        # 查找所有Cxxx条件
        conditions = {}
        
        # Pattern 1: Cxxx followed by condition
        pattern1 = r'(C\d+)\s*[:\s]+([^\n]{1,500})'
        matches1 = re.findall(pattern1, condition_section)
        
        print(f"\nFound {len(matches1)} condition definitions")
        
        # 显示前20个条件
        print("\nCondition definitions:")
        print("-" * 40)
        for i, (cond_id, definition) in enumerate(matches1[:20], 1):
            definition = definition.strip()
            
            # 检查是否包含IF-THEN逻辑
            if 'IF' in definition.upper():
                print(f"\n{i}. {cond_id}: [IF-THEN LOGIC]")
                print(f"   {definition[:200]}")
            else:
                print(f"\n{i}. {cond_id}:")
                print(f"   {definition[:100]}")
    
    # 4. 查找PICS引用（A.x.x格式）
    print("\n" + "=" * 80)
    print("🔗 PICS REFERENCES")
    print("=" * 80)
    
    # 在条件定义中查找PICS引用
    if table_41b_pos != -1:
        condition_section = content[table_41b_pos:table_41b_pos+50000]
        
        # 查找PICS引用
        pics_pattern = r'(A\.\d+(?:[/\-]\d+)*)'
        pics_refs = re.findall(pics_pattern, condition_section)
        unique_pics = list(set(pics_refs))
        
        print(f"\nFound {len(unique_pics)} unique PICS references in conditions")
        print("\nSample PICS references:")
        for pics in unique_pics[:20]:
            print(f"  - {pics}")
    
    # 5. 查找具体的IF-THEN-ELSE条件
    print("\n" + "=" * 80)
    print("⚡ IF-THEN-ELSE CONDITIONS")
    print("=" * 80)
    
    # 搜索整个文档中的IF-THEN条件
    if_then_pattern = r'(C\d+)[:\s]+.*?(IF.*?THEN.*?(?:ELSE.*?)?(?:C\d+|$))'
    if_then_matches = re.findall(if_then_pattern, content, re.IGNORECASE | re.DOTALL)
    
    if if_then_matches:
        print(f"\nFound {len(if_then_matches)} IF-THEN conditions")
        
        for i, (cond_id, logic) in enumerate(if_then_matches[:10], 1):
            # Clean up the logic string
            logic = ' '.join(logic.split())[:200]
            print(f"\n{i}. {cond_id}:")
            print(f"   {logic}")
    
    # 6. 查找Annex A（PICS定义）
    print("\n" + "=" * 80)
    print("📎 ANNEX A - PICS DEFINITIONS")
    print("=" * 80)
    
    annex_a_pos = content.find("Annex A")
    if annex_a_pos != -1:
        print(f"\n✅ Found Annex A at position {annex_a_pos}")
        
        # 提取Annex A的内容
        annex_section = content[annex_a_pos:annex_a_pos+10000]
        
        # 查找A.x.x格式的PICS项
        pics_items = re.findall(r'(A\.\d+(?:[/\-]\d+)*)\s+([^\n]{1,100})', annex_section)
        
        print(f"\nFound {len(pics_items)} PICS items in Annex A")
        print("\nSample PICS items:")
        for pics_id, desc in pics_items[:10]:
            print(f"  {pics_id}: {desc[:60]}")
    
    # 7. 总结
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    print("\n✨ Document Structure:")
    print(f"  - Total length: {len(content)} chars")
    print(f"  - Main sections found: {len(sections)}")
    print(f"  - Table 4.1-1 found: {'Yes' if table_41_pos != -1 else 'No'}")
    print(f"  - Table 4.1-1b found: {'Yes' if table_41b_pos != -1 else 'No'}")
    print(f"  - Annex A found: {'Yes' if annex_a_pos != -1 else 'No'}")
    
    if table_41b_pos != -1:
        print("\n✨ Conditions:")
        print(f"  - Condition definitions found: {len(matches1)}")
        print(f"  - IF-THEN conditions found: {len(if_then_matches)}")
        print(f"  - PICS references in conditions: {len(unique_pics)}")
    
    print("\n✨ Next Steps:")
    print("  1. Extract all condition definitions from Table 4.1-1b")
    print("  2. Parse IF-THEN-ELSE logic for each condition")
    print("  3. Map conditions to PICS items (A.x.x references)")
    print("  4. Store mappings in DuckDB for query")


if __name__ == "__main__":
    analyze_document_structure()