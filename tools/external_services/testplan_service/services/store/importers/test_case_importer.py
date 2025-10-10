"""
Test Case Importer

Handles importing test cases and conditions from 3GPP specifications.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

from .base_importer import BaseImporter
import sys
from pathlib import Path
# Add the base path to sys.path for imports
base_module_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(base_module_path))

# from services.extractor.applicability_extractor import ApplicabilityExtractor  # TODO: Fix this import
# from services.parser.document_parser import UniversalDocumentParser  # TODO: Fix this import

logger = logging.getLogger(__name__)


class TestCaseImporter(BaseImporter):
    """Importer for test cases and conditions"""
    
    def import_specification_data(self, spec_info: Dict[str, Any]):
        """
        Import all data for a single specification
        
        Args:
            spec_info: Specification information dictionary
        """
        spec_id = spec_info['spec_id']
        logger.info(f"\nImporting data for {spec_id}...")
        
        # Import specification metadata
        self.execute("""
            INSERT OR REPLACE INTO specifications 
            (spec_id, spec_name, spec_version, spec_type, sheet_name)
            VALUES (?, ?, ?, ?, ?)
        """, (spec_id, spec_info['spec_name'], f"{spec_id}-1", "TEST", spec_info['target_sheet']))
        
        try:
            # Extract data from specification documents
            extracted_data = self._extract_specification_data(spec_info)
            
            # Import test cases
            if extracted_data.get('test_cases'):
                self._import_test_cases(spec_id, extracted_data['test_cases'])
            
            # Import conditions
            if extracted_data.get('conditions'):
                self._import_conditions(spec_id, extracted_data['conditions'])
            
            self.commit()
            
        except Exception as e:
            logger.error(f"Failed to extract data for {spec_id}: {e}")
            # Create minimal entry for specs we can't extract
            self._create_minimal_specification_entry(spec_id)
    
    def _extract_specification_data(self, spec_info: Dict[str, str]) -> Dict[str, Any]:
        """Extract data from 3GPP specification documents"""
        spec_id = spec_info['spec_id']
        source_path = Path(spec_info['source_path'])
        
        logger.info(f"  📂 Extracting data from {source_path}")
        
        extracted_data = {
            'test_cases': [],
            'conditions': []
        }
        
        try:
            # Extract test cases AND conditions from documents
            logger.info(f"    🔍 Extracting test cases and conditions from documents...")
            test_data = self._extract_test_data_from_docs(source_path, spec_id)
            extracted_data['test_cases'] = test_data.get('test_cases', [])
            extracted_data['conditions'] = test_data.get('conditions', [])
            
            logger.info(f"  ✅ Extracted {len(extracted_data['test_cases'])} test cases, "
                       f"{len(extracted_data['conditions'])} conditions")
            
        except Exception as e:
            logger.warning(f"  ⚠️ Extraction failed for {spec_id}: {e}")
        
        return extracted_data
    
    def _extract_test_data_from_docs(self, source_path: Path, spec_id: str) -> Dict[str, Any]:
        """Extract test cases and conditions from documents using ApplicabilityExtractor"""
        result = {
            'test_cases': [],
            'conditions': []
        }
        
        try:
            # Find all document files (now supports .docx, .doc, .pdf)
            doc_files = []
            for ext in ['*.docx', '*.doc', '*.pdf']:
                doc_files.extend(list(source_path.rglob(ext)))
            
            if not doc_files:
                logger.warning(f"    ⚠️ No documents found in {source_path}")
                return result
            
            # Sort files to ensure consistent ordering
            doc_files.sort(key=lambda p: p.name)
            
            # Handle multi-part documents if needed
            if len(doc_files) > 1:
                logger.info(f"    📚 Found {len(doc_files)} document parts")
                # Check if they are multi-part specs
                parser = UniversalDocumentParser()
                merged_doc = parser.merge_documents(doc_files)
                logger.info(f"    🔗 Merged {len(doc_files)} documents")
                # For now, still use the first file with ApplicabilityExtractor
                # TODO: Update ApplicabilityExtractor to work with ParsedDocument directly
                doc_file = doc_files[0]
            else:
                doc_file = doc_files[0]
            
            logger.info(f"    📄 Processing document: {doc_file.name}")
            
            # Use ApplicabilityExtractor
            extractor = ApplicabilityExtractor(str(doc_file))
            extraction_result = extractor.extract_all()
            
            if extraction_result:
                # Extract test cases
                if 'applicability' in extraction_result and 'test_cases' in extraction_result['applicability']:
                    result['test_cases'] = extraction_result['applicability']['test_cases']
                    logger.info(f"    ✅ Extracted {len(result['test_cases'])} test cases")
                
                # Extract conditions
                if 'conditions' in extraction_result:
                    if 'c_conditions' in extraction_result['conditions']:
                        result['conditions'].extend(extraction_result['conditions']['c_conditions'])
                        logger.info(f"    ✅ Extracted {len(extraction_result['conditions']['c_conditions'])} C-conditions")
                    
                    if 'pics_conditions' in extraction_result['conditions']:
                        result['conditions'].extend(extraction_result['conditions']['pics_conditions'])
                        logger.info(f"    ✅ Extracted {len(extraction_result['conditions']['pics_conditions'])} PICS conditions")
                
        except Exception as e:
            logger.error(f"    ❌ Document extraction failed: {e}")
        
        return result
    
    def _import_test_cases(self, spec_id: str, test_cases: List[Dict]):
        """Import test cases to database"""
        for tc in test_cases:
            self.execute("""
                INSERT OR REPLACE INTO test_cases
                (test_id, spec_id, clause, title, release, 
                 applicability_condition, applicability_comment, 
                 specific_ics, specific_ixit, num_executions, 
                 release_other_rat, standard, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tc.get('test_id'), spec_id, tc.get('clause'), 
                tc.get('title'), tc.get('release'),
                tc.get('applicability_condition'), tc.get('applicability_comment'),
                tc.get('specific_ics'), tc.get('specific_ixit'),
                tc.get('num_executions'), tc.get('release_other_rat'),
                tc.get('standard'), tc.get('version')
            ))
        
        logger.info(f"  ✅ Imported {len(test_cases)} test cases")
    
    def _import_conditions(self, spec_id: str, conditions: List[Dict]):
        """Import conditions to database"""
        for condition in conditions:
            self.execute("""
                INSERT OR REPLACE INTO conditions
                (condition_id, spec_id, condition_type, definition, table_index, raw_data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                condition.get('condition_id'),
                spec_id,
                condition.get('condition_type', 'Unknown'),
                condition.get('definition', ''),
                condition.get('table_index', 0),
                json.dumps(condition.get('raw_data', {}))
            ))
        
        logger.info(f"  ✅ Imported {len(conditions)} conditions")
    
    def _create_minimal_specification_entry(self, spec_id: str):
        """Create minimal entry for specs we can't extract"""
        logger.info(f"  📝 Creating minimal entry for {spec_id}")
        
        # Import minimal test cases based on common patterns
        from .specification_discovery import SpecificationDiscovery
        discovery = SpecificationDiscovery(self.base_path)
        test_patterns = discovery.get_common_test_patterns(spec_id)
        
        test_cases = []
        for test_id in test_patterns[:20]:  # Limit to 20 patterns
            test_case = {
                'test_id': test_id,
                'clause': test_id,
                'title': f'Test {test_id}',
                'release': 'Rel-8',
                'applicability_condition': 'M',
                'applicability_comment': '',
                'specific_ics': '',
                'specific_ixit': '',
                'num_executions': '1',
                'release_other_rat': '',
                'standard': spec_id,
                'version': f'{spec_id}-2'
            }
            test_cases.append(test_case)
        
        if test_cases:
            self._import_test_cases(spec_id, test_cases)