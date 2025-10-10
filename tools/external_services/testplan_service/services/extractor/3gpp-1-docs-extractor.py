#!/usr/bin/env python3
"""
Test Procedure Extractor for 3GPP Implementation Specifications (-1)

Extracts test case IDs and titles from test procedure documents
that contain actual test implementations rather than applicability tables.
"""

from docx import Document
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestProcedure:
    """Represents a test procedure from implementation specs"""
    test_id: str
    title: str
    section: str
    document_file: str
    
    def to_dict(self) -> Dict:
        return {
            'test_id': self.test_id,
            'title': self.title,
            'section': self.section,
            'document_file': self.document_file
        }


class TestProcedureExtractor:
    """
    Extracts test procedures from 3GPP implementation specification documents (-1)
    
    These documents contain test procedures like:
    6.2.2    UE Maximum Output Power
    6.2.2.1  Test purpose
    6.2.2.2  Test applicability
    """
    
    def __init__(self, spec_dir: str):
        """
        Initialize with specification directory containing multiple documents
        
        Args:
            spec_dir: Path to directory containing -1 spec documents
        """
        self.spec_dir = Path(spec_dir)
        if not self.spec_dir.exists():
            raise FileNotFoundError(f"Specification directory not found: {spec_dir}")
        
        logger.info(f"📄 Initializing TestProcedureExtractor for: {self.spec_dir.name}")
    
    def extract_test_procedures(self) -> Tuple[List[TestProcedure], Dict]:
        """
        Extract all test procedures from all documents in the specification
        
        Returns:
            Tuple of (list of TestProcedure objects, raw data dict)
        """
        logger.info("🔍 Searching for test procedures across all documents...")
        
        # Find all .docx files recursively (exclude temp files)
        doc_files = [f for f in self.spec_dir.rglob('*.docx') if not f.name.startswith('~$')]
        logger.info(f"   Found {len(doc_files)} documents to process")
        
        all_procedures = []
        raw_data = {
            'spec_directory': str(self.spec_dir),
            'documents_processed': [],
            'total_procedures': 0
        }
        
        for doc_file in sorted(doc_files):
            logger.info(f"   📖 Processing: {doc_file.name}")
            
            try:
                procedures = self._extract_from_document(doc_file)
                all_procedures.extend(procedures)
                
                raw_data['documents_processed'].append({
                    'file': doc_file.name,
                    'procedures_found': len(procedures)
                })
                
                logger.info(f"      ✅ Found {len(procedures)} test procedures")
                
            except Exception as e:
                logger.warning(f"      ⚠️  Error processing {doc_file.name}: {e}")
                raw_data['documents_processed'].append({
                    'file': doc_file.name,
                    'error': str(e)
                })
        
        # Remove duplicates (same test_id might appear in multiple docs)
        unique_procedures = {}
        for proc in all_procedures:
            if proc.test_id not in unique_procedures:
                unique_procedures[proc.test_id] = proc
        
        final_procedures = list(unique_procedures.values())
        raw_data['total_procedures'] = len(final_procedures)
        
        logger.info(f"📊 Extracted {len(final_procedures)} unique test procedures")
        return final_procedures, raw_data
    
    def _extract_from_document(self, doc_file: Path) -> List[TestProcedure]:
        """Extract test procedures from a single document"""
        
        doc = Document(str(doc_file))
        procedures = []
        
        # Look for test case patterns in paragraph text
        # Enhanced pattern to match complex test IDs like:
        # 6.2.2, 6.2.2A, 6.2.2.1, 6.2.2A.1, 6.3.4.1, 6.3.5A.1.1, etc.
        test_pattern = re.compile(r'^(\d+\.\d+\.\d+(?:[A-Z])?(?:\.\d+)*(?:[A-Z](?:\.\d+)*)?)\s+(.+)$')
        
        for para in doc.paragraphs:
            text = para.text.strip()
            
            # Skip empty paragraphs
            if not text:
                continue
            
            # Match test case pattern
            match = test_pattern.match(text)
            if match:
                test_id = match.group(1)
                title = match.group(2).strip()
                
                # Filter out very deep sub-sections (like 6.2.2.1.1.1)
                # But keep reasonable levels like 6.2.2.1, 6.2.2A.1, etc.
                if not re.match(r'^\d+\.\d+\.\d+\.\d+\.\d+\.\d+', test_id):
                    # Skip common sub-section titles
                    if title.lower() not in ['test purpose', 'test applicability', 
                                           'minimum conformance requirements', 'test description',
                                           'initial condition', 'test procedure', 'test requirements',
                                           'void']:
                        
                        procedure = TestProcedure(
                            test_id=test_id,
                            title=title,
                            section=text,
                            document_file=doc_file.name
                        )
                        procedures.append(procedure)
        
        return procedures
    
    def get_test_ids(self) -> List[str]:
        """Get just the test IDs for mapping purposes"""
        procedures, _ = self.extract_test_procedures()
        return [proc.test_id for proc in procedures]
    
    def get_test_mapping_data(self) -> Tuple[List[str], Dict[str, str]]:
        """
        Get data formatted for TestMappingExtractor
        
        Returns:
            Tuple of (test_ids, id_to_title_mapping)
        """
        procedures, _ = self.extract_test_procedures()
        
        test_ids = [proc.test_id for proc in procedures]
        id_to_title = {proc.test_id: proc.title for proc in procedures}
        
        return test_ids, id_to_title


def main():
    """CLI interface for the extractor"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract test procedures from 3GPP implementation documents'
    )
    parser.add_argument('spec_dir', help='Path to specification directory')
    parser.add_argument(
        '-o', '--output',
        help='Output JSON file',
        default=None
    )
    
    args = parser.parse_args()
    
    # Create extractor
    extractor = TestProcedureExtractor(args.spec_dir)
    
    # Extract procedures
    procedures, raw_data = extractor.extract_test_procedures()
    
    # Save to file if specified
    if args.output:
        import json
        output_data = {
            'test_procedures': [proc.to_dict() for proc in procedures],
            'raw_data': raw_data
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved {len(procedures)} procedures to: {args.output}")
    
    return procedures


if __name__ == "__main__":
    main()