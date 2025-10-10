#!/usr/bin/env python3
"""
Certification Data Extractor
基础数据准备：从PTCRB和GCF认证机构数据中提取测试ID并保存到数据库

单一职责：
1. 读取data_source/PTCRB/和data_source/GCF/的数据文件
2. 提取测试ID列表
3. 保存到DuckDB的certification_tests表
"""

import re
import logging
import duckdb
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CertificationTest:
    """认证测试数据结构"""
    test_id: str
    spec_id: str
    spec_version: str
    certification_body: str  # PTCRB or GCF
    test_name: Optional[str] = None
    band: Optional[str] = None
    status: Optional[str] = None  # Active, Legacy, etc.
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ExtractionResult:
    """提取结果"""
    certification_body: str
    total_tests: int
    specs_covered: Dict[str, int]  # spec_id -> count
    tests: List[CertificationTest]
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'certification_body': self.certification_body,
            'total_tests': self.total_tests,
            'specs_covered': self.specs_covered,
            'test_count_by_spec': self.specs_covered,
            'warnings': self.warnings
        }


class CertificationDataExtractor:
    """
    认证数据提取器
    
    从PTCRB和GCF的官方数据中提取测试ID，建立标准测试库
    """
    
    # 简化的规范映射（基于测试ID前缀推断）
    # 实际规范应该从文件名或元数据中获取
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化提取器
        
        Args:
            db_path: DuckDB数据库路径
        """
        if db_path is None:
            base_path = Path(__file__).parent.parent.parent
            db_path = base_path / "database" / "testplan.duckdb"
        
        self.db_path = Path(db_path)
        self.conn = None
        
        logger.info(f"Initialized CertificationDataExtractor with database: {self.db_path}")
    
    def connect(self):
        """建立数据库连接"""
        self.conn = duckdb.connect(str(self.db_path))
        logger.info("Connected to database")
        
        # 创建认证测试表（如果不存在）
        self._create_tables()
    
    def disconnect(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Disconnected from database")
    
    def _create_tables(self):
        """创建必要的数据库表"""
        # 创建认证测试表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS certification_tests (
                test_id VARCHAR,
                spec_id VARCHAR,
                spec_version VARCHAR,
                certification_body VARCHAR,
                test_name VARCHAR,
                band VARCHAR,
                status VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (test_id, spec_id, certification_body)
            )
        """)
        
        # 创建索引
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cert_spec 
            ON certification_tests(spec_id, certification_body)
        """)
        
        logger.info("Database tables ready")
    
    def extract_ptcrb_data(self, 
                          data_dir: str = "data_source/PTCRB") -> ExtractionResult:
        """
        从PTCRB数据提取测试ID
        
        Args:
            data_dir: PTCRB数据目录
            
        Returns:
            ExtractionResult: 提取结果
        """
        logger.info(f"Extracting PTCRB data from {data_dir}")
        
        tests = []
        specs_covered = {}
        warnings = []
        
        data_path = Path(data_dir)
        
        # 1. 处理Excel文件
        excel_files = list(data_path.glob("*.xlsx")) + list(data_path.glob("*.xls"))
        for excel_file in excel_files:
            try:
                logger.info(f"Processing {excel_file.name}")
                df = pd.read_excel(excel_file, sheet_name=None)
                
                for sheet_name, sheet_df in df.items():
                    # 查找包含test ID的列
                    test_id_cols = [col for col in sheet_df.columns 
                                   if 'test' in str(col).lower() and 'id' in str(col).lower()]
                    
                    if test_id_cols:
                        for _, row in sheet_df.iterrows():
                            test_id = str(row[test_id_cols[0]]).strip()
                            if self._is_valid_test_id(test_id):
                                spec_id = self._extract_spec_from_test_id(test_id)
                                
                                test = CertificationTest(
                                    test_id=test_id,
                                    spec_id=spec_id,
                                    spec_version=sheet_name,
                                    certification_body='PTCRB',
                                    test_name=row.get('Test Name', ''),
                                    band=row.get('Band', ''),
                                    status='Active'
                                )
                                tests.append(test)
                                
                                # 统计
                                specs_covered[spec_id] = specs_covered.get(spec_id, 0) + 1
                                
            except Exception as e:
                warnings.append(f"Failed to process {excel_file.name}: {e}")
                logger.warning(f"Failed to process {excel_file.name}: {e}")
        
        # 2. 处理文本文件（如ptcrb_clean_test_ids.txt）
        txt_files = list(Path('.').glob("ptcrb*.txt"))
        for txt_file in txt_files:
            try:
                logger.info(f"Processing {txt_file.name}")
                with open(txt_file, 'r') as f:
                    for line in f:
                        test_id = line.strip()
                        if self._is_valid_test_id(test_id):
                            spec_id = self._extract_spec_from_test_id(test_id)
                            
                            test = CertificationTest(
                                test_id=test_id,
                                spec_id=spec_id,
                                spec_version='Unknown',
                                certification_body='PTCRB',
                                status='Active'
                            )
                            tests.append(test)
                            specs_covered[spec_id] = specs_covered.get(spec_id, 0) + 1
                            
            except Exception as e:
                warnings.append(f"Failed to process {txt_file.name}: {e}")
                logger.warning(f"Failed to process {txt_file.name}: {e}")
        
        logger.info(f"Extracted {len(tests)} PTCRB tests covering {len(specs_covered)} specs")
        
        return ExtractionResult(
            certification_body='PTCRB',
            total_tests=len(tests),
            specs_covered=specs_covered,
            tests=tests,
            warnings=warnings
        )
    
    def extract_gcf_data(self, 
                        data_dir: str = "data_source/GCF") -> ExtractionResult:
        """
        从GCF数据提取测试ID
        
        Args:
            data_dir: GCF数据目录
            
        Returns:
            ExtractionResult: 提取结果
        """
        logger.info(f"Extracting GCF data from {data_dir}")
        
        tests = []
        specs_covered = {}
        warnings = []
        
        data_path = Path(data_dir)
        
        # 处理Excel文件
        excel_files = list(data_path.glob("*.xlsx")) + list(data_path.glob("*.xls"))
        for excel_file in excel_files:
            try:
                logger.info(f"Processing {excel_file.name}")
                df = pd.read_excel(excel_file, sheet_name=None)
                
                for sheet_name, sheet_df in df.items():
                    # 查找test ID列
                    test_id_cols = [col for col in sheet_df.columns 
                                   if 'test' in str(col).lower() or 'tc' in str(col).lower()]
                    
                    if test_id_cols:
                        for _, row in sheet_df.iterrows():
                            test_id = str(row[test_id_cols[0]]).strip()
                            if self._is_valid_test_id(test_id):
                                spec_id = self._extract_spec_from_test_id(test_id)
                                
                                test = CertificationTest(
                                    test_id=test_id,
                                    spec_id=spec_id,
                                    spec_version=sheet_name,
                                    certification_body='GCF',
                                    test_name=row.get('Test Name', ''),
                                    band=row.get('Band', ''),
                                    status=row.get('Status', 'Active')
                                )
                                tests.append(test)
                                specs_covered[spec_id] = specs_covered.get(spec_id, 0) + 1
                                
            except Exception as e:
                warnings.append(f"Failed to process {excel_file.name}: {e}")
                logger.warning(f"Failed to process {excel_file.name}: {e}")
        
        # 处理文本文件
        txt_files = list(Path('.').glob("gcf*.txt"))
        for txt_file in txt_files:
            try:
                logger.info(f"Processing {txt_file.name}")
                with open(txt_file, 'r') as f:
                    for line in f:
                        test_id = line.strip()
                        if self._is_valid_test_id(test_id):
                            spec_id = self._extract_spec_from_test_id(test_id)
                            
                            test = CertificationTest(
                                test_id=test_id,
                                spec_id=spec_id,
                                spec_version='Unknown',
                                certification_body='GCF',
                                status='Active'
                            )
                            tests.append(test)
                            specs_covered[spec_id] = specs_covered.get(spec_id, 0) + 1
                            
            except Exception as e:
                warnings.append(f"Failed to process {txt_file.name}: {e}")
                logger.warning(f"Failed to process {txt_file.name}: {e}")
        
        logger.info(f"Extracted {len(tests)} GCF tests covering {len(specs_covered)} specs")
        
        return ExtractionResult(
            certification_body='GCF',
            total_tests=len(tests),
            specs_covered=specs_covered,
            tests=tests,
            warnings=warnings
        )
    
    def save_to_database(self, extraction_result: ExtractionResult):
        """
        保存提取结果到数据库
        
        Args:
            extraction_result: 提取结果
        """
        if not self.conn:
            self.connect()
        
        # 先删除该认证机构的旧数据
        self.conn.execute("""
            DELETE FROM certification_tests 
            WHERE certification_body = ?
        """, [extraction_result.certification_body])
        
        # 批量插入新数据
        for test in extraction_result.tests:
            try:
                self.conn.execute("""
                    INSERT INTO certification_tests 
                    (test_id, spec_id, spec_version, certification_body, 
                     test_name, band, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [
                    test.test_id,
                    test.spec_id,
                    test.spec_version,
                    test.certification_body,
                    test.test_name,
                    test.band,
                    test.status
                ])
            except Exception as e:
                logger.debug(f"Failed to insert {test.test_id}: {e}")
        
        # 提交事务
        self.conn.commit()
        
        logger.info(f"Saved {len(extraction_result.tests)} {extraction_result.certification_body} tests to database")
    
    def _is_valid_test_id(self, test_id: str) -> bool:
        """
        验证是否为有效的测试ID
        
        Args:
            test_id: 测试ID
            
        Returns:
            是否有效
        """
        if not test_id or test_id == 'nan' or test_id == 'None':
            return False
        
        # 3GPP测试ID通常以数字开头
        if not re.match(r'^\d', test_id):
            return False
        
        # 过滤掉明显的非测试ID
        if len(test_id) > 20 or len(test_id) < 3:
            return False
        
        return True
    
    def _extract_spec_from_test_id(self, test_id: str) -> str:
        """
        从测试ID推断规范ID
        
        Args:
            test_id: 测试ID（如6.2.2, 6.2.2A.1）
            
        Returns:
            规范ID（如365211）
        """
        # 基于测试ID前缀判断规范
        # 这是简化版本，实际可能需要更复杂的逻辑
        
        # 默认映射（基于常见模式）
        if test_id.startswith('6.') or test_id.startswith('7.'):
            return '365211'  # 36.521-1 (Radio)
        elif test_id.startswith('8.') or test_id.startswith('9.'):
            return '365231'  # 36.523-1 (Protocol)
        elif test_id.startswith('10.') or test_id.startswith('11.'):
            return '385211'  # 38.521-1 (5G Radio)
        elif test_id.startswith('12.') or test_id.startswith('13.'):
            return '385231'  # 38.523-1 (5G Protocol)
        else:
            return '365211'  # 默认为36.521-1
    
    # 移除映射功能，保持单一职责
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取认证数据统计"""
        if not self.conn:
            self.connect()
        
        stats = {}
        
        # 总体统计
        total = self.conn.execute("""
            SELECT certification_body, COUNT(*) as count
            FROM certification_tests
            GROUP BY certification_body
        """).fetchall()
        
        stats['by_certification'] = {body: count for body, count in total}
        
        # 按规范统计
        by_spec = self.conn.execute("""
            SELECT spec_id, certification_body, COUNT(*) as count
            FROM certification_tests
            GROUP BY spec_id, certification_body
            ORDER BY spec_id, certification_body
        """).fetchall()
        
        stats['by_spec'] = {}
        for spec_id, body, count in by_spec:
            if spec_id not in stats['by_spec']:
                stats['by_spec'][spec_id] = {}
            stats['by_spec'][spec_id][body] = count
        
        return stats


def main():
    """测试认证数据提取器"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Certification Data Extractor')
    parser.add_argument('--extract-ptcrb', action='store_true', help='Extract PTCRB data from data_source/PTCRB/')
    parser.add_argument('--extract-gcf', action='store_true', help='Extract GCF data from data_source/GCF/')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--db', help='Database path (optional)')
    
    args = parser.parse_args()
    
    extractor = CertificationDataExtractor(db_path=args.db)
    
    try:
        extractor.connect()
        
        if args.extract_ptcrb:
            print("=== Extracting PTCRB Data ===")
            result = extractor.extract_ptcrb_data()
            print(f"Extracted {result.total_tests} PTCRB tests")
            print(f"Specs covered: {list(result.specs_covered.keys())}")
            
            if result.warnings:
                print(f"\nWarnings:")
                for warning in result.warnings:
                    print(f"  - {warning}")
            
            extractor.save_to_database(result)
            print("✅ Saved to database")
        
        if args.extract_gcf:
            print("\n=== Extracting GCF Data ===")
            result = extractor.extract_gcf_data()
            print(f"Extracted {result.total_tests} GCF tests")
            print(f"Specs covered: {list(result.specs_covered.keys())}")
            
            if result.warnings:
                print(f"\nWarnings:")
                for warning in result.warnings:
                    print(f"  - {warning}")
            
            extractor.save_to_database(result)
            print("✅ Saved to database")
        
        if args.stats or not any([args.extract_ptcrb, args.extract_gcf]):
            print("\n=== Statistics ===")
            stats = extractor.get_statistics()
            
            print("\nTests by certification body:")
            for body, count in stats.get('by_certification', {}).items():
                print(f"  {body}: {count} tests")
            
            print("\nTests by specification:")
            for spec_id, bodies in stats.get('by_spec', {}).items():
                print(f"  {spec_id}:")
                for body, count in bodies.items():
                    print(f"    {body}: {count} tests")
        
    finally:
        extractor.disconnect()


if __name__ == "__main__":
    main()