#!/usr/bin/env python3
"""
Enhanced Data Extractor

This script addresses the critical data incompleteness issues identified in DATA_COLLECTION_ASSESSMENT.md:
1. Process all 15 document files in TS 36.521-1 (not just one)
2. Remove artificial limits (100k chars, 100 matches)
3. Improve test case identification with better patterns
4. Support multiple specifications
5. Extract complete test-condition mappings

Key improvements over prepare_real_data.py:
- Processes ALL document fragments
- No content limits
- Better regex patterns
- Multi-specification support
- Comprehensive validation against PDX data
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Add paths
sys.path.insert(0, "/Users/xenodennis/Documents/Fun/isA_MCP")
base_path = Path(__file__).parent.parent
sys.path.insert(0, str(base_path))

from services.parser.document_parser import DocumentParser


class EnhancedDataExtractor:
    """
    Enhanced data extractor that addresses the critical data incompleteness issues
    """
    
    def __init__(self):
        self.base_path = base_path
        self.parser = DocumentParser()
        self.processed_docs = set()
        self.extracted_test_cases = []
        self.extracted_conditions = []
        self.extracted_pics = []
        self.test_condition_mappings = []
        
    def extract_comprehensive_data(self) -> Dict[str, Any]:
        """
        Extract comprehensive data from all available 3GPP documents
        
        Returns:
            Complete dataset with all test cases, conditions, and mappings
        """
        logger.info("🚀 Starting comprehensive data extraction...")
        start_time = time.time()
        
        # 1. Extract all test cases from all 36.521-1 documents
        logger.info("📄 Extracting test cases from ALL 36.521-1 documents...")
        test_cases_36521_1 = self.extract_all_36521_1_test_cases()
        
        # 2. Extract test cases from other major specifications
        logger.info("📄 Extracting test cases from other specifications...")
        test_cases_others = self.extract_other_specifications_test_cases()
        
        # 3. Extract conditions from 36.521-2
        logger.info("📄 Extracting conditions from 36.521-2...")
        conditions = self.extract_enhanced_conditions_from_36521_2()
        
        # 4. Extract PICS definitions
        logger.info("📄 Extracting PICS definitions...")
        pics_definitions = self.extract_enhanced_pics_definitions()
        
        # 5. Extract comprehensive test-condition mappings
        logger.info("📄 Extracting test-condition mappings...")
        mappings = self.extract_comprehensive_test_condition_mappings()
        
        # Combine all test cases
        all_test_cases = test_cases_36521_1 + test_cases_others
        
        # Create comprehensive dataset
        comprehensive_data = {
            "source": "3GPP Comprehensive Extraction",
            "extraction_date": time.strftime("%Y-%m-%d"),
            "extraction_time": f"{time.time() - start_time:.2f}s",
            "conditions": conditions,
            "test_cases": all_test_cases,
            "pics_definitions": pics_definitions,
            "test_to_condition_mapping": mappings,
            "statistics": {
                "total_conditions": len(conditions),
                "total_test_cases": len(all_test_cases),
                "total_pics_items": len(pics_definitions),
                "total_mappings": len(mappings),
                "documents_processed": len(self.processed_docs),
                "test_cases_by_spec": self._count_by_specification(all_test_cases)
            },
            "quality_metrics": self._calculate_quality_metrics(all_test_cases, conditions, mappings)
        }
        
        # Save to enhanced JSON file
        output_file = self.base_path / "services/store/enhanced_3gpp_data.json"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(comprehensive_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Comprehensive extraction completed!")
        logger.info(f"📊 Statistics:")
        logger.info(f"  - Total test cases: {len(all_test_cases)}")
        logger.info(f"  - Total conditions: {len(conditions)}")
        logger.info(f"  - Total PICS: {len(pics_definitions)}")
        logger.info(f"  - Total mappings: {len(mappings)}")
        logger.info(f"  - Documents processed: {len(self.processed_docs)}")
        logger.info(f"  - Processing time: {time.time() - start_time:.2f}s")
        logger.info(f"  - Saved to: {output_file}")
        
        return comprehensive_data
    
    def extract_all_36521_1_test_cases(self) -> List[Dict[str, Any]]:
        """
        Extract test cases from ALL 36.521-1 document fragments
        
        Returns:
            List of all test cases from 36.521-1
        """
        doc_dir = self.base_path / "data_source/3GPP/TS 36.521-1/36521-1-i80"
        
        # All 15 document files (not just one!)
        doc_files = [
            "36521-1-i80_s00-s05.docx",
            "36521-1-i80_s06a-s06b4.docx", 
            "36521-1-i80_s06b5-s06d.docx",
            "36521-1-i80_s06e-s06f2.docx",
            "36521-1-i80_s06f3-s06h.docx",
            "36521-1-i80_s07a-s07ca8.docx",
            "36521-1-i80_s07ca9-s07d.docx",
            "36521-1-i80_s07e-s07j.docx",
            "36521-1-i80_s08a-s08g.docx",
            "36521-1-i80_s08h-s08_14.docx",
            "36521-1-i80_s09-s14.docx",
            "36521-1-i80_sAnnexAa-sAnnexAc.docx",
            "36521-1-i80_sAnnexAd-sAnnexE.docx",
            "36521-1-i80_sAnnexF-sAnnexL.docx"
        ]
        
        all_test_cases = []
        
        # Process documents in parallel for speed
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {
                executor.submit(self._extract_test_cases_from_single_doc, doc_dir / doc_file, "36.521-1"): doc_file 
                for doc_file in doc_files if (doc_dir / doc_file).exists()
            }
            
            for future in as_completed(future_to_file):
                doc_file = future_to_file[future]
                try:
                    test_cases = future.result()
                    all_test_cases.extend(test_cases)
                    logger.info(f"  ✓ {doc_file}: {len(test_cases)} test cases")
                except Exception as e:
                    logger.error(f"  ✗ {doc_file}: {e}")
        
        # Deduplicate test cases
        all_test_cases = self._deduplicate_test_cases(all_test_cases)
        
        logger.info(f"  📊 Total 36.521-1 test cases: {len(all_test_cases)}")
        return all_test_cases
    
    def extract_other_specifications_test_cases(self) -> List[Dict[str, Any]]:
        """
        Extract test cases from other major specifications
        
        Returns:
            List of test cases from other specifications
        """
        # Priority specifications based on PDX data analysis
        priority_specs = [
            ("TS 38.521-1", "38.521-1"),  # 5,082 test cases in PDX
            ("TS 36.523-1", "36.523-1"),  # 1,344 test cases in PDX  
            ("TS 36.521-3", "36.521-3"),  # 1,172 test cases in PDX
            ("TS 51.010-1", "51.010-1"),  # 1,021 test cases in PDX
            ("TS 38.521-3", "38.521-3"),  # 931 test cases in PDX
        ]
        
        all_test_cases = []
        
        for spec_dir, spec_name in priority_specs:
            spec_path = self.base_path / f"data_source/3GPP/{spec_dir}"
            if spec_path.exists():
                logger.info(f"  Processing {spec_name}...")
                test_cases = self._extract_from_specification_directory(spec_path, spec_name)
                all_test_cases.extend(test_cases)
                logger.info(f"    ✓ {len(test_cases)} test cases from {spec_name}")
            else:
                logger.warning(f"    ⚠️ {spec_name} directory not found: {spec_path}")
        
        return all_test_cases
    
    def _extract_test_cases_from_single_doc(self, doc_path: Path, specification: str) -> List[Dict[str, Any]]:
        """
        Extract test cases from a single document with improved patterns
        
        Args:
            doc_path: Path to document
            specification: Specification name
            
        Returns:
            List of test cases from the document
        """
        if not doc_path.exists():
            logger.warning(f"Document not found: {doc_path}")
            return []
        
        try:
            parsed_doc = self.parser.parse_document(str(doc_path))
            if not parsed_doc.success:
                logger.warning(f"Failed to parse: {doc_path}")
                return []
            
            # CRITICAL FIX: Use ALL content, not just first 100k characters
            content = parsed_doc.content
            self.processed_docs.add(str(doc_path))
            
            test_cases = []
            
            # Enhanced test case patterns
            patterns = [
                # Standard test case format: "6.2.2 Test Name"
                r'(\d+\.\d+(?:\.\d+)*)\s+([A-Z][^0-9\n]{10,200}?)(?=\n|$|\d+\.\d+)',
                
                # Test case with "Test purpose" 
                r'(\d+\.\d+(?:\.\d+)*)\s+Test\s+purpose[:\s]+(.+?)(?=\d+\.\d+|Test\s+purpose|$)',
                
                # Test case with section headers
                r'(\d+\.\d+(?:\.\d+)*)\s+([A-Z][^0-9]{10,200}?)(?=\n\s*\d+\.\d+|\n\s*Test|$)',
                
                # Numbered test procedures
                r'Test\s+case\s+(\d+\.\d+(?:\.\d+)*)[:\s]+(.+?)(?=Test\s+case|\n\n|$)',
            ]
            
            seen_test_ids = set()
            
            for pattern_idx, pattern in enumerate(patterns):
                matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                
                # CRITICAL FIX: Process ALL matches, not just first 100
                for test_id, test_name in matches:
                    test_id = test_id.strip()
                    test_name = self._clean_test_name(test_name)
                    
                    # Validate test case
                    if (self._is_valid_test_case(test_id, test_name) and 
                        test_id not in seen_test_ids):
                        
                        seen_test_ids.add(test_id)
                        test_cases.append({
                            "test_id": test_id,
                            "test_name": test_name,
                            "specification": specification,
                            "source_doc": doc_path.name,
                            "extraction_pattern": f"pattern_{pattern_idx}",
                            "required_pics": self._extract_pics_from_test_description(test_name),
                            "test_purpose": self._extract_test_purpose(content, test_id)
                        })
            
            return test_cases
            
        except Exception as e:
            logger.error(f"Error processing {doc_path}: {e}")
            return []
    
    def _extract_from_specification_directory(self, spec_dir: Path, spec_name: str) -> List[Dict[str, Any]]:
        """
        Extract test cases from all documents in a specification directory
        
        Args:
            spec_dir: Directory containing specification documents
            spec_name: Name of the specification
            
        Returns:
            List of test cases from the specification
        """
        test_cases = []
        
        # Find all .docx files in the directory
        for doc_path in spec_dir.rglob("*.docx"):
            if not doc_path.name.startswith("~"):  # Skip temp files
                doc_test_cases = self._extract_test_cases_from_single_doc(doc_path, spec_name)
                test_cases.extend(doc_test_cases)
        
        return test_cases
    
    def extract_enhanced_conditions_from_36521_2(self) -> List[Dict[str, Any]]:
        """
        Extract conditions with enhanced parsing from 36.521-2
        
        Returns:
            List of condition definitions
        """
        doc_path = self.base_path / "data_source/3GPP/TS 36.521-2/36521-2-i80/36521-2-i80.docx"
        
        if not doc_path.exists():
            logger.warning(f"36.521-2 document not found: {doc_path}")
            return []
        
        try:
            parsed_doc = self.parser.parse_document(str(doc_path))
            if not parsed_doc.success:
                return []
            
            content = parsed_doc.content
            conditions = []
            
            # Enhanced condition patterns
            patterns = [
                # Standard IF-THEN-ELSE format
                r'(C\d{1,3})[:\s]*IF\s+(.+?)\s+THEN\s+([^E]+?)\s+ELSE\s+([^\n\r]+?)(?=\s*C\d+|\s*$)',
                
                # Alternative formats
                r'(C\d{1,3})[:\s]*(.+?)\s*→\s*([RM]|N/A)',
                
                # Table format conditions
                r'(C\d{1,3})\s*\|\s*(.+?)\s*\|\s*([RM]|N/A)',
            ]
            
            seen_conditions = set()
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                
                for match in matches:
                    if len(match) >= 3:
                        cond_id = match[0].strip()
                        
                        if cond_id not in seen_conditions:
                            seen_conditions.add(cond_id)
                            
                            if len(match) == 4:  # IF-THEN-ELSE format
                                if_clause = ' '.join(match[1].split()).strip()
                                then_val = match[2].strip()
                                else_val = match[3].strip()
                            else:  # Simplified format
                                if_clause = ' '.join(match[1].split()).strip()
                                then_val = match[2].strip()
                                else_val = "N/A"
                            
                            # Extract PICS references with improved pattern
                            pics_refs = re.findall(r'A\.\d+(?:\.\d+)*(?:[-/]\d+[a-z]*)*(?:/\d+[a-z]*)*', if_clause)
                            
                            conditions.append({
                                "condition_id": cond_id,
                                "if_clause": if_clause,
                                "then_value": then_val,
                                "else_value": else_val,
                                "pics_references": list(set(pics_refs))  # Remove duplicates
                            })
            
            logger.info(f"  ✓ Extracted {len(conditions)} conditions")
            return conditions
            
        except Exception as e:
            logger.error(f"Error extracting conditions: {e}")
            return []
    
    def extract_enhanced_pics_definitions(self) -> List[Dict[str, Any]]:
        """
        Extract PICS definitions with enhanced parsing
        
        Returns:
            List of PICS definitions
        """
        doc_path = self.base_path / "data_source/3GPP/TS 36.521-2/36521-2-i80/36521-2-i80.docx"
        
        if not doc_path.exists():
            logger.warning(f"36.521-2 document not found: {doc_path}")
            return []
        
        try:
            parsed_doc = self.parser.parse_document(str(doc_path))
            if not parsed_doc.success:
                return []
            
            content = parsed_doc.content
            pics_items = []
            
            # Find Annex A section
            annex_patterns = [
                r'Annex\s+A[:\s]',
                r'A\.4\s+PICS',
                r'A\.0\s+UE\s+Release'
            ]
            
            annex_pos = -1
            for pattern in annex_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    annex_pos = match.start()
                    break
            
            if annex_pos != -1:
                # Extract larger section for PICS (not limited to 200k)
                annex_content = content[annex_pos:]
                
                # Enhanced PICS patterns
                patterns = [
                    # Standard format: A.4.1-1/1 Description
                    r'(A\.\d+(?:\.\d+)*(?:[-/]\d+[a-z]*)*(?:/\d+[a-z]*)*)\s+([^A\n]{10,300}?)(?=\n\s*A\.\d+|\n\n|$)',
                    
                    # Table format
                    r'(A\.\d+(?:\.\d+)*(?:[-/]\d+[a-z]*)*(?:/\d+[a-z]*)*)\s*\|\s*([^|\n]{10,300})',
                    
                    # With categories
                    r'(A\.\d+(?:\.\d+)*(?:[-/]\d+[a-z]*)*(?:/\d+[a-z]*)*)\s+(.+?)(?=\s+(?:TRUE|FALSE|Optional|Mandatory))',
                ]
                
                seen_pics = set()
                
                for pattern in patterns:
                    matches = re.findall(pattern, annex_content, re.IGNORECASE | re.DOTALL)
                    
                    for pics_id, description in matches:
                        pics_id = pics_id.strip()
                        description = self._clean_pics_description(description)
                        
                        if (pics_id not in seen_pics and 
                            self._is_valid_pics_id(pics_id) and
                            len(description) > 5):
                            
                            seen_pics.add(pics_id)
                            pics_items.append({
                                "pics_id": pics_id,
                                "description": description,
                                "category": self._categorize_pics(pics_id),
                                "section": self._get_pics_section(pics_id)
                            })
            
            logger.info(f"  ✓ Extracted {len(pics_items)} PICS definitions")
            return pics_items
            
        except Exception as e:
            logger.error(f"Error extracting PICS: {e}")
            return []
    
    def extract_comprehensive_test_condition_mappings(self) -> List[Dict[str, Any]]:
        """
        Extract comprehensive test-condition mappings from multiple sources
        
        Returns:
            List of test-condition mappings
        """
        mappings = []
        
        # Extract from Table 4.1-1 (main mapping table)
        main_mappings = self._extract_from_table_4_1_1()
        mappings.extend(main_mappings)
        
        # Extract from other mapping sources
        additional_mappings = self._extract_additional_mappings()
        mappings.extend(additional_mappings)
        
        # Deduplicate mappings
        mappings = self._deduplicate_mappings(mappings)
        
        logger.info(f"  ✓ Extracted {len(mappings)} test-condition mappings")
        return mappings
    
    def _extract_from_table_4_1_1(self) -> List[Dict[str, Any]]:
        """Extract mappings from Table 4.1-1 in 36.521-2"""
        doc_path = self.base_path / "data_source/3GPP/TS 36.521-2/36521-2-i80/36521-2-i80.docx"
        
        if not doc_path.exists():
            return []
        
        try:
            parsed_doc = self.parser.parse_document(str(doc_path))
            if not parsed_doc.success:
                return []
            
            content = parsed_doc.content
            mappings = []
            
            # Find Table 4.1-1
            table_patterns = [
                r'Table\s+4\.1-1',
                r'Table\s+4\.1\.1',
                r'Mapping\s+of\s+test\s+cases'
            ]
            
            table_pos = -1
            for pattern in table_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    table_pos = match.start()
                    break
            
            if table_pos != -1:
                # Extract table content (larger section)
                table_content = content[table_pos:table_pos + 500000]  # 500k chars
                
                # Enhanced mapping patterns
                patterns = [
                    # Direct test-condition mapping
                    r'(\d+\.\d+(?:\.\d+)*)\s+.{0,200}?\s+(C\d+)',
                    
                    # Table row format
                    r'(\d+\.\d+(?:\.\d+)*)\s*\|\s*.{0,200}?\s*\|\s*(C\d+)',
                    
                    # Multiple conditions per test
                    r'(\d+\.\d+(?:\.\d+)*)\s+.{0,200}?\s+(C\d+(?:\s*,\s*C\d+)*)',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, table_content, re.IGNORECASE | re.DOTALL)
                    
                    for test_id, condition_ids in matches:
                        test_id = test_id.strip()
                        
                        # Handle multiple conditions
                        if ',' in condition_ids:
                            for cond_id in condition_ids.split(','):
                                cond_id = cond_id.strip()
                                if cond_id.startswith('C'):
                                    mappings.append({
                                        "test_id": test_id,
                                        "condition_id": cond_id,
                                        "source": "Table_4.1-1"
                                    })
                        else:
                            condition_ids = condition_ids.strip()
                            if condition_ids.startswith('C'):
                                mappings.append({
                                    "test_id": test_id,
                                    "condition_id": condition_ids,
                                    "source": "Table_4.1-1"
                                })
            
            return mappings
            
        except Exception as e:
            logger.error(f"Error extracting Table 4.1-1 mappings: {e}")
            return []
    
    def _extract_additional_mappings(self) -> List[Dict[str, Any]]:
        """Extract mappings from additional sources"""
        # This would extract from other mapping tables and implicit mappings
        # For now, return empty list - can be extended later
        return []
    
    # Utility methods
    def _clean_test_name(self, test_name: str) -> str:
        """Clean and normalize test name"""
        if not test_name:
            return ""
        
        # Remove excessive whitespace
        test_name = ' '.join(test_name.split())
        
        # Remove common artifacts
        artifacts = [
            r'\s+Test\s+purpose\s*:?\s*',
            r'\s+Test\s+case\s*:?\s*',
            r'\s+\d+\.\d+(?:\.\d+)*\s*',
        ]
        
        for artifact in artifacts:
            test_name = re.sub(artifact, ' ', test_name, flags=re.IGNORECASE)
        
        return test_name.strip()[:200]  # Limit length
    
    def _clean_pics_description(self, description: str) -> str:
        """Clean and normalize PICS description"""
        if not description:
            return ""
        
        # Remove excessive whitespace and artifacts
        description = ' '.join(description.split())
        description = description.replace('|', '').replace('\t', ' ')
        
        return description.strip()[:200]
    
    def _is_valid_test_case(self, test_id: str, test_name: str) -> bool:
        """Validate if this is a real test case"""
        if not test_id or not test_name:
            return False
        
        # Test ID should be numeric format
        if not re.match(r'^\d+\.\d+(?:\.\d+)*$', test_id):
            return False
        
        # Test name should be meaningful
        if len(test_name) < 10:
            return False
        
        # Exclude obvious non-test cases
        exclude_patterns = [
            r'^The\s+',
            r'^This\s+',
            r'^Table\s+',
            r'^Figure\s+',
            r'^Annex\s+',
            r'^\d+\.\d+\s*$',  # Just numbers
        ]
        
        for pattern in exclude_patterns:
            if re.match(pattern, test_name, re.IGNORECASE):
                return False
        
        return True
    
    def _is_valid_pics_id(self, pics_id: str) -> bool:
        """Validate PICS ID format"""
        return bool(re.match(r'^A\.\d+(?:\.\d+)*(?:[-/]\d+[a-z]*)*(?:/\d+[a-z]*)*$', pics_id))
    
    def _categorize_pics(self, pics_id: str) -> str:
        """Categorize PICS based on ID pattern"""
        if pics_id.startswith('A.0'):
            return "Release"
        elif pics_id.startswith('A.4.1'):
            return "Radio Technology"
        elif pics_id.startswith('A.4.2'):
            return "Frequency Bands"
        elif pics_id.startswith('A.4.3'):
            return "UE Categories"
        elif pics_id.startswith('A.4.4'):
            return "Carrier Aggregation"
        elif pics_id.startswith('A.4.5'):
            return "Features"
        else:
            return "Other"
    
    def _get_pics_section(self, pics_id: str) -> str:
        """Get PICS section from ID"""
        parts = pics_id.split('.')
        if len(parts) >= 2:
            return f"A.{parts[1]}"
        return "A"
    
    def _extract_pics_from_test_description(self, test_description: str) -> List[str]:
        """Extract PICS references from test description"""
        pics_pattern = r'A\.\d+(?:\.\d+)*(?:[-/]\d+[a-z]*)*(?:/\d+[a-z]*)*'
        return re.findall(pics_pattern, test_description)
    
    def _extract_test_purpose(self, content: str, test_id: str) -> str:
        """Extract test purpose for a specific test ID"""
        # Look for test purpose near the test ID
        pattern = rf'{re.escape(test_id)}.*?Test\s+purpose[:\s]+(.{{10,300}}?)(?=\d+\.\d+|Test\s+purpose|$)'
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        
        if match:
            purpose = ' '.join(match.group(1).split())
            return purpose[:200]
        
        return ""
    
    def _deduplicate_test_cases(self, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate test cases"""
        seen = set()
        unique_cases = []
        
        for test_case in test_cases:
            key = (test_case['test_id'], test_case['specification'])
            if key not in seen:
                seen.add(key)
                unique_cases.append(test_case)
        
        return unique_cases
    
    def _deduplicate_mappings(self, mappings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate mappings"""
        seen = set()
        unique_mappings = []
        
        for mapping in mappings:
            key = (mapping['test_id'], mapping['condition_id'])
            if key not in seen:
                seen.add(key)
                unique_mappings.append(mapping)
        
        return unique_mappings
    
    def _count_by_specification(self, test_cases: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count test cases by specification"""
        counts = {}
        for test_case in test_cases:
            spec = test_case.get('specification', 'Unknown')
            counts[spec] = counts.get(spec, 0) + 1
        return counts
    
    def _calculate_quality_metrics(self, test_cases: List[Dict[str, Any]], 
                                 conditions: List[Dict[str, Any]], 
                                 mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate data quality metrics"""
        return {
            "test_cases_with_pics": len([tc for tc in test_cases if tc.get('required_pics')]),
            "test_cases_with_purpose": len([tc for tc in test_cases if tc.get('test_purpose')]),
            "conditions_with_pics": len([c for c in conditions if c.get('pics_references')]),
            "mapped_test_cases": len(set(m['test_id'] for m in mappings)),
            "coverage_rate": len(set(m['test_id'] for m in mappings)) / len(test_cases) * 100 if test_cases else 0
        }


def main():
    """Run enhanced data extraction"""
    print("="*70)
    print("ENHANCED 3GPP DATA EXTRACTION")
    print("="*70)
    print("Addressing critical data incompleteness issues:")
    print("- Processing ALL 36.521-1 document fragments (not just one)")
    print("- Removing artificial content limits")
    print("- Improved test case identification")
    print("- Multi-specification support")
    print("="*70)
    
    extractor = EnhancedDataExtractor()
    
    try:
        comprehensive_data = extractor.extract_comprehensive_data()
        
        print(f"\n🎯 EXTRACTION RESULTS:")
        print(f"📊 Test Cases: {len(comprehensive_data['test_cases'])} (vs 41 previously)")
        print(f"📊 Conditions: {len(comprehensive_data['conditions'])}")
        print(f"📊 PICS: {len(comprehensive_data['pics_definitions'])}")
        print(f"📊 Mappings: {len(comprehensive_data['test_to_condition_mapping'])}")
        print(f"📊 Documents: {comprehensive_data['statistics']['documents_processed']}")
        
        # Compare with PDX expectations
        pdx_36521_1_count = 5695
        our_36521_1_count = comprehensive_data['statistics']['test_cases_by_spec'].get('36.521-1', 0)
        coverage_percent = our_36521_1_count / pdx_36521_1_count * 100 if pdx_36521_1_count > 0 else 0
        
        print(f"\n📈 COVERAGE ANALYSIS:")
        print(f"Expected 36.521-1 tests (PDX): {pdx_36521_1_count}")
        print(f"Extracted 36.521-1 tests: {our_36521_1_count}")
        print(f"Coverage: {coverage_percent:.1f}%")
        
        if coverage_percent < 80:
            print(f"⚠️  Coverage below 80% - may need additional extraction improvements")
        else:
            print(f"✅ Good coverage achieved!")
        
        print(f"\n✅ Enhanced extraction completed successfully!")
        
    except Exception as e:
        logger.error(f"Enhanced extraction failed: {e}")
        raise


if __name__ == "__main__":
    main()
