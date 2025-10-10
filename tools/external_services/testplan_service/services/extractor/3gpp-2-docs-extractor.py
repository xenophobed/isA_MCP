#!/usr/bin/env python3
"""
Applicability and Conditions Extractor for 3GPP Documents

This tool extracts:
1. Applicability table (test cases with all fields)
2. Conditions tables (C-conditions, PICS conditions, etc.)

Enhanced with:
- Better .doc file support
- Chunked processing for large documents
- Split document handling (e.g., 38.521-2)
- Robust error handling
"""

import json
from pathlib import Path
import re
from typing import Dict, List, Any, Optional, Tuple, Union
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
import sys
import asyncio
import subprocess
import tempfile

# Add path for imports
base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(base_path))

from services.parser.document_parser import UniversalDocumentParser, Table, ParsedDocument
from services.utils.llm_table_parser import LLMTableParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Represents a test case from the Applicability table"""
    test_id: str
    clause: str
    title: str
    release: str
    applicability_condition: str  # Condition ID (e.g., C186, C39a)
    applicability_comment: str    # Comments text description
    specific_ics: str
    specific_ixit: str
    num_executions: str
    release_other_rat: str
    tested_bands: str             # New field: Tested Bands / CA-Configurations Selection
    branch: str                   # New field: Branch
    additional_information: str   # New field: Additional Information
    standard: str
    version: str
    raw_row_data: Dict            # Store all original row data
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Condition:
    """Represents a condition definition"""
    condition_id: str
    definition: str
    condition_type: str  # 'C-condition', 'PICS', 'Other'
    table_index: int
    standard: str
    version: str
    raw_data: Dict  # Store all original fields
    
    def to_dict(self) -> Dict:
        return asdict(self)


# DocumentConverter class removed - we'll use document_parser.py's built-in conversion


class ApplicabilityExtractor:
    """
    Extracts Applicability and Conditions from 3GPP documents
    Enhanced with better format support and error handling
    """
    
    def __init__(self, doc_path: str):
        """
        Initialize the extractor with a document path
        
        Args:
            doc_path: Path to the 3GPP document (.docx, .doc, .pdf, etc.)
        """
        self.doc_path = Path(doc_path)
        if not self.doc_path.exists():
            raise FileNotFoundError(f"Document not found: {doc_path}")
        
        # Extract standard and version from path
        parts = self.doc_path.parts
        self.standard = None
        self.version = None
        
        for part in parts:
            if part.startswith('TS '):
                self.standard = part.replace('TS ', '')
            elif '-' in part and part[0].isdigit():
                self.version = part.split('.')[0]  # Remove extension
        
        # Initialize parser (it handles all conversions internally)
        self.parser = UniversalDocumentParser()
        self.doc = None
        self.file_type = self.doc_path.suffix.lower()
        self._prepare_document()
        
        # Initialize LLM table parser (lazy loading)
        self.llm_parser = None
        
        logger.info(f"📄 Processing document: {self.doc_path.name}")
        logger.info(f"   Standard: {self.standard}, Version: {self.version}")
        logger.info(f"   File type: {self.file_type}")
        logger.info(f"   Tables found: {len(self.doc.tables) if self.doc else 0}")
    
    def _prepare_document(self):
        """Prepare document for parsing, handle conversions"""
        # Parse document - document_parser.py handles all format conversions internally
        self.doc = self.parser.parse(self.doc_path)
        
        # Check if parsing was successful
        if not self.doc.success:
            logger.warning(f"Initial parse failed: {self.doc.error}")
            # For .doc files, suggest installing LibreOffice or docx2txt
            if self.file_type == '.doc':
                logger.info("To better support .doc files, install one of:")
                logger.info("  - LibreOffice: brew install libreoffice")
                logger.info("  - docx2txt: pip install docx2txt")
        
        # Handle split documents for 38.521-2
        if '_s' in self.doc_path.stem and self.standard == '38.521-2':
            self._handle_split_documents()
    
    def _handle_split_documents(self):
        """Handle 38.521-2 style split documents"""
        parent = self.doc_path.parent
        stem = self.doc_path.stem
        base_name = stem.split('_s')[0]
        pattern = f"{base_name}_s*.docx"
        split_files = sorted(parent.glob(pattern))
        
        if len(split_files) > 1:
            logger.info(f"Found {len(split_files)} split documents, merging...")
            for split_file in split_files[1:]:
                if split_file != self.doc_path:
                    split_doc = self.parser.parse(split_file)
                    if split_doc.tables:
                        self.doc.tables.extend(split_doc.tables)
            logger.info(f"Merged to {len(self.doc.tables)} total tables")
    
    async def extract_applicability_table(self) -> Tuple[List[TestCase], Dict]:
        """
        Extract test cases from LLM-identified tables
        
        Returns:
            Tuple of (list of TestCase objects, raw data dict)
        """
        logger.info("🤖 Using LLM to identify test case tables...")
        
        # Initialize LLM parser if not done
        if not self.llm_parser:
            self.llm_parser = LLMTableParser()
        
        # For very large documents, use chunked processing
        if len(self.doc.tables) > 100:
            logger.info(f"Large document ({len(self.doc.tables)} tables), using chunked analysis")
            test_table_indices = await self._analyze_tables_chunked()
        else:
            # Use LLM to identify test tables
            try:
                llm_result = await self.llm_parser.analyze_document(str(self.doc_path))
                
                if not llm_result['success']:
                    logger.error(f"LLM analysis failed: {llm_result['error']}")
                    # Fallback to pattern-based detection
                    test_table_indices = self._detect_test_tables_by_pattern()
                else:
                    test_table_indices = llm_result['test_tables']
            except Exception as e:
                logger.error(f"LLM analysis error: {e}")
                # Fallback to pattern-based detection
                test_table_indices = self._detect_test_tables_by_pattern()
        
        logger.info(f"✅ Identified {len(test_table_indices)} test tables: {test_table_indices}")
        
        if not test_table_indices:
            logger.warning("⚠️  No test tables identified")
            return [], {}
        
        # Extract test cases from all identified tables
        all_test_cases = []
        all_headers = []
        extraction_summary = {}
        
        for table_idx in test_table_indices:
            if table_idx >= len(self.doc.tables):
                logger.warning(f"Table {table_idx} does not exist")
                continue
                
            table = self.doc.tables[table_idx]
            headers = table.headers if table.headers else []
            all_headers.extend(headers)
            
            logger.info(f"📋 Processing table {table_idx}")
            logger.info(f"   Headers: {headers[:5]}...")
            logger.info(f"   Rows: {len(table.rows)}")
            
            table_test_cases = []
            
            for row_idx, row_values in enumerate(table.rows, 1):
                if not row_values:
                    continue
                    
                row_data = {}
                for col_idx, value in enumerate(row_values):
                    if col_idx < len(headers):
                        header = headers[col_idx]
                        # Clean up value
                        value_str = str(value).strip() if value else ''
                        # Clean up newlines and extra spaces
                        value_str = ' '.join(value_str.split())
                        
                        # Handle duplicate column names by creating unique keys
                        unique_header = header
                        counter = 1
                        while unique_header in row_data:
                            unique_header = f"{header}_{counter}"
                            counter += 1
                        
                        row_data[unique_header] = value_str
                
                # Check if this is a valid test case row
                first_cell = str(row_values[0]).strip() if row_values else ""
                
                # Check for test ID patterns
                is_test_case = bool(re.match(r'^(\d+\.\d+|TC[_-]?\d+|\d+\.\d+\.\d+|\d+\.\d+_\d+|\d+\.\d+[A-Z]+)', first_cell))
                
                if is_test_case:
                    # Create TestCase object
                    # Handle both "TC Title" and "Title" headers  
                    title = row_data.get('TC Title', '') or row_data.get('Title', '')
                    
                    # Smart field mapping based on table structure
                    applicability_condition = ''
                    applicability_comment = ''
                    
                    # Method 1: Standard table with named columns
                    if 'Applicability Condition' in row_data:
                        applicability_condition = row_data.get('Applicability Condition', '')
                        applicability_comment = row_data.get('Applicability Comment', '')
                    
                    # Method 2: Look for any "Applicability" columns
                    elif any('Applicability' in k for k in row_data.keys()):
                        applicability_values = []
                        for k, v in row_data.items():
                            if 'Applicability' in k:
                                applicability_values.append(v)
                        
                        if len(applicability_values) >= 2:
                            val1, val2 = applicability_values[0], applicability_values[1]
                            # Smart detection: condition vs comment
                            if (val1 and len(val1) <= 20 and 
                                (val1.startswith('C') or val1 in ['R', 'M', 'O', 'N/A'] or 
                                 not val1.startswith('UE supporting'))):
                                applicability_condition = val1
                                applicability_comment = val2
                            else:
                                applicability_condition = val2
                                applicability_comment = val1
                        elif len(applicability_values) == 1:
                            val = applicability_values[0]
                            if (val and len(val) <= 20 and 
                                (val.startswith('C') or val in ['R', 'M', 'O', 'N/A'])):
                                applicability_condition = val
                            else:
                                applicability_comment = val
                    
                    # Method 3: Positional mapping for tables without proper headers
                    # Check if this table has no Applicability columns but has data in positions 3,4
                    elif len(row_values) >= 5:
                        # For tables like 1,2 where data is in fixed positions
                        potential_condition = str(row_values[3]).strip() if len(row_values) > 3 else ''
                        potential_comment = str(row_values[4]).strip() if len(row_values) > 4 else ''
                        
                        # Check if position 3 looks like a condition
                        if (potential_condition and len(potential_condition) <= 20 and 
                            (potential_condition.startswith('C') or potential_condition in ['R', 'M', 'O', 'N/A'])):
                            applicability_condition = potential_condition
                            applicability_comment = potential_comment
                            logger.debug(f"Positional mapping for {first_cell}: {potential_condition} | {potential_comment}")
                    
                    # Method 4: Fallback - look for any C-condition in any field
                    if not applicability_condition:
                        for value in row_values:
                            value_str = str(value).strip()
                            if (value_str and len(value_str) <= 20 and 
                                (value_str.startswith('C') or value_str in ['R', 'M', 'O', 'N/A'])):
                                applicability_condition = value_str
                                break
                    
                    tc = TestCase(
                        test_id=first_cell,
                        clause=first_cell,
                        title=title,
                        release=row_data.get('Release', ''),
                        applicability_condition=applicability_condition,
                        applicability_comment=applicability_comment,
                        specific_ics=row_data.get('Specific ICS', ''),
                        specific_ixit=row_data.get('Specific IXIT', ''),
                        num_executions=row_data.get('Number of TC Executions', ''),
                        release_other_rat=row_data.get('Release other RAT', ''),
                        tested_bands=row_data.get('Tested Bands / CA-Configurations Selection', ''),
                        branch=row_data.get('Branch', ''),
                        additional_information=row_data.get('Additional Information', ''),
                        standard=self.standard or '',
                        version=self.version or '',
                        raw_row_data=row_data.copy()
                    )
                    table_test_cases.append(tc)
            
            all_test_cases.extend(table_test_cases) 
            extraction_summary[f'table_{table_idx}'] = len(table_test_cases)
            
            logger.info(f"   ✅ Extracted {len(table_test_cases)} test cases from table {table_idx}")
        
        # Build final raw_data structure
        raw_data = {
            'standard': self.standard,
            'version': self.version,
            'extraction_date': datetime.now().isoformat(),
            'headers': list(set(all_headers)),  # Unique headers from all tables
            'test_cases': [tc.raw_row_data for tc in all_test_cases],
            'llm_analysis': {
                'tables_processed': test_table_indices,
                'extraction_summary': extraction_summary
            }
        }
        
        logger.info(f"📊 Total extracted: {len(all_test_cases)} test cases from {len(test_table_indices)} tables")
        logger.info(f"   Per-table breakdown: {extraction_summary}")
        return all_test_cases, raw_data
    
    async def _analyze_tables_chunked(self) -> List[int]:
        """Analyze tables in chunks for large documents"""
        test_indices = []
        chunk_size = 50
        
        for i in range(0, len(self.doc.tables), chunk_size):
            chunk_end = min(i + chunk_size, len(self.doc.tables))
            chunk_indices = list(range(i, chunk_end))
            
            # Analyze chunk
            for idx in chunk_indices:
                if self._is_test_table(self.doc.tables[idx]):
                    test_indices.append(idx)
        
        return test_indices
    
    def _detect_test_tables_by_pattern(self) -> List[int]:
        """Detect test tables by header patterns"""
        test_indices = []
        
        for idx, table in enumerate(self.doc.tables):
            if self._is_test_table(table):
                test_indices.append(idx)
        
        return test_indices
    
    def _is_test_table(self, table: Table) -> bool:
        """Check if table is likely a test case table"""
        if not table.headers:
            return False
        
        headers_str = ' '.join(table.headers).lower()
        
        # Test table patterns
        test_patterns = [
            r'clause.*title.*release.*applicability',
            r'test.*case.*condition',
            r'tc.*title.*applicability'
        ]
        
        for pattern in test_patterns:
            if re.search(pattern, headers_str):
                return True
        
        # Check first few rows for test ID pattern
        if table.rows:
            for row in table.rows[:5]:
                if row and row[0]:
                    first_cell = str(row[0]).strip()
                    if re.match(r'^(\d+\.\d+|TC[_-]?\d+|\d+\.\d+\.\d+)', first_cell):
                        return True
        
        return False
    
    def _has_test_ids_pattern(self, header_text: str) -> bool:
        """Check if header text suggests this is a test table"""
        test_indicators = ['Test', 'TC', 'Procedure', 'Requirement', 'Conformance']
        return any(indicator in header_text for indicator in test_indicators)
    
    def extract_c_conditions_table(self) -> Tuple[List[Condition], Dict]:
        """
        Extract C-conditions table (usually Table 7 or similar)
        Contains conditions like C01, C02, etc.
        
        Returns:
            Tuple of (list of Condition objects, raw data dict)
        """
        logger.info("🔍 Searching for C-conditions table...")
        
        c_conditions = []
        raw_data = {
            'standard': self.standard,
            'version': self.version,
            'extraction_date': datetime.now().isoformat(),
            'conditions': []
        }
        
        # Find C-conditions table
        c_table = None
        for i, table in enumerate(self.doc.tables):
            if not table.rows:
                continue
            
            # Skip the applicability table (usually index 0)
            if i == 0:
                continue
            
            # Check if table contains C-conditions
            # Convert table data to text for pattern matching
            table_text = '\n'.join([
                ' '.join([str(cell) for cell in row if cell]) 
                for row in table.rows[:10]  # Check first 10 rows
            ])
            
            # Look for C01, C02, etc. at the beginning of lines
            if re.search(r'^C\d{2,3}\b', table_text, re.MULTILINE):
                c_table = table
                logger.info(f"✅ Found C-conditions table at index {i}")
                break
        
        if not c_table:
            logger.warning("⚠️  C-conditions table not found")
            return [], raw_data
        
        # Get table index
        table_index = self.doc.tables.index(c_table) if c_table else -1
        
        # Extract conditions from table data
        for row_values in c_table.rows:
            row_text = ' '.join([str(cell).strip() for cell in row_values if cell])
            # Clean up extra spaces
            row_text = ' '.join(row_text.split())
            
            # Parse C-condition pattern
            match = re.match(r'^(C\d+[a-zA-Z]?)\s+(.+)', row_text)
            if match:
                condition_id = match.group(1)
                definition = match.group(2)
                
                condition = Condition(
                    condition_id=condition_id,
                    definition=definition,
                    condition_type='C-condition',
                    table_index=table_index,
                    standard=self.standard or '',
                    version=self.version or '',
                    raw_data={'full_text': row_text}
                )
                c_conditions.append(condition)
                raw_data['conditions'].append({
                    'id': condition_id,
                    'definition': definition,
                    'type': 'C-condition'
                })
        
        logger.info(f"📊 Extracted {len(c_conditions)} C-conditions")
        return c_conditions, raw_data
    
    def _find_pics_tables_enhanced(self) -> List[int]:
        """Enhanced PICS table detection"""
        pics_indices = []
        
        for idx, table in enumerate(self.doc.tables):
            if not table.headers:
                continue
            
            headers_str = ' '.join(table.headers).lower()
            
            # PICS patterns
            pics_patterns = [
                'additional information',
                'item.*capability',
                'item.*reference',
                'pics.*item',
                'mnemonic'
            ]
            
            for pattern in pics_patterns:
                if pattern in headers_str:
                    pics_indices.append(idx)
                    break
            
            # Also check for pc_ in first few rows
            if idx not in pics_indices and table.rows:
                for row in table.rows[:5]:
                    row_text = ' '.join([str(cell) for cell in row if cell])
                    if 'pc_' in row_text:
                        pics_indices.append(idx)
                        break
        
        return pics_indices
    
    def extract_pics_conditions(self) -> Tuple[List[Condition], Dict]:
        """
        Extract PICS conditions tables (pc_ mnemonics)
        
        Returns:
            Tuple of (list of Condition objects, raw data dict)
        """
        logger.info("🔍 Searching for PICS conditions tables...")
        
        pics_conditions = []
        raw_data = {
            'standard': self.standard,
            'version': self.version,
            'extraction_date': datetime.now().isoformat(),
            'conditions': []
        }
        
        # Find all PICS tables with enhanced detection
        pics_table_indices = self._find_pics_tables_enhanced()
        
        for i in pics_table_indices:
            table = self.doc.tables[i]
            if not table.rows:
                continue
            
            # Use headers from Table object
            headers = table.headers
            
            # Find Mnemonic column or Item column
            mnemonic_col = -1
            item_col = -1
            for idx, header in enumerate(headers):
                if 'Mnemonic' in header:
                    mnemonic_col = idx
                elif 'Item' in header:
                    item_col = idx
            
            # If no mnemonic column but has item column, use item column
            if mnemonic_col == -1 and item_col == -1:
                continue
            
            target_col = mnemonic_col if mnemonic_col != -1 else item_col
            
            logger.info(f"   Processing PICS table {i} with headers: {headers[:3]}...")
            
            # Extract conditions from table data
            for row_values in table.rows:
                row_data = {}
                for col_idx, value in enumerate(row_values):
                    if col_idx < len(headers):
                        header = headers[col_idx]
                        value_str = str(value).strip() if value else ''
                        value_str = ' '.join(value_str.split())
                        row_data[header] = value_str
                
                # Get mnemonic or item
                if target_col >= 0 and target_col < len(row_values):
                    identifier = str(row_values[target_col]).strip() if row_values[target_col] else ''
                    # Accept pc_ items or A.x.x patterns
                    if identifier and (identifier.startswith('pc_') or re.match(r'^A\.\d', identifier)):
                        # Create condition
                        condition = Condition(
                            condition_id=identifier,
                            definition=json.dumps(row_data),  # Store all fields as JSON
                            condition_type='PICS',
                            table_index=i,
                            standard=self.standard or '',
                            version=self.version or '',
                            raw_data=row_data
                        )
                        pics_conditions.append(condition)
                        raw_data['conditions'].append(row_data)
        
        logger.info(f"📊 Extracted {len(pics_conditions)} PICS conditions")
        return pics_conditions, raw_data
    
    async def extract_all(self, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract all tables and optionally save to files
        
        Args:
            output_dir: Directory to save JSON files (optional)
        
        Returns:
            Dictionary containing all extracted data
        """
        logger.info("="*60)
        logger.info("🚀 Starting complete extraction...")
        
        # Extract all data
        test_cases, tc_raw = await self.extract_applicability_table()
        c_conditions, c_raw = self.extract_c_conditions_table()
        pics_conditions, pics_raw = self.extract_pics_conditions()
        
        # Combine results
        result = {
            'document': {
                'path': str(self.doc_path),
                'standard': self.standard,
                'version': self.version,
                'extraction_date': datetime.now().isoformat()
            },
            'applicability': {
                'test_cases': [tc.to_dict() for tc in test_cases],
                'raw_data': tc_raw
            },
            'conditions': {
                'c_conditions': [c.to_dict() for c in c_conditions],
                'c_conditions_raw': c_raw,
                'pics_conditions': [p.to_dict() for p in pics_conditions],
                'pics_conditions_raw': pics_raw
            },
            'summary': {
                'total_test_cases': len(test_cases),
                'total_c_conditions': len(c_conditions),
                'total_pics_conditions': len(pics_conditions),
                'total_conditions': len(c_conditions) + len(pics_conditions)
            }
        }
        
        # Save to files if output directory is specified
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate filename based on standard and version
            base_name = f"{self.standard}_{self.version}" if self.standard and self.version else "extracted"
            
            # Save applicability data
            app_file = output_path / f"{base_name}_applicability.json"
            with open(app_file, 'w', encoding='utf-8') as f:
                json.dump(result['applicability'], f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Saved applicability data to: {app_file}")
            
            # Save conditions data
            cond_file = output_path / f"{base_name}_conditions.json"
            with open(cond_file, 'w', encoding='utf-8') as f:
                json.dump(result['conditions'], f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Saved conditions data to: {cond_file}")
            
            # Save complete data
            complete_file = output_path / f"{base_name}_complete.json"
            with open(complete_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Saved complete data to: {complete_file}")
        
        # Print summary
        logger.info("="*60)
        logger.info("✅ Extraction Complete!")
        logger.info(f"   📋 Test Cases: {result['summary']['total_test_cases']}")
        logger.info(f"   📋 C-Conditions: {result['summary']['total_c_conditions']}")
        logger.info(f"   📋 PICS Conditions: {result['summary']['total_pics_conditions']}")
        logger.info("="*60)
        
        return result
    
    def to_duckdb(self, db_path: str):
        """
        Export extracted data to DuckDB database
        (Future implementation)
        
        Args:
            db_path: Path to DuckDB database file
        """
        # TODO: Implement DuckDB export
        logger.info("⚠️  DuckDB export not yet implemented")
        pass


async def main():
    """
    CLI interface for the extractor
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract Applicability and Conditions from 3GPP documents'
    )
    parser.add_argument('doc_path', help='Path to the 3GPP .docx file')
    parser.add_argument(
        '-o', '--output',
        help='Output directory for JSON files',
        default='outputs'
    )
    parser.add_argument(
        '--db',
        help='Path to DuckDB database (future feature)',
        default=None
    )
    
    args = parser.parse_args()
    
    # Create extractor
    extractor = ApplicabilityExtractor(args.doc_path)
    
    # Extract all data
    result = await extractor.extract_all(output_dir=args.output)
    
    # Export to DuckDB if specified
    if args.db:
        extractor.to_duckdb(args.db)
    
    return result


if __name__ == "__main__":
    asyncio.run(main())