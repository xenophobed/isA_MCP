#!/usr/bin/env python3
"""
PICS Extraction Service
核心服务：从用户上传的Excel中提取PICS TRUE项目

这是整个流程的第一步，负责：
1. 读取用户Excel文件
2. 提取所有Value=TRUE的PICS项目
3. 输出标准化的PICS数据结构
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
import json
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PICSItem:
    """标准化的PICS项目数据结构"""
    item_id: str  # e.g., "A.4.1-1/1"
    group: str
    description: str
    mnemonic: Optional[str] = None
    value: bool = True
    is_test_plan_relevant: Optional[str] = None
    status: Optional[str] = None
    row_index: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class BandInfo:
    """详细的Band信息"""
    band_name: str         # e.g., "Band_1", "n77", "CA_1C"
    band_type: str         # FDD, TDD, CA, DC
    band_category: str     # single_carrier, carrier_aggregation, dual_connectivity
    frequency_range: Optional[str] = None
    pics_ids: List[str] = field(default_factory=list)  # 相关的PICS IDs
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass 
class PICSExtractionResult:
    """PICS提取结果"""
    pics_items: List[PICSItem]
    total_items: int
    true_items: int
    band_info: List[str]  # 简单的band列表（向后兼容）
    detailed_bands: List[BandInfo]  # 详细的band信息
    features: List[str]    # 提取的feature信息
    spec_id: str          # 规范ID (e.g., "36521-2")
    metadata: Dict = field(default_factory=dict)
    
    def to_excel(self, output_path: str):
        """导出到Excel文件"""
        df = pd.DataFrame([item.to_dict() for item in self.pics_items])
        df.to_excel(output_path, index=False, sheet_name='PICS_TRUE_Items')
        logger.info(f"Exported {len(self.pics_items)} PICS items to {output_path}")
    
    def to_json(self, output_path: str):
        """导出到JSON文件"""
        with open(output_path, 'w') as f:
            json.dump({
                'total_items': self.total_items,
                'true_items': self.true_items,
                'band_info': self.band_info,
                'features': self.features,
                'spec_id': self.spec_id,
                'metadata': self.metadata,
                'pics_items': [item.to_dict() for item in self.pics_items]
            }, f, indent=2)
        logger.info(f"Exported PICS data to {output_path}")


class PICSExtractionService:
    """
    PICS提取服务 - 流程的第一步
    """
    
    def __init__(self):
        """初始化服务"""
        self.supported_sheets = [
            "3GPP TS 36.521-2",
            "3GPP TS 38.521-2",
            "3GPP TS 34.123-2",
            "PICS"
        ]
        logger.info("Initialized PICSExtractionService")
    
    def extract_from_excel(self, 
                          file_path: str, 
                          sheet_name: Optional[str] = None,
                          process_all_sheets: bool = True) -> PICSExtractionResult:
        """
        从Excel文件提取PICS TRUE项目
        
        Args:
            file_path: Excel文件路径
            sheet_name: Sheet名称，如果为None则处理所有3GPP sheets
            process_all_sheets: 是否处理所有3GPP sheets
            
        Returns:
            PICSExtractionResult: 提取结果
        """
        logger.info(f"Extracting PICS from: {file_path}")
        
        # 验证文件
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # 获取所有sheet名称
        excel_file = pd.ExcelFile(file_path)
        
        if process_all_sheets or sheet_name is None:
            # 处理所有3GPP TS开头的sheets
            gpp_sheets = [name for name in excel_file.sheet_names if name.startswith('3GPP TS')]
            logger.info(f"Found {len(gpp_sheets)} 3GPP specification sheets")
        else:
            # 只处理指定的sheet
            gpp_sheets = [sheet_name] if sheet_name else [self._detect_pics_sheet(file_path)]
        
        all_pics_items = []
        all_bands = set()
        all_features = set()
        total_items_count = 0
        metadata = {
            'file_name': file_path.name,
            'sheets_processed': []
        }
        
        # 处理每个sheet
        for sheet in gpp_sheets:
            logger.info(f"Processing sheet: {sheet}")
            
            try:
                # 读取数据 - 使用header=1（基于corrected_interlab_reader.py）
                df = pd.read_excel(file_path, sheet_name=sheet, header=1)
                
                # 提取TRUE项目（这里需要使用SupportedStartValue而不是Value）
                pics_items = self._extract_true_items_corrected(df, sheet)
                
                # 提取band信息（包括详细信息）
                band_info = self._extract_band_info(pics_items)
                all_bands.update(band_info)
                
                # 提取features
                features = self._extract_features(pics_items)
                all_features.update(features)
                
                all_pics_items.extend(pics_items)
                total_items_count += len(df)
                
                metadata['sheets_processed'].append({
                    'sheet': sheet,
                    'total_rows': len(df),
                    'true_items': len(pics_items)
                })
                
            except Exception as e:
                logger.warning(f"Failed to process sheet {sheet}: {e}")
                continue
        
        # 统计信息
        true_items = len(all_pics_items)
        has_mnemonic = sum(1 for item in all_pics_items if item.mnemonic)
        
        metadata.update({
            'total_rows': total_items_count,
            'true_items': true_items,
            'items_with_mnemonic': has_mnemonic,
            'items_without_mnemonic': true_items - has_mnemonic
        })
        
        logger.info(f"Extracted {true_items} TRUE items from {total_items_count} total")
        logger.info(f"  - With mnemonic: {has_mnemonic}")
        logger.info(f"  - Without mnemonic: {true_items - has_mnemonic}")
        logger.info(f"  - Bands found: {len(all_bands)}")
        logger.info(f"  - Features found: {len(all_features)}")
        
        # 检测主要规范ID（基于最多的sheet）
        spec_id = self._detect_primary_spec_id(gpp_sheets)
        
        # 提取详细的band信息
        detailed_bands = self._extract_detailed_band_info(all_pics_items)
        
        return PICSExtractionResult(
            pics_items=all_pics_items,
            total_items=total_items_count,
            true_items=true_items,
            band_info=sorted(list(all_bands)),
            detailed_bands=detailed_bands,
            features=sorted(list(all_features)),
            spec_id=spec_id,
            metadata=metadata
        )
    
    def _detect_pics_sheet(self, file_path: Path) -> str:
        """自动检测PICS sheet"""
        xl_file = pd.ExcelFile(file_path)
        sheet_names = xl_file.sheet_names
        
        # 查找匹配的sheet
        for sheet in sheet_names:
            for supported in self.supported_sheets:
                if supported in sheet:
                    logger.info(f"Auto-detected PICS sheet: {sheet}")
                    return sheet
        
        # 默认返回第一个sheet
        logger.warning(f"No PICS sheet detected, using first sheet: {sheet_names[0]}")
        return sheet_names[0]
    
    def _extract_true_items(self, df: pd.DataFrame) -> List[PICSItem]:
        """提取所有TRUE项目（旧方法，用于兼容性）"""
        pics_items = []
        
        # 确定Value列
        value_col = 'Value' if 'Value' in df.columns else None
        if not value_col:
            # 尝试其他可能的列名
            for col in ['Supported', 'Support', 'Status']:
                if col in df.columns:
                    value_col = col
                    break
        
        if not value_col:
            raise ValueError("Cannot find value column in Excel")
        
        # 提取TRUE行
        true_rows = df[df[value_col] == True].copy()
        
        # 转换为PICSItem对象
        for idx, row in true_rows.iterrows():
            item = PICSItem(
                item_id=str(row.get('Item', '')),
                group=str(row.get('Group', '')),
                description=str(row.get('Description', '')),
                mnemonic=row.get('Mnemonic') if pd.notna(row.get('Mnemonic')) else None,
                value=True,
                is_test_plan_relevant=row.get('Is Test Plan\nRelevant', ''),
                status=row.get('Status', ''),
                row_index=idx
            )
            pics_items.append(item)
        
        return pics_items
    
    def _extract_true_items_corrected(self, df: pd.DataFrame, sheet_name: str) -> List[PICSItem]:
        """提取所有TRUE项目（基于corrected_interlab_reader的正确方法）"""
        pics_items = []
        
        # 使用SupportedStartValue列（这是正确的列）
        value_col = 'SupportedStartValue'
        
        # 如果SupportedStartValue不存在，尝试Value列
        if value_col not in df.columns:
            value_col = 'Value' if 'Value' in df.columns else None
            logger.warning(f"Sheet {sheet_name}: SupportedStartValue not found, using {value_col}")
        
        if not value_col:
            logger.warning(f"Sheet {sheet_name}: No value column found")
            return []
        
        # 遍历所有行
        for idx, row in df.iterrows():
            supported_value = row.get(value_col)
            
            # 检查是否支持
            is_supported = str(supported_value).upper() == 'TRUE' if pd.notna(supported_value) else False
            
            if is_supported:
                item_id = str(row.get('Item', ''))
                
                # 验证PICS ID格式
                if not item_id or pd.isna(row.get('Item')):
                    continue
                    
                item = PICSItem(
                    item_id=item_id,
                    group=str(row.get('Group', '')),
                    description=str(row.get('Description', '')),
                    mnemonic=row.get('Mnemonic') if pd.notna(row.get('Mnemonic')) else None,
                    value=True,
                    is_test_plan_relevant=row.get('Is Test Plan\nRelevant', ''),
                    status=row.get('Status', ''),
                    row_index=idx
                )
                pics_items.append(item)
        
        return pics_items
    
    def _extract_band_info(self, pics_items: List[PICSItem]) -> List[str]:
        """从PICS项目中提取band信息（简单版本）"""
        bands = set()
        
        for item in pics_items:
            # 从description中提取band信息
            desc = item.description.lower()
            
            # LTE bands (Band 1-71)
            import re
            lte_bands = re.findall(r'band\s*(\d+)', desc)
            for band in lte_bands:
                bands.add(f"Band_{band}")
            
            # NR bands (n1-n261)
            nr_bands = re.findall(r'n(\d+)', desc)
            for band in nr_bands:
                bands.add(f"n{band}")
            
            # FDD/TDD info
            if 'fdd' in desc:
                for band in lte_bands:
                    bands.add(f"Band_{band}_FDD")
            if 'tdd' in desc:
                for band in lte_bands:
                    bands.add(f"Band_{band}_TDD")
        
        return sorted(list(bands))
    
    def _extract_detailed_band_info(self, pics_items: List[PICSItem]) -> List[BandInfo]:
        """从PICS项目中提取详细的band信息（替代band_mapping_extractor_v2）"""
        import re
        band_dict = {}  # band_name -> BandInfo
        
        # Band类型判断规则
        FDD_BANDS = set(range(1, 32))  # Band 1-31 are FDD
        TDD_BANDS = set(range(33, 54))  # Band 33-53 are TDD
        
        for item in pics_items:
            desc = item.description.lower()
            item_id = item.item_id
            
            # 1. 提取单载波bands
            lte_bands = re.findall(r'band\s*(\d+)', desc)
            for band_num in lte_bands:
                band_num_int = int(band_num)
                band_name = f"Band_{band_num}"
                
                # 判断FDD还是TDD
                if band_num_int in FDD_BANDS or 'fdd' in desc:
                    band_type = 'FDD'
                    full_band_name = f"{band_name}_FDD"
                elif band_num_int in TDD_BANDS or 'tdd' in desc:
                    band_type = 'TDD'
                    full_band_name = f"{band_name}_TDD"
                else:
                    band_type = 'Unknown'
                    full_band_name = band_name
                
                if full_band_name not in band_dict:
                    band_dict[full_band_name] = BandInfo(
                        band_name=full_band_name,
                        band_type=band_type,
                        band_category='single_carrier',
                        pics_ids=[item_id]
                    )
                else:
                    band_dict[full_band_name].pics_ids.append(item_id)
            
            # 2. 提取NR bands
            nr_bands = re.findall(r'n(\d+)', desc)
            for band_num in nr_bands:
                band_name = f"n{band_num}"
                
                if band_name not in band_dict:
                    band_dict[band_name] = BandInfo(
                        band_name=band_name,
                        band_type='NR',
                        band_category='single_carrier',
                        pics_ids=[item_id]
                    )
                else:
                    band_dict[band_name].pics_ids.append(item_id)
            
            # 3. 提取CA配置（基于PICS ID模式）
            if 'A.4.6.1-3/' in item_id or 'ca' in desc or 'carrier aggregation' in desc:
                # 提取CA配置名称
                ca_match = re.search(r'A\.4\.6\.1-3/(.+)', item_id)
                if ca_match:
                    ca_name = ca_match.group(1)
                    if ca_name not in band_dict:
                        band_dict[ca_name] = BandInfo(
                            band_name=ca_name,
                            band_type='CA',
                            band_category='carrier_aggregation',
                            pics_ids=[item_id]
                        )
                    else:
                        band_dict[ca_name].pics_ids.append(item_id)
            
            # 4. 提取DC配置
            if 'dual connectivity' in desc or 'dc' in desc:
                # 尝试提取DC配置
                dc_match = re.search(r'dc[_-]?(\w+)', desc)
                if dc_match:
                    dc_name = f"DC_{dc_match.group(1)}"
                    if dc_name not in band_dict:
                        band_dict[dc_name] = BandInfo(
                            band_name=dc_name,
                            band_type='DC',
                            band_category='dual_connectivity',
                            pics_ids=[item_id]
                        )
                    else:
                        band_dict[dc_name].pics_ids.append(item_id)
            
            # 5. 提取频率范围（如果有）
            freq_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*(MHz|GHz)', desc)
            if freq_match:
                freq_range = f"{freq_match.group(1)}-{freq_match.group(2)} {freq_match.group(3)}"
                # 更新最近添加的band的频率范围
                for band_info in band_dict.values():
                    if item_id in band_info.pics_ids and not band_info.frequency_range:
                        band_info.frequency_range = freq_range
        
        # 转换为列表并排序
        detailed_bands = sorted(band_dict.values(), key=lambda x: (x.band_category, x.band_name))
        
        # 记录统计信息
        stats = {
            'single_carrier': sum(1 for b in detailed_bands if b.band_category == 'single_carrier'),
            'carrier_aggregation': sum(1 for b in detailed_bands if b.band_category == 'carrier_aggregation'),
            'dual_connectivity': sum(1 for b in detailed_bands if b.band_category == 'dual_connectivity'),
            'fdd_bands': sum(1 for b in detailed_bands if b.band_type == 'FDD'),
            'tdd_bands': sum(1 for b in detailed_bands if b.band_type == 'TDD'),
            'nr_bands': sum(1 for b in detailed_bands if b.band_type == 'NR'),
            'ca_configs': sum(1 for b in detailed_bands if b.band_type == 'CA')
        }
        
        logger.info(f"Extracted detailed band information:")
        logger.info(f"  - Single Carrier: {stats['single_carrier']} bands")
        logger.info(f"  - Carrier Aggregation: {stats['carrier_aggregation']} configs")
        logger.info(f"  - Dual Connectivity: {stats['dual_connectivity']} configs")
        logger.info(f"  - FDD: {stats['fdd_bands']}, TDD: {stats['tdd_bands']}, NR: {stats['nr_bands']}")
        
        return detailed_bands
    
    def _extract_features(self, pics_items: List[PICSItem]) -> List[str]:
        """从PICS项目中提取feature信息"""
        features = set()
        
        feature_keywords = [
            'ca', 'carrier aggregation', 'mimo', 'ul-mimo', 'dl-mimo',
            '64qam', '256qam', '1024qam', 'v2x', 'prose', 'mbms',
            'volte', 'vowifi', 'endc', 'nsa', 'sa', 'dsds', 'dsda'
        ]
        
        for item in pics_items:
            desc = item.description.lower()
            for keyword in feature_keywords:
                if keyword in desc:
                    features.add(keyword.upper().replace(' ', '_'))
        
        return sorted(list(features))
    
    def _detect_spec_id(self, sheet_name: str) -> str:
        """从sheet名称检测规范ID"""
        import re
        
        # 匹配模式
        patterns = [
            (r'36\.521-2', '365212'),
            (r'38\.521-2', '385212'),
            (r'34\.123', '34123'),
            (r'36\.521-1', '365211'),
            (r'38\.521-1', '385211')
        ]
        
        for pattern, spec_id in patterns:
            if re.search(pattern, sheet_name):
                return spec_id
        
        return 'unknown'
    
    def _detect_primary_spec_id(self, sheet_names: List[str]) -> str:
        """检测主要的规范ID（基于最常见的）"""
        from collections import Counter
        
        spec_ids = []
        for sheet_name in sheet_names:
            spec_id = self._detect_spec_id(sheet_name)
            if spec_id != 'unknown':
                spec_ids.append(spec_id)
        
        if spec_ids:
            # 返回最常见的spec_id
            counter = Counter(spec_ids)
            return counter.most_common(1)[0][0]
        
        return 'unknown'
    
    def validate_extraction(self, result: PICSExtractionResult) -> Dict:
        """验证提取结果的完整性"""
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 检查是否有TRUE项目
        if result.true_items == 0:
            validation['errors'].append("No TRUE items found")
            validation['is_valid'] = False
        
        # 检查band信息
        if len(result.band_info) == 0:
            validation['warnings'].append("No band information extracted")
        
        # 检查spec_id
        if result.spec_id == 'unknown':
            validation['warnings'].append("Could not detect specification ID")
        
        # 检查mnemonic覆盖率
        with_mnemonic = result.metadata.get('items_with_mnemonic', 0)
        if result.true_items > 0:
            mnemonic_coverage = with_mnemonic / result.true_items
            if mnemonic_coverage < 0.1:
                validation['warnings'].append(f"Low mnemonic coverage: {mnemonic_coverage*100:.1f}%")
        
        return validation


def main():
    """测试服务"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PICS Extraction Service')
    parser.add_argument('input', help='Input Excel file path')
    parser.add_argument('--sheet', help='Sheet name (auto-detect if not provided)')
    parser.add_argument('--output-excel', help='Output Excel file path')
    parser.add_argument('--output-json', help='Output JSON file path')
    
    args = parser.parse_args()
    
    # 创建服务实例
    service = PICSExtractionService()
    
    try:
        # 提取PICS
        result = service.extract_from_excel(args.input, args.sheet)
        
        # 验证结果
        validation = service.validate_extraction(result)
        
        print(f"\n=== Extraction Results ===")
        print(f"Total items: {result.total_items}")
        print(f"TRUE items: {result.true_items}")
        print(f"Bands: {result.band_info[:10]}...")
        print(f"Features: {result.features[:10]}...")
        print(f"Spec ID: {result.spec_id}")
        
        print(f"\n=== Validation ===")
        print(f"Valid: {validation['is_valid']}")
        if validation['errors']:
            print(f"Errors: {validation['errors']}")
        if validation['warnings']:
            print(f"Warnings: {validation['warnings']}")
        
        # 导出结果
        if args.output_excel:
            result.to_excel(args.output_excel)
            print(f"Exported to Excel: {args.output_excel}")
        
        if args.output_json:
            result.to_json(args.output_json)
            print(f"Exported to JSON: {args.output_json}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())