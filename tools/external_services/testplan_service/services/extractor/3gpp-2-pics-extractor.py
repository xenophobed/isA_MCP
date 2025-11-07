#!/usr/bin/env python3
"""
Enhanced 3GPP-2 PICS Extractor for Interlab Excel Template Generation

这个服务从3GPP -2文档中提取PICS数据，并生成Interlab Excel模板格式
参考文件：Interlab_EVO_Feature_Spreadsheet_Template_All_20250920.xlsx

功能：
1. 从3GPP -2文档的PICS表格中提取结构化数据
2. 转换为Interlab Excel模板格式
3. 支持多个3GPP -2规范（34.121-2, 34.123-2, 34.229-2, 36.521-2, 36.523-2, 38.508-2）
4. 生成完整的Excel工作簿，包含所有必要的工作表和格式
"""

import logging
import pandas as pd
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import re
import sys

# 导入现有的3GPP-2文档提取器
import importlib.util
spec = importlib.util.spec_from_file_location("gpp_2_docs_extractor", Path(__file__).parent / "3gpp-2-docs-extractor.py")
extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor_module)
ApplicabilityExtractor = extractor_module.ApplicabilityExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PICSItem:
    """PICS项目数据结构 - 适配Interlab格式"""
    group: str                    # 表格组名，如"Table A.4.1-1"
    group_description: str        # 组描述，如"UE Radio Technologies"
    item: str                     # PICS项目ID，如"A.4.1-1/1"
    description: str              # 功能描述
    mnemonic: Optional[str] = None        # 助记符
    value: str = "FALSE"                  # 默认值
    allowed_settings: str = "TRUE|FALSE"  # 允许的设置
    is_test_plan_relevant: str = "TRUE"   # 是否与测试计划相关
    status: str = "Optional"              # 状态
    response_details: str = ""            # 响应详情
    feature_id: str = ""                  # 功能ID（UUID）
    external_feature_gid: str = ""       # 外部功能组ID（UUID）
    supported_start_value: str = "FALSE" # 支持的起始值
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'Group': self.group,
            'Group Description': self.group_description,
            'Item': self.item,
            'Description': self.description,
            'Mnemonic': self.mnemonic,
            'Value': self.value,
            'Allowed\nSettings': self.allowed_settings,
            'Is Test Plan\nRelevant': self.is_test_plan_relevant,
            'Status': self.status,
            'Response Details': self.response_details,
            'FeatureID': self.feature_id,
            'ExternalFeatureGID': self.external_feature_gid,
            'SupportedStartValue': self.supported_start_value
        }


@dataclass
class SpecificationPICS:
    """规范的PICS数据"""
    spec_name: str
    spec_version: str
    pics_items: List[PICSItem]
    extraction_metadata: Dict = field(default_factory=dict)


class Enhanced3GPP2PICSExtractor:
    """增强的3GPP-2 PICS提取器 - 生成Interlab Excel模板"""
    
    def __init__(self):
        """初始化提取器"""
        self.supported_specs = {
            '34.121-2': 'TS 34.121-2',
            '34.123-2': 'TS 34.123-2', 
            '34.229-2': 'TS 34.229-2',
            '36.521-2': 'TS 36.521-2',
            '36.523-2': 'TS 36.523-2',
            '38.508-2': 'TS 38.508-2'
        }
        
        self.data_source_base = Path("data_source/3GPP")
        logger.info(f"Initialized Enhanced3GPP2PICSExtractor for {len(self.supported_specs)} specifications")
    
    def extract_all_specs_to_excel(self, output_path: str = "generated_interlab_template.xlsx") -> Dict[str, Any]:
        """
        提取所有支持的3GPP -2规范并生成Interlab Excel模板
        
        Args:
            output_path: 输出Excel文件路径
            
        Returns:
            Dict: 提取结果摘要
        """
        logger.info("🚀 Starting enhanced PICS extraction for all 3GPP -2 specifications...")
        
        all_spec_data = {}
        extraction_summary = {
            'total_specs_processed': 0,
            'total_pics_items': 0,
            'successful_specs': [],
            'failed_specs': [],
            'output_file': output_path
        }
        
        # 1. 提取每个规范的PICS数据
        for spec_id, spec_name in self.supported_specs.items():
            logger.info(f"\n📄 Processing {spec_name} ({spec_id})...")
            
            try:
                spec_pics = self._extract_spec_pics(spec_id, spec_name)
                if spec_pics and spec_pics.pics_items:
                    all_spec_data[spec_id] = spec_pics
                    extraction_summary['total_pics_items'] += len(spec_pics.pics_items)
                    extraction_summary['successful_specs'].append(spec_id)
                    logger.info(f"✅ Extracted {len(spec_pics.pics_items)} PICS items from {spec_name}")
                else:
                    logger.warning(f"⚠️ No PICS items extracted from {spec_name}")
                    extraction_summary['failed_specs'].append(spec_id)
                    
            except Exception as e:
                logger.error(f"❌ Failed to extract {spec_name}: {e}")
                extraction_summary['failed_specs'].append(spec_id)
        
        extraction_summary['total_specs_processed'] = len(extraction_summary['successful_specs'])
        
        # 2. 生成Excel模板
        if all_spec_data:
            logger.info(f"\n📊 Generating Interlab Excel template with {extraction_summary['total_pics_items']} total PICS items...")
            self._generate_interlab_excel(all_spec_data, output_path)
            logger.info(f"✅ Excel template generated: {output_path}")
        else:
            logger.error("❌ No PICS data extracted, cannot generate Excel template")
        
        # 3. 输出摘要
        logger.info(f"\n🎯 Extraction Summary:")
        logger.info(f"   Processed specs: {extraction_summary['total_specs_processed']}/{len(self.supported_specs)}")
        logger.info(f"   Total PICS items: {extraction_summary['total_pics_items']}")
        logger.info(f"   Successful: {extraction_summary['successful_specs']}")
        if extraction_summary['failed_specs']:
            logger.info(f"   Failed: {extraction_summary['failed_specs']}")
        
        return extraction_summary
    
    def _extract_spec_pics(self, spec_id: str, spec_name: str) -> Optional[SpecificationPICS]:
        """
        提取单个规范的PICS数据
        
        Args:
            spec_id: 规范ID，如"36.521-2"
            spec_name: 规范名称，如"TS 36.521-2"
            
        Returns:
            SpecificationPICS: 提取的PICS数据，如果失败则返回None
        """
        # 查找规范文档
        spec_folders = list(self.data_source_base.glob(f"TS {spec_id}"))
        
        if not spec_folders:
            # 尝试其他可能的命名模式
            spec_folders = list(self.data_source_base.glob(f"*{spec_id}*"))
        
        if not spec_folders:
            logger.warning(f"Cannot find folder for {spec_name}")
            return None
        
        spec_folder = spec_folders[0]
        logger.info(f"   Found spec folder: {spec_folder}")
        
        # 查找文档文件，过滤掉临时文件
        doc_files = []
        for pattern in ['*.docx', '*.doc']:
            files = list(spec_folder.rglob(pattern))
            # 过滤掉临时文件（以~$开头）
            files = [f for f in files if not f.name.startswith('~$')]
            doc_files.extend(files)
        
        if not doc_files:
            logger.warning(f"No documents found in {spec_folder}")
            return None
        
        # 使用第一个找到的文档
        doc_file = doc_files[0]
        logger.info(f"   Using document: {doc_file.name}")
        
        try:
            # 使用现有的ApplicabilityExtractor提取PICS数据
            extractor = ApplicabilityExtractor(str(doc_file))
            
            # 使用异步调用
            import asyncio
            extraction_result = asyncio.run(extractor.extract_all())
            
            if not extraction_result:
                logger.warning(f"No extraction result from {doc_file}")
                return None
            
            # 转换为Enhanced PICS格式
            pics_items = self._convert_to_enhanced_pics(extraction_result, spec_id, spec_name)
            
            spec_pics = SpecificationPICS(
                spec_name=spec_name,
                spec_version=spec_id,
                pics_items=pics_items,
                extraction_metadata={
                    'source_document': str(doc_file),
                    'extraction_date': pd.Timestamp.now().isoformat(),
                    'original_pics_count': len(extraction_result.get('conditions', {}).get('pics_conditions', [])),
                    'enhanced_pics_count': len(pics_items)
                }
            )
            
            return spec_pics
            
        except Exception as e:
            logger.error(f"Failed to extract PICS from {doc_file}: {e}")
            return None
    
    def _convert_to_enhanced_pics(self, extraction_result: Dict, spec_id: str, spec_name: str) -> List[PICSItem]:
        """
        将现有的PICS提取结果转换为增强的PICS格式
        
        Args:
            extraction_result: 来自ApplicabilityExtractor的提取结果
            spec_id: 规范ID
            spec_name: 规范名称
            
        Returns:
            List[PICSItem]: 转换后的PICS项目列表
        """
        pics_items = []
        
        # 获取PICS条件数据
        pics_conditions = extraction_result.get('conditions', {}).get('pics_conditions', [])
        
        for pics_condition in pics_conditions:
            # 解析PICS项目数据
            condition_id = pics_condition.get('condition_id', '')
            definition = pics_condition.get('definition', '')
            
            # 从condition_id推断group和item
            group, item = self._parse_pics_id(condition_id)
            
            # 生成UUID
            feature_id = str(uuid.uuid4())
            external_feature_gid = str(uuid.uuid4())
            
            # 推断mnemonic（如果definition中包含）
            mnemonic = self._extract_mnemonic(definition)
            
            # 推断status（基于规范和项目类型）
            status = self._infer_status(condition_id, definition)
            
            # 推断supported_start_value（基于项目类型）
            supported_start_value = self._infer_supported_start_value(condition_id, definition)
            
            pics_item = PICSItem(
                group=group,
                group_description=self._get_group_description(group, spec_id),
                item=item,
                description=definition,
                mnemonic=mnemonic,
                value="FALSE",  # 默认值
                allowed_settings="TRUE|FALSE",
                is_test_plan_relevant="TRUE",
                status=status,
                response_details="",
                feature_id=feature_id,
                external_feature_gid=external_feature_gid,
                supported_start_value=supported_start_value
            )
            
            pics_items.append(pics_item)
        
        return pics_items
    
    def _parse_pics_id(self, condition_id: str) -> Tuple[str, str]:
        """
        解析PICS ID以提取group和item
        
        Args:
            condition_id: PICS条件ID，如"A.4.1-1/1"
            
        Returns:
            Tuple[str, str]: (group, item)
        """
        if not condition_id:
            return "Unknown", "Unknown"
        
        # 尝试匹配标准PICS ID格式
        match = re.match(r'(A\.\d+(?:\.\d+)*(?:-\d+)?)', condition_id)
        if match:
            base_id = match.group(1)
            # 推断表格名称
            group = f"Table {base_id}"
            item = condition_id
            return group, item
        
        # 如果是PC_开头的条件
        if condition_id.startswith('PC_'):
            return "Protocol Conditions", condition_id
        
        # 其他格式
        return "Other Conditions", condition_id
    
    def _extract_mnemonic(self, definition: str) -> Optional[str]:
        """
        从定义中提取mnemonic（助记符）
        
        Args:
            definition: 功能定义字符串
            
        Returns:
            Optional[str]: 提取的mnemonic，如果没有则返回None
        """
        if not definition:
            return None
        
        # 寻找常见的mnemonic模式
        mnemonic_patterns = [
            r'pc_(\w+)',
            r'mnemonic[:\s]+(\w+)',
            r'\((\w+)\)',
        ]
        
        for pattern in mnemonic_patterns:
            match = re.search(pattern, definition, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _infer_status(self, condition_id: str, definition: str) -> str:
        """
        推断PICS项目的状态
        
        Args:
            condition_id: PICS条件ID
            definition: 功能定义
            
        Returns:
            str: 推断的状态（Mandatory, Optional等）
        """
        definition_lower = definition.lower() if definition else ""
        
        if any(keyword in definition_lower for keyword in ['mandatory', 'shall', 'required']):
            return "Mandatory"
        elif any(keyword in definition_lower for keyword in ['optional', 'may']):
            return "Optional"
        else:
            return "Optional"  # 默认为Optional
    
    def _infer_supported_start_value(self, condition_id: str, definition: str) -> str:
        """
        推断支持的起始值
        
        Args:
            condition_id: PICS条件ID
            definition: 功能定义
            
        Returns:
            str: 推断的起始值（TRUE或FALSE）
        """
        definition_lower = definition.lower() if definition else ""
        
        # 基于定义内容推断
        if any(keyword in definition_lower for keyword in ['mandatory', 'default', 'basic']):
            return "TRUE"
        else:
            return "FALSE"
    
    def _get_group_description(self, group: str, spec_id: str) -> str:
        """
        获取组描述
        
        Args:
            group: 组名称
            spec_id: 规范ID
            
        Returns:
            str: 组描述
        """
        # 基于组名称和规范ID推断描述
        group_descriptions = {
            "Table A.0": "UE Release information",
            "Table A.1": "UE Radio Technologies",
            "Table A.2": "Roles",
            "Table A.3": "UE capabilities",
            "Table A.4": "RF capabilities",
            "Protocol Conditions": "Protocol-specific conditions",
            "Other Conditions": "Other conditions"
        }
        
        # 查找匹配的描述
        for key, desc in group_descriptions.items():
            if key in group:
                return desc
        
        return "Feature group"  # 默认描述
    
    def _generate_interlab_excel(self, all_spec_data: Dict[str, SpecificationPICS], output_path: str):
        """
        生成Interlab Excel模板
        
        Args:
            all_spec_data: 所有规范的PICS数据
            output_path: 输出文件路径
        """
        logger.info("📝 Creating Interlab Excel template...")
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 1. 创建Overview工作表
            self._create_overview_sheet(writer, all_spec_data)
            
            # 2. 创建Info工作表
            self._create_info_sheet(writer)
            
            # 3. 为每个规范创建工作表
            for spec_id, spec_pics in all_spec_data.items():
                sheet_name = f"3GPP {spec_pics.spec_name}"
                self._create_spec_sheet(writer, sheet_name, spec_pics)
        
        logger.info(f"✅ Excel template created with {len(all_spec_data)} specification sheets")
    
    def _create_overview_sheet(self, writer: pd.ExcelWriter, all_spec_data: Dict[str, SpecificationPICS]):
        """创建Overview工作表"""
        overview_data = []
        
        overview_data.append([
            "The purpose of this Feature Spreadsheet is to import product features into InterLab to describe an Object Under Test and create a device-specific test plan. Enter 'TRUE' or 'FALSE' in the value field to indicate support of a specific feature. Values for some features are enumerated types. The Allowed Values column indicates the expected values. Each individual worksheets represent one specification (as shown in the table below) which contains Features / Requirements / PICS / PIXIT.\n\nIt is strongly recommended not change the format of this document. Template Version: 1.2.1 (Generated)",
            None,
            None
        ])
        
        overview_data.append(["Test Specification", "Release", "Comments"])
        
        for spec_id, spec_pics in all_spec_data.items():
            overview_data.append([
                f"3GPP {spec_pics.spec_name}",
                "Latest",
                f"Generated from 3GPP documents ({len(spec_pics.pics_items)} PICS items)"
            ])
        
        overview_df = pd.DataFrame(overview_data, columns=["Feature Spreadsheet Overview", "Unnamed: 1", "Unnamed: 2"])
        overview_df.to_excel(writer, sheet_name="Overview", index=False)
    
    def _create_info_sheet(self, writer: pd.ExcelWriter):
        """创建Info工作表"""
        info_data = [
            [None, None],
            ["Project Name:", "Generated 3GPP PICS"],
            ["Generated By:", "Enhanced 3GPP-2 PICS Extractor"],
            ["Generation Date:", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["Version:", "1.0"]
        ]
        
        info_df = pd.DataFrame(info_data, columns=["Unnamed: 0", "Feature Spreadsheet Info"])
        info_df.to_excel(writer, sheet_name="Info", index=False)
    
    def _create_spec_sheet(self, writer: pd.ExcelWriter, sheet_name: str, spec_pics: SpecificationPICS):
        """为规范创建工作表（完全匹配原始模板格式）"""
        import numpy as np
        
        # 提取规范名称
        spec_name_col = sheet_name.split(' ')[-1]  # 如"36.521-2"
        
        # 创建完全匹配原始模板的数据结构
        all_rows = []
        
        # 第一行：Excel工作表标题行（与原始模板完全一致）
        title_row = [np.nan, np.nan, f'3GPP TS {spec_name_col}', np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
        all_rows.append(title_row)
        
        # 第二行：列标题行
        column_headers = ['Group', 'Group Description', 'Item', 'Description', 'Mnemonic', 'Value', 'Allowed\nSettings', 'Is Test Plan\nRelevant', 'Status', 'Response Details', 'FeatureID', 'ExternalFeatureGID', 'SupportedStartValue']
        all_rows.append(column_headers)
        
        # 数据行
        if spec_pics.pics_items:
            for pics_item in spec_pics.pics_items:
                data_row = [
                    pics_item.group,
                    pics_item.group_description,
                    pics_item.item,
                    pics_item.description,
                    pics_item.mnemonic,
                    pics_item.value,
                    pics_item.allowed_settings,
                    pics_item.is_test_plan_relevant,
                    pics_item.status,
                    pics_item.response_details,
                    pics_item.feature_id,
                    pics_item.external_feature_gid,
                    pics_item.supported_start_value
                ]
                all_rows.append(data_row)
        
        # 创建DataFrame（无列名）
        final_df = pd.DataFrame(all_rows)
        
        # 写入Excel（无标题，无索引）
        final_df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
        
        if spec_pics.pics_items:
            logger.info(f"   Created sheet '{sheet_name}' with {len(spec_pics.pics_items)} PICS items (perfect format match)")
        else:
            logger.warning(f"   Created empty sheet '{sheet_name}' (perfect format match)")


def main():
    """主程序入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced 3GPP-2 PICS Extractor for Interlab Templates')
    parser.add_argument('--output', '-o', default='generated_interlab_template.xlsx', 
                       help='Output Excel file path (default: generated_interlab_template.xlsx)')
    parser.add_argument('--specs', nargs='+', help='Specific specs to extract (e.g., 36.521-2 36.523-2)')
    
    args = parser.parse_args()
    
    # 创建提取器
    extractor = Enhanced3GPP2PICSExtractor()
    
    # 如果指定了特定规范，限制处理范围
    if args.specs:
        original_specs = extractor.supported_specs.copy()
        extractor.supported_specs = {spec: original_specs[spec] for spec in args.specs if spec in original_specs}
        logger.info(f"Processing only specified specs: {list(extractor.supported_specs.keys())}")
    
    try:
        # 执行提取并生成Excel模板
        result = extractor.extract_all_specs_to_excel(args.output)
        
        print("\n🎉 Enhanced PICS extraction completed!")
        print(f"📊 Summary:")
        print(f"   Processed specifications: {result['total_specs_processed']}")
        print(f"   Total PICS items extracted: {result['total_pics_items']}")
        print(f"   Output file: {result['output_file']}")
        
        if result['successful_specs']:
            print(f"   ✅ Successful: {', '.join(result['successful_specs'])}")
        if result['failed_specs']:
            print(f"   ❌ Failed: {', '.join(result['failed_specs'])}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())su