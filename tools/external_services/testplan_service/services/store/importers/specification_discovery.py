"""
Specification Discovery Module

Auto-discovers 3GPP specifications from the data source directory
and supports merging multi-part specifications.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Set
import re

logger = logging.getLogger(__name__)


class SpecificationDiscovery:
    """Discovers and manages 3GPP specification data sources"""
    
    def __init__(self, base_path: Path):
        """
        Initialize specification discovery
        
        Args:
            base_path: Base path to testplan_service directory
        """
        self.base_path = base_path
        self.gpp_path = base_path / "data_source/3GPP"
    
    def auto_discover_specifications(self) -> List[Dict[str, any]]:
        """
        Auto-discover all specifications from data_source/3GPP/ directory
        
        Returns:
            List of specification information dictionaries
        """
        specs = []
        seen_specs = set()
        
        logger.info(f"Looking for 3GPP data in: {self.gpp_path}")
        
        if not self.gpp_path.exists():
            logger.warning(f"3GPP data directory not found: {self.gpp_path}")
            return specs
        
        # Scan all TS directories
        for spec_dir in self.gpp_path.iterdir():
            if spec_dir.is_dir() and spec_dir.name.startswith("TS "):
                # Extract spec ID from directory name: "TS 34.123-1" -> "341231"
                spec_name = spec_dir.name.replace("TS ", "")
                # Create unique spec_id by removing dots and hyphens
                spec_id = spec_name.replace(".", "").replace("-", "")
                
                # Skip duplicates
                if spec_id in seen_specs:
                    continue
                seen_specs.add(spec_id)
                
                # Check if there are any document files and find all parts
                document_files = self._find_document_files(spec_dir)
                if document_files:
                    specs.append({
                        'spec_id': spec_id,
                        'spec_name': f"3GPP TS {spec_name}",
                        'target_sheet': f"3GPP TS {spec_name}",
                        'source_path': str(spec_dir),
                        'spec_full_name': spec_name,
                        'document_files': document_files  # List of all document files
                    })
        
        logger.info(f"Auto-discovered {len(specs)} specifications from 3GPP directory:")
        for spec in specs:
            logger.info(f"  - {spec['spec_id']}: {spec['spec_name']} ({len(spec['document_files'])} files)")
        
        return specs
    
    def _find_document_files(self, spec_dir: Path) -> List[Path]:
        """
        Find all document files in a specification directory
        
        Args:
            spec_dir: Directory to check
            
        Returns:
            List of document file paths
        """
        document_files = []
        supported_extensions = ['.doc', '.docx', '.pdf']
        
        # Search for document files (recursive)
        for file_path in spec_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                document_files.append(file_path)
        
        # Sort files to ensure consistent ordering (important for multi-part specs)
        document_files.sort(key=lambda p: (p.parent.name, p.name))
        
        return document_files
    
    def _has_documents(self, spec_dir: Path) -> bool:
        """
        Check if a specification directory contains documents
        
        Args:
            spec_dir: Directory to check
            
        Returns:
            True if documents found, False otherwise
        """
        return len(self._find_document_files(spec_dir)) > 0
    
    def find_specification_path(self, spec_name: str) -> Path:
        """
        Find the path to a specific specification
        
        Args:
            spec_name: Specification name (e.g., "36.521-1")
            
        Returns:
            Path to specification directory or None if not found
        """
        # Try with TS prefix
        spec_path = self.gpp_path / f"TS {spec_name}"
        if spec_path.exists():
            return spec_path
        
        # Try without TS prefix
        spec_path = self.gpp_path / spec_name
        if spec_path.exists():
            return spec_path
        
        return None
    
    def identify_multi_part_documents(self, document_files: List[Path]) -> Dict[str, List[Path]]:
        """
        Identify and group multi-part documents
        
        Args:
            document_files: List of document file paths
            
        Returns:
            Dictionary mapping document base names to their parts
        """
        grouped_docs = {}
        
        for doc_path in document_files:
            # Look for patterns like "part1", "Part_1", "P1", etc.
            filename = doc_path.stem
            
            # Try to extract base name and part number
            # Pattern 1: "document_part1" or "document_Part_1"
            match = re.match(r'^(.+?)[-_]?[Pp]art[-_]?(\d+)$', filename)
            if match:
                base_name = match.group(1)
                part_num = int(match.group(2))
            # Pattern 2: "document_P1" or "document_p1"
            elif match := re.match(r'^(.+?)[-_]?[Pp](\d+)$', filename):
                base_name = match.group(1)
                part_num = int(match.group(2))
            # Pattern 3: Numbered files in same directory (e.g., "36521-1", "36521-2")
            elif match := re.match(r'^(\d+)-(\d+)$', filename):
                base_name = match.group(1)
                part_num = int(match.group(2))
            else:
                # Single document
                base_name = filename
                part_num = 0
            
            if base_name not in grouped_docs:
                grouped_docs[base_name] = []
            grouped_docs[base_name].append((part_num, doc_path))
        
        # Sort parts within each group
        for base_name in grouped_docs:
            grouped_docs[base_name].sort(key=lambda x: x[0])
            # Keep only the paths
            grouped_docs[base_name] = [path for _, path in grouped_docs[base_name]]
        
        return grouped_docs
    
    def merge_specification_documents(self, spec_info: Dict) -> Optional[Path]:
        """
        Merge multiple document parts for a specification if needed
        
        Args:
            spec_info: Specification information dictionary
            
        Returns:
            Path to merged document or primary document if no merge needed
        """
        document_files = spec_info.get('document_files', [])
        
        if not document_files:
            return None
        
        # If only one document, return it
        if len(document_files) == 1:
            return document_files[0]
        
        # Group multi-part documents
        grouped = self.identify_multi_part_documents(document_files)
        
        # Find the main document group (usually has most parts)
        main_group = None
        max_parts = 0
        for base_name, parts in grouped.items():
            if len(parts) > max_parts:
                max_parts = len(parts)
                main_group = parts
        
        if main_group and len(main_group) > 1:
            logger.info(f"Identified {len(main_group)} parts for merging in {spec_info['spec_name']}")
            # Return list of files to merge (caller will handle actual merging)
            return main_group
        
        # Return the first document if no clear multi-part structure
        return document_files[0]
    
    def get_common_test_patterns(self, spec_id: str) -> List[str]:
        """
        Get common test patterns for different specifications
        
        Args:
            spec_id: Specification ID
            
        Returns:
            List of common test ID patterns
        """
        patterns = []
        
        # LTE specifications (36.xxx)
        if spec_id.startswith('365'):
            patterns.extend([
                '6.2.2', '6.2.3', '6.2.4', '6.3.1', '6.3.2',
                '7.1.1', '7.1.2', '7.2.1', '7.3.1', '7.3.2',
                '8.1.1', '8.1.2', '8.2.1', '8.2.2', '8.3.1'
            ])
        
        # GSM/UMTS specifications (34.xxx)
        elif spec_id.startswith('34'):
            patterns.extend([
                '6.1.1.1', '6.1.1.2', '6.1.1.3', '6.1.1.4', '6.1.1.5',
                '6.1.2.1', '6.1.2.2', '6.1.3.1', '6.1.3.2',
                '10.1.2.1.1', '10.1.2.2.2', '10.1.2.3.1', '10.1.2.4.3'
            ])
        
        # 5G NR specifications (38.xxx)
        elif spec_id.startswith('38'):
            patterns.extend([
                '6.1.1', '6.1.2', '6.2.1', '6.2.2', '6.3.1',
                '7.1.1', '7.1.2', '7.2.1', '7.3.1', '8.1.1'
            ])
        
        # Security/SIM specifications (31.xxx)
        elif spec_id.startswith('31'):
            patterns.extend([
                '5.1.1', '5.1.2', '5.2.1', '5.2.2', '5.3.1',
                '6.1.1', '6.1.2', '6.2.1', '6.3.1'
            ])
        
        # Location services (37.xxx)
        elif spec_id.startswith('37'):
            patterns.extend([
                '5.1.1', '5.1.2', '5.2.1', '6.1.1', '6.1.2',
                '7.1.1', '7.1.2', '8.1.1'
            ])
        
        # GSM specifications (51.xxx)
        elif spec_id.startswith('51'):
            patterns.extend([
                '20.1', '20.2', '20.3', '26.6.1', '26.6.2',
                '26.7.1', '26.8.1', '26.9.1', '26.10.1'
            ])
        
        else:
            # Generic patterns for unknown specs
            patterns.extend([
                '5.1.1', '5.1.2', '6.1.1', '6.1.2', '7.1.1',
                '8.1.1', '9.1.1', '10.1.1'
            ])
        
        return patterns[:50]  # Limit to reasonable number