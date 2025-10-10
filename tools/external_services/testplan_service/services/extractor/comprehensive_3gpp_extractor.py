#!/usr/bin/env python3
"""
Comprehensive 3GPP Standards Extractor
全面提取所有3GPP标准并生成Interlab兼容的Excel模板

功能：
1. 自动发现并提取所有3GPP规范（-1, -2, -3, -4, -5等）
2. 生成与Interlab模板格式完全兼容的Excel文件
3. 支持test cases, conditions, PICS等多种数据提取
4. 提供详细的对比分析报告
"""

import logging
import pandas as pd
import numpy as np
import asyncio
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import re
import sys
import json
from datetime import datetime

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

# 导入现有的提取器
import importlib.util
spec = importlib.util.spec_from_file_location("gpp_2_docs_extractor", Path(__file__).parent / "3gpp-2-docs-extractor.py")
extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor_module)
ApplicabilityExtractor = extractor_module.ApplicabilityExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SpecificationData:
    """规范数据结构"""
    spec_id: str                    # 规范ID，如"36.521-2"
    spec_type: str                   # 类型：TS或TR
    spec_category: str               # 分类：-1, -2, -3等
    test_cases: List[Dict] = field(default_factory=list)
    c_conditions: List[Dict] = field(default_factory=list)
    pics_conditions: List[Dict] = field(default_factory=list)
    extraction_status: str = "pending"  # pending, success, failed, partial
    error_message: str = ""
    file_path: str = ""
    extraction_time: str = ""
    

@dataclass 
class ExtractionReport:
    """提取报告"""
    total_specs: int = 0
    successful_specs: int = 0
    failed_specs: int = 0
    partial_specs: int = 0
    total_test_cases: int = 0
    total_conditions: int = 0
    total_pics: int = 0
    specs_data: Dict[str, SpecificationData] = field(default_factory=dict)
    comparison_with_interlab: Dict = field(default_factory=dict)


class Comprehensive3GPPExtractor:
    """全面的3GPP标准提取器"""
    
    def __init__(self, data_source_path: str = "data_source/3GPP"):
        """
        初始化提取器
        
        Args:
            data_source_path: 3GPP数据源路径
        """
        self.data_source_path = Path(data_source_path)
        self.report = ExtractionReport()
        logger.info(f"Initialized Comprehensive3GPPExtractor with source: {self.data_source_path}")
    
    async def extract_all_standards(self) -> ExtractionReport:
        """
        提取所有3GPP标准
        
        Returns:
            ExtractionReport: 完整的提取报告
        """
        logger.info("🚀 Starting comprehensive 3GPP standards extraction...")
        
        # 1. 发现所有可用的3GPP规范
        available_specs = self._discover_specifications()
        self.report.total_specs = len(available_specs)
        logger.info(f"📁 Discovered {len(available_specs)} specifications")
        
        # 2. 批量提取所有规范
        for spec_id, spec_info in available_specs.items():
            logger.info(f"\n📄 Processing {spec_id}...")
            spec_data = await self._extract_specification(spec_id, spec_info)
            self.report.specs_data[spec_id] = spec_data
            
            # 更新统计
            if spec_data.extraction_status == "success":
                self.report.successful_specs += 1
                self.report.total_test_cases += len(spec_data.test_cases)
                self.report.total_conditions += len(spec_data.c_conditions)
                self.report.total_pics += len(spec_data.pics_conditions)
            elif spec_data.extraction_status == "partial":
                self.report.partial_specs += 1
                self.report.total_test_cases += len(spec_data.test_cases)
                self.report.total_conditions += len(spec_data.c_conditions)
                self.report.total_pics += len(spec_data.pics_conditions)
            else:
                self.report.failed_specs += 1
        
        # 3. 生成摘要
        self._generate_summary()
        
        return self.report
    
    def _discover_specifications(self) -> Dict[str, Dict]:
        """
        发现所有可用的3GPP规范
        
        Returns:
            Dict: 规范ID到规范信息的映射
        """
        specifications = {}
        
        # 查找所有TS和TR文件夹
        for spec_folder in sorted(self.data_source_path.glob("TS *")):
            if spec_folder.is_dir():
                spec_id = spec_folder.name.replace("TS ", "")
                spec_type = "TS"
                spec_category = self._categorize_spec(spec_id)
                
                # 查找文档文件
                doc_files = []
                for ext in ['*.docx', '*.doc']:
                    files = list(spec_folder.rglob(ext))
                    # 过滤临时文件
                    files = [f for f in files if not f.name.startswith('~$')]
                    doc_files.extend(files)
                
                if doc_files:
                    specifications[spec_id] = {
                        'type': spec_type,
                        'category': spec_category,
                        'folder': spec_folder,
                        'files': doc_files
                    }
        
        # 同样处理TR文件夹
        for spec_folder in sorted(self.data_source_path.glob("TR *")):
            if spec_folder.is_dir():
                spec_id = spec_folder.name.replace("TR ", "")
                spec_type = "TR"
                spec_category = "TR"
                
                doc_files = []
                for ext in ['*.docx', '*.doc']:
                    files = list(spec_folder.rglob(ext))
                    files = [f for f in files if not f.name.startswith('~$')]
                    doc_files.extend(files)
                
                if doc_files:
                    specifications[spec_id] = {
                        'type': spec_type,
                        'category': spec_category,
                        'folder': spec_folder,
                        'files': doc_files
                    }
        
        return specifications
    
    def _categorize_spec(self, spec_id: str) -> str:
        """
        分类规范
        
        Args:
            spec_id: 规范ID
            
        Returns:
            str: 规范类别
        """
        if '-1' in spec_id:
            return '-1'
        elif '-2' in spec_id:
            return '-2'
        elif '-3' in spec_id:
            return '-3'
        elif '-4' in spec_id:
            return '-4'
        elif '-5' in spec_id:
            return '-5'
        else:
            return 'base'
    
    async def _extract_specification(self, spec_id: str, spec_info: Dict) -> SpecificationData:
        """
        提取单个规范的数据
        
        Args:
            spec_id: 规范ID
            spec_info: 规范信息
            
        Returns:
            SpecificationData: 提取的规范数据
        """
        spec_data = SpecificationData(
            spec_id=spec_id,
            spec_type=spec_info['type'],
            spec_category=spec_info['category'],
            extraction_time=datetime.now().isoformat()
        )
        
        try:
            # 选择要处理的文件（通常选择第一个主文件）
            doc_file = self._select_main_file(spec_info['files'])
            if not doc_file:
                spec_data.extraction_status = "failed"
                spec_data.error_message = "No suitable document file found"
                return spec_data
            
            spec_data.file_path = str(doc_file)
            
            # 使用ApplicabilityExtractor提取
            logger.info(f"   Extracting from: {doc_file.name}")
            extractor = ApplicabilityExtractor(str(doc_file))
            result = await extractor.extract_all()
            
            if result:
                # 提取test cases
                test_cases = result.get('applicability', {}).get('test_cases', [])
                spec_data.test_cases = test_cases
                
                # 提取conditions
                if 'conditions' in result:
                    spec_data.c_conditions = result['conditions'].get('c_conditions', [])
                    spec_data.pics_conditions = result['conditions'].get('pics_conditions', [])
                
                # 判断提取状态
                if len(test_cases) > 0 or len(spec_data.c_conditions) > 0 or len(spec_data.pics_conditions) > 0:
                    spec_data.extraction_status = "success"
                    logger.info(f"   ✅ Extracted: {len(test_cases)} test cases, "
                              f"{len(spec_data.c_conditions)} C-conditions, "
                              f"{len(spec_data.pics_conditions)} PICS")
                else:
                    spec_data.extraction_status = "partial"
                    logger.warning(f"   ⚠️ No data extracted")
            else:
                spec_data.extraction_status = "failed"
                spec_data.error_message = "Extraction returned no result"
                logger.error(f"   ❌ Failed to extract")
                
        except Exception as e:
            spec_data.extraction_status = "failed"
            spec_data.error_message = str(e)[:200]
            logger.error(f"   ❌ Extraction failed: {str(e)[:100]}")
        
        return spec_data
    
    def _select_main_file(self, files: List[Path]) -> Optional[Path]:
        """
        选择主文档文件
        
        Args:
            files: 文件列表
            
        Returns:
            Optional[Path]: 选择的主文件
        """
        if not files:
            return None
        
        # 优先选择.docx文件
        docx_files = [f for f in files if f.suffix == '.docx']
        if docx_files:
            # 优先选择不包含特殊部分标记的文件
            main_files = [f for f in docx_files if not any(x in f.stem for x in ['_s', '_cover', '_annex'])]
            if main_files:
                return main_files[0]
            return docx_files[0]
        
        # 如果没有.docx，选择.doc文件
        doc_files = [f for f in files if f.suffix == '.doc']
        if doc_files:
            return doc_files[0]
        
        return files[0] if files else None
    
    def _generate_summary(self):
        """生成提取摘要"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 Extraction Summary:")
        logger.info(f"   Total specifications: {self.report.total_specs}")
        logger.info(f"   ✅ Successful: {self.report.successful_specs}")
        logger.info(f"   ⚠️ Partial: {self.report.partial_specs}")
        logger.info(f"   ❌ Failed: {self.report.failed_specs}")
        logger.info(f"   Total test cases: {self.report.total_test_cases}")
        logger.info(f"   Total conditions: {self.report.total_conditions}")
        logger.info(f"   Total PICS: {self.report.total_pics}")
    
    def generate_excel_template(self, output_path: str = "comprehensive_3gpp_template.xlsx"):
        """
        生成Excel模板（Interlab格式）
        
        Args:
            output_path: 输出文件路径
        """
        logger.info(f"\n📝 Generating comprehensive Excel template...")
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 1. 创建Overview工作表
            self._create_overview_sheet(writer)
            
            # 2. 创建Info工作表
            self._create_info_sheet(writer)
            
            # 3. 为每个成功提取的规范创建工作表
            for spec_id, spec_data in self.report.specs_data.items():
                if spec_data.extraction_status in ["success", "partial"]:
                    if spec_data.pics_conditions:  # 只为有PICS数据的规范创建sheet
                        sheet_name = f"3GPP {spec_data.spec_type} {spec_id}"
                        # Excel sheet名称限制31字符
                        if len(sheet_name) > 31:
                            sheet_name = sheet_name[:31]
                        self._create_spec_sheet(writer, sheet_name, spec_data)
        
        logger.info(f"✅ Excel template generated: {output_path}")
    
    def _create_overview_sheet(self, writer: pd.ExcelWriter):
        """创建Overview工作表"""
        overview_data = []
        
        # 添加说明文字
        overview_data.append([
            "Comprehensive 3GPP Standards Extraction Report\n\n"
            "This spreadsheet contains PICS data extracted from all available 3GPP standards. "
            "Generated by Comprehensive3GPPExtractor.",
            None,
            None
        ])
        
        overview_data.append(["Test Specification", "Status", "Extracted Data"])
        
        # 添加每个规范的状态
        for spec_id, spec_data in sorted(self.report.specs_data.items()):
            status_icon = "✅" if spec_data.extraction_status == "success" else "⚠️" if spec_data.extraction_status == "partial" else "❌"
            data_summary = f"{len(spec_data.test_cases)} tests, {len(spec_data.c_conditions)} conditions, {len(spec_data.pics_conditions)} PICS"
            overview_data.append([
                f"3GPP {spec_data.spec_type} {spec_id}",
                f"{status_icon} {spec_data.extraction_status}",
                data_summary
            ])
        
        overview_df = pd.DataFrame(overview_data)
        overview_df.to_excel(writer, sheet_name="Overview", index=False, header=False)
    
    def _create_info_sheet(self, writer: pd.ExcelWriter):
        """创建Info工作表"""
        info_data = [
            [None, None],
            ["Extraction Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["Total Specifications:", str(self.report.total_specs)],
            ["Successful Extractions:", str(self.report.successful_specs)],
            ["Total Test Cases:", str(self.report.total_test_cases)],
            ["Total Conditions:", str(self.report.total_conditions)],
            ["Total PICS:", str(self.report.total_pics)],
            ["Generator:", "Comprehensive3GPPExtractor v1.0"]
        ]
        
        info_df = pd.DataFrame(info_data)
        info_df.to_excel(writer, sheet_name="Info", index=False, header=False)
    
    def _create_spec_sheet(self, writer: pd.ExcelWriter, sheet_name: str, spec_data: SpecificationData):
        """为规范创建工作表（Interlab格式）"""
        # 创建完全匹配原始模板的数据结构
        all_rows = []
        
        # 第一行：Excel工作表标题行
        spec_name = f"3GPP {spec_data.spec_type} {spec_data.spec_id}"
        title_row = [np.nan, np.nan, spec_name, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
        all_rows.append(title_row)
        
        # 第二行：列标题行
        column_headers = ['Group', 'Group Description', 'Item', 'Description', 'Mnemonic', 'Value', 'Allowed\nSettings', 'Is Test Plan\nRelevant', 'Status', 'Response Details', 'FeatureID', 'ExternalFeatureGID', 'SupportedStartValue']
        all_rows.append(column_headers)
        
        # 数据行 - 转换PICS数据
        for pics in spec_data.pics_conditions:
            data_row = [
                f"Table {spec_data.spec_id}",  # Group
                "Feature group",                # Group Description
                pics.get('condition_id', ''),   # Item
                pics.get('definition', ''),     # Description
                None,                           # Mnemonic
                "FALSE",                        # Value
                "TRUE|FALSE",                   # Allowed Settings
                "TRUE",                         # Is Test Plan Relevant
                "Optional",                     # Status
                "",                            # Response Details
                str(uuid.uuid4()),             # FeatureID
                str(uuid.uuid4()),             # ExternalFeatureGID
                "FALSE"                        # SupportedStartValue
            ]
            all_rows.append(data_row)
        
        # 如果没有PICS但有test cases，也添加
        if not spec_data.pics_conditions and spec_data.test_cases:
            for test in spec_data.test_cases[:10]:  # 限制最多10个
                data_row = [
                    f"Tests",
                    "Test cases",
                    test.get('test_id', ''),
                    test.get('title', ''),
                    None,
                    "FALSE",
                    "TRUE|FALSE",
                    "TRUE",
                    "Optional",
                    "",
                    str(uuid.uuid4()),
                    str(uuid.uuid4()),
                    "FALSE"
                ]
                all_rows.append(data_row)
        
        # 创建DataFrame并写入
        final_df = pd.DataFrame(all_rows)
        final_df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
    
    def compare_with_interlab(self, interlab_path: str = "data_source/test_cases/Interlab_EVO_Feature_Spreadsheet_Template_All_20250920.xlsx"):
        """
        与Interlab模板对比
        
        Args:
            interlab_path: Interlab模板路径
        """
        logger.info("\n🔍 Comparing with Interlab template...")
        
        try:
            # 读取Interlab模板
            xl_file = pd.ExcelFile(interlab_path)
            interlab_sheets = xl_file.sheet_names
            
            # 获取Interlab中的3GPP规范
            interlab_3gpp_specs = []
            for sheet in interlab_sheets:
                if sheet.startswith('3GPP TS') or sheet.startswith('3GPP TR'):
                    spec_id = sheet.replace('3GPP TS ', '').replace('3GPP TR ', '')
                    interlab_3gpp_specs.append(spec_id)
            
            # 获取我们提取的规范
            our_specs = list(self.report.specs_data.keys())
            our_successful_specs = [spec_id for spec_id, data in self.report.specs_data.items() 
                                   if data.extraction_status in ["success", "partial"]]
            
            # 计算差异
            interlab_set = set(interlab_3gpp_specs)
            our_set = set(our_successful_specs)
            
            common_specs = interlab_set & our_set
            interlab_only = interlab_set - our_set
            our_only = our_set - interlab_set
            
            # 保存对比结果
            self.report.comparison_with_interlab = {
                'interlab_specs': interlab_3gpp_specs,
                'our_specs': our_successful_specs,
                'common_specs': list(common_specs),
                'interlab_only': list(interlab_only),
                'our_only': list(our_only),
                'coverage_rate': len(common_specs) / len(interlab_set) * 100 if interlab_set else 0
            }
            
            # 打印对比结果
            logger.info(f"\n📊 Comparison Results:")
            logger.info(f"   Interlab 3GPP specs: {len(interlab_3gpp_specs)}")
            logger.info(f"   Our extracted specs: {len(our_successful_specs)}")
            logger.info(f"   Common specs: {len(common_specs)}")
            logger.info(f"   Coverage rate: {self.report.comparison_with_interlab['coverage_rate']:.1f}%")
            
            if interlab_only:
                logger.info(f"\n   ❌ Specs in Interlab but not extracted ({len(interlab_only)}):")
                for spec in sorted(interlab_only):
                    logger.info(f"      - {spec}")
            
            if our_only:
                logger.info(f"\n   ➕ Additional specs we extracted ({len(our_only)}):")
                for spec in sorted(our_only)[:10]:  # 只显示前10个
                    logger.info(f"      - {spec}")
            
            return self.report.comparison_with_interlab
            
        except Exception as e:
            logger.error(f"Failed to compare with Interlab: {e}")
            return {}


async def main():
    """主程序"""
    logger.info("=" * 80)
    logger.info("🚀 Comprehensive 3GPP Standards Extraction")
    logger.info("=" * 80)
    
    # 创建提取器
    extractor = Comprehensive3GPPExtractor()
    
    # 执行全面提取
    report = await extractor.extract_all_standards()
    
    # 生成Excel模板
    output_file = "comprehensive_3gpp_template.xlsx"
    extractor.generate_excel_template(output_file)
    
    # 与Interlab模板对比
    comparison = extractor.compare_with_interlab()
    
    # 保存详细报告
    report_file = "extraction_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        report_dict = {
            'summary': {
                'total_specs': report.total_specs,
                'successful_specs': report.successful_specs,
                'failed_specs': report.failed_specs,
                'partial_specs': report.partial_specs,
                'total_test_cases': report.total_test_cases,
                'total_conditions': report.total_conditions,
                'total_pics': report.total_pics
            },
            'specs_details': {
                spec_id: {
                    'status': data.extraction_status,
                    'test_cases': len(data.test_cases),
                    'c_conditions': len(data.c_conditions),
                    'pics_conditions': len(data.pics_conditions),
                    'error': data.error_message
                }
                for spec_id, data in report.specs_data.items()
            },
            'comparison_with_interlab': comparison
        }
        json.dump(report_dict, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n✅ Extraction complete!")
    logger.info(f"   Excel template: {output_file}")
    logger.info(f"   Detailed report: {report_file}")
    
    return report


if __name__ == "__main__":
    asyncio.run(main())