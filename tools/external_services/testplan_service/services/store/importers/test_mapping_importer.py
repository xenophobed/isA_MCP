"""
Test Mapping Importer

Handles importing test mappings between specification versions.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from .base_importer import BaseImporter
import sys
from pathlib import Path
# Add the base path to sys.path for imports
base_module_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(base_module_path))

from services.extractor.test_mapping_extractor import TestMappingExtractor
from services.extractor.test_procedure_extractor import TestProcedureExtractor
from .specification_discovery import SpecificationDiscovery

logger = logging.getLogger(__name__)


class TestMappingImporter(BaseImporter):
    """Importer for test mappings between specifications"""
    
    def extract_and_import_mappings(self, spec_id: str, spec_full_name: str, test_cases: List[Dict] = None):
        """
        Extract and import test mappings between specification versions
        
        Args:
            spec_id: Specification ID
            spec_full_name: Full specification name (e.g., "36.521-2")
            test_cases: List of test cases from the source specification
        """
        mappings = {}
        
        try:
            # Determine if this is a -2 spec that needs mapping to -1
            if spec_full_name.endswith('-2'):
                source_spec = spec_full_name
                target_spec = spec_full_name.replace('-2', '-1')
                
                logger.info(f"    🔗 Extracting mappings from {source_spec} to {target_spec}")
                
                # Extract mappings
                mappings = self._extract_mappings(spec_id, source_spec, target_spec, test_cases)
                
                if mappings:
                    # Import the mappings
                    self._import_test_mappings(spec_id, mappings)
                    
        except Exception as e:
            logger.error(f"    ❌ Test mapping extraction failed: {e}")
    
    def _extract_mappings(self, spec_id: str, source_spec: str, target_spec: str, 
                         test_cases: List[Dict] = None) -> Dict[str, str]:
        """Extract mappings between source and target specifications"""
        # Create TestMappingExtractor
        extractor = TestMappingExtractor()
        
        # Get source tests
        source_tests = self._get_source_tests(spec_id, test_cases)
        
        # Get target tests
        target_tests = self._get_target_tests(spec_id, target_spec)
        
        if source_tests and target_tests:
            # Extract mappings
            mapping_result = extractor.extract_mappings(
                source_tests, 
                target_tests,
                specification_pair=(source_spec, target_spec)
            )
            
            if mapping_result and 'mappings' in mapping_result:
                mappings = mapping_result['mappings']
                logger.info(f"    ✅ Extracted {len(mappings)} test mappings")
                return mappings
        else:
            logger.warning(f"    ⚠️ Insufficient test data for mapping extraction")
        
        return {}
    
    def _get_source_tests(self, spec_id: str, test_cases: List[Dict] = None) -> List[str]:
        """Get source test IDs"""
        if test_cases:
            return [tc.get('test_id') for tc in test_cases if tc.get('test_id')]
        else:
            # Fallback: try to get from database
            result = self.fetch_all(
                "SELECT DISTINCT test_id FROM test_cases WHERE spec_id = ?", 
                (spec_id,)
            )
            return [row[0] for row in result]
    
    def _get_target_tests(self, spec_id: str, target_spec: str) -> List[str]:
        """Get target test IDs from -1 specification"""
        target_tests = []
        
        # Find target specification path
        discovery = SpecificationDiscovery(self.base_path)
        target_spec_path = discovery.find_specification_path(target_spec)
        
        if target_spec_path and target_spec_path.exists():
            logger.info(f"    📄 Using TestProcedureExtractor for {target_spec_path.name}")
            try:
                proc_extractor = TestProcedureExtractor(str(target_spec_path))
                target_tests, _ = proc_extractor.get_test_mapping_data()
                logger.info(f"    ✅ Extracted {len(target_tests)} test procedures from -1 spec")
            except Exception as e:
                logger.warning(f"    ⚠️ TestProcedureExtractor failed: {e}")
        
        # Fallback if extraction didn't work
        if not target_tests:
            # Try database
            target_spec_id = spec_id.replace('2', '1')  # Convert 365212 -> 365211
            result = self.fetch_all(
                "SELECT DISTINCT test_id FROM test_cases WHERE spec_id = ?", 
                (target_spec_id,)
            )
            
            if result:
                target_tests = [row[0] for row in result]
                logger.info(f"    Using {len(target_tests)} test cases from database {target_spec_id}")
            else:
                # Last fallback to patterns
                target_tests = discovery.get_common_test_patterns(spec_id)
                logger.info(f"    Using {len(target_tests)} pattern-based target tests")
        
        return target_tests
    
    def _import_test_mappings(self, spec_id: str, test_mappings: Dict[str, str]):
        """Import test mappings to database"""
        # Determine source and target spec names
        source_spec = f"{spec_id}-2"
        target_spec = f"{spec_id}-1"
        
        for source_test, target_test in test_mappings.items():
            self.execute("""
                INSERT OR REPLACE INTO test_mappings
                (source_test_id, target_test_id, source_spec, target_spec, mapping_type, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (source_test, target_test, source_spec, target_spec, 'extracted', 0.9))
        
        self.commit()
        logger.info(f"  ✅ Imported {len(test_mappings)} test mappings")