#!/usr/bin/env python3
"""
完整采集所有 36.521 和 36.523 系列文档
提取测试用例、PICS定义和映射关系
"""

import asyncio
import json
from pathlib import Path
import sys
import re
from typing import List, Dict, Any
import time

# Add paths
sys.path.insert(0, "/Users/xenodennis/Documents/Fun/isA_MCP")
base_path = Path(__file__).parent.parent
sys.path.insert(0, str(base_path))

from services.parser.document_parser import DocumentParser
from services.extractor.dask_text_extractor import DaskTextExtractor

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Complete3GPPExtractor:
    """完整的3GPP文档提取器"""
    
    def __init__(self):
        self.parser = DocumentParser()
        self.ai_extractor = DaskTextExtractor(chunk_size=10000, overlap=1500)
        self.data_source = base_path / "data_source/3GPP"
        
        # 收集的数据
        self.all_test_cases = []
        self.all_pics_items = []
        self.pics_to_test_mappings = []
        
    async def extract_all_documents(self):
        """提取所有36.521和36.523系列文档"""
        
        # 定义要处理的文档
        documents_to_process = {
            # 测试规范 (-1 后缀，包含测试用例)
            "36.521-1": {
                "type": "test_spec",
                "paths": [
                    "TS 36.521-1/36521-1-i80/36521-1-i80_s06a-s06b4.docx",
                    "TS 36.521-1/36521-1-i80/36521-1-i80_s06c-s06e.docx",
                    "TS 36.521-1/36521-1-i80/36521-1-i80_s07_01.docx",
                    "TS 36.521-1/36521-1-i80/36521-1-i80_s08_01-08_05.docx",
                ]
            },
            "36.523-1": {
                "type": "test_spec",
                "paths": [
                    "TS 36.523-1/36523-1-i80/36523-1-i80_s06.docx",
                    "TS 36.523-1/36523-1-i80/36523-1-i80_s07_01.docx",
                    "TS 36.523-1/36523-1-i80/36523-1-i80_s08.docx",
                    "TS 36.523-1/36523-1-i80/36523-1-i80_s09_01.docx",
                ]
            },
            # PICS规范 (-2 后缀，包含PICS定义)
            "36.521-2": {
                "type": "pics_spec",
                "paths": [
                    "TS 36.521-2/36521-2-i80/36521-2-i80.docx",
                ]
            },
            "36.523-2": {
                "type": "pics_spec", 
                "paths": [
                    "TS 36.523-2/36523-2-i80/36523-2-i80.docx",
                ]
            }
        }
        
        # 初始化AI提取器
        logger.info("🤖 Initializing Dask AI extractor...")
        success = await self.ai_extractor.initialize_dask(workers=4, threads_per_worker=2)
        if not success:
            logger.error("Failed to initialize Dask")
            return
        
        try:
            # 处理每个文档系列
            for spec_name, spec_info in documents_to_process.items():
                logger.info(f"\n{'='*80}")
                logger.info(f"📚 Processing {spec_name} ({spec_info['type']})")
                logger.info(f"{'='*80}")
                
                for doc_path_str in spec_info['paths']:
                    doc_path = self.data_source / doc_path_str
                    if not doc_path.exists():
                        logger.warning(f"❌ Not found: {doc_path_str}")
                        continue
                    
                    logger.info(f"\n📄 Processing: {doc_path.name}")
                    
                    if spec_info['type'] == 'test_spec':
                        await self._extract_test_specification(doc_path, spec_name)
                    else:
                        await self._extract_pics_specification(doc_path, spec_name)
            
            # 保存结果
            self._save_results()
            
        finally:
            self.ai_extractor.close_dask()
            logger.info("\n✅ Extraction complete")
    
    async def _extract_test_specification(self, doc_path: Path, spec_name: str):
        """提取测试规范文档（包含测试用例）"""
        
        # 解析文档
        parsed_doc = self.parser.parse_document(str(doc_path))
        if not parsed_doc.success:
            logger.error(f"Failed to parse: {parsed_doc.error}")
            return
        
        content = parsed_doc.content
        logger.info(f"  Document length: {len(content)} chars")
        
        # 1. 使用正则提取测试用例
        test_pattern = r'(\d+\.\d+(?:\.\d+)*)\s+([^\n]{1,200})'
        test_matches = re.findall(test_pattern, content[:50000])  # 扫描前50k字符
        
        logger.info(f"  Found {len(test_matches)} potential test cases via regex")
        
        for test_id, test_name in test_matches[:100]:  # 处理前100个
            # 过滤掉明显不是测试用例的内容
            if len(test_id.split('.')) >= 3 and not test_name.startswith('The'):
                # 查找这个测试的PICS要求
                test_context_start = content.find(test_id)
                if test_context_start != -1:
                    test_context = content[test_context_start:test_context_start+5000]
                    
                    # 提取PICS要求
                    pics_patterns = [
                        r'PICS[:\s]+([A-Z]\.\d+[\./]\d+[-/]\d+(?:[,\s]+[A-Z]\.\d+[\./]\d+[-/]\d+)*)',
                        r'Applicability[:\s]+([^\n]+)',
                        r'Required PICS[:\s]+([^\n]+)',
                        r'applies to.*?([A-Z]\.\d+[\./]\d+[-/]\d+)',
                    ]
                    
                    required_pics = []
                    for pattern in pics_patterns:
                        matches = re.findall(pattern, test_context, re.IGNORECASE)
                        for match in matches:
                            # 解析PICS IDs
                            pics_ids = re.findall(r'[A-Z]\.\d+[\./]\d+[-/]\d+', match)
                            required_pics.extend(pics_ids)
                    
                    # 提取测试目的
                    purpose_match = re.search(r'Test Purpose.*?:?\s*(.{50,500})', test_context, re.IGNORECASE | re.DOTALL)
                    test_purpose = purpose_match.group(1).strip() if purpose_match else ""
                    
                    test_case = {
                        "test_id": test_id,
                        "test_name": test_name.strip(),
                        "specification": spec_name,
                        "required_pics": list(set(required_pics)),  # 去重
                        "test_purpose": test_purpose[:500],  # 限制长度
                        "source_doc": doc_path.name
                    }
                    
                    self.all_test_cases.append(test_case)
                    
                    # 创建映射关系
                    for pics_id in required_pics:
                        self.pics_to_test_mappings.append({
                            "pics_id": pics_id,
                            "test_id": test_id,
                            "specification": spec_name,
                            "requirement_type": "REQUIRED"
                        })
        
        # 2. 使用AI提取补充
        logger.info("  Running AI extraction...")
        
        # 为了效率，只处理文档的一部分
        sample_size = min(100000, len(content))  # 最多100k字符
        sample_content = content[:sample_size]
        
        extraction_schema = {
            "test_cases": """Extract test case IDs and names:
                Format: 7.1.1.1.1 Test Case Name
                Return: {"id": "7.1.1.1.1", "name": "Test Case Name"}""",
            
            "pics_requirements": """For each test, extract required PICS:
                Format: Test 7.1.1.1.1 requires PICS A.4.1-1/1, A.4.3/4
                Return: {"test_id": "7.1.1.1.1", "pics": ["A.4.1-1/1", "A.4.3/4"]}""",
            
            "test_purposes": """Extract test purpose descriptions:
                Return: {"test_id": "7.1.1.1.1", "purpose": "To verify..."}"""
        }
        
        ai_result = await self.ai_extractor.extract_3gpp_content_parallel(
            text=sample_content,
            confidence_threshold=0.6
        )
        
        if ai_result.success:
            logger.info(f"  AI found {len(ai_result.entities)} entities")
            
            # 处理AI结果
            for entity in ai_result.entities:
                if entity.get("entity_type") == "TEST_CASE":
                    text = entity.get("text", "")
                    # 解析测试ID和名称
                    id_match = re.match(r'(\d+\.\d+\.\d+(?:\.\d+)*)\s*(.*)', text)
                    if id_match:
                        test_id = id_match.group(1)
                        test_name = id_match.group(2).strip()
                        
                        # 检查是否已存在
                        if not any(tc["test_id"] == test_id for tc in self.all_test_cases):
                            self.all_test_cases.append({
                                "test_id": test_id,
                                "test_name": test_name,
                                "specification": spec_name,
                                "required_pics": [],
                                "source": "AI",
                                "confidence": entity.get("confidence", 0)
                            })
    
    async def _extract_pics_specification(self, doc_path: Path, spec_name: str):
        """提取PICS规范文档（包含PICS定义）"""
        
        parsed_doc = self.parser.parse_document(str(doc_path))
        if not parsed_doc.success:
            logger.error(f"Failed to parse: {parsed_doc.error}")
            return
        
        content = parsed_doc.content
        logger.info(f"  Document length: {len(content)} chars")
        
        # 提取PICS项
        # 格式: A.4.1-1/1 Description
        pics_pattern = r'([A-Z]\.\d+(?:[\./]\d+)*(?:[-/]\d+)?)\s+([^\n]{1,200})'
        pics_matches = re.findall(pics_pattern, content[:100000])
        
        logger.info(f"  Found {len(pics_matches)} potential PICS items")
        
        for pics_id, pics_desc in pics_matches[:500]:  # 处理前500个
            # 过滤掉明显不是PICS的内容
            if re.match(r'[A-Z]\.\d+', pics_id) and len(pics_desc) > 5:
                pics_item = {
                    "pics_id": pics_id,
                    "description": pics_desc.strip()[:200],
                    "specification": spec_name,
                    "source_doc": doc_path.name
                }
                
                # 避免重复
                if not any(p["pics_id"] == pics_id for p in self.all_pics_items):
                    self.all_pics_items.append(pics_item)
    
    def _save_results(self):
        """保存提取结果"""
        
        # 统计信息
        unique_test_ids = list(set(tc["test_id"] for tc in self.all_test_cases))
        unique_pics_ids = list(set(p["pics_id"] for p in self.all_pics_items))
        
        results = {
            "extraction_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_cases": self.all_test_cases,
            "pics_definitions": self.all_pics_items,
            "pics_to_test_mappings": self.pics_to_test_mappings,
            "summary": {
                "total_test_cases": len(self.all_test_cases),
                "unique_test_ids": len(unique_test_ids),
                "total_pics": len(self.all_pics_items),
                "unique_pics_ids": len(unique_pics_ids),
                "total_mappings": len(self.pics_to_test_mappings),
                "specs_processed": list(set(tc["specification"] for tc in self.all_test_cases))
            }
        }
        
        output_file = base_path / "outputs/complete_3gpp_extraction.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\n💾 Saved extraction results to: {output_file}")
        logger.info("\n📊 Extraction Summary:")
        logger.info(f"  - Test cases extracted: {len(self.all_test_cases)}")
        logger.info(f"  - Unique test IDs: {len(unique_test_ids)}")
        logger.info(f"  - PICS items extracted: {len(self.all_pics_items)}")
        logger.info(f"  - Unique PICS IDs: {len(unique_pics_ids)}")
        logger.info(f"  - PICS-Test mappings: {len(self.pics_to_test_mappings)}")
        
        # 显示样本
        if self.all_test_cases:
            logger.info("\n📋 Sample Test Cases:")
            for tc in self.all_test_cases[:5]:
                logger.info(f"  • {tc['test_id']}: {tc['test_name'][:50]}...")
                if tc['required_pics']:
                    logger.info(f"    PICS: {', '.join(tc['required_pics'][:3])}")
        
        if self.all_pics_items:
            logger.info("\n🔧 Sample PICS Items:")
            for pics in self.all_pics_items[:5]:
                logger.info(f"  • {pics['pics_id']}: {pics['description'][:50]}...")
        
        if self.pics_to_test_mappings:
            logger.info("\n🔗 Sample Mappings:")
            for mapping in self.pics_to_test_mappings[:5]:
                logger.info(f"  • {mapping['pics_id']} → Test {mapping['test_id']}")


async def main():
    """主函数"""
    logger.info("🚀 Starting complete 3GPP document extraction...")
    logger.info("Processing 36.521 and 36.523 series documents")
    
    extractor = Complete3GPPExtractor()
    await extractor.extract_all_documents()
    
    logger.info("\n✅ All done!")


if __name__ == "__main__":
    asyncio.run(main())